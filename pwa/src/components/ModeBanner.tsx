import React, { useEffect, useState } from 'react';
import { AlertTriangle, AlertCircle, ShieldCheck } from 'lucide-react';

export interface ModeState {
  broken_build: boolean;
  lan_mode: boolean;
  real_data: number;
  heartbeat_stale: boolean;
  error?: string;
}

export const ModeBanner: React.FC = () => {
  const [mode, setMode] = useState<ModeState>({
    broken_build: false,
    lan_mode: false,
    real_data: 0,
    heartbeat_stale: false,
  });

  useEffect(() => {
    let mounted = true;

    const checkModes = async () => {
      try {
        const modeRes = await fetch('/mode');
        const modeData = modeRes.ok ? await modeRes.json() : {};

        const healthRes = await fetch('/healthz');
        const healthData = healthRes.ok ? await healthRes.json() : {};

        if (mounted) {
          const nowMs = Date.now();
          let stale = false;
          if (healthData.components) {
            for (const comp of Object.values<any>(healthData.components)) {
              const age = comp.age_seconds ?? (comp.last_heartbeat_ms ? (nowMs - comp.last_heartbeat_ms) / 1000 : 0);
              if (age > 15) {
                stale = true;
                break;
              }
            }
          }

          setMode({
            broken_build: Boolean(modeData.broken_build || modeData.BROKEN_BUILD),
            lan_mode: Boolean(modeData.lan_mode || modeData.LAN_MODE),
            real_data: Number(modeData.real_data ?? 0),
            heartbeat_stale: stale,
          });
        }
      } catch (err: any) {
        if (mounted) {
          // If offline or fetch failed, don't crash
          setMode((prev) => ({ ...prev, heartbeat_stale: true }));
        }
      }
    };

    checkModes();
    const interval = setInterval(checkModes, 5000);
    return () => {
      mounted = false;
      clearInterval(interval);
    };
  }, []);

  return (
    <div className="w-full flex flex-col gap-1 z-50">
      {/* 1. Flashing Red Banner for BROKEN_BUILD == 1 */}
      {mode.broken_build && (
        <div className="bg-red-600 text-white font-extrabold px-4 py-2 flex items-center justify-center gap-3 animate-pulse border-b-2 border-red-900 shadow-lg tracking-wide uppercase text-sm sm:text-base">
          <AlertTriangle className="w-5 h-5 flex-shrink-0" />
          <span>BROKEN BUILD — SCRATCH DB (LEASE GUARD DISABLED)</span>
          <AlertTriangle className="w-5 h-5 flex-shrink-0" />
        </div>
      )}

      {/* 2. Amber Banner for LAN_MODE == 1 or Stale Heartbeat (>15s) */}
      {(mode.lan_mode || mode.heartbeat_stale) && (
        <div className="bg-amber-500 text-black font-semibold px-4 py-1.5 flex items-center justify-between text-xs sm:text-sm border-b border-amber-600">
          <div className="flex items-center gap-2">
            <AlertCircle className="w-4 h-4 flex-shrink-0" />
            <span>
              {mode.lan_mode && 'LAN MODE ACTIVE — Turnstile Bypassed.'}
              {mode.heartbeat_stale && ' Warning: Worker heartbeat >15s stale.'}
            </span>
          </div>
          <span className="text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 bg-amber-600/30 rounded">
            Degraded Telemetry
          </span>
        </div>
      )}

      {/* 3. Top Header Bar with Persistent Synthetic Data Badge */}
      <div className="bg-slate-800/90 backdrop-blur border-b border-slate-700 px-4 py-1.5 flex items-center justify-between text-xs text-slate-300">
        <div className="flex items-center gap-2">
          <span className="font-bold tracking-tight text-white flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-emerald-400 inline-block animate-ping"></span>
            ReferralHandshake
          </span>
          <span className="text-slate-400">|</span>
          <span className="text-slate-300 font-mono">Protocol RHP-1</span>
        </div>

        <div className="flex items-center gap-2">
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-semibold bg-blue-900/40 text-blue-300 border border-blue-700/50">
            <ShieldCheck className="w-3.5 h-3.5 text-blue-400" />
            SYNTHETIC DATA ONLY (REAL_DATA=0)
          </span>
        </div>
      </div>
    </div>
  );
};

