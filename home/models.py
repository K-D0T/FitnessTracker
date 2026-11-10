from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone


class BodyWeight(models.Model):
    weight = models.FloatField(validators=[MinValueValidator(0)])
    # Was null=True, which meant a single null row crashed the homepage when
    # the view called .strftime() on every date. Defaults to today in the
    # project's TIME_ZONE.
    date = models.DateField(default=timezone.localdate)

    def __str__(self):
        return f"{self.weight} on {self.date}"

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

    # Was auto_now_add=True, which made the field non-editable: workouts could
    # never be backdated or corrected. A default keeps new workouts on today
    # while leaving the field editable.
    date = models.DateField(default=timezone.localdate)
    split = models.CharField(
        max_length=2,
        choices=SPLIT_CHOICES,
        default=PUSH,
    )
    start_time = models.DateTimeField(null=True, blank=True)
    end_time = models.DateTimeField(null=True, blank=True)
    rating = models.IntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
    )

    @property
    def duration(self):
        if self.end_time and self.start_time:
            return self.end_time - self.start_time
        return None

    def complete_workout(self):
        self.end_time = timezone.now()
        self.save(update_fields=['end_time'])

    def __str__(self):
        return f"{self.get_split_display()} on {self.date}"

    class Meta:
        ordering = ['date']


class Lift(models.Model):
    workout = models.ForeignKey(Workout, on_delete=models.CASCADE)
    lift = models.CharField(max_length=100)
    sets = models.PositiveIntegerField(null=True, blank=True)

    def __str__(self):
        # Was `return self.lift.name`, but `lift` is a CharField, so this
        # raised AttributeError in the admin, the shell and any {{ lift }}.
        return self.lift

    class Meta:
        ordering = ['id']


class Set(models.Model):
    lift = models.ForeignKey(Lift, on_delete=models.CASCADE)
    weight = models.FloatField(validators=[MinValueValidator(0)])
    reps = models.PositiveIntegerField(validators=[MinValueValidator(1)])

    def __str__(self):
        return f"{self.reps} x {self.weight}"

    class Meta:
        ordering = ['id']


class Goals(models.Model):
    goal = models.CharField(max_length=100)
    completed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True, null=True)

    def __str__(self):
        return self.goal

    class Meta:
        ordering = ['completed', 'created_at', 'id']
