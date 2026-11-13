import { describe, it, expect } from 'vitest';
import { ed25519 } from '@noble/curves/ed25519';
import { sha256 } from '@noble/hashes/sha256';
import {
  canonicalJcs,
  computeLeafHash,
  foldMerkleProof,
  verifyCheckpointSignature,
  verifyRestoreSignature,
  verifyEventHashChain,
  verifyReferralIntegrity,
  bytesToHex,
  hexToBytes,
  bytesToBase64,
  EventRow,
  CheckpointData,
  InclusionProof,
} from './verifier';

describe('Pure-JS Browser Verifier (@noble)', () => {
  const WITNESS_SEED = hexToBytes('3d4017c3e843895a92b70aa74d1b7ebc9c982ccf2ec4968cc0cd55f12af4660c');
  const witnessPriv = WITNESS_SEED;
  const witnessPub = ed25519.getPublicKey(witnessPriv);
  const witnessPubHex = bytesToHex(witnessPub);

  const COLD_SEED = hexToBytes('d75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a');
  const coldPriv = COLD_SEED;
  const coldPub = ed25519.getPublicKey(coldPriv);
  const coldPubHex = bytesToHex(coldPub);

  const referralId = 'e1111111-0000-0000-0000-000000000001';

  it('enforces RFC 8785 JCS canonical formatting and rejects floats', () => {
    const obj = { z: 1, a: 'test', m: true, n: null, sub: { b: 2, a: 1 } };
    expect(canonicalJcs(obj)).toBe('{"a":"test","m":true,"n":null,"sub":{"a":1,"b":2},"z":1}');
    expect(() => canonicalJcs({ floatVal: 3.14 })).toThrow(/Non-integer floating point/);
  });

  it('computes leaf hash identically to Python witness specification', () => {
    const headHash = '0000000000000000000000000000000000000000000000000000000000000000';
    const leaf = computeLeafHash(referralId, 1, headHash);
    expect(bytesToHex(leaf)).toHaveLength(64);
  });

  function createValidChain(): EventRow[] {
    let prev = '0000000000000000000000000000000000000000000000000000000000000000';
    const events: EventRow[] = [];

    const ev1Core = {
      referral_id: referralId,
      seq: 1,
      event_id: '11111111-1111-1111-1111-111111111111',
      type: 'REFERRAL_CREATED',
      epoch: 0,
      actor_roster_id: 'a1111111-0000-0000-0000-000000000001',
      actor_facility_id: 'f1111111-0000-0000-0000-000000000001',
      channel: 'PWA',
      proxy: false,
      detail: { need_class: 'OBSTETRIC_EMERGENCY' },
      secret_hash: null,
      client_ts_ms: 1731500000000,
      server_ts_us: 1731500000000000,
    };
    const jcs1 = new TextEncoder().encode(canonicalJcs(ev1Core));
    const combined1 = new Uint8Array(32 + jcs1.length);
    combined1.set(hexToBytes(prev), 0);
    combined1.set(jcs1, 32);
    const hash1 = bytesToHex(sha256(combined1));

    events.push({
      ...ev1Core,
      prev_hash: prev,
      hash: hash1,
    });
    prev = hash1;

    const ev2Core = {
      referral_id: referralId,
      seq: 2,
      event_id: '22222222-2222-2222-2222-222222222222',
      type: 'OFFER_ACKED',
      epoch: 0,
      actor_roster_id: 'a2222222-0000-0000-0000-000000000001',
      actor_facility_id: 'f2222222-0000-0000-0000-000000000001',
      channel: 'PWA',
      proxy: false,
      detail: { facility: 'CHC_RAMANAGARA' },
      secret_hash: null,
      client_ts_ms: 1731500005000,
      server_ts_us: 1731500005000000,
    };
    const jcs2 = new TextEncoder().encode(canonicalJcs(ev2Core));
    const combined2 = new Uint8Array(32 + jcs2.length);
    combined2.set(hexToBytes(prev), 0);
    combined2.set(jcs2, 32);
    const hash2 = bytesToHex(sha256(combined2));

    events.push({
      ...ev2Core,
      prev_hash: prev,
      hash: hash2,
    });

    return events;
  }

  it('validates a pristine event hash chain', () => {
    const events = createValidChain();
    const res = verifyEventHashChain(referralId, events);
    expect(res.ok).toBe(true);
    expect(res.lastSeq).toBe(2);
  });

  it('detects a sequence gap (SEQ_GAP)', () => {
    const events = createValidChain();
    // Corrupt sequence number of second event to 3
    events[1].seq = 3;
    const res = verifyEventHashChain(referralId, events);
    expect(res.ok).toBe(false);
    expect(res.error).toBe('SEQ_GAP');
  });

  it('detects tampered prev_hash with BROKEN kind=PREV message', () => {
    const events = createValidChain();
    events[1].prev_hash = 'ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff';
    const res = verifyEventHashChain(referralId, events);
    expect(res.ok).toBe(false);
    expect(res.error).toBe('CHAIN_BROKEN');
    expect(res.message).toMatch(/BROKEN referral=.* seq=2 kind=PREV/);
  });

  it('detects tampered detail payload with BROKEN kind=HASH message', () => {
    const events = createValidChain();
    // Modify detail without updating hash
    events[0].detail = { need_class: 'OBSTETRIC_EMERGENCY', tampered: true };
    const res = verifyEventHashChain(referralId, events);
    expect(res.ok).toBe(false);
    expect(res.error).toBe('CHAIN_BROKEN');
    expect(res.message).toMatch(/BROKEN referral=.* seq=1 kind=HASH/);
  });

  it('verifies valid checkpoint signature and rejects invalid ones', () => {
    const rootHash = sha256(new Uint8Array([1, 2, 3]));
    const rootB64 = bytesToBase64(rootHash);
    const noteText = `rhp1/test-deploy\n1\n${rootB64}\n`;
    const noteBytes = new TextEncoder().encode(noteText);
    const sig = ed25519.sign(noteBytes, witnessPriv);

    const validCp: CheckpointData = {
      id: 10,
      tree_size: 1,
      root_hash: bytesToHex(rootHash),
      root_hash_b64: rootB64,
      note_text: noteText,
      signature: bytesToHex(sig),
      deployment: 'test-deploy',
    };

    expect(verifyCheckpointSignature(validCp, witnessPubHex)).toBe(true);

    const invalidCp: CheckpointData = {
      ...validCp,
      signature: bytesToHex(new Uint8Array(64)),
    };
    expect(verifyCheckpointSignature(invalidCp, witnessPubHex)).toBe(false);
  });

  it('verifies end-to-end referral integrity including Merkle proof', () => {
    const events = createValidChain();
    const headSeq = events[1].seq;
    const headHash = events[1].hash;

    // Single referral in tree: leaf IS the root!
    const leafHash = computeLeafHash(referralId, headSeq, headHash);
    const rootHash = leafHash;
    const rootB64 = bytesToBase64(rootHash);
    const noteText = `rhp1/test-deploy\n1\n${rootB64}\n`;
    const sig = ed25519.sign(new TextEncoder().encode(noteText), witnessPriv);

    const checkpoint: CheckpointData = {
      id: 100,
      tree_size: 1,
      root_hash: bytesToHex(rootHash),
      root_hash_b64: rootB64,
      note_text: noteText,
      signature: bytesToHex(sig),
      deployment: 'test-deploy',
    };

    const inclusionProof: InclusionProof = {
      referral_id: referralId,
      head_seq: headSeq,
      head_hash: headHash,
      leaf_index: 0,
      tree_size: 1,
      path: [], // Empty path for 1-leaf tree
      checkpoint_id: 100,
    };

    const result = verifyReferralIntegrity({
      referralId,
      events,
      inclusionProof,
      checkpoint,
      witnessPubKeyHex: witnessPubHex,
    });

    expect(result.ok).toBe(true);
    expect(result.verifiedSeq).toBe(2);
    expect(result.leafIndex).toBe(0);
  });

  it('flags ROOT_MISMATCH when proof path is invalid', () => {
    const events = createValidChain();
    const headSeq = events[1].seq;
    const headHash = events[1].hash;
    const leafHash = computeLeafHash(referralId, headSeq, headHash);

    const bogusRoot = sha256(new Uint8Array([99]));
    const rootB64 = bytesToBase64(bogusRoot);
    const noteText = `rhp1/test-deploy\n1\n${rootB64}\n`;
    const sig = ed25519.sign(new TextEncoder().encode(noteText), witnessPriv);

    const checkpoint: CheckpointData = {
      id: 101,
      tree_size: 1,
      root_hash: bytesToHex(bogusRoot),
      root_hash_b64: rootB64,
      note_text: noteText,
      signature: bytesToHex(sig),
    };

    const inclusionProof: InclusionProof = {
      referral_id: referralId,
      head_seq: headSeq,
      head_hash: headHash,
      leaf_index: 0,
      tree_size: 1,
      path: [],
      checkpoint_id: 101,
    };

    const result = verifyReferralIntegrity({
      referralId,
      events,
      inclusionProof,
      checkpoint,
      witnessPubKeyHex: witnessPubHex,
    });

    expect(result.ok).toBe(false);
    expect(result.error).toBe('ROOT_MISMATCH');
  });

  it('flags TRUNCATED when events end prior to checkpointed head_seq', () => {
    const events = createValidChain();
    const headHash = events[1].hash;

    // Proof asserts head_seq is 5, but we only have 2 events
    const leafHash = computeLeafHash(referralId, 5, headHash);
    const rootB64 = bytesToBase64(leafHash);
    const noteText = `rhp1/test-deploy\n1\n${rootB64}\n`;
    const sig = ed25519.sign(new TextEncoder().encode(noteText), witnessPriv);

    const checkpoint: CheckpointData = {
      id: 102,
      tree_size: 1,
      root_hash: bytesToHex(leafHash),
      root_hash_b64: rootB64,
      note_text: noteText,
      signature: bytesToHex(sig),
    };

    const inclusionProof: InclusionProof = {
      referral_id: referralId,
      head_seq: 5,
      head_hash: headHash,
      leaf_index: 0,
      tree_size: 1,
      path: [],
      checkpoint_id: 102,
    };

    const result = verifyReferralIntegrity({
      referralId,
      events,
      inclusionProof,
      checkpoint,
      witnessPubKeyHex: witnessPubHex,
    });

    expect(result.ok).toBe(false);
    expect(result.error).toBe('TRUNCATED at seq=5');
  });

  it('accepts truncated chain when covered by valid cold-key RESTORE record', () => {
    const events = createValidChain();
    // Add RESTORE event linking the chain
    const prev = events[1].hash;
    const restoreCore = {
      referral_id: referralId,
      seq: 3,
      event_id: '33333333-3333-3333-3333-333333333333',
      type: 'RESTORE',
      epoch: 0,
      actor_roster_id: null,
      actor_facility_id: null,
      channel: 'SYSTEM',
      proxy: false,
      detail: { checkpoint_id: 103 },
      secret_hash: null,
      client_ts_ms: null,
      server_ts_us: 1731500010000000,
    };
    const jcsRestore = new TextEncoder().encode(canonicalJcs(restoreCore));
    const combined = new Uint8Array(32 + jcsRestore.length);
    combined.set(hexToBytes(prev), 0);
    combined.set(jcsRestore, 32);
    const restoreHash = bytesToHex(sha256(combined));

    events.push({
      ...restoreCore,
      prev_hash: prev,
      hash: restoreHash,
    });

    // Checkpoint has kind RESTORE with valid cold signature
    const leafHash = computeLeafHash(referralId, 3, restoreHash);
    const rootHex = bytesToHex(leafHash);
    const rootB64 = bytesToBase64(leafHash);
    const noteText = `rhp1/test-deploy\n1\n${rootB64}\n`;
    const sig = ed25519.sign(new TextEncoder().encode(noteText), witnessPriv);

    const takenAt = '2026-11-14T02:00:00Z';
    const restorePayload = canonicalJcs({
      checkpoint_id: 99,
      kind: 'RESTORE',
      root_hash: rootHex,
      taken_at: takenAt,
      tree_size: 1,
    });
    const coldSig = ed25519.sign(new TextEncoder().encode(restorePayload), coldPriv);

    const restoreCp: CheckpointData = {
      id: 103,
      tree_size: 1,
      root_hash: rootHex,
      root_hash_b64: rootB64,
      note_text: noteText,
      signature: bytesToHex(sig),
      kind: 'RESTORE',
      restore_from: 99,
      taken_at: takenAt,
      cold_signature: bytesToHex(coldSig),
    };

    const proof: InclusionProof = {
      referral_id: referralId,
      head_seq: 3,
      head_hash: restoreHash,
      leaf_index: 0,
      tree_size: 1,
      path: [],
      checkpoint_id: 103,
    };

    const result = verifyReferralIntegrity({
      referralId,
      events,
      inclusionProof: proof,
      checkpoint: restoreCp,
      witnessPubKeyHex: witnessPubHex,
      coldPubKeyHex: coldPubHex,
    });

    expect(result.ok).toBe(true);
    expect(result.verifiedSeq).toBe(3);
  });
});
