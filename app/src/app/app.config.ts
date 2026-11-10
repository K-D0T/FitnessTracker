import { provideHttpClient } from '@angular/common/http';
import {
  ApplicationConfig,
  provideBrowserGlobalErrorListeners,
  provideZoneChangeDetection,
} from '@angular/core';
import { RouteReuseStrategy, provideRouter, withComponentInputBinding } from '@angular/router';
import { IonicRouteStrategy, provideIonicAngular } from '@ionic/angular';
import { provideCharts, withDefaultRegisterables } from 'ng2-charts';

import { routes } from './app.routes';

export const appConfig: ApplicationConfig = {
  providers: [
    provideBrowserGlobalErrorListeners(),
    // Ionic 9 still drives change detection through NgZone, so this project
    // runs zone-based rather than Angular 22's zoneless default.
    provideZoneChangeDetection({ eventCoalescing: true }),
    provideIonicAngular(),
    // Keeps Ionic page transitions and view caching working with the router.
    { provide: RouteReuseStrategy, useClass: IonicRouteStrategy },
    // withComponentInputBinding() is what binds :id straight to input().
    provideRouter(routes, withComponentInputBinding()),
    provideHttpClient(),
    provideCharts(withDefaultRegisterables()),
  ],
};
