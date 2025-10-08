from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from channels.testing import WebsocketCommunicator
from django.test import override_settings
from config.asgi import application

from .models import UserProfile, Plan, Conversation


class HealthTests(APITestCase):
    def test_health(self):
        url = reverse('Health')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, {"message": "Server is up!"})


class AuthAndRoleTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(username="admin", password="pass", is_staff=True)
        UserProfile.objects.create(user=self.admin, role="admin")
        self.coach = User.objects.create_user(username="coach", password="pass")
        UserProfile.objects.create(user=self.coach, role="coach")
        self.client_user = User.objects.create_user(username="client", password="pass")
        UserProfile.objects.create(user=self.client_user, role="client")

    def auth_token(self, username, password="pass"):
        resp = self.client.post("/api/auth/login", {"username": username, "password": password}, format="json")
        self.assertEqual(resp.status_code, 200)
        return resp.data["access"]

    def test_me_endpoint(self):
        token = self.auth_token("coach")
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        resp = client.get("/api/users/me")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["role"], "coach")

    def test_plan_create_requires_coach_or_admin(self):
        # client cannot create plan
        token = self.auth_token("client")
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        resp = client.post("/api/plans/", {"name": "Plan1", "description": "", "coach": 1, "client": 3}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

        # coach can create plan
        token = self.auth_token("coach")
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        resp = client.post("/api/plans/", {"name": "Plan1", "description": "", "coach": self.coach.id, "client": self.client_user.id}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Plan.objects.filter(name="Plan1").exists())


class WebsocketTests(APITestCase):
    @override_settings(CHANNEL_LAYERS={"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}})
    def test_basic_chat_broadcast(self):
        # create user and conversation
        user = User.objects.create_user(username="wsuser", password="pass")
        UserProfile.objects.create(user=user, role="client")
        conv = Conversation.objects.create(title="c1")
        conv.participants.add(user)

        # login to get JWT
        resp = self.client.post("/api/auth/login", {"username": "wsuser", "password": "pass"}, format="json")
        self.assertEqual(resp.status_code, 200)
        token = resp.data["access"]

        # connect
        path = f"/ws/chat/{conv.id}/?token={token}"
        communicator = WebsocketCommunicator(application, path)
        connected, _ = self.async_run(communicator.connect())
        self.assertTrue(connected)

        # send and get echo via group broadcast
        self.async_run(communicator.send_json_to({"content": "hello"}))
        msg = self.async_run(communicator.receive_json_from())
        self.assertEqual(msg["content"], "hello")

        self.async_run(communicator.disconnect())

    # helper to run async from TestCase
    def async_run(self, awaitable):
        import asyncio
        return asyncio.get_event_loop().run_until_complete(awaitable)
