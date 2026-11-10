import { HttpClient } from '@angular/common/http';
import { Component, inject, signal } from '@angular/core';
import {
  IonButton,
  IonContent,
  IonHeader,
  IonTitle,
  IonToolbar,
} from '@ionic/angular';
import { firstValueFrom } from 'rxjs';

@Component({
  selector: 'app-motivation',
  imports: [IonHeader, IonToolbar, IonTitle, IonContent, IonButton],
  template: `
    <ion-header>
      <ion-toolbar>
        <ion-title>Motivation</ion-title>
      </ion-toolbar>
    </ion-header>

    <ion-content class="ion-padding ion-text-center">
      <blockquote class="quote">{{ quote() }}</blockquote>
      <ion-button fill="clear" (click)="shuffle()">Another</ion-button>
    </ion-content>
  `,
  styles: `
    .quote {
      margin: 3rem 1rem;
      font-size: 1.35rem;
      line-height: 1.5;
    }
  `,
})
export class MotivationPage {
  private readonly http = inject(HttpClient);

  private quotes: string[] = [];
  readonly quote = signal('Showing up is the whole trick.');

  async ngOnInit(): Promise<void> {
    try {
      // Ported from the Django app's home/quotes.txt.
      this.quotes = await firstValueFrom(this.http.get<string[]>('quotes.json'));
      this.shuffle();
    } catch {
      // Keep the fallback quote rather than showing an error for this.
    }
  }

  shuffle(): void {
    if (this.quotes.length === 0) {
      return;
    }
    const next = this.quotes[Math.floor(Math.random() * this.quotes.length)];
    this.quote.set(next);
  }
}
