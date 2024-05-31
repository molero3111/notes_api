from authentication.views import LogoutView
from authentication.views import UserRegistration
from django.urls import path
from rest_framework.authtoken.views import ObtainAuthToken

urlpatterns = [
    path('register/', UserRegistration.as_view(), name='register'),
    path('login/', ObtainAuthToken.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
]
