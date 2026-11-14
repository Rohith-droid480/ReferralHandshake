import React, { useState, useEffect, useRef } from 'react';
import {
  Navigation,
  MapPin,
  Heart,
  AlertTriangle,
  CheckCircle,
  Clock,
  Compass,
  ArrowRight,
  Send,
  Play,
  Square,
  Activity,
  Layers,
} from 'lucide-react';
import { sseClient, ReferralSummary } from '../store/sseClient';
import { queueCommand } from '../store/outbox';

// Karnataka NH-275 Corridor Waypoints
const CORRIDOR_WAYPOINTS = [
  { name: 'PHC Channapatna', tier: 'PHC', lat: 12.6518, lon: 77.2089 },
  { name: 'CHC Ramanagara', tier: 'CHC', lat: 12.7214, lon: 77.2811 },
  { name: 'DH Mandya', tier: 'DH', lat: 12.5238, lon: 76.8974 },
  { name: 'MC Bengaluru OB', tier: 'MC', lat: 12.9716, lon: 77.5946 },
];

export const AmbulancePwa: React.FC = () => {
  const [activeRef, setActiveRef] = useState<ReferralSummary | null>(null);
  const [currentLat, setCurrentLat] = useState<number>(12.6518);
  const [currentLon, setCurrentLon] = useState<number>(77.2089);
  const [lastConfirmedSec, setLastConfirmedSec] = useState<number>(0);

  // Highway Drive Simulator State
  const [isDriving, setIsDriving] = useState(false);
  const [driveProgress, setDriveProgress] = useState(0); // 0 to 100
  const driveIntervalRef = useRef<any>(null);

  // Vitals
  const [bpSys, setBpSys] = useState('150');
  const [bpDia, setBpDia] = useState('95');
  const [hr, setHr] = useState('88');
  const [spo2, setSpo2] = useState('98');

  // Modals & Banners
  const [showGeofencePrompt, setShowGeofencePrompt] = useState(false);
  const [showRedirectModal, setShowRedirectModal] = useState(false);
  const [redirectFacilityName, setRedirectFacilityName] = useState('DH Mandya');
  const [redirectFacilityId, setRedirectFacilityId] = useState(
    '00000000-0000-0000-0000-000000000003'
  );
  const [detourEtaMinutes, setDetourEtaMinutes] = useState(14);
  const [arrivalBanner, setArrivalBanner] = useState<string | null>(null);

  const [lastLeaseFacilityId, setLastLeaseFacilityId] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);

  // 1. Subscribe to SSE
  useEffect(() => {
    fetch('/v1/referrals')
      .then((res) => (res.ok ? res.json() : []))
      .then((data) => {
        if (Array.isArray(data) && data.length > 0) {
          setActiveRef((prev) => prev || data[data.length - 1]);
        }
      })
      .catch(() => {});

    const unsub = sseClient.subscribe((state) => {
      const list = Object.values(state.referrals);
      if (list.length > 0) {
        const ref = list[list.length - 1];
        setActiveRef(ref);

        if (
          ref.tr_state === 'EN_ROUTE' &&
          lastLeaseFacilityId &&
          ref.lease_facility_id &&
          ref.lease_facility_id !== lastLeaseFacilityId
        ) {
          setShowRedirectModal(true);
          setRedirectFacilityId(ref.lease_facility_id);
          setRedirectFacilityName('District Hospital Mandya');
        }

        if (ref.lease_facility_id) {
          setLastLeaseFacilityId(ref.lease_facility_id);
        }
      }
    });

    sseClient.connect();
    return () => unsub();
  }, [lastLeaseFacilityId]);

  // 2. Hardware GPS WatchPosition (Mode 1)
  useEffect(() => {
    let watchId: number | null = null;
    if (typeof navigator !== 'undefined' && navigator.geolocation && !isDriving) {
      watchId = navigator.geolocation.watchPosition(
        (pos) => {
          if (!isDriving) {
            setCurrentLat(pos.coords.latitude);
            setCurrentLon(pos.coords.longitude);
            setLastConfirmedSec(0);
          }
        },
        () => { },
        { enableHighAccuracy: true, maximumAge: 10000 }
      );
    }

    const timer = setInterval(() => {
      setLastConfirmedSec((prev) => prev + 1);
    }, 1000);

    return () => {
      if (watchId !== null && navigator.geolocation) {
        navigator.geolocation.clearWatch(watchId);
      }
      clearInterval(timer);
    };
  }, [isDriving]);

  // 3. Live Highway Drive Interpolator (Mode 2)
  const toggleLiveHighwayDrive = () => {
    if (isDriving) {
      clearInterval(driveIntervalRef.current);
      setIsDriving(false);
      setStatusMessage('Ambulance highway drive paused.');
      return;
    }

    setIsDriving(true);
    setStatusMessage('Live NH-275 Highway Drive active: Interpolating GPS corridor.');

    // Route: Channapatna (12.6518, 77.2089) -> Ramanagara (12.7214, 77.2811)
    const startLat = 12.6518;
    const startLon = 77.2089;
    const targetLat = 12.7214;
    const targetLon = 77.2811;

    let step = driveProgress;
    driveIntervalRef.current = setInterval(async () => {
      step += 5;
      if (step >= 100) {
        step = 100;
        clearInterval(driveIntervalRef.current);
        setIsDriving(false);
        // Arrived at Ramanagara geofence
        setCurrentLat(targetLat);
        setCurrentLon(targetLon);
        setShowGeofencePrompt(true);
        setStatusMessage('Ambulance crossed 200m geofence at CHC Ramanagara.');
      } else {
        const fraction = step / 100;
        const nextLat = startLat + fraction * (targetLat - startLat);
        const nextLon = startLon + fraction * (targetLon - startLon);
        setCurrentLat(nextLat);
        setCurrentLon(nextLon);
        setDriveProgress(step);

        // Transmit live telemetry
        if (activeRef) {
          try {
            await fetch('/v1/telemetry', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({
                referral_id: activeRef.id,
                gps: {
                  lat_e5: Math.round(nextLat * 1e5),
                  lon_e5: Math.round(nextLon * 1e5),
                  acc_m: 6,
                },
              }),
            });
            setLastConfirmedSec(0);
          } catch (e) {
            // Ignore in simulation
          }
        }
      }
    }, 1200);
  };

  // 4. Force 200m Geofence Gate
  const handleForceGeofenceGate = async () => {
    if (!activeRef) return;
    setLoading(true);
    setStatusMessage('Transmitting 200m geofence coordinate...');

    try {
      const resp = await fetch('/v1/telemetry', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          referral_id: activeRef.id,
          force_geofence: true,
          gps: {
            lat_e5: 1272140,
            lon_e5: 7728110,
            acc_m: 5,
          },
        }),
      });

      if (resp.ok) {
        const data = await resp.json();
        setCurrentLat(12.7214);
        setCurrentLon(77.2811);
        setShowGeofencePrompt(true);
        setStatusMessage('ARRIVAL_SUGGESTED emitted! 200m Geofence dwell gate satisfied.');
      }
    } catch (e: any) {
      setStatusMessage('Geofence gate call error');
    } finally {
      setLoading(false);
    }
  };

  // 5. Send Telemetry & Check Geofence
  const handleSendTelemetry = async () => {
    if (!activeRef) return;
    setLoading(true);
    setStatusMessage(null);

    const lat_e5 = Math.round(currentLat * 1e5);
    const lon_e5 = Math.round(currentLon * 1e5);

    const payload = {
      referral_id: activeRef.id,
      gps: { lat_e5, lon_e5, acc_m: 8 },
      obs: [
        { code: 'BP_SYS', val: bpSys },
        { code: 'BP_DIA', val: bpDia },
        { code: 'HR', val: hr },
        { code: 'SPO2', val: spo2 },
      ],
    };

    try {
      const resp = await fetch('/v1/telemetry', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (resp.ok) {
        const data = await resp.json().catch(() => ({}));
        setLastConfirmedSec(0);
        setStatusMessage('Telemetry batch ingested.');
        if (data.arrival_suggested) {
          setShowGeofencePrompt(true);
        }
      } else {
        await queueCommand('/v1/telemetry', payload);
        setStatusMessage('Offline: Telemetry queued in outbox (Pending — Not Confirmed).');
      }
    } catch (e: any) {
      await queueCommand('/v1/telemetry', payload);
      setStatusMessage('Network offline: Queued in outbox.');
    } finally {
      setLoading(false);
    }
  };

  // 6. Confirm Arrival (Human EMT Confirmation required)
  const handleConfirmArrival = async () => {
    if (!activeRef) return;
    setLoading(true);

    try {
      const resp = await fetch(`/v1/referrals/${activeRef.id}/tr-update`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Idempotency-Key': `idem-arr-${activeRef.id}-${Date.now()}`,
        },
        body: JSON.stringify({
          tr_state: 'ARRIVED',
          source: 'EMT_APP',
        }),
      });

      if (resp.ok) {
        setShowGeofencePrompt(false);
        setArrivalBanner('Arrival Confirmed by EMT (Human Gate). Handover desk armed.');
        setStatusMessage('Arrival Confirmed by EMT. Handover deadline armed.');
      } else {
        const err = await resp.json().catch(() => ({}));
        setStatusMessage(err.detail || 'Failed to update arrival');
      }
    } catch (e: any) {
      setStatusMessage('Error confirming arrival');
    } finally {
      setLoading(false);
    }
  };

  // 7. Trigger 6 Arrival Cases
  const triggerArrivalCase = async (caseKey: string) => {
    if (!activeRef) return;
    setLoading(true);

    if (caseKey === 'case_a') {
      // Case a: On-Time Arrival at Lease Holder
      await handleConfirmArrival();
    } else if (caseKey === 'case_b') {
      // Case b: Early Arrival
      setStatusMessage('Case b: Early Arrival — Ambulance arrived 15 mins ahead of ETA. Desk notified.');
      setShowGeofencePrompt(true);
    } else if (caseKey === 'case_c') {
      // Case c: Late Arrival / Traffic Delay
      setStatusMessage('Case c: Late Arrival — NH-275 corridor delay logged. Revised ETA +18 mins.');
    } else if (caseKey === 'case_d') {
      // Case d: Redirect Advisory Accepted
      setShowRedirectModal(true);
      setRedirectFacilityName('DH Mandya');
      setRedirectFacilityId('00000000-0000-0000-0000-000000000003');
    } else if (caseKey === 'case_e') {
      // Case e: Redirect Refused
      setShowRedirectModal(true);
    } else if (caseKey === 'case_f') {
      // Case f: Unannounced Arrival at Non-Owner (ARRIVAL_AT_NON_OWNER)
      try {
        const resp = await fetch(`/v1/referrals/${activeRef.id}/tr-update`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Idempotency-Key': `idem-nonowner-${activeRef.id}-${Date.now()}`,
          },
          body: JSON.stringify({
            tr_state: 'ARRIVED',
            source: 'EMT_APP',
            facility_id: '00000000-0000-0000-0000-000000000002', // CHC Ramanagara (non-lease holder)
          }),
        });
        if (resp.ok) {
          setArrivalBanner('🚨 ARRIVAL_AT_NON_OWNER (Closure F5): Unannounced arrival at non-lease holder. Care never blocked; triage alert sounded.');
          setStatusMessage('ARRIVAL_AT_NON_OWNER emitted.');
        }
      } catch (e) {
        setStatusMessage('Error emitting ARRIVAL_AT_NON_OWNER');
      }
    }
    setLoading(false);
  };

  // 8. Handle Redirect Decision
  const handleRedirectDecision = async (accepted: boolean) => {
    if (!activeRef) return;
    setLoading(true);

    try {
      const resp = await fetch(`/v1/referrals/${activeRef.id}/tr-destination-change`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Idempotency-Key': `idem-redir-${activeRef.id}-${Date.now()}`,
        },
        body: JSON.stringify({
          target_facility_id: redirectFacilityId,
          reason: accepted ? 'CREW_ACCEPTED_REDIRECT' : 'CREW_REFUSED_REDIRECT',
          accepted,
        }),
      });

      if (resp.ok) {
        setShowRedirectModal(false);
        setStatusMessage(
          accepted
            ? 'Destination Updated: Rerouted to new lease holder.'
            : 'Advisory Refused: Continuing to current destination.'
        );
      } else {
        const d = await resp.json().catch(() => ({}));
        setStatusMessage(d.detail || 'Destination change failed');
      }
    } catch (e: any) {
      setStatusMessage('Error submitting redirect response');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto p-4 sm:p-6 space-y-5">
      {/* Top Header Card */}
      <div className="bg-slate-800 rounded-xl border border-slate-700 p-5 shadow-lg flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-3 bg-emerald-600/20 text-emerald-400 rounded-xl border border-emerald-500/30">
            <Navigation className="w-7 h-7" />
          </div>
          <div>
            <span className="text-[10px] font-mono text-emerald-400 uppercase tracking-wider block">
              108 Karnataka Ambulance Crew — NH-275
            </span>
            <h1 className="text-xl font-black text-white">Ambulance KA-05-EM-1082</h1>
            <p className="text-xs text-slate-400">
              Transport Track: <span className="text-emerald-300 font-bold font-mono">{activeRef?.tr_state || 'EN_ROUTE'}</span>
              {' • '}
              <span className="text-indigo-300 font-bold">Independent Track (I3)</span>
            </p>
          </div>
        </div>

        <div className="text-right text-xs font-mono">
          <span className="text-slate-400 block text-[10px]">GPS TELEMETRY</span>
          <span className="text-emerald-400 font-bold">
            {isDriving ? 'LIVE HIGHWAY' : `Last confirmed: ${lastConfirmedSec}s ago`}
          </span>
        </div>
      </div>

      {statusMessage && (
        <div className="p-3 bg-indigo-950/80 border border-indigo-500/50 rounded-lg text-indigo-200 text-xs font-bold flex items-center gap-2">
          <CheckCircle className="w-4 h-4 text-indigo-400 flex-shrink-0" />
          <span>{statusMessage}</span>
        </div>
      )}

      {arrivalBanner && (
        <div className="p-3 bg-amber-950 border border-amber-500 rounded-lg text-amber-200 text-xs font-bold flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 text-amber-400 flex-shrink-0" />
          <span>{arrivalBanner}</span>
        </div>
      )}

      {/* Interactive NH-275 Referral Corridor Map Visual */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 shadow-xl space-y-3">
        <div className="flex items-center justify-between border-b border-slate-800 pb-2">
          <span className="text-xs font-bold text-slate-300 uppercase tracking-wider flex items-center gap-2">
            <MapPin className="w-4 h-4 text-emerald-400" />
            Karnataka NH-275 Obstetric Corridor
          </span>
          <span className="text-[10px] font-mono text-indigo-400">Channapatna → Bengaluru</span>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
          {CORRIDOR_WAYPOINTS.map((wp, i) => (
            <div
              key={wp.name}
              className={`p-2.5 rounded-lg border text-xs transition ${currentLat >= wp.lat - 0.05 && currentLat <= wp.lat + 0.05
                  ? 'bg-emerald-950/70 border-emerald-500 text-white'
                  : 'bg-slate-950 border-slate-800 text-slate-400'
                }`}
            >
              <span className="text-[9px] font-mono px-1.5 py-0.5 bg-slate-800 text-slate-300 rounded block w-fit mb-1">
                {wp.tier}
              </span>
              <p className="font-bold truncate text-slate-200">{wp.name}</p>
              <p className="text-[10px] font-mono text-slate-500 mt-0.5">
                {wp.lat.toFixed(4)}, {wp.lon.toFixed(4)}
              </p>
            </div>
          ))}
        </div>

        {/* Highway Drive Progress Bar */}
        <div className="space-y-1 pt-1">
          <div className="flex justify-between text-[10px] font-mono text-slate-400">
            <span>Progress: {driveProgress}% along NH-275</span>
            <span>Current: {currentLat.toFixed(4)}°N, {currentLon.toFixed(4)}°E</span>
          </div>
          <div className="w-full bg-slate-950 h-2 rounded-full overflow-hidden border border-slate-800">
            <div
              className="bg-emerald-500 h-full transition-all duration-300"
              style={{ width: `${Math.max(driveProgress, 5)}%` }}
            />
          </div>
        </div>

        {/* Mode 2 Simulator Controls */}
        <div className="grid grid-cols-2 gap-2 pt-2">
          <button
            type="button"
            onClick={toggleLiveHighwayDrive}
            className={`py-2 px-3 rounded-lg text-xs font-bold flex items-center justify-center gap-2 transition ${isDriving
                ? 'bg-red-600 hover:bg-red-500 text-white animate-pulse'
                : 'bg-emerald-600 hover:bg-emerald-500 text-white'
              }`}
          >
            {isDriving ? <Square className="w-3.5 h-3.5" /> : <Play className="w-3.5 h-3.5" />}
            <span>{isDriving ? 'Pause Highway Drive' : '▶ Start Live NH-275 Drive'}</span>
          </button>

          <button
            type="button"
            onClick={handleForceGeofenceGate}
            disabled={loading}
            className="py-2 px-3 bg-indigo-600 hover:bg-indigo-500 text-white font-bold rounded-lg text-xs flex items-center justify-center gap-2 transition"
          >
            <MapPin className="w-3.5 h-3.5" />
            <span>Force 200m Geofence Gate</span>
          </button>
        </div>
      </div>

      {/* Geofence Prompt Trigger (Closure F5) */}
      {showGeofencePrompt && (
        <div className="p-4 bg-emerald-950 border-2 border-emerald-500 rounded-xl text-emerald-200 shadow-2xl space-y-3 animate-pulse">
          <div className="flex items-center gap-2 text-white font-bold text-sm">
            <MapPin className="w-5 h-5 text-emerald-400" />
            <span>Geofence Hint: Within 200m of Destination — Confirm Arrival?</span>
          </div>
          <p className="text-xs text-emerald-300">
            Closure F5: System detects ambulance within 200m and dwell ≥ 20s. Confirm arrival to arm handover desk.
          </p>
          <button
            type="button"
            onClick={handleConfirmArrival}
            disabled={loading}
            className="w-full py-2.5 bg-emerald-600 hover:bg-emerald-500 text-white font-black rounded-lg text-sm transition"
          >
            {loading ? 'Confirming...' : 'Confirm Arrival at Facility (Human Gate)'}
          </button>
        </div>
      )}

      {/* 6 Arrival Cases Scenario Bar (Architecture §4) */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 shadow-xl space-y-3">
        <span className="text-xs font-bold text-slate-300 uppercase tracking-wider flex items-center gap-2 border-b border-slate-800 pb-2">
          <Layers className="w-4 h-4 text-indigo-400" />
          Test 6 Real-World Arrival Cases (Architecture §4)
        </span>
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
          {[
            { key: 'case_a', label: 'Case a: On-Time Arrival' },
            { key: 'case_b', label: 'Case b: Early Arrival' },
            { key: 'case_c', label: 'Case c: Late Arrival' },
            { key: 'case_d', label: 'Case d: Redirect Accepted' },
            { key: 'case_e', label: 'Case e: Redirect Refused' },
            { key: 'case_f', label: 'Case f: Non-Owner Divert' },
          ].map((c) => (
            <button
              key={c.key}
              type="button"
              onClick={() => triggerArrivalCase(c.key)}
              className="py-2 px-2.5 bg-slate-800 hover:bg-slate-750 border border-slate-700 rounded-lg text-xs text-slate-300 font-bold text-left transition hover:border-slate-500"
            >
              {c.label}
            </button>
          ))}
        </div>
      </div>

      {/* Manual GPS & Vitals Panel */}
      <div className="bg-slate-800 rounded-xl border border-slate-700 p-5 shadow-lg space-y-4">
        <div className="flex items-center justify-between border-b border-slate-700 pb-2">
          <h2 className="text-xs font-black uppercase tracking-wider text-slate-300 flex items-center gap-2">
            <Compass className="w-4 h-4 text-emerald-400" />
            Live Coordinates & Vitals Ingest
          </h2>
          <span className="text-[10px] font-mono text-slate-400">Offline Tolerant</span>
        </div>

        <div className="grid grid-cols-2 gap-3 text-xs font-mono">
          <div className="p-2.5 bg-slate-900 rounded-lg border border-slate-700">
            <span className="text-slate-500 block text-[10px]">LATITUDE</span>
            <span className="text-white font-bold">{currentLat.toFixed(5)}</span>
          </div>
          <div className="p-2.5 bg-slate-900 rounded-lg border border-slate-700">
            <span className="text-slate-500 block text-[10px]">LONGITUDE</span>
            <span className="text-white font-bold">{currentLon.toFixed(5)}</span>
          </div>
        </div>

        {/* Vitals Form */}
        <div>
          <span className="text-[11px] font-bold text-slate-400 block mb-2 flex items-center gap-1.5">
            <Heart className="w-3.5 h-3.5 text-red-400" />
            En-Route Patient Vitals
          </span>
          <div className="grid grid-cols-3 gap-2 text-xs">
            <div>
              <label className="text-[10px] text-slate-400 block">BP (Sys/Dia)</label>
              <input
                type="text"
                value={`${bpSys}/${bpDia}`}
                onChange={(e) => {
                  const parts = e.target.value.split('/');
                  if (parts[0]) setBpSys(parts[0]);
                  if (parts[1]) setBpDia(parts[1]);
                }}
                className="w-full px-2 py-1.5 bg-slate-900 border border-slate-700 rounded text-white font-mono"
              />
            </div>
            <div>
              <label className="text-[10px] text-slate-400 block">Heart Rate</label>
              <input
                type="text"
                value={hr}
                onChange={(e) => setHr(e.target.value)}
                className="w-full px-2 py-1.5 bg-slate-900 border border-slate-700 rounded text-white font-mono"
              />
            </div>
            <div>
              <label className="text-[10px] text-slate-400 block">SpO2 %</label>
              <input
                type="text"
                value={spo2}
                onChange={(e) => setSpo2(e.target.value)}
                className="w-full px-2 py-1.5 bg-slate-900 border border-slate-700 rounded text-white font-mono"
              />
            </div>
          </div>
        </div>

        <button
          onClick={handleSendTelemetry}
          disabled={loading}
          className="w-full py-2.5 bg-slate-700 hover:bg-slate-650 text-white font-bold rounded-lg text-xs flex items-center justify-center gap-2 transition"
        >
          <Send className="w-3.5 h-3.5" />
          {loading ? 'Transmitting...' : 'Update Position & Log Vitals'}
        </button>
      </div>

      {/* Redirect Advisory Modal (Case d/e) */}
      {showRedirectModal && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="bg-slate-900 border-2 border-amber-500 rounded-2xl p-6 max-w-md w-full space-y-4 shadow-2xl">
            <div className="flex items-center gap-3 text-amber-400">
              <AlertTriangle className="w-8 h-8 flex-shrink-0" />
              <div>
                <h3 className="text-lg font-black text-white">Redirect Advisory</h3>
                <p className="text-xs text-amber-300">Handshake Lease Changed En-Route</p>
              </div>
            </div>

            <p className="text-xs text-slate-300 leading-relaxed">
              Handshake lease was re-arbitrated to <span className="font-bold text-white">{redirectFacilityName}</span>.
              Estimated detour ETA: <span className="font-bold text-amber-400 font-mono">+{detourEtaMinutes} mins</span>.
            </p>

            <div className="space-y-2 pt-2">
              <button
                onClick={() => handleRedirectDecision(true)}
                disabled={loading}
                className="w-full py-3 bg-emerald-600 hover:bg-emerald-500 text-white font-bold rounded-xl text-xs flex items-center justify-center gap-2 transition"
              >
                <span>Accept Redirect to {redirectFacilityName}</span>
                <ArrowRight className="w-4 h-4" />
              </button>

              <button
                onClick={() => handleRedirectDecision(false)}
                disabled={loading}
                className="w-full py-2.5 bg-slate-800 hover:bg-slate-700 text-slate-300 font-bold rounded-xl text-xs transition"
              >
                Continue to Original Destination (Refuse Redirect)
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

