from django.contrib import admin
from .models import (
    UserProfile, ClientProfile, Food, Recipe, RecipeIngredient, Exercise, Workout,
    WorkoutExercise, Habit, HabitAssignment, HabitLog, Plan, PlanItem, MealLog,
    WorkoutLog, Measurement, Conversation, Message, Subscription, Invoice,
    AnalyticsEvent, FileUpload
)

models_to_register = [
    UserProfile, ClientProfile, Food, Recipe, RecipeIngredient, Exercise, Workout,
    WorkoutExercise, Habit, HabitAssignment, HabitLog, Plan, PlanItem, MealLog,
    WorkoutLog, Measurement, Conversation, Message, Subscription, Invoice,
    AnalyticsEvent, FileUpload
]
for m in models_to_register:
    try:
        admin.site.register(m)
    except admin.sites.AlreadyRegistered:
        pass
