/**
 * ReferralHandshake Protocol RHP-1 — Pure-JS Browser Verifier
 * 
 * Specification Anchors:
 * - Architecture §11: Integrity, Merkle Proofs & Independent Witnesses [F8]
 * - Invariant I5: Hash Chaining & Append-Only Log
 * - BUILD_PLAN §6.3: Pure-JS Browser Verifier (@noble)
 * 
 * Runs on judge phones, Guarantee Arena screens, and browser clients.
 * Uses pure-JS @noble/curves/ed25519 and @noble/hashes/sha256 to verify:
 * 1. Checkpoint signature with pinned witness key -> else CHECKPOINT_SIG
 * 2. Hash chain from genesis -> at first mismatch BROKEN referral=<id> seq=<n> kind=PREV|HASH; missing seq -> SEQ_GAP
 * 3. Binary Merkle inclusion proof folded to root -> else ROOT_MISMATCH
 * 4. Truncation detection -> TRUNCATED at seq=<k> unless valid cold-key RESTORE record covers it.
 */

import { ed25519 } from '@noble/curves/ed25519';
import { sha256 } from '@noble/hashes/sha256';

export interface EventCore {
  referral_id: string;
  seq: number;
  event_id: string;
  type: string;
  epoch: number;
  actor_roster_id: string | null;
  actor_facility_id: string | null;
  channel: string;
  proxy: boolean;
  detail: Record<string, any>;
  secret_hash: string | null;
  client_ts_ms: number | null;
  server_ts_us: number;
}

export interface EventRow extends EventCore {
  prev_hash: string; // 64-char hex
  hash: string;      // 64-char hex
  server_ts?: string;
  proxy_for?: string | null;
}

export interface MerklePathItem {
  side: 'L' | 'R';
  hash: string; // 64-char hex or base64
}

export interface InclusionProof {
  referral_id: string;
  head_seq: number;
  head_hash: string; // 64-char hex or base64
  leaf_index: number;
  tree_size: number;
  path: MerklePathItem[];
  checkpoint_id: number;
}

export interface CheckpointData {
  id: number;
  tree_size: number;
  root_hash: string; // hex or base64
  root_hash_b64?: string;
  signature: string; // hex or base64
  signer_key_id?: string;
  taken_at?: string;
  note_text?: string;
  deployment?: string;
  kind?: 'REGULAR' | 'RESTORE';
  restore_from?: number | null;
  cold_signature?: string | null;
}

export interface VerificationResult {
  ok: boolean;
  error?: string;
  message?: string;
  verifiedSeq?: number;
  leafIndex?: number;
  treeSize?: number;
}

// ============================================================================
// Encoding & Binary Utility Helpers
// ============================================================================

export function hexToBytes(hex: string): Uint8Array {
  const clean = hex.startsWith('0x') ? hex.slice(2) : hex;
  if (clean.length % 2 !== 0) {
    throw new Error(`Invalid hex string length: ${hex}`);
  }
  const bytes = new Uint8Array(clean.length / 2);
  for (let i = 0; i < clean.length; i += 2) {
    bytes[i / 2] = parseInt(clean.substring(i, i + 2), 16);
  }
  return bytes;
}

export function bytesToHex(bytes: Uint8Array): string {
  let hex = '';
  for (let i = 0; i < bytes.length; i++) {
    hex += bytes[i].toString(16).padStart(2, '0');
  }
  return hex;
}

export function base64ToBytes(b64: string): Uint8Array {
  const binary = atob(b64);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) {
    bytes[i] = binary.charCodeAt(i);
  }
  return bytes;
}

export function bytesToBase64(bytes: Uint8Array): string {
  let binary = '';
  for (let i = 0; i < bytes.length; i++) {
    binary += String.fromCharCode(bytes[i]);
  }
  return btoa(binary);
}

export function arraysEqual(a: Uint8Array, b: Uint8Array): boolean {
  if (a.length !== b.length) return false;
  for (let i = 0; i < a.length; i++) {
    if (a[i] !== b[i]) return false;
  }
  return true;
}

