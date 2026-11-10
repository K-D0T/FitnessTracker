import { Routes } from '@angular/router';

import { authGuard, guestGuard } from './core/auth.guard';

export const routes: Routes = [
  {
    path: 'login',
    canActivate: [guestGuard],
    loadComponent: () => import('./pages/login/login.page').then((m) => m.LoginPage),
  },
  {
    path: '',
    canActivate: [authGuard],
    loadComponent: () => import('./pages/tabs/tabs.page').then((m) => m.TabsPage),
    children: [
      { path: '', pathMatch: 'full', redirectTo: 'home' },
      {
        path: 'home',
        loadComponent: () => import('./pages/home/home.page').then((m) => m.HomePage),
      },
      {
        path: 'workouts',
        loadComponent: () =>
          import('./pages/workouts/workouts.page').then((m) => m.WorkoutsPage),
      },
      {
        path: 'workouts/:id',
        loadComponent: () =>
          import('./pages/workout-detail/workout-detail.page').then(
            (m) => m.WorkoutDetailPage,
          ),
      },
      {
        path: 'workouts/:id/add-lift',
        loadComponent: () =>
          import('./pages/add-lift/add-lift.page').then((m) => m.AddLiftPage),
      },
      {
        path: 'motivation',
        loadComponent: () =>
          import('./pages/motivation/motivation.page').then((m) => m.MotivationPage),
      },
    ],
  },
  { path: '**', redirectTo: '' },
];
