from django.urls import path
from .views import RoomMessageListView


app_name = 'chat'
urlpatterns = [
    path('rooms/<uuid:room_id>/messages/', RoomMessageListView.as_view(), name='room_messages')
]