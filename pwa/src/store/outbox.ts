import { openDB, DBSchema, IDBPDatabase } from 'idb';
import { v7 as uuidv7 } from 'uuid';

export interface OutboxItem {
  id: string;
  idemKey: string;
  url: string;
  cmd: any;
  createdAt: number;
  status: 'PENDING_NOT_CONFIRMED' | 'SENT' | 'FAILED';
  error?: string;
  httpStatus?: number;
}

interface RhpOutboxDB extends DBSchema {
  commands: {
    key: string;
    value: OutboxItem;
    indexes: { 'by-status': string; 'by-created': number };
  };
}

const DB_NAME = 'rhp_outbox_db';
const DB_VERSION = 1;

let dbPromise: Promise<IDBPDatabase<RhpOutboxDB>> | null = null;

function getDb(): Promise<IDBPDatabase<RhpOutboxDB>> {
  if (!dbPromise) {
    dbPromise = openDB<RhpOutboxDB>(DB_NAME, DB_VERSION, {
      upgrade(db) {
        if (!db.objectStoreNames.contains('commands')) {
          const store = db.createObjectStore('commands', { keyPath: 'id' });
          store.createIndex('by-status', 'status');
          store.createIndex('by-created', 'createdAt');
        }
      },
    });
  }
  return dbPromise;
}

export async function queueCommand(url: string, cmd: any, explicitIdemKey?: string): Promise<OutboxItem> {
  const db = await getDb();
  const id = uuidv7();
  const idemKey = explicitIdemKey || `idem-${id}`;
  const item: OutboxItem = {
    id,
    idemKey,
    url,
    cmd,
    createdAt: Date.now(),
    status: 'PENDING_NOT_CONFIRMED',
  };
  await db.put('commands', item);
  return item;
}

export async function getPendingCommands(): Promise<OutboxItem[]> {
  const db = await getDb();
  const all = await db.getAll('commands');
  return all
    .filter((it) => it.status === 'PENDING_NOT_CONFIRMED')
    .sort((a, b) => a.createdAt - b.createdAt);
}

export type OutboxListener = (items: OutboxItem[], bannerMessage?: string) => void;
const listeners = new Set<OutboxListener>();

export function subscribeOutbox(listener: OutboxListener): () => void {
  listeners.add(listener);
  getPendingCommands().then((items) => listener(items));
  return () => {
    listeners.delete(listener);
  };
}

function notifyListeners(bannerMessage?: string) {
  getPendingCommands().then((items) => {
    listeners.forEach((l) => l(items, bannerMessage));
  });
}

export async function flushOutbox(
  onConflictOrPrecondition?: (item: OutboxItem, status: number, response: any) => void
): Promise<number> {
  if (!navigator.onLine) {
    return 0;
  }
  const pending = await getPendingCommands();
  if (pending.length === 0) return 0;

  const db = await getDb();
  let processed = 0;

  for (const item of pending) {
    try {
      const resp = await fetch(item.url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Idempotency-Key': item.idemKey,
        },
        body: JSON.stringify(item.cmd),
      });

      if (resp.ok) {
        item.status = 'SENT';
        item.httpStatus = resp.status;
        await db.put('commands', item);
        processed++;
      } else if (resp.status === 409 || resp.status === 412) {
        const errJson = await resp.json().catch(() => ({}));
        item.status = 'FAILED';
        item.httpStatus = resp.status;
        item.error = errJson.detail || `Server returned ${resp.status}`;
        await db.put('commands', item);
        const bannerMsg = `Command rejected (${resp.status} ${item.error}): Local optimistic state replaced with authoritative server state.`;
        if (onConflictOrPrecondition) {
          onConflictOrPrecondition(item, resp.status, errJson);
        }
        notifyListeners(bannerMsg);
        processed++;
      } else {
        item.error = `HTTP ${resp.status}`;
        await db.put('commands', item);
        break; // Stop queue on network/server error to preserve ordering
      }
    } catch (err: any) {
      item.error = err?.message || 'Network fetch failed';
      await db.put('commands', item);
      break;
    }
  }

  notifyListeners();
  return processed;
}

if (typeof window !== 'undefined') {
  window.addEventListener('online', () => {
    flushOutbox();
  });
  window.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'visible' && navigator.onLine) {
      flushOutbox();
    }
  });
}

