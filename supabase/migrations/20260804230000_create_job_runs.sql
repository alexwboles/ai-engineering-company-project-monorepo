-- Nightly orchestration state is separate from pipeline_runs. The former
-- controls the export/trigger job; the latter audits the ETL stages.
create table if not exists public.job_runs (
    id uuid primary key default gen_random_uuid(),
    job_name text not null,
    target_date date not null,
    status text not null check (status in ('pending', 'processing', 'completed', 'failed')),
    started_at timestamptz,
    finished_at timestamptz,
    error_message text,
    created_at timestamptz not null default now(),
    unique (job_name, target_date)
);

create index if not exists job_runs_job_name_target_date_idx
    on public.job_runs (job_name, target_date);

create unique index if not exists job_runs_one_processing_idx
    on public.job_runs (job_name, status)
    where status = 'processing';
