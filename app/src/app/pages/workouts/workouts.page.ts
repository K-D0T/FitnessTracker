import { Component, inject, signal } from '@angular/core';
import { Router, RouterLink } from '@angular/router';
import {
  ActionSheetController,
  IonBadge,
  IonButton,
  IonButtons,
  IonContent,
  IonHeader,
  IonItem,
  IonLabel,
  IonList,
  IonNote,
  IonRefresher,
  IonRefresherContent,
  IonSpinner,
  IonTitle,
  IonToolbar,
} from '@ionic/angular';

import { SPLIT_LABELS, Workout, WorkoutSplit } from '../../core/models';
import { TrackerService } from '../../core/tracker.service';

interface WorkoutRow {
  workout: Workout;
  bodyweight: number | null;
  stars: string;
}

@Component({
  selector: 'app-workouts',
  imports: [
    RouterLink,
    IonHeader,
    IonToolbar,
    IonTitle,
    IonButtons,
    IonButton,
    IonContent,
    IonRefresher,
    IonRefresherContent,
    IonList,
    IonItem,
    IonLabel,
    IonBadge,
    IonNote,
    IonSpinner,
  ],
  templateUrl: './workouts.page.html',
})
export class WorkoutsPage {
  private readonly tracker = inject(TrackerService);
  private readonly router = inject(Router);
  private readonly actionSheet = inject(ActionSheetController);

  readonly rows = signal<WorkoutRow[]>([]);
  readonly loading = signal(true);
  readonly error = signal<string | null>(null);
  readonly splitLabels = SPLIT_LABELS;

  async ionViewWillEnter(): Promise<void> {
    await this.load();
  }

  async load(): Promise<void> {
    this.loading.set(true);
    this.error.set(null);
    try {
      // Two queries regardless of workout count -- the bodyweight lookup is a
      // map, not a query per row like the Django version did.
      const [workouts, bodyweights] = await Promise.all([
        this.tracker.listWorkouts(),
        this.tracker.listBodyWeights(),
      ]);
      const weightByDate = new Map(bodyweights.map((b) => [b.date, b.weight]));
      this.rows.set(
        workouts.map((workout) => ({
          workout,
          bodyweight: weightByDate.get(workout.date) ?? null,
          stars: workout.rating ? '⭐'.repeat(workout.rating) : 'No rating',
        })),
      );
    } catch (err: unknown) {
      this.error.set(err instanceof Error ? err.message : 'Could not load workouts.');
    } finally {
      this.loading.set(false);
    }
  }

  async handleRefresh(event: CustomEvent): Promise<void> {
    await this.load();
    (event.target as HTMLIonRefresherElement | null)?.complete();
  }

  /** Pick a split, create the workout, then go straight to adding lifts. */
  async startWorkout(): Promise<void> {
    const sheet = await this.actionSheet.create({
      header: 'What are you training?',
      buttons: [
        ...(Object.keys(SPLIT_LABELS) as WorkoutSplit[]).map((split) => ({
          text: SPLIT_LABELS[split],
          data: split,
        })),
        { text: 'Cancel', role: 'cancel' as const },
      ],
    });
    await sheet.present();

    const { data } = await sheet.onDidDismiss<WorkoutSplit>();
    if (!data) {
      return;
    }

    try {
      const workout = await this.tracker.createWorkout(data);
      await this.router.navigate(['/workouts', workout.id, 'add-lift']);
    } catch (err: unknown) {
      this.error.set(err instanceof Error ? err.message : 'Could not start the workout.');
    }
  }
}
