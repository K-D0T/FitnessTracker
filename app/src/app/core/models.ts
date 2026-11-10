/** Row shapes matching supabase/migrations/0001_init.sql. */

export type WorkoutSplit = 'push' | 'pull' | 'legs' | 'arms';

export const SPLIT_LABELS: Record<WorkoutSplit, string> = {
  push: 'Push',
  pull: 'Pull',
  legs: 'Legs',
  arms: 'Arms',
};

export interface Workout {
  id: string;
  user_id: string;
  /** ISO date, yyyy-mm-dd. */
  date: string;
  split: WorkoutSplit;
  started_at: string | null;
  ended_at: string | null;
  /** 1-5, enforced by a CHECK constraint in the database. */
  rating: number | null;
  created_at: string;
}

export interface Lift {
  id: string;
  user_id: string;
  workout_id: string;
  name: string;
  position: number;
  created_at: string;
}

export interface LiftSet {
  id: string;
  user_id: string;
  lift_id: string;
  reps: number;
  weight: number;
  position: number;
  created_at: string;
}

export interface BodyWeight {
  id: string;
  user_id: string;
  date: string;
  weight: number;
  created_at: string;
}

export interface Goal {
  id: string;
  user_id: string;
  goal: string;
  completed: boolean;
  created_at: string;
}

/** One row of the lift_progress view: heaviest set per lift per date. */
export interface LiftProgressRow {
  user_id: string;
  lift_key: string;
  lift_name: string;
  date: string;
  max_weight: number;
}

/** A workout with its lifts and their sets nested, for the detail screen. */
export interface WorkoutDetail extends Workout {
  lifts: (Lift & { lift_sets: LiftSet[] })[];
}
