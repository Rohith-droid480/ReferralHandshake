import React, { useState, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { Shield, CheckCircle, AlertTriangle, Hospital, ArrowRight } from 'lucide-react';

export const JudgeJoin: React.FC = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();

  const [jti, setJti] = useState(searchParams.get('jti') || '');
  const [turnstileToken, setTurnstileToken] = useState('lan-mode-token');
  const [isLanMode, setIsLanMode] = useState(true);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [assignedDesk, setAssignedDesk] = useState<any | null>(null);

  useEffect(() => {
    fetch('/mode')
      .then((r) => r.json())
      .then((data) => {
        setIsLanMode(Boolean(data.lan_mode || data.LAN_MODE));
      })
      .catch(() => setIsLanMode(true));
  }, []);

  const handleJoin = async () => {
    if (!jti.trim()) {
      setError('Please provide or scan a valid QR token (JTI)');
      return;
    }
    setLoading(true);
    setError(null);

    try {
      const resp = await fetch('/v1/judge/join', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          jti: jti.trim(),
          turnstile_token: turnstileToken,
        }),
      });

      const data = await resp.json();

      if (!resp.ok) {
        if (resp.status === 429) {
          setError('429 ADMISSION_CAP_REACHED: 20 judge desks already active.');
        } else if (resp.status === 403) {
          setError(`403 FORBIDDEN: ${data.detail || 'Invalid or already used QR token'}`);
        } else {
          setError(data.detail || `Join failed (HTTP ${resp.status})`);
        }
        setLoading(false);
        return;
      }

      setAssignedDesk(data);
      // Store session token in localStorage or cookie
      if (data.session_token) {
        localStorage.setItem('rhp_session_token', data.session_token);
        localStorage.setItem('rhp_facility_id', data.facility_id);
        localStorage.setItem('rhp_facility_name', data.facility_name);
        localStorage.setItem('rhp_desk_number', String(data.desk_number));
      }

      setTimeout(() => {
        navigate('/judge-desk');
      }, 1200);
    } catch (err: any) {
      setError(err?.message || 'Network error during join');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-md mx-auto p-6 mt-8 bg-slate-800 rounded-xl border border-slate-700 shadow-2xl">
      <div className="flex items-center gap-3 mb-6">
        <div className="p-3 bg-indigo-600/20 text-indigo-400 rounded-lg border border-indigo-500/30">
          <Hospital className="w-8 h-8" />
        </div>
        <div>
          <h1 className="text-xl font-bold text-white">Judge Admission Desk</h1>
          <p className="text-xs text-slate-400">Rotating QR Admission (≤20 Desks Cap)</p>
        </div>
      </div>

      {error && (
        <div className="mb-4 p-3 bg-red-900/40 border border-red-500/50 rounded-lg text-red-200 text-sm flex items-start gap-2">
          <AlertTriangle className="w-5 h-5 flex-shrink-0 text-red-400 mt-0.5" />
          <span>{error}</span>
        </div>
      )}

      {assignedDesk ? (
        <div className="p-4 bg-emerald-950/40 border border-emerald-500/40 rounded-lg text-emerald-200 text-center">
          <CheckCircle className="w-10 h-10 text-emerald-400 mx-auto mb-2 animate-bounce" />
          <h2 className="text-lg font-bold text-white">Admission Approved!</h2>
          <p className="text-sm text-emerald-300 font-semibold mt-1">
            Desk #{assignedDesk.desk_number}: {assignedDesk.facility_name}
          </p>
          <p className="text-xs text-slate-400 mt-2">Redirecting to Live Race Desk...</p>
        </div>
      ) : (
        <div className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1">
              QR Token (JTI)
            </label>
            <input
              type="text"
              value={jti}
              onChange={(e) => setJti(e.target.value)}
              placeholder="e.g. 550e8400-e29b-41d4-a716-446655440000"
              className="w-full px-3 py-2 bg-slate-900 border border-slate-700 rounded-lg text-white font-mono text-sm focus:outline-none focus:border-indigo-500"
            />
          </div>

          <div className="p-3 bg-slate-900/60 rounded-lg border border-slate-700/60">
            <div className="flex items-center justify-between text-xs text-slate-400">
              <span className="flex items-center gap-1.5 font-medium text-slate-300">
                <Shield className="w-4 h-4 text-emerald-400" />
                Anti-Bot Verification
              </span>
              <span className="text-emerald-400 font-mono text-[11px]">
                {isLanMode ? 'LAN Bypass Active' : 'Cloudflare Turnstile'}
              </span>
            </div>
            <p className="text-[11px] text-slate-400 mt-1">
              {isLanMode
                ? 'Local / Hotspot mode active. Bot protection enforced by rotating 15s single-use JTI.'
                : 'Cloudflare Turnstile token validated by API gateway.'}
            </p>
          </div>

          <button
            onClick={handleJoin}
            disabled={loading}
            className="w-full py-3 px-4 bg-indigo-600 hover:bg-indigo-500 disabled:bg-slate-700 text-white font-semibold rounded-lg shadow flex items-center justify-center gap-2 transition"
          >
            {loading ? 'Admitting...' : 'Join as Receiving Desk'}
            <ArrowRight className="w-4 h-4" />
          </button>
        </div>
      )}
    </div>
  );
};

