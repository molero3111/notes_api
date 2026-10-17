from django.conf import settings
from rest_framework import serializers

from .models import Note, Tag, Category


class TagListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ['id', 'name']


class CategoryListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name']


class NoteListSerializer(serializers.ModelSerializer):
    tags = TagListSerializer(many=True)
    categories = CategoryListSerializer(many=True)

    class Meta:
        model = Note
        fields = ['id', 'title', 'content', 'tags', 'categories', 'archived', 'created_at', 'updated_at']


class NoteSerializer(serializers.ModelSerializer):
    tags = serializers.PrimaryKeyRelatedField(many=True, queryset=Tag.objects.all())
    categories = serializers.PrimaryKeyRelatedField(many=True, queryset=Category.objects.all())

    class Meta:
        model = Note
        fields = ['id', 'title', 'content', 'tags', 'categories', 'archived', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']

    def validate_content(self, value):
        max_length = settings.NOTE_MAX_CONTENT_LENGTH
        if len(value) > max_length:
            raise serializers.ValidationError(f'Ensure this field has no more than {max_length} characters.')
        return value
