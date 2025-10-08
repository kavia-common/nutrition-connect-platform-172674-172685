from datetime import timedelta
import json
import logging
from typing import Optional

import jwt
import requests
from django.db.models import Count
from django.utils import timezone
from rest_framework import permissions, viewsets
from rest_framework.decorators import api_view, action, permission_classes
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from django.conf import settings
from .models import (
    UserProfile, Food, Recipe, Exercise, Workout,
    Habit, HabitAssignment, HabitLog, Plan, MealLog,
    WorkoutLog, Measurement, Conversation, Message, Subscription, Invoice,
    AnalyticsEvent
)
from .serializers import (
    UserSerializer, FoodSerializer,
    RecipeSerializer, ExerciseSerializer, WorkoutSerializer, HabitSerializer,
    HabitAssignmentSerializer, HabitLogSerializer, PlanSerializer, MealLogSerializer,
    WorkoutLogSerializer, MeasurementSerializer, ConversationSerializer, MessageSerializer,
    SubscriptionSerializer, InvoiceSerializer, AnalyticsEventSerializer
)

logger = logging.getLogger(__name__)


# Role-based permissions
class IsAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_staff)


class IsCoach(permissions.BasePermission):
    def has_permission(self, request, view):
        try:
            return request.user.is_authenticated and request.user.profile.role == UserProfile.ROLE_COACH
        except Exception:
            return False


class IsClient(permissions.BasePermission):
    def has_permission(self, request, view):
        try:
            return request.user.is_authenticated and request.user.profile.role == UserProfile.ROLE_CLIENT
        except Exception:
            return False


# Supabase JWT helper (optional, non-blocking)
# This helper is designed to fail gracefully: JWKS fetch or verification failures
# do NOT prevent API startup or local JWT auth from functioning.
def _fetch_jwks(jwks_url: str) -> Optional[dict]:
    try:
        resp = requests.get(jwks_url, timeout=5)
        if resp.ok:
            return resp.json()
    except Exception as e:
        # Keep warnings low-noise; do not raise
        logger.warning("JWKS fetch failed: %s", e)
    return None


def _verify_supabase_jwt(token: str) -> bool:
    if not settings.USE_SUPABASE_AUTH or not settings.SUPABASE_JWKS_URL:
        return False
    jwks = _fetch_jwks(settings.SUPABASE_JWKS_URL)
    if not jwks:
        return False
    try:
        unverified_header = jwt.get_unverified_header(token)
        for key in jwks.get("keys", []):
            if key.get("kid") == unverified_header.get("kid"):
                public_key = jwt.algorithms.RSAAlgorithm.from_jwk(json.dumps(key))
                jwt.decode(
                    token,
                    public_key,
                    algorithms=[unverified_header.get("alg", "RS256")],
                    audience=None,
                    options={"verify_aud": False},
                )
                return True
    except Exception as e:
        logger.info("Supabase JWT verification failed: %s", e)
    return False


# JWT Auth serializers/views
class MyTokenObtainPairSerializer(TokenObtainPairSerializer):
    # PUBLIC_INTERFACE
    def validate(self, attrs):
        data = super().validate(attrs)
        profile = UserProfile.objects.filter(user=self.user).first()
        data["user"] = UserSerializer(self.user).data
        data["role"] = profile.role if profile else "client"
        return data


# PUBLIC_INTERFACE
class LoginView(TokenObtainPairView):
    """JWT login endpoint returning access/refresh tokens and user info."""
    serializer_class = MyTokenObtainPairSerializer


# PUBLIC_INTERFACE
class RefreshView(TokenRefreshView):
    """JWT refresh endpoint."""
    pass


# Basic health endpoint
@api_view(['GET'])
def health(request):
    """Healthcheck returning 200 OK with message."""
    return Response({"message": "Server is up!"})


# ViewSets
class BaseOwnedModelViewSet(viewsets.ModelViewSet):
    """Base class to auto-assign owner to request.user when creating."""
    owner_field = "owner"

    def perform_create(self, serializer):
        if self.owner_field in [f.name for f in serializer.Meta.model._meta.fields]:
            serializer.save(**{self.owner_field: self.request.user})
        else:
            serializer.save()


# PUBLIC_INTERFACE
class FoodViewSet(BaseOwnedModelViewSet):
    """CRUD for foods with search/filter."""
    queryset = Food.objects.all().order_by("-id")
    serializer_class = FoodSerializer
    filterset_fields = ["brand"]
    search_fields = ["name", "brand"]
    permission_classes = [permissions.IsAuthenticated]


# PUBLIC_INTERFACE
class RecipeViewSet(BaseOwnedModelViewSet):
    queryset = Recipe.objects.all().order_by("-id")
    serializer_class = RecipeSerializer
    permission_classes = [permissions.IsAuthenticated]


