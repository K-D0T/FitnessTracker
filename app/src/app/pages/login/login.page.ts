import { Component, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router } from '@angular/router';
import {
  IonButton,
  IonContent,
  IonHeader,
  IonInput,
  IonItem,
  IonList,
  IonNote,
  IonSpinner,
  IonTitle,
  IonToolbar,
} from '@ionic/angular';

import { AuthService } from '../../core/auth.service';
import { SupabaseService } from '../../core/supabase.service';

@Component({
  selector: 'app-login',
  imports: [
    ReactiveFormsModule,
    IonHeader,
    IonToolbar,
    IonTitle,
    IonContent,
    IonList,
    IonItem,
    IonInput,
    IonButton,
    IonNote,
    IonSpinner,
  ],
  templateUrl: './login.page.html',
})
export class LoginPage {
  private readonly auth = inject(AuthService);
  private readonly supabase = inject(SupabaseService);
  private readonly router = inject(Router);
  private readonly fb = inject(FormBuilder);

  readonly isConfigured = this.supabase.isConfigured;
  readonly mode = signal<'signin' | 'signup'>('signin');
  readonly busy = signal(false);
  readonly error = signal<string | null>(null);

  readonly form = this.fb.nonNullable.group({
    email: ['', [Validators.required, Validators.email]],
    password: ['', [Validators.required, Validators.minLength(8)]],
  });

  toggleMode(): void {
    this.mode.update((m) => (m === 'signin' ? 'signup' : 'signin'));
    this.error.set(null);
  }

  async submit(): Promise<void> {
    if (this.form.invalid || this.busy()) {
      this.form.markAllAsTouched();
      return;
    }

    this.busy.set(true);
    this.error.set(null);
    const { email, password } = this.form.getRawValue();

    try {
      if (this.mode() === 'signin') {
        await this.auth.signIn(email, password);
      } else {
        await this.auth.signUp(email, password);
      }
      await this.router.navigateByUrl('/home');
    } catch (err: unknown) {
      this.error.set(err instanceof Error ? err.message : 'Something went wrong.');
    } finally {
      this.busy.set(false);
    }
  }
}
