from datetime import timedelta
from unittest import mock

from django.contrib.auth.models import User
from django.core.cache import cache
from django.test import override_settings
from django.utils import timezone
from rest_framework.authtoken.models import Token
from rest_framework.parsers import JSONParser
from rest_framework.request import Request
from rest_framework.test import APIRequestFactory, APITestCase

from notes_manager.throttling import LoginThrottle

LOCMEM_CACHE = {'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}
RATES = {'anon': '1000/min', 'user': '1000/min', 'login': '1000/min', 'login_ip': '1000/min',
         'register': '1000/hour'}


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

    def login(self, ip='203.0.113.1', password='wrong', username='alice'):
        return self.client.post('/api/login/', {'username': username, 'password': password},
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

    @override_settings(REGISTRATIONS_PER_DAY=1)
    def test_daily_cap_response_has_retry_after(self):
        self.assertEqual(self.register('u1').status_code, 201)
        response = self.register('u2', ip='198.51.100.7')
        self.assertEqual(response.status_code, 429)
        self.assertTrue(0 < int(response['Retry-After']) <= 86400)

    @override_settings(NOTES_THROTTLE_RATES=rates(register='1/hour'))
    def test_register_groups_ipv6_by_48_prefix(self):
        # A /56 or /48 is easy to get, so rotating /64s inside it must not reset the sign-up limit
        self.assertEqual(self.register('u1', ip='2001:db8:1:1::1').status_code, 201)
        self.assertEqual(self.register('u2', ip='2001:db8:1:ff::1').status_code, 429)
        self.assertEqual(self.register('u3', ip='2001:db8:2:1::1').status_code, 201)

    @override_settings(REGISTRATIONS_PER_DAY=2)
    def test_retry_after_uses_the_signup_that_frees_a_slot_when_over_the_cap(self):
        # 3 sign-ups in the window with a cap of 2: a slot frees when the 2nd-oldest (10 h ago) ages out
        now = timezone.now()
        for name, hours_ago in (('a', 23), ('b', 10), ('c', 1)):
            user = User.objects.create_user(username=name, password='x')
            User.objects.filter(pk=user.pk).update(date_joined=now - timedelta(hours=hours_ago))
        retry_after = int(self.register('d')['Retry-After'])
        self.assertAlmostEqual(retry_after, 14 * 3600, delta=120)

    @override_settings(DB_WRITE_GUARD_PATH='/', DB_WRITE_GUARD_MIN_FREE_MB=1024 ** 3)
    def test_registration_is_refused_when_storage_is_full(self):
        response = self.register('u1')
        self.assertEqual(response.status_code, 507)
        self.assertFalse(User.objects.filter(username='u1').exists())

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

    def test_successful_login_returns_token(self):
        response = self.login(password='right-pass-123')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['token'], Token.objects.get(user__username='alice').key)

    @override_settings(NOTES_THROTTLE_RATES=rates(login='3/min'))
    def test_login_is_limited_per_ip_and_username(self):
        for _ in range(3):
            self.assertEqual(self.login().status_code, 400)
        self.assertEqual(self.login(password='right-pass-123').status_code, 429)
        self.assertEqual(self.login(ip='198.51.100.7', password='right-pass-123').status_code, 200)

    @override_settings(NOTES_THROTTLE_RATES=rates(login='3/min'))
    def test_one_users_failures_do_not_block_others_on_a_shared_ip(self):
        User.objects.create_user(username='carol', password='carol-pass-123')
        for _ in range(4):
            self.login()
        self.assertEqual(self.login(username='carol', password='carol-pass-123').status_code, 200)

    def test_login_throttle_key_is_bounded_and_case_insensitive(self):
        factory = APIRequestFactory()

        def key_for(username):
            request = Request(factory.post('/api/login/', {'username': username, 'password': 'x'}, format='json',
                                           HTTP_CF_CONNECTING_IP='203.0.113.1'), parsers=[JSONParser()])
            return LoginThrottle().get_cache_key(request, None)

        self.assertLess(len(key_for('x' * 100000)), 200)
        self.assertEqual(key_for('Alice'), key_for(' alice '))
        self.assertNotEqual(key_for('alice'), key_for('bob'))

    def test_lone_surrogate_username_is_a_400(self):
        response = self.client.post('/api/login/', '{"username": "\\ud800", "password": "x"}',
                                    content_type='application/json', HTTP_CF_CONNECTING_IP='203.0.113.1')
        self.assertEqual(response.status_code, 400)

    def test_malformed_login_body_is_a_400_not_a_cache_warning(self):
        with self.assertNoLogs('notes_manager.throttling', level='WARNING'):
            response = self.client.post('/api/login/', '{not json', content_type='application/json',
                                        HTTP_CF_CONNECTING_IP='203.0.113.1')
        self.assertEqual(response.status_code, 400)

    @override_settings(NOTES_THROTTLE_RATES=rates(login_ip='3/min'))
    def test_login_has_a_looser_per_ip_limit_across_usernames(self):
        for i in range(3):
            self.login(username=f'nobody{i}')
        self.assertEqual(self.login(password='right-pass-123').status_code, 429)


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

    @override_settings(NOTES_THROTTLE_RATES=rates(anon='1/min'))
    def test_ipv4_mapped_ipv6_is_the_same_client_as_ipv4(self):
        self.assertEqual(self.client.get('/api/', HTTP_CF_CONNECTING_IP='203.0.113.1').status_code, 200)
        self.assertEqual(self.client.get('/api/', HTTP_CF_CONNECTING_IP='::ffff:203.0.113.1').status_code, 429)

    @override_settings(NOTES_THROTTLE_RATES=rates(anon='1/min'))
    def test_cache_outage_fails_open(self):
        with mock.patch('django.core.cache.cache.get', side_effect=ConnectionError('redis down')), \
                self.assertLogs('notes_manager.throttling', level='WARNING'):
            for _ in range(3):
                self.assertEqual(self.client.get('/api/', HTTP_CF_CONNECTING_IP='203.0.113.1').status_code, 200)

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
