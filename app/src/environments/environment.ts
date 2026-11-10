/**
 * Supabase connection settings.
 *
 * The publishable key is designed to ship to the browser -- it carries no
 * privileges of its own. Every table has Row Level Security enabled with an
 * owner-only policy granted to `authenticated`, so this key alone reads
 * nothing. That is why it is committed, unlike the Django SECRET_KEY.
 *
 * Never put the service_role key here: that one bypasses RLS entirely and
 * belongs only in an Edge Function's secrets.
 */
export const environment = {
  production: false,
  supabaseUrl: 'https://clyqroonsrmjbltcldif.supabase.co',
  supabasePublishableKey: 'sb_publishable_mqHAradGBnioN3abowA8JA_NVSFWri8',
};
