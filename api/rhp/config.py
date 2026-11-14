"""ReferralHandshake Protocol RHP-1 — Workspace & Application Configuration.

Specification Anchors:
- Architecture §6: Timing Profiles & Real Data Guard [F2, I13]
- Architecture §12: Broken-Build Concurrency Sandbox & Scratch Isolation [F20]
- Architecture §17: Local & Demo Topology (T0-T3 Flags)
- BUILD_PLAN §1.1: Monorepo Topology & Environment Boot Guards
"""

from __future__ import annotations

import os
import sys
from functools import lru_cache
from typing import Optional

from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Protocol RHP-1 Application Settings & Environment Configuration."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    # 1. Profile & Safety Modes (§6, §12)
    PROFILE: str = Field(
        default="DEMO_FAST",
        validation_alias=AliasChoices("PROFILE", "ACTIVE_PROFILE"),
        description="Active timing profile: PILOT_OB_CRITICAL | PILOT_STANDARD | DEMO_FAST | DEMO_VOICE",
    )
    REAL_DATA: int = Field(
        default=0,
        description="Safety boundary: 0 = synthetic data only; 1 = real clinical data",
    )
    BROKEN_BUILD: int = Field(
        default=0,
        description="F20 fault switch: 1 routes traffic to rhp_scratch_broken without one_lease",
    )
    LAN_MODE: int = Field(
        default=0,
        description="Fail-closed local hotspot mode when venue internet is unavailable",
    )
    DEPLOYMENT_ID: str = Field(
        default="colossus3-bengaluru-demo",
        description="Deployment instance identifier",
    )

    # 2. Tier Feature Flags (§2)
    T1_TRANSPORT: int = Field(default=1, description="Tier 1: Transport tracking")
    T2_REACH: int = Field(default=1, description="Tier 2: Voice IVR, DLT SMS, Crockford paper codes")
    T3_EXTRAS: int = Field(default=0, description="Tier 3: Envelope crypto, AI intake, native Android")

    @property
    def broken_build(self) -> int:
        return self.BROKEN_BUILD

    @property
    def lan_mode(self) -> int:
        return self.LAN_MODE

    @property
    def profile(self) -> str:
        return self.PROFILE

    @property
    def real_data(self) -> int:
        return self.REAL_DATA

    # 3. Database Connection Strings (§7, §12)
    APP_DSN: str = Field(
        default="postgresql://rhp_app:rhp_app_local_dev_only@pg:5432/rhp_main",
        validation_alias=AliasChoices("APP_DSN", "RHP_APP_DSN", "PG_APP_DSN"),
        description="Primary database DSN for application command pipeline",
    )
    AUTONOMOUS_DSN: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("AUTONOMOUS_DSN", "PG_AUTONOMOUS_DSN"),
        description="Dedicated connection DSN for autonomous PIN lockout updates (F7)",
    )
    RHP_SCRATCH_DSN: str = Field(
        default="postgresql://rhp_scratch_app:rhp_scratch_local_dev_only@pg:5432/rhp_scratch_broken",
        validation_alias=AliasChoices("RHP_SCRATCH_DSN", "SCRATCH_DSN", "PG_SCRATCH_BROKEN_DSN"),
        description="Scratch database DSN for BROKEN_BUILD=1 isolated testing",
    )
    MONITOR_DSN: str = Field(
        default="postgresql://rhp_monitor:rhp_monitor_local_dev_only@pg:5432/rhp_main",
        validation_alias=AliasChoices("MONITOR_DSN", "RHP_MONITOR_DSN", "PG_MONITOR_DSN"),
        description="Read-only monitor DSN (F17)",
    )
    WITNESS_DSN: str = Field(
        default="postgresql://rhp_witness:rhp_witness_local_dev_only@pg:5432/rhp_main",
        validation_alias=AliasChoices("WITNESS_DSN", "RHP_WITNESS_DSN", "PG_WITNESS_DSN"),
        description="Witness signer DSN (F8)",
    )

    # 4. Cryptographic Keys & Public Key Anchors (§9, §11)
    COLD_PUBKEY_HEX: str = Field(
        default="d75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a",
        validation_alias=AliasChoices("COLD_PUBKEY_HEX", "COLD_PUBLIC_KEY_HEX"),
        description="Pinned Ed25519 cold public key for profile and restore verification",
    )
    WITNESS_PUBKEY_HEX: str = Field(
        default="3d4017c3e843895a92b70aa74d1b7ebc9c982ccf2ec4968cc0cd55f12af4660c",
        validation_alias=AliasChoices("WITNESS_PUBKEY_HEX", "WITNESS_PUBLIC_KEY_HEX"),
        description="Pinned Ed25519 witness public key for checkpoint signature verification",
    )

    # 5. Operational Specifications Path
    SPEC_DIR: str = Field(default="./spec", description="Path to directory containing frozen spec artifacts")

    @field_validator("AUTONOMOUS_DSN", mode="after")
    @classmethod
    def set_default_autonomous_dsn(cls, v: Optional[str], info) -> str:
        """Defaults AUTONOMOUS_DSN to APP_DSN if not explicitly provided."""
        if v:
            return v
        return info.data.get("APP_DSN", "postgresql://rhp_app:rhp_app_local_dev_only@pg:5432/rhp_main")

    def check_guards(self) -> None:
        """Enforces boot safety invariants directly on this settings instance."""
        check_boot_guards(self)


