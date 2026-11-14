import React, { useState, useEffect } from 'react';
import { UserCheck, Shield, KeyRound, Wifi } from 'lucide-react';

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
    label: 'CHC Ramanagara',
    tier: 'CHC',
    role: 'CMO',
    facilityName: 'Ramanagara Community Health Centre',
    pin: '1234',
  },
  {
    key: 'DH_MANDYA',
    label: 'DH Mandya',
    tier: 'DH',
    role: 'CMO',
    facilityName: 'Mandya District Hospital',
    pin: '1234',
  },
  {
    key: 'MC_BENGALURU_OB',
    label: 'MC Bengaluru',
    tier: 'MC',
    role: 'CONSULTANT',
    facilityName: 'Bengaluru Apex Obstetric Medical College',
    pin: '1234',
  },
  {
    key: 'DISPATCH_108_CENTRAL',
    label: '108 Dispatcher',
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

  const activeRole = DEMO_ROLES.find((r) => r.key === currentRoleKey) || DEMO_ROLES[0];

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
        setFeedback(`Active: ${data.role_slot} @ ${data.facility_name} (PIN: 1234)`);
        window.dispatchEvent(new Event('rhp-session-changed'));
      } else {
        setFeedback('Failed to switch role');
      }
    } catch (e) {
      setFeedback('Offline / Mock session active');
    } finally {
      setLoading(false);
      setTimeout(() => setFeedback(null), 3000);
    }
  };

  useEffect(() => {
    if (!localStorage.getItem('rhp_session_token')) {
      switchRole('PHC_CHANNAPATNA');
    }

    const handler = () => {
      const savedKey = localStorage.getItem('rhp_demo_role_key');
      if (savedKey && savedKey !== currentRoleKey) {
        setCurrentRoleKey(savedKey);
      }
    };
    window.addEventListener('rhp-session-changed', handler);
    return () => window.removeEventListener('rhp-session-changed', handler);
  }, [currentRoleKey]);

  return (
    <div className="bg-slate-900/95 border-b border-slate-800 px-4 py-2 flex flex-wrap items-center justify-between gap-3 text-xs">
      {/* Current Active Role Badge */}
      <div className="flex items-center gap-2">
        <span className="text-slate-400 font-medium">Acting as:</span>
        <div className="flex items-center gap-1.5 px-2.5 py-1 bg-slate-800 border border-slate-700 rounded-md font-semibold text-white">
          <span className="w-2 h-2 rounded-full bg-teal-400"></span>
          <span className="text-teal-300 font-mono">{activeRole.role}</span>
          <span className="text-slate-400">@</span>
          <span>{activeRole.facilityName}</span>
          <span className="text-slate-400 text-[10px] font-mono ml-1.5 px-1 bg-slate-900 rounded border border-slate-700">
            PIN: 1234
          </span>
        </div>
      </div>

      {/* Role Selection Buttons */}
      <div className="flex items-center gap-1.5">
        <span className="text-[11px] text-slate-400 hidden sm:inline">Switch Role:</span>
        <div className="flex items-center gap-1 overflow-x-auto">
          {DEMO_ROLES.map((r) => {
            const isSelected = currentRoleKey === r.key;
            return (
              <button
                key={r.key}
                onClick={() => switchRole(r.key)}
                disabled={loading}
                className={`px-2 py-1 rounded text-[11px] font-medium transition ${
                  isSelected
                    ? 'bg-teal-700 text-white font-bold border border-teal-500'
                    : 'bg-slate-800 text-slate-300 hover:bg-slate-700 hover:text-white border border-slate-700'
                }`}
              >
                {r.label}
              </button>
            );
          })}
        </div>
      </div>

      {/* Feedback toast */}
      {feedback && (
        <span className="text-[11px] text-teal-300 font-mono bg-teal-950/80 px-2 py-0.5 rounded border border-teal-800 animate-fade">
          {feedback}
        </span>
      )}
    </div>
  );
};
