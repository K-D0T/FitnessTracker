from collections import OrderedDict
import json
import random

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.db.models import Max
from django.forms import formset_factory
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import WorkoutForm, LiftForm, SetForm, BodyWeightForm, GoalsForm
from .models import Workout, Lift, Set, BodyWeight, Goals

# Read once at import, from an absolute path. The view used to call
# open('home/quotes.txt') on every request, which depended on the process
# working directory and broke under any server not started from the repo root.
_QUOTES_PATH = settings.BASE_DIR / 'home' / 'quotes.txt'
try:
    QUOTES = [
        line.strip()
        for line in _QUOTES_PATH.read_text(encoding='utf-8').splitlines()
        if line.strip()
    ]
except OSError:
    QUOTES = []

FALLBACK_QUOTE = 'Showing up is the whole trick.'


@login_required
def home(request):
    bodyWeightForm = BodyWeightForm()
    goalForm = GoalsForm()

    if request.method == 'POST':
        # Both forms post to this URL, so a hidden form_type says which one was
        # submitted. Previously each form was validated against the other's
        # POST data and the goal branch returned first, which only worked
        # because neither form's required fields appeared in the other.
        form_type = request.POST.get('form_type')
        if form_type == 'goal':
            goalForm = GoalsForm(request.POST)
            if goalForm.is_valid():
                goalForm.save()
                return redirect('home:home')
        elif form_type == 'bodyweight':
            bodyWeightForm = BodyWeightForm(request.POST)
            if bodyWeightForm.is_valid():
                bodyWeightForm.save()
                return redirect('home:home')

    body_weights = BodyWeight.objects.order_by('date')
    context = {
        'bodyWeightForm': bodyWeightForm,
        'goalForm': goalForm,
        'dates': [bw.date.strftime('%Y-%m-%d') for bw in body_weights],
        'weights': [bw.weight for bw in body_weights],
        'goals': Goals.objects.all(),
    }
    return render(request, 'home.html', context)


@login_required
def get_workout_data(request):
    """Heaviest set per lift per workout date, for the progress chart."""
    # The lift list used to be hardcoded to four names, so every other lift a
    # user logged was silently missing from the chart. One grouped query now
    # replaces the per-name loop.
    rows = (
        Set.objects
        .values('lift__lift', 'lift__workout__date')
        .annotate(max_weight=Max('weight'))
        .order_by('lift__workout__date')
    )

    data = OrderedDict()
    for row in rows:
        name = (row['lift__lift'] or '').strip()
        date = row['lift__workout__date']
        if not name or date is None:
            continue
        # Group case-insensitively, keeping the first spelling seen, which
        # preserves the old __iexact matching behaviour.
        key = name.lower()
        series = data.setdefault(key, {'label': name, 'dates': [], 'liftValues': []})
        series['dates'].append(date.strftime('%Y-%m-%d'))
        series['liftValues'].append(row['max_weight'])

    return JsonResponse(
        {series['label']: {'dates': series['dates'], 'liftValues': series['liftValues']}
         for series in data.values()}
    )


@login_required
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



@login_required
def add_lifts(request, workout_id):
    SetFormSet = formset_factory(SetForm, extra=1)
    workout = get_object_or_404(Workout, id=workout_id)
    error = None

    if request.method == 'POST':
        form = LiftForm(request.POST)
        formset = SetFormSet(request.POST, prefix='sets')
        if form.is_valid() and formset.is_valid():
            # Only forms the user actually filled in. The old code iterated
            # every form, including the blank extra one, and set
            # lift.sets = len(formset) -- counting blanks as real sets.
            new_sets = [f.save(commit=False) for f in formset if f.has_changed()]
            if new_sets:
                lift = form.save(commit=False)
                lift.workout = workout
                lift.sets = len(new_sets)
                lift.save()
                for new_set in new_sets:
                    new_set.lift = lift
                    new_set.save()
                return redirect('home:workout_detail', workout_id=workout.id)
            error = 'Add at least one set before saving.'
    else:
        form = LiftForm()
        formset = SetFormSet(prefix='sets')

    return render(request, 'add_lifts.html', {
        'form': form,
        'formset': formset,
        'workout': workout,
        'workoutType': workout.get_split_display(),
        'date': workout.date,
        'error': error,
    })


@login_required
def workout_detail(request, workout_id):
    workout = get_object_or_404(Workout, id=workout_id)
    # prefetch_related turns 1 + N queries into 2.
    lifts = Lift.objects.filter(workout=workout).prefetch_related('set_set')
    workout_data = [{'lift': lift, 'sets': lift.set_set.all()} for lift in lifts]
    return render(request, 'workout_detail.html', {
        'workout': workout,
        'workout_data': workout_data,
    })


@login_required
def all_workouts(request):
    # One query for every bodyweight instead of one per workout.
    weight_by_date = dict(BodyWeight.objects.values_list('date', 'weight'))

    workouts_data = []
    for workout in Workout.objects.all():
        rating = workout.rating
        workouts_data.append({
            'workout': workout,
            'bodyweight': weight_by_date.get(workout.date),
            'rating_stars': '⭐' * rating if rating else 'No rating',
        })
    return render(request, 'all_workouts.html', {'workouts_data': workouts_data})


@login_required
def motivation(request):
    quote = random.choice(QUOTES) if QUOTES else FALLBACK_QUOTE
    return render(request, 'motivation.html', {'quote': quote})


@login_required
@require_POST
def remove_set(request, set_id):
    # Was @csrf_exempt with no method check, so a bare GET deleted the set and
    # cascade-deleted its lift -- reachable by any crawler or link preview.
    try:
        target = Set.objects.get(id=set_id)
    except Set.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Set not found'}, status=404)

    lift = target.lift
    target.delete()
    if not lift.set_set.exists():
        lift.delete()
    return JsonResponse({'success': True})


@login_required
@require_POST
def rate_workout(request, workout_id):
    workout = get_object_or_404(Workout, id=workout_id)

    try:
        payload = json.loads(request.body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({'status': 'error', 'error': 'Invalid JSON'}, status=400)

    try:
        rating = int(payload.get('rating'))
    except (TypeError, ValueError):
        return JsonResponse(
            {'status': 'error', 'error': 'rating must be an integer'}, status=400
        )

    # The endpoint previously stored anything, including 99.
    if not 1 <= rating <= 5:
        return JsonResponse(
            {'status': 'error', 'error': 'rating must be between 1 and 5'}, status=400
        )

    workout.rating = rating
    workout.save(update_fields=['rating'])
    return JsonResponse({'status': 'success', 'rating': rating})


@login_required
@require_POST
def update_goal(request):
    # require_POST replaces the old implicit `return None` on GET, which made
    # Django raise "didn't return an HttpResponse" and serve a 500.
    goal = get_object_or_404(Goals, id=request.POST.get('goalId'))
    goal.completed = request.POST.get('completed') == 'true'
    goal.save(update_fields=['completed'])
    return JsonResponse({'status': 'success'})
