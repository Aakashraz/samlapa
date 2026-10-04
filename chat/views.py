from django.shortcuts import render
from rest_framework.generics import ListAPIView
from rest_framework.exceptions import PermissionDenied, NotFound

from .models import ChatRoom, Membership, Message
from .serializers import MessageSerializer



class RoomMessageListView(ListAPIView):
    serializer_class = MessageSerializer

    def get_queryset(self):
            room_id = self.kwargs['room_id']
            if Membership.objects.filter(user=self.request.user, chatroom.id=room_id, left_at__isnull=False).exists():




# The __ is just Django's separator. field__lookup=value. The lookup is one of: isnull, gt, gte, lt,
# lte, contains, startswith, in, year, month, date, and more.