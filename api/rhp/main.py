"""FastAPI Application Main Entry Point (§5, §6, Closures F10, F11, Invariants I10, I16).

Provides:
- GET /healthz: Checks DB connectivity, evaluates worker heartbeats (POLLER, RELAY, MONITOR, WITNESS),
  and alarms on stale components (>15s) or excessive NTP drift (>2000ms) with AMBER status.
- GET /metrics: Exposes Prometheus-compatible text metrics for heartbeats and clock slew alarms.
- GET /v1/stream: Authorized Server-Sent Events (SSE) hub endpoint with Last-Event-ID support,
  15s heartbeats, and per-frame Invariant I10 payload grant enforcement.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import queue
import tempfile
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any, AsyncGenerator, Dict, List, Optional
from uuid import UUID

from fastapi import Cookie, FastAPI, Header, HTTPException, Query, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse, StreamingResponse

from api.rhp.auth import AuthError, Session, load_session
from api.rhp.commands.judge_join import router as judge_router
from api.rhp.config import check_boot_guards, get_settings
from api.rhp.db import get_main_connection
from api.rhp.routes import router as v1_router
from api.rhp.sse import SSESubscriber, format_heartbeat_frame, get_sse_hub

logger = logging.getLogger("rhp.api")

# Required background components whose heartbeats must be tracked
REQUIRED_HEARTBEAT_COMPONENTS = ["POLLER", "RELAY", "MONITOR", "WITNESS"]


def evaluate_heartbeats(conn: Any) -> Dict[str, Any]:
    """Queries the heartbeat table and computes component status and alarms.

    Alarms if any component last_seen > 15s ago or abs(ntp_offset_ms) > 2000ms.
    """
    now = datetime.now(timezone.utc)
    results: Dict[str, Dict[str, Any]] = {}
    is_amber = False
    alarms: List[str] = []

    # Read from MockDatabase, IPC file, or PostgreSQL
    raw_rows: Dict[str, Dict[str, Any]] = {}
    ipc_path = os.path.join(tempfile.gettempdir(), "rhp_heartbeats_ipc.json")
    if os.path.exists(ipc_path):
        try:
            with open(ipc_path, "r", encoding="utf-8") as f:
                ipc_data = json.load(f)
                for k, v in ipc_data.items():
                    raw_rows[v["subject_kind"].upper()] = v
        except Exception:
            pass

    if hasattr(conn, "db"):
        if hasattr(conn.db, "heartbeats"):
            for (kind, sid), data in conn.db.heartbeats.items():
                if kind.upper() not in raw_rows:
                    raw_rows[kind.upper()] = data
    else:
        cur = conn.execute("SELECT subject_kind, subject_id, last_seen, ntp_offset_ms FROM heartbeat;")
        rows = cur.fetchall() if cur else []
        for r in rows:
            kind, sid, last_seen, offset = str(r[0]).upper(), str(r[1]), r[2], r[3]
            raw_rows[kind] = {
                "subject_kind": kind,
                "subject_id": sid,
                "last_seen": last_seen,
                "ntp_offset_ms": int(offset or 0),
            }

    for comp in REQUIRED_HEARTBEAT_COMPONENTS:
        data = raw_rows.get(comp)
        if not data:
            results[comp] = {"status": "MISSING", "age_seconds": None, "ntp_offset_ms": 0}
            is_amber = True
            alarms.append(f"{comp}_HEARTBEAT_MISSING")
            continue

        last_seen = data.get("last_seen")
        if isinstance(last_seen, str):
            last_seen = datetime.fromisoformat(last_seen)
        if last_seen and last_seen.tzinfo is None:
            last_seen = last_seen.replace(tzinfo=timezone.utc)

        age_sec = (now - last_seen).total_seconds() if last_seen else 9999.0
        ntp_offset = int(data.get("ntp_offset_ms", 0) or 0)

        st = "OK"
        if age_sec > 15.0:
            st = "STALE"
            is_amber = True
            alarms.append(f"{comp}_STALE_{int(age_sec)}S")
        if abs(ntp_offset) > 2000:
            st = "CLOCK_DRIFT"
            is_amber = True
            alarms.append(f"{comp}_NTP_OFFSET_{ntp_offset}MS")

        results[comp] = {
            "status": st,
            "subject_id": data.get("subject_id"),
            "age_seconds": round(age_sec, 2),
            "ntp_offset_ms": ntp_offset,
        }

    return {
        "overall_status": "AMBER" if is_amber else "GREEN",
        "alarms": alarms,
        "components": results,
    }


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Enforces strict boot-time guards and timing profile signature verification."""
    check_boot_guards()
    yield