export function uuidToBytes(uuidStr: string): Uint8Array {
  const clean = uuidStr.replace(/-/g, '').toLowerCase();
  if (clean.length !== 32) {
    throw new Error(`Invalid UUID string: ${uuidStr}`);
  }
  return hexToBytes(clean);
}

export function int64ToBigEndianBytes(n: number | bigint): Uint8Array {
  const buf = new Uint8Array(8);
  const view = new DataView(buf.buffer);
  view.setBigInt64(0, BigInt(n), false);
  return buf;
}

// ============================================================================
// RFC 8785 JSON Canonicalization Scheme (JCS)
// ============================================================================

export function canonicalJcs(obj: any): string {
  if (obj === null || obj === undefined) {
    return 'null';
  }
  if (typeof obj === 'number') {
    if (!Number.isInteger(obj)) {
      throw new Error(`Non-integer floating point number forbidden in canonical JCS: ${obj}`);
    }
    return obj.toString();
  }
  if (typeof obj === 'boolean') {
    return obj ? 'true' : 'false';
  }
  if (typeof obj === 'string') {
    return JSON.stringify(obj);
  }
  if (Array.isArray(obj)) {
    return '[' + obj.map(canonicalJcs).join(',') + ']';
  }
  if (typeof obj === 'object') {
    const keys = Object.keys(obj).sort();
    return '{' + keys.map(k => `${JSON.stringify(k)}:${canonicalJcs(obj[k])}`).join(',') + '}';
  }
  throw new Error(`Unsupported type in canonical JCS: ${typeof obj}`);
}

// ============================================================================
// Merkle Tree & Leaf Hash Calculation
// ============================================================================

/**
 * Computes binary Merkle tree leaf hash:
 * Leaf = SHA256(0x00 || referral_id(16B) || head_seq(8B BE) || head_hash(32B))
 */
export function computeLeafHash(
  referralId: string,
  headSeq: number | bigint,
  headHash: string | Uint8Array
): Uint8Array {
  const prefix = new Uint8Array([0x00]);
  const idBytes = uuidToBytes(referralId);
  const seqBytes = int64ToBigEndianBytes(headSeq);
  const hashBytes = typeof headHash === 'string'
    ? (headHash.length === 64 ? hexToBytes(headHash) : base64ToBytes(headHash))
    : headHash;

  const totalLen = prefix.length + idBytes.length + seqBytes.length + hashBytes.length;
  const combined = new Uint8Array(totalLen);
  let offset = 0;
  combined.set(prefix, offset); offset += prefix.length;
  combined.set(idBytes, offset); offset += idBytes.length;
  combined.set(seqBytes, offset); offset += seqBytes.length;
  combined.set(hashBytes, offset);

  return sha256(combined);
}

/**
 * Folds a Merkle inclusion proof path to derive the candidate root hash:
 * node = SHA256(0x01 || left || right)
 */
export function foldMerkleProof(
  leafHash: Uint8Array,
  path: MerklePathItem[]
): Uint8Array {
  let curr = leafHash;
  for (const step of path) {
    const sibling = typeof step.hash === 'string'
      ? (step.hash.length === 64 ? hexToBytes(step.hash) : base64ToBytes(step.hash))
      : step.hash;

    const nodeBuf = new Uint8Array(1 + 32 + 32);
    nodeBuf[0] = 0x01; // interior node prefix
    if (step.side === 'L') {
      nodeBuf.set(sibling, 1);
      nodeBuf.set(curr, 33);
    } else {
      nodeBuf.set(curr, 1);
      nodeBuf.set(sibling, 33);
    }
    curr = sha256(nodeBuf);
  }
  return curr;
}

// ============================================================================
// Cryptographic Signature Verification
// ============================================================================

