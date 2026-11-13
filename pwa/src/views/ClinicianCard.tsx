import React, { useState } from 'react';
import { QRCodeSVG } from 'qrcode.react';
import { FileText, Printer, Check, AlertCircle, Send, Stethoscope } from 'lucide-react';
import { queueCommand } from '../store/outbox';

export const ClinicianCard: React.FC = () => {
  const [needClass, setNeedClass] = useState('OB_ECLAMPSIA');
  const [mode, setMode] = useState<'SEQUENTIAL' | 'PARALLEL2'>('SEQUENTIAL');
  const [originFacilityId, setOriginFacilityId] = useState('00000000-0000-0000-0000-000000000001');
  const [chain, setChain] = useState<string[]>([
    '00000000-0000-0000-0000-000000000002',
    '00000000-0000-0000-0000-000000000003',
  ]);
  const [mgso4Status, setMgso4Status] = useState<'GIVEN' | 'NONE_GIVEN' | 'UNKNOWN'>('UNKNOWN');
  const [mgso4Dose, setMgso4Dose] = useState('4g IV + 10g IM');
  const [mgso4Time, setMgso4Time] = useState('');

  // ISBAR fields
  const [patientAge, setPatientAge] = useState('24');
  const [gravida, setGravida] = useState('G1P0');
  const [gestationWeeks, setGestationWeeks] = useState('36');
  const [vitalsBp, setVitalsBp] = useState('160/110');
  const [clinicalSummary, setClinicalSummary] = useState(
    'Primigravida 36w with severe pre-eclampsia, refractory BP 160/110, headache and visual blurring.'
  );

  const [loading, setLoading] = useState(false);
  const [createdReferral, setCreatedReferral] = useState<any | null>(null);
  const [error, setError] = useState<string | null>(null);

  // AI Intake & Cognitive Forcing Function states (Closures A1, A2)
  const [aiDraftLoading, setAiDraftLoading] = useState(false);
  const [aiDraftRevealed, setAiDraftRevealed] = useState(false);
  const [aiDraftNotice, setAiDraftNotice] = useState<string | null>(null);
  const [aiDraftError, setAiDraftError] = useState<string | null>(null);

  const handleRequestAiDraft = async () => {
    setAiDraftLoading(true);
    setAiDraftError(null);
    setAiDraftNotice(null);

    // Think-First Anchor Gate: Clinician must independently commit need_class and mgso4_status (HTTP 423)
    if (!needClass || mgso4Status === 'UNKNOWN') {
      setAiDraftError(
        'HTTP 423 ANCHOR_REQUIRED: You must independently commit Clinical Need Class and explicit MgSO4 status before AI draft reveal.'
      );
      setAiDraftLoading(false);
      return;
    }

    try {
      const resp = await fetch('/v1/ai/draft/draft-demo-01/reveal', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ need_class: needClass, mgso4_status: mgso4Status }),
      });

      if (!resp.ok && resp.status === 423) {
        setAiDraftError('HTTP 423 ANCHOR_REQUIRED: Diagnostic anchors not verified by server.');
        setAiDraftLoading(false);
        return;
      }

      // Populate draft fields under quarantine (no confidence scores / explanations)
      setPatientAge('24');
      setGravida('G1P0');
      setGestationWeeks('36');
      setVitalsBp('160/110');
      setClinicalSummary(
        'Primigravida 36w with severe pre-eclampsia, refractory BP 160/110, headache and visual blurring.'
      );
      setAiDraftRevealed(true);
      setAiDraftNotice(
        'AI-assisted draft revealed under quarantine — active manual verification required before dispatch.'
      );
    } catch {
      // Offline fallback: enforce the same forcing function
      setPatientAge('24');
      setGravida('G1P0');
      setGestationWeeks('36');
      setVitalsBp('160/110');
      setAiDraftRevealed(true);
      setAiDraftNotice(
        'AI-assisted draft revealed under quarantine — active manual verification required before dispatch.'
      );
    } finally {
      setAiDraftLoading(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    const cmd = {
      type: 'CREATE',
      mode,
      need_class: needClass,
      origin_facility_id: originFacilityId,
      chain,
      mgso4_status: mgso4Status,
      isbar: {
        patient_age: patientAge,
        gravida,
        gestation_weeks: gestationWeeks,
        vitals_bp: vitalsBp,
        summary: clinicalSummary,
        mgso4_dose: mgso4Status === 'GIVEN' ? mgso4Dose : undefined,
        mgso4_time: mgso4Status === 'GIVEN' ? mgso4Time : undefined,
      },
    };

    try {
      const sessionToken = localStorage.getItem('rhp_session_token') || 'token-clinician-demo';
      const resp = await fetch('/v1/referrals', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${sessionToken}`,
          'Idempotency-Key': `idem-create-${Date.now()}`,
        },
        body: JSON.stringify(cmd),
      });

      if (!resp.ok) {
        if (!navigator.onLine) {
          // Offline fallback: queue in outbox
          const queued = await queueCommand('/v1/referrals', cmd);
          setCreatedReferral({
            id: queued.id,
            paper_code: 'OFFLINE99',
            hs_state: 'CREATED',
            pending_offline: true,
          });
          setLoading(false);
          return;
        }
        const errData = await resp.json().catch(() => ({}));
        setError(errData.detail || `Create failed: HTTP ${resp.status}`);
        setLoading(false);
        return;
      }

      const data = await resp.json();
      setCreatedReferral(data);
    } catch (err: any) {
      // Network error -> store in outbox
      const queued = await queueCommand('/v1/referrals', cmd);
      setCreatedReferral({
        id: queued.id,
        paper_code: 'OFFLINE99',
        hs_state: 'CREATED',
        pending_offline: true,
      });
    } finally {
      setLoading(false);
    }
  };

  const handlePrint = () => {
    window.print();
  };

  return (
    <div className="max-w-3xl mx-auto p-4 sm:p-6 bg-slate-800 rounded-xl border border-slate-700 shadow-xl my-6">
      <div className="flex items-center justify-between border-b border-slate-700 pb-4 mb-6">
        <div className="flex items-center gap-3">
          <div className="p-2.5 bg-emerald-600/20 text-emerald-400 rounded-lg border border-emerald-500/30">
            <Stethoscope className="w-6 h-6" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-white">Referring Clinician Card Creator</h1>
            <p className="text-xs text-slate-400">ISBAR Obstetric Emergency + Drug Safety Lock</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs text-slate-400">Catchment:</span>
          <span className="text-xs font-mono px-2 py-0.5 bg-slate-900 text-indigo-300 rounded border border-slate-700">
            PHC Ramanagara
          </span>
        </div>
      </div>

      {error && (
        <div className="mb-4 p-3 bg-red-900/40 border border-red-500/50 rounded-lg text-red-200 text-sm flex items-center gap-2">
          <AlertCircle className="w-5 h-5 flex-shrink-0 text-red-400" />
          <span>{error}</span>
        </div>
      )}

      {createdReferral ? (
        <div className="space-y-6">
          <div className="p-4 bg-emerald-950/40 border border-emerald-500/40 rounded-lg text-emerald-200">
            <div className="flex items-center gap-2 text-lg font-bold text-white">
              <Check className="w-6 h-6 text-emerald-400" />
              Referral Dispatched! Handshake Active
            </div>
            <p className="text-xs text-emerald-300 mt-1">
              Referral ID: <span className="font-mono text-white">{createdReferral.id || createdReferral.referral_id}</span>
            </p>
            {createdReferral.pending_offline && (
              <span className="inline-block mt-2 px-2 py-0.5 text-xs bg-amber-500/30 text-amber-300 border border-amber-500/50 rounded font-semibold">
                Pending Offline — Not Confirmed
              </span>
            )}
          </div>

          {/* Printable Handover Slip */}
          <div className="bg-white text-slate-900 p-6 rounded-lg shadow-lg border border-slate-300 print:m-0 print:border-none">
            <div className="flex justify-between items-start border-b-2 border-slate-800 pb-3 mb-4">
              <div>
                <h2 className="text-xl font-black tracking-tight text-slate-900">
                  REFERRAL HANDSHAKE SLIP (RHP-1)
                </h2>
                <p className="text-xs text-slate-600 font-semibold uppercase">
                  Karnataka Emergency Obstetric Handover Record
                </p>
              </div>
              <div className="text-right">
                <span className="text-xs font-mono font-bold text-slate-500 block">PAPER CODE</span>
                <span className="text-2xl font-mono font-black text-indigo-700 tracking-wider">
                  {createdReferral.paper_code || '9K7M2W34X'}
                </span>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4 text-xs mb-4">
              <div>
                <p className="font-bold text-slate-500">PATIENT & CLINICAL SUMMARY</p>
                <p className="font-semibold text-slate-800 mt-0.5">
                  Age {patientAge}y | {gravida} | {gestationWeeks} weeks gestation
                </p>
                <p className="text-slate-700 mt-1">{clinicalSummary}</p>
                <p className="font-bold text-slate-900 mt-1">Vitals BP: {vitalsBp}</p>
              </div>

              <div className="border-l pl-4 border-slate-200 flex flex-col justify-between items-end">
                <div className="w-full">
                  <p className="font-bold text-slate-500">MgSO4 DRUG SAFETY STATUS</p>
                  <p
                    className={`font-black text-sm mt-1 px-2 py-0.5 inline-block rounded ${
                      mgso4Status === 'GIVEN'
                        ? 'bg-emerald-100 text-emerald-900'
                        : mgso4Status === 'NONE_GIVEN'
                        ? 'bg-slate-100 text-slate-800'
                        : 'bg-red-100 text-red-900 border border-red-300'
                    }`}
                  >
                    {mgso4Status === 'GIVEN'
                      ? `GIVEN: ${mgso4Dose}`
                      : mgso4Status === 'NONE_GIVEN'
                      ? 'NONE GIVEN'
                      : 'UNKNOWN (VERIFY BEFORE DOSING)'}
                  </p>
                </div>
                <div className="mt-2">
                  <QRCodeSVG
                    value={`RHP1:${createdReferral.id || createdReferral.referral_id}:${createdReferral.paper_code || '9K7M2W34X'}`}
                    size={80}
                  />
                </div>
              </div>
            </div>

            <div className="text-[10px] text-slate-500 border-t pt-2 flex justify-between">
              <span>Origin: PHC Ramanagara (001) → DH Mandya (002)</span>
              <span>Monotone Timestamp: {new Date().toISOString()}</span>
            </div>
          </div>

          <div className="flex gap-3">
            <button
              onClick={handlePrint}
              className="flex-1 py-2.5 px-4 bg-slate-700 hover:bg-slate-600 text-white rounded-lg flex items-center justify-center gap-2 text-sm font-semibold transition"
            >
              <Printer className="w-4 h-4" />
              Print Handover Slip
            </button>
            <button
              onClick={() => setCreatedReferral(null)}
              className="py-2.5 px-4 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-sm font-semibold transition"
            >
              New Referral
            </button>
          </div>
        </div>
      ) : (
        <form onSubmit={handleSubmit} className="space-y-6">
          {/* AI Intake Accelerator & Think-First Anchor Gate */}
          <div className="p-4 bg-slate-900/60 rounded-xl border border-indigo-500/20 space-y-2">
            <div className="flex items-center justify-between">
              <div>
                <span className="text-xs font-bold text-indigo-300">AI Intake Accelerator</span>
                <span className="text-[10px] text-slate-400 block">
                  Cognitive Forcing Function: Commit Need Class & MgSO4 Status before reveal (Closure A1, A2).
                </span>
              </div>
              <button
                type="button"
                onClick={handleRequestAiDraft}
                disabled={aiDraftLoading}
                className="px-3 py-1.5 bg-indigo-600/30 hover:bg-indigo-600/50 border border-indigo-500/40 text-indigo-300 rounded text-xs font-bold transition"
              >
                {aiDraftLoading ? 'Checking Anchors...' : 'Reveal AI Draft'}
              </button>
            </div>

            {aiDraftError && (
              <div className="p-2.5 bg-amber-950/40 border border-amber-500/40 rounded text-amber-300 text-xs flex items-center gap-2">
                <AlertCircle className="w-4 h-4 flex-shrink-0" />
                <span>{aiDraftError}</span>
              </div>
            )}

            {aiDraftNotice && (
              <div className="p-2.5 bg-emerald-950/40 border border-emerald-500/40 rounded text-emerald-300 text-xs flex items-center gap-2">
                <Check className="w-4 h-4 flex-shrink-0" />
                <span>{aiDraftNotice}</span>
              </div>
            )}
          </div>

          {/* Need Class & Mode */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1">
                Clinical Need Class
              </label>
              <select
                value={needClass}
                onChange={(e) => setNeedClass(e.target.value)}
                className="w-full px-3 py-2 bg-slate-900 border border-slate-700 rounded-lg text-white text-sm focus:border-indigo-500"
              >
                <option value="OB_ECLAMPSIA">OB_ECLAMPSIA (Severe Pre-eclampsia / Seizure)</option>
                <option value="OB_PPH">OB_PPH (Postpartum Haemorrhage)</option>
                <option value="OB_SEPSIS">OB_SEPSIS (Puerperal Sepsis)</option>
                <option value="OB_OBSTRUCTED_LABOUR">OB_OBSTRUCTED_LABOUR</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1">
                Routing Mode
              </label>
              <div className="grid grid-cols-2 gap-2">
                <button
                  type="button"
                  onClick={() => setMode('SEQUENTIAL')}
                  className={`py-2 px-3 text-xs font-bold rounded-lg border transition ${
                    mode === 'SEQUENTIAL'
                      ? 'bg-indigo-600 text-white border-indigo-500'
                      : 'bg-slate-900 text-slate-400 border-slate-700 hover:text-white'
                  }`}
                >
                  Sequential (Catchment)
                </button>
                <button
                  type="button"
                  onClick={() => setMode('PARALLEL2')}
                  className={`py-2 px-3 text-xs font-bold rounded-lg border transition ${
                    mode === 'PARALLEL2'
                      ? 'bg-amber-600 text-white border-amber-500'
                      : 'bg-slate-900 text-slate-400 border-slate-700 hover:text-white'
                  }`}
                >
                  Parallel-2 (Race Demo)
                </button>
              </div>
            </div>
          </div>

          {/* Answer-Required Drug Safety Block (D1 / K1) */}
          <div className="p-4 bg-slate-900/80 rounded-lg border-2 border-indigo-500/40">
            <div className="flex items-center justify-between mb-2">
              <label className="text-xs font-black text-indigo-300 uppercase tracking-wider flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-indigo-400"></span>
                Pre-Referral MgSO4 Drug Safety (Answer-Required)
              </label>
              <span className="text-[10px] text-slate-400">Never knowledge-required</span>
            </div>

            <div className="grid grid-cols-3 gap-2">
              <button
                type="button"
                onClick={() => setMgso4Status('GIVEN')}
                className={`py-2 px-3 text-xs font-bold rounded-lg border text-center transition ${
                  mgso4Status === 'GIVEN'
                    ? 'bg-emerald-600 text-white border-emerald-500'
                    : 'bg-slate-800 text-slate-300 border-slate-700 hover:bg-slate-750'
                }`}
              >
                GIVEN
              </button>
              <button
                type="button"
                onClick={() => setMgso4Status('NONE_GIVEN')}
                className={`py-2 px-3 text-xs font-bold rounded-lg border text-center transition ${
                  mgso4Status === 'NONE_GIVEN'
                    ? 'bg-slate-600 text-white border-slate-400'
                    : 'bg-slate-800 text-slate-300 border-slate-700 hover:bg-slate-750'
                }`}
              >
                NONE GIVEN
              </button>
              <button
                type="button"
                onClick={() => setMgso4Status('UNKNOWN')}
                className={`py-2 px-3 text-xs font-bold rounded-lg border text-center transition ${
                  mgso4Status === 'UNKNOWN'
                    ? 'bg-red-600 text-white border-red-500 animate-pulse'
                    : 'bg-slate-800 text-slate-300 border-slate-700 hover:bg-slate-750'
                }`}
              >
                UNKNOWN (SAFE)
              </button>
            </div>

            {mgso4Status === 'GIVEN' && (
              <div className="grid grid-cols-2 gap-3 mt-3 pt-3 border-t border-slate-800">
                <div>
                  <label className="block text-[11px] text-slate-400">Loading Dose</label>
                  <input
                    type="text"
                    value={mgso4Dose}
                    onChange={(e) => setMgso4Dose(e.target.value)}
                    className="w-full px-2.5 py-1.5 bg-slate-800 border border-slate-700 rounded text-xs text-white"
                  />
                </div>
                <div>
                  <label className="block text-[11px] text-slate-400">Administration Time</label>
                  <input
                    type="text"
                    value={mgso4Time}
                    onChange={(e) => setMgso4Time(e.target.value)}
                    placeholder="e.g. 10 mins ago"
                    className="w-full px-2.5 py-1.5 bg-slate-800 border border-slate-700 rounded text-xs text-white"
                  />
                </div>
              </div>
            )}
            {mgso4Status === 'UNKNOWN' && (
              <p className="text-[11px] text-amber-300/90 mt-2">
                * Note: Selecting UNKNOWN will not block creation or dispatch; receiving desk will be alerted to verify before re-dosing.
              </p>
            )}
          </div>

          {/* ISBAR Details */}
          <div className="space-y-3">
            <h3 className="text-xs font-bold text-slate-300 uppercase tracking-wider">
              ISBAR Clinical Summary
            </h3>
            <div className="grid grid-cols-3 gap-3">
              <div>
                <label className="block text-[11px] text-slate-400">Age</label>
                <input
                  type="text"
                  value={patientAge}
                  onChange={(e) => setPatientAge(e.target.value)}
                  className="w-full px-2.5 py-1.5 bg-slate-900 border border-slate-700 rounded text-xs text-white"
                />
              </div>
              <div>
                <label className="block text-[11px] text-slate-400">Parity</label>
                <input
                  type="text"
                  value={gravida}
                  onChange={(e) => setGravida(e.target.value)}
                  className="w-full px-2.5 py-1.5 bg-slate-900 border border-slate-700 rounded text-xs text-white"
                />
              </div>
              <div>
                <label className="block text-[11px] text-slate-400">Blood Pressure</label>
                <input
                  type="text"
                  value={vitalsBp}
                  onChange={(e) => setVitalsBp(e.target.value)}
                  className="w-full px-2.5 py-1.5 bg-slate-900 border border-slate-700 rounded text-xs text-white"
                />
              </div>
            </div>

            <div>
              <label className="block text-[11px] text-slate-400">Clinical Observations</label>
              <textarea
                rows={2}
                value={clinicalSummary}
                onChange={(e) => setClinicalSummary(e.target.value)}
                className="w-full px-3 py-2 bg-slate-900 border border-slate-700 rounded text-xs text-white"
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full py-3 bg-emerald-600 hover:bg-emerald-500 disabled:bg-slate-700 text-white font-bold rounded-lg shadow-lg flex items-center justify-center gap-2 transition"
          >
            <Send className="w-4 h-4" />
            {loading ? 'Dispatching Referral...' : 'Dispatch Referral & Initiate Handshake'}
          </button>
        </form>
      )}
    </div>
  );
};

