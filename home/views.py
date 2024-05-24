from django.shortcuts import render, redirect
from .forms import WorkoutForm, LiftForm, SetForm, BodyWeightForm, GoalsForm
from .models import Workout, Lift, Set, BodyWeight, Goals
from django.utils import timezone
from django.forms import formset_factory
from django.http import JsonResponse
from collections import defaultdict
import time
from django.db.models import Max
from django.views.decorators.csrf import csrf_exempt
from openai import OpenAI
from dotenv import load_dotenv
import os
import json
from django.core.exceptions import ObjectDoesNotExist
from datetime import datetime, timedelta
import random
# Load the environment variables from the .env file
load_dotenv()

# Ensure API key is set
if "OPENAI_API_KEY" not in os.environ:
    raise Exception("OPENAI_API_KEY environment variable not set")

client = OpenAI()

'''
@csrf_exempt
def generate_workout(request):
    # Get the user's previous workouts
    previous_workouts = Workout.objects.all()

    # Format the previous workouts into a string
    previous_workouts_str = format_workouts(previous_workouts)
    print(previous_workouts_str)
    # Generate a response from the OpenAI model

    completion = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are a certified physical trainer. You are to take in the information provided givin body weight, different lifts and weights, and provide a new workout plan for the user. Please format the workout plan as follows: 'Workout: {workout_name}, Lifts: [{lift_name, sets: [{set_reps, set_weight}, ...]}, ...]"},
            {"role": "user", "content": previous_workouts_str}
        ]
    )
    

    # Get the workout plan from the response
    workout_plan = completion.choices[0].message.content

    print(workout_plan)
    # Save the workout plan to the database
    save_workout_plan(workout_plan)

    return JsonResponse({'success': True})


def format_workouts(workouts):
    # Format the workouts into a list of dictionaries
    formatted_workouts = []
    for workout in workouts:
        lifts = Lift.objects.filter(workout=workout)
        formatted_workout = {
            'workout_name': workout.split,
            'lifts': [{'lift_name': lift.lift, 'sets': [{'set_reps': set.reps, 'set_weight': set.weight} for set in Set.objects.filter(lift=lift)]} for lift in lifts]
        }
        formatted_workouts.append(formatted_workout)

    # Convert the list of dictionaries into a JSON string
    return json.dumps(formatted_workouts)



def save_workout_plan(workout_plans):
    # Parse the workout plans from a JSON string into a list
    workout_plans = json.loads(workout_plans)

    # Get the current date
    current_date = datetime.now().date()

    # Loop through the workout plans
    for i, workout_plan in enumerate(workout_plans):
        # Create a new workout with a date
        workout = Workout(split=workout_plan['workout_name'], date=current_date + timedelta(days=i))
        workout.save()

        # Create the lifts and sets for the workout
        for lift_data in workout_plan['lifts']:
            lift = Lift(workout=workout, lift=lift_data['lift_name'], sets=len(lift_data['sets']))
            lift.save()
            for set_data in lift_data['sets']:
                set = Set(lift=lift, weight=set_data['set_weight'], reps=set_data['set_reps'])
                set.save()
'''

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