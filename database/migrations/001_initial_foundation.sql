
-- WZDM LiveRecord
-- Migration: 001_initial_foundation
-- Synthetic development data only.

create extension if not exists pgcrypto;

create schema if not exists private;

-- 1. Practices: each practice is a separate tenant.
create table if not exists public.practices (
    id uuid primary key default gen_random_uuid(),
    name text not null,
    timezone text not null default 'UTC',
    settings jsonb not null default '{}'::jsonb,
    status text not null default 'active'
        check (status in ('active', 'suspended', 'archived')),
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

-- 2. User profiles. Authentication credentials remain with Supabase Auth.
create table if not exists public.users (
    id uuid primary key references auth.users(id) on delete cascade,
    email text,
    full_name text,
    status text not null default 'active'
        check (status in ('active', 'disabled')),
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

-- 3. A user can belong to more than one practice.
create table if not exists public.practice_memberships (
    id uuid primary key default gen_random_uuid(),
    practice_id uuid not null references public.practices(id),
    user_id uuid not null references public.users(id),
    status text not null default 'invited'
        check (status in ('invited', 'active', 'suspended', 'revoked')),
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    unique (practice_id, user_id),
    unique (id, practice_id)
);

-- 4. Roles are separate from identity and membership.
create table if not exists public.membership_roles (
    id uuid primary key default gen_random_uuid(),
    membership_id uuid not null,
    practice_id uuid not null,
    role text not null check (
        role in (
            'orthodontist',
            'clinical_assistant',
            'front_desk',
            'practice_manager'
        )
    ),
    created_at timestamptz not null default now(),

    foreign key (membership_id, practice_id)
        references public.practice_memberships(id, practice_id)
        on delete cascade,

    unique (membership_id, role)
);

-- 5. Idempotency: prevents duplicate processing of retried requests.
create table if not exists public.idempotency_records (
    id uuid primary key default gen_random_uuid(),
    practice_id uuid not null references public.practices(id),
    idempotency_key text not null,
    request_hash text not null,
    response_status integer,
    response_body jsonb,
    created_at timestamptz not null default now(),
    expires_at timestamptz,
    unique (practice_id, idempotency_key)
);

-- 6. Scheduled jobs: worker-managed background work.
create table if not exists public.scheduled_jobs (
    id uuid primary key default gen_random_uuid(),
    practice_id uuid not null references public.practices(id),
    job_type text not null,
    payload jsonb not null default '{}'::jsonb,
    status text not null default 'pending'
        check (status in ('pending', 'processing', 'completed', 'failed', 'cancelled')),
    attempts integer not null default 0 check (attempts >= 0),
    run_at timestamptz not null default now(),
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

-- 7. Outbox: durable record of events waiting to be dispatched.
create table if not exists public.outbox_messages (
    id uuid primary key default gen_random_uuid(),
    practice_id uuid not null references public.practices(id),
    event_type text not null,
    aggregate_type text not null,
    aggregate_id uuid,
    payload jsonb not null default '{}'::jsonb,
    status text not null default 'pending'
        check (status in ('pending', 'processing', 'dispatched', 'failed')),
    attempts integer not null default 0 check (attempts >= 0),
    created_at timestamptz not null default now(),
    dispatched_at timestamptz
);

-- 8. Audit: append-only record of important system actions.
create table if not exists public.audit_entries (
    id uuid primary key default gen_random_uuid(),
    practice_id uuid not null references public.practices(id),
    actor_user_id uuid references public.users(id),
    action text not null,
    resource_type text not null,
    resource_id uuid,
    correlation_id uuid,
    metadata jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now()
);

-- Indexes for common tenant-scoped queries.
create index if not exists idx_memberships_user
    on public.practice_memberships(user_id, status);

create index if not exists idx_roles_membership
    on public.membership_roles(membership_id, practice_id);

create index if not exists idx_idempotency_expiry
    on public.idempotency_records(expires_at);

create index if not exists idx_jobs_due
    on public.scheduled_jobs(status, run_at);

create index if not exists idx_outbox_pending
    on public.outbox_messages(status, created_at);

create index if not exists idx_audit_practice_time
    on public.audit_entries(practice_id, created_at desc);

-- Tenant-access helper.
-- SECURITY DEFINER avoids recursive membership-table RLS checks.
create or replace function private.has_active_practice_membership(
    target_practice_id uuid
)
returns boolean
language sql
stable
security definer
set search_path = ''
as $$
    select exists (
        select 1
        from public.practice_memberships pm
        where pm.practice_id = target_practice_id
          and pm.user_id = (select auth.uid())
          and pm.status = 'active'
    );
$$;

revoke all on function private.has_active_practice_membership(uuid)
    from public, anon;

grant usage on schema private to authenticated;

grant execute on function private.has_active_practice_membership(uuid)
    to authenticated;

-- Enable Row Level Security.
alter table public.practices enable row level security;
alter table public.users enable row level security;
alter table public.practice_memberships enable row level security;
alter table public.membership_roles enable row level security;
alter table public.idempotency_records enable row level security;
alter table public.scheduled_jobs enable row level security;
alter table public.outbox_messages enable row level security;
alter table public.audit_entries enable row level security;

-- Users can read only their own profile.
create policy users_select_self
on public.users
for select to authenticated
using (id = (select auth.uid()));

-- Users can read practices where they have active membership.
create policy practices_select_member
on public.practices
for select to authenticated
using (
    (select private.has_active_practice_membership(id))
);

-- Users can read their own membership rows.
create policy memberships_select_self
on public.practice_memberships
for select to authenticated
using (user_id = (select auth.uid()));

-- Users can read roles attached to their own memberships.
create policy membership_roles_select_self
on public.membership_roles
for select to authenticated
using (
    exists (
        select 1
        from public.practice_memberships pm
        where pm.id = membership_roles.membership_id
          and pm.practice_id = membership_roles.practice_id
          and pm.user_id = (select auth.uid())
          and pm.status = 'active'
    )
);

-- Practice members can read audit entries for their own practice.
create policy audit_select_practice_member
on public.audit_entries
for select to authenticated
using (
    (select private.has_active_practice_membership(practice_id))
);

-- Intentionally no authenticated-user policies for:
-- idempotency_records, scheduled_jobs, outbox_messages.
-- These are backend/worker-managed tables.

-- Audit entries intentionally have no UPDATE or DELETE policies.
