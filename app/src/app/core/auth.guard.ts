import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';

import { AuthService } from './auth.service';

/** Blocks a route until a session is restored, then requires a signed-in user. */
export const authGuard: CanActivateFn = async (_route, state) => {
  const auth = inject(AuthService);
  const router = inject(Router);

  await auth.ready;

  if (auth.isSignedIn()) {
    return true;
  }

  return router.createUrlTree(['/login'], {
    queryParams: { next: state.url },
  });
};

/** Keeps signed-in users off the login screen. */
export const guestGuard: CanActivateFn = async () => {
  const auth = inject(AuthService);
  const router = inject(Router);

  await auth.ready;

  return auth.isSignedIn() ? router.createUrlTree(['/home']) : true;
};
