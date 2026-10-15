import json

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from .services import is_room_member, room_group_name



class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # read user (from JWT middleware), room_id (from URL), subprotocol
        self.user = self.scope['user']
        self.room_id = self.scope['url_route']['kwargs']['room_id']
        protocol = self.scope['subprotocol']
        self.group_name = room_group_name(self.room_id)

        # Reject anonymous users
        if self.user is None or self.user.is_anonymous:
            await self.close(code=4003)     # Forbidden
            return

        # reject non-members (DB call -> database_suyc_to_async)
        check_member = await database_sync_to_async(is_room_member)(self.user.id, self.room_id)
        if not check_member:
            await self.close()
            return

        # accept connection using subprotocol
        await self.accept(subprotocol=protocol)
        await self.channel_layer.group_add(self.group_name, self.channel_name)

    # chat_message(): handler for {"type": "chat.message"}
    async def chat_message(self, event):
        await self.send(text_data=json.dumps(event["message"]))    # sends the WHOLE dict from self.group_name.

    # receive(): client -> server messages. Unused: REST is the write path.
    async def receive(self, text_data=None, bytes_data=None):
        pass

    # disconnect(): cleanup. group_discard so no dead channels remain in the group.
    async def disconnect(self, code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)



# Honest gap: the membership check only runs at connect time. If Bob is removed from the room while his
# connection is open, he stays in the Redis group and keeps receiving messages until he disconnects.
# Note it down, because a “remove member” feature will need to call group_discard or force a disconnect.

# FOR your A plan:
# Add this to the Android design: on every WebSocket (re)connect, run the catch-up fetch. Without it,
# every dropped connection silently loses messages, and your server-side logging decision from earlier
# only stays safe because of this fetch.