// @vitest-environment jsdom
import { describe, it, expect, vi, beforeAll } from 'vitest';
import React from 'react';
import { render, screen } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { ModeBanner } from '../components/ModeBanner';
import { ArenaBigScreen } from './ArenaBigScreen';
import { JudgeJoin } from './JudgeJoin';
import { JudgeDesk } from './JudgeDesk';
import { ClinicianCard } from './ClinicianCard';
import { ReceivingDesk } from './ReceivingDesk';
import { AmbulancePwa } from './AmbulancePwa';
import { DispatcherConsole } from './DispatcherConsole';
import { CommandCentre } from './CommandCentre';

beforeAll(() => {
  // Mock global EventSource
  class MockEventSource {
    onopen: any = null;
    onmessage: any = null;
    onerror: any = null;
    addEventListener = vi.fn();
    removeEventListener = vi.fn();
    close = vi.fn();
  }
  global.EventSource = MockEventSource as any;

  // Mock global fetch for API endpoints
  global.fetch = vi.fn().mockImplementation((url: string) => {
    if (url.includes('/mode')) {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve({ broken_build: false, lan_mode: false, real_data: 0 }),
      });
    }
    if (url.includes('/healthz')) {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve({ components: {} }),
      });
    }
    if (url.includes('/v1/judge/qr-token')) {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve({ jti: 'test-jti-uuid' }),
      });
    }
    return Promise.resolve({
      ok: true,
      json: () => Promise.resolve([]),
    });
  });
});

describe('Module 7 & 8 Physical React Component Rendering Tests', () => {
  it('renders ModeBanner with synthetic data badge', async () => {
    render(<ModeBanner />);
    expect(screen.getByText(/SYNTHETIC DATA ONLY \(REAL_DATA=0\)/i)).toBeDefined();
    expect(screen.getByText(/Protocol RHP-1/i)).toBeDefined();
  });

  it('renders ArenaBigScreen with 16 Invariant tiles and dual ladders', async () => {
    render(<ArenaBigScreen />);
    expect(screen.getByText(/GREEN: ALL 16 INVARIANTS HOLDING/i)).toBeDefined();
    expect(screen.getByText(/HANDSHAKE TRACK \(hs_state\)/i)).toBeDefined();
    expect(screen.getByText(/TRANSPORT TRACK \(tr_state — Never blocks on HS\)/i)).toBeDefined();
    expect(screen.getByText(/Join Concurrency Race/i)).toBeDefined();
    expect(screen.getByText(/\[5\] Run 30s Live Proof Loop/i)).toBeDefined();
  });

  it('renders JudgeJoin with admission button and anti-bot verification', async () => {
    render(
      <BrowserRouter>
        <JudgeJoin />
      </BrowserRouter>
    );
    expect(screen.getByText(/Judge Admission Desk/i)).toBeDefined();
    expect(screen.getByText(/Join as Receiving Desk/i)).toBeDefined();
  });

  it('renders JudgeDesk with concurrency accept button and drawer', async () => {
    render(<JudgeDesk />);
    expect(screen.getByText(/Judge Live Concurrency Desk/i)).toBeDefined();
    expect(screen.getByText(/Inspect & Verify Cryptographic Proof/i)).toBeDefined();
  });

  it('renders ClinicianCard with ISBAR and answer-required MgSO4 block', async () => {
    render(<ClinicianCard />);
    expect(screen.getByText(/Referring Clinician Card Creator/i)).toBeDefined();
    expect(screen.getByText(/Pre-Referral MgSO4 Drug Safety \(Answer-Required\)/i)).toBeDefined();
    expect(screen.getByText(/UNKNOWN \(SAFE\)/i)).toBeDefined();
    expect(screen.getByText(/Dispatch Referral & Initiate Handshake/i)).toBeDefined();
  });

  it('renders ReceivingDesk with anti-Goodhart priority queue', async () => {
    render(<ReceivingDesk />);
    expect(screen.getByText(/Receiving Desk Queue/i)).toBeDefined();
    expect(screen.getByText(/Anti-Goodhart \(No Clocks\)/i)).toBeDefined();
  });

  it('renders AmbulancePwa with coordinates and en-route vitals', async () => {
    render(<AmbulancePwa />);
    expect(screen.getByText(/Ambulance KA-05-EM-1082/i)).toBeDefined();
    expect(screen.getByText(/Live Coordinates & Vitals Ingest/i)).toBeDefined();
    expect(screen.getByText(/En-Route Patient Vitals/i)).toBeDefined();
  });

  it('renders DispatcherConsole with action queue and command header', async () => {
    render(<DispatcherConsole />);
    expect(screen.getByText(/108 Dispatcher Console & Proxy Hub/i)).toBeDefined();
    expect(screen.getAllByText(/Action Queue/i).length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText(/Role: DISPATCHER \(Tier T1\)/i)).toBeDefined();
  });

  it('renders CommandCentre with APOT KPIs, capability ages, and k>=5 aggregations', async () => {
    render(<CommandCentre />);
    expect(screen.getByText(/District Command Centre & Analytics/i)).toBeDefined();
    expect(screen.getByText(/APOT Handover Latency/i)).toBeDefined();
    expect(screen.getByText(/Verified Capability Attestations/i)).toBeDefined();
    expect(screen.getByText(/Descriptive Network Graph \(Not Causal\)/i)).toBeDefined();
    expect(screen.getAllByText(/Privacy-Preserving Aggregations/i).length).toBeGreaterThanOrEqual(1);
  });
});