# PUBLIC_INTERFACE
class ExerciseViewSet(BaseOwnedModelViewSet):
    queryset = Exercise.objects.all().order_by("-id")
    serializer_class = ExerciseSerializer
    permission_classes = [permissions.IsAuthenticated]


# PUBLIC_INTERFACE
class WorkoutViewSet(BaseOwnedModelViewSet):
    queryset = Workout.objects.all().order_by("-id")
    serializer_class = WorkoutSerializer
    permission_classes = [permissions.IsAuthenticated]


# PUBLIC_INTERFACE
class HabitViewSet(BaseOwnedModelViewSet):
    queryset = Habit.objects.all().order_by("-id")
    serializer_class = HabitSerializer
    permission_classes = [permissions.IsAuthenticated]


# PUBLIC_INTERFACE
class HabitAssignmentViewSet(viewsets.ModelViewSet):
    queryset = HabitAssignment.objects.all().order_by("-id")
    serializer_class = HabitAssignmentSerializer
    permission_classes = [permissions.IsAuthenticated]


# PUBLIC_INTERFACE
class HabitLogViewSet(viewsets.ModelViewSet):
    queryset = HabitLog.objects.all().order_by("-id")
    serializer_class = HabitLogSerializer
    permission_classes = [permissions.IsAuthenticated]

    @action(detail=False, methods=["get"], url_path="assignment/(?P<assignment_id>[^/.]+)/logs")
    def list_by_assignment(self, request, assignment_id=None):
        logs = HabitLog.objects.filter(assignment_id=assignment_id).order_by("-date")
        return Response(HabitLogSerializer(logs, many=True).data)


# PUBLIC_INTERFACE
class PlanViewSet(viewsets.ModelViewSet):
    queryset = Plan.objects.all().order_by("-id")
    serializer_class = PlanSerializer
    permission_classes = [permissions.IsAuthenticated, IsCoach | IsAdmin]


# PUBLIC_INTERFACE
class MealLogViewSet(viewsets.ModelViewSet):
    queryset = MealLog.objects.all().order_by("-id")
    serializer_class = MealLogSerializer
    permission_classes = [permissions.IsAuthenticated]


# PUBLIC_INTERFACE
class WorkoutLogViewSet(viewsets.ModelViewSet):
    queryset = WorkoutLog.objects.all().order_by("-id")
    serializer_class = WorkoutLogSerializer
    permission_classes = [permissions.IsAuthenticated]


# PUBLIC_INTERFACE
class MeasurementViewSet(viewsets.ModelViewSet):
    queryset = Measurement.objects.all().order_by("-id")
    serializer_class = MeasurementSerializer
    permission_classes = [permissions.IsAuthenticated]


# PUBLIC_INTERFACE
class ConversationViewSet(viewsets.ModelViewSet):
    queryset = Conversation.objects.all().order_by("-id")
    serializer_class = ConversationSerializer
    permission_classes = [permissions.IsAuthenticated]

    @action(detail=True, methods=["get"])
    def messages(self, request, pk=None):
        msgs = Message.objects.filter(conversation_id=pk).order_by("created_at")
        return Response(MessageSerializer(msgs, many=True).data)


# PUBLIC_INTERFACE
class MessageViewSet(viewsets.ModelViewSet):
    queryset = Message.objects.all().order_by("created_at")
    serializer_class = MessageSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(sender=self.request.user)


# PUBLIC_INTERFACE
class SubscriptionViewSet(viewsets.ModelViewSet):
    queryset = Subscription.objects.all()
    serializer_class = SubscriptionSerializer
    permission_classes = [permissions.IsAuthenticated]


# PUBLIC_INTERFACE
class InvoiceViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Invoice.objects.all().order_by("-created_at")
    serializer_class = InvoiceSerializer
    permission_classes = [permissions.IsAuthenticated]


# PUBLIC_INTERFACE
class AnalyticsEventViewSet(viewsets.ModelViewSet):
    queryset = AnalyticsEvent.objects.all().order_by("-created_at")
    serializer_class = AnalyticsEventSerializer
    permission_classes = [permissions.IsAuthenticated]

    @action(detail=False, methods=["get"], url_path="reports/summary")
    def summary(self, request):
        now = timezone.now()
        since = now - timedelta(days=30)
        qs = AnalyticsEvent.objects.filter(created_at__gte=since)
        summary = qs.values("event_type").annotate(count=Count("id")).order_by("-count")
        return Response({"since": since.isoformat(), "summary": list(summary)})


# PUBLIC_INTERFACE
@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def me(request):
    """Current user info with role."""
    profile = UserProfile.objects.filter(user=request.user).first()
    return Response({
        "user": UserSerializer(request.user).data,
        "role": profile.role if profile else "client",
    })