export function verifyCheckpointSignature(
  checkpoint: CheckpointData,
  witnessPubKeyHex: string
): boolean {
  try {
    const pubKey = hexToBytes(witnessPubKeyHex);
    let noteText = checkpoint.note_text;
    if (!noteText) {
      const rootB64 = checkpoint.root_hash_b64 || bytesToBase64(
        typeof checkpoint.root_hash === 'string' && checkpoint.root_hash.length === 64
          ? hexToBytes(checkpoint.root_hash)
          : base64ToBytes(checkpoint.root_hash)
      );
      const deployment = checkpoint.deployment || 'colossus3-bengaluru-demo';
      noteText = `rhp1/${deployment}\n${checkpoint.tree_size}\n${rootB64}\n`;
    }

    const noteBytes = new TextEncoder().encode(noteText);
    const sigBytes = typeof checkpoint.signature === 'string'
      ? (checkpoint.signature.length === 128 ? hexToBytes(checkpoint.signature) : base64ToBytes(checkpoint.signature))
      : checkpoint.signature;

    return ed25519.verify(sigBytes, noteBytes, pubKey);
  } catch (err) {
    return false;
  }
}

export function verifyRestoreSignature(
  checkpoint: CheckpointData,
  coldPubKeyHex: string
): boolean {
  if (!checkpoint.cold_signature || !checkpoint.restore_from) {
    return false;
  }
  try {
    const coldPub = hexToBytes(coldPubKeyHex);
    const coldSig = checkpoint.cold_signature.length === 128
      ? hexToBytes(checkpoint.cold_signature)
      : base64ToBytes(checkpoint.cold_signature);

    const rootHex = typeof checkpoint.root_hash === 'string' && checkpoint.root_hash.length === 64
      ? checkpoint.root_hash.toLowerCase()
      : bytesToHex(base64ToBytes(checkpoint.root_hash));

    const payload = canonicalJcs({
      checkpoint_id: checkpoint.restore_from,
      kind: 'RESTORE',
      root_hash: rootHex,
      taken_at: checkpoint.taken_at || '',
      tree_size: checkpoint.tree_size,
    });

    const payloadBytes = new TextEncoder().encode(payload);
    if (ed25519.verify(coldSig, payloadBytes, coldPub)) {
      return true;
    }

    // Also try alternative note format
    const altNote = `rhp1/restore/${checkpoint.restore_from}\n${checkpoint.tree_size}\n${rootHex}\n`;
    return ed25519.verify(coldSig, new TextEncoder().encode(altNote), coldPub);
  } catch (err) {
    return false;
  }
}

// ============================================================================
// Event Hash Chain Verification
// ============================================================================

export function verifyEventHashChain(
  referralId: string,
  events: EventRow[]
): { ok: boolean; error?: string; message?: string; lastSeq: number; lastHash: string } {
  let prevHash = new Uint8Array(32); // 32 zeros
  let expectedSeq = 1;

  for (const ev of events) {
    if (ev.seq !== expectedSeq) {
      return {
        ok: false,
        error: 'SEQ_GAP',
        message: `SEQ_GAP expected seq=${expectedSeq} got=${ev.seq}`,
        lastSeq: expectedSeq - 1,
        lastHash: bytesToHex(prevHash),
      };
    }

    const evPrev = hexToBytes(ev.prev_hash);
    if (!arraysEqual(evPrev, prevHash)) {
      return {
        ok: false,
        error: 'CHAIN_BROKEN',
        message: `BROKEN referral=${referralId} seq=${ev.seq} kind=PREV expected=${bytesToHex(prevHash)} got=${ev.prev_hash}`,
        lastSeq: ev.seq,
        lastHash: ev.hash,
      };
    }

    const core: EventCore = {
      actor_facility_id: ev.actor_facility_id ?? null,
      actor_roster_id: ev.actor_roster_id ?? null,
      channel: ev.channel,
      client_ts_ms: ev.client_ts_ms ?? null,
      detail: ev.detail ?? {},
      epoch: ev.epoch,
      event_id: ev.event_id,
      proxy: ev.proxy,
      referral_id: ev.referral_id,
      secret_hash: ev.secret_hash ?? null,
      seq: ev.seq,
      server_ts_us: ev.server_ts_us,
      type: ev.type,
    };

    const jcsBytes = new TextEncoder().encode(canonicalJcs(core));
    const combined = new Uint8Array(prevHash.length + jcsBytes.length);
    combined.set(prevHash, 0);
    combined.set(jcsBytes, prevHash.length);
    const computedHash = sha256(combined);

    if (bytesToHex(computedHash) !== ev.hash.toLowerCase()) {
      return {
        ok: false,
        error: 'CHAIN_BROKEN',
        message: `BROKEN referral=${referralId} seq=${ev.seq} kind=HASH expected=${bytesToHex(computedHash)} got=${ev.hash}`,
        lastSeq: ev.seq,
        lastHash: ev.hash,
      };
    }

    prevHash = computedHash;
    expectedSeq++;
  }

  return {
    ok: true,
    lastSeq: events.length,
    lastHash: bytesToHex(prevHash),
  };
}

