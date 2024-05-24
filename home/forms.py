from django import forms
from .models import Workout, Lift, Set, BodyWeight, Goals
from django.utils import timezone

class WorkoutForm(forms.ModelForm):
    class Meta:
        model = Workout
        fields = ['split']


class LiftForm(forms.ModelForm):

    class Meta:
        model = Lift
        fields = ['lift', 'sets']


class SetForm(forms.ModelForm):
    class Meta:
        model = Set
        fields = ['reps', 'weight']


class BodyWeightForm(forms.ModelForm):
    class Meta:
        model = BodyWeight
        fields = ['weight', 'date']


class GoalsForm(forms.ModelForm):
    class Meta:
        model = Goals
        fields = ['goal']