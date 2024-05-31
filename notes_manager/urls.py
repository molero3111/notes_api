from django.contrib import admin
from django.urls import path, include

from notes_manager.settings import URL_PREFIX

api_base_path = f'{URL_PREFIX}api/'

urlpatterns = [
    path(f'{URL_PREFIX}admin/', admin.site.urls),
    path(api_base_path, include('authentication.urls')),
    path(api_base_path, include('notes.urls')),
]
