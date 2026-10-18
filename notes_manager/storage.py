import logging
import time

from django.conf import settings
from django.db import DatabaseError, connection, transaction
from rest_framework import status
from rest_framework.exceptions import APIException

logger = logging.getLogger(__name__)

_cache = {'checked_at': None, 'bytes': 0}


class StorageFull(APIException):
    status_code = status.HTTP_507_INSUFFICIENT_STORAGE
    default_detail = 'Storage is full, so new data cannot be saved right now. Existing notes can still be read or deleted.'
    default_code = 'storage_full'


def database_bytes():
    """On-disk size of every database in the cluster plus its WAL, which together fill the data volume."""
    with connection.cursor() as cursor:
        cursor.execute('SELECT sum(pg_database_size(datname)) FROM pg_database')
        total = int(cursor.fetchone()[0] or 0)
        try:
            # Savepoint, so a permission error here doesn't abort the request's transaction
            with transaction.atomic():
                cursor.execute('SELECT coalesce(sum(size), 0) FROM pg_ls_waldir()')
                total += int(cursor.fetchone()[0])
        except DatabaseError:
            pass  # pg_ls_waldir needs superuser or pg_monitor; the database size alone still bounds most growth
    return total


def reset_cache():
    _cache['checked_at'] = None


def storage_full():
    """True once the cluster reaches DB_WRITE_GUARD_MAX_MB (0 disables). Measured at most every
    DB_WRITE_GUARD_CACHE_SECONDS per worker, since growth between checks is bounded by the throttles."""
    limit_mb = settings.DB_WRITE_GUARD_MAX_MB
    if not limit_mb:
        return False
    now = time.monotonic()
    checked_at = _cache['checked_at']
    if checked_at is None or now - checked_at >= settings.DB_WRITE_GUARD_CACHE_SECONDS:
        _cache['bytes'] = database_bytes()
        _cache['checked_at'] = now
    return _cache['bytes'] >= limit_mb * 1024 * 1024


def refuse_if_storage_full(action):
    if storage_full():
        logger.warning('Write refused (%s): database is %d MB, limit DB_WRITE_GUARD_MAX_MB=%d',
                       action, _cache['bytes'] // (1024 * 1024), settings.DB_WRITE_GUARD_MAX_MB)
        raise StorageFull()
