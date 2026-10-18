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

from notes_manager.throttling import AnonThrottle, LoginThrottle, RegisterThrottle
from .serializers import UserSerializer


class UserRegistration(APIView):
    throttle_classes = [AnonThrottle, RegisterThrottle]

    def post(self, request):
        # Caps on accounts that exist, not on attempts, so failed or throttled requests can't use them up.
        # Both are 0 (off) by default.
        if settings.MAX_USERS and User.objects.count() >= settings.MAX_USERS:
            return Response({'detail': 'Registration is closed.'}, status=HTTP_403_FORBIDDEN)
        if settings.REGISTRATIONS_PER_DAY:
            since = timezone.now() - timedelta(days=1)
            if User.objects.filter(date_joined__gte=since).count() >= settings.REGISTRATIONS_PER_DAY:
                return Response({'detail': 'Too many new accounts today, please try again later.'},
                                status=HTTP_429_TOO_MANY_REQUESTS)

        serializer = UserSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=HTTP_400_BAD_REQUEST)
        user = serializer.save()
        token, _ = Token.objects.get_or_create(user=user)
        return Response({'token': token.key}, status=HTTP_201_CREATED)


class LoginView(ObtainAuthToken):
    throttle_classes = [AnonThrottle, LoginThrottle]


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
