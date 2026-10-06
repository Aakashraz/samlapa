from django.shortcuts import render
from rest_framework.generics import ListAPIView
from rest_framework.exceptions import PermissionDenied, NotFound
from rest_framework.permissions import IsAuthenticated

from .models import ChatRoom, Membership, Message
from .serializers import MessageSerializer



# the view must be IsAuthenticated, and soon. Otherwise, the very first unauthenticated Android call causes a server error.
class RoomMessageListView(ListAPIView):
    serializer_class = MessageSerializer
    permission_classes = [IsAuthenticated]

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


# --------------------------------
# JWTAuthentication.authenticate_header returns 'Bearer realm="api"'. So if you put JWT first in the list,
# unauthenticated requests will get 401 with a WWW-Authenticate: Bearer header — which is the correct,
# standards-compliant answer for a token API. That’s a concrete benefit of switching, not just an
# auth mechanism swap.