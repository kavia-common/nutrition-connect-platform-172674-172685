import json
from urllib.parse import parse_qs

from asgiref.sync import sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.contrib.auth.models import User
from rest_framework_simplejwt.tokens import AccessToken

from .models import Message


class JWTAuthMixin:
    async def get_user_from_jwt(self):
        # Support querystring token ?token=... or subprotocol Authorization header not available here
        try:
            query_string = self.scope.get("query_string", b"").decode()
            params = parse_qs(query_string)
            token = None
            # PUBLIC_INTERFACE
            if "token" in params:
                token = params["token"][0]
            if not token:
                return None
            access = AccessToken(token)
            user_id = access.get("user_id")
            user = await sync_to_async(User.objects.get)(id=user_id)
            return user
        except Exception:
            return None


class ChatConsumer(JWTAuthMixin, AsyncWebsocketConsumer):
    """PUBLIC_INTERFACE
    WebSocket consumer for chat at /ws/chat/<conversation_id>/.
    Authenticate with JWT access token via query param ?token=... .
    """

    async def connect(self):
        self.conversation_id = self.scope["url_route"]["kwargs"]["conversation_id"]
        self.group_name = f"chat_{self.conversation_id}"
        self.user = await self.get_user_from_jwt()
        if self.user is None:
            await self.close(code=4401)  # Unauthorized
            return

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data=None, bytes_data=None):
        try:
            payload = json.loads(text_data or "{}")
            content = payload.get("content", "")
            if not content.strip():
                return
            # Persist message
            await sync_to_async(Message.objects.create)(
                conversation_id=self.conversation_id,
                sender=self.user,
                content=content,
            )
            # Broadcast to group
            await self.channel_layer.group_send(
                self.group_name,
                {"type": "chat.message", "sender": self.user.username, "content": content},
            )
        except Exception:
            # swallow invalid payloads
            pass

    async def chat_message(self, event):
        await self.send(text_data=json.dumps({"sender": event["sender"], "content": event["content"]}))
