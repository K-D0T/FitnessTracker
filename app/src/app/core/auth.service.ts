import { Injectable, computed, inject, signal } from '@angular/core';
import { Session, User } from '@supabase/supabase-js';

import { SupabaseService } from './supabase.service';

@Injectable({ providedIn: 'root' })
export class AuthService {
  private readonly supabase = inject(SupabaseService);

  private readonly sessionSignal = signal<Session | null>(null);
  readonly session = this.sessionSignal.asReadonly();
  readonly user = computed<User | null>(() => this.sessionSignal()?.user ?? null);
  readonly isSignedIn = computed(() => this.user() !== null);

  /** Resolves once the stored session has been restored from disk. */
  readonly ready: Promise<void>;

  constructor() {
    const client = this.supabase.client;

    if (!client) {
      this.ready = Promise.resolve();
      return;
    }

    this.ready = client.auth.getSession().then(({ data }) => {
      this.sessionSignal.set(data.session);
    });

    client.auth.onAuthStateChange((_event, session) => {
      this.sessionSignal.set(session);
    });
  }

  async signIn(email: string, password: string): Promise<void> {
    const { error } = await this.supabase
      .require()
      .auth.signInWithPassword({ email, password });
    if (error) {
      throw error;
    }
  }

  async signUp(email: string, password: string): Promise<void> {
    const { error } = await this.supabase.require().auth.signUp({ email, password });
    if (error) {
      throw error;
    }
  }

  async signOut(): Promise<void> {
    await this.supabase.require().auth.signOut();
  }
}
