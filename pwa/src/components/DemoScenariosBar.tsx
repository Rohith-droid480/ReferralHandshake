import React from 'react';
import { Sparkles, AlertCircle, Zap, ShieldAlert, HeartPulse, Activity } from 'lucide-react';

export interface DemoScenario {
  id: number;
  title: string;
  badge: string;
  badgeColor: string;
  pathway: string;
  description: string;
  needClass: string;
  mgso4Status: 'GIVEN' | 'NONE_GIVEN' | 'UNKNOWN';
  mode: 'SEQUENTIAL' | 'PARALLEL2';
}

export const DEMO_SCENARIOS: DemoScenario[] = [
  {
    id: 1,
    title: '1. Severe Eclampsia',
    badge: 'UNKNOWN MgSO4 (D1)',
    badgeColor: 'text-rose-400 bg-rose-950/50 border-rose-600/40',
    pathway: 'PHC Channapatna -> CHC',
    description: 'Never blocks dispatch. Triggers persistent RED verification alert on receiving triage screen.',
    needClass: 'OBSTETRIC_EMERGENCY',
    mgso4Status: 'UNKNOWN',
    mode: 'SEQUENTIAL',
  },
  {
    id: 2,
    title: '2. Critical PPH Race',
    badge: 'PARALLEL2 Mode (I2)',
    badgeColor: 'text-amber-400 bg-amber-950/50 border-amber-600/40',
    pathway: 'Ramanagara vs Mandya',
    description: 'Concurrent race offers to 2 facilities. First valid PIN wins lease; loser instantly transitions to SUPERSEDED.',
    needClass: 'OBSTETRIC_EMERGENCY',
    mgso4Status: 'GIVEN',
    mode: 'PARALLEL2',
  },
  {
    id: 3,
    title: '3. Preterm Neonatal',
    badge: 'NICU + Paediatrician',
    badgeColor: 'text-cyan-400 bg-cyan-950/50 border-cyan-600/40',
    pathway: 'Counter / Decline flow',
    description: 'Tests live capability attestation (I15) and capacity-based counter-offer or deterministic redirection.',
    needClass: 'NEONATAL',
    mgso4Status: 'NONE_GIVEN',
    mode: 'SEQUENTIAL',
  },
  {
    id: 4,
    title: '4. NH-275 Polytrauma',
    badge: 'OT + Blood + Anesth',
    badgeColor: 'text-emerald-400 bg-emerald-950/50 border-emerald-600/40',
    pathway: 'Highway Transit & Geofence',
    description: 'Ambulance GPS telemetry along NH-275 corridor. 200m geofence emits advisory; requires human EMT confirmation.',
    needClass: 'TRAUMA',
    mgso4Status: 'NONE_GIVEN',
    mode: 'SEQUENTIAL',
  },
  {
    id: 5,
    title: '5. Acute STEMI',
    badge: 'Cardiac Extensibility',
    badgeColor: 'text-purple-400 bg-purple-950/50 border-purple-600/40',
    pathway: 'Apex Medical College',
    description: 'Proves protocol model extensibility beyond obstetric pathways into cardiac and stroke emergency care.',
    needClass: 'CARDIAC',
    mgso4Status: 'NONE_GIVEN',
    mode: 'SEQUENTIAL',
  },
];

interface DemoScenariosBarProps {
  onSelectScenario: (scenarioId: number) => void;
  activeScenarioId?: number;
}

export const DemoScenariosBar: React.FC<DemoScenariosBarProps> = ({
  onSelectScenario,
  activeScenarioId,
}) => {
  return (
    <div className="p-3 bg-slate-900/90 border border-slate-800 rounded-xl shadow-lg">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-1.5 text-xs font-semibold text-emerald-400 uppercase tracking-wider">
          <Sparkles className="w-4 h-4 text-emerald-400" />
          <span>1-Tap Real-World Emergency Scenarios</span>
        </div>
        <span className="text-[11px] text-slate-400 font-mono">Karnataka NH-275 Emergency Network</span>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-2">
        {DEMO_SCENARIOS.map((sc) => {
          const isSelected = activeScenarioId === sc.id;
          return (
            <button
              key={sc.id}
              type="button"
              onClick={() => onSelectScenario(sc.id)}
              className={`p-2.5 rounded-lg border text-left transition flex flex-col justify-between ${
                isSelected
                  ? 'bg-indigo-950/60 border-indigo-500 shadow-md ring-1 ring-indigo-500'
                  : 'bg-slate-950/60 border-slate-800 hover:border-slate-700 hover:bg-slate-800/50'
              }`}
            >
              <div>
                <div className="flex items-center justify-between gap-1 mb-1">
                  <span className="text-xs font-bold text-white leading-tight">{sc.title}</span>
                </div>
                <span
                  className={`inline-block px-1.5 py-0.5 rounded text-[10px] font-semibold border ${sc.badgeColor} mb-1`}
                >
                  {sc.badge}
                </span>
                <p className="text-[11px] text-slate-400 leading-snug">{sc.pathway}</p>
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
};
