from datetime import timedelta
from io import StringIO

from django.contrib.auth.models import User
from django.core.management import CommandError, call_command
from django.test import override_settings
from django.utils import timezone
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from .models import Category, Note, Tag

NOTES_URL = '/api/notes/'


class NoteLimitsTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='alice', password='pw-alice-123')
        token = Token.objects.create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

    def create_note(self, content='hello'):
        return self.client.post(NOTES_URL, {'title': 't', 'content': content, 'tags': [], 'categories': []},
                                format='json')

    @override_settings(NOTE_MAX_CONTENT_LENGTH=20)
    def test_content_at_max_length_is_accepted(self):
        response = self.create_note('x' * 20)
        self.assertEqual(response.status_code, 201)

    @override_settings(NOTE_MAX_CONTENT_LENGTH=20)
    def test_content_over_max_length_is_rejected(self):
        response = self.create_note('x' * 21)
        self.assertEqual(response.status_code, 400)
        self.assertIn('content', response.data)

    @override_settings(NOTE_MAX_CONTENT_LENGTH=20)
    def test_update_over_max_length_is_rejected(self):
        note = Note.objects.create(user=self.user, title='t', content='short')
        response = self.client.patch(f'{NOTES_URL}{note.id}/', {'content': 'x' * 21}, format='json')
        self.assertEqual(response.status_code, 400)

    @override_settings(NOTES_MAX_PER_USER=2)
    def test_create_is_rejected_once_user_reaches_quota(self):
        self.assertEqual(self.create_note().status_code, 201)
        self.assertEqual(self.create_note().status_code, 201)
        response = self.create_note()
        self.assertEqual(response.status_code, 400)
        self.assertEqual(Note.objects.filter(user=self.user).count(), 2)

    @override_settings(NOTES_MAX_PER_USER=1)
    def test_archived_notes_count_towards_quota(self):
        Note.objects.create(user=self.user, title='t', content='c', archived=True)
        self.assertEqual(self.create_note().status_code, 400)

    @override_settings(NOTES_MAX_PER_USER=1)
    def test_quota_is_per_user(self):
        other = User.objects.create_user(username='bob', password='pw-bob-123')
        Note.objects.create(user=other, title='t', content='c')
        self.assertEqual(self.create_note().status_code, 201)

    @override_settings(NOTE_MAX_TAGS=2, NOTE_MAX_CATEGORIES=2)
    def test_tags_and_categories_per_note_are_capped(self):
        tags = [Tag.objects.create(name=f'tag{i}').pk for i in range(3)]
        categories = [Category.objects.create(name=f'cat{i}').pk for i in range(3)]
        ok = self.client.post(NOTES_URL, {'title': 't', 'content': 'c', 'tags': tags[:2], 'categories': categories[:2]},
                              format='json')
        self.assertEqual(ok.status_code, 201)
        too_many_tags = self.client.post(NOTES_URL, {'title': 't', 'content': 'c', 'tags': tags, 'categories': []},
                                         format='json')
        self.assertEqual(too_many_tags.status_code, 400)
        self.assertIn('tags', too_many_tags.data)
        too_many_categories = self.client.post(NOTES_URL, {'title': 't', 'content': 'c', 'tags': [],
                                                           'categories': categories}, format='json')
        self.assertEqual(too_many_categories.status_code, 400)
        self.assertIn('categories', too_many_categories.data)

    @override_settings(NOTE_MAX_TAGS=2)
    def test_tag_cap_is_checked_before_ids_are_resolved(self):
        # 1000 ids would be 1000 lookups; the length check must reject the request first
        with self.assertNumQueries(1):  # only the token auth lookup (token joined with its user)
            response = self.client.post(NOTES_URL, {'title': 't', 'content': 'c', 'tags': list(range(1, 1001)),
                                                    'categories': []}, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('tags', response.data)

    def test_non_object_body_is_rejected_with_400(self):
        for body in ([1, 2], 'x'):
            response = self.client.post(NOTES_URL, body, format='json')
            self.assertEqual(response.status_code, 400, body)

    def test_note_exposes_timestamps(self):
        response = self.create_note()
        self.assertIn('created_at', response.data)
        self.assertIn('updated_at', response.data)


class TagCategoryPermissionTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='alice', password='pw-alice-123')
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {Token.objects.create(user=self.user).key}')
        self.tag = Tag.objects.create(name='Important')

    def test_users_can_list_but_not_write_tags_or_categories(self):
        self.assertEqual(self.client.get('/api/tags/').status_code, 200)
        self.assertEqual(self.client.get('/api/categories/').status_code, 200)
        self.assertEqual(self.client.post('/api/tags/', {'name': 'spam'}, format='json').status_code, 403)
        self.assertEqual(self.client.post('/api/categories/', {'name': 'spam'}, format='json').status_code, 403)
        self.assertEqual(self.client.delete(f'/api/tags/{self.tag.pk}/').status_code, 403)
        self.assertTrue(Tag.objects.filter(pk=self.tag.pk).exists())

    def test_staff_can_write_tags(self):
        self.user.is_staff = True
        self.user.save()
        self.assertEqual(self.client.post('/api/tags/', {'name': 'new'}, format='json').status_code, 201)


class PurgeOldNotesTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='alice', password='pw-alice-123')

    def make_note(self, days_since_update):
        note = Note.objects.create(user=self.user, title='t', content='c')
        # update() bypasses auto_now, so the timestamp can be backdated
        Note.objects.filter(pk=note.pk).update(updated_at=timezone.now() - timedelta(days=days_since_update))
        return note

    @override_settings(NOTES_RETENTION_DAYS=30)
    def test_deletes_only_notes_not_updated_within_retention(self):
        old = self.make_note(31)
        recent = self.make_note(29)
        call_command('purge_old_notes', stdout=StringIO())
        self.assertFalse(Note.objects.filter(pk=old.pk).exists())
        self.assertTrue(Note.objects.filter(pk=recent.pk).exists())

    def test_dry_run_deletes_nothing(self):
        old = self.make_note(400)
        out = StringIO()
        call_command('purge_old_notes', '--dry-run', stdout=out)
        self.assertTrue(Note.objects.filter(pk=old.pk).exists())
        self.assertIn('1', out.getvalue())

    def test_purges_in_batches(self):
        tag = Tag.objects.create(name='t')
        for _ in range(5):
            self.make_note(40).tags.add(tag)
        keep = self.make_note(1)
        call_command('purge_old_notes', '--batch-size', '2', stdout=StringIO())
        self.assertEqual(list(Note.objects.values_list('pk', flat=True)), [keep.pk])
        self.assertTrue(Tag.objects.filter(pk=tag.pk).exists())

    def test_rejects_retention_below_one_day(self):
        note = self.make_note(400)
        with self.assertRaises(CommandError):
            call_command('purge_old_notes', '--days', '0', stdout=StringIO())
        with override_settings(NOTES_RETENTION_DAYS=-1), self.assertRaises(CommandError):
            call_command('purge_old_notes', stdout=StringIO())
        self.assertTrue(Note.objects.filter(pk=note.pk).exists())

    def test_days_option_overrides_setting(self):
        note = self.make_note(10)
        call_command('purge_old_notes', '--days', '7', stdout=StringIO())
        self.assertFalse(Note.objects.filter(pk=note.pk).exists())
