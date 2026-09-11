import logging
import math
from dataclasses import dataclass
from typing import Any, ClassVar

from shared.base_agent import AgentResult, AgentStatus, BaseAgent

logger = logging.getLogger("RiskGuard")


@dataclass
class RiskValidationResult:
    is_approved: bool
    status: str  # "APPROVED" or "REJECTED"
    risk_reward_ratio: float
    risk_distance: float
    reward_distance: float
    risk_pips: float
    reward_pips: float
    max_risk_dollars: float
    actual_risk_dollars: float
    actual_risk_pct: float
    recommended_lots: float
    rejection_reasons: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "is_approved": self.is_approved,
            "status": self.status,
            "risk_reward_ratio": round(self.risk_reward_ratio, 2),
            "risk_distance": round(self.risk_distance, 5),
            "reward_distance": round(self.reward_distance, 5),
            "risk_pips": round(self.risk_pips, 1),
            "reward_pips": round(self.reward_pips, 1),
            "max_risk_dollars": round(self.max_risk_dollars, 2),
            "actual_risk_dollars": round(self.actual_risk_dollars, 2),
            "actual_risk_pct": round(self.actual_risk_pct, 3),
            "recommended_lots": round(self.recommended_lots, 2),
            "rejection_reasons": self.rejection_reasons,
        }


