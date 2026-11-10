"""Regression tests for the issues found in the initial code review.

Each test names the behaviour it pins down. The security tests exist because
the originals were all reachable by an anonymous user.
"""

import datetime
import json

import importlib

from django.contrib.auth.models import User
from django.db import connection
from django.test import TestCase, override_settings
from django.test.utils import CaptureQueriesContext
from django.urls import Resolver404, clear_url_caches, resolve, reverse
from django.utils import timezone

from .models import BodyWeight, Goals, Lift, Set, Workout

PASSWORD = 'test-password-12345'


class AuthenticatedTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('tester', password=PASSWORD)
        self.client.force_login(self.user)

    def make_workout(self, **kwargs):
        return Workout.objects.create(**{'split': Workout.PUSH, **kwargs})

    def make_lift_with_set(self, workout=None, lift='Bench Press', weight=100, reps=5):
        workout = workout or self.make_workout()
        lift_obj = Lift.objects.create(workout=workout, lift=lift, sets=1)
        set_obj = Set.objects.create(lift=lift_obj, weight=weight, reps=reps)
        return lift_obj, set_obj

    def count_queries(self, url):
        with CaptureQueriesContext(connection) as captured:
            response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        return len(captured)


SENSITIVE_PATHS = (
    '/db.sqlite3',
    '/fitnesstracker/settings.py',
    '/manage.py',
    '/home/views.py',
    '/requirements.txt',
    '/.env',
)


class NoFileDisclosureTests(TestCase):
    """urls.py used to register a catch-all route serving the project directory.

    static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT) with both
    settings undefined became static('/', document_root=''), i.e. a
    ^(?P<path>.*)$ route rooted at the working directory. GET /db.sqlite3
    returned the whole database and GET /fitnesstracker/settings.py returned
    the SECRET_KEY.
    """

    def test_source_and_database_are_not_served(self):
        for path in SENSITIVE_PATHS:
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 404)

    def test_no_catch_all_route_exists_even_with_debug_on(self):
        """The important case: the old route was behind `if settings.DEBUG`.

        Tests run with DEBUG=False, so an HTTP request alone would pass against
        the vulnerable code. Reload the URLconf with DEBUG on and assert that
        nothing resolves these paths.
        """
        from fitnesstracker import urls as project_urls
        try:
            with override_settings(DEBUG=True):
                importlib.reload(project_urls)
                clear_url_caches()
                for path in SENSITIVE_PATHS:
                    with self.subTest(path=path):
                        with self.assertRaises(Resolver404):
                            resolve(path, urlconf=project_urls)
        finally:
            importlib.reload(project_urls)
            clear_url_caches()


class LoginRequiredTests(TestCase):
    """Every view holds personal health data and must require a session."""

    def setUp(self):
        self.workout = Workout.objects.create(split=Workout.PUSH)

    def test_all_views_redirect_anonymous_users_to_login(self):
        urls = [
            reverse('home:home'),
            reverse('home:create_workout'),
            reverse('home:all_workouts'),
            reverse('home:motivation'),
            reverse('home:get_workout_data'),
            reverse('home:add_lifts', args=[self.workout.id]),
            reverse('home:workout_detail', args=[self.workout.id]),
        ]
        for url in urls:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 302)
                self.assertIn('/accounts/login/', response['Location'])

    def test_write_endpoints_reject_anonymous_users(self):
        lift = Lift.objects.create(workout=self.workout, lift='Bench', sets=1)
        set_obj = Set.objects.create(lift=lift, weight=100, reps=5)
        goal = Goals.objects.create(goal='Bench 225')

        cases = [
            (reverse('home:remove_set', args=[set_obj.id]), {}),
            (reverse('home:update_goal'), {'goalId': goal.id, 'completed': 'true'}),
        ]
        for url, data in cases:
            with self.subTest(url=url):
                response = self.client.post(url, data)
                self.assertEqual(response.status_code, 302)
                self.assertIn('/accounts/login/', response['Location'])

        # Nothing was mutated.
        self.assertEqual(Set.objects.count(), 1)
        goal.refresh_from_db()
        self.assertFalse(goal.completed)


