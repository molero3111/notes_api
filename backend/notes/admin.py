from django.contrib import admin

from notes.models import Category, Tag, Note

# Register your models here.
admin.site.register(Tag)
admin.site.register(Category)
admin.site.register(Note)
