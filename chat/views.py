from django.shortcuts import render
from rest_framework import status, pagination
from rest_framework.generics import ListCreateAPIView
from rest_framework.exceptions import PermissionDenied, NotFound
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from .models import ChatRoom, Membership, Message
from .serializers import MessageSerializer, MessageCreateSerializer
from .services import room_group_name
import logging



logger = logging.getLogger(__name__)

# CursorPagination Subclassing
class MessageCursorPagination(pagination.CursorPagination):
    page_size = 50
    ordering = ['-created_at','id']

# the view must be IsAuthenticated, and soon. Otherwise, the very first unauthenticated Android call causes a server error.
class RoomMessageListView(ListCreateAPIView):
    # serializer_class = MessageSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = MessageCursorPagination

    def get_queryset(self):
        chatroom = self.get_room_and_check_membership()
        qs = Message.all_objects.filter(chatroom_id=chatroom.id).select_related('sender')
        return qs


    def get_serializer_class(self):
        if self.request.method=='POST':
            return MessageCreateSerializer
        return MessageSerializer


    def create(self, request, *args, **kwargs):
        chatroom = self.get_room_and_check_membership()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        new_message = serializer.save(chatroom=chatroom, sender=request.user)
        read_data = MessageSerializer(new_message).data

        channel_layer = get_channel_layer()
        try:
            async_to_sync(channel_layer.group_send)(
                room_group_name(chatroom.id),
                {
                    "type": "chat.message",
                    "message": read_data,
                },
            )
        except Exception:
            # Log the exact error traceback silently without crashing your app
            logger.exception("Error sending message to chatroom %s --------", chatroom.id)
        return Response(read_data, status=status.HTTP_201_CREATED)


    def get_room_and_check_membership(self):
        room_id = self.kwargs['room_id']
        if not Membership.objects.filter(
                user=self.request.user, chatroom_id=room_id, left_at__isnull=True).exists():
            raise NotFound()

        room = ChatRoom.objects.get(id=room_id)
        return room
        # 404 over 403: attacker can't distinguish "room doesn't exist" from
        # "room exists, but you're not a member." Hides existence.



# The __ is just Django's separator. field__lookup=value. The lookup is one of: isnull, gt, gte, lt,
# lte, contains, startswith, in, year, month, date, and more.


# --------------------------------
# JWTAuthentication.authenticate_header returns 'Bearer realm="api"'. So if you put JWT first in the list,
# unauthenticated requests will get 401 with a WWW-Authenticate: Bearer header — which is the correct,
# standards-compliant answer for a token API. That’s a concrete benefit of switching, not just an
# auth mechanism swap.

# WWW-Authenticate: Bearer realm="api" on a 401. That’s your contract with the Android client.
# --- without Username:Password and no JWT token