class RiskGuard(BaseAgent):
    """Mathematical Safety Bounds & Capital Protection Gatekeeper.

    Enforces unbreakable risk constraints:
    1. Maximum 1.0% account risk per trade setup.
    2. Unbreakable minimum 1:2.0 Risk-to-Reward ratio.
    Rejects any trade setup that fails these institutional safety bounds.
    """

    MAX_ACCOUNT_RISK_RATIO: ClassVar[float] = 0.01  # Hard ceiling: 1%
    MIN_RISK_REWARD_RATIO: ClassVar[float] = 2.0  # Hard floor: 1:2 RR

    def __init__(self, name: str = "RiskGuard"):
        super().__init__(name=name)

    @staticmethod
    def get_pip_specs(pair: str, current_price: float = 1.0) -> tuple[float, float]:
        """Returns (pip_size, pip_value_per_standard_lot_usd) for the asset."""
        clean = pair.upper().replace("/", "").replace("_", "")
        if "XAU" in clean or "GOLD" in clean:
            # Gold: 1 pip = $0.10, standard 100oz contract = $10 per 0.10 move ($100 / point)
            return 0.10, 10.0
        elif "JPY" in clean:
            # JPY pairs: 1 pip = 0.01; pip value in USD = 1000 / USDJPY rate (~$6.50 - $10)
            pip_size = 0.01
            jpy_rate = current_price if current_price > 10.0 else 150.0
            pip_value = 1000.0 / jpy_rate
            return pip_size, pip_value
        else:
            # Standard FX pairs (EURUSD, GBPUSD, AUDUSD): 1 pip = 0.0001, $10 per pip on 100k lot
            return 0.0001, 10.0

    def validate_setup(
        self,
        direction: str,
        entry_price: float,
        stop_loss: float,
        target_price: float,
        account_balance: float = 10000.0,
        pair: str = "EURUSD",
    ) -> RiskValidationResult:
        """Mathematically verifies strict risk compliance against unbreakable bounds."""
        rejection_reasons: list[str] = []
        dir_clean = direction.strip().upper()

        if account_balance <= 0:
            rejection_reasons.append(
                f"Invalid account balance: ${account_balance:.2f}. Balance must be positive."
            )
            account_balance = 10000.0

        if entry_price <= 0 or stop_loss <= 0 or target_price <= 0:
            rejection_reasons.append("Entry, Stop Loss, and Target must all be positive numbers.")
            return RiskValidationResult(
                is_approved=False,
                status="REJECTED",
                risk_reward_ratio=0.0,
                risk_distance=0.0,
                reward_distance=0.0,
                risk_pips=0.0,
                reward_pips=0.0,
                max_risk_dollars=account_balance * self.MAX_ACCOUNT_RISK_RATIO,
                actual_risk_dollars=0.0,
                actual_risk_pct=0.0,
                recommended_lots=0.0,
                rejection_reasons=rejection_reasons,
            )

        pip_size, pip_value_usd = self.get_pip_specs(pair, current_price=entry_price)
        max_risk_dollars = account_balance * self.MAX_ACCOUNT_RISK_RATIO

        # Directional Geometry & Distance Checks
        if dir_clean in ("BUY", "LONG", "BULLISH"):
            if stop_loss >= entry_price:
                rejection_reasons.append(
                    f"Structural violation: For a LONG setup, Stop Loss ({stop_loss}) "
                    f"must be strictly below Entry ({entry_price})."
                )
            if target_price <= entry_price:
                rejection_reasons.append(
                    f"Structural violation: For a LONG setup, Target ({target_price}) "
                    f"must be strictly above Entry ({entry_price})."
                )
            risk_dist = max(0.0, entry_price - stop_loss)
            reward_dist = max(0.0, target_price - entry_price)

        elif dir_clean in ("SELL", "SHORT", "BEARISH"):
            if stop_loss <= entry_price:
                rejection_reasons.append(
                    f"Structural violation: For a SHORT setup, Stop Loss ({stop_loss}) "
                    f"must be strictly above Entry ({entry_price})."
                )
            if target_price >= entry_price:
                rejection_reasons.append(
                    f"Structural violation: For a SHORT setup, Target ({target_price}) "
                    f"must be strictly below Entry ({entry_price})."
                )
            risk_dist = max(0.0, stop_loss - entry_price)
            reward_dist = max(0.0, entry_price - target_price)

        else:
            rejection_reasons.append(
                f"Unknown trade direction '{direction}'. Must be BUY/LONG or SELL/SHORT."
            )
            risk_dist = abs(entry_price - stop_loss)
            reward_dist = abs(target_price - entry_price)

        if risk_dist <= 0:
            rejection_reasons.append("Zero or negative risk distance. Cannot calculate Risk-to-Reward.")
            rr_ratio = 0.0
            risk_pips = 0.0
            reward_pips = 0.0
        else:
            rr_ratio = round(reward_dist / risk_dist, 2)
            risk_pips = round(risk_dist / pip_size, 1)
            reward_pips = round(reward_dist / pip_size, 1)

        # Unbreakable Rule 1: Risk-to-Reward Floor (1:2.0)
        # Using 4 decimal places rounding to avoid IEEE 754 precision artifacts (e.g. 1.999999999999911 < 2.0)
        if round(rr_ratio, 4) < self.MIN_RISK_REWARD_RATIO:
            rejection_reasons.append(
                f"UNBREAKABLE BOUND VIOLATION: Risk-to-Reward ratio 1:{rr_ratio:.2f} "
                f"is strictly below the mandatory institutional threshold of 1:{self.MIN_RISK_REWARD_RATIO:.1f}."
            )

        # Unbreakable Rule 2: Maximum 1% Account Risk Position Sizing
        if risk_pips > 0:
            raw_lot_size = max_risk_dollars / (risk_pips * pip_value_usd)
            # Round down to 2 decimal places to strictly never exceed 1% risk
            recommended_lots = math.floor(raw_lot_size * 100.0) / 100.0

            if recommended_lots < 0.01:
                # Even the micro-lot threshold of 0.01 exceeds 1% risk
                micro_risk_dollars = 0.01 * risk_pips * pip_value_usd
                micro_risk_pct = (micro_risk_dollars / account_balance) * 100.0
                rejection_reasons.append(
                    f"UNBREAKABLE BOUND VIOLATION: Stop loss distance ({risk_pips:.1f} pips) "
                    f"would risk {micro_risk_pct:.2f}% even at minimum broker lot size (0.01 lots), "
                    f"exceeding the strict 1.0% account ceiling (${max_risk_dollars:.2f})."
                )
                recommended_lots = 0.0
                actual_risk_dollars = micro_risk_dollars
                actual_risk_pct = micro_risk_pct
            else:
                actual_risk_dollars = recommended_lots * risk_pips * pip_value_usd
                actual_risk_pct = (actual_risk_dollars / account_balance) * 100.0
        else:
            recommended_lots = 0.0
            actual_risk_dollars = 0.0
            actual_risk_pct = 0.0

        is_approved = len(rejection_reasons) == 0

        return RiskValidationResult(
            is_approved=is_approved,
            status="APPROVED" if is_approved else "REJECTED",
            risk_reward_ratio=rr_ratio,
            risk_distance=risk_dist,
            reward_distance=reward_dist,
            risk_pips=risk_pips,
            reward_pips=reward_pips,
            max_risk_dollars=max_risk_dollars,
            actual_risk_dollars=actual_risk_dollars,
            actual_risk_pct=actual_risk_pct,
            recommended_lots=recommended_lots,
            rejection_reasons=rejection_reasons,
        )

    async def execute(self, payload: dict[str, Any] | None = None) -> AgentResult:
        payload = payload or {}
        pair = payload.get("pair", "EURUSD")
        direction = payload.get("direction", "BUY")
        entry = float(payload.get("entry_price", payload.get("entry", 1.0850)))
        stop_loss = float(payload.get("stop_loss", 1.0800))
        target = float(payload.get("target_price", payload.get("target", 1.0950)))
        balance = float(payload.get("account_balance", payload.get("balance", 10000.0)))

        validation = self.validate_setup(
            direction=direction,
            entry_price=entry,
            stop_loss=stop_loss,
            target_price=target,
            account_balance=balance,
            pair=pair,
        )

        return AgentResult(
            status=AgentStatus.SUCCESS,
            data={
                "pair": pair,
                "direction": direction,
                "entry_price": entry,
                "stop_loss": stop_loss,
                "target_price": target,
                "account_balance": balance,
                "validation": validation.to_dict(),
            },
        )
