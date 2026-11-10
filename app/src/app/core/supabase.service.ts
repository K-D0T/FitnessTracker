import { Injectable } from '@angular/core';
import { SupabaseClient, createClient } from '@supabase/supabase-js';

import { environment } from '../../environments/environment';

/**
 * Holds the single Supabase client.
 *
 * If the environment has not been filled in yet the service stays
 * unconfigured rather than throwing, so the app can boot and show a setup
 * message instead of a blank screen.
 */
@Injectable({ providedIn: 'root' })
export class SupabaseService {
  readonly client: SupabaseClient | null;

  constructor() {
    const { supabaseUrl, supabasePublishableKey } = environment;

    if (!supabaseUrl || !supabasePublishableKey) {
      console.error(
        'Supabase is not configured. Set supabaseUrl and ' +
          'supabasePublishableKey in src/environments/environment.ts',
      );
      this.client = null;
      return;
    }

    this.client = createClient(supabaseUrl, supabasePublishableKey, {
      auth: {
        persistSession: true,
        autoRefreshToken: true,
        // No OAuth redirect flow yet; email + password only.
        detectSessionInUrl: false,
      },
    });
  }

  get isConfigured(): boolean {
    return this.client !== null;
  }

  /** Narrowing helper so callers get a non-null client or a clear error. */
  require(): SupabaseClient {
    if (!this.client) {
      throw new Error('Supabase is not configured.');
    }
    return this.client;
  }
}
