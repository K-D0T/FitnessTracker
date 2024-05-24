from django.db import models
from django.utils import timezone

class BodyWeight(models.Model):
    weight = models.FloatField()
    date = models.DateField(null=True, blank=True)

    def __str__(self):
        return str(self.weight)
    
    class Meta:
        ordering = ['date']

class Workout(models.Model):
    PUSH = 'PU'
    PULL = 'PL'
    LEGS = 'LG'
    ARMS = 'AR'
    SPLIT_CHOICES = [
        (PUSH, 'Push'),
        (PULL, 'Pull'),
        (LEGS, 'Legs'),
        (ARMS, 'Arms'),
    ]

    date = models.DateField(auto_now_add=True)
    split = models.CharField(
        max_length=2,
        choices=SPLIT_CHOICES,
        default=PUSH,
    )
    start_time = models.DateTimeField(null=True, blank=True)
    end_time = models.DateTimeField(null=True, blank=True)
    rating = models.IntegerField(null=True, blank=True)

    @property
    def duration(self):
        if self.end_time and self.start_time:
            return self.end_time - self.start_time
        else:
            return None

    def complete_workout(self):
        self.end_time = timezone.now()
        self.save()

    def __str__(self):
        return f"{self.get_split_display()}"

    class Meta:
        ordering = ['date']


class Lift(models.Model):
    workout = models.ForeignKey(Workout, on_delete=models.CASCADE)
    lift = models.CharField(max_length=100)
    sets = models.IntegerField(null=True, blank=True)

    def __str__(self):
        return self.lift.name
    
    
class Set(models.Model):
    lift = models.ForeignKey(Lift, on_delete=models.CASCADE)
    weight = models.FloatField()
    reps = models.IntegerField()


class Goals(models.Model):
    goal = models.CharField(max_length=100)
    completed = models.BooleanField(default=False)

    def __str__(self):
        return self.goal
