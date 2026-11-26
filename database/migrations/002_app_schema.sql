-- WZDM LiveRecord
-- Migration: 002_app_schema
-- Tables for all application features (Step 7 canonical data model)

-- 9. Patients
create table if not exists public.patients (
    id uuid primary key default gen_random_uuid(),
    practice_id uuid not null references public.practices(id) on delete cascade,
    status text not null default 'active'
        check (status in ('active', 'withdrawn', 'deceased')),
    given_name text,
    family_name text,
    birth_date text,
    locale text not null default 'en',
    timezone text not null default 'UTC',
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create index idx_patients_practice on public.patients(practice_id);

-- 10. Patient identifiers
create table if not exists public.patient_identifiers (
    id uuid primary key default gen_random_uuid(),
    patient_id uuid not null references public.patients(id) on delete cascade,
    source_system text not null,
    external_id text not null,
    valid_from timestamptz not null default now(),
    valid_to timestamptz
);

create index idx_patient_identifiers_patient on public.patient_identifiers(patient_id);

-- 11. Patient-user links
create table if not exists public.patient_user_links (
    id uuid primary key default gen_random_uuid(),
    patient_id uuid not null references public.patients(id) on delete cascade,
    user_id uuid not null references public.users(id) on delete cascade,
    status text not null default 'active'
        check (status in ('active', 'revoked')),
    verified_by uuid references public.users(id) on delete set null,
    verified_at timestamptz,
    revoked_at timestamptz,
    created_at timestamptz not null default now()
);

create index idx_patient_user_links_patient on public.patient_user_links(patient_id);

-- 12. Proxy relationships
create table if not exists public.proxy_relationships (
    id uuid primary key default gen_random_uuid(),
    practice_id uuid not null references public.practices(id) on delete cascade,
    patient_id uuid not null references public.patients(id) on delete cascade,
    proxy_user_id uuid not null references public.users(id) on delete cascade,
    relationship_code text not null,
    authority_scopes text not null, -- JSON-encoded array
    verification_method text not null,
    policy_version_id text,
    status text not null default 'active'
        check (status in ('active', 'expired', 'revoked', 'contested')),
    effective_from timestamptz not null default now(),
    effective_to timestamptz,
    revoked_at timestamptz,
    revoked_reason_code text,
    created_at timestamptz not null default now()
);

create index idx_proxy_relationships_patient on public.proxy_relationships(patient_id);
create index idx_proxy_relationships_proxy_user on public.proxy_relationships(proxy_user_id);

-- 13. Consents
create table if not exists public.consents (
    id uuid primary key default gen_random_uuid(),
    practice_id uuid not null references public.practices(id) on delete cascade,
    patient_id uuid not null references public.patients(id) on delete cascade,
    consent_kind text not null,
    decision text not null
        check (decision in ('permit', 'deny', 'withdraw')),
    source_content_version_id text,
    source_document_sha256 text,
    locale text not null default 'en',
    effective_from timestamptz not null default now(),
    effective_to timestamptz,
    supersedes_consent_id uuid references public.consents(id) on delete set null,
    created_at timestamptz not null default now()
);

create index idx_consents_patient on public.consents(patient_id);

-- 14. Notification preferences
create table if not exists public.notification_preferences (
    id uuid primary key default gen_random_uuid(),
    practice_id uuid not null references public.practices(id) on delete cascade,
    patient_id uuid not null references public.patients(id) on delete cascade,
    user_id uuid not null references public.users(id) on delete cascade,
    channel_code text not null,
    destination_ref text,
    status text not null default 'active'
        check (status in ('active', 'opted_out', 'revoked')),
    timezone text not null default 'UTC',
    quiet_start text,
    quiet_end text,
    consent_id uuid references public.consents(id) on delete set null,
    row_version integer not null default 1,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create index idx_notification_preferences_patient on public.notification_preferences(patient_id);

-- 15. Scheduled jobs
create table if not exists public.scheduled_jobs (
    id uuid primary key default gen_random_uuid(),
    practice_id uuid not null references public.practices(id) on delete cascade,
    job_type text not null,
    entity_type text,
    entity_id uuid,
    milestone_version text,
    run_at timestamptz not null default now(),
    status text not null default 'pending'
        check (status in ('pending', 'processing', 'completed', 'failed', 'cancelled')),
    attempts integer not null default 0 check (attempts >= 0),
    lease_owner text,
    lease_expires_at timestamptz,
    last_reason_code text,
    dedupe_key text,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create index idx_jobs_due on public.scheduled_jobs(run_at);

-- 16. Outbox messages
create table if not exists public.outbox_messages (
    id uuid primary key default gen_random_uuid(),
    practice_id uuid not null references public.practices(id) on delete cascade,
    event_type text not null,
    aggregate_type text not null,
    aggregate_id uuid,
    payload text,
    status text not null default 'pending'
        check (status in ('pending', 'processing', 'dispatched', 'failed')),
    attempts integer not null default 0 check (attempts >= 0),
    created_at timestamptz not null default now(),
    dispatched_at timestamptz
);

create index idx_outbox_pending on public.outbox_messages(status, created_at);

-- 17. Idempotency records
create table if not exists public.idempotency_records (
    id uuid primary key default gen_random_uuid(),
    practice_id uuid not null references public.practices(id) on delete cascade,
    actor_user_id uuid references public.users(id) on delete set null,
    route_key text not null,
    idempotency_key text not null,
    request_hash text not null,
    status text not null,
    response_status integer,
    response_reference text,
    created_at timestamptz not null default now(),
    expires_at timestamptz
);

create index idx_idempotency_key on public.idempotency_records(idempotency_key);

-- 18. Audit entries
create table if not exists public.audit_entries (
    id uuid primary key default gen_random_uuid(),
    practice_id uuid not null references public.practices(id) on delete cascade,
    actor_user_id uuid references public.users(id) on delete set null,
    action text not null,
    resource_type text not null,
    resource_id uuid,
    patient_id uuid references public.patients(id) on delete set null,
    purpose_code text,
    policy_reference text,
    outcome_code text,
    reason_code text,
    correlation_id uuid,
    source_network_prefix text,
    release_id text,
    created_at timestamptz not null default now()
);

create index idx_audit_practice_time on public.audit_entries(practice_id, created_at desc);

-- 19. Metric facts
create table if not exists public.metric_facts (
    id uuid primary key default gen_random_uuid(),
    practice_id uuid not null references public.practices(id) on delete cascade,
    fact_type text not null,
    recorded_at timestamptz not null default now(),
    patient_id uuid references public.patients(id) on delete set null,
    source_event_id uuid references public.care_events(id) on delete set null,
    approved_dimensions text, -- JSON-encoded
    value text,
    definition_version text,
    created_at timestamptz not null default now()
);

-- 20. Support grants
create table if not exists public.support_grants (
    id uuid primary key default gen_random_uuid(),
    practice_id uuid not null references public.practices(id) on delete cascade,
    support_user_id uuid not null references public.users(id) on delete cascade,
    ticket_reference text,
    purpose_code text not null,
    scope_json text,
    approved_by_id uuid references public.users(id) on delete set null,
    second_approver_id uuid references public.users(id) on delete set null,
    effective_from timestamptz not null default now(),
    effective_to timestamptz,
    revoked_at timestamptz,
    created_at timestamptz not null default now()
);

-- 21. Care events (append-only patient timeline)
create table if not exists public.care_events (
    id uuid primary key default gen_random_uuid(),
    practice_id uuid not null references public.practices(id) on delete cascade,
    patient_id uuid not null references public.patients(id) on delete cascade,
    event_type text not null,
    schema_version text,
    occurred_at timestamptz,
    recorded_at timestamptz not null default now(),
    actor_type text,
    actor_id text,
    privacy_scope text not null,
    payload text,
    correlation_id text,
    causation_id text,
    idempotency_key text,
    prior_event_hash text,
    event_hash text,
    created_at timestamptz not null default now()
);

create index idx_care_events_patient on public.care_events(patient_id);
create index idx_care_events_occurred on public.care_events(occurred_at);

-- 22. Event attachments
create table if not exists public.event_attachments (
    id uuid primary key default gen_random_uuid(),
    event_id uuid not null references public.care_events(id) on delete cascade,
    attachment_id uuid not null references public.attachments(id) on delete cascade,
    relation_code text not null
);

-- 23. Attachments (secure photo storage)
create table if not exists public.attachments (
    id uuid primary key default gen_random_uuid(),
    practice_id uuid not null references public.practices(id) on delete cascade,
    patient_id uuid not null references public.patients(id) on delete cascade,
    object_key text not null,
    purpose_code text not null,
    declared_mime text,
    detected_mime text,
    byte_size integer,
    sha256 text not null,
    privacy_scope text not null,
    status text not null default 'upload_pending'
        check (status in ('upload_pending', 'quarantined', 'available', 'rejected', 'tombstoned')),
    malware_detected boolean not null default false,
    uploaded_by text,
    uploaded_at timestamptz,
    available_at timestamptz,
    retention_class text,
    tombstone_at timestamptz,
    created_at timestamptz not null default now()
);

create index idx_attachments_patient on public.attachments(patient_id);

-- 24. Cards (role inboxes, card lifecycle)
create table if not exists public.cards (
    id uuid primary key default gen_random_uuid(),
    practice_id uuid not null references public.practices(id) on delete cascade,
    patient_id uuid not null references public.patients(id) on delete cascade,
    source_event_id uuid references public.care_events(id) on delete set null,
    card_type text not null,
    recipient_role text,
    recipient_user_id uuid references public.users(id) on delete set null,
    owner_membership_id uuid references public.practice_memberships(id) on delete set null,
    absolute_deadline timestamptz,
    timezone text not null default 'UTC',
    rule_version_id text,
    content_version_id text,
    privacy_scope text not null,
    status text not null default 'available'
        check (status in ('available', 'acknowledged', 'in_progress', 'result_recorded', 'closed', 'cancelled', 'superseded', 'access_revoked', 'failed_delivery')),
    mandatory_flag boolean not null default false,
    acknowledged_at timestamptz,
    closed_at timestamptz,
    row_version integer not null default 1,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create index idx_cards_practice_status on public.cards(practice_id, status);
create index idx_cards_patient on public.cards(patient_id);

-- 25. Card acknowledgements
create table if not exists public.card_acknowledgements (
    id uuid primary key default gen_random_uuid(),
    card_id uuid not null references public.cards(id) on delete cascade,
    card_version integer not null,
    actor_id text not null,
    acknowledged_at timestamptz not null default now(),
    channel text
);

-- 26. Card results
create table if not exists public.card_results (
    id uuid primary key default gen_random_uuid(),
    card_id uuid not null references public.cards(id) on delete cascade,
    result_code text not null,
    payload text,
    actor_id text not null,
    recorded_at timestamptz not null default now(),
    verifier_id text
);

-- 27. Card escalations
create table if not exists public.card_escalations (
    id uuid primary key default gen_random_uuid(),
    card_id uuid not null references public.cards(id) on delete cascade,
    policy_version_id text,
    milestone text not null,
    due_at timestamptz,
    executed_at timestamptz,
    action text,
    recipient_id text,
    disposition text,
    created_at timestamptz not null default now()
);

-- 28. Rule sets
create table if not exists public.rule_sets (
    id uuid primary key default gen_random_uuid(),
    practice_id uuid not null references public.practices(id) on delete cascade,
    semantic_key text not null,
    trigger_event text not null,
    active_version_id uuid references public.rule_versions(id) on delete set null,
    created_at timestamptz not null default now()
);

-- 29. Rule versions
create table if not exists public.rule_versions (
    id uuid primary key default gen_random_uuid(),
    rule_set_id uuid not null references public.rule_sets(id) on delete cascade,
    version_number integer not null,
    state text not null default 'draft'
        check (state in ('draft', 'submitted', 'approved', 'active', 'retired', 'rejected')),
    definition text, -- JSON-encoded rule definition
    checksum text not null,
    author text,
    reason text,
    effective_from timestamptz,
    effective_to timestamptz,
    created_at timestamptz not null default now()
);

create index idx_rule_versions_set on public.rule_versions(rule_set_id);

-- 30. Rule approvals
create table if not exists public.rule_approvals (
    id uuid primary key default gen_random_uuid(),
    rule_version_id uuid not null references public.rule_versions(id) on delete cascade,
    approver_id text not null,
    decision text not null
        check (decision in ('approve', 'reject')),
    approved_checksum text,
    reason text,
    approved_at timestamptz not null default now()
);

-- 31. Rule executions
create table if not exists public.rule_executions (
    id uuid primary key default gen_random_uuid(),
    rule_version_id uuid not null references public.rule_versions(id) on delete cascade,
    trigger_event_id uuid references public.care_events(id) on delete set null,
    input_fact_hash text,
    output_plan_hash text,
    state text not null,
    explanation_codes text,
    created_at timestamptz not null default now()
);

-- 32. Content items
create table if not exists public.content_items (
    id uuid primary key default gen_random_uuid(),
    practice_id uuid not null references public.practices(id) on delete cascade,
    semantic_key text not null,
    content_class text not null,
    audience text not null,
    purpose text not null,
    created_at timestamptz not null default now()
);

create index idx_content_items_semantic on public.content_items(semantic_key);

-- 33. Content versions
create table if not exists public.content_versions (
    id uuid primary key default gen_random_uuid(),
    content_item_id uuid not null references public.content_items(id) on delete cascade,
    version_number integer not null,
    locale text not null,
    state text not null default 'draft'
        check (state in ('draft', 'approved', 'active', 'retired', 'rejected', 'withdrawn')),
    body text not null, -- JSON-encoded content body
    checksum text not null,
    readability text,
    author text,
    created_at timestamptz not null default now()
);

create index idx_content_versions_item on public.content_versions(content_item_id);

-- 34. Content approvals
create table if not exists public.content_approvals (
    id uuid primary key default gen_random_uuid(),
    content_version_id uuid not null references public.content_versions(id) on delete cascade,
    reviewer_id text not null,
    review_type text not null
        check (review_type in ('clinical', 'legal', 'accessibility', 'translation')),
    decision text not null
        check (decision in ('approve', 'reject')),
    approved_checksum text,
    reviewed_at timestamptz not null default now()
);

-- 35. Privacy policy versions
create table if not exists public.privacy_policy_versions (
    id uuid primary key default gen_random_uuid(),
    practice_id uuid not null references public.practices(id) on delete cascade,
    jurisdiction_code text not null,
    version_label text not null,
    status text not null default 'draft'
        check (status in ('draft', 'approved', 'active', 'retired', 'rejected')),
    policy_json text not null,
    checksum text not null,
    approved_by text,
    approved_at timestamptz,
    effective_from timestamptz not null default now(),
    effective_to timestamptz,
    created_at timestamptz not null default now()
);

-- 36. Practice settings versions
create table if not exists public.practice_settings_versions (
    id uuid primary key default gen_random_uuid(),
    practice_id uuid not null references public.practices(id) on delete cascade,
    version_label text not null,
    settings_json text not null, -- JSON-encoded settings
    checksum text not null,
    approved_by text,
    approved_at timestamptz,
    effective_from timestamptz not null default now(),
    effective_to timestamptz,
    created_at timestamptz not null default now()
);

-- 37. Import batches
create table if not exists public.import_batches (
    id uuid primary key default gen_random_uuid(),
    practice_id uuid not null references public.practices(id) on delete cascade,
    source_system text not null,
    source_tenant_id text,
    package_hash text not null,
    mapping_version text,
    mode text not null default 'daily',
    state text not null default 'upload'
        check (state in ('upload', 'validation', 'ready', 'committed', 'rejected')),
    object_reference text,
    export_time timestamptz,
    upload_time timestamptz,
    commit_time timestamptz,
    uploader text,
    row_count integer not null default 0,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create index idx_import_batches_practice on public.import_batches(practice_id);

-- 38. Import rows
create table if not exists public.import_rows (
    id uuid primary key default gen_random_uuid(),
    batch_id uuid not null references public.import_batches(id) on delete cascade,
    file text not null,
    row_number integer not null,
    entity_type text not null,
    external_id text not null,
    source_updated_at timestamptz,
    row_hash text,
    parsed_payload text,
    planned_action text,
    result_code text,
    error_detail text,
    created_at timestamptz not null default now()
);

create index idx_import_rows_batch on public.import_rows(batch_id);

-- 39. Import events (source lineage)
create table if not exists public.import_events (
    id uuid primary key default gen_random_uuid(),
    batch_id uuid not null references public.import_batches(id) on delete cascade,
    event_type text not null,
    payload text,
    source text,
    row_hash text,
    created_at timestamptz not null default now()
);

-- Enable Row Level Security
alter table public.patients enable row level security;
alter table public.patient_identifiers enable row level security;
alter table public.patient_user_links enable row level security;
alter table public.proxy_relationships enable row level security;
alter table public.consents enable row level security;
alter table public.notification_preferences enable row level security;
alter table public.scheduled_jobs enable row level security;
alter table public.outbox_messages enable row level security;
alter table public.idempotency_records enable row level security;
alter table public.audit_entries enable row level security;
alter table public.metric_facts enable row level security;
alter table public.support_grants enable row level security;
alter table public.care_events enable row level security;
alter table public.event_attachments enable row level security;
alter table public.attachments enable row level security;
alter table public.cards enable row level security;
alter table public.card_acknowledgements enable row level security;
alter table public.card_results enable row level security;
alter table public.card_escalations enable row level security;
alter table public.rule_sets enable row level security;
alter table public.rule_versions enable row level security;
alter table public.rule_approvals enable row level security;
alter table public.rule_executions enable row level security;
alter table public.content_items enable row level security;
alter table public.content_versions enable row level security;
alter table public.content_approvals enable row level security;
alter table public.privacy_policy_versions enable row level security;
alter table public.practice_settings_versions enable row level security;
alter table public.import_batches enable row level security;
alter table public.import_rows enable row level security;
alter table public.import_events enable row level security;

-- No SELECT policies for backend/worker tables (RBAC in app layer)
