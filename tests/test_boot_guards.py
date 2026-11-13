"""Test Suite for Protocol RHP-1 Startup & Boot Guards (T-F2, T-F20, ST-2).

Specification Anchors:
- Architecture §6: Timing Profiles & Real Data Guard [F2, I13]
- Architecture §12: Broken-Build Concurrency Sandbox & Scratch Isolation [F20]
- BUILD_PLAN §1.1: Verification Gate (T-F2, T-F20)
"""

import sys
from pathlib import Path
import pytest

# Ensure api directory is on sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT / "api") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "api"))

from rhp.config import Settings, check_boot_guards


def test_valid_demo_fast_boot_with_synthetic_data():
    """Confirms DEMO_FAST boots cleanly when REAL_DATA=0 and BROKEN_BUILD=0."""
    settings = Settings(REAL_DATA=0, PROFILE="DEMO_FAST", BROKEN_BUILD=0, LAN_MODE=0)
    # Must not raise or exit
    check_boot_guards(settings)


def test_valid_demo_voice_boot_with_synthetic_data():
    """Confirms DEMO_VOICE boots cleanly when REAL_DATA=0 and BROKEN_BUILD=0."""
    settings = Settings(REAL_DATA=0, PROFILE="DEMO_VOICE", BROKEN_BUILD=0, LAN_MODE=0)
    check_boot_guards(settings)


def test_valid_pilot_profiles_with_real_data():
    """Confirms production pilot profiles (PILOT_OB_CRITICAL, PILOT_STANDARD) are permitted with REAL_DATA=1."""
    for pilot in ("PILOT_OB_CRITICAL", "PILOT_STANDARD"):
        settings = Settings(REAL_DATA=1, PROFILE=pilot, BROKEN_BUILD=0, LAN_MODE=0)
        check_boot_guards(settings)


def test_f2_demo_fast_aborts_on_real_data():
    """Closure F2: DEMO_FAST strictly refuses boot (hard abort code 78) when REAL_DATA=1."""
    settings = Settings(REAL_DATA=1, PROFILE="DEMO_FAST", BROKEN_BUILD=0, LAN_MODE=0)
    with pytest.raises(SystemExit) as exc_info:
        check_boot_guards(settings)
    assert exc_info.value.code == 78, f"Expected exit code 78, got {exc_info.value.code}"


def test_f2_demo_voice_aborts_on_real_data():
    """Closure F2: DEMO_VOICE strictly refuses boot (hard abort code 78) when REAL_DATA=1."""
    settings = Settings(REAL_DATA=1, PROFILE="DEMO_VOICE", BROKEN_BUILD=0, LAN_MODE=0)
    with pytest.raises(SystemExit) as exc_info:
        check_boot_guards(settings)
    assert exc_info.value.code == 78, f"Expected exit code 78, got {exc_info.value.code}"


def test_lan_mode_aborts_on_real_data():
    """Safety Guard: LAN_MODE=1 strictly refuses boot (hard abort code 78) when REAL_DATA=1."""
    settings = Settings(REAL_DATA=1, PROFILE="PILOT_OB_CRITICAL", BROKEN_BUILD=0, LAN_MODE=1)
    with pytest.raises(SystemExit) as exc_info:
        check_boot_guards(settings)
    assert exc_info.value.code == 78, f"Expected exit code 78, got {exc_info.value.code}"


def test_f20_broken_build_aborts_on_real_data():
    """Closure F20: BROKEN_BUILD=1 strictly refuses boot (hard abort code 78) when REAL_DATA=1."""
    settings = Settings(
        REAL_DATA=1,
        PROFILE="PILOT_OB_CRITICAL",
        BROKEN_BUILD=1,
        APP_DSN="postgresql://rhp_scratch_app:pw@pg:5432/rhp_scratch_broken",
    )
    with pytest.raises(SystemExit) as exc_info:
        check_boot_guards(settings)
    assert exc_info.value.code == 78, f"Expected exit code 78, got {exc_info.value.code}"


def test_f20_broken_build_aborts_on_primary_database_dsn():
    """Closure F20: BROKEN_BUILD=1 strictly refuses boot (hard abort code 78) if APP_DSN targets primary rhp_main."""
    settings = Settings(
        REAL_DATA=0,
        PROFILE="DEMO_FAST",
        BROKEN_BUILD=1,
        APP_DSN="postgresql://rhp_app:rhp_app_local_dev_only@pg:5432/rhp_main",
    )
    with pytest.raises(SystemExit) as exc_info:
        check_boot_guards(settings)
    assert exc_info.value.code == 78, f"Expected exit code 78, got {exc_info.value.code}"


def test_f20_broken_build_passes_with_scratch_database():
    """Closure F20: BROKEN_BUILD=1 boots cleanly when pointing exclusively to rhp_scratch_broken with REAL_DATA=0."""
    settings = Settings(
        REAL_DATA=0,
        PROFILE="DEMO_FAST",
        BROKEN_BUILD=1,
        APP_DSN="postgresql://rhp_scratch_app:pw@pg:5432/rhp_scratch_broken",
    )
    check_boot_guards(settings)


def test_settings_method_check_guards():
    """Confirms settings.check_guards() invokes the boot guard verification."""
    settings = Settings(REAL_DATA=1, PROFILE="DEMO_FAST")
    with pytest.raises(SystemExit) as exc_info:
        settings.check_guards()
    assert exc_info.value.code == 78