// ============================================================================
// Comprehensive Referral Integrity Verifier
// ============================================================================

export interface ReferralIntegrityOptions {
  referralId: string;
  events: EventRow[];
  inclusionProof: InclusionProof;
  checkpoint: CheckpointData;
  witnessPubKeyHex: string;
  coldPubKeyHex?: string;
}

export function verifyReferralIntegrity({
  referralId,
  events,
  inclusionProof,
  checkpoint,
  witnessPubKeyHex,
  coldPubKeyHex,
}: ReferralIntegrityOptions): VerificationResult {
  // Step 1: Verify checkpoint signature
  if (!verifyCheckpointSignature(checkpoint, witnessPubKeyHex)) {
    return {
      ok: false,
      error: 'CHECKPOINT_SIG',
      message: 'CHECKPOINT_SIG: Invalid witness Ed25519 signature on checkpoint',
    };
  }

  // Step 2: Verify event hash chain
  const chainRes = verifyEventHashChain(referralId, events);
  if (!chainRes.ok) {
    return {
      ok: false,
      error: chainRes.error,
      message: chainRes.message,
    };
  }

  // Step 3: Verify Merkle inclusion proof
  const leafHash = computeLeafHash(
    referralId,
    inclusionProof.head_seq,
    inclusionProof.head_hash
  );
  const derivedRoot = foldMerkleProof(leafHash, inclusionProof.path);
  const expectedRoot = typeof checkpoint.root_hash === 'string' && checkpoint.root_hash.length === 64
    ? hexToBytes(checkpoint.root_hash)
    : base64ToBytes(checkpoint.root_hash);

  if (!arraysEqual(derivedRoot, expectedRoot)) {
    return {
      ok: false,
      error: 'ROOT_MISMATCH',
      message: 'ROOT_MISMATCH: Computed Merkle root does not match signed checkpoint root',
    };
  }

  // Step 4: Live chain sequence vs checkpoint head sequence (Truncation check)
  if (chainRes.lastSeq < inclusionProof.head_seq) {
    // Regression/truncation detected
    const isColdRestoreValid = checkpoint.kind === 'RESTORE' &&
      coldPubKeyHex &&
      verifyRestoreSignature(checkpoint, coldPubKeyHex);

    const hasRestoreEvent = events.some(e => e.type === 'RESTORE');

    if (!isColdRestoreValid || !hasRestoreEvent) {
      return {
        ok: false,
        error: `TRUNCATED at seq=${inclusionProof.head_seq}`,
        message: `TRUNCATED at seq=${inclusionProof.head_seq}: chain ended at seq=${chainRes.lastSeq}`,
      };
    }
  }

  return {
    ok: true,
    verifiedSeq: chainRes.lastSeq,
    leafIndex: inclusionProof.leaf_index,
    treeSize: inclusionProof.tree_size,
  };
}
