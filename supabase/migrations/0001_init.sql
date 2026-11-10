-- FitnessTracker schema.
--
-- Design notes:
--  * user_id is denormalised onto every table, including lifts and lift_sets,
--    so RLS policies never need a join. Policies that join are both slower and
--    much easier to get subtly wrong.
--  * Composite foreign keys on (parent_id, user_id) make it impossible to
--    attach a row to another user's parent. Plain FK checks bypass RLS, so
--    without this a user could hang a set off someone else's lift.
--  * auth.uid() is wrapped in a scalar subquery so Postgres evaluates it once
--    per statement instead of once per row.

create type public.workout_split as enum ('push', 'pull', 'legs', 'arms');

-- Workouts ------------------------------------------------------------------
create table public.workouts (
    id          uuid primary key default gen_random_uuid(),
    user_id     uuid not null default auth.uid()
                references auth.users (id) on delete cascade,
    date        date not null default current_date,
    split       public.workout_split not null default 'push',
    started_at  timestamptz,
    ended_at    timestamptz,
    rating      smallint check (rating between 1 and 5),
    created_at  timestamptz not null default now(),

    constraint workouts_id_user_key unique (id, user_id),
    constraint workouts_ends_after_start check (ended_at is null
                                                or started_at is null
                                                or ended_at >= started_at)
);

-- Lifts ---------------------------------------------------------------------
create table public.lifts (
    id          uuid primary key default gen_random_uuid(),
    user_id     uuid not null default auth.uid()
                references auth.users (id) on delete cascade,
    workout_id  uuid not null,
    name        text not null check (length(trim(name)) > 0),
    position    integer not null default 0,
    created_at  timestamptz not null default now(),

    constraint lifts_id_user_key unique (id, user_id),
    constraint lifts_workout_fk foreign key (workout_id, user_id)
               references public.workouts (id, user_id) on delete cascade
);

-- Sets ----------------------------------------------------------------------
create table public.lift_sets (
    id          uuid primary key default gen_random_uuid(),
    user_id     uuid not null default auth.uid()
                references auth.users (id) on delete cascade,
    lift_id     uuid not null,
    reps        integer not null check (reps > 0),
    weight      numeric(6, 2) not null check (weight >= 0),
    position    integer not null default 0,
    created_at  timestamptz not null default now(),

    constraint lift_sets_lift_fk foreign key (lift_id, user_id)
               references public.lifts (id, user_id) on delete cascade
);

-- Bodyweight ----------------------------------------------------------------
create table public.bodyweights (
    id          uuid primary key default gen_random_uuid(),
    user_id     uuid not null default auth.uid()
                references auth.users (id) on delete cascade,
    date        date not null default current_date,
    weight      numeric(6, 2) not null check (weight > 0),
    created_at  timestamptz not null default now(),

    -- One weigh-in per day; upsert on conflict to correct a mistake.
    constraint bodyweights_user_date_key unique (user_id, date)
);

-- Goals ---------------------------------------------------------------------
create table public.goals (
    id          uuid primary key default gen_random_uuid(),
    user_id     uuid not null default auth.uid()
                references auth.users (id) on delete cascade,
    goal        text not null check (length(trim(goal)) > 0),
    completed   boolean not null default false,
    created_at  timestamptz not null default now()
);

-- Indexes -------------------------------------------------------------------
create index workouts_user_date_idx    on public.workouts (user_id, date desc);
create index lifts_workout_idx         on public.lifts (workout_id, position);
create index lift_sets_lift_idx        on public.lift_sets (lift_id, position);
create index bodyweights_user_date_idx on public.bodyweights (user_id, date);
create index goals_user_idx            on public.goals (user_id, completed);

-- Row Level Security --------------------------------------------------------
-- Every table is owner-only, and granted to `authenticated` alone so the
-- public anon key cannot read or write anything at all.
alter table public.workouts    enable row level security;
alter table public.lifts       enable row level security;
alter table public.lift_sets   enable row level security;
alter table public.bodyweights enable row level security;
alter table public.goals       enable row level security;

create policy "owner can do everything" on public.workouts
    for all to authenticated
    using (user_id = (select auth.uid()))
    with check (user_id = (select auth.uid()));

create policy "owner can do everything" on public.lifts
    for all to authenticated
    using (user_id = (select auth.uid()))
    with check (user_id = (select auth.uid()));

create policy "owner can do everything" on public.lift_sets
    for all to authenticated
    using (user_id = (select auth.uid()))
    with check (user_id = (select auth.uid()));

create policy "owner can do everything" on public.bodyweights
    for all to authenticated
    using (user_id = (select auth.uid()))
    with check (user_id = (select auth.uid()));

create policy "owner can do everything" on public.goals
    for all to authenticated
    using (user_id = (select auth.uid()))
    with check (user_id = (select auth.uid()));

-- Progress view -------------------------------------------------------------
-- Replaces the old get_workout_data view: heaviest set per lift per date,
-- grouped case-insensitively by lift name. security_invoker makes it run with
-- the caller's permissions, so the underlying RLS policies still apply.
create view public.lift_progress with (security_invoker = on) as
select  l.user_id,
        lower(trim(l.name))  as lift_key,
        min(l.name)          as lift_name,
        w.date               as date,
        max(s.weight)        as max_weight
from        public.lifts     l
join        public.workouts  w on w.id = l.workout_id
join        public.lift_sets s on s.lift_id = l.id
group by    l.user_id, lower(trim(l.name)), w.date;
