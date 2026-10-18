from datetime import timedelta

from django.contrib.auth.models import User
from django.core.cache import cache
from django.test import override_settings
from django.utils import timezone
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

LOCMEM_CACHE = {'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}
RATES = {'anon': '1000/min', 'user': '1000/min', 'login': '1000/min', 'register': '1000/hour'}


def rates(**overrides):
    return {**RATES, **overrides}


@override_settings(CACHES=LOCMEM_CACHE, THROTTLING_ENABLED=True, CLIENT_IP_HEADER='HTTP_CF_CONNECTING_IP',
                   NOTES_THROTTLE_RATES=RATES, MAX_USERS=0, REGISTRATIONS_PER_DAY=0)
class ThrottleTestCase(APITestCase):
    def setUp(self):
        cache.clear()

    def register(self, username, ip='203.0.113.1', **headers):
        return self.client.post('/api/register/', {'username': username, 'password': 'Passw0rd!xyz',
                                                   'email': f'{username}@example.com'},
                                format='json', HTTP_CF_CONNECTING_IP=ip, **headers)

    def login(self, ip='203.0.113.1', password='wrong'):
        return self.client.post('/api/login/', {'username': 'alice', 'password': password},
                                format='json', HTTP_CF_CONNECTING_IP=ip)


class RegisterThrottleTests(ThrottleTestCase):
    @override_settings(NOTES_THROTTLE_RATES=rates(register='2/hour'))
    def test_register_is_limited_per_ip(self):
        self.assertEqual(self.register('u1').status_code, 201)
        self.assertEqual(self.register('u2').status_code, 201)
        self.assertEqual(self.register('u3').status_code, 429)
        self.assertEqual(self.register('u4', ip='198.51.100.7').status_code, 201)
        self.assertFalse(User.objects.filter(username='u3').exists())

    @override_settings(NOTES_THROTTLE_RATES=rates(register='1/hour'))
    def test_failed_registrations_count_towards_the_limit(self):
        self.assertEqual(self.client.post('/api/register/', {}, format='json',
                                          HTTP_CF_CONNECTING_IP='203.0.113.1').status_code, 400)
        self.assertEqual(self.register('u1').status_code, 429)

    @override_settings(REGISTRATIONS_PER_DAY=3)
    def test_register_has_a_global_daily_cap_across_ips(self):
        for i in range(3):
            self.assertEqual(self.register(f'u{i}', ip=f'198.51.100.{i}').status_code, 201)
        self.assertEqual(self.register('u9', ip='192.0.2.9').status_code, 429)
        self.assertFalse(User.objects.filter(username='u9').exists())

    @override_settings(REGISTRATIONS_PER_DAY=1, NOTES_THROTTLE_RATES=rates(register='1/hour'))
    def test_rejected_attempts_do_not_use_up_the_daily_cap(self):
        # One IP hammering register must not lock everyone else out: only created accounts count
        self.client.post('/api/register/', {}, format='json', HTTP_CF_CONNECTING_IP='203.0.113.1')
        for _ in range(5):
            self.register('spam', ip='203.0.113.1')
        self.assertEqual(self.register('real', ip='198.51.100.7').status_code, 201)

    @override_settings(REGISTRATIONS_PER_DAY=1)
    def test_daily_cap_only_counts_the_last_24_hours(self):
        old = User.objects.create_user(username='old', password='x')
        User.objects.filter(pk=old.pk).update(date_joined=timezone.now() - timedelta(days=2))
        self.assertEqual(self.register('new').status_code, 201)

    @override_settings(MAX_USERS=2)
    def test_registration_closes_at_max_users(self):
        User.objects.create_user(username='a', password='x')
        self.assertEqual(self.register('b').status_code, 201)
        response = self.register('c')
        self.assertEqual(response.status_code, 403)
        self.assertEqual(User.objects.count(), 2)

    @override_settings(NOTES_THROTTLE_RATES=rates(register='1/hour'))
    def test_spoofed_forwarded_for_does_not_reset_the_limit(self):
        self.assertEqual(self.register('u1').status_code, 201)
        self.assertEqual(self.register('u2', HTTP_X_FORWARDED_FOR='10.9.9.9').status_code, 429)


class LoginThrottleTests(ThrottleTestCase):
    def setUp(self):
        super().setUp()
        User.objects.create_user(username='alice', password='right-pass-123')

    @override_settings(NOTES_THROTTLE_RATES=rates(login='3/min'))
    def test_login_is_limited_per_ip(self):
        for _ in range(3):
            self.assertEqual(self.login().status_code, 400)
        self.assertEqual(self.login(password='right-pass-123').status_code, 429)
        self.assertEqual(self.login(ip='198.51.100.7', password='right-pass-123').status_code, 200)


class GeneralThrottleTests(ThrottleTestCase):
    @override_settings(NOTES_THROTTLE_RATES=rates(anon='2/min'))
    def test_anonymous_requests_are_limited_per_ip(self):
        for _ in range(2):
            self.assertEqual(self.client.get('/api/', HTTP_CF_CONNECTING_IP='203.0.113.1').status_code, 200)
        self.assertEqual(self.client.get('/api/', HTTP_CF_CONNECTING_IP='203.0.113.1').status_code, 429)
        self.assertEqual(self.client.get('/api/', HTTP_CF_CONNECTING_IP='198.51.100.7').status_code, 200)

    @override_settings(NOTES_THROTTLE_RATES=rates(user='2/min'))
    def test_authenticated_requests_are_limited_per_user(self):
        user = User.objects.create_user(username='bob', password='x')
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {Token.objects.create(user=user).key}')
        for ip in ('203.0.113.1', '198.51.100.7'):
            self.assertEqual(self.client.get('/api/notes/', HTTP_CF_CONNECTING_IP=ip).status_code, 200)
        self.assertEqual(self.client.get('/api/notes/', HTTP_CF_CONNECTING_IP='192.0.2.9').status_code, 429)

    @override_settings(NOTES_THROTTLE_RATES=rates(anon='1/min'))
    def test_ipv6_clients_are_grouped_by_64_prefix(self):
        # One subscriber controls a whole /64, so rotating the interface id must not reset the limit
        self.assertEqual(self.client.get('/api/', HTTP_CF_CONNECTING_IP='2001:db8:1:2::1').status_code, 200)
        self.assertEqual(self.client.get('/api/', HTTP_CF_CONNECTING_IP='2001:db8:1:2:aaaa::ffff').status_code, 429)
        self.assertEqual(self.client.get('/api/', HTTP_CF_CONNECTING_IP='2001:db8:1:3::1').status_code, 200)

    @override_settings(NOTES_THROTTLE_RATES=rates(anon='1/min'), CLIENT_IP_HEADER='')
    def test_without_client_ip_header_remote_addr_is_used_not_forwarded_for(self):
        self.assertEqual(self.client.get('/api/', HTTP_X_FORWARDED_FOR='10.0.0.1').status_code, 200)
        self.assertEqual(self.client.get('/api/', HTTP_X_FORWARDED_FOR='10.0.0.2').status_code, 429)

    @override_settings(THROTTLING_ENABLED=False, NOTES_THROTTLE_RATES=rates(anon='1/min', register='1/hour'))
    def test_disabled_by_default_setting_lets_everything_through(self):
        for _ in range(3):
            self.assertEqual(self.client.get('/api/').status_code, 200)
        self.assertEqual(self.register('u1').status_code, 201)
        self.assertEqual(self.register('u2').status_code, 201)
