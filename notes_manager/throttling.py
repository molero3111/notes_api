import hashlib
import ipaddress
import logging

from django.conf import settings
from django_redis.exceptions import ConnectionInterrupted
from redis.exceptions import RedisError
from rest_framework.throttling import SimpleRateThrottle

logger = logging.getLogger(__name__)

# What an unreachable or failing cache raises; anything else is a real bug and should surface
CACHE_ERRORS = (ConnectionInterrupted, RedisError, OSError)


class NotesRateThrottle(SimpleRateThrottle):
    """Rate limit read from NOTES_THROTTLE_RATES at request time; a no-op unless THROTTLING_ENABLED."""

    # IPv6 clients share a bucket per prefix of this length, since one subscriber controls the prefix
    ipv6_prefix = 64

    def get_rate(self):
        return settings.NOTES_THROTTLE_RATES[self.scope]

    def allow_request(self, request, view):
        if not settings.THROTTLING_ENABLED:
            return True
        # Build the key outside the try, so request parsing errors and bugs aren't mistaken for an outage
        self.get_cache_key(request, view)
        try:
            return super().allow_request(request, view)
        except CACHE_ERRORS:
            # The counters live in Redis; if it's unreachable, serve the request rather than fail all of them
            logger.warning('Throttle %s skipped: cache unavailable', self.scope, exc_info=True)
            return True

    def get_ident(self, request):
        # Behind a proxy chain REMOTE_ADDR is the proxy, so CLIENT_IP_HEADER names a header the trusted
        # edge always overwrites (e.g. HTTP_CF_CONNECTING_IP). X-Forwarded-For is never used: DRF's
        # default reads it, and a client can set it to any value to get a fresh bucket.
        header = settings.CLIENT_IP_HEADER
        value = request.META.get(header, '').split(',')[0].strip() if header else ''
        return client_bucket(value or request.META.get('REMOTE_ADDR', ''), self.ipv6_prefix)

    def ident_cache_key(self, request, suffix=''):
        return self.cache_format % {'scope': self.scope, 'ident': self.get_ident(request) + suffix}


def client_bucket(address, ipv6_prefix=64):
    """IPv4 addresses are their own bucket; IPv6 ones share their /ipv6_prefix network."""
    try:
        ip = ipaddress.ip_address(address)
    except ValueError:
        return address
    if ip.version == 6:
        if ip.ipv4_mapped:
            return str(ip.ipv4_mapped)
        return str(ipaddress.ip_network(f'{ip}/{ipv6_prefix}', strict=False))
    return str(ip)


class AnonThrottle(NotesRateThrottle):
    scope = 'anon'

    def get_cache_key(self, request, view):
        if request.user and request.user.is_authenticated:
            return None
        return self.ident_cache_key(request)


class UserThrottle(NotesRateThrottle):
    scope = 'user'

    def get_cache_key(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return None
        return self.cache_format % {'scope': self.scope, 'ident': request.user.pk}


class LoginThrottle(NotesRateThrottle):
    """Tight limit per client and username, so one person's failed logins don't lock out a shared IP."""
    scope = 'login'

    def get_cache_key(self, request, view):
        username = request.data.get('username', '') if hasattr(request.data, 'get') else ''
        # Hashed so a huge username can't write huge Redis keys and push other throttles out of the cache
        # surrogatepass: JSON can carry lone surrogates, which plain UTF-8 encoding rejects
        digest = hashlib.sha256(str(username).strip().lower().encode('utf-8', 'surrogatepass')).hexdigest()[:32]
        return self.ident_cache_key(request, suffix=f'|{digest}')


class LoginIPThrottle(NotesRateThrottle):
    """Looser limit per client across all usernames, against spraying many accounts from one IP."""
    scope = 'login_ip'

    def get_cache_key(self, request, view):
        return self.ident_cache_key(request)


class RegisterThrottle(NotesRateThrottle):
    scope = 'register'
    # Sign-ups are where address rotation pays off, and a /56 or /48 is easy to get
    ipv6_prefix = 48

    def get_cache_key(self, request, view):
        return self.ident_cache_key(request)
