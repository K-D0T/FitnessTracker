import { Component, inject, input, signal } from '@angular/core';
import { FormArray, FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router } from '@angular/router';
import {
  IonBackButton,
  IonButton,
  IonButtons,
  IonContent,
  IonHeader,
  IonIcon,
  IonInput,
  IonItem,
  IonList,
  IonNote,
  IonSpinner,
  IonTitle,
  IonToolbar,
} from '@ionic/angular';
import { addIcons } from 'ionicons';
import { closeCircleOutline } from 'ionicons/icons';

import { TrackerService } from '../../core/tracker.service';

@Component({
  selector: 'app-add-lift',
  imports: [
    ReactiveFormsModule,
    IonHeader,
    IonToolbar,
    IonTitle,
    IonButtons,
    IonBackButton,
    IonButton,
    IonContent,
    IonList,
    IonItem,
    IonInput,
    IonIcon,
    IonNote,
    IonSpinner,
  ],
  templateUrl: './add-lift.page.html',
})
export class AddLiftPage {
  readonly workoutId = input.required<string>({ alias: 'id' });

  private readonly tracker = inject(TrackerService);
  private readonly router = inject(Router);
  private readonly fb = inject(FormBuilder);

  readonly busy = signal(false);
  readonly error = signal<string | null>(null);

  readonly form = this.fb.nonNullable.group({
    name: ['', [Validators.required]],
    sets: this.fb.nonNullable.array([this.makeSetGroup()]),
  });

  constructor() {
    addIcons({ closeCircleOutline });
  }

  get sets(): FormArray {
    return this.form.controls.sets;
  }

  private makeSetGroup() {
    return this.fb.nonNullable.group({
      reps: [null as number | null, [Validators.required, Validators.min(1)]],
      weight: [null as number | null, [Validators.required, Validators.min(0)]],
    });
  }

  addSet(): void {
    // Carry the previous set's numbers forward -- you usually repeat them.
    const previous = this.sets.at(this.sets.length - 1)?.getRawValue() as
      | { reps: number | null; weight: number | null }
      | undefined;
    const group = this.makeSetGroup();
    if (previous) {
      group.patchValue({ reps: previous.reps, weight: previous.weight });
    }
    this.sets.push(group);
  }

  removeSet(index: number): void {
    // Always leave one row on screen to type into.
    if (this.sets.length > 1) {
      this.sets.removeAt(index);
    } else {
      this.sets.at(0).reset();
    }
  }

  async save(): Promise<void> {
    if (this.busy()) {
      return;
    }
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      this.error.set('Fill in reps and weight for every set.');
      return;
    }

    this.busy.set(true);
    this.error.set(null);

    const { name, sets } = this.form.getRawValue();

    try {
      await this.tracker.addLift(
        this.workoutId(),
        name,
        sets.map((set) => ({ reps: Number(set.reps), weight: Number(set.weight) })),
      );
      await this.router.navigate(['/workouts', this.workoutId()]);
    } catch (err: unknown) {
      this.error.set(err instanceof Error ? err.message : 'Could not save the lift.');
    } finally {
      this.busy.set(false);
    }
  }
}
