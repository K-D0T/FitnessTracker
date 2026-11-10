import { Component, inject, input, signal } from '@angular/core';
import { Router, RouterLink } from '@angular/router';
import {
  AlertController,
  IonAccordion,
  IonAccordionGroup,
  IonBackButton,
  IonButton,
  IonButtons,
  IonContent,
  IonFooter,
  IonHeader,
  IonIcon,
  IonItem,
  IonLabel,
  IonList,
  IonNote,
  IonSpinner,
  IonTitle,
  IonToolbar,
} from '@ionic/angular';
import { addIcons } from 'ionicons';
import { star, starOutline, trashOutline } from 'ionicons/icons';

import { SPLIT_LABELS, WorkoutDetail } from '../../core/models';
import { TrackerService } from '../../core/tracker.service';

@Component({
  selector: 'app-workout-detail',
  imports: [
    RouterLink,
    IonHeader,
    IonToolbar,
    IonTitle,
    IonButtons,
    IonBackButton,
    IonButton,
    IonContent,
    IonList,
    IonItem,
    IonLabel,
    IonNote,
    IonIcon,
    IonSpinner,
    IonAccordionGroup,
    IonAccordion,
    IonFooter,
  ],
  templateUrl: './workout-detail.page.html',
})
export class WorkoutDetailPage {
  /** Bound from the route via withComponentInputBinding(). */
  readonly id = input.required<string>();

  private readonly tracker = inject(TrackerService);
  private readonly router = inject(Router);
  private readonly alerts = inject(AlertController);

  readonly workout = signal<WorkoutDetail | null>(null);
  readonly loading = signal(true);
  readonly error = signal<string | null>(null);
  readonly stars = [1, 2, 3, 4, 5];
  readonly splitLabels = SPLIT_LABELS;

  constructor() {
    addIcons({ star, starOutline, trashOutline });
  }

  async ionViewWillEnter(): Promise<void> {
    await this.load();
  }

  async load(): Promise<void> {
    this.loading.set(true);
    this.error.set(null);
    try {
      const workout = await this.tracker.getWorkout(this.id());
      if (!workout) {
        this.error.set('That workout no longer exists.');
      }
      this.workout.set(workout);
    } catch (err: unknown) {
      this.error.set(err instanceof Error ? err.message : 'Could not load the workout.');
    } finally {
      this.loading.set(false);
    }
  }

  totalSets(): number {
    return (this.workout()?.lifts ?? []).reduce((sum, lift) => sum + lift.lift_sets.length, 0);
  }

  async rate(rating: number): Promise<void> {
    try {
      await this.tracker.rateWorkout(this.id(), rating);
      const current = this.workout();
      if (current) {
        this.workout.set({ ...current, rating });
      }
    } catch (err: unknown) {
      this.error.set(err instanceof Error ? err.message : 'Could not save the rating.');
    }
  }

  /** Confirms first -- deleting a set is not undoable. */
  async confirmRemoveSet(setId: string): Promise<void> {
    const alert = await this.alerts.create({
      header: 'Delete this set?',
      message: 'The lift is removed too if this was its last set.',
      buttons: [
        { text: 'Cancel', role: 'cancel' },
        { text: 'Delete', role: 'destructive' },
      ],
    });
    await alert.present();

    const { role } = await alert.onDidDismiss();
    if (role !== 'destructive') {
      return;
    }

    try {
      await this.tracker.removeSet(setId);
      await this.load();
    } catch (err: unknown) {
      this.error.set(err instanceof Error ? err.message : 'Could not delete the set.');
    }
  }

  async confirmDeleteWorkout(): Promise<void> {
    const alert = await this.alerts.create({
      header: 'Delete this workout?',
      message: 'Its lifts and sets go with it. This cannot be undone.',
      buttons: [
        { text: 'Cancel', role: 'cancel' },
        { text: 'Delete', role: 'destructive' },
      ],
    });
    await alert.present();

    const { role } = await alert.onDidDismiss();
    if (role !== 'destructive') {
      return;
    }

    try {
      await this.tracker.deleteWorkout(this.id());
      await this.router.navigateByUrl('/workouts');
    } catch (err: unknown) {
      this.error.set(err instanceof Error ? err.message : 'Could not delete the workout.');
    }
  }
}
