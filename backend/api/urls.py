from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    health,
    LoginView,
    RefreshView,
    me,
    FoodViewSet, RecipeViewSet, ExerciseViewSet, WorkoutViewSet,
    HabitViewSet, HabitAssignmentViewSet, HabitLogViewSet,
    PlanViewSet,
    MealLogViewSet, WorkoutLogViewSet, MeasurementViewSet,
    ConversationViewSet, MessageViewSet,
    SubscriptionViewSet, InvoiceViewSet,
    AnalyticsEventViewSet,
)

router = DefaultRouter()
router.register(r"foods", FoodViewSet, basename="food")
router.register(r"recipes", RecipeViewSet, basename="recipe")
router.register(r"exercises", ExerciseViewSet, basename="exercise")
router.register(r"workouts", WorkoutViewSet, basename="workout")
router.register(r"habits", HabitViewSet, basename="habit")
router.register(r"habit-assignments", HabitAssignmentViewSet, basename="habit-assignment")
router.register(r"habit-logs", HabitLogViewSet, basename="habit-log")
router.register(r"plans", PlanViewSet, basename="plan")
router.register(r"meal-logs", MealLogViewSet, basename="meal-log")
router.register(r"workout-logs", WorkoutLogViewSet, basename="workout-log")
router.register(r"measurements", MeasurementViewSet, basename="measurement")
router.register(r"chat/conversations", ConversationViewSet, basename="conversation")
router.register(r"chat/messages", MessageViewSet, basename="message")
router.register(r"billing/subscription", SubscriptionViewSet, basename="subscription")
router.register(r"billing/invoices", InvoiceViewSet, basename="invoice")
router.register(r"analytics/events", AnalyticsEventViewSet, basename="analytics-event")

urlpatterns = [
    path('health/', health, name='Health'),
    # Auth
    path('auth/login', LoginView.as_view(), name='auth-login'),
    path('auth/refresh', RefreshView.as_view(), name='auth-refresh'),
    path('users/me', me, name='users-me'),
    # API sets
    path('', include(router.urls)),
]
