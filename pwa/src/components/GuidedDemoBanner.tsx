import React, { useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import {
  Compass,
  ChevronDown,
  ChevronUp,
  Stethoscope,
  Hospital,
  Tv,
  Navigation,
  PhoneCall,
  Activity,
  KeyRound,
  CheckCircle2,
  ExternalLink,
} from 'lucide-react';

interface DemoStep {
  path: string;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
  roleHint: string;
  actionHint: string;
  invariantBadge: string;
}

const DEMO_STEPS: DemoStep[] = [
  {
    path: '/clinician',
    label: '1. Clinician Card',
    icon: Stethoscope,
    roleHint: 'Role: PHC Channapatna (CLINICIAN)',
    actionHint: 'Click "1. Severe Eclampsia" scenario -> Note UNKNOWN MgSO4 -> Click "Sign & Dispatch Referral"',
    invariantBadge: 'D1 Drug Safety Lock',
  },
  {
    path: '/receiving-desk',
    label: '2. Receiving Desk',
    icon: Hospital,
    roleHint: 'Role: CHC Ramanagara (CMO)',
    actionHint: 'Notice zero ticking countdown clocks -> Confirm OT/Blood -> Enter PIN 1234 -> Click "Sign & Commit Acceptance"',
    invariantBadge: 'I2 Single Leaseholder',
  },
  {
    path: '/arena',
    label: '3. Guarantee Arena',
    icon: Tv,
    roleHint: 'Big Screen Concurrency Race',
    actionHint: 'Watch DH Mandya transition to SUPERSEDED -> Scan QR or click "Join as Judge Desk" -> Run pure-JS verifier',
    invariantBadge: 'F8 Ed25519 Merkle Proof',
  },
  {
    path: '/ambulance',
    label: '4. Ambulance PWA',
    icon: Navigation,
    roleHint: 'Role: 108 Emergency EMT',
    actionHint: 'Click "Start Highway Simulation" along NH-275 -> Cross 200m geofence -> Click human "Confirm Arrival"',
    invariantBadge: 'D2 Human Arrival Gate',
  },
  {
    path: '/dispatcher',
    label: '5. Dispatcher Hub',
    icon: PhoneCall,
    roleHint: 'Role: 108 Central Dispatcher',
    actionHint: 'Select escalated case -> Drag "Deterministic Time-Scrubber" slider to audit history -> Assign to Apex College',
    invariantBadge: 'I13 Finite Bound T_max',
  },
  {
    path: '/command-centre',
    label: '6. Command Centre',
    icon: Activity,
    roleHint: 'Role: District Health Officer',
    actionHint: 'Export FHIR R4 / IEEE 1849 XES / BSA s.63 Certificate -> Click "1-Click DPDP 2023 Crypto-Shred"',
    invariantBadge: 'Closure F9 DPDP Shred',
  },
];

export const GuidedDemoBanner: React.FC = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const [collapsed, setCollapsed] = useState(false);

  // Find active step matching current path
  const currentStepIndex = DEMO_STEPS.findIndex((s) => s.path === location.pathname);
  const activeStep = currentStepIndex !== -1 ? DEMO_STEPS[currentStepIndex] : null;

  return (
    <div className="bg-slate-900 border-b border-indigo-900/50 shadow-md">
      <div className="max-w-7xl mx-auto px-4 py-2 flex flex-col gap-2">
        {/* Header row */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="p-1.5 bg-indigo-600/30 text-indigo-400 rounded border border-indigo-500/30">
              <Compass className="w-4 h-4" />
            </div>
            <div>
              <span className="text-xs font-bold text-white tracking-wide uppercase">
                Interactive Judge Walkthrough Guide
              </span>
              <span className="ml-2 text-[11px] text-slate-400">
                Protocol RHP-1 Multi-Desk Demonstration
              </span>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-emerald-950/60 border border-emerald-500/40 text-emerald-300 text-xs font-mono font-medium">
              <KeyRound className="w-3 h-3 text-emerald-400" />
              Demo PIN: 1234
            </span>
            <button
              onClick={() => setCollapsed(!collapsed)}
              className="text-xs text-slate-400 hover:text-white flex items-center gap-1 transition"
            >
              {collapsed ? (
                <>
                  <span className="text-[11px]">Expand Steps</span>
                  <ChevronDown className="w-3.5 h-3.5" />
                </>
              ) : (
                <>
                  <span className="text-[11px]">Minimize</span>
                  <ChevronUp className="w-3.5 h-3.5" />
                </>
              )}
            </button>
          </div>
        </div>

        {/* Step buttons bar */}
        {!collapsed && (
          <div className="flex items-center gap-1.5 overflow-x-auto pb-1 pt-0.5">
            {DEMO_STEPS.map((step, idx) => {
              const Icon = step.icon;
              const isActive = location.pathname === step.path;
              return (
                <button
                  key={step.path}
                  onClick={() => navigate(step.path)}
                  className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-medium whitespace-nowrap transition border ${
                    isActive
                      ? 'bg-indigo-600 text-white border-indigo-400 shadow-sm'
                      : 'bg-slate-800/80 text-slate-300 border-slate-700 hover:bg-slate-800 hover:text-white'
                  }`}
                >
                  <Icon className="w-3.5 h-3.5" />
                  <span>{step.label}</span>
                  {isActive && <CheckCircle2 className="w-3 h-3 text-emerald-300 ml-0.5" />}
                </button>
              );
            })}
          </div>
        )}

        {/* Active contextual hint */}
        {activeStep && (
          <div className="flex flex-wrap items-center justify-between gap-2 px-3 py-1.5 bg-slate-950/70 border border-slate-800 rounded-lg text-xs">
            <div className="flex items-center gap-2">
              <span className="text-amber-400 font-semibold uppercase text-[10px] tracking-wider px-1.5 py-0.5 bg-amber-950/40 border border-amber-600/30 rounded">
                Current Action
              </span>
              <span className="text-slate-200">{activeStep.actionHint}</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-slate-400 text-[11px]">{activeStep.roleHint}</span>
              <span className="px-2 py-0.5 bg-indigo-950/50 border border-indigo-600/40 text-indigo-300 rounded text-[11px] font-mono">
                {activeStep.invariantBadge}
              </span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

