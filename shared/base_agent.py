from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import logging

class AgentStatus(Enum):
    IDLE = "idle"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"

@dataclass
class AgentResult:
    status: AgentStatus
    data: Dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    @property
    def is_success(self) -> bool:
        return self.status == AgentStatus.SUCCESS

class BaseAgent(ABC):
    """
    Abstract Base Class for all specialized agents in Chronos.
    Enforces standardized execution lifecycle, logging, and error handling.
    """
    def __init__(self, name: Optional[str] = None):
        self.name = name or self.__class__.__name__
        self.logger = logging.getLogger(f"Agent.{self.name}")
        self.status = AgentStatus.IDLE

    @abstractmethod
    async def execute(self, payload: Optional[Dict[str, Any]] = None) -> AgentResult:
        """
        Core agent logic to be implemented by child classes.
        """
        pass

    async def run(self, payload: Optional[Dict[str, Any]] = None) -> AgentResult:
        """
        Wrapper around execute providing lifecycle management, status updates, and logging.
        """
        self.status = AgentStatus.RUNNING
        self.logger.info(f"Executing agent task with payload keys: {list(payload.keys()) if payload else []}")
        try:
            result = await self.execute(payload)
            self.status = result.status
            if result.is_success:
                self.logger.info("Execution completed successfully.")
            else:
                self.logger.warning(f"Execution finished with failure: {result.error_message}")
            return result
        except Exception as e:
            self.status = AgentStatus.FAILED
            self.logger.error(f"Unhandled exception during execution: {e}", exc_info=True)
            return AgentResult(
                status=AgentStatus.FAILED,
                error_message=str(e),
                data={"exception_type": type(e).__name__}
            )

    def get_info(self) -> Dict[str, Any]:
        """Returns agent metadata."""
        return {
            "name": self.name,
            "class": self.__class__.__name__,
            "status": self.status.value
        }
