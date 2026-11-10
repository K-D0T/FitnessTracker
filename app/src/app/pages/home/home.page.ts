import { Component, computed, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router } from '@angular/router';
import { ChartConfiguration } from 'chart.js';
import {
  AlertController,
  IonButton,
  IonButtons,
  IonCheckbox,
  IonContent,
  IonHeader,
  IonIcon,
  IonInput,
  IonItem,
  IonItemOption,
  IonItemOptions,
  IonItemSliding,
  IonLabel,
  IonList,
  IonNote,
  IonRefresher,
  IonRefresherContent,
  IonSpinner,
  IonTitle,
  IonToolbar,
} from '@ionic/angular';
import { addIcons } from 'ionicons';
import { logOutOutline, trashOutline } from 'ionicons/icons';
import { BaseChartDirective } from 'ng2-charts';

import { AuthService } from '../../core/auth.service';
import { BodyWeight, Goal, LiftProgressRow } from '../../core/models';
import { TrackerService } from '../../core/tracker.service';

/** Distinct, colour-blind-safe series colours for the lift chart. */
const SERIES_COLOURS = [
  '#4e79a7',
  '#f28e2b',
  '#59a14f',
  '#e15759',
  '#b07aa1',
  '#76b7b2',
  '#edc948',
  '#9c755f',
];

@Component({
  selector: 'app-home',
  imports: [
    ReactiveFormsModule,
    BaseChartDirective,
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
    IonInput,
    IonLabel,
    IonCheckbox,
    IonNote,
    IonIcon,
    IonSpinner,
    IonItemSliding,
    IonItemOptions,
    IonItemOption,
  ],
  templateUrl: './home.page.html',
  styleUrl: './home.page.scss',
})
export class HomePage {
  private readonly tracker = inject(TrackerService);
  private readonly fb = inject(FormBuilder);
  private readonly router = inject(Router);
  private readonly alerts = inject(AlertController);
  protected readonly auth = inject(AuthService);

  readonly bodyweights = signal<BodyWeight[]>([]);
  readonly goals = signal<Goal[]>([]);
  readonly progress = signal<LiftProgressRow[]>([]);
  readonly loading = signal(true);
  readonly error = signal<string | null>(null);

  readonly weightForm = this.fb.nonNullable.group({
    weight: [null as number | null, [Validators.required, Validators.min(1)]],
    // Blank means today. The Django version exposed this field and then threw
    // the value away, so a weigh-in could never be backdated.
    date: [this.today()],
  });

  readonly goalForm = this.fb.nonNullable.group({
    goal: ['', [Validators.required]],
  });

  constructor() {
    addIcons({ trashOutline, logOutOutline });
  }

