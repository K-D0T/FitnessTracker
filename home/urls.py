from django.urls import path
from django.contrib import admin
from . import views

app_name = 'home'

urlpatterns = [
    path('', views.home, name='home'),
    path('create_workout/', views.create_workout, name='create_workout'),
    path('add_lifts/<int:workout_id>/', views.add_lifts, name='add_lifts'),
    path('workout_detail/<int:workout_id>/', views.workout_detail, name='workout_detail'),
    path('all_workouts/', views.all_workouts, name='all_workouts'),
    path('get_workout_data/', views.get_workout_data, name='get_workout_data'),
    path('remove_set/<int:set_id>/', views.remove_set, name='remove_set'),
    path('rate_workout/<int:workout_id>/', views.rate_workout, name='rate_workout'),
    path('motivation/', views.motivation, name='motivation'),
    path('update_goal/', views.update_goal, name='update_goal'),
    #path('generate_workout/', views.generate_workout, name='generate_workout'),

]
