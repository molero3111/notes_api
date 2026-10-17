from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from notes.models import Note


class Command(BaseCommand):
    help = 'Delete notes that have not been updated within the retention period (NOTES_RETENTION_DAYS).'

    def add_arguments(self, parser):
        parser.add_argument('--days', type=int, default=None,
                            help='Retention in days; defaults to the NOTES_RETENTION_DAYS setting.')
        parser.add_argument('--batch-size', type=int, default=500, help='Notes deleted per query.')
        parser.add_argument('--dry-run', action='store_true', help='Report how many notes would be deleted.')

    def handle(self, *args, **options):
        days = options['days'] if options['days'] is not None else settings.NOTES_RETENTION_DAYS
        # A zero or negative retention would delete every note on the next scheduled run
        if days < 1:
            raise CommandError(f'Retention must be at least 1 day, got {days}.')
        if options['batch_size'] < 1:
            raise CommandError('--batch-size must be at least 1.')

        cutoff = timezone.now() - timedelta(days=days)
        old_notes = Note.objects.filter(updated_at__lt=cutoff)

        if options['dry_run']:
            self.stdout.write(f'{old_notes.count()} notes not updated since {cutoff:%Y-%m-%d %H:%M} UTC would be deleted.')
            return

        # Delete in pk batches and load only pks: the tag/category M2M makes Django collect each Note
        # in Python before deleting, and loading full rows (content included) could exceed the
        # scheduler's memory limit on a large purge.
        deleted = 0
        while True:
            batch = list(old_notes.values_list('pk', flat=True)[:options['batch_size']])
            if not batch:
                break
            Note.objects.filter(pk__in=batch, updated_at__lt=cutoff).only('pk').delete()
            deleted += len(batch)

        self.stdout.write(f'Deleted {deleted} notes not updated since {cutoff:%Y-%m-%d %H:%M} UTC.')