class RemoveSetTests(AuthenticatedTestCase):
    """remove_set was @csrf_exempt with no method check, so a bare GET deleted."""

    def test_get_does_not_delete(self):
        _, set_obj = self.make_lift_with_set()
        response = self.client.get(reverse('home:remove_set', args=[set_obj.id]))
        self.assertEqual(response.status_code, 405)
        self.assertEqual(Set.objects.count(), 1)
        self.assertEqual(Lift.objects.count(), 1)

    def test_post_deletes_the_set(self):
        _, set_obj = self.make_lift_with_set()
        response = self.client.post(reverse('home:remove_set', args=[set_obj.id]))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['success'])
        self.assertEqual(Set.objects.count(), 0)

    def test_deleting_the_last_set_removes_the_empty_lift(self):
        lift, set_obj = self.make_lift_with_set()
        Set.objects.create(lift=lift, weight=110, reps=3)
        self.client.post(reverse('home:remove_set', args=[set_obj.id]))
        self.assertEqual(Lift.objects.count(), 1, 'lift still has one set')
        self.client.post(reverse('home:remove_set', args=[Set.objects.get().id]))
        self.assertEqual(Lift.objects.count(), 0, 'empty lift should be removed')

    def test_missing_set_returns_404(self):
        response = self.client.post(reverse('home:remove_set', args=[9999]))
        self.assertEqual(response.status_code, 404)
        self.assertFalse(response.json()['success'])


class RateWorkoutTests(AuthenticatedTestCase):
    """The endpoint used to store any integer, 99 included."""

    def post_rating(self, workout, body):
        return self.client.post(
            reverse('home:rate_workout', args=[workout.id]),
            body,
            content_type='application/json',
        )

    def test_valid_rating_is_stored(self):
        workout = self.make_workout()
        response = self.post_rating(workout, json.dumps({'rating': 4}))
        self.assertEqual(response.status_code, 200)
        workout.refresh_from_db()
        self.assertEqual(workout.rating, 4)

    def test_out_of_range_rating_is_rejected(self):
        workout = self.make_workout()
        for bad in (0, 6, 99, -3):
            with self.subTest(rating=bad):
                response = self.post_rating(workout, json.dumps({'rating': bad}))
                self.assertEqual(response.status_code, 400)
        workout.refresh_from_db()
        self.assertIsNone(workout.rating)

    def test_malformed_payloads_are_rejected(self):
        workout = self.make_workout()
        for body in ('not json', json.dumps({'rating': 'five'}), json.dumps({})):
            with self.subTest(body=body):
                self.assertEqual(self.post_rating(workout, body).status_code, 400)

    def test_get_is_not_allowed(self):
        workout = self.make_workout()
        response = self.client.get(reverse('home:rate_workout', args=[workout.id]))
        self.assertEqual(response.status_code, 405)


class UpdateGoalTests(AuthenticatedTestCase):
    """A GET used to fall off the end of the view returning None -> 500."""

    def test_get_returns_405_not_500(self):
        response = self.client.get(reverse('home:update_goal'))
        self.assertEqual(response.status_code, 405)

    def test_post_toggles_completion(self):
        goal = Goals.objects.create(goal='Bench 225')
        self.client.post(reverse('home:update_goal'),
                         {'goalId': goal.id, 'completed': 'true'})
        goal.refresh_from_db()
        self.assertTrue(goal.completed)

        self.client.post(reverse('home:update_goal'),
                         {'goalId': goal.id, 'completed': 'false'})
        goal.refresh_from_db()
        self.assertFalse(goal.completed)

    def test_unknown_goal_returns_404(self):
        response = self.client.post(reverse('home:update_goal'),
                                    {'goalId': 9999, 'completed': 'true'})
        self.assertEqual(response.status_code, 404)


