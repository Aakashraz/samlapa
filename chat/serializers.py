from typing import Any

from rest_framework import serializers
from users.models import User
from .models import Message



class UserSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username']


class MessageSerializer(serializers.ModelSerializer):
    chatroom_id = serializers.UUIDField(read_only=True)
    parent_id = serializers.UUIDField(read_only=True)
    sender = UserSummarySerializer(read_only=True, allow_null=True)
    # allow_null=True: as the sender field is SET_NULL in the model, serializer may not know it's null or not,
    # so, to prevent serializer from crashing by allowing null=True

    class Meta:
        model = Message
        fields = [
            'id',
            'chatroom_id',     # DRF outputs this as chatroom_id automatically.
            'sender',
            'message_type',
            'content',
            'parent_id',       # DRF outputs as parent_id
            'is_deleted',
            'created_at',
            'edited_at',
        ]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if instance.is_deleted:
            data['sender']= None
            data['message_type'] = None
            data['content'] = None
            data['parent_id'] = None
            data['edited_at'] = None
        return data



class MessageCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = ['content', 'message_type', 'parent_id']

    def validate(self, attrs: Any) -> Any:
        print(attrs)
        if attrs.get('message_type', 'text') == 'text'  and  not attrs['content'].strip():
            raise serializers.ValidationError({'content':'Content cannot be empty'})

        return attrs


# --- NOTE ---
# --- This is a different way of dealing with the model attributes: corresponding to the serializer's fields ---
# When you serialize a message and want to include {id, username}:
# -- You need sender (the User object) — because username lives on User.
# -- If you only needed the id, sender_id would do.
#
# When your field is named chatroom_id and you want a string UUID:
# -- You need chatroom_id — the raw value. chatroom (the FK object) would require a DB fetch for no reason.
# -- That's why the alias is named chatroom_id, not chatroom.
# Heuristic: if the JSON field ends in _id, use the _id attribute. If it's a nested object, use the FK attribute.


# DRF's default to_representation. It:
# -- Receives the model instance.
# -- Iterates over every declared field.
# -- Calls each field's own to_representation(value) to convert Python → JSON-able.
# -- Returns a plain dict: {'id': ..., 'chatroom_id': ..., 'sender': {...}, ...}.
# -- That dict is what .data returns. So to_representation is the function that builds the output dict.