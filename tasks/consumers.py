import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from urllib.parse import parse_qs


class BoardConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        self.project_id = self.scope['url_route']['kwargs']['project_id']
        self.group_name = f'board_{self.project_id}'

        print(f'[WS] Connect attempt for project: {self.project_id}')

        user = await self.get_user_from_token()
        if not user:
            print('[WS] REJECTED — token auth failed')
            await self.close(code=4001)
            return

        self.user = user
        print(f'[WS] Auth OK — user: {user.username}')

        is_member = await self.check_membership()
        if not is_member:
            print(f'[WS] REJECTED — {user.username} is not a member')
            await self.close(code=4003)
            return

        print(f'[WS] ACCEPTED — {user.username} joined board {self.project_id}')
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

        await self.channel_layer.group_send(self.group_name, {
            'type': 'user_joined',
            'user': {'id': str(user.id), 'username': user.username},
            'sender_channel': self.channel_name,
        })

    async def disconnect(self, code):
        if hasattr(self, 'group_name'):
            if hasattr(self, 'user'):
                await self.channel_layer.group_send(self.group_name, {
                    'type': 'user_left',
                    'user_id': str(self.user.id),
                    'sender_channel': self.channel_name,
                })
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            data['sender_channel'] = self.channel_name
            await self.channel_layer.group_send(self.group_name, data)
        except Exception as e:
            print(f'[WS] receive error: {e}')

    async def task_created(self, event):
        await self._send_if_not_sender(event)

    async def task_updated(self, event):
        await self._send_if_not_sender(event)

    async def task_deleted(self, event):
        await self._send_if_not_sender(event)

    async def task_moved(self, event):
        await self._send_if_not_sender(event)

    async def column_created(self, event):
        await self._send_if_not_sender(event)

    async def column_updated(self, event):
        await self._send_if_not_sender(event)

    async def column_deleted(self, event):
        await self._send_if_not_sender(event)

    async def user_joined(self, event):
        await self._send_if_not_sender(event)

    async def user_left(self, event):
        await self._send_if_not_sender(event)
    async def notification_event(self, event):
        await self._send_if_not_sender(event)

    async def _send_if_not_sender(self, event):
        if event.get('sender_channel') != self.channel_name:
            payload = {k: v for k, v in event.items() if k not in ('type', 'sender_channel')}
            payload['type'] = event['type']
            await self.send(text_data=json.dumps(payload))

    @database_sync_to_async
    def get_user_from_token(self):
        try:
            query_string = self.scope.get('query_string', b'').decode()
            params = parse_qs(query_string)
            token_list = params.get('token', [])
            if not token_list:
                print('[WS] No token in query string')
                return None

            from rest_framework_simplejwt.tokens import AccessToken
            from django.contrib.auth import get_user_model
            User = get_user_model()

            validated = AccessToken(token_list[0])
            user_id = validated['user_id']
            print(f'[WS] Token user_id: {user_id} (type: {type(user_id)})')

            user = User.objects.filter(pk=user_id).first()
            if not user:
                user = User.objects.filter(id=str(user_id)).first()
            return user
        except Exception as e:
            print(f'[WS Auth Error] {type(e).__name__}: {e}')
            return None

    @database_sync_to_async
    def check_membership(self):
        try:
            from projects.models import Project
            from workspaces.models import WorkspaceMember
            project = Project.objects.select_related('workspace').get(id=self.project_id)
            return WorkspaceMember.objects.filter(
                workspace=project.workspace,
                user=self.user
            ).exists()
        except Exception as e:
            print(f'[WS Membership Error] {type(e).__name__}: {e}')
            return False