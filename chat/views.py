from django.shortcuts import render
from rest_framework.generics import ListCreateAPIView
from rest_framework.exceptions import PermissionDenied, NotFound
from rest_framework.permissions import IsAuthenticated

from .models import ChatRoom, Membership, Message
from .serializers import MessageSerializer, MessageCreateSerializer


# the view must be IsAuthenticated, and soon. Otherwise, the very first unauthenticated Android call causes a server error.
class RoomMessageListView(ListCreateAPIView):
    # serializer_class = MessageSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        chatroom = self.get_room_and_check_membership()
        # To fetch the last 50 messages from a chatroom -- needed reversed order.
        qs = Message.all_objects.filter(chatroom_id=chatroom.id).select_related('sender').order_by('-created_at')[:50]
        return list(reversed(qs))

    def get_serializer_class(self):
        if self.request.method=='POST':
            return MessageCreateSerializer
        return MessageSerializer

    def create(self, request, *args, **kwargs):
        chatroom = self.get_room_and_check_membership()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        # serializer.save()
        # chatroom.messages.create(sender=request.user)



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