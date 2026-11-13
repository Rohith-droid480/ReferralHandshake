/**
 * ReferralHandshake Protocol RHP-1 — Reactive SSE Stream Client
 * 
 * Specification Anchors:
 * - Architecture §9: Stream Authorization & GRANT_REVOKED Handling [Closure F10, Invariant I10]
 * - BUILD_PLAN §7.1: Real-Time SSE Synchronization & DOM Memory Scrubbing
 */

export interface ReferralSnapshot {
  id: string;
  hs_state: string;
  tr_state: string;
  lease_epoch: number;
  lease_facility_id: string | null;
  need_class?: string;
  mode?: string;
  mgso4_status?: string;
  paper_code?: string;
  open_offers?: number;
  clinical_payload?: Record<string, any> | null;
  offers: Record<string, any>;
  head_seq: number;
  updated_at: string;
  [key: string]: any;
}

export type ReferralSummary = ReferralSnapshot;

export interface SSEState {
  referrals: Record<string, ReferralSnapshot>;
}

export type SSEListener = (state: SSEState) => void;

class SSEClient {
  private eventSource: EventSource | null = null;
  private lastEventId: string | null = null;
  private referrals: Record<string, ReferralSnapshot> = {};
  private listeners: Set<SSEListener> = new Set();
  private isConnected = false;
  private reconnectTimer: any = null;

  constructor(private baseUrl: string = '/v1/stream') {}

  public subscribe(listener: SSEListener): () => void {
    this.listeners.add(listener);
    listener({ referrals: this.referrals });
    if (!this.isConnected && !this.eventSource) {
      this.connect();
    }
    return () => {
      this.listeners.delete(listener);
      if (this.listeners.size === 0) {
        this.disconnect();
      }
    };
  }

  public connect(): void {
    if (this.eventSource) {
      this.eventSource.close();
    }

    const url = new URL(this.baseUrl, window.location.origin);
    if (this.lastEventId) {
      url.searchParams.set('last_event_id', this.lastEventId);
    }

    try {
      this.eventSource = new EventSource(url.toString(), { withCredentials: true });

      this.eventSource.onopen = () => {
        this.isConnected = true;
      };

      this.eventSource.onerror = (err) => {
        this.isConnected = false;
        if (this.eventSource) {
          this.eventSource.close();
          this.eventSource = null;
        }
        if (!this.reconnectTimer) {
          this.reconnectTimer = setTimeout(() => {
            this.reconnectTimer = null;
            this.connect();
          }, 3000);
        }
      };

      this.eventSource.onmessage = (msg) => {
        if (msg.lastEventId) {
          this.lastEventId = msg.lastEventId;
        }
        if (msg.data.startsWith(':heartbeat')) {
          return;
        }
        try {
          const payload = JSON.parse(msg.data);
          this.processEvent(payload);
        } catch (e) {
          console.warn('Failed to parse SSE frame data', e);
        }
      };

      // Listen for custom event types
      const eventTypes = [
        'REFERRAL_CREATED',
        'OFFER_ACKED',
        'RESOURCE_CONFIRMED',
        'OFFER_ACCEPTED',
        'LEASE_GRANTED',
        'OFFER_COUNTERED',
        'OFFER_DECLINED',
        'TR_UPDATED',
        'ARRIVAL_SUGGESTED',
        'ARRIVAL_AT_NON_OWNER',
        'GRANT_REVOKED',
        'CLOSED',
        'CANCELLED',
      ];

      for (const evType of eventTypes) {
        this.eventSource.addEventListener(evType, (e: MessageEvent) => {
          if (e.lastEventId) {
            this.lastEventId = e.lastEventId;
          }
          try {
            const data = JSON.parse(e.data);
            this.processEvent({ type: evType, ...data });
          } catch (err) {
            console.warn(`Error handling ${evType} frame`, err);
          }
        });
      }
    } catch (e) {
      console.error('SSE connection initiation failed', e);
    }
  }

  public disconnect(): void {
    if (this.eventSource) {
      this.eventSource.close();
      this.eventSource = null;
    }
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    this.isConnected = false;
  }

  public processEvent(event: Record<string, any>): void {
    const refId = event.referral_id || (event.detail && event.detail.referral_id);
    if (!refId) return;

    if (!this.referrals[refId]) {
      this.referrals[refId] = {
        id: refId,
        hs_state: 'CREATED',
        tr_state: 'REQUESTED',
        lease_epoch: 0,
        lease_facility_id: null,
        offers: {},
        head_seq: event.seq || 0,
        updated_at: new Date().toISOString(),
      };
    }

    const current = this.referrals[refId];
    current.head_seq = Math.max(current.head_seq, event.seq || current.head_seq);
    current.updated_at = new Date().toISOString();

    const evType = event.type;
    const detail = event.detail || {};

    if (evType === 'REFERRAL_CREATED') {
      current.hs_state = 'OFFERED';
      current.need_class = detail.need_class;
      current.mgso4_status = detail.mgso4;
    } else if (evType === 'OFFER_ACKED') {
      current.hs_state = 'ACKNOWLEDGED';
    } else if (evType === 'RESOURCE_CONFIRMED') {
      // Confirmed capability
    } else if (evType === 'OFFER_ACCEPTED' || evType === 'LEASE_GRANTED') {
      current.hs_state = 'ACCEPTED';
      current.lease_facility_id = detail.facility || current.lease_facility_id;
      current.lease_epoch = detail.epoch !== undefined ? detail.epoch : current.lease_epoch + 1;
    } else if (evType === 'TR_UPDATED') {
      current.tr_state = detail.tr_state || current.tr_state;
    } else if (evType === 'GRANT_REVOKED') {
      // Invariant I10: Immediately scrub sensitive clinical payload from memory and DOM
      current.clinical_payload = null;
      delete (current as any).phi;
    } else if (evType === 'CLOSED' || evType === 'CANCELLED') {
      current.hs_state = evType;
    }

    this.notify();
  }

  private notify(): void {
    for (const listener of this.listeners) {
      listener({ referrals: { ...this.referrals } });
    }
  }

  public getReferral(refId: string): ReferralSnapshot | undefined {
    return this.referrals[refId];
  }
}

export const sseClient = new SSEClient();
