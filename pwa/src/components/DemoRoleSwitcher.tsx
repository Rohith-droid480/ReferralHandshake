import React, { useState, useEffect } from 'react';
import { UserCheck, Shield, KeyRound, RefreshCw, CheckCircle2 } from 'lucide-react';

interface RoleOption {
  key: string;
  label: string;
  tier: string;
  role: string;
  facilityName: string;
  pin: string;
}

const DEMO_ROLES: RoleOption[] = [
  {
    key: 'PHC_CHANNAPATNA',
    label: 'PHC Channapatna',
    tier: 'PHC',
    role: 'CLINICIAN',
    facilityName: 'Channapatna Primary Health Centre',
    pin: '1234',
  },
  {
    key: 'CHC_RAMANAGARA',
    label: 'CHC Ramanagara (Desk 1)',
    tier: 'CHC',
    role: 'CMO',
    facilityName: 'Ramanagara Community Health Centre',
    pin: '1234',
  },
  {
    key: 'DH_MANDYA',
    label: 'DH Mandya (Desk 2)',
    tier: 'DH',
    role: 'CMO',
    facilityName: 'Mandya District Hospital',
    pin: '1234',
  },
  {
    key: 'MC_BENGALURU_OB',
    label: 'MC Bengaluru (Desk 3)',
    tier: 'MC',
    role: 'CONSULTANT',
    facilityName: 'Bengaluru Apex Obstetric Medical College',
    pin: '1234',
  },
  {
    key: 'DISPATCH_108_CENTRAL',
    label: '108 Dispatch & EMT',
    tier: 'DISPATCH',
    role: 'DISPATCHER',
    facilityName: 'Karnataka 108 Central Dispatch Hub',
    pin: '1234',
  },
];

export const DemoRoleSwitcher: React.FC = () => {
  const [currentRoleKey, setCurrentRoleKey] = useState<string>(
    localStorage.getItem('rhp_demo_role_key') || 'PHC_CHANNAPATNA'
  );
  const [loading, setLoading] = useState<boolean>(false);
  const [feedback, setFeedback] = useState<string | null>(null);

  const switchRole = async (roleKey: string) => {
    setLoading(true);
    setFeedback(null);
    try {
      const res = await fetch('/v1/auth/demo-session', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ role_key: roleKey }),
      });

      if (res.ok) {
        const data = await res.json();
        localStorage.setItem('rhp_demo_role_key', roleKey);
        localStorage.setItem('rhp_session_token', data.token);
        localStorage.setItem('rhp_roster_id', data.roster_id);
        localStorage.setItem('rhp_facility_id', data.facility_id);
        localStorage.setItem('rhp_role_slot', data.role_slot);
        localStorage.setItem('rhp_pin', data.pin || '1234');
        setCurrentRoleKey(roleKey);
        setFeedback(`Switched to ${data.facility_name} (${data.role_slot}) — PIN: 1234`);
        window.dispatchEvent(new Event('rhp-session-changed'));
      } else {
        setFeedback('Failed to switch role');
      }
    } catch (e) {
      setFeedback('Offline/Mock session active');
    } finally {
      setLoading(false);
      setTimeout(() => setFeedback(null), 4000);
    }
  };

  useEffect(() => {
    if (!localStorage.getItem('rhp_session_token')) {
      switchRole('PHC_CHANNAPATNA');
    }
  }, []);

  return (
    <div className="bg-slate-900/90 border-b border-indigo-900/50 px-3 py-1.5 flex flex-wrap items-center justify-between gap-2 text-xs backdrop-blur-sm">
      <div className="flex items-center gap-2">
        <span className="flex items-center gap-1 font-semibold text-indigo-400">
          <UserCheck className="w-3.5 h-3.5" />
          Quick Role Switcher:
        </span>
        <div className="flex items-center gap-1 overflow-x-auto py-0.5">
          {DEMO_ROLES.map((r) => {
            const isSelected = currentRoleKey === r.key;
            return (
              <button
                key={r.key}
                onClick={() => switchRole(r.key)}
                disabled={loading}
                className={`px-2.5 py-1 rounded-md text-[11px] font-medium transition flex items-center gap-1 ${
                  isSelected
                    ? 'bg-indigo-600 text-white shadow-sm ring-1 ring-indigo-400'
                    : 'bg-slate-800 text-slate-300 hover:bg-slate-700 hover:text-white'
                }`}
              >
                <span>{r.label}</span>
                <span className="text-[9px] opacity-75">({r.role})</span>
              </button>
            );
          })}
        </div>
      </div>

      <div className="flex items-center gap-3">
        <span className="flex items-center gap-1 text-slate-400 text-[11px]">
          <KeyRound className="w-3 h-3 text-amber-400" />
          Demo PIN: <strong className="text-amber-300 font-mono">1234</strong>
        </span>
      </div>

      {feedback && (
        <div className="w-full mt-1 bg-indigo-950/80 border border-indigo-700 text-indigo-200 px-2 py-0.5 rounded text-[11px] flex items-center gap-1">
          <CheckCircle2 className="w-3 h-3 text-emerald-400" />
          <span>{feedback}</span>
        </div>
      )}
    </div>
  );
};

