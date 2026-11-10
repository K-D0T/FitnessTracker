import { Injectable, inject } from '@angular/core';
import { PostgrestError } from '@supabase/supabase-js';

import {
  BodyWeight,
  Goal,
  Lift,
  LiftProgressRow,
  Workout,
  WorkoutDetail,
  WorkoutSplit,
} from './models';
import { SupabaseService } from './supabase.service';

interface PostgrestResult<T> {
  data: T | null;
  error: PostgrestError | null;
}

/** Throws on a Postgrest error, otherwise returns the rows. */
function unwrap<T>(result: PostgrestResult<T>): T {
  if (result.error) {
    throw new Error(result.error.message);
  }
  if (result.data === null) {
    throw new Error('Supabase returned no data.');
  }
  return result.data;
}

/** All database access lives here so pages never touch the client directly. */
@Injectable({ providedIn: 'root' })
export class TrackerService {
  private readonly supabase = inject(SupabaseService);

  private get db() {
    return this.supabase.require();
  }

  private async currentUserId(): Promise<string> {
    const { data, error } = await this.db.auth.getUser();
    if (error || !data.user) {
      throw new Error('Not signed in.');
    }
    return data.user.id;
  }

  // -- Workouts -------------------------------------------------------------

  async listWorkouts(): Promise<Workout[]> {
    return unwrap<Workout[]>(
      await this.db.from('workouts').select('*').order('date', { ascending: false }),
    );
  }

  /** A workout with its lifts and sets, sorted client-side by position. */
  async getWorkout(id: string): Promise<WorkoutDetail | null> {
    const { data, error } = await this.db
      .from('workouts')
      .select('*, lifts(*, lift_sets(*))')
      .eq('id', id)
      .maybeSingle();

    if (error) {
      throw new Error(error.message);
    }
    if (!data) {
      return null;
    }

    const workout = data as WorkoutDetail;
    workout.lifts.sort((a, b) => a.position - b.position);
    for (const lift of workout.lifts) {
      lift.lift_sets.sort((a, b) => a.position - b.position);
    }
    return workout;
  }

  async createWorkout(split: WorkoutSplit): Promise<Workout> {
    // user_id and date come from column defaults (auth.uid(), current_date).
    return unwrap<Workout>(
      await this.db
        .from('workouts')
        .insert({ split, started_at: new Date().toISOString() })
        .select()
        .single(),
    );
  }

  async rateWorkout(id: string, rating: number): Promise<void> {
    // The database also enforces this with a CHECK constraint; failing here
    // first gives a clearer message than a constraint violation.
    if (!Number.isInteger(rating) || rating < 1 || rating > 5) {
      throw new Error('Rating must be a whole number from 1 to 5.');
    }
    const { error } = await this.db.from('workouts').update({ rating }).eq('id', id);
    if (error) {
      throw new Error(error.message);
    }
  }

  async finishWorkout(id: string): Promise<void> {
    const { error } = await this.db
      .from('workouts')
      .update({ ended_at: new Date().toISOString() })
      .eq('id', id);
    if (error) {
      throw new Error(error.message);
    }
  }

  async deleteWorkout(id: string): Promise<void> {
    // Lifts and sets go with it via ON DELETE CASCADE.
    const { error } = await this.db.from('workouts').delete().eq('id', id);
    if (error) {
      throw new Error(error.message);
    }
  }

  // -- Lifts and sets -------------------------------------------------------

  /**
   * Adds a lift and its sets. Postgrest has no multi-table transaction, so if
   * the sets fail to insert the lift is deleted again rather than left behind
   * with nothing attached.
   */
  async addLift(
    workoutId: string,
    name: string,
    sets: readonly { reps: number; weight: number }[],
  ): Promise<Lift> {
    const trimmed = name.trim();
    if (!trimmed) {
      throw new Error('Give the lift a name.');
    }
    if (sets.length === 0) {
      throw new Error('Add at least one set.');
    }

    const existing = await this.db
      .from('lifts')
      .select('position')
      .eq('workout_id', workoutId)
      .order('position', { ascending: false })
      .limit(1);
    const nextPosition = ((existing.data?.[0]?.position as number | undefined) ?? -1) + 1;

    const lift = unwrap<Lift>(
      await this.db
        .from('lifts')
        .insert({ workout_id: workoutId, name: trimmed, position: nextPosition })
        .select()
        .single(),
    );

    const { error } = await this.db.from('lift_sets').insert(
      sets.map((set, index) => ({
        lift_id: lift.id,
        reps: set.reps,
        weight: set.weight,
        position: index,
      })),
    );

    if (error) {
      await this.db.from('lifts').delete().eq('id', lift.id);
      throw new Error(error.message);
    }

    return lift;
  }

  /** Deletes a set, and the parent lift too if that was its last one. */
  async removeSet(setId: string): Promise<void> {
    const target = unwrap<{ lift_id: string }>(
      await this.db.from('lift_sets').select('lift_id').eq('id', setId).single(),
    );

    const { error } = await this.db.from('lift_sets').delete().eq('id', setId);
    if (error) {
      throw new Error(error.message);
    }

    const { count } = await this.db
      .from('lift_sets')
      .select('id', { count: 'exact', head: true })
      .eq('lift_id', target.lift_id);

    if (count === 0) {
      await this.db.from('lifts').delete().eq('id', target.lift_id);
    }
  }

  // -- Bodyweight -----------------------------------------------------------

  async listBodyWeights(): Promise<BodyWeight[]> {
    return unwrap<BodyWeight[]>(
      await this.db.from('bodyweights').select('*').order('date', { ascending: true }),
    );
  }

  /** Upserts, so re-entering today's weight corrects it instead of failing. */
  async saveBodyWeight(weight: number, date: string): Promise<void> {
    if (!(weight > 0)) {
      throw new Error('Enter a weight greater than zero.');
    }
    const user_id = await this.currentUserId();
    const { error } = await this.db
      .from('bodyweights')
      .upsert({ user_id, weight, date }, { onConflict: 'user_id,date' });
    if (error) {
      throw new Error(error.message);
    }
  }

  // -- Goals ----------------------------------------------------------------

  async listGoals(): Promise<Goal[]> {
    return unwrap<Goal[]>(
      await this.db
        .from('goals')
        .select('*')
        .order('completed', { ascending: true })
        .order('created_at', { ascending: true }),
    );
  }

  async addGoal(goal: string): Promise<Goal> {
    const trimmed = goal.trim();
    if (!trimmed) {
      throw new Error('Write the goal first.');
    }
    return unwrap<Goal>(
      await this.db.from('goals').insert({ goal: trimmed }).select().single(),
    );
  }

  async setGoalCompleted(id: string, completed: boolean): Promise<void> {
    const { error } = await this.db.from('goals').update({ completed }).eq('id', id);
    if (error) {
      throw new Error(error.message);
    }
  }

  async deleteGoal(id: string): Promise<void> {
    const { error } = await this.db.from('goals').delete().eq('id', id);
    if (error) {
      throw new Error(error.message);
    }
  }

  // -- Progress -------------------------------------------------------------

  /** Heaviest set per lift per date, from the lift_progress view. */
  async listLiftProgress(): Promise<LiftProgressRow[]> {
    return unwrap<LiftProgressRow[]>(
      await this.db.from('lift_progress').select('*').order('date', { ascending: true }),
    );
  }
}
