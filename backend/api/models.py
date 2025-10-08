from django.db import models
from django.contrib.auth.models import User


class TimeStampedModel(models.Model):
    """Abstract base for created/updated timestamps."""
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class UserProfile(TimeStampedModel):
    """Extended profile containing role and coach-client relations."""
    ROLE_ADMIN = "admin"
    ROLE_COACH = "coach"
    ROLE_CLIENT = "client"
    ROLE_CHOICES = [
        (ROLE_ADMIN, "Admin"),
        (ROLE_COACH, "Coach"),
        (ROLE_CLIENT, "Client"),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=ROLE_CLIENT)
    bio = models.TextField(blank=True, default="")

    def __str__(self):
        return f"{self.user.username} ({self.role})"


class ClientProfile(TimeStampedModel):
    """Client-specific data and association to coach."""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="client_profile")
    coach = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name="clients")
    goals = models.TextField(blank=True, default="")
    start_date = models.DateField(null=True, blank=True)


class Food(TimeStampedModel):
    name = models.CharField(max_length=255)
    brand = models.CharField(max_length=255, blank=True, default="")
    calories = models.FloatField(default=0)
    protein = models.FloatField(default=0)
    carbs = models.FloatField(default=0)
    fat = models.FloatField(default=0)
    serving_size = models.CharField(max_length=100, blank=True, default="")


class Recipe(TimeStampedModel):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name="recipes")


class RecipeIngredient(models.Model):
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE, related_name="ingredients")
    food = models.ForeignKey(Food, on_delete=models.CASCADE)
    quantity = models.FloatField(default=0)
    unit = models.CharField(max_length=50, blank=True, default="")


class Exercise(TimeStampedModel):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    equipment = models.CharField(max_length=255, blank=True, default="")
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name="exercises")


class Workout(TimeStampedModel):
    name = models.CharField(max_length=255)
    notes = models.TextField(blank=True, default="")
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name="workouts")


class WorkoutExercise(models.Model):
    workout = models.ForeignKey(Workout, on_delete=models.CASCADE, related_name="items")
    exercise = models.ForeignKey(Exercise, on_delete=models.CASCADE)
    order = models.PositiveIntegerField(default=0)
    sets = models.PositiveIntegerField(default=3)
    reps = models.PositiveIntegerField(default=10)
    rest_seconds = models.PositiveIntegerField(default=60)


class Habit(TimeStampedModel):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name="habits")


class HabitAssignment(TimeStampedModel):
    habit = models.ForeignKey(Habit, on_delete=models.CASCADE, related_name="assignments")
    client = models.ForeignKey(User, on_delete=models.CASCADE, related_name="habit_assignments")
    frequency_per_week = models.PositiveIntegerField(default=7)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)


class HabitLog(TimeStampedModel):
    assignment = models.ForeignKey(HabitAssignment, on_delete=models.CASCADE, related_name="logs")
    date = models.DateField()
    completed = models.BooleanField(default=False)
    notes = models.TextField(blank=True, default="")

    class Meta:
        unique_together = ("assignment", "date")


class Plan(TimeStampedModel):
    """General plan which can include meals/workouts/habits."""
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    coach = models.ForeignKey(User, on_delete=models.CASCADE, related_name="plans")
    client = models.ForeignKey(User, on_delete=models.CASCADE, related_name="assigned_plans")


class PlanItem(models.Model):
    TYPE_MEAL = "meal"
    TYPE_WORKOUT = "workout"
    TYPE_HABIT = "habit"
    TYPE_CHOICES = [(TYPE_MEAL, "Meal"), (TYPE_WORKOUT, "Workout"), (TYPE_HABIT, "Habit")]
    plan = models.ForeignKey(Plan, on_delete=models.CASCADE, related_name="items")
    item_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    # For meal - store recipe name or free-text,
    # For workout - reference workout ID,
    # For habit - reference habit ID.
    reference_id = models.IntegerField(null=True, blank=True)
    text = models.CharField(max_length=255, blank=True, default="")
    day = models.PositiveIntegerField(default=1)
    order = models.PositiveIntegerField(default=0)


class MealLog(TimeStampedModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="meal_logs")
    food = models.ForeignKey(Food, null=True, blank=True, on_delete=models.SET_NULL)
    recipe = models.ForeignKey(Recipe, null=True, blank=True, on_delete=models.SET_NULL)
    date = models.DateField()
    quantity = models.FloatField(default=1.0)
    notes = models.TextField(blank=True, default="")


class WorkoutLog(TimeStampedModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="workout_logs")
    workout = models.ForeignKey(Workout, null=True, blank=True, on_delete=models.SET_NULL)
    date = models.DateField()
    duration_min = models.PositiveIntegerField(default=0)
    notes = models.TextField(blank=True, default="")


class Measurement(TimeStampedModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="measurements")
    date = models.DateField()
    weight_kg = models.FloatField(null=True, blank=True)
    body_fat_pct = models.FloatField(null=True, blank=True)
    waist_cm = models.FloatField(null=True, blank=True)
    notes = models.TextField(blank=True, default="")


class Conversation(TimeStampedModel):
    """Chat conversation between users (coach-client)."""
    title = models.CharField(max_length=255, blank=True, default="")
    participants = models.ManyToManyField(User, related_name="conversations")


class Message(TimeStampedModel):
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name="messages_sent")
    content = models.TextField()


class Subscription(TimeStampedModel):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="subscription")
    status = models.CharField(max_length=50, default="inactive")  # active, past_due, canceled
    plan_name = models.CharField(max_length=100, default="free")
    current_period_end = models.DateTimeField(null=True, blank=True)


class Invoice(TimeStampedModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="invoices")
    amount_cents = models.PositiveIntegerField()
    currency = models.CharField(max_length=10, default="usd")
    status = models.CharField(max_length=50, default="open")  # paid, open, void
    due_date = models.DateField(null=True, blank=True)


class AnalyticsEvent(TimeStampedModel):
    user = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name="analytics_events")
    event_type = models.CharField(max_length=100)
    data = models.JSONField(default=dict)


class FileUpload(TimeStampedModel):
    """File metadata; actual storage may be local or Supabase depending on env."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="files")
    path = models.CharField(max_length=512)
    original_name = models.CharField(max_length=255)
    size_bytes = models.BigIntegerField(default=0)
    content_type = models.CharField(max_length=100, blank=True, default="")
