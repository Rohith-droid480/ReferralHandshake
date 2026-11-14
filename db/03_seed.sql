-- =============================================================================
-- ReferralHandshake Protocol RHP-1 — Synthetic District Seed Data (REAL_DATA=0)
-- Karnataka Obstetric Referral Network: PHC -> CHC -> FRU -> DH -> MC -> DISPATCH
-- Specification Anchor: Architecture §6, §7, §14; BUILD_PLAN §1.3 (F2, F3, I13)
-- =============================================================================

-- Ensure clean re-seeding within transaction
BEGIN;

-- -----------------------------------------------------------------------------
-- 1. Curated Synthetic Facilities Across Karnataka Obstetric Tiers
-- -----------------------------------------------------------------------------
-- Deterministic synthetic UUIDs
-- PHC: Channapatna Primary Health Centre
-- CHC: Ramanagara Community Health Centre
-- FRU: Kanakapura First Referral Unit
-- DH:  Mandya District Hospital
-- MC:  Bengaluru Apex Obstetric Medical College
-- DISP: Karnataka 108 Emergency Dispatch Centre

INSERT INTO facility (id, code, name, tier, lat_e5, lon_e5, active) VALUES
  ('11111111-1111-1111-1111-111111111111', 'PHC_CHANNAPATNA',     'Channapatna Primary Health Centre',         'PHC',      1265180, 7720890, true),
  ('22222222-2222-2222-2222-222222222222', 'CHC_RAMANAGARA',      'Ramanagara Community Health Centre',        'CHC',      1272090, 7727990, true),
  ('33333333-3333-3333-3333-333333333333', 'FRU_KANAKAPURA',      'Kanakapura First Referral Unit',            'FRU',      1254630, 7742050, true),
  ('44444444-4444-4444-4444-444444444444', 'DH_MANDYA',           'Mandya District Hospital',                  'DH',       1252390, 7689660, true),
  ('55555555-5555-5555-5555-555555555555', 'MC_BENGALURU_OB',      'Bengaluru Apex Obstetric Medical College',  'MC',       1297160, 7759460, true),
  ('66666666-6666-6666-6666-666666666666', 'DISPATCH_108_CENTRAL', 'Karnataka 108 Central Dispatch Hub',       'DISPATCH', 1297670, 7759010, true)
ON CONFLICT (id) DO UPDATE SET
  code = EXCLUDED.code, name = EXCLUDED.name, tier = EXCLUDED.tier,
  lat_e5 = EXCLUDED.lat_e5, lon_e5 = EXCLUDED.lon_e5, active = EXCLUDED.active;

-- -----------------------------------------------------------------------------
-- 2. Need Class Requirements
-- -----------------------------------------------------------------------------
INSERT INTO need_class_requirement (need_class, capability) VALUES
  ('OBSTETRIC_EMERGENCY', 'OT'),
  ('OBSTETRIC_EMERGENCY', 'BLOOD'),
  ('OBSTETRIC_EMERGENCY', 'ANAESTHETIST'),
  ('OBSTETRIC_EMERGENCY', 'NICU'),
  ('NEONATAL',            'NICU'),
  ('NEONATAL',            'PAEDIATRICIAN'),
  ('TRAUMA',              'OT'),
  ('TRAUMA',              'BLOOD'),
  ('TRAUMA',              'ANAESTHETIST'),
  ('CARDIAC',             'OT'),
  ('CARDIAC',             'ANAESTHETIST'),
  ('STROKE',              'OT'),
  ('STROKE',              'ANAESTHETIST')
ON CONFLICT (need_class, capability) DO NOTHING;

