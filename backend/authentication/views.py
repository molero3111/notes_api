from rest_framework.authtoken.models import Token
from rest_framework.response import Response
from rest_framework.status import HTTP_400_BAD_REQUEST, HTTP_201_CREATED, HTTP_200_OK
from rest_framework.views import APIView

from .serializers import UserSerializer


class UserRegistration(APIView):
    def post(self, request):
        serializer = UserSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=HTTP_400_BAD_REQUEST)
        user = serializer.save()
        token, _ = Token.objects.get_or_create(user=user)
        return Response({'token': token.key}, status=HTTP_201_CREATED)


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
