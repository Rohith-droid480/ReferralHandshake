import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Play,
  RotateCcw,
  AlertTriangle,
  Users,
  Clock,
  WifiOff,
  ShieldAlert,
  Sliders,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
} from 'lucide-react';

interface ScenarioResult {
  scenario: string;
  status: 'IDLE' | 'RUNNING' | 'SUCCESS' | 'ERROR';
  message: string;
  referralId?: string;
}

export const DemoScenariosBar: React.FC = () => {
  const navigate = useNavigate();
  const [result, setResult] = useState<ScenarioResult | null>(null);
  const [underTheHoodOpen, setUnderTheHoodOpen] = useState(false);
  const [loading, setLoading] = useState(false);

  // S1: Eclampsia with UNKNOWN MgSO4
  const runS1 = async () => {
    setLoading(true);
    setResult({ scenario: 'S1', status: 'RUNNING', message: 'Creating severe eclampsia referral with MgSO4 UNKNOWN...' });
    try {
      const resp = await fetch('/v1/referrals', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          mode: 'SEQUENTIAL',
          need_class: 'OBSTETRIC_EMERGENCY',
          origin_facility_id: '11111111-1111-1111-1111-111111111111',
          chain: [
            '22222222-2222-2222-2222-222222222222',
            '44444444-4444-4444-4444-444444444444',
          ],
          mgso4_status: 'UNKNOWN',
          expected_version: 0,
          clinical_payload: {
            patient_id: 'SYNTH-OB-S1',
            age: 23,
            gravida: 1,
            para: 0,
            bp_sys: 168,
            bp_dia: 112,
            clinical_summary: 'Severe pre-eclampsia with seizures. MgSO4 status UNKNOWN.',
          },
        }),
      });

      if (resp.ok) {
        const data = await resp.json();
        setResult({
          scenario: 'S1',
          status: 'SUCCESS',
          message: 'S1 Created! Receiving hospital shows red alert: "Pre-referral MgSO4 dose unknown — verify before dosing".',
          referralId: data.referral_id || data.id,
        });
        // Switch to receiving desk view
        setTimeout(() => navigate('/receiving-desk'), 800);
      } else {
        const err = await resp.json().catch(() => ({}));
        setResult({ scenario: 'S1', status: 'ERROR', message: err.detail || 'Creation failed' });
      }
    } catch (e: any) {
      setResult({ scenario: 'S1', status: 'ERROR', message: e.message });
    } finally {
      setLoading(false);
    }
  };

  // S2: Two hospitals accept at once (concurrency race)
  const runS2 = async () => {
    setLoading(true);
    setResult({ scenario: 'S2', status: 'RUNNING', message: 'Spawning 2-facility race: CHC Ramanagara vs DH Mandya...' });
    try {
      const resp = await fetch('/v1/arena/spawn-race', { method: 'POST' });
      if (resp.ok) {
        const data = await resp.json();
        setResult({
          scenario: 'S2',
          status: 'SUCCESS',
          message: `S2 Race Active! Case offered to two hospitals simultaneously. Exactly 1 can hold the admission lease.`,
          referralId: data.referral_id,
        });
        setTimeout(() => navigate('/arena'), 800);
      } else {
        const err = await resp.json().catch(() => ({}));
        setResult({ scenario: 'S2', status: 'ERROR', message: err.detail || 'Race setup failed' });
      }
    } catch (e: any) {
      setResult({ scenario: 'S2', status: 'ERROR', message: e.message });
    } finally {
      setLoading(false);
    }
  };

  // S3: Nobody responds (accelerated escalation)
  const runS3 = async () => {
    setLoading(true);
    setResult({ scenario: 'S3', status: 'RUNNING', message: 'Starting silence ladder with accelerated demo profile...' });
    try {
      const resp = await fetch('/v1/arena/spawn-silence-ladder', { method: 'POST' });
      if (resp.ok) {
        const data = await resp.json();
        setResult({
          scenario: 'S3',
          status: 'SUCCESS',
          message: 'S3 Silence Ladder active! Demo clock accelerated (production: minutes). Offer times out to 108 Dispatcher.',
          referralId: data.referral_id,
        });
        setTimeout(() => navigate('/dispatcher'), 800);
      } else {
        const err = await resp.json().catch(() => ({}));
        setResult({ scenario: 'S3', status: 'ERROR', message: err.detail || 'Ladder spawn failed' });
      }
    } catch (e: any) {
      setResult({ scenario: 'S3', status: 'ERROR', message: e.message });
    } finally {
      setLoading(false);
    }
  };

  // S4: Network offline & paper code handover
  const runS4 = () => {
    setResult({
      scenario: 'S4',
      status: 'SUCCESS',
      message: 'S4 Offline Handover: Paper Code "XKV68JK68" (9-char Crockford Base32 + mod-37). Offline crew handovers sync back on reconnect.',
    });
    navigate('/clinician');
  };

  // S5: Stale capability reconfirmation test
  const runS5 = async () => {
    setLoading(true);
    setResult({ scenario: 'S5', status: 'RUNNING', message: 'Staling capability confirmations (e.g. blood bank depleted)...' });
    try {
      const resp = await fetch('/v1/arena/stale-capability', { method: 'POST' });
      if (resp.ok) {
        setResult({
          scenario: 'S5',
          status: 'SUCCESS',
          message: 'S5 Stale Capability: Hospital Blood/OT confirmation expired. Acceptance blocked until clinician reconfirms on desk.',
        });
        setTimeout(() => navigate('/receiving-desk'), 800);
      } else {
        setResult({ scenario: 'S5', status: 'ERROR', message: 'Failed to expire capability' });
      }
    } catch (e: any) {
      setResult({ scenario: 'S5', status: 'ERROR', message: e.message });
    } finally {
      setLoading(false);
    }
  };

  // S6: Tamper test
  const runS6 = async () => {
    setLoading(true);
    setResult({ scenario: 'S6', status: 'RUNNING', message: 'Injecting simulated database tampering into event log...' });
    try {
      const resp = await fetch('/v1/arena/tamper', { method: 'POST' });
      if (resp.ok) {
        setResult({
          scenario: 'S6',
          status: 'SUCCESS',
          message: 'S6 Tamper Injected! Database event log modified. Browser verifier will flag RED: TAMPER DETECTED.',
        });
        setTimeout(() => navigate('/arena'), 800);
      } else {
        setResult({ scenario: 'S6', status: 'ERROR', message: 'Tamper injection failed' });
      }
    } catch (e: any) {
      setResult({ scenario: 'S6', status: 'ERROR', message: e.message });
    } finally {
      setLoading(false);
    }
  };

  // Reset and seed
  const runReset = async () => {
    setLoading(true);
    setResult({ scenario: 'RESET', status: 'RUNNING', message: 'Resetting synthetic demo data...' });
    try {
      const resp = await fetch('/v1/demo/reset-and-seed', { method: 'POST' });
      if (resp.ok) {
        setResult({
          scenario: 'RESET',
          status: 'SUCCESS',
          message: 'Clean Demo State: Referrals, rosters, and test cases reset to initial state.',
        });
      } else {
        setResult({ scenario: 'RESET', status: 'ERROR', message: 'Reset failed' });
      }
    } catch (e: any) {
      setResult({ scenario: 'RESET', status: 'ERROR', message: e.message });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-slate-900 border-b border-slate-800 text-xs text-slate-300">
      <div className="max-w-7xl mx-auto px-4 py-2.5">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-2 font-semibold text-slate-200">
            <Sliders className="w-4 h-4 text-teal-400" />
            <span className="tracking-tight">Demo Scenarios (One-Click Live Deterministic Flows):</span>
          </div>

          <div className="flex flex-wrap items-center gap-1.5">
            <button
              onClick={runS1}
              disabled={loading}
              className="px-2.5 py-1 bg-slate-800 hover:bg-slate-700 text-teal-300 hover:text-white border border-slate-700 rounded font-medium flex items-center gap-1 transition"
              title="Severe Eclampsia: MgSO4 status UNKNOWN. Receiving hospital shows persistent red warning."
            >
              <AlertTriangle className="w-3.5 h-3.5 text-amber-400" />
              <span>S1: MgSO4 UNKNOWN</span>
            </button>

            <button
              onClick={runS2}
              disabled={loading}
              className="px-2.5 py-1 bg-slate-800 hover:bg-slate-700 text-teal-300 hover:text-white border border-slate-700 rounded font-medium flex items-center gap-1 transition"
              title="2 Hospitals Accept at Once: Exactly one holds the case; the other receives 409 Conflict."
            >
              <Users className="w-3.5 h-3.5 text-blue-400" />
              <span>S2: 2-Hospital Race</span>
            </button>

            <button
              onClick={runS3}
              disabled={loading}
              className="px-2.5 py-1 bg-slate-800 hover:bg-slate-700 text-teal-300 hover:text-white border border-slate-700 rounded font-medium flex items-center gap-1 transition"
              title="Nobody Responds: Accelerated demo timing ladder escalates case to 108 Dispatcher."
            >
              <Clock className="w-3.5 h-3.5 text-indigo-400" />
              <span>S3: Silence Escalation</span>
            </button>

            <button
              onClick={runS4}
              disabled={loading}
              className="px-2.5 py-1 bg-slate-800 hover:bg-slate-700 text-teal-300 hover:text-white border border-slate-700 rounded font-medium flex items-center gap-1 transition"
              title="Network Offline: 9-character Crockford paper code handover."
            >
              <WifiOff className="w-3.5 h-3.5 text-slate-400" />
              <span>S4: Offline Paper Handover</span>
            </button>

            <button
              onClick={runS5}
              disabled={loading}
              className="px-2.5 py-1 bg-slate-800 hover:bg-slate-700 text-teal-300 hover:text-white border border-slate-700 rounded font-medium flex items-center gap-1 transition"
              title="Capability Stale: Blood bank or OT depleted. Acceptance blocked until reconfirmed."
            >
              <AlertTriangle className="w-3.5 h-3.5 text-orange-400" />
              <span>S5: Stale Capability Block</span>
            </button>

            <button
              onClick={runS6}
              disabled={loading}
              className="px-2.5 py-1 bg-slate-800 hover:bg-slate-700 text-red-300 hover:text-white border border-red-900/60 rounded font-medium flex items-center gap-1 transition"
              title="Tamper Test: Modifies database row. Verifier detects Merkle hash drift and flags TAMPER."
            >
              <ShieldAlert className="w-3.5 h-3.5 text-red-400" />
              <span>S6: Tamper Test</span>
            </button>

            <button
              onClick={runReset}
              disabled={loading}
              className="px-2 py-1 bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-slate-200 border border-slate-700 rounded font-medium flex items-center gap-1 transition ml-1"
              title="Reset synthetic referrals to clean demo state"
            >
              <RotateCcw className="w-3 h-3" />
              <span>Reset State</span>
            </button>

            <button
              onClick={() => setUnderTheHoodOpen(!underTheHoodOpen)}
              className="px-2 py-1 bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-slate-200 border border-slate-700 rounded font-medium flex items-center gap-1 transition"
            >
              <span>Under the Hood</span>
              {underTheHoodOpen ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
            </button>
          </div>
        </div>

        {/* Status banner */}
        {result && (
          <div
            className={`mt-2 p-2 rounded border flex items-center gap-2 text-xs ${
              result.status === 'SUCCESS'
                ? 'bg-teal-950/80 border-teal-600/60 text-teal-200'
                : result.status === 'ERROR'
                ? 'bg-red-950/80 border-red-700/60 text-red-200'
                : 'bg-slate-800 border-slate-700 text-slate-300'
            }`}
          >
            {result.status === 'SUCCESS' ? (
              <CheckCircle2 className="w-4 h-4 text-teal-400 flex-shrink-0" />
            ) : (
              <AlertTriangle className="w-4 h-4 text-amber-400 flex-shrink-0" />
            )}
            <span>{result.message}</span>
          </div>
        )}

        {/* Under the Hood Drawer */}
        {underTheHoodOpen && (
          <div className="mt-3 p-3 bg-slate-950 border border-slate-800 rounded-lg text-xs space-y-2 font-mono">
            <div className="flex items-center justify-between border-b border-slate-800 pb-1.5 text-slate-400 font-sans">
              <span className="font-bold uppercase tracking-wider text-[11px] text-teal-400">
                Protocol RHP-1 Technical Telemetry & Verification Ledger
              </span>
              <span className="text-[10px]">Strict Invariant Enforcement</span>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-2 text-[11px]">
              <div className="p-2 bg-slate-900 rounded border border-slate-800">
                <span className="text-slate-500 block">SINGLE LEASE GUARANTEE (I2)</span>
                <span className="text-teal-300">Partial unique index: one_lease WHERE status = 'ACCEPTED'</span>
              </div>
              <div className="p-2 bg-slate-900 rounded border border-slate-800">
                <span className="text-slate-500 block">DECOUPLED TRACKS (I3)</span>
                <span className="text-teal-300">Care State: hs_state | Transport State: tr_state</span>
              </div>
              <div className="p-2 bg-slate-900 rounded border border-slate-800">
                <span className="text-slate-500 block">CANONICAL HASH CHAIN (I5)</span>
                <span className="text-teal-300">RFC 8785 JCS + SHA-256 (32 zero genesis bytes)</span>
              </div>
              <div className="p-2 bg-slate-900 rounded border border-slate-800">
                <span className="text-slate-500 block">ESCALATION BOUND (I13)</span>
                <span className="text-teal-300">T_max = F * (A + D + eps) &lt;= B (DEMO_FAST: 24s &lt;= 25s)</span>
              </div>
              <div className="p-2 bg-slate-900 rounded border border-slate-800">
                <span className="text-slate-500 block">GLOBAL LOCK ORDER (I14)</span>
                <span className="text-teal-300">referral -&gt; offer -&gt; deadline -&gt; outbox</span>
              </div>
              <div className="p-2 bg-slate-900 rounded border border-slate-800">
                <span className="text-slate-500 block">COMMON-MODE INDEPENDENCE (F17)</span>
                <span className="text-teal-300">Lane B Runtime Monitor: 0 imports from api/</span>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

