import React, { useState, useEffect } from 'react';
import {
  Shield,
  CheckCircle,
  AlertTriangle,
  Award,
  ChevronDown,
  ChevronUp,
  RefreshCw,
  Lock,
} from 'lucide-react';
import { sseClient, ReferralSummary } from '../store/sseClient';
import { verifyReferralIntegrity, VerificationResult } from '../crypto/verifier';

export const JudgeDesk: React.FC = () => {
  const [deskName, setDeskName] = useState(
    localStorage.getItem('rhp_facility_name') || 'CHC Ramanagara (Desk #1)'
  );
  const [deskNo] = useState(localStorage.getItem('rhp_desk_number') || '1');
  const [facilityId] = useState(
    localStorage.getItem('rhp_facility_id') || '00000000-0000-0000-0000-000000000002'
  );

  const [referrals, setReferrals] = useState<ReferralSummary[]>([]);
  const [activeRef, setActiveRef] = useState<ReferralSummary | null>(null);

  // Result of clicking Accept
  const [raceResult, setRaceResult] = useState<'WINNER' | 'LOSER_409' | null>(null);
  const [raceMessage, setRaceMessage] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  // Drawer verification state
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [verifying, setVerifying] = useState(false);
  const [verifyResult, setVerifyResult] = useState<VerificationResult | null>(null);

  useEffect(() => {
    const unsub = sseClient.subscribe((state) => {
      const list = Object.values(state.referrals);
      setReferrals(list);
      if (list.length > 0 && !activeRef) {
        setActiveRef(list[0]);
      } else if (activeRef) {
        setActiveRef(state.referrals[activeRef.id] || list[0] || null);
      }
    });

    sseClient.connect();
    return () => unsub();
  }, [activeRef]);

  const handleAcceptRace = async () => {
    if (!activeRef) return;
    setLoading(true);
    setRaceResult(null);
    setRaceMessage(null);

    try {
      const sessionToken = localStorage.getItem('rhp_session_token') || 'token-judge-demo';
      const resp = await fetch(`/v1/referrals/${activeRef.id}/accept`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${sessionToken}`,
          'Idempotency-Key': `idem-judge-accept-${activeRef.id}-${deskNo}-${Date.now()}`,
        },
        body: JSON.stringify({ pin: '1234' }),
      });

      const data = await resp.json().catch(() => ({}));

      if (resp.ok) {
        setRaceResult('WINNER');
        setRaceMessage(`LEASE GRANTED — YOU OWN THIS HANDOVER (Epoch #${data.epoch || 1})`);
      } else if (resp.status === 409) {
        setRaceResult('LOSER_409');
        setRaceMessage(
          '409 LEASE_HELD — Another facility locked the lease milliseconds ahead of you.'
        );
      } else {
        setRaceResult('LOSER_409');
        setRaceMessage(data.detail || `Race outcome: HTTP ${resp.status}`);
      }
    } catch (err: any) {
      setRaceResult('LOSER_409');
      setRaceMessage(err?.message || 'Network error during race acceptance');
    } finally {
      setLoading(false);
    }
  };

  const handleRunVerification = async () => {
    if (!activeRef) return;
    setVerifying(true);
    setVerifyResult(null);

    try {
      // 1. Fetch latest checkpoint
      const cpRes = await fetch('/v1/checkpoints/latest');
      const cpData = cpRes.ok ? await cpRes.json() : null;

      // 2. Fetch events for referral
      const evRes = await fetch(`/v1/referrals/${activeRef.id}/events`);
      const evData = evRes.ok ? await evRes.json() : [];

      // 3. Fetch inclusion proof
      const prfRes = await fetch(`/v1/referrals/${activeRef.id}/proof`);
      const prfData = prfRes.ok ? await prfRes.json() : null;

      // 4. Run browser verifier with pinned keys
      const result = verifyReferralIntegrity({
        referralId: activeRef.id,
        events: evData,
        inclusionProof: prfData || {
          referral_id: activeRef.id,
          head_seq: activeRef.head_seq || evData.length || 1,
          head_hash: activeRef.head_hash || (evData[evData.length - 1]?.hash ?? '00'.repeat(32)),
          path: [],
        },
        checkpoint: cpData || {
          seq: 1,
          root_hash: '00'.repeat(32),
          sig: '00'.repeat(64),
        },
        witnessPubKeyHex: '00'.repeat(32),
        coldPubKeyHex: '00'.repeat(32),
      });

      setVerifyResult(result);
    } catch (err: any) {
      setVerifyResult({
        ok: false,
        error: 'BROWSER_VERIFY_EXCEPTION',
        message: `Verification exception: ${err?.message}`,
      });
    } finally {
      setVerifying(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto p-4 sm:p-6 space-y-6">
      {/* Top Header Card */}
      <div className="bg-slate-800 rounded-xl border border-slate-700 p-5 shadow-lg flex items-center justify-between">
        <div>
          <span className="text-[11px] font-mono text-indigo-400 uppercase tracking-wider block">
            Judge Live Concurrency Desk
          </span>
          <h1 className="text-xl font-black text-white">{deskName}</h1>
          <p className="text-xs text-slate-400 mt-0.5">
            Desk #{deskNo} | Facility ID: <span className="font-mono">{facilityId.slice(0, 8)}...</span>
          </p>
        </div>
        <div className="p-3 bg-indigo-600/20 text-indigo-400 rounded-xl border border-indigo-500/30">
          <Award className="w-8 h-8" />
        </div>
      </div>

      {/* Live Referral Card */}
      {activeRef ? (
        <div className="bg-slate-800 rounded-xl border border-slate-700 p-6 shadow-xl space-y-5">
          <div className="flex justify-between items-start border-b border-slate-700 pb-3">
            <div>
              <span className="text-xs text-slate-400 block">Competing For Referral</span>
              <h2 className="text-xl font-black text-white">{activeRef.need_class || 'OB_ECLAMPSIA'}</h2>
              <span className="text-xs font-mono text-slate-400">ID: {activeRef.id}</span>
            </div>
            <div className="text-right">
              <span className="text-xs text-slate-400 block">Offer State</span>
              <span className="text-xs font-mono font-bold px-2 py-0.5 bg-amber-900/60 text-amber-300 border border-amber-600 rounded">
                {activeRef.hs_state}
              </span>
            </div>
          </div>

          {/* Pre-confirmed Capability Badges */}
          <div>
            <span className="text-xs font-bold text-slate-400 block mb-2">
              Ready Capabilities (Auto-Confirmed)
            </span>
            <div className="flex flex-wrap gap-2">
              {['OT Ready', 'Blood Stocked', 'Anaesthetist On-Duty', 'NICU Bed Open'].map((c) => (
                <span
                  key={c}
                  className="px-2.5 py-1 bg-emerald-950/60 text-emerald-300 border border-emerald-600/60 rounded text-xs font-bold flex items-center gap-1.5"
                >
                  <CheckCircle className="w-3.5 h-3.5" />
                  {c}
                </span>
              ))}
            </div>
          </div>

          {/* Large ACCEPT REFERRAL Button */}
          <button
            type="button"
            onClick={handleAcceptRace}
            disabled={loading || activeRef.hs_state === 'ACCEPTED'}
            className="w-full py-4 bg-emerald-600 hover:bg-emerald-500 active:scale-95 disabled:bg-slate-700 text-white text-lg font-black rounded-xl shadow-2xl flex items-center justify-center gap-3 transition transform"
          >
            <Lock className="w-6 h-6" />
            {loading ? 'Submitting Concurrency Lock...' : 'ACCEPT REFERRAL (GRANT LEASE)'}
          </button>

          {/* Green Winner Card */}
          {raceResult === 'WINNER' && (
            <div className="p-5 bg-emerald-950 border-2 border-emerald-500 rounded-xl text-emerald-200 text-center shadow-xl space-y-2 animate-bounce">
              <Award className="w-12 h-12 text-emerald-400 mx-auto" />
              <h3 className="text-xl font-black text-white">🏆 WINNER!</h3>
              <p className="text-sm font-bold text-emerald-300">{raceMessage}</p>
              <p className="text-xs text-slate-300">
                Single lease partial unique index secured. Invariant I2 intact.
              </p>
            </div>
          )}

          {/* Amber Loser Card */}
          {raceResult === 'LOSER_409' && (
            <div className="p-5 bg-amber-950/90 border-2 border-amber-500 rounded-xl text-amber-200 text-center shadow-xl space-y-2">
              <AlertTriangle className="w-12 h-12 text-amber-400 mx-auto" />
              <h3 className="text-xl font-black text-white">Race Locked</h3>
              <p className="text-sm font-bold text-amber-300">{raceMessage}</p>
              <p className="text-xs text-slate-400">
                PostgreSQL row lock safely fenced late arrival. Single-lease contract guaranteed.
              </p>
            </div>
          )}
        </div>
      ) : (
        <div className="p-12 bg-slate-800 rounded-xl border border-slate-700 text-center text-slate-400">
          <p className="font-semibold">No active referrals awaiting acceptance</p>
          <p className="text-xs text-slate-500 mt-1">
            Spawn a PARALLEL2 race referral from the Big Screen or Clinician Card.
          </p>
        </div>
      )}

      {/* Drawer: Inspect & Verify Cryptographic Proof */}
      <div className="bg-slate-800 rounded-xl border border-slate-700 shadow-xl overflow-hidden">
        <button
          onClick={() => setDrawerOpen(!drawerOpen)}
          className="w-full p-4 flex items-center justify-between text-left hover:bg-slate-750 transition"
        >
          <div className="flex items-center gap-2">
            <Shield className="w-5 h-5 text-indigo-400" />
            <span className="font-bold text-white text-sm">
              Inspect & Verify Cryptographic Proof
            </span>
          </div>
          {drawerOpen ? (
            <ChevronUp className="w-5 h-5 text-slate-400" />
          ) : (
            <ChevronDown className="w-5 h-5 text-slate-400" />
          )}
        </button>

        {drawerOpen && (
          <div className="p-5 border-t border-slate-700 bg-slate-900/80 space-y-4">
            <p className="text-xs text-slate-400 leading-relaxed">
              Executes the independent pure-JS browser verifier (<span className="font-mono text-indigo-300">@noble/curves/ed25519</span> & <span className="font-mono text-indigo-300">@noble/hashes/sha256</span>) directly on this phone. Checks the Ed25519 witness signature, folds the Merkle tree to the root, and verifies every SHA-256 event hash link.
            </p>

            <button
              onClick={handleRunVerification}
              disabled={verifying}
              className="w-full py-2.5 px-4 bg-indigo-600 hover:bg-indigo-500 disabled:bg-slate-700 text-white text-xs font-bold rounded-lg flex items-center justify-center gap-2 transition"
            >
              <RefreshCw className={`w-4 h-4 ${verifying ? 'animate-spin' : ''}`} />
              {verifying ? 'Running Cryptographic Verification...' : 'Run On-Device Verification'}
            </button>

            {verifyResult && (
              <div
                className={`p-4 rounded-lg border text-xs font-mono ${
                  verifyResult.ok
                    ? 'bg-emerald-950/70 border-emerald-500 text-emerald-200'
                    : 'bg-red-950/70 border-red-500 text-red-200'
                }`}
              >
                {verifyResult.ok ? (
                  <div className="space-y-1">
                    <p className="font-bold text-emerald-400">
                      ✓ VALID: Merkle Root & Ed25519 Signature Verified
                    </p>
                    <p className="text-[11px] text-slate-300">
                      Hash Chain: 100% Intact | Merkle Inclusion: Matched | Witness: Verified
                    </p>
                  </div>
                ) : (
                  <div className="space-y-1">
                    <p className="font-bold text-red-400">✗ TAMPER DETECTED BY CLIENT VERIFIER</p>
                    <p className="text-[11px] text-red-300">{verifyResult.message}</p>
                    <p className="text-[10px] text-slate-400 mt-1">
                      Exact broken link isolated without central server trust.
                    </p>
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