-- -----------------------------------------------------------------------------
-- 3. Synthetic Roster Duty Slots
-- PIN '1234' Argon2id hash: $argon2id$v=19$m=65536,t=2,p=2$r1+4ctj1qHcRB3Flno/Brg$up2gzDfaZsUHA5o+l4b6X5Ogjyn5taKv66fSb7vWLeM
-- -----------------------------------------------------------------------------
INSERT INTO roster (id, facility_id, role_slot, slot_no, phone_e164, pin_hash, valid_from, valid_to) VALUES
  -- PHC Channapatna Staff
  ('a1111111-0000-0000-0000-000000000001', '11111111-1111-1111-1111-111111111111', 'CLINICIAN',  1, '+919000000001', '$argon2id$v=19$m=65536,t=2,p=2$r1+4ctj1qHcRB3Flno/Brg$up2gzDfaZsUHA5o+l4b6X5Ogjyn5taKv66fSb7vWLeM', now() - interval '1 day', now() + interval '90 days'),
  ('a1111111-0000-0000-0000-000000000002', '11111111-1111-1111-1111-111111111111', 'NURSE',      1, '+919000000002', '$argon2id$v=19$m=65536,t=2,p=2$r1+4ctj1qHcRB3Flno/Brg$up2gzDfaZsUHA5o+l4b6X5Ogjyn5taKv66fSb7vWLeM', now() - interval '1 day', now() + interval '90 days'),

  -- CHC Ramanagara Staff
  ('a2222222-0000-0000-0000-000000000001', '22222222-2222-2222-2222-222222222222', 'CMO',        1, '+919000000003', '$argon2id$v=19$m=65536,t=2,p=2$r1+4ctj1qHcRB3Flno/Brg$up2gzDfaZsUHA5o+l4b6X5Ogjyn5taKv66fSb7vWLeM', now() - interval '1 day', now() + interval '90 days'),
  ('a2222222-0000-0000-0000-000000000002', '22222222-2222-2222-2222-222222222222', 'NURSE',      1, '+919000000004', '$argon2id$v=19$m=65536,t=2,p=2$r1+4ctj1qHcRB3Flno/Brg$up2gzDfaZsUHA5o+l4b6X5Ogjyn5taKv66fSb7vWLeM', now() - interval '1 day', now() + interval '90 days'),

  -- FRU Kanakapura Staff
  ('a3333333-0000-0000-0000-000000000001', '33333333-3333-3333-3333-333333333333', 'CMO',        1, '+919000000005', '$argon2id$v=19$m=65536,t=2,p=2$r1+4ctj1qHcRB3Flno/Brg$up2gzDfaZsUHA5o+l4b6X5Ogjyn5taKv66fSb7vWLeM', now() - interval '1 day', now() + interval '90 days'),
  ('a3333333-0000-0000-0000-000000000002', '33333333-3333-3333-3333-333333333333', 'CONSULTANT', 1, '+919000000006', '$argon2id$v=19$m=65536,t=2,p=2$r1+4ctj1qHcRB3Flno/Brg$up2gzDfaZsUHA5o+l4b6X5Ogjyn5taKv66fSb7vWLeM', now() - interval '1 day', now() + interval '90 days'),
  ('a3333333-0000-0000-0000-000000000003', '33333333-3333-3333-3333-333333333333', 'NURSE',      1, '+919000000007', '$argon2id$v=19$m=65536,t=2,p=2$r1+4ctj1qHcRB3Flno/Brg$up2gzDfaZsUHA5o+l4b6X5Ogjyn5taKv66fSb7vWLeM', now() - interval '1 day', now() + interval '90 days'),

  -- DH Mandya Staff (S=3 slots for Consultant)
  ('a4444444-0000-0000-0000-000000000001', '44444444-4444-4444-4444-444444444444', 'CONSULTANT', 1, '+919000000008', '$argon2id$v=19$m=65536,t=2,p=2$r1+4ctj1qHcRB3Flno/Brg$up2gzDfaZsUHA5o+l4b6X5Ogjyn5taKv66fSb7vWLeM', now() - interval '1 day', now() + interval '90 days'),
  ('a4444444-0000-0000-0000-000000000002', '44444444-4444-4444-4444-444444444444', 'CONSULTANT', 2, '+919000000009', '$argon2id$v=19$m=65536,t=2,p=2$r1+4ctj1qHcRB3Flno/Brg$up2gzDfaZsUHA5o+l4b6X5Ogjyn5taKv66fSb7vWLeM', now() - interval '1 day', now() + interval '90 days'),
  ('a4444444-0000-0000-0000-000000000003', '44444444-4444-4444-4444-444444444444', 'CONSULTANT', 3, '+919000000010', '$argon2id$v=19$m=65536,t=2,p=2$r1+4ctj1qHcRB3Flno/Brg$up2gzDfaZsUHA5o+l4b6X5Ogjyn5taKv66fSb7vWLeM', now() - interval '1 day', now() + interval '90 days'),
  ('a4444444-0000-0000-0000-000000000004', '44444444-4444-4444-4444-444444444444', 'CMO',        1, '+919000000011', '$argon2id$v=19$m=65536,t=2,p=2$r1+4ctj1qHcRB3Flno/Brg$up2gzDfaZsUHA5o+l4b6X5Ogjyn5taKv66fSb7vWLeM', now() - interval '1 day', now() + interval '90 days'),
  ('a4444444-0000-0000-0000-000000000005', '44444444-4444-4444-4444-444444444444', 'NURSE',      1, '+919000000012', '$argon2id$v=19$m=65536,t=2,p=2$r1+4ctj1qHcRB3Flno/Brg$up2gzDfaZsUHA5o+l4b6X5Ogjyn5taKv66fSb7vWLeM', now() - interval '1 day', now() + interval '90 days'),

  -- MC Bengaluru Apex Staff (S=3 slots for Consultant)
  ('a5555555-0000-0000-0000-000000000001', '55555555-5555-5555-5555-555555555555', 'CONSULTANT', 1, '+919000000013', '$argon2id$v=19$m=65536,t=2,p=2$r1+4ctj1qHcRB3Flno/Brg$up2gzDfaZsUHA5o+l4b6X5Ogjyn5taKv66fSb7vWLeM', now() - interval '1 day', now() + interval '90 days'),
  ('a5555555-0000-0000-0000-000000000002', '55555555-5555-5555-5555-555555555555', 'CONSULTANT', 2, '+919000000014', '$argon2id$v=19$m=65536,t=2,p=2$r1+4ctj1qHcRB3Flno/Brg$up2gzDfaZsUHA5o+l4b6X5Ogjyn5taKv66fSb7vWLeM', now() - interval '1 day', now() + interval '90 days'),
  ('a5555555-0000-0000-0000-000000000003', '55555555-5555-5555-5555-555555555555', 'CONSULTANT', 3, '+919000000015', '$argon2id$v=19$m=65536,t=2,p=2$r1+4ctj1qHcRB3Flno/Brg$up2gzDfaZsUHA5o+l4b6X5Ogjyn5taKv66fSb7vWLeM', now() - interval '1 day', now() + interval '90 days'),
  ('a5555555-0000-0000-0000-000000000004', '55555555-5555-5555-5555-555555555555', 'CMO',        1, '+919000000016', '$argon2id$v=19$m=65536,t=2,p=2$r1+4ctj1qHcRB3Flno/Brg$up2gzDfaZsUHA5o+l4b6X5Ogjyn5taKv66fSb7vWLeM', now() - interval '1 day', now() + interval '90 days'),
  ('a5555555-0000-0000-0000-000000000005', '55555555-5555-5555-5555-555555555555', 'NURSE',      1, '+919000000017', '$argon2id$v=19$m=65536,t=2,p=2$r1+4ctj1qHcRB3Flno/Brg$up2gzDfaZsUHA5o+l4b6X5Ogjyn5taKv66fSb7vWLeM', now() - interval '1 day', now() + interval '90 days'),

  -- DISPATCH Central 108 Staff
  ('a6666666-0000-0000-0000-000000000001', '66666666-6666-6666-6666-666666666666', 'DISPATCHER', 1, '+919000000018', '$argon2id$v=19$m=65536,t=2,p=2$r1+4ctj1qHcRB3Flno/Brg$up2gzDfaZsUHA5o+l4b6X5Ogjyn5taKv66fSb7vWLeM', now() - interval '1 day', now() + interval '90 days'),
  ('a6666666-0000-0000-0000-000000000002', '66666666-6666-6666-6666-666666666666', 'DISPATCHER', 2, '+919000000019', '$argon2id$v=19$m=65536,t=2,p=2$r1+4ctj1qHcRB3Flno/Brg$up2gzDfaZsUHA5o+l4b6X5Ogjyn5taKv66fSb7vWLeM', now() - interval '1 day', now() + interval '90 days'),
  ('a6666666-0000-0000-0000-000000000003', '66666666-6666-6666-6666-666666666666', 'EMT',        1, '+919000000020', '$argon2id$v=19$m=65536,t=2,p=2$r1+4ctj1qHcRB3Flno/Brg$up2gzDfaZsUHA5o+l4b6X5Ogjyn5taKv66fSb7vWLeM', now() - interval '1 day', now() + interval '90 days'),
  ('a6666666-0000-0000-0000-000000000004', '66666666-6666-6666-6666-666666666666', 'EMT',        2, '+919000000021', '$argon2id$v=19$m=65536,t=2,p=2$r1+4ctj1qHcRB3Flno/Brg$up2gzDfaZsUHA5o+l4b6X5Ogjyn5taKv66fSb7vWLeM', now() - interval '1 day', now() + interval '90 days'),
  ('a6666666-0000-0000-0000-000000000005', '66666666-6666-6666-6666-666666666666', 'ADMIN',      1, '+919000000022', '$argon2id$v=19$m=65536,t=2,p=2$r1+4ctj1qHcRB3Flno/Brg$up2gzDfaZsUHA5o+l4b6X5Ogjyn5taKv66fSb7vWLeM', now() - interval '1 day', now() + interval '90 days')
ON CONFLICT (id) DO UPDATE SET
  facility_id = EXCLUDED.facility_id, role_slot = EXCLUDED.role_slot,
  slot_no = EXCLUDED.slot_no, phone_e164 = EXCLUDED.phone_e164, pin_hash = EXCLUDED.pin_hash;

-- Insert 20 JUDGE_DESK Roster Slots for Live Evaluation Demo
INSERT INTO roster (id, facility_id, role_slot, slot_no, phone_e164, pin_hash, valid_from, valid_to)
SELECT
  ('d0000000-0000-0000-0000-' || lpad(i::text, 12, '0'))::uuid,
  '66666666-6666-6666-6666-666666666666'::uuid,
  'JUDGE_DESK',
  i::smallint,
  '+9190000000' || lpad((22 + i)::text, 2, '0'),
  '$argon2id$v=19$m=65536,t=2,p=2$r1+4ctj1qHcRB3Flno/Brg$up2gzDfaZsUHA5o+l4b6X5Ogjyn5taKv66fSb7vWLeM',
  now() - interval '1 day',
  now() + interval '90 days'
FROM generate_series(1, 20) AS i
ON CONFLICT (id) DO NOTHING;

-- -----------------------------------------------------------------------------
-- 4. Facility Capabilities (attested for 24h validity)
-- -----------------------------------------------------------------------------
INSERT INTO facility_capability (facility_id, capability, attested_at, attested_by, expires_at) VALUES
  -- CHC Ramanagara: OT and Blood
  ('22222222-2222-2222-2222-222222222222', 'OT',            now() - interval '1 hour', 'a2222222-0000-0000-0000-000000000001', now() + interval '23 hours'),
  ('22222222-2222-2222-2222-222222222222', 'BLOOD',         now() - interval '1 hour', 'a2222222-0000-0000-0000-000000000001', now() + interval '23 hours'),

  -- FRU Kanakapura: OT, Blood, Anaesthetist
  ('33333333-3333-3333-3333-333333333333', 'OT',            now() - interval '1 hour', 'a3333333-0000-0000-0000-000000000001', now() + interval '23 hours'),
  ('33333333-3333-3333-3333-333333333333', 'BLOOD',         now() - interval '1 hour', 'a3333333-0000-0000-0000-000000000001', now() + interval '23 hours'),
  ('33333333-3333-3333-3333-333333333333', 'ANAESTHETIST',  now() - interval '1 hour', 'a3333333-0000-0000-0000-000000000001', now() + interval '23 hours'),

  -- DH Mandya: Full Comprehensive Emergency Obstetric & Neonatal Care (CEmONC)
  ('44444444-4444-4444-4444-444444444444', 'OT',            now() - interval '1 hour', 'a4444444-0000-0000-0000-000000000001', now() + interval '23 hours'),
  ('44444444-4444-4444-4444-444444444444', 'BLOOD',         now() - interval '1 hour', 'a4444444-0000-0000-0000-000000000001', now() + interval '23 hours'),
  ('44444444-4444-4444-4444-444444444444', 'ANAESTHETIST',  now() - interval '1 hour', 'a4444444-0000-0000-0000-000000000001', now() + interval '23 hours'),
  ('44444444-4444-4444-4444-444444444444', 'NICU',           now() - interval '1 hour', 'a4444444-0000-0000-0000-000000000001', now() + interval '23 hours'),
  ('44444444-4444-4444-4444-444444444444', 'PAEDIATRICIAN', now() - interval '1 hour', 'a4444444-0000-0000-0000-000000000001', now() + interval '23 hours'),

  -- MC Bengaluru: Apex Academic Referral Hospital (All capabilities)
  ('55555555-5555-5555-5555-555555555555', 'OT',            now() - interval '1 hour', 'a5555555-0000-0000-0000-000000000001', now() + interval '23 hours'),
  ('55555555-5555-5555-5555-555555555555', 'BLOOD',         now() - interval '1 hour', 'a5555555-0000-0000-0000-000000000001', now() + interval '23 hours'),
  ('55555555-5555-5555-5555-555555555555', 'ANAESTHETIST',  now() - interval '1 hour', 'a5555555-0000-0000-0000-000000000001', now() + interval '23 hours'),
  ('55555555-5555-5555-5555-555555555555', 'NICU',           now() - interval '1 hour', 'a5555555-0000-0000-0000-000000000001', now() + interval '23 hours'),
  ('55555555-5555-5555-5555-555555555555', 'PAEDIATRICIAN', now() - interval '1 hour', 'a5555555-0000-0000-0000-000000000001', now() + interval '23 hours')
ON CONFLICT (facility_id, capability) DO UPDATE SET
  attested_at = EXCLUDED.attested_at, attested_by = EXCLUDED.attested_by, expires_at = EXCLUDED.expires_at;

-- -----------------------------------------------------------------------------
-- 5. Catchment Chains
-- -----------------------------------------------------------------------------
-- Primary referral ladder for PHC Channapatna -> CHC Ramanagara -> DH Mandya -> MC Bengaluru Ob
INSERT INTO catchment_chain (origin_facility_id, need_class, position, target_facility_id, approved_by, approved_at) VALUES
  ('11111111-1111-1111-1111-111111111111', 'OBSTETRIC_EMERGENCY', 1, '22222222-2222-2222-2222-222222222222', 'Dr. Ramesh (DHO Ramanagara)', now() - interval '30 days'),
  ('11111111-1111-1111-1111-111111111111', 'OBSTETRIC_EMERGENCY', 2, '44444444-4444-4444-4444-444444444444', 'Dr. Ramesh (DHO Ramanagara)', now() - interval '30 days'),
  ('11111111-1111-1111-1111-111111111111', 'OBSTETRIC_EMERGENCY', 3, '55555555-5555-5555-5555-555555555555', 'Dr. Ramesh (DHO Ramanagara)', now() - interval '30 days'),

  -- Referral ladder for CHC Ramanagara -> DH Mandya -> MC Bengaluru Ob
  ('22222222-2222-2222-2222-222222222222', 'OBSTETRIC_EMERGENCY', 1, '44444444-4444-4444-4444-444444444444', 'Dr. Ramesh (DHO Ramanagara)', now() - interval '30 days'),
  ('22222222-2222-2222-2222-222222222222', 'OBSTETRIC_EMERGENCY', 2, '55555555-5555-5555-5555-555555555555', 'Dr. Ramesh (DHO Ramanagara)', now() - interval '30 days'),

  -- Referral ladder for FRU Kanakapura -> DH Mandya -> MC Bengaluru Ob
  ('33333333-3333-3333-3333-333333333333', 'OBSTETRIC_EMERGENCY', 1, '44444444-4444-4444-4444-444444444444', 'Dr. Ramesh (DHO Ramanagara)', now() - interval '30 days'),
  ('33333333-3333-3333-3333-333333333333', 'OBSTETRIC_EMERGENCY', 2, '55555555-5555-5555-5555-555555555555', 'Dr. Ramesh (DHO Ramanagara)', now() - interval '30 days')
ON CONFLICT (origin_facility_id, need_class, position) DO UPDATE SET
  target_facility_id = EXCLUDED.target_facility_id, approved_by = EXCLUDED.approved_by, approved_at = EXCLUDED.approved_at;

-- -----------------------------------------------------------------------------
-- 6. Pre-Registered Test Devices
-- -----------------------------------------------------------------------------
-- Standard 32-byte Ed25519 cold/dev test pubkey: d75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a
INSERT INTO device (id, roster_id, pubkey, platform, registered_at, revoked_at) VALUES
  ('e1111111-0000-0000-0000-000000000001', 'a1111111-0000-0000-0000-000000000001', decode('d75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a','hex'), 'PWA',     now() - interval '5 days', NULL),
  ('e2222222-0000-0000-0000-000000000001', 'a2222222-0000-0000-0000-000000000001', decode('d75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a','hex'), 'PWA',     now() - interval '5 days', NULL),
  ('e4444444-0000-0000-0000-000000000001', 'a4444444-0000-0000-0000-000000000001', decode('d75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a','hex'), 'PWA',     now() - interval '5 days', NULL),
  ('e5555555-0000-0000-0000-000000000001', 'a5555555-0000-0000-0000-000000000001', decode('d75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a','hex'), 'PWA',     now() - interval '5 days', NULL),
  ('e6666666-0000-0000-0000-000000000001', 'a6666666-0000-0000-0000-000000000001', decode('d75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a','hex'), 'PWA',     now() - interval '5 days', NULL),
  ('e6666666-0000-0000-0000-000000000003', 'a6666666-0000-0000-0000-000000000003', decode('d75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a','hex'), 'ANDROID', now() - interval '5 days', NULL)
ON CONFLICT (id) DO UPDATE SET
  pubkey = EXCLUDED.pubkey, platform = EXCLUDED.platform, registered_at = EXCLUDED.registered_at;

COMMIT;
