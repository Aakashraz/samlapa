import uuid
from django.conf import settings
from django.db import models


# Attachment Model, your recommendation for Future.
# Model: ChatRoom/Room
# Purpose - The chat room for conversation between any two users or more or them(group).
# message- reverse FK
# created_by-User FK
# participants = M2M field, User, through='Membership', related_name='chatrooms'
# title-char field
# dm_key-str field (combination of two ids)
# Type: choices direct/group - but where do I define these choices direct and group
# created_at, updated_at, last_message_at -datetime field (for sorting conversation efficiently)
# is_active/is_archived -- for FUTURE
# -- active = normal, people can chat
# -- archived = closed, nobody can send new messages, but old messages are still readable

class ChatRoom(models.Model):
    """
        A conversation. Two types:
        - DIRECT: exactly two members, one per unique user pair.
        - GROUP: N members, has a title, has roles.
        Both use Membership as the join table, so the rest of the code treats them identically.
    """
    class RoomType(models.TextChoices):
        DIRECT = 'direct', 'Direct'
        GROUP = 'group', 'Group'
        # Python name = 'DB value', 'Human label'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    type = models.CharField(max_length=10, choices=RoomType.choices, default=RoomType.GROUP)
    # Only used for GROUP rooms. Blank for DIRECT.
    title = models.CharField(max_length=255, blank=True)
    # Who created it. Keep the room if the user is deleted.
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='created_rooms',
        null=True, blank=True,
    )
    # Uniqueness key for DIRECT rooms: "smaller_id-larger_id".
    # NULL for GROUP room. unique=True allows many NULLs in Postgres.
    dm_key = models.CharField(max_length=64, null=True, unique=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_message_at = models.DateTimeField(null=True, blank=True, db_index=True)

    # FUTURE: is_active, is_archived for soft-closing a room.

    # The M2M lives here, but the join table is OUR Membership model.
    participants = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        through='Membership',
        through_fields=('chatroom', 'user'),
        related_name='chatrooms',
    )

    class Meta:
        ordering = ['-last_message_at', '-created_at']

    def __str__(self):
        return self.title or f"{self.type}:{self.id}"


# Membership
# Purpose - To define the role and permissions of a user in a group.
# user-User FK
# chatroom-ChatRoom FK
# role-choice field from Member, Admin and Owner
# joined_at-datetime field(now=True)
# left_at-datetime field
# muted_until-permission cleared by the owner/admin, datetime field

class Membership(models.Model):
    """
        Join the row between User and ChatRoom, carrying role + read state.
        Exists for BOTH direct and group rooms (DM = 2-person group).
    """
    class Role(models.TextChoices):
        OWNER = 'owner', 'Owner',
        ADMIN = 'admin', 'Admin',
        MEMBER = 'member', 'Member'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='memberships',
        db_index=False,     # <- stop auto-indexing.Both (user, left_at) and the unique constraint cover it.
    )

    chatroom  = models.ForeignKey(
        ChatRoom, on_delete=models.CASCADE, related_name='memberships',
    )

    role = models.CharField(max_length=10, choices=Role.choices, default=Role.MEMBER)
    joined_at = models.DateTimeField(auto_now_add=True)

    # Unread badge: count messages where created_at > last_read_at.
    last_read_at = models.DateTimeField(null=True, blank=True)

    # Per-user mute. NULL = not muted.
    muted_until = models.DateTimeField(null=True, blank=True)

    # Soft-leave/kick. NULL = active member.
    left_at = models.DateTimeField(null=True, blank=True)

    # For kicks: who removed them (audit trail).
    removed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='removals',
        null=True, blank=True,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'chatroom'],
                name='unique_membership_per_user_per_room',
            ),
        ]
        indexes = [
            models.Index(fields=['user', 'left_at']),
        ]

    def __str__(self):
        return f"{self.user} in {self.chatroom} ({self.role})"

    @property
    def is_active_member(self):
        return self.left_at is None


# Model: Message
# Purpose - The real message content.
# chatroom-ChatRoom FK, related_name= messages
# sender-User FK, related_name=
# created_at-datetime field(now=True)
# edited_at-datetime field
# content - textfield
# message_type (text/image/file)- may be FK to Attachment model
# updated_at-datetime field
# parent (for replies)-a self-referential FK-It points to another Message model
# is_deleted-soft delete

class Message(models.Model):
    """
        A single message in a room. Same model for DM and GROUP.
    """
    class Kind(models.TextChoices):
        TEXT    = 'text', 'Text',
        IMAGE   = 'image', 'Image',
        FILE    = 'file', 'File',
        SYSTEM  = 'system', 'System'    # A system message, not sent by a user.

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    chatroom = models.ForeignKey(
        ChatRoom,
        on_delete=models.CASCADE,
        related_name='messages',
        db_index=False,         # The composite index below on Meta class covers it.
    )

    # Keep the message if the sender is deleted.
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='messages',
        null=True, blank=True,
    )

    content = models.TextField(blank=True)
    message_type = models.CharField(max_length=10, choices=Kind.choices, default=Kind.TEXT)

    # Reply threading. Self-FK: a Message can point to another Message.
    # In DB: a Row pointing to another Row in the same Table.
    parent = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='replies',
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    edited_at = models.DateTimeField(null=True, blank=True)

    # Soft delete. keep row, hide content on client.
    is_deleted = models.BooleanField(default=False)

    class Meta:
        ordering = ['created_at']
        indexes = [
            # The no. 1 query: fetch messages of a room in order.
            models.Index(fields=['chatroom', 'created_at']),
        ]

    def __str__(self):
        return f"msg:{self.id} in {self.chatroom_id}"