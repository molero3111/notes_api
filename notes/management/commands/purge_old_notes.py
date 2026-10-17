from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from notes.models import Note


class Command(BaseCommand):
    help = 'Delete notes that have not been updated within the retention period (NOTES_RETENTION_DAYS).'

    def add_arguments(self, parser):
        parser.add_argument('--days', type=int, default=None,
                            help='Retention in days; defaults to the NOTES_RETENTION_DAYS setting.')
        parser.add_argument('--dry-run', action='store_true', help='Report how many notes would be deleted.')

    def handle(self, *args, **options):
        days = options['days'] if options['days'] is not None else settings.NOTES_RETENTION_DAYS
        cutoff = timezone.now() - timedelta(days=days)
        old_notes = Note.objects.filter(updated_at__lt=cutoff)

        if options['dry_run']:
            self.stdout.write(f'{old_notes.count()} notes not updated since {cutoff:%Y-%m-%d %H:%M} UTC would be deleted.')
            return

        count = old_notes.count()
        old_notes.delete()
        self.stdout.write(f'Deleted {count} notes not updated since {cutoff:%Y-%m-%d %H:%M} UTC.')