class ModelTests(TestCase):
    def test_lift_str_returns_the_name(self):
        # Was `return self.lift.name` on a CharField -> AttributeError.
        workout = Workout.objects.create(split=Workout.PUSH)
        lift = Lift.objects.create(workout=workout, lift='Bench Press', sets=3)
        self.assertEqual(str(lift), 'Bench Press')

    def test_workout_date_is_editable_and_defaults_to_today(self):
        # Was auto_now_add=True, so the field was non-editable entirely.
        self.assertFalse(Workout._meta.get_field('date').auto_now_add)
        self.assertTrue(Workout._meta.get_field('date').editable)
        self.assertEqual(Workout.objects.create(split=Workout.PUSH).date,
                         timezone.localdate())

        backdated = Workout.objects.create(split=Workout.PULL,
                                           date=datetime.date(2024, 1, 15))
        backdated.refresh_from_db()
        self.assertEqual(backdated.date, datetime.date(2024, 1, 15))

    def test_bodyweight_date_is_not_nullable(self):
        # A single null row used to 500 the homepage via .strftime().
        self.assertFalse(BodyWeight._meta.get_field('date').null)
        self.assertEqual(BodyWeight.objects.create(weight=200).date,
                         timezone.localdate())

    def test_workout_duration(self):
        start = timezone.now()
        workout = Workout.objects.create(
            split=Workout.PUSH, start_time=start,
            end_time=start + datetime.timedelta(minutes=75))
        self.assertEqual(workout.duration, datetime.timedelta(minutes=75))
        self.assertIsNone(Workout.objects.create(split=Workout.PUSH).duration)


