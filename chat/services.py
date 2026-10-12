from .models import Membership


def is_room_member(user_id, room_id) -> bool:
    return Membership.objects.filter(chatroom_id=room_id, user_id=user_id, left_at__isnull=True).exists()
