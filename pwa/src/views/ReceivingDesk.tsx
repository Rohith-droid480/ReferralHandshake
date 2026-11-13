import React, { useState, useEffect } from 'react';
import {
  AlertTriangle,
  CheckCircle,
  XCircle,
  Clock,
  ShieldCheck,
  RefreshCw,
  Lock,
  Hospital,
} from 'lucide-react';
import { sseClient, ReferralSummary } from '../store/sseClient';

export const ReceivingDesk: React.FC = () => {
  const [referrals, setReferrals] = useState<ReferralSummary[]>([]);
  const [selectedRef, setSelectedRef] = useState<ReferralSummary | null>(null);

  // Capability toggles
  const [capabilities, setCapabilities] = useState<{ [cap: string]: boolean }>({
    OT: true,
    BLOOD: true,
    ANAESTHETIST: true,
    NICU: true,
  });

  // Action states
  const [pin, setPin] = useState('1234');
  const [showPinModal, setShowPinModal] = useState(false);
  const [showReconfirmModal, setShowReconfirmModal] = useState(false);
  const [showDeclineModal, setShowDeclineModal] = useState(false);
  const [declineReason, setDeclineReason] = useState('BED_UNAVAILABLE');
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [isError, setIsError] = useState(false);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const unsub = sseClient.subscribe((state) => {
      const list = Object.values(state.referrals);
      setReferrals(list);
      if (selectedRef) {
        setSelectedRef(state.referrals[selectedRef.id] || null);
      }
    });

    sseClient.connect();
    return () => unsub();
  }, [selectedRef]);

  const handleSelect = async (ref: ReferralSummary) => {
    setSelectedRef(ref);
    setStatusMessage(null);
    setIsError(false);

    // Opening card sends ACK automatically if offered
    if (ref.hs_state === 'OFFERED' || ref.hs_state === 'CREATED') {
      try {
        await fetch(`/v1/referrals/${ref.id}/ack`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Idempotency-Key': `idem-ack-${ref.id}-${Date.now()}`,
          },
        });
      } catch (e) {
        // Handled silently
      }
    }
  };

  const handleToggleCapability = async (cap: string) => {
    const nextVal = !capabilities[cap];
    setCapabilities((prev) => ({ ...prev, [cap]: nextVal }));

    if (selectedRef && nextVal) {
      try {
        await fetch(`/v1/referrals/${selectedRef.id}/resource-confirm`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Idempotency-Key': `idem-rc-${cap}-${selectedRef.id}-${Date.now()}`,
          },
          body: JSON.stringify({
            capability: cap,
            expires_in_s: 300,
          }),
        });
      } catch (e) {
        // Ignore
      }
    }
  };

  const handleAccept = async () => {
    if (!selectedRef) return;
    setLoading(true);
    setStatusMessage(null);
    setIsError(false);

    try {
      const resp = await fetch(`/v1/referrals/${selectedRef.id}/accept`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Idempotency-Key': `idem-accept-${selectedRef.id}-${Date.now()}`,
        },
        body: JSON.stringify({ pin }),
      });

      const data = await resp.json().catch(() => ({}));

      if (!resp.ok) {
        if (resp.status === 409 && data.detail?.includes('STALE_CONFIRMATION')) {
          setShowReconfirmModal(true);
          setShowPinModal(false);
          setIsError(true);
          setStatusMessage('409 STALE_CONFIRMATION_RECONFIRM_REQUIRED: Capability confirmations expired.');
        } else {
          setIsError(true);
          setStatusMessage(data.detail || `Accept failed: HTTP ${resp.status}`);
        }
      } else {
        setShowPinModal(false);
        setStatusMessage('LEASE GRANTED — Handshake Accepted! Ambulance routed.');
        setIsError(false);
      }
    } catch (err: any) {
      setIsError(true);
      setStatusMessage(err?.message || 'Network error during accept');
    } finally {
      setLoading(false);
    }
  };

  const handleReconfirmAndAccept = async () => {
    if (!selectedRef) return;
    setLoading(true);

    try {
      for (const cap of ['OT', 'BLOOD', 'ANAESTHETIST', 'NICU']) {
        await fetch(`/v1/referrals/${selectedRef.id}/resource-confirm`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Idempotency-Key': `idem-reconfirm-${cap}-${Date.now()}`,
          },
          body: JSON.stringify({ capability: cap, expires_in_s: 300 }),
        });
      }
      setShowReconfirmModal(false);
      await handleAccept();
    } catch (err: any) {
      setIsError(true);
      setStatusMessage(err?.message || 'Failed to reconfirm capabilities');
    } finally {
      setLoading(false);
    }
  };

  const handleDecline = async () => {
    if (!selectedRef) return;
    setLoading(true);

    try {
      const resp = await fetch(`/v1/referrals/${selectedRef.id}/decline`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Idempotency-Key': `idem-decline-${selectedRef.id}-${Date.now()}`,
        },
        body: JSON.stringify({
          reason: declineReason,
          redirect_facility_id: null,
        }),
      });

      if (resp.ok) {
        setShowDeclineModal(false);
        setStatusMessage('Offer declined. Referral escalated to next tier.');
        setIsError(false);
      } else {
        const d = await resp.json().catch(() => ({}));
        setIsError(true);
        setStatusMessage(d.detail || 'Decline failed');
      }
    } catch (e: any) {
      setIsError(true);
      setStatusMessage(e?.message || 'Error declining');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-6xl mx-auto p-4 sm:p-6 grid grid-cols-1 lg:grid-cols-3 gap-6">
      {/* Left: Anti-Goodhart Priority Queue (No countdown clocks!) */}
      <div className="bg-slate-800 rounded-xl border border-slate-700 p-4 shadow-lg lg:col-span-1">
        <div className="flex items-center justify-between pb-3 border-b border-slate-700 mb-3">
          <div className="flex items-center gap-2">
            <Hospital className="w-5 h-5 text-indigo-400" />
            <h2 className="font-bold text-white text-base">Receiving Desk Queue</h2>
          </div>
          <span className="text-[11px] font-mono px-2 py-0.5 bg-slate-900 text-slate-400 rounded">
            Anti-Goodhart (No Clocks)
          </span>
        </div>

        {referrals.length === 0 ? (
          <div className="text-center py-12 text-slate-500 text-sm">
            <Clock className="w-8 h-8 mx-auto mb-2 opacity-50" />
            No active incoming referrals
          </div>
        ) : (
          <div className="space-y-2">
            {referrals.map((r) => (
              <div
                key={r.id}
                onClick={() => handleSelect(r)}
                className={`p-3 rounded-lg border cursor-pointer transition ${
                  selectedRef?.id === r.id
                    ? 'bg-indigo-950/60 border-indigo-500'
                    : 'bg-slate-900/60 border-slate-700/70 hover:border-slate-500'
                }`}
              >
                <div className="flex items-center justify-between mb-1">
                  <span className="font-bold text-white text-sm">
                    {r.need_class || 'OBSTETRIC_EMERGENCY'}
                  </span>
                  <span
                    className={`text-[10px] font-bold px-2 py-0.5 rounded ${
                      r.hs_state === 'ACCEPTED'
                        ? 'bg-emerald-900/60 text-emerald-300 border border-emerald-700'
                        : r.hs_state === 'OFFERED'
                        ? 'bg-amber-900/60 text-amber-300 border border-amber-700 animate-pulse'
                        : 'bg-slate-800 text-slate-300'
                    }`}
                  >
                    {r.hs_state}
                  </span>
                </div>
                <div className="flex items-center justify-between text-xs text-slate-400">
                  <span>ID: {r.id.slice(0, 8)}...</span>
                  <span>{r.mode}</span>
                </div>
                {r.mgso4_status === 'UNKNOWN' && (
                  <span className="inline-block mt-1 text-[10px] font-bold text-red-400">
                    ⚠ MgSO4 UNKNOWN
                  </span>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Center & Right: Selected Referral & Handshake Controls */}
      <div className="bg-slate-800 rounded-xl border border-slate-700 p-6 shadow-lg lg:col-span-2 space-y-5">
        {selectedRef ? (
          <>
            {/* Top Info */}
            <div className="flex justify-between items-start border-b border-slate-700 pb-4">
              <div>
                <span className="text-xs font-mono text-indigo-400 uppercase tracking-wider block">
                  Incoming Handshake Offer
                </span>
                <h1 className="text-2xl font-black text-white">
                  {selectedRef.need_class || 'OBSTETRIC EMERGENCY'}
                </h1>
                <p className="text-xs text-slate-400 mt-0.5">
                  Referral ID: <span className="font-mono text-slate-300">{selectedRef.id}</span>
                </p>
              </div>
              <div className="text-right">
                <span className="text-xs text-slate-400 block">Current Status</span>
                <span className="text-sm font-bold text-emerald-400 font-mono">
                  {selectedRef.hs_state}
                </span>
              </div>
            </div>

            {/* D1 / K1: High-Contrast Red Banner for UNKNOWN MgSO4 */}
            {selectedRef.mgso4_status === 'UNKNOWN' && (
              <div className="p-3 bg-red-950/80 border-2 border-red-500 rounded-lg text-red-200 text-xs sm:text-sm font-black flex items-center gap-3 animate-pulse">
                <AlertTriangle className="w-6 h-6 flex-shrink-0 text-red-400" />
                <span>
                  PRE-REFERRAL MgSO4 DOSE UNKNOWN — VERIFY WITH PATIENT / ESCORT BEFORE DOSING
                </span>
              </div>
            )}

            {/* Status Messages */}
            {statusMessage && (
              <div
                className={`p-3 rounded-lg text-xs font-bold flex items-center gap-2 ${
                  isError
                    ? 'bg-red-900/40 border border-red-500/50 text-red-200'
                    : 'bg-emerald-900/40 border border-emerald-500/50 text-emerald-200'
                }`}
              >
                {isError ? <AlertTriangle className="w-4 h-4" /> : <CheckCircle className="w-4 h-4" />}
                <span>{statusMessage}</span>
              </div>
            )}

            {/* Capability Checklist (RESOURCE_CONFIRM) */}
            <div className="p-4 bg-slate-900/70 rounded-lg border border-slate-700">
              <h3 className="text-xs font-bold text-slate-300 uppercase tracking-wider mb-2 flex items-center gap-2">
                <ShieldCheck className="w-4 h-4 text-emerald-400" />
                Live Resource Confirmations (TTL Enforced)
              </h3>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                {['OT', 'BLOOD', 'ANAESTHETIST', 'NICU'].map((cap) => (
                  <button
                    key={cap}
                    type="button"
                    onClick={() => handleToggleCapability(cap)}
                    className={`py-2 px-3 rounded-lg text-xs font-bold border flex items-center justify-between transition ${
                      capabilities[cap]
                        ? 'bg-emerald-950/50 border-emerald-500 text-emerald-300'
                        : 'bg-slate-800 border-slate-700 text-slate-400'
                    }`}
                  >
                    <span>{cap}</span>
                    <span>{capabilities[cap] ? '✓' : '✗'}</span>
                  </button>
                ))}
              </div>
            </div>

            {/* Actions: Accept, Counter, Decline */}
            <div className="flex flex-wrap gap-3 pt-2">
              <button
                type="button"
                onClick={() => setShowPinModal(true)}
                disabled={loading || selectedRef.hs_state === 'ACCEPTED'}
                className="flex-1 py-3 px-4 bg-emerald-600 hover:bg-emerald-500 disabled:bg-slate-700 text-white font-bold rounded-lg shadow flex items-center justify-center gap-2 transition"
              >
                <Lock className="w-4 h-4" />
                Accept & Grant Lease
              </button>

              <button
                type="button"
                onClick={() => setShowDeclineModal(true)}
                disabled={loading || selectedRef.hs_state === 'ACCEPTED'}
                className="py-3 px-4 bg-red-700 hover:bg-red-600 disabled:bg-slate-700 text-white font-bold rounded-lg transition"
              >
                Decline
              </button>
            </div>
          </>
        ) : (
          <div className="text-center py-20 text-slate-400">
            <Hospital className="w-12 h-12 mx-auto mb-3 opacity-40" />
            <p className="text-base font-semibold">Select an incoming referral from the priority queue</p>
            <p className="text-xs text-slate-500 mt-1">
              Opening a referral initiates acknowledgment without gaming timers.
            </p>
          </div>
        )}
      </div>

      {/* PIN Verification Modal */}
      {showPinModal && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="bg-slate-800 rounded-xl border border-slate-700 p-6 max-w-sm w-full space-y-4">
            <h3 className="text-lg font-bold text-white flex items-center gap-2">
              <Lock className="w-5 h-5 text-indigo-400" />
              Duty PIN Verification
            </h3>
            <p className="text-xs text-slate-400">
              Enter your 4-digit clinician duty PIN to bind legal acceptance.
            </p>
            <input
              type="password"
              maxLength={6}
              value={pin}
              onChange={(e) => setPin(e.target.value)}
              className="w-full text-center text-2xl font-mono tracking-widest py-2 bg-slate-900 border border-slate-700 rounded-lg text-white"
            />
            <div className="flex gap-2">
              <button
                onClick={() => setShowPinModal(false)}
                className="flex-1 py-2 bg-slate-700 text-slate-300 font-bold rounded-lg"
              >
                Cancel
              </button>
              <button
                onClick={handleAccept}
                disabled={loading}
                className="flex-1 py-2 bg-emerald-600 hover:bg-emerald-500 text-white font-bold rounded-lg"
              >
                {loading ? 'Verifying...' : 'Confirm'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Stale Reconfirm Modal (Invariant I15) */}
      {showReconfirmModal && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="bg-slate-800 rounded-xl border-2 border-amber-500 p-6 max-w-md w-full space-y-4 shadow-2xl">
            <div className="flex items-center gap-3 text-amber-400">
              <AlertTriangle className="w-8 h-8" />
              <div>
                <h3 className="text-lg font-black text-white">Capabilities Expired</h3>
                <p className="text-xs text-amber-300">Invariant I15 Live Reconfirm Required</p>
              </div>
            </div>
            <p className="text-xs text-slate-300 leading-relaxed">
              OT, Blood, or Specialist confirmation TTL expired while the referral was open.
              Re-confirm live availability to grant the lease safely.
            </p>
            <div className="flex gap-3">
              <button
                onClick={() => setShowReconfirmModal(false)}
                className="flex-1 py-2 bg-slate-700 text-slate-300 font-bold rounded-lg text-xs"
              >
                Cancel
              </button>
              <button
                onClick={handleReconfirmAndAccept}
                disabled={loading}
                className="flex-1 py-2.5 bg-amber-600 hover:bg-amber-500 text-black font-extrabold rounded-lg text-xs flex items-center justify-center gap-1.5 transition"
              >
                <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
                Reconfirm Live Now
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Decline Reason Modal */}
      {showDeclineModal && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="bg-slate-800 rounded-xl border border-slate-700 p-6 max-w-md w-full space-y-4">
            <h3 className="text-lg font-bold text-white flex items-center gap-2">
              <XCircle className="w-5 h-5 text-red-400" />
              Decline Referral
            </h3>
            <p className="text-xs text-slate-400">
              Select structured reason for decline. Referral will advance immediately to the next tier.
            </p>
            <select
              value={declineReason}
              onChange={(e) => setDeclineReason(e.target.value)}
              className="w-full px-3 py-2 bg-slate-900 border border-slate-700 rounded-lg text-white text-sm"
            >
              <option value="BED_UNAVAILABLE">Bed Unavailable</option>
              <option value="OT_OCCUPIED">OT Currently Occupied</option>
              <option value="SPECIALIST_UNAVAILABLE">Specialist / Anaesthetist Unavailable</option>
              <option value="EQUIPMENT_FAILURE">Critical Equipment Failure</option>
            </select>
            <div className="flex gap-2">
              <button
                onClick={() => setShowDeclineModal(false)}
                className="flex-1 py-2 bg-slate-700 text-slate-300 font-bold rounded-lg"
              >
                Cancel
              </button>
              <button
                onClick={handleDecline}
                disabled={loading}
                className="flex-1 py-2 bg-red-600 hover:bg-red-500 text-white font-bold rounded-lg"
              >
                {loading ? 'Declining...' : 'Confirm Decline'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

