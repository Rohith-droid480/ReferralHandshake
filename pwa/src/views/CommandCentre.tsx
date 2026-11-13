import React, { useState, useEffect } from 'react';
import {
  Activity,
  Layers,
  ShieldCheck,
  TrendingUp,
  Clock,
  MapPin,
  EyeOff,
  Hospital,
  AlertCircle,
  Network,
} from 'lucide-react';

interface KPIState {
  median_ack_latency_s: number;
  p95_ack_latency_s: number;
  median_apot_handover_s: number;
  p95_apot_handover_s: number;
  unanswered_offer_rate: number;
  arrival_rejected_rate: number;
  total_referrals: number;
  total_offers: number;
  accepted_referrals: number;
}

interface CapabilityAttestation {
  facility_id: string;
  facility_name: string;
  capability: string;
  age_label: string;
  confirmed_at: string;
}

interface BucketedRow {
  facility_id: string;
  need_class: string;
  bucket_4h: string;
  count: string;
  is_suppressed: boolean;
}

export const CommandCentre: React.FC = () => {
  const [kpis, setKpis] = useState<KPIState>({
    median_ack_latency_s: 18.4,
    p95_ack_latency_s: 42.1,
    median_apot_handover_s: 114.0,
    p95_apot_handover_s: 240.0,
    unanswered_offer_rate: 0.045,
    arrival_rejected_rate: 0.0,
    total_referrals: 38,
    total_offers: 46,
    accepted_referrals: 36,
  });

  const [capabilities, setCapabilities] = useState<CapabilityAttestation[]>([
    {
      facility_id: '00000000-0000-0000-0000-000000000002',
      facility_name: 'CHC Ramanagara',
      capability: 'OT (Emergency Obstetric)',
      age_label: 'Attested 1h 12m ago',
      confirmed_at: new Date(Date.now() - 4320000).toISOString(),
    },
    {
      facility_id: '00000000-0000-0000-0000-000000000002',
      facility_name: 'CHC Ramanagara',
      capability: 'Blood Stock (O-ve, B+ve)',
      age_label: 'Attested 45m ago',
      confirmed_at: new Date(Date.now() - 2700000).toISOString(),
    },
    {
      facility_id: '00000000-0000-0000-0000-000000000003',
      facility_name: 'DH Mandya',
      capability: 'Specialist (Anaesthetist On-Duty)',
      age_label: 'Attested 2h 05m ago',
      confirmed_at: new Date(Date.now() - 7500000).toISOString(),
    },
    {
      facility_id: '00000000-0000-0000-0000-000000000003',
      facility_name: 'DH Mandya',
      capability: 'NICU Bed Available',
      age_label: 'Attested 30m ago',
      confirmed_at: new Date(Date.now() - 1800000).toISOString(),
    },
  ]);

  const [buckets, setBuckets] = useState<BucketedRow[]>([
    {
      facility_id: 'CHC Ramanagara',
      need_class: 'OB_ECLAMPSIA',
      bucket_4h: '2026-11-14 00:00',
      count: '<5',
      is_suppressed: true,
    },
    {
      facility_id: 'DH Mandya',
      need_class: 'OB_ECLAMPSIA',
      bucket_4h: '2026-11-14 00:00',
      count: '7',
      is_suppressed: false,
    },
    {
      facility_id: 'PHC Ramanagara',
      need_class: 'OB_PPH',
      bucket_4h: '2026-11-14 04:00',
      count: '<5',
      is_suppressed: true,
    },
  ]);

  const [networkNodes, setNetworkNodes] = useState([
    { id: 'PHC Ramanagara', betweenness: 0.12 },
    { id: 'CHC Ramanagara', betweenness: 0.65 },
    { id: 'DH Mandya', betweenness: 0.82 },
  ]);

  useEffect(() => {
    fetch('/v1/analytics/kpis')
      .then((r) => (r.ok ? r.json() : null))
      .then((data) => {
        if (data) setKpis(data);
      })
      .catch(() => {});

    fetch('/v1/analytics/capabilities')
      .then((r) => (r.ok ? r.json() : null))
      .then((data) => {
        if (Array.isArray(data)) setCapabilities(data);
      })
      .catch(() => {});

    fetch('/v1/analytics/buckets')
      .then((r) => (r.ok ? r.json() : null))
      .then((data) => {
        if (Array.isArray(data)) setBuckets(data);
      })
      .catch(() => {});
  }, []);

  return (
    <div className="max-w-6xl mx-auto p-4 sm:p-6 space-y-6">
      {/* Header */}
      <div className="bg-slate-800 rounded-xl border border-slate-700 p-5 shadow-lg flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-3 bg-emerald-600/20 text-emerald-400 rounded-xl border border-emerald-500/30">
            <Activity className="w-7 h-7" />
          </div>
          <div>
            <span className="text-[10px] font-mono text-emerald-400 uppercase tracking-wider block">
              District Health Operations
            </span>
            <h1 className="text-xl font-black text-white">District Command Centre & Analytics</h1>
            <p className="text-xs text-slate-400">
              Anti-Goodhart Bottleneck Intelligence & Privacy-Preserving Aggregations
            </p>
          </div>
        </div>
        <span className="text-xs font-mono font-bold px-3 py-1 bg-slate-900 text-indigo-300 border border-slate-700 rounded-lg">
          Strict Audit Log Derived
        </span>
      </div>

      {/* APOT-Separated KPIs (Separates arrival from acceptance!) */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-slate-800 p-4 rounded-xl border border-slate-700 space-y-1">
          <span className="text-[10px] text-slate-400 uppercase font-mono block">Median Time-to-ACK</span>
          <span className="text-2xl font-black text-white font-mono">{kpis.median_ack_latency_s}s</span>
          <span className="text-[10px] text-slate-500 block">p95: {kpis.p95_ack_latency_s}s</span>
        </div>

        <div className="bg-slate-800 p-4 rounded-xl border-2 border-emerald-500/50 space-y-1">
          <span className="text-[10px] text-emerald-400 uppercase font-mono font-bold block">
            APOT Handover Latency
          </span>
          <span className="text-2xl font-black text-emerald-300 font-mono">
            {kpis.median_apot_handover_s}s
          </span>
          <span className="text-[10px] text-slate-400 block">
            Physical Arrival → Handover (p95: {kpis.p95_apot_handover_s}s)
          </span>
        </div>

        <div className="bg-slate-800 p-4 rounded-xl border border-slate-700 space-y-1">
          <span className="text-[10px] text-slate-400 uppercase font-mono block">Unanswered Offer Rate</span>
          <span className="text-2xl font-black text-amber-400 font-mono">
            {(kpis.unanswered_offer_rate * 100).toFixed(1)}%
          </span>
          <span className="text-[10px] text-slate-500 block">Intra-facility escalation</span>
        </div>

        <div className="bg-slate-800 p-4 rounded-xl border border-slate-700 space-y-1">
          <span className="text-[10px] text-slate-400 uppercase font-mono block">Total Referrals</span>
          <span className="text-2xl font-black text-white font-mono">{kpis.total_referrals}</span>
          <span className="text-[10px] text-slate-500 block">
            Accepted: {kpis.accepted_referrals} ({((kpis.accepted_referrals / max(1, kpis.total_referrals)) * 100).toFixed(0)}%)
          </span>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Capability Attestations with Age (Never 'live beds') */}
        <div className="bg-slate-800 rounded-xl border border-slate-700 p-5 shadow-lg space-y-4">
          <div className="flex items-center justify-between border-b border-slate-700 pb-3">
            <h3 className="text-sm font-bold text-white flex items-center gap-2">
              <ShieldCheck className="w-4 h-4 text-emerald-400" />
              Verified Capability Attestations
            </h3>
            <span className="text-[10px] font-mono text-slate-400">Time-bounded TTL</span>
          </div>

          <div className="space-y-2 max-h-72 overflow-y-auto">
            {capabilities.map((c, i) => (
              <div
                key={i}
                className="p-3 bg-slate-900 rounded-lg border border-slate-700 flex items-center justify-between"
              >
                <div>
                  <span className="font-bold text-white text-xs block">{c.facility_name}</span>
                  <span className="text-[11px] text-indigo-300 font-mono">{c.capability}</span>
                </div>
                <div className="text-right">
                  <span className="text-[10px] font-bold px-2 py-0.5 bg-emerald-950 text-emerald-300 border border-emerald-600 rounded block">
                    {c.age_label}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Descriptive Referral Network Graph */}
        <div className="bg-slate-800 rounded-xl border border-slate-700 p-5 shadow-lg space-y-4">
          <div className="flex items-center justify-between border-b border-slate-700 pb-3">
            <h3 className="text-sm font-bold text-white flex items-center gap-2">
              <Network className="w-4 h-4 text-indigo-400" />
              Descriptive Network Graph (Not Causal)
            </h3>
            <span className="text-[10px] font-mono text-indigo-300">networkx DiGraph</span>
          </div>

          <p className="text-xs text-slate-400">
            Node betweenness centrality indicates routing concentration and bottleneck facilities:
          </p>

          <div className="space-y-2">
            {networkNodes.map((n, i) => (
              <div
                key={i}
                className="p-3 bg-slate-900 rounded-lg border border-slate-700 flex items-center justify-between"
              >
                <span className="text-xs font-bold text-white">{n.id}</span>
                <span className="text-xs font-mono font-bold text-emerald-400">
                  Centrality: {n.betweenness.toFixed(2)}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* 4-Hour Bucketed Privacy-Preserving Aggregations (k >= 5) */}
      <div className="bg-slate-800 rounded-xl border border-slate-700 p-5 shadow-lg space-y-4">
        <div className="flex items-center justify-between border-b border-slate-700 pb-3">
          <h3 className="text-sm font-bold text-white flex items-center gap-2">
            <EyeOff className="w-4 h-4 text-amber-400" />
            Privacy-Preserving Aggregations (4h Windows, k ≥ 5 Suppression)
          </h3>
          <span className="text-[10px] font-mono text-amber-300">Closure F9</span>
        </div>

        <p className="text-xs text-slate-400">
          Small-cell referral counts under 5 are masked to prevent patient re-identification:
        </p>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs font-mono">
            <thead>
              <tr className="border-b border-slate-700 text-slate-400 text-[11px]">
                <th className="py-2 px-3">Facility</th>
                <th className="py-2 px-3">Need Class</th>
                <th className="py-2 px-3">4h Window</th>
                <th className="py-2 px-3">Referrals</th>
                <th className="py-2 px-3">Privacy Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800">
              {buckets.map((b, i) => (
                <tr key={i} className="hover:bg-slate-750">
                  <td className="py-2.5 px-3 font-semibold text-white">{b.facility_id}</td>
                  <td className="py-2.5 px-3 text-indigo-300">{b.need_class}</td>
                  <td className="py-2.5 px-3 text-slate-400">{b.bucket_4h}</td>
                  <td className="py-2.5 px-3 font-bold text-emerald-400">{b.count}</td>
                  <td className="py-2.5 px-3">
                    {b.is_suppressed ? (
                      <span className="text-[10px] px-2 py-0.5 bg-amber-950 text-amber-300 border border-amber-600 rounded">
                        Suppressed (&lt;5)
                      </span>
                    ) : (
                      <span className="text-[10px] px-2 py-0.5 bg-emerald-950 text-emerald-300 border border-emerald-600 rounded">
                        Emitted (≥5)
                      </span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

function max(a: number, b: number): number {
  return a > b ? a : b;
}

