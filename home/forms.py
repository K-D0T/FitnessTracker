from django import forms
from django.utils import timezone

from .models import Workout, Lift, Set, BodyWeight, Goals


class WorkoutForm(forms.ModelForm):
    class Meta:
        model = Workout
        fields = ['split']


class LiftForm(forms.ModelForm):
    class Meta:
        # `sets` is derived from the submitted set rows in the view rather than
        # entered by hand, and the template never rendered it.
        model = Lift
        fields = ['lift']


class SetForm(forms.ModelForm):
    class Meta:
        model = Set
        fields = ['reps', 'weight']


class BodyWeightForm(forms.ModelForm):
    # Optional so the compact homepage form can submit weight alone; a blank
    # date means today. The view used to overwrite whatever was submitted here
    # with timezone.now(), so a date could never actually be chosen.
    date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date'}),
        help_text='Leave blank for today.',
    )

    class Meta:
        model = BodyWeight
        fields = ['weight', 'date']

    def clean_date(self):
        return self.cleaned_data.get('date') or timezone.localdate()


class GoalsForm(forms.ModelForm):
    class Meta:
        model = Goals
        fields = ['goal']
