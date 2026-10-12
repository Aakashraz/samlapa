"""
ASGI config for samlapa project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/6.1/howto/deployment/asgi/
"""

import os
from channels.routing import ProtocolTypeRouter, URLRouter
# from channels.security.websocket import AllowedHostsOriginValidator   # re-enable after confirming Andriod sends Origin header
from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'samlapa.settings')

django_asgi_app = get_asgi_application()

from chat.routing import websocket_urlpatterns
from chat.middleware import JWTMiddleware

application = ProtocolTypeRouter({
    'http': django_asgi_app,
    'websocket': JWTMiddleware(
            URLRouter(websocket_urlpatterns)
        ),
})

