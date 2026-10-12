from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.tokens import AccessToken
from rest_framework_simplejwt.exceptions import TokenError


User = get_user_model()


class JWTMiddleware:
    """
    Middleware to read JWT out of the subprotocols header, verify it, look up the user, and
    put that user into scope['user'] before the consumer runs.
    """
    def __init__(self, inner):
        self.inner = inner

    async def __call__(self, scope, receive, send):
        # Defaults - the resting state for every connection.
        scope['user'] = AnonymousUser()
        scope['subprotocol'] = None

        # Extracting the access token from the subprotocols
        raw_token = None
        for protocol in scope.get('subprotocols', []):
            if protocol.startswith('access_token.'):
                split_token= protocol.split('.',1)
                raw_token = split_token[1]
                # scope['subprotocol'] stores the whole matched string, so the consumer can echo it back verbatim.
                scope['subprotocol'] = protocol
                break

        # Only attempt token work if there is a token.
        if raw_token is not None:
            try:
                # Decode and verify the raw_token
                token = AccessToken(raw_token)
                # Two steps here. database_sync_to_async(User.objects.get) wraps the ORM method -- the callable, not called
                # -- and returns an async callable. Then you call it with (id=token['user_id']) and await it.
                user = await database_sync_to_async(User.objects.get)(id=token['user_id'])
                scope['user'] = user
            except (TokenError, User.DoesNotExist):
                pass    # default AnonymousUser stands

        return await self.inner(scope, receive, send)