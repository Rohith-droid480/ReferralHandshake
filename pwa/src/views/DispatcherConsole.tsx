import React, { useState, useEffect } from 'react';
import {
  PhoneCall,
  Sliders,
  CheckCircle,
  AlertTriangle,
  History,
  ShieldAlert,
  ArrowRight,
  UserCheck,
} from 'lucide-react';
import { sseClient, ReferralSummary } from '../store/sseClient';

export const DispatcherConsole: React.FC = () => {
  const [escalatedQueue, setEscalatedQueue] = useState<ReferralSummary[]>([]);
  const [selectedRef, setSelectedRef] = useState<ReferralSummary | null>(null);

  // Proxy Action inputs
  const [proxyAction, setProxyAction] = useState('DISPATCHER_ASSIGN');
  const [targetFacilityId, setTargetFacilityId] = useState(
    '00000000-0000-0000-0000-000000000003'
  );
  const [proxyForRosterId, setProxyForRosterId] = useState(
    '00000000-0000-0000-0000-000000000020'
  );
  const [proxyReason, setProxyReason] = useState('PHONE_CONFIRMED_BY_CONSULTANT');
  const [pin, setPin] = useState('1234');
  const [loading, setLoading] = useState(false);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);

  // Time-Scrubber Replay
  const [events, setEvents] = useState<any[]>([]);
  const [scrubSeq, setScrubSeq] = useState<number>(1);
  const [replayedState, setReplayedState] = useState<{
    seq: number;
    hs_state: string;
    tr_state: string;
    lease_facility_id: string | null;
    eventType: string;
  }>({
    seq: 1,
    hs_state: 'CREATED',
    tr_state: 'REQUESTED',
    lease_facility_id: null,
    eventType: 'CREATED',
  });

  // 1. Initial Fetch and Subscribe to SSE
  useEffect(() => {
    fetch('/v1/referrals')
      .then((r) => (r.ok ? r.json() : []))
      .then((list) => {
        if (Array.isArray(list) && list.length > 0) {
          const esc = list.filter(
            (r) =>
              r.hs_state === 'ESCALATED_TO_DISPATCHER' ||
              r.hs_state === 'OFFERED' ||
              r.tr_state === 'ARRIVED'
          );
          const queue = esc.length > 0 ? esc : list;
          setEscalatedQueue(queue);
          const prio = queue.find((r) => r.hs_state === 'ESCALATED_TO_DISPATCHER') || queue[0];
          setSelectedRef(prio);
        }
      })
      .catch(() => {});

    const unsub = sseClient.subscribe((state) => {
      const list = Object.values(state.referrals);
      // Escalated or attention queue
      const esc = list.filter(
        (r) =>
          r.hs_state === 'ESCALATED_TO_DISPATCHER' ||
          r.hs_state === 'OFFERED' ||
          r.tr_state === 'ARRIVED'
      );
      setEscalatedQueue(esc.length > 0 ? esc : list);
      if (selectedRef) {
        setSelectedRef(state.referrals[selectedRef.id] || null);
      } else if (list.length > 0) {
        const prio = list.find((r) => r.hs_state === 'ESCALATED_TO_DISPATCHER') || list[0];
        setSelectedRef(prio);
      }
    });

    sseClient.connect();
    return () => unsub();
  }, []);

  // 2. Fetch Events for selected referral
  useEffect(() => {
    if (!selectedRef) return;

    fetch(`/v1/referrals/${selectedRef.id}/events`)
      .then((r) => (r.ok ? r.json() : []))
      .then((evs) => {
        setEvents(evs);
        setScrubSeq(evs.length || 1);
        if (evs.length > 0) {
          foldEventsUpTo(evs, evs.length);
        }
      })
      .catch(() => {});
  }, [selectedRef?.id]);

  // Client-side event fold for scrubber
  const foldEventsUpTo = (allEvents: any[], targetSeq: number) => {
    let hs = 'CREATED';
    let tr = 'REQUESTED';
    let lease: string | null = null;
    let lastType = 'CREATED';

    for (const ev of allEvents) {
      if (ev.seq > targetSeq) break;
      lastType = ev.type;

      if (ev.type === 'OFFER_CREATED') hs = 'OFFERED';
      if (ev.type === 'OFFER_ACK') hs = 'ACKED';
      if (ev.type === 'OFFER_ACCEPTED' || ev.type === 'DISPATCHER_ASSIGN') {
        hs = 'ACCEPTED';
        lease = ev.detail?.facility_id || ev.actor_facility_id;
      }
      if (ev.type === 'TIMEOUT' && ev.detail?.kind === 'ACK') hs = 'OFFERED';
      if (ev.type === 'ESCALATED_TO_DISPATCHER') hs = 'ESCALATED_TO_DISPATCHER';
      if (ev.type === 'CANCEL') hs = 'CANCELLED';
      if (ev.type === 'CLOSE') hs = 'CLOSED';

      if (ev.type === 'TR_UPDATE') {
        tr = ev.detail?.tr_state || tr;
      }
      if (ev.type === 'TR_DESTINATION_CHANGE' && ev.detail?.accepted) {
        lease = ev.detail.target_facility_id;
      }
    }

    setReplayedState({
      seq: targetSeq,
      hs_state: hs,
      tr_state: tr,
      lease_facility_id: lease,
      eventType: lastType,
    });
  };

  const handleSliderChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = Number(e.target.value);
    setScrubSeq(val);
    foldEventsUpTo(events, val);
  };

  // 3. Submit Proxy Action
  const handleExecuteProxy = async () => {
    if (!selectedRef) return;
    setLoading(true);
    setStatusMessage(null);

    const body: any = {
      type: proxyAction,
      proxy: true,
      proxy_for: proxyForRosterId,
      reason: proxyReason,
      pin,
    };

    if (proxyAction === 'DISPATCHER_ASSIGN') {
      body.target_facility_id = targetFacilityId;
    }

    let endpoint = `/v1/referrals/${selectedRef.id}/dispatcher-assign`;
    if (proxyAction === 'ACCEPT') {
      endpoint = `/v1/referrals/${selectedRef.id}/accept`;
    } else if (proxyAction === 'DECLINE') {
      endpoint = `/v1/referrals/${selectedRef.id}/decline`;
    }

    try {
      const resp = await fetch(endpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Idempotency-Key': `idem-proxy-${selectedRef.id}-${Date.now()}`,
        },
        body: JSON.stringify(body),
      });

      const data = await resp.json().catch(() => ({}));

      if (resp.ok) {
        setStatusMessage(
          `Proxy Action Executed: ${proxyAction} committed on behalf of role with audit tag.`
        );
      } else {
        setStatusMessage(`Proxy failed (${resp.status}): ${data.detail || 'Rejected'}`);
      }
    } catch (e: any) {
      setStatusMessage(`Network error during proxy execution: ${e?.message}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-6xl mx-auto p-4 sm:p-6 space-y-6">
      {/* Top Header */}
      <div className="bg-slate-800 rounded-xl border border-slate-700 p-5 shadow-lg flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-3 bg-indigo-600/20 text-indigo-400 rounded-xl border border-indigo-500/30">
            <PhoneCall className="w-7 h-7" />
          </div>
          <div>
            <span className="text-[10px] font-mono text-indigo-400 uppercase tracking-wider block">
              Central Emergency Command
            </span>
            <h1 className="text-xl font-black text-white">108 Dispatcher Console & Proxy Hub</h1>
            <p className="text-xs text-slate-400">
              Deterministic Time-Scrubber Replay & Assisted Intake
            </p>
          </div>
        </div>
        <span className="text-xs font-mono font-bold px-3 py-1 bg-indigo-950/60 text-indigo-300 border border-indigo-500/40 rounded-lg">
          Role: DISPATCHER (Tier T1)
        </span>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left: Escalated Action Queue */}
        <div className="bg-slate-800 rounded-xl border border-slate-700 p-4 shadow-lg lg:col-span-1 space-y-3">
          <h2 className="text-xs font-black uppercase tracking-wider text-slate-300 flex items-center justify-between border-b border-slate-700 pb-2">
            <span className="flex items-center gap-2">
              <ShieldAlert className="w-4 h-4 text-amber-400" />
              Action Queue
            </span>
            <span className="text-[10px] font-mono text-amber-400">Attention Required</span>
          </h2>

          <div className="space-y-2 max-h-[500px] overflow-y-auto">
            {escalatedQueue.length === 0 ? (
              <div className="p-4 bg-slate-900/60 rounded-lg border border-slate-750 text-center space-y-2">
                <p className="text-xs text-slate-400">All referrals progressing normally within SLA.</p>
                <button
                  type="button"
                  onClick={async () => {
                    await fetch('/v1/arena/spawn-silence-ladder', { method: 'POST' });
                    const res = await fetch('/v1/referrals');
                    if (res.ok) {
                      const list = await res.json();
                      setEscalatedQueue(list);
                      setSelectedRef(list[0]);
                    }
                  }}
                  className="py-1.5 px-3 bg-indigo-600/80 hover:bg-indigo-600 text-white rounded text-xs font-bold transition"
                >
                  Spawn Escalated Case
                </button>
              </div>
            ) : (
              escalatedQueue.map((r) => (
                <div
                  key={r.id}
                  onClick={() => setSelectedRef(r)}
                  className={`p-3 rounded-lg border cursor-pointer transition ${
                    selectedRef?.id === r.id
                      ? 'bg-indigo-950/70 border-indigo-500'
                      : 'bg-slate-900/60 border-slate-700 hover:border-slate-500'
                  }`}
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="font-bold text-white text-xs">{r.need_class || 'OB_ECLAMPSIA'}</span>
                    <span
                      className={`text-[9px] font-bold px-1.5 py-0.5 rounded ${
                        r.hs_state === 'ESCALATED_TO_DISPATCHER'
                          ? 'bg-red-900/70 text-red-300 border border-red-500 animate-pulse'
                          : 'bg-slate-800 text-slate-300'
                      }`}
                    >
                      {r.hs_state}
                    </span>
                  </div>
                  <div className="text-[10px] font-mono text-slate-400 truncate">ID: {r.id}</div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Center & Right: Proxy Panel & Time-Scrubber Replay */}
        <div className="lg:col-span-2 space-y-6">
          {selectedRef && (
            <>
              {/* Proxy Action Panel */}
              <div className="bg-slate-800 rounded-xl border border-slate-700 p-5 shadow-lg space-y-4">
                <div className="flex items-center justify-between border-b border-slate-700 pb-3">
                  <h3 className="text-sm font-bold text-white flex items-center gap-2">
                    <UserCheck className="w-4 h-4 text-emerald-400" />
                    Assisted Proxy Action Panel (Closure F6 / §4.6)
                  </h3>
                  <span className="text-[10px] text-slate-400 font-mono">
                    Audit Tag: proxy = True
                  </span>
                </div>

                {statusMessage && (
                  <div className="p-3 bg-indigo-950/80 border border-indigo-500/50 rounded-lg text-indigo-200 text-xs font-bold flex items-center gap-2">
                    <CheckCircle className="w-4 h-4 text-indigo-400" />
                    <span>{statusMessage}</span>
                  </div>
                )}

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
                  <div>
                    <label className="text-slate-400 block mb-1">Proxy Action Type</label>
                    <select
                      value={proxyAction}
                      onChange={(e) => setProxyAction(e.target.value)}
                      className="w-full px-2.5 py-1.5 bg-slate-900 border border-slate-700 rounded text-white"
                    >
                      <option value="DISPATCHER_ASSIGN">DISPATCHER_ASSIGN (Emergency Override)</option>
                      <option value="ACCEPT">ACCEPT (Phone-Assisted)</option>
                      <option value="DECLINE">DECLINE (Phone-Assisted)</option>
                    </select>
                  </div>

                  <div>
                    <label className="text-slate-400 block mb-1">Target Facility Assignment</label>
                    <select
                      value={targetFacilityId}
                      onChange={(e) => setTargetFacilityId(e.target.value)}
                      className="w-full px-2.5 py-1.5 bg-slate-900 border border-slate-700 rounded text-white"
                    >
                      <option value="00000000-0000-0000-0000-000000000002">CHC Ramanagara (002)</option>
                      <option value="00000000-0000-0000-0000-000000000003">DH Mandya (003)</option>
                    </select>
                  </div>

                  <div>
                    <label className="text-slate-400 block mb-1">Acting Roster Slot (Proxy For)</label>
                    <input
                      type="text"
                      value={proxyForRosterId}
                      onChange={(e) => setProxyForRosterId(e.target.value)}
                      className="w-full px-2.5 py-1.5 bg-slate-900 border border-slate-700 rounded text-white font-mono"
                    />
                  </div>

                  <div>
                    <label className="text-slate-400 block mb-1">Structured Telephony Reason</label>
                    <input
                      type="text"
                      value={proxyReason}
                      onChange={(e) => setProxyReason(e.target.value)}
                      className="w-full px-2.5 py-1.5 bg-slate-900 border border-slate-700 rounded text-white"
                    />
                  </div>
                </div>

                <button
                  type="button"
                  onClick={handleExecuteProxy}
                  disabled={loading}
                  className="w-full py-2.5 bg-indigo-600 hover:bg-indigo-500 disabled:bg-slate-700 text-white font-bold rounded-lg text-xs flex items-center justify-center gap-2 transition"
                >
                  <PhoneCall className="w-4 h-4" />
                  {loading ? 'Executing Proxy Mutation...' : 'Execute Proxy Command'}
                </button>
              </div>

              {/* Deterministic Time-Scrubber Replay */}
              <div className="bg-slate-800 rounded-xl border border-slate-700 p-5 shadow-lg space-y-4">
                <div className="flex items-center justify-between border-b border-slate-700 pb-3">
                  <h3 className="text-sm font-bold text-white flex items-center gap-2">
                    <History className="w-4 h-4 text-indigo-400" />
                    Deterministic Time-Scrubber Replay
                  </h3>
                  <span className="text-[10px] text-slate-400 font-mono">
                    Sequence: #{scrubSeq} of {events.length || 1}
                  </span>
                </div>

                {/* Slider */}
                <div className="space-y-1">
                  <div className="flex justify-between text-[11px] font-mono text-slate-400">
                    <span>seq=1</span>
                    <span>seq={events.length || 1}</span>
                  </div>
                  <input
                    type="range"
                    min={1}
                    max={events.length || 1}
                    value={scrubSeq}
                    onChange={handleSliderChange}
                    className="w-full accent-indigo-500"
                  />
                </div>

                {/* Replayed State View */}
                <div className="p-4 bg-slate-900/90 rounded-lg border border-slate-700/80 grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs font-mono">
                  <div>
                    <span className="text-slate-500 block text-[10px]">EVENT AT SEQ</span>
                    <span className="font-bold text-indigo-300">{replayedState.eventType}</span>
                  </div>
                  <div>
                    <span className="text-slate-500 block text-[10px]">HS_STATE</span>
                    <span className="font-bold text-emerald-400">{replayedState.hs_state}</span>
                  </div>
                  <div>
                    <span className="text-slate-500 block text-[10px]">TR_STATE</span>
                    <span className="font-bold text-amber-400">{replayedState.tr_state}</span>
                  </div>
                  <div>
                    <span className="text-slate-500 block text-[10px]">LEASE HOLDER</span>
                    <span className="font-bold text-white truncate">
                      {replayedState.lease_facility_id ? replayedState.lease_facility_id.slice(0, 8) : 'None'}
                    </span>
                  </div>
                </div>
              </div>
            </>
          )}

          {!selectedRef && (
            <div className="bg-slate-800 rounded-xl border border-slate-700 p-8 shadow-lg text-center space-y-3">
              <ShieldAlert className="w-10 h-10 text-indigo-400 mx-auto opacity-70 animate-pulse" />
              <h3 className="text-sm font-bold text-white">Central Emergency Dispatch Console</h3>
              <p className="text-xs text-slate-400 max-w-md mx-auto">
                Select an active case from the Action Queue on the left to activate the Assisted Proxy Action Panel and the Deterministic Time-Scrubber Replay.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

