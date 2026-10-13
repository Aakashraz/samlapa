from .models import Membership



# To check if a user is a member of a chatroom
def is_room_member(user_id, room_id) -> bool:
    return Membership.objects.filter(chatroom_id=room_id, user_id=user_id, left_at__isnull=True).exists()


# Get the group name of a chatroom
def room_group_name(room_id) -> str:
    return f"chatroom_{room_id}"