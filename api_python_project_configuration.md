[build-system]
requires = ["hatchling>=1.25.0"]
build-backend = "hatchling.build"

[project]
name = "rhp-api"
version = "1.0.0"
description = "ReferralHandshake (RHP-1) Reference Platform: Command API, 2-Phase Deadline Poller, Outbox Relay & Proof Harness"
readme = "../README.md"
requires-python = ">=3.12"
license = { text = "MIT" }
authors = [
  { name = "Team MAHA YODHAS (Colossus 3.0)" }
]
dependencies = [
  "fastapi>=0.115.4",
  "uvicorn[standard]>=0.32.0",
  "psycopg[binary,pool]>=3.2.3",
  "pydantic>=2.9.2",
  "pydantic-settings>=2.6.1",
  "argon2-cffi>=23.1.0",
  "cryptography>=43.0.3",
  "pyyaml>=6.0.2",
  "httpx>=0.27.2",
  "sse-starlette>=2.1.3",
  "networkx>=3.4.2",
  "python-multipart>=0.0.17"
]

[project.optional-dependencies]
dev = [
  "pytest>=8.3.3",
  "pytest-asyncio>=0.24.0",
  "pytest-timeout>=2.3.1",
  "hypothesis>=6.115.6",
  "ruff>=0.7.2",
  "mypy>=1.13.0",
  "types-PyYAML>=6.0.12.20240917"
]

[project.scripts]
rhp-api = "rhp.main:run"
rhp-poller = "rhp.poller:main"
rhp-relay = "rhp.relay:main"
rhp-validate-profiles = "rhp.profiles:validate_cli"

[tool.hatch.build.targets.wheel]
packages = ["rhp"]

[tool.pytest.ini_options]
minversion = "8.0"
asyncio_mode = "auto"
asyncio_default_fixture_loop_scope = "function"
testpaths = ["tests"]
addopts = "-ra -q --strict-markers"
markers = [
  "conformance: RHP-1 state machine conformance vectors",
  "race200: 200-way concurrent accept barrier test (T-C1) and lock-order test (T-F1)",
  "mutation: Six-part mutation test suite (M1-M6, T-F17)",
  "toxiproxy: Network and database fault-injection matrix",
  "security: PIN lockout scope, BOLA, and SSE grant revocation tests"
]

[tool.ruff]
target-version = "py312"
line-length = 100

[tool.ruff.lint]
select = ["E", "F", "I", "B", "UP", "S", "ASYNC"]
ignore = ["S101"]

[tool.mypy]
python_version = "3.12"
strict = true
warn_return_any = true
warn_unused_configs = true
plugins = ["pydantic.mypy"]