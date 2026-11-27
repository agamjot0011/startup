-- WZDM LiveRecord — application persistence schema
-- Run once in Supabase SQL Editor (Service Role executes with RLS bypass).
-- All statements are idempotent (IF NOT EXISTS).

CREATE TABLE IF NOT EXISTS application_sessions (
  session_id text PRIMARY KEY,
  user_id text NOT NULL,
  csrf_token text NOT NULL,
  assurance text NOT NULL,
  auth_methods jsonb NOT NULL DEFAULT '[]',
  active_practice_id text,
  active_membership_id text,
  roles jsonb NOT NULL DEFAULT '[]',
  issued_at timestamptz NOT NULL,
  last_activity_at timestamptz NOT NULL,
  last_auth_at timestamptz NOT NULL,
  idle_expires_at timestamptz NOT NULL,
  absolute_expires_at timestamptz NOT NULL,
  session_version integer NOT NULL DEFAULT 1,
  revoked boolean NOT NULL DEFAULT false,
  revoke_reason text
);
CREATE INDEX IF NOT EXISTS idx_sessions_user ON application_sessions(user_id);

CREATE TABLE IF NOT EXISTS care_events (
  event_id text PRIMARY KEY,
  practice_id text NOT NULL,
  patient_id text NOT NULL,
  event_type text NOT NULL,
  source_type text NOT NULL,
  source_id text NOT NULL,
  payload jsonb NOT NULL DEFAULT '{}',
  actor_user_id text,
  recorded_at timestamptz NOT NULL,
  prev_hash text NOT NULL,
  event_hash text NOT NULL,
  correction_of text,
  correction_reason text,
  superseded_by text
);
CREATE INDEX IF NOT EXISTS idx_events_patient ON care_events(practice_id, patient_id, recorded_at);

CREATE TABLE IF NOT EXISTS cards (
  card_id text PRIMARY KEY,
  practice_id text NOT NULL,
  patient_id text NOT NULL,
  card_type text NOT NULL,
  state text NOT NULL,
  owner_membership_id text NOT NULL,
  owner_role text NOT NULL,
  deadline timestamptz NOT NULL,
  row_version integer NOT NULL DEFAULT 1,
  result_code text,
  cancellation_reason text,
  created_at timestamptz NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_cards_practice ON cards(practice_id, state, deadline);

CREATE TABLE IF NOT EXISTS problem_reports (
  report_id text PRIMARY KEY,
  practice_id text NOT NULL,
  patient_id text NOT NULL,
  title text NOT NULL,
  description text NOT NULL,
  received_at timestamptz NOT NULL,
  status text NOT NULL,
  urgency text,
  approved_instruction text,
  triaged_by text,
  triaged_at timestamptz,
  triage_card_id text,
  photo_attached boolean NOT NULL DEFAULT false
);

CREATE TABLE IF NOT EXISTS visit_briefs (
  brief_id text PRIMARY KEY,
  appointment_id text NOT NULL,
  practice_id text NOT NULL,
  patient_id text NOT NULL,
  events_since_cutoff jsonb NOT NULL DEFAULT '[]',
  source_watermark text NOT NULL,
  snapshot_hash text NOT NULL,
  generated_at timestamptz NOT NULL,
  row_version integer NOT NULL DEFAULT 1,
  superseded_by text
);
CREATE INDEX IF NOT EXISTS idx_briefs_appointment ON visit_briefs(appointment_id);

CREATE TABLE IF NOT EXISTS brief_signatures (
  signature_id text PRIMARY KEY,
  brief_id text NOT NULL REFERENCES visit_briefs(brief_id),
  signer_user_id text NOT NULL,
  signed_at timestamptz NOT NULL,
  snapshot_hash text NOT NULL,
  attestation text NOT NULL,
  assurance text NOT NULL
);

CREATE TABLE IF NOT EXISTS chairside_captures (
  capture_id text PRIMARY KEY,
  appointment_id text NOT NULL,
  patient_id text NOT NULL,
  capture_type text NOT NULL,
  content text NOT NULL,
  checklist_version text NOT NULL,
  captured_by text NOT NULL,
  captured_at timestamptz NOT NULL
);

CREATE TABLE IF NOT EXISTS promises (
  promise_id text PRIMARY KEY,
  practice_id text NOT NULL,
  patient_id text NOT NULL,
  text text NOT NULL,
  owner_membership_id text NOT NULL,
  due_at timestamptz NOT NULL,
  state text NOT NULL DEFAULT 'open'
);

CREATE TABLE IF NOT EXISTS notification_commands (
  command_id text PRIMARY KEY,
  practice_id text NOT NULL,
  patient_id text NOT NULL,
  channel text NOT NULL,
  template_id text NOT NULL,
  rendered text NOT NULL,
  status text NOT NULL,
  not_before timestamptz NOT NULL,
  dedupe_key text NOT NULL,
  payload_hash text NOT NULL,
  attempts integer NOT NULL DEFAULT 0,
  provider text,
  blocked_reason text
);
CREATE INDEX IF NOT EXISTS idx_notif_status ON notification_commands(status, not_before);

CREATE TABLE IF NOT EXISTS provider_configs (
  site_id text PRIMARY KEY,
  sms_enabled boolean NOT NULL DEFAULT false,
  email_enabled boolean NOT NULL DEFAULT false
);

CREATE TABLE IF NOT EXISTS messages (
  message_id text PRIMARY KEY,
  practice_id text NOT NULL,
  patient_id text NOT NULL,
  body text NOT NULL,
  published_by text NOT NULL,
  published_at timestamptz NOT NULL
);
CREATE TABLE IF NOT EXISTS message_views (
  view_id text PRIMARY KEY DEFAULT gen_random_uuid()::text,
  message_id text NOT NULL REFERENCES messages(message_id),
  viewer_user_id text NOT NULL,
  viewed_at timestamptz NOT NULL,
  is_acknowledgement boolean NOT NULL DEFAULT false
);

CREATE TABLE IF NOT EXISTS import_batches (
  import_id text PRIMARY KEY,
  practice_id text NOT NULL,
  filename text NOT NULL,
  sha256 text NOT NULL,
  state text NOT NULL,
  received_at timestamptz NOT NULL,
  mapping jsonb NOT NULL DEFAULT '{}',
  committed_at timestamptz,
  correction_of text
);
CREATE TABLE IF NOT EXISTS import_rows (
  import_id text NOT NULL REFERENCES import_batches(import_id),
  row_number integer NOT NULL,
  raw jsonb NOT NULL,
  normalized jsonb NOT NULL DEFAULT '{}',
  status text NOT NULL,
  issues jsonb NOT NULL DEFAULT '[]',
  PRIMARY KEY (import_id, row_number)
);

CREATE TABLE IF NOT EXISTS governed_versions (
  version_id text PRIMARY KEY,
  item_id text NOT NULL,
  kind text NOT NULL,
  body jsonb NOT NULL,
  checksum text NOT NULL,
  state text NOT NULL,
  author_user_id text NOT NULL,
  created_at timestamptz NOT NULL,
  approver_user_id text,
  approved_at timestamptz,
  activated_at timestamptz,
  withdrawn_at timestamptz,
  withdrawal_reason text,
  effective_from text,
  locale text NOT NULL DEFAULT 'en'
);
CREATE INDEX IF NOT EXISTS idx_governed_item ON governed_versions(item_id, state);

CREATE TABLE IF NOT EXISTS metric_facts (
  metric_id text PRIMARY KEY,
  definition_version text NOT NULL,
  numerator double precision NOT NULL,
  denominator double precision NOT NULL,
  value double precision,
  input_hash text NOT NULL,
  computed_at timestamptz NOT NULL,
  provisional boolean NOT NULL DEFAULT true
);

-- Tenant isolation: service role bypasses RLS; add policies before anon use.
ALTER TABLE application_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE care_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE cards ENABLE ROW LEVEL SECURITY;
ALTER TABLE problem_reports ENABLE ROW LEVEL SECURITY;
ALTER TABLE visit_briefs ENABLE ROW LEVEL SECURITY;
ALTER TABLE messages ENABLE ROW LEVEL SECURITY;
