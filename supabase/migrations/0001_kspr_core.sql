create extension if not exists pgcrypto;

create table if not exists public.analyses (
  id uuid primary key default gen_random_uuid(),
  analysis_id text not null unique,
  project_name text not null,
  status text not null,
  provider text not null,
  model text not null,
  summary jsonb not null default '{}'::jsonb,
  report jsonb not null default '{}'::jsonb,
  artifacts jsonb not null default '[]'::jsonb,
  response_text text not null default '',
  created_at timestamptz not null default now()
);

create index if not exists analyses_project_name_idx on public.analyses (project_name);
create index if not exists analyses_created_at_idx on public.analyses (created_at desc);

alter table public.analyses add column if not exists response_text text not null default '';

alter table public.analyses enable row level security;
comment on table public.analyses is 'KSPR analysis results and generated context artifacts';