def check_boot_guards(settings: Optional[Settings] = None) -> None:
    """Enforces non-negotiable boot refusal invariants with exit code 78 (EX_CONFIG).

    Specification Closures:
    - Closure F2: Demo timing profiles (DEMO_FAST, DEMO_VOICE) MUST refuse boot if REAL_DATA=1.
    - Closure F20: BROKEN_BUILD=1 MUST refuse boot if REAL_DATA=1, and MUST point APP_DSN
      exclusively to the isolated scratch database rhp_scratch_broken.
    - LAN Mode Safety: LAN_MODE=1 is strictly forbidden with REAL_DATA=1.
    """
    if settings is None:
        settings = get_settings()
    # Guard 1 (F2): Demo profiles refuse boot on real data
    if settings.REAL_DATA == 1 and settings.PROFILE in ("DEMO_FAST", "DEMO_VOICE"):
        sys.stderr.write(
            f"FATAL [F2 GUARD]: Demo profile '{settings.PROFILE}' is strictly forbidden when REAL_DATA=1. "
            "Refusing boot with exit code 78.\n"
        )
        sys.exit(78)

    # Guard 2: LAN Mode refuse boot on real data
    if settings.REAL_DATA == 1 and settings.LAN_MODE == 1:
        sys.stderr.write(
            "FATAL [LAN GUARD]: LAN_MODE=1 is strictly forbidden when REAL_DATA=1. "
            "Refusing boot with exit code 78.\n"
        )
        sys.exit(78)

    # Guard 3 (F20): Broken build isolation guards
    if settings.BROKEN_BUILD == 1:
        if settings.REAL_DATA == 1:
            sys.stderr.write(
                "FATAL [F20 GUARD]: BROKEN_BUILD=1 is strictly forbidden when REAL_DATA=1. "
                "Refusing boot with exit code 78.\n"
            )
            sys.exit(78)

        if "rhp_scratch_broken" not in settings.APP_DSN:
            sys.stderr.write(
                f"FATAL [F20 GUARD]: BROKEN_BUILD=1 requires APP_DSN to target 'rhp_scratch_broken'. "
                f"Got '{settings.APP_DSN}'. Refusing boot with exit code 78.\n"
            )
            sys.exit(78)


@lru_cache(maxsize=1)
def get_settings(enforce_guards: bool = True) -> Settings:
    """Returns singleton Settings instance, optionally verifying boot guards."""
    s = Settings()
    if enforce_guards:
        check_boot_guards(s)
    return s
