import logging
import os

from django.conf import settings
from rest_framework import status
from rest_framework.exceptions import APIException

logger = logging.getLogger(__name__)


class StorageFull(APIException):
    status_code = status.HTTP_507_INSUFFICIENT_STORAGE
    default_detail = 'Storage is full, so new data cannot be saved right now. Existing notes can still be read or deleted.'
    default_code = 'storage_full'


def free_bytes(path):
    """Space left for unprivileged writers on the filesystem holding path. Postgres runs as a normal user,
    so the root-reserved blocks are excluded, just as they are for it."""
    stats = os.statvfs(path)
    return stats.f_bavail * stats.f_frsize


def refuse_if_storage_full(action):
    """Raise StorageFull when the Postgres data filesystem has less than DB_WRITE_GUARD_MIN_FREE_MB free.
    DB_WRITE_GUARD_PATH is a read-only mount of an empty directory on that filesystem. Measuring the
    filesystem itself counts everything that fills it: data, WAL, temp and stats files. No-op when unset."""
    path = settings.DB_WRITE_GUARD_PATH
    if not path:
        return
    try:
        # Fail closed: a missing mount, or an ordinary directory that would measure the container's own
        # disk, must not silently switch the protection off
        if not os.path.ismount(path):
            raise OSError(f'{path} is not a mount point')
        # Any bind mount passes ismount, so also reject a filesystem bigger than the db volume can be,
        # which is what a bind of a root-disk directory would measure
        max_total_mb = settings.DB_WRITE_GUARD_MAX_TOTAL_MB
        stats = os.statvfs(path)
        if max_total_mb and stats.f_blocks * stats.f_frsize > max_total_mb * 1024 * 1024:
            raise OSError(f'{path} is on a {stats.f_blocks * stats.f_frsize // (1024 * 1024)} MB filesystem, '
                          f'over DB_WRITE_GUARD_MAX_TOTAL_MB={max_total_mb}')
        free = free_bytes(path)
    except OSError:
        logger.error('Write refused (%s): cannot measure free space at DB_WRITE_GUARD_PATH=%s', action, path,
                     exc_info=True)
        raise StorageFull()
    min_free = settings.DB_WRITE_GUARD_MIN_FREE_MB * 1024 * 1024
    if free < min_free:
        logger.warning('Write refused (%s): %d MB free on the database volume, minimum DB_WRITE_GUARD_MIN_FREE_MB=%d',
                       action, free // (1024 * 1024), settings.DB_WRITE_GUARD_MIN_FREE_MB)
        raise StorageFull()
