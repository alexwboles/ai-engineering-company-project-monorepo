-- The telemetry table is append-only. The eight columns mirror the event
-- envelope, with the frontend properties stored in the allowlisted tags JSONB.
create table if not exists public.telemetry_events (
    event_id text primary key,
    timestamp timestamptz not null,
    session_id text not null,
    user_id text,
    event_type text not null,
    schema_version text not null,
    request_id text not null,
    tags jsonb not null default '{}'::jsonb
);

create index if not exists telemetry_events_timestamp_idx
    on public.telemetry_events (timestamp desc);

create index if not exists telemetry_events_event_type_idx
    on public.telemetry_events (event_type);

create index if not exists telemetry_events_tags_gin_idx
    on public.telemetry_events using gin (tags);

alter table public.telemetry_events enable row level security;