class HomeViewTests(AuthenticatedTestCase):
    def test_bodyweight_submission_honours_the_submitted_date(self):
        # The view used to overwrite the form's date with timezone.now().
        response = self.client.post(reverse('home:home'), {
            'form_type': 'bodyweight', 'weight': '198.6', 'date': '2024-03-01',
        })
        self.assertEqual(response.status_code, 302)
        entry = BodyWeight.objects.get()
        self.assertEqual(entry.date, datetime.date(2024, 3, 1))
        self.assertAlmostEqual(entry.weight, 198.6)

    def test_bodyweight_submission_without_a_date_uses_today(self):
        self.client.post(reverse('home:home'),
                         {'form_type': 'bodyweight', 'weight': '201.4'})
        self.assertEqual(BodyWeight.objects.get().date, timezone.localdate())

    def test_goal_submission_goes_to_the_goal_form(self):
        response = self.client.post(reverse('home:home'),
                                    {'form_type': 'goal', 'goal': 'Squat 315'})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Goals.objects.get().goal, 'Squat 315')
        self.assertEqual(BodyWeight.objects.count(), 0)

    def test_the_two_forms_do_not_interfere(self):
        # Both post to this URL; a hidden form_type says which one.
        self.client.post(reverse('home:home'),
                         {'form_type': 'bodyweight', 'weight': '200'})
        self.client.post(reverse('home:home'),
                         {'form_type': 'goal', 'goal': 'Deadlift 405'})
        self.assertEqual(BodyWeight.objects.count(), 1)
        self.assertEqual(Goals.objects.count(), 1)

    def test_invalid_bodyweight_redisplays_the_page(self):
        response = self.client.post(reverse('home:home'),
                                    {'form_type': 'bodyweight', 'weight': 'heavy'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(BodyWeight.objects.count(), 0)

    def test_homepage_renders_with_bodyweight_history(self):
        BodyWeight.objects.create(weight=200, date=datetime.date(2024, 5, 1))
        BodyWeight.objects.create(weight=199, date=datetime.date(2024, 5, 2))
        response = self.client.get(reverse('home:home'))
        self.assertEqual(response.status_code, 200)
        # Chart data goes through json_script, not |safe.
        self.assertContains(response, 'id="bodyweight-dates"')
        self.assertContains(response, 'id="bodyweight-weights"')


class WorkoutDataTests(AuthenticatedTestCase):
    def test_lifts_outside_the_old_hardcoded_list_are_included(self):
        # The view used to iterate ['bench', 'squat', 'curls', 'db bench'], so
        # anything else a user logged never reached the chart.
        workout = self.make_workout(date=datetime.date(2024, 6, 1))
        self.make_lift_with_set(workout, lift='Romanian Deadlift', weight=225, reps=5)

        data = self.client.get(reverse('home:get_workout_data')).json()
        self.assertIn('Romanian Deadlift', data)
        self.assertEqual(data['Romanian Deadlift']['dates'], ['2024-06-01'])
        self.assertEqual(data['Romanian Deadlift']['liftValues'], [225.0])

    def test_reports_the_heaviest_set_per_lift(self):
        workout = self.make_workout(date=datetime.date(2024, 6, 1))
        lift, _ = self.make_lift_with_set(workout, lift='Bench Press', weight=185, reps=5)
        Set.objects.create(lift=lift, weight=205, reps=1)
        Set.objects.create(lift=lift, weight=195, reps=3)

        data = self.client.get(reverse('home:get_workout_data')).json()
        self.assertEqual(data['Bench Press']['liftValues'], [205.0])

    def test_lift_names_are_grouped_case_insensitively(self):
        first = self.make_workout(date=datetime.date(2024, 6, 1))
        second = self.make_workout(date=datetime.date(2024, 6, 8))
        self.make_lift_with_set(first, lift='Bench Press', weight=185)
        self.make_lift_with_set(second, lift='bench press', weight=195)

        data = self.client.get(reverse('home:get_workout_data')).json()
        self.assertEqual(len(data), 1)
        series = data['Bench Press']
        self.assertEqual(series['dates'], ['2024-06-01', '2024-06-08'])
        self.assertEqual(series['liftValues'], [185.0, 195.0])

    def test_query_count_does_not_grow_with_the_number_of_lifts(self):
        # Was one query per name in a hardcoded list; now one grouped query.
        url = reverse('home:get_workout_data')
        workout = self.make_workout()
        for name in ('Bench', 'Squat'):
            self.make_lift_with_set(workout, lift=name)
        with_two = self.count_queries(url)

        for name in ('Row', 'Curl', 'Press', 'Dip', 'Fly', 'Lunge'):
            self.make_lift_with_set(workout, lift=name)
        with_eight = self.count_queries(url)

        self.assertEqual(with_two, with_eight,
                         'lift count should not change the query count')


class AllWorkoutsTests(AuthenticatedTestCase):
    def seed(self, days):
        for day in days:
            date = datetime.date(2024, 7, day)
            self.make_workout(date=date)
            BodyWeight.objects.create(weight=200 - day, date=date)

    def test_bodyweight_lookup_does_not_scale_with_workout_count(self):
        # Was a BodyWeight query per workout (1 + N).
        url = reverse('home:all_workouts')
        self.seed(range(1, 4))
        with_three = self.count_queries(url)

        self.seed(range(4, 16))
        with_fifteen = self.count_queries(url)

        self.assertEqual(with_three, with_fifteen,
                         'workout count should not change the query count')

    def test_rating_renders_as_stars_and_tolerates_no_rating(self):
        self.make_workout(date=datetime.date(2024, 7, 1), rating=3)
        self.make_workout(date=datetime.date(2024, 7, 2))
        response = self.client.get(reverse('home:all_workouts'))
        ratings = [row['rating_stars'] for row in response.context['workouts_data']]
        self.assertIn('⭐' * 3, ratings)
        self.assertIn('No rating', ratings)

    def test_split_label_is_rendered(self):
        self.make_workout(split=Workout.LEGS)
        response = self.client.get(reverse('home:all_workouts'))
        self.assertContains(response, 'Legs Workout')


class WorkoutDetailTests(AuthenticatedTestCase):
    def test_sets_are_prefetched(self):
        # Was 1 + N: one Set query per lift.
        workout = self.make_workout()
        url = reverse('home:workout_detail', args=[workout.id])
        for name in ('Bench', 'Incline'):
            self.make_lift_with_set(workout, lift=name)
        with_two = self.count_queries(url)

        for name in ('Dip', 'Fly', 'Pushdown', 'Press', 'Raise', 'Crossover'):
            self.make_lift_with_set(workout, lift=name)
        with_eight = self.count_queries(url)

        self.assertEqual(with_two, with_eight,
                         'lift count should not change the query count')

    def test_unknown_workout_returns_404(self):
        response = self.client.get(reverse('home:workout_detail', args=[9999]))
        self.assertEqual(response.status_code, 404)

    def test_workout_with_no_sets_still_has_a_csrf_token(self):
        # The old template emitted an empty <form> per set row purely to
        # produce a token, so a workout with no sets had none and the AJAX
        # calls would be rejected once CSRF was enforced.
        workout = self.make_workout()
        self.assertEqual(Set.objects.count(), 0)
        response = self.client.get(
            reverse('home:workout_detail', args=[workout.id]))
        self.assertContains(response, 'name="csrfmiddlewaretoken"')


class AddLiftsTests(AuthenticatedTestCase):
    def post_lift(self, workout, rows):
        data = {
            'lift': 'Bench Press',
            'sets-TOTAL_FORMS': str(len(rows)),
            'sets-INITIAL_FORMS': '0',
            'sets-MIN_NUM_FORMS': '0',
            'sets-MAX_NUM_FORMS': '1000',
        }
        for index, row in enumerate(rows):
            data[f'sets-{index}-reps'] = row.get('reps', '')
            data[f'sets-{index}-weight'] = row.get('weight', '')
        return self.client.post(
            reverse('home:add_lifts', args=[workout.id]), data)

    def test_saves_a_lift_with_its_sets(self):
        workout = self.make_workout()
        response = self.post_lift(workout, [
            {'reps': '5', 'weight': '185'},
            {'reps': '3', 'weight': '195'},
        ])
        self.assertEqual(response.status_code, 302)
        lift = Lift.objects.get()
        self.assertEqual(lift.lift, 'Bench Press')
        self.assertEqual(Set.objects.count(), 2)
        self.assertEqual(lift.sets, 2, 'set count should match the real rows')

    def test_blank_formset_rows_are_ignored(self):
        # The old view counted blank extra forms as sets and called
        # save(commit=False) on them.
        workout = self.make_workout()
        self.post_lift(workout, [{'reps': '5', 'weight': '185'}, {}])
        self.assertEqual(Set.objects.count(), 1)
        self.assertEqual(Lift.objects.get().sets, 1)

    def test_a_lift_with_no_sets_is_rejected(self):
        workout = self.make_workout()
        response = self.post_lift(workout, [{}])
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Lift.objects.count(), 0)
        self.assertContains(response, 'Add at least one set')


class CreateWorkoutTests(AuthenticatedTestCase):
    def test_creates_a_workout_and_redirects_to_add_lifts(self):
        response = self.client.post(reverse('home:create_workout'),
                                    {'split': Workout.LEGS})
        workout = Workout.objects.get()
        self.assertEqual(workout.split, Workout.LEGS)
        self.assertIsNotNone(workout.start_time)
        self.assertRedirects(
            response, reverse('home:add_lifts', args=[workout.id]))


class MotivationTests(AuthenticatedTestCase):
    def test_renders_a_quote_from_the_quotes_file(self):
        from . import views
        self.assertTrue(views.QUOTES, 'quotes.txt should load at import time')
        response = self.client.get(reverse('home:motivation'))
        self.assertEqual(response.status_code, 200)
        self.assertIn(response.context['quote'], views.QUOTES)

    def test_quotes_contain_no_blank_entries(self):
        from . import views
        self.assertTrue(all(q.strip() for q in views.QUOTES))
