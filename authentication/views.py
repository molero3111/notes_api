import logging
import math
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.models import User
from django.utils import timezone
from rest_framework.authtoken.models import Token
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.response import Response
from rest_framework.status import (HTTP_400_BAD_REQUEST, HTTP_201_CREATED, HTTP_200_OK, HTTP_403_FORBIDDEN,
                                   HTTP_429_TOO_MANY_REQUESTS)
from rest_framework.views import APIView

from notes_manager.storage import refuse_if_storage_full
from notes_manager.throttling import AnonThrottle, LoginIPThrottle, LoginThrottle, RegisterThrottle
from .serializers import UserSerializer

logger = logging.getLogger(__name__)


class UserRegistration(APIView):
    throttle_classes = [AnonThrottle, RegisterThrottle]

    def post(self, request):
        # Caps on accounts that exist, not on attempts, so failed or throttled requests can't use them up.
        # Both are 0 (off) by default. Bots that reach a cap also block real sign-ups until an admin
        # deletes them (Django admin), so hitting either one is logged as a warning.
        refuse_if_storage_full('register')
        if settings.MAX_USERS and User.objects.count() >= settings.MAX_USERS:
            logger.warning('Registration refused: MAX_USERS=%s reached', settings.MAX_USERS)
            return Response({'detail': 'Registration is closed.'}, status=HTTP_403_FORBIDDEN)
        if settings.REGISTRATIONS_PER_DAY:
            cap = settings.REGISTRATIONS_PER_DAY
            now = timezone.now()
            joined = list(User.objects.filter(date_joined__gte=now - timedelta(days=1))
                          .order_by('date_joined').values_list('date_joined', flat=True))
            if len(joined) >= cap:
                logger.warning('Registration refused: REGISTRATIONS_PER_DAY=%s reached', cap)
                # A slot frees once the window holds cap - 1 sign-ups, i.e. when this one turns 24 hours old
                frees_at = joined[len(joined) - cap] + timedelta(days=1)
                retry_after = max(1, math.ceil((frees_at - now).total_seconds()))
                return Response({'detail': 'Too many new accounts today, please try again later.'},
                                status=HTTP_429_TOO_MANY_REQUESTS, headers={'Retry-After': str(retry_after)})

        serializer = UserSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=HTTP_400_BAD_REQUEST)
        user = serializer.save()
        token, _ = Token.objects.get_or_create(user=user)
        return Response({'token': token.key}, status=HTTP_201_CREATED)


class LoginView(ObtainAuthToken):
    throttle_classes = [AnonThrottle, LoginIPThrottle, LoginThrottle]


class LogoutView(APIView):
    def post(self, request):
        # Get the token from the request headers or wherever it's stored
        # You might need to adjust this depending on how you handle authentication tokens
        token = request.META.get('HTTP_AUTHORIZATION').split()[1]

        # Delete the token
        try:
            Token.objects.get(key=token).delete()
            return Response({"message": "Logout successful"}, status=HTTP_200_OK)
        except Token.DoesNotExist:
            return Response({"error": "Invalid token."}, status=HTTP_400_BAD_REQUEST)
