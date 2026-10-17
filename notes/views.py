from django.conf import settings
from django.contrib.auth.models import User
from django.db import transaction
from rest_framework import viewsets
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import SAFE_METHODS, BasePermission, IsAuthenticated
from rest_framework.response import Response

from .models import Note, Category, Tag
from .serializers import NoteListSerializer, NoteSerializer, CategoryListSerializer, TagListSerializer


class IsStaffOrReadOnly(BasePermission):
    """Tags and categories are shared by all users, so only staff may change them."""

    def has_permission(self, request, view):
        return request.method in SAFE_METHODS or request.user.is_staff


class NoteViewSet(viewsets.ModelViewSet):
    queryset = Note.objects.filter(archived=False)
    serializer_class = NoteSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        # Archived notes count too: the quota bounds what a user stores, not what they see.
        # Locking the user row serialises concurrent creates, so parallel requests can't exceed it.
        max_notes = settings.NOTES_MAX_PER_USER
        with transaction.atomic():
            User.objects.select_for_update().get(pk=self.request.user.pk)
            if Note.objects.filter(user=self.request.user).count() >= max_notes:
                raise ValidationError({'detail': f'Note limit reached: each user can keep at most {max_notes} notes.'})
            serializer.save(user=self.request.user)

    def get_serializer_class(self):
        if self.action == 'list' or self.action == 'retrieve':
            return NoteListSerializer
        return NoteSerializer

    def get_queryset(self):
        queryset = Note.objects.filter(user=self.request.user)

        # Get query parameters for filtering
        tag_id = self.request.query_params.get('tag_id', None)
        category_id = self.request.query_params.get('category_id', None)
        archived = self.request.query_params.get('archived', None)

        if tag_id:  # Filter queryset based on tag_id
            queryset = queryset.filter(tags__id=tag_id)
        if category_id:  # Filter queryset based on category_id
            queryset = queryset.filter(categories__id=category_id)
        if archived is not None:  # Filter queryset based on archived status
            queryset = queryset.filter(archived=(archived == '1'))

        return queryset

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', True)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data)


class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategoryListSerializer
    permission_classes = [IsAuthenticated, IsStaffOrReadOnly]


class TagViewSet(viewsets.ModelViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagListSerializer
    permission_classes = [IsAuthenticated, IsStaffOrReadOnly]
