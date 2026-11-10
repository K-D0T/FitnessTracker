#!/usr/bin/env python3
"""Turn fitness-data-export.json into SQL for the Supabase schema.

The export came out of the Django SQLite database. Rows need an owner, and
user_id is only known once the account exists, so it is passed in:

    python3 scripts/generate_import_sql.py <user-uuid> > import.sql

Emits one plpgsql block so workout -> lift -> set links are built from
returned ids rather than hardcoded primary keys.
"""

import argparse
import json
import pathlib
import sys
import uuid

# Django stored two-letter split codes; the Postgres enum uses words.
SPLIT_MAP = {'PU': 'push', 'PL': 'pull', 'LG': 'legs', 'AR': 'arms'}


def sql_str(value):
    """Quote a value as a SQL literal, or NULL."""
    if value is None:
        return 'null'
    return "'" + str(value).replace("'", "''") + "'"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('user_id', help='auth.users UUID that will own the rows')
    parser.add_argument(
        '--export',
        default='fitness-data-export.json',
        type=pathlib.Path,
        help='path to the JSON export',
    )
    args = parser.parse_args()

    # Fail early on a malformed id rather than producing invalid SQL.
    try:
        owner = str(uuid.UUID(args.user_id))
    except ValueError:
        sys.exit(f'Not a valid UUID: {args.user_id}')

    data = json.loads(args.export.read_text(encoding='utf-8'))

    out = [
        'do $$',
        'declare',
        f"  v_user uuid := '{owner}';",
        '  v_workout uuid;',
        '  v_lift uuid;',
        'begin',
    ]

    bodyweights = data.get('bodyweights', [])
    if bodyweights:
        values = ',\n    '.join(
            f"(v_user, {sql_str(b['date'])}, {float(b['weight'])})" for b in bodyweights
        )
        out += [
            '  insert into public.bodyweights (user_id, date, weight) values',
            f'    {values}',
            '  on conflict (user_id, date) do update set weight = excluded.weight;',
            '',
        ]

    goals = data.get('goals', [])
    if goals:
        values = ',\n    '.join(
            f"(v_user, {sql_str(g['goal'])}, {str(bool(g['completed'])).lower()})"
            for g in goals
        )
        out += [
            '  insert into public.goals (user_id, goal, completed) values',
            f'    {values};',
            '',
        ]

    for workout in data.get('workouts', []):
        split = SPLIT_MAP.get(workout['split'])
        if split is None:
            sys.exit(f"Unknown split code: {workout['split']!r}")

        rating = workout.get('rating')
        # The old schema let any integer through; this one has a 1-5 CHECK.
        rating_sql = str(rating) if isinstance(rating, int) and 1 <= rating <= 5 else 'null'

        out += [
            '  insert into public.workouts'
            ' (user_id, date, split, started_at, ended_at, rating) values',
            f"    (v_user, {sql_str(workout['date'])}, {sql_str(split)},"
            f" {sql_str(workout.get('start_time'))}, {sql_str(workout.get('end_time'))},"
            f' {rating_sql})',
            '  returning id into v_workout;',
        ]

        for position, lift in enumerate(workout.get('lifts', [])):
            out += [
                '  insert into public.lifts (user_id, workout_id, name, position) values',
                f"    (v_user, v_workout, {sql_str(lift['name'])}, {position})",
                '  returning id into v_lift;',
            ]
            sets = lift.get('sets', [])
            if sets:
                values = ',\n    '.join(
                    f"(v_user, v_lift, {int(s['reps'])}, {float(s['weight'])}, {i})"
                    for i, s in enumerate(sets)
                )
                out += [
                    '  insert into public.lift_sets'
                    ' (user_id, lift_id, reps, weight, position) values',
                    f'    {values};',
                ]
        out.append('')

    out += ['end $$;']
    print('\n'.join(out))


if __name__ == '__main__':
    main()
