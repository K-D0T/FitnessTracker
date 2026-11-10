from django.contrib import admin

from .models import BodyWeight, Goals, Lift, Set, Workout


class SetInline(admin.TabularInline):
    model = Set
    extra = 1


@admin.register(Workout)
class WorkoutAdmin(admin.ModelAdmin):
    list_display = ('date', 'split', 'rating', 'duration')
    list_filter = ('split', 'date')
    date_hierarchy = 'date'


@admin.register(Lift)
class LiftAdmin(admin.ModelAdmin):
    list_display = ('lift', 'workout', 'sets')
    list_filter = ('workout__split',)
    search_fields = ('lift',)
    inlines = [SetInline]


@admin.register(Set)
class SetAdmin(admin.ModelAdmin):
    list_display = ('lift', 'reps', 'weight')


@admin.register(BodyWeight)
class BodyWeightAdmin(admin.ModelAdmin):
    list_display = ('date', 'weight')
    date_hierarchy = 'date'


@admin.register(Goals)
class GoalsAdmin(admin.ModelAdmin):
    list_display = ('goal', 'completed', 'created_at')
    list_filter = ('completed',)
    search_fields = ('goal',)