  readonly bodyweightChart = computed<ChartConfiguration<'line'>>(() => {
    const rows = this.bodyweights();
    return {
      type: 'line',
      data: {
        labels: rows.map((r) => r.date),
        datasets: [
          {
            label: 'Bodyweight',
            data: rows.map((r) => r.weight),
            borderColor: SERIES_COLOURS[0],
            backgroundColor: SERIES_COLOURS[0],
            tension: 0.3,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: { y: { beginAtZero: false } },
        plugins: { legend: { display: false } },
      },
    };
  });

  readonly liftChart = computed<ChartConfiguration<'line'>>(() => {
    const rows = this.progress();

    // Group by lift. The Django endpoint only ever charted four hardcoded
    // names, so anything else logged was invisible.
    const byLift = new Map<string, { label: string; points: { x: string; y: number }[] }>();
    for (const row of rows) {
      const series = byLift.get(row.lift_key) ?? { label: row.lift_name, points: [] };
      series.points.push({ x: row.date, y: row.max_weight });
      byLift.set(row.lift_key, series);
    }

    const dates = [...new Set(rows.map((r) => r.date))].sort();

    return {
      type: 'line',
      data: {
        labels: dates,
        datasets: [...byLift.values()].map((series, index) => ({
          label: series.label,
          data: dates.map(
            (date) => series.points.find((p) => p.x === date)?.y ?? null,
          ) as (number | null)[],
          borderColor: SERIES_COLOURS[index % SERIES_COLOURS.length],
          backgroundColor: SERIES_COLOURS[index % SERIES_COLOURS.length],
          spanGaps: true,
          tension: 0.3,
        })),
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: { y: { beginAtZero: false } },
      },
    };
  });

  readonly hasBodyweights = computed(() => this.bodyweights().length > 0);
  readonly hasProgress = computed(() => this.progress().length > 0);

  async ionViewWillEnter(): Promise<void> {
    await this.load();
  }

  private today(): string {
    // Local date, not UTC -- an evening weigh-in must not land on tomorrow.
    const now = new Date();
    const offsetMs = now.getTimezoneOffset() * 60_000;
    return new Date(now.getTime() - offsetMs).toISOString().slice(0, 10);
  }

  async load(): Promise<void> {
    this.loading.set(true);
    this.error.set(null);
    try {
      const [bodyweights, goals, progress] = await Promise.all([
        this.tracker.listBodyWeights(),
        this.tracker.listGoals(),
        this.tracker.listLiftProgress(),
      ]);
      this.bodyweights.set(bodyweights);
      this.goals.set(goals);
      this.progress.set(progress);
    } catch (err: unknown) {
      this.error.set(err instanceof Error ? err.message : 'Could not load your data.');
    } finally {
      this.loading.set(false);
    }
  }

  async handleRefresh(event: CustomEvent): Promise<void> {
    await this.load();
    (event.target as HTMLIonRefresherElement | null)?.complete();
  }

  async saveWeight(): Promise<void> {
    if (this.weightForm.invalid) {
      this.weightForm.markAllAsTouched();
      return;
    }
    const { weight, date } = this.weightForm.getRawValue();
    try {
      await this.tracker.saveBodyWeight(Number(weight), date || this.today());
      this.weightForm.patchValue({ weight: null });
      await this.load();
    } catch (err: unknown) {
      this.error.set(err instanceof Error ? err.message : 'Could not save your weight.');
    }
  }

  async addGoal(): Promise<void> {
    if (this.goalForm.invalid) {
      this.goalForm.markAllAsTouched();
      return;
    }
    try {
      await this.tracker.addGoal(this.goalForm.getRawValue().goal);
      this.goalForm.reset({ goal: '' });
      await this.load();
    } catch (err: unknown) {
      this.error.set(err instanceof Error ? err.message : 'Could not add the goal.');
    }
  }

  async toggleGoal(goal: Goal, completed: boolean): Promise<void> {
    // Update locally first so the checkbox responds immediately.
    this.goals.update((all) =>
      all.map((g) => (g.id === goal.id ? { ...g, completed } : g)),
    );
    try {
      await this.tracker.setGoalCompleted(goal.id, completed);
    } catch (err: unknown) {
      this.goals.update((all) =>
        all.map((g) => (g.id === goal.id ? { ...g, completed: !completed } : g)),
      );
      this.error.set(err instanceof Error ? err.message : 'Could not update the goal.');
    }
  }

  async deleteGoal(goal: Goal): Promise<void> {
    try {
      await this.tracker.deleteGoal(goal.id);
      this.goals.update((all) => all.filter((g) => g.id !== goal.id));
    } catch (err: unknown) {
      this.error.set(err instanceof Error ? err.message : 'Could not delete the goal.');
    }
  }

  async signOut(): Promise<void> {
    const alert = await this.alerts.create({
      header: 'Sign out?',
      buttons: [
        { text: 'Cancel', role: 'cancel' },
        { text: 'Sign out', role: 'confirm' },
      ],
    });
    await alert.present();
    const { role } = await alert.onDidDismiss();
    if (role === 'confirm') {
      await this.auth.signOut();
      await this.router.navigateByUrl('/login');
    }
  }
}
