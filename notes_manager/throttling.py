import ipaddress

from django.conf import settings
from rest_framework.throttling import SimpleRateThrottle


class NotesRateThrottle(SimpleRateThrottle):
    """Rate limit read from NOTES_THROTTLE_RATES at request time; a no-op unless THROTTLING_ENABLED."""

    def get_rate(self):
        return settings.NOTES_THROTTLE_RATES[self.scope]

    def allow_request(self, request, view):
        if not settings.THROTTLING_ENABLED:
            return True
        return super().allow_request(request, view)

    def get_ident(self, request):
        # Behind a proxy chain REMOTE_ADDR is the proxy, so CLIENT_IP_HEADER names a header the trusted
        # edge always overwrites (e.g. HTTP_CF_CONNECTING_IP). X-Forwarded-For is never used: DRF's
        # default reads it, and a client can set it to any value to get a fresh bucket.
        header = settings.CLIENT_IP_HEADER
        value = request.META.get(header, '').split(',')[0].strip() if header else ''
        return client_bucket(value or request.META.get('REMOTE_ADDR', ''))

    def ident_cache_key(self, request):
        return self.cache_format % {'scope': self.scope, 'ident': self.get_ident(request)}


def client_bucket(address):
    """IPv4 addresses are their own bucket; IPv6 ones share their /64, which one subscriber controls."""
    try:
        ip = ipaddress.ip_address(address)
    except ValueError:
        return address
    if ip.version == 6:
        if ip.ipv4_mapped:
            return str(ip.ipv4_mapped)
        return str(ipaddress.ip_network(f'{ip}/64', strict=False))
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
    scope = 'login'

    def get_cache_key(self, request, view):
        return self.ident_cache_key(request)


class RegisterThrottle(NotesRateThrottle):
    scope = 'register'

    def get_cache_key(self, request, view):
        return self.ident_cache_key(request)
