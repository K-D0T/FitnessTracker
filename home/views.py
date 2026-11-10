from django.forms import formset_factory
from django.http import JsonResponse
from django.db.models import Max
from django.shortcuts import render, redirect
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
import json
import random

from .forms import WorkoutForm, LiftForm, SetForm, BodyWeightForm, GoalsForm
from .models import Workout, Lift, Set, BodyWeight, Goals


def get_workout_data(request):
    lift_names = ['bench', 'squat', 'curls', 'db bench']
    data = {}
    for lift_name in lift_names:
        workouts = Workout.objects.filter(lift__lift__iexact=lift_name).annotate(max_weight=Max('lift__set__weight')).order_by('date')
        dates = [workout.date.strftime('%Y-%m-%d') for workout in workouts]
        liftValues = [workout.max_weight for workout in workouts]
        data[lift_name] = {'dates': dates, 'liftValues': liftValues}
    return JsonResponse(data)


@csrf_exempt
def remove_set(request, set_id):
    try:
        set = Set.objects.get(id=set_id)
        lift = set.lift
        set.delete()
        if lift.set_set.count() == 0:
            lift.delete()
        return JsonResponse({'success': True})
    except Set.DoesNotExist:
        return JsonResponse({'success': False})


def home(request):
    if request.method == 'POST':
        bodyWeightForm = BodyWeightForm(request.POST)  # Pass the POST data to the form
        goalForm = GoalsForm(request.POST)
        if goalForm.is_valid():
            goal = goalForm.save(commit=False)
            goal.save()
            return redirect('home:home')
        else: 
            print(goalForm.errors)
        if bodyWeightForm.is_valid():
            body_weight = bodyWeightForm.save(commit=False)
            body_weight.date = timezone.now()
            body_weight.save()
            return redirect('home:home')
        else:
            print(bodyWeightForm.errors)
    else:
        bodyWeightForm = BodyWeightForm()
        goalForm = GoalsForm()
        
    body_weights = BodyWeight.objects.order_by('date')
    dates = [bw.date.strftime('%Y-%m-%d') for bw in body_weights]
    weights = [bw.weight for bw in body_weights]
    goals = Goals.objects.all()


    return render(request, 'home.html', {'bodyWeightForm': bodyWeightForm, 'goalForm': goalForm, 'dates': dates, 'weights': weights, 'goals': goals})


def create_workout(request):
    if request.method == 'POST':
        form = WorkoutForm(request.POST)
        if form.is_valid():
            workout = form.save(commit=False)
            workout.start_time = timezone.now()
            workout.save()
            return redirect('home:add_lifts', workout_id=workout.id)
    else:
        form = WorkoutForm()
    return render(request, 'workout.html', {'form': form})


def add_lifts(request, workout_id):
    SetFormSet = formset_factory(SetForm, extra=1)  # Ensure there's at least one empty form to start with
    workout = Workout.objects.get(id=workout_id)
    workoutType = workout.split  # Define workoutType here
    date = workout.date  # Define date here
    if request.method == 'POST':
        form = LiftForm(request.POST)
        formset = SetFormSet(request.POST, prefix='sets')
        print(form.errors)  # Print form errors
        print(formset.errors)  # Print formset errors
        if form.is_valid() and formset.is_valid():
            print("kaiden")
            lift = form.save(commit=False)
            lift.workout = workout
            lift.sets = len(formset)
            lift.save()
            for form in formset:
                set = form.save(commit=False)
                set.lift = lift
                set.save()
            return redirect('home:workout_detail', workout_id=workout.id)
    else:
        form = LiftForm()
        formset = SetFormSet(prefix='sets')
    return render(request, 'add_lifts.html', {'form': form, 'formset': formset, 'workout': workout, 'workoutType': workoutType, 'date': date})


@csrf_exempt
def rate_workout(request, workout_id):
    if request.method == 'POST':
        data = json.loads(request.body)
        rating = data.get('rating')
        
        # Save the rating to the database (adjust to your models)
        workout = Workout.objects.get(id=workout_id)
        workout.rating = rating
        workout.save()
        
        return JsonResponse({'status': 'success', 'rating': rating})
    return JsonResponse({'status': 'error'}, status=400)


def workout_detail(request, workout_id):
    workout = Workout.objects.get(id=workout_id)
    lifts = Lift.objects.filter(workout_id=workout_id)
    
    workout_data = []
    for lift in lifts:
        sets = Set.objects.filter(lift_id=lift.id).values('id', 'reps', 'weight')
        workout_data.append({'lift': lift, 'sets': sets})
        
    return render(request, 'workout_detail.html', {'workout': workout, 'workout_data': workout_data})

def all_workouts(request):
    workouts = Workout.objects.all()
    workouts_data = []
    for workout in workouts:
        bodyweight = BodyWeight.objects.filter(date=workout.date).first()
        try:
            rating_stars = '⭐' * int(workout.rating)
        except:
            rating_stars = 'No rating'
        workouts_data.append({'workout': workout, 'bodyweight': bodyweight, 'rating_stars': rating_stars})
    return render(request, 'all_workouts.html', {'workouts_data': workouts_data})


def motivation(request):
    with open('home/quotes.txt', 'r') as f:
        lines = f.readlines()
    quote = random.choice(lines)
    return render(request, 'motivation.html', {'quote': quote})


@csrf_exempt
def update_goal(request):
    if request.method == 'POST':
        goal_id = request.POST.get('goalId')
        completed = request.POST.get('completed') == 'true'
        goal = Goals.objects.get(id=goal_id)
        goal.completed = completed
        goal.save()
        return JsonResponse({'status': 'success'})