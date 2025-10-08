from django.contrib.auth.models import User
from rest_framework import serializers

from .models import (
    UserProfile, ClientProfile, Food, Recipe, RecipeIngredient, Exercise, Workout,
    WorkoutExercise, Habit, HabitAssignment, HabitLog, Plan, PlanItem, MealLog,
    WorkoutLog, Measurement, Conversation, Message, Subscription, Invoice,
    AnalyticsEvent, FileUpload
)


class UserSerializer(serializers.ModelSerializer):
    # PUBLIC_INTERFACE
    class Meta:
        model = User
        fields = ["id", "username", "email", "first_name", "last_name"]


class UserProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    # PUBLIC_INTERFACE
    class Meta:
        model = UserProfile
        fields = ["id", "user", "role", "bio", "created_at", "updated_at"]


class ClientProfileSerializer(serializers.ModelSerializer):
    # PUBLIC_INTERFACE
    class Meta:
        model = ClientProfile
        fields = ["id", "user", "coach", "goals", "start_date", "created_at", "updated_at"]


class FoodSerializer(serializers.ModelSerializer):
    # PUBLIC_INTERFACE
    class Meta:
        model = Food
        fields = "__all__"


class RecipeIngredientSerializer(serializers.ModelSerializer):
    # PUBLIC_INTERFACE
    class Meta:
        model = RecipeIngredient
        fields = ["id", "food", "quantity", "unit"]


class RecipeSerializer(serializers.ModelSerializer):
    ingredients = RecipeIngredientSerializer(many=True, required=False)

    # PUBLIC_INTERFACE
    class Meta:
        model = Recipe
        fields = ["id", "name", "description", "owner", "ingredients", "created_at", "updated_at"]

    def create(self, validated_data):
        ingredients = validated_data.pop("ingredients", [])
        recipe = Recipe.objects.create(**validated_data)
        for ing in ingredients:
            RecipeIngredient.objects.create(recipe=recipe, **ing)
        return recipe

    def update(self, instance, validated_data):
        ingredients = validated_data.pop("ingredients", None)
        for attr, val in validated_data.items():
            setattr(instance, attr, val)
        instance.save()
        if ingredients is not None:
            instance.ingredients.all().delete()
            for ing in ingredients:
                RecipeIngredient.objects.create(recipe=instance, **ing)
        return instance


class ExerciseSerializer(serializers.ModelSerializer):
    # PUBLIC_INTERFACE
    class Meta:
        model = Exercise
        fields = "__all__"


class WorkoutExerciseSerializer(serializers.ModelSerializer):
    # PUBLIC_INTERFACE
    class Meta:
        model = WorkoutExercise
        fields = ["id", "exercise", "order", "sets", "reps", "rest_seconds"]


class WorkoutSerializer(serializers.ModelSerializer):
    items = WorkoutExerciseSerializer(many=True, required=False)

    # PUBLIC_INTERFACE
    class Meta:
        model = Workout
        fields = ["id", "name", "notes", "owner", "items", "created_at", "updated_at"]

    def create(self, validated_data):
        items = validated_data.pop("items", [])
        workout = Workout.objects.create(**validated_data)
        for item in items:
            WorkoutExercise.objects.create(workout=workout, **item)
        return workout

    def update(self, instance, validated_data):
        items = validated_data.pop("items", None)
        for attr, val in validated_data.items():
            setattr(instance, attr, val)
        instance.save()
        if items is not None:
            instance.items.all().delete()
            for item in items:
                WorkoutExercise.objects.create(workout=instance, **item)
        return instance


class HabitSerializer(serializers.ModelSerializer):
    # PUBLIC_INTERFACE
    class Meta:
        model = Habit
        fields = "__all__"


class HabitAssignmentSerializer(serializers.ModelSerializer):
    # PUBLIC_INTERFACE
    class Meta:
        model = HabitAssignment
        fields = "__all__"


class HabitLogSerializer(serializers.ModelSerializer):
    # PUBLIC_INTERFACE
    class Meta:
        model = HabitLog
        fields = "__all__"


class PlanItemSerializer(serializers.ModelSerializer):
    # PUBLIC_INTERFACE
    class Meta:
        model = PlanItem
        fields = "__all__"


class PlanSerializer(serializers.ModelSerializer):
    items = PlanItemSerializer(many=True, required=False)

    # PUBLIC_INTERFACE
    class Meta:
        model = Plan
        fields = ["id", "name", "description", "coach", "client", "items", "created_at", "updated_at"]

    def create(self, validated_data):
        items = validated_data.pop("items", [])
        plan = Plan.objects.create(**validated_data)
        for it in items:
            PlanItem.objects.create(plan=plan, **it)
        return plan

    def update(self, instance, validated_data):
        items = validated_data.pop("items", None)
        for attr, val in validated_data.items():
            setattr(instance, attr, val)
        instance.save()
        if items is not None:
            instance.items.all().delete()
            for it in items:
                PlanItem.objects.create(plan=instance, **it)
        return instance


class MealLogSerializer(serializers.ModelSerializer):
    # PUBLIC_INTERFACE
    class Meta:
        model = MealLog
        fields = "__all__"


class WorkoutLogSerializer(serializers.ModelSerializer):
    # PUBLIC_INTERFACE
    class Meta:
        model = WorkoutLog
        fields = "__all__"


class MeasurementSerializer(serializers.ModelSerializer):
    # PUBLIC_INTERFACE
    class Meta:
        model = Measurement
        fields = "__all__"


class ConversationSerializer(serializers.ModelSerializer):
    # PUBLIC_INTERFACE
    class Meta:
        model = Conversation
        fields = ["id", "title", "participants", "created_at", "updated_at"]


class MessageSerializer(serializers.ModelSerializer):
    # PUBLIC_INTERFACE
    class Meta:
        model = Message
        fields = ["id", "conversation", "sender", "content", "created_at", "updated_at"]


class SubscriptionSerializer(serializers.ModelSerializer):
    # PUBLIC_INTERFACE
    class Meta:
        model = Subscription
        fields = "__all__"


class InvoiceSerializer(serializers.ModelSerializer):
    # PUBLIC_INTERFACE
    class Meta:
        model = Invoice
        fields = "__all__"


class AnalyticsEventSerializer(serializers.ModelSerializer):
    # PUBLIC_INTERFACE
    class Meta:
        model = AnalyticsEvent
        fields = "__all__"


class FileUploadSerializer(serializers.ModelSerializer):
    # PUBLIC_INTERFACE
    class Meta:
        model = FileUpload
        fields = "__all__"
