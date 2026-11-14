import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ChevronLeft, ChevronRight, Compass, ShieldCheck } from 'lucide-react';

interface DemoStep {
  step: number;
  title: string;
  path: string;
  roleKey: string;
  roleName: string;
  instruction: string;
}

const DEMO_STEPS: DemoStep[] = [
  {
    step: 1,
    title: 'Step 1 of 6: Referring Clinician & MgSO4 Safety Lock (S1)',
    path: '/clinician',
    roleKey: 'PHC_CHANNAPATNA',
    roleName: 'Dr. Asha (Clinician @ PHC Channapatna)',
    instruction: 'Create emergency obstetric referral. Observe that MgSO4 UNKNOWN never blocks referral, but arms the safety banner.',
  },
  {
    step: 2,
    title: 'Step 2 of 6: Receiving Hospital Triage & Anti-Goodhart Desk (S1)',
    path: '/receiving-desk',
    roleKey: 'CHC_RAMANAGARA',
    roleName: 'Dr. Suresh (CMO @ CHC Ramanagara)',
    instruction: 'View priority queue (zero countdown clocks). See red MgSO4 warning banner. Confirm capabilities & accept with PIN 1234.',
  },
  {
    step: 3,
    title: 'Step 3 of 6: Two-Hospital Concurrency Race (S2)',
    path: '/arena',
    roleKey: 'CHC_RAMANAGARA',
    roleName: 'Judge / Arena View',
    instruction: 'Demonstrate Invariant I2. Exactly 1 facility wins the lease; the other receives 409 CONFLICT.',
  },
  {
    step: 4,
    title: 'Step 4 of 6: Unresponsive Facility Silence Escalation (S3)',
    path: '/dispatcher',
    roleKey: 'DISPATCH_108_CENTRAL',
    roleName: 'Officer Ramesh (108 Central Dispatcher)',
    instruction: 'When facilities fail to acknowledge, the accelerated notice ladder automatically escalates the case to the 108 Dispatcher.',
  },
  {
    step: 5,
    title: 'Step 5 of 6: Ambulance Highway Telemetry & Human Arrival Gate',
    path: '/ambulance',
    roleKey: 'DISPATCH_108_CENTRAL',
    roleName: 'EMT Manjunath (108 Ambulance KA-05-EM-1082)',
    instruction: 'Stream GPS telemetry on NH-275. Cross 200m geofence: system suggests arrival, but care handover requires human confirmation.',
  },
  {
    step: 6,
    title: 'Step 6 of 6: Pure-JS Browser Verifier & Tamper Proof (S6)',
    path: '/arena',
    roleKey: 'CHC_RAMANAGARA',
    roleName: 'Independent Verifier',
    instruction: 'Browser verifies Ed25519 Merkle root with zero server trust. Click "Inject SQL Tamper" to see browser instantly detect tampering.',
  },
];

export const GuidedDemoBanner: React.FC = () => {
  const navigate = useNavigate();
  const [currentStepIdx, setCurrentStepIdx] = useState<number>(() => {
    const saved = localStorage.getItem('rhp_demo_step');
    return saved ? parseInt(saved, 10) : 0;
  });

  const step = DEMO_STEPS[currentStepIdx] || DEMO_STEPS[0];

  const goToStep = (idx: number) => {
    if (idx < 0 || idx >= DEMO_STEPS.length) return;
    setCurrentStepIdx(idx);
    localStorage.setItem('rhp_demo_step', String(idx));
    const target = DEMO_STEPS[idx];
    navigate(target.path);

    // Update role if switcher exists
    fetch('/v1/auth/demo-session', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ role_key: target.roleKey }),
    })
      .then((r) => r.json())
      .then((data) => {
        localStorage.setItem('rhp_demo_role_key', target.roleKey);
        localStorage.setItem('rhp_session_token', data.token);
        localStorage.setItem('rhp_facility_id', data.facility_id);
        window.dispatchEvent(new Event('rhp-session-changed'));
      })
      .catch(() => {});
  };

  return (
    <div className="bg-slate-900 border-b border-teal-900/60 px-4 py-2 text-xs text-slate-200">
      <div className="max-w-7xl mx-auto flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <span className="px-2 py-0.5 bg-teal-900/80 text-teal-300 border border-teal-700/60 rounded font-bold font-mono text-[10px]">
            DEMO GUIDE
          </span>
          <span className="font-bold text-white tracking-tight">{step.title}</span>
          <span className="text-slate-400 hidden sm:inline">— {step.roleName}</span>
        </div>

        <div className="flex items-center gap-2">
          <p className="text-slate-300 text-[11px] hidden md:block max-w-lg truncate">{step.instruction}</p>
          <div className="flex items-center gap-1">
            <button
              onClick={() => goToStep(currentStepIdx - 1)}
              disabled={currentStepIdx === 0}
              className="p-1 rounded bg-slate-800 hover:bg-slate-700 disabled:opacity-40 text-slate-300 hover:text-white transition"
              title="Previous Demo Step"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>
            <span className="font-mono text-[11px] text-teal-400 px-1 font-bold">
              {currentStepIdx + 1}/{DEMO_STEPS.length}
            </span>
            <button
              onClick={() => goToStep(currentStepIdx + 1)}
              disabled={currentStepIdx === DEMO_STEPS.length - 1}
              className="p-1 rounded bg-slate-800 hover:bg-slate-700 disabled:opacity-40 text-slate-300 hover:text-white transition"
              title="Next Demo Step"
            >
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

