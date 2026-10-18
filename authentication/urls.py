from authentication.views import LoginView
from authentication.views import LogoutView
from authentication.views import UserRegistration
from django.urls import path

urlpatterns = [
    path('register/', UserRegistration.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
]
