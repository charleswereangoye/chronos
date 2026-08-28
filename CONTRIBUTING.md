# 🤝 Contributing to Chronos

Thank you for your interest in contributing to **Chronos**! We welcome contributions from developers, AI enthusiasts, and open-source contributors of all skill levels.

---

## 🧭 Code of Conduct
Please read and adhere to our [Code of Conduct](CODE_OF_CONDUCT.md) to ensure an inclusive, respectful environment for everyone.

---

## 🚀 Getting Started

### 1. Fork & Clone
```bash
git clone https://github.com/<your-username>/chronos.git
cd chronos
```

### 2. Branching Conventions
We use structured branch names:
- `feature/<agent-or-feature-name>` for new capabilities
- `bugfix/<issue-name>` for fixing bugs
- `docs/<topic>` for documentation improvements
- `chore/<task>` for maintenance, tooling, and CI/CD

Create your branch:
```bash
git checkout -b feature/awesome-agent
```

### 3. Local Environment Setup
```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scriptsctivate

# Install dependencies
pip install -r requirements.txt
pip install pytest ruff pytest-asyncio

# Install Playwright browser binaries
playwright install chromium

# Configure environment
cp .env.example .env  # Populate your API keys
```

---

## 🧪 Quality Standards & Testing

Before submitting a Pull Request, please ensure:
1. **Formatting & Linting**:
   ```bash
   ruff check .
   ```
2. **Automated Tests**:
   ```bash
   pytest test_*.py -v
   ```
3. **Container Compatibility**:
   ```bash
   docker-compose build
   ```

---

## 📬 Submitting a Pull Request
1. Commit your changes with descriptive messages:
   ```bash
   git commit -m "feat(social): add TikTok publisher connector"
   ```
2. Push to your fork:
   ```bash
   git push origin feature/awesome-agent
   ```
3. Open a Pull Request on GitHub against the `main` branch using the provided PR template.

Thank you for making Chronos better!
