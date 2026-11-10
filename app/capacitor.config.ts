import type { CapacitorConfig } from '@capacitor/cli';

const config: CapacitorConfig = {
  appId: 'com.kdot.fitnesstracker',
  appName: 'Fitness Tracker',
  // Angular 22 emits the browser build here; Capacitor copies it into the
  // native project with `npx cap sync`.
  webDir: 'dist/app/browser',
  ios: {
    // Lets Ionic lay content out under the notch and home indicator.
    contentInset: 'always',
  },
};

export default config;