app = FastAPI(
    title="ReferralHandshake (Protocol RHP-1) API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(judge_router)
app.include_router(v1_router)


@app.get("/mode")
def get_mode():
    """Returns runtime deployment mode flags for PWA banner and judge onboarding."""
    settings = get_settings()
    return {
        "broken_build": settings.broken_build,
        "lan_mode": settings.lan_mode,
        "profile": settings.profile,
        "real_data": settings.real_data,
    }


@app.get("/healthz")
def get_healthz():
    """Health check endpoint exposing DB connectivity, worker liveness, and clock sync."""
    try:
        with get_main_connection() as conn:
            # Slew-only clock check: clock_timestamp() >= head_ts
            cur = conn.execute("SELECT clock_timestamp();")
            server_now = cur.fetchone()[0] if cur else datetime.now(timezone.utc)
            hb_data = evaluate_heartbeats(conn)

        overall = hb_data["overall_status"]
        status_code = status.HTTP_200_OK if overall == "GREEN" else status.HTTP_503_SERVICE_UNAVAILABLE

        resp_body = {
            "status": overall,
            "server_time": str(server_now),
            "alarms": hb_data["alarms"],
            "components": hb_data["components"],
        }
        return Response(
            content=json.dumps(resp_body),
            status_code=status_code,
            media_type="application/json",
        )
    except Exception as e:
        logger.error(f"Healthz failure: {e}")
        return Response(
            content=f'{{"status": "DOWN", "error": "{str(e)}"}}',
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            media_type="application/json",
        )


@app.get("/metrics", response_class=PlainTextResponse)
def get_metrics():
    """Prometheus-compatible metrics endpoint."""
    lines: List[str] = [
        "# HELP rhp_health_status Status of the system (1 = GREEN, 0 = AMBER/DOWN)",
        "# TYPE rhp_health_status gauge",
    ]
    try:
        with get_main_connection() as conn:
            hb = evaluate_heartbeats(conn)

        is_green = 1 if hb["overall_status"] == "GREEN" else 0
        lines.append(f'rhp_health_status{{status="{hb["overall_status"]}"}} {is_green}')

        lines.append("# HELP rhp_heartbeat_last_seen_seconds Age of component heartbeat in seconds")
        lines.append("# TYPE rhp_heartbeat_last_seen_seconds gauge")
        for comp, info in hb["components"].items():
            age = info["age_seconds"] if info["age_seconds"] is not None else 9999.0
            lines.append(f'rhp_heartbeat_last_seen_seconds{{component="{comp}"}} {age}')

        lines.append("# HELP rhp_heartbeat_ntp_offset_ms NTP offset reported by component")
        lines.append("# TYPE rhp_heartbeat_ntp_offset_ms gauge")
        for comp, info in hb["components"].items():
            lines.append(f'rhp_heartbeat_ntp_offset_ms{{component="{comp}"}} {info["ntp_offset_ms"]}')

        lines.append("# HELP rhp_clock_slew_alarm Flag indicating excessive clock offset (>2000ms)")
        lines.append("# TYPE rhp_clock_slew_alarm gauge")
        for comp, info in hb["components"].items():
            alarm = 1 if abs(info["ntp_offset_ms"]) > 2000 else 0
            lines.append(f'rhp_clock_slew_alarm{{component="{comp}"}} {alarm}')

    except Exception as e:
        lines.append(f"# Error collecting metrics: {e}")

    return "\n".join(lines) + "\n"


@app.get("/v1/stream")
async def stream_events(
    request: Request,
    rhp_session: Optional[str] = Cookie(default=None),
    authorization: Optional[str] = Header(default=None),
    last_event_id: Optional[str] = Header(default=None, alias="Last-Event-ID"),
):
    """Server-Sent Events endpoint with session validation and Per-Frame Grant Checking."""
    # 1. Resolve session token
    token = rhp_session
    if not token and authorization:
        parts = authorization.split()
        if len(parts) == 2 and parts[0].lower() == "bearer":
            token = parts[1]

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="rhp_session cookie or Bearer token is required",
        )

    # 2. Authenticate session
    with get_main_connection() as conn:
        try:
            sess = load_session(conn, token)
        except AuthError as ae:
            raise HTTPException(status_code=ae.http_status, detail=ae.message)

    # Parse Last-Event-ID
    from_id: Optional[int] = None
    if last_event_id is not None:
        try:
            from_id = int(last_event_id)
        except ValueError:
            pass

    hub = get_sse_hub()
    sub = hub.subscribe(session=sess, last_event_id=from_id)

    # Replay missed events if requested
    if from_id is not None:
        with get_main_connection() as conn:
            hub.replay_missed_events(conn, sub, from_id)

    async def sse_generator() -> AsyncGenerator[str, None]:
        hb_interval = 15.0
        try:
            while sub.active:
                # Check for queued frames with a 15-second heartbeat timeout
                try:
                    # Run queue get in executor to avoid blocking async event loop
                    frame = await asyncio.to_thread(sub.queue.get, True, hb_interval)
                    yield frame
                except queue.Empty:
                    # Emit 15s heartbeat comment frame
                    yield format_heartbeat_frame()

                    # Re-verify session validity on each heartbeat
                    with get_main_connection() as conn_hb:
                        try:
                            load_session(conn_hb, token)
                        except AuthError:
                            logger.info(f"Session {sess.id} expired during SSE stream, disconnecting")
                            break
        finally:
            hub.unsubscribe(sub)

    return StreamingResponse(
        sse_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
