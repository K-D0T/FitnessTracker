/**
 * Supabase connection settings.
 *
 * The publishable (anon) key is designed to ship to the browser -- it carries
 * no privileges of its own. Every table is protected by Row Level Security,
 * so the key alone grants no access to anyone's data. This is unlike the
 * Django SECRET_KEY, which had to stay private.
 *
 * Never put the service_role key here. That one bypasses RLS entirely.
 */
export const environment = {
  production: false,
  supabaseUrl: '',
  supabasePublishableKey: '',
};
