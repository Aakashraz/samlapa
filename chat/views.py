from django.shortcuts import render
from rest_framework.generics import ListAPIView
from rest_framework.exceptions import PermissionDenied, NotFound

from .models import ChatRoom, Membership, Message
from .serializers import MessageSerializer



class RoomMessageListView(ListAPIView):
    serializer_class = MessageSerializer

    def get_queryset(self):
        room_id = self.kwargs['room_id']
        if not Membership.objects.filter(
                user=self.request.user, chatroom_id=room_id, left_at__isnull=True).exists():
            raise NotFound()
        # 404 over 403: attacker can't distinguish "room doesn't exist" from
        # "room exists, but you're not a member." Hides existence.

        # To fetch the last 50 messages from a chatroom -- needed reversed order.
        qs = Message.all_objects.filter(chatroom_id=room_id).select_related('sender').order_by('-created_at')[:50]
        return list(reversed(qs))



# The __ is just Django's separator. field__lookup=value. The lookup is one of: isnull, gt, gte, lt,
# lte, contains, startswith, in, year, month, date, and more.