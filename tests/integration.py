"""Live checks: temporary user accounts and links, using Python's standard library."""
import base64
import concurrent.futures
import hashlib
import hmac
import json
import os
from pathlib import Path
import secrets
import subprocess
import time
import unittest
import urllib.request
import urllib.error
from datetime import datetime, timedelta, timezone

BASE = os.environ.get('TEST_BASE_URL', 'http://localhost:8000')
TOKEN = None
class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args):
        return None
opener = urllib.request.build_opener(NoRedirect)
def request(path, method='GET', body=None, auth=True, token=None):
    selected_token = token if token is not None else TOKEN
    req = urllib.request.Request(BASE + path, data=json.dumps(body).encode() if body is not None else None, method=method,
        headers={'Content-Type': 'application/json', **({'Authorization': 'Bearer ' + selected_token} if auth and selected_token else {})})
    try:
        response = opener.open(req, timeout=30)
    except urllib.error.HTTPError as e:
        response = e
    with response:
        raw = response.read()
        return response.status, response.headers, json.loads(raw) if raw and response.headers.get_content_type() == 'application/json' else raw

def signed_token(claims, secret, algorithm='HS256'):
    def encode(value):
        return base64.urlsafe_b64encode(json.dumps(value).encode()).rstrip(b'=')
    content = encode({'alg': algorithm, 'typ': 'JWT'}) + b'.' + encode(claims)
    signature = base64.urlsafe_b64encode(hmac.new(secret.encode(), content, hashlib.sha256).digest()).rstrip(b'=')
    return (content + b'.' + signature).decode()

class Integration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        global TOKEN
        cls.password = secrets.token_urlsafe(24)
        cls.email = 'integration-' + str(time.time_ns()) + '@example.com'
        status, _, session = request('/api/auth/register', 'POST', {'email': cls.email, 'password': cls.password}, auth=False)
        if status != 201:
            raise AssertionError(session)
        TOKEN = session['access_token']
        cls.user = session['user']
        cls.other_email = 'other-' + str(time.time_ns()) + '@example.com'
        status, _, session = request('/api/auth/register', 'POST', {'email': cls.other_email, 'password': cls.password}, auth=False)
        if status != 201:
            raise AssertionError(session)
        cls.other_token = session['access_token']
        cls.other_user = session['user']
    @classmethod
    def tearDownClass(cls):
        if BASE == 'http://localhost:8000':
            # Remove only the two disposable accounts created by this test run.
            ids = [int(cls.user['id']), int(cls.other_user['id'])]
            subprocess.run(['docker', 'compose', 'exec', '-T', 'postgres', 'psql', '-U', 'bitly', '-d', 'bitly',
                            '-v', 'ON_ERROR_STOP=1', '-c', 'DELETE FROM users WHERE id IN (%d,%d)' % tuple(ids)],
                           check=True, capture_output=True)

    def setUp(self):
        self.codes = []
    def tearDown(self):
        for code in self.codes:
            request('/api/links/' + code, 'DELETE')
    def create(self, **extra):
        status, _, row = request('/api/links', 'POST', {'original_url': 'https://example.com/path', **extra})
        self.assertEqual(status, 201, row)
        self.codes.append(row['code'])
        return row
    def test_registration_login(self):
        self.assertEqual(request('/api/auth/me')[2], self.user)
        credentials = {'email': self.email.upper(), 'password': self.password}
        self.assertEqual(request('/api/auth/register', 'POST', credentials, auth=False)[0], 409)
        status, _, session = request('/api/auth/login', 'POST', credentials, auth=False)
        self.assertEqual(status, 200)
        self.assertEqual(request('/api/auth/me', token=session['access_token'])[2], self.user)
        credentials['password'] = 'wrong-password-123'
        self.assertEqual(request('/api/auth/login', 'POST', credentials, auth=False)[0], 401)
        credentials['email'] = 'missing-' + self.email
        self.assertEqual(request('/api/auth/login', 'POST', credentials, auth=False)[0], 401)
        self.assertEqual(request('/api/auth/register', 'POST', {'email': 'bad-email', 'password': self.password}, auth=False)[0], 422)
        self.assertEqual(request('/api/auth/register', 'POST', {'email': self.email, 'password': 'short'}, auth=False)[0], 422)
    def test_jwt_rejection_and_claims(self):
        for token in ['not-a-token', TOKEN[:-10]+'tamperedxx', 'old-management-token']:
            self.assertEqual(request('/api/links', token=token)[0], 401)
            self.assertEqual(request('/api/links', 'POST', {'original_url': 'https://example.com'}, token=token)[0], 401)
        if BASE != 'http://localhost:8000':
            return  # Signing key tests are local-only; never require a remote deployment secret.
        env = dict(line.split('=',1) for line in Path('.env').read_text().splitlines() if '=' in line)
        secret = env['JWT_SECRET']
        claims = {'sub': str(self.user['id']), 'iat': int(time.time())-60, 'exp': int(time.time())+60, 'iss': 'bitly-lab', 'aud': 'bitly-api'}
        self.assertEqual(request('/api/auth/me', token=signed_token(claims, secret))[0], 200)
        for override in [{'exp': int(time.time())-1}, {'aud': 'wrong-api'}, {'iss': 'wrong-issuer'}, {'sub': '999999999999'}]:
            self.assertEqual(request('/api/links', token=signed_token({**claims, **override}, secret))[0], 401)
        no_exp = {k:v for k,v in claims.items() if k != 'exp'}
        self.assertEqual(request('/api/links', token=signed_token(no_exp, secret))[0], 401)
        self.assertEqual(request('/api/links', token=signed_token(claims, secret, 'none'))[0], 401)
    def test_ownership(self):
        row = self.create(created_by=self.other_user['id'])
        path = '/api/links/'+row['code']
        self.assertFalse(any(x['code']==row['code'] for x in request('/api/links', token=self.other_token)[2]))
        self.assertEqual(request(path, 'PUT', {'original_url':'https://example.org'}, token=self.other_token)[0], 404)
        self.assertEqual(request(path, 'DELETE', token=self.other_token)[0], 404)
        for method, body in [('PUT', {'original_url':'https://example.org'}), ('DELETE',None)]:
            self.assertEqual(request(path, method, body, auth=False)[0], 401)
        self.assertEqual(request(row['short_path'], auth=False)[0], 302)
        self.assertEqual(request(path, auth=False)[0], 200)
        self.assertEqual(request(path)[2]['original_url'], 'https://example.com/path')
    def test_crud_cache(self):
        row = self.create(); code = row['code']
        for _ in range(2):
            status, headers, _ = request('/s/' + code, auth=False)
            self.assertEqual(status, 302)
            self.assertEqual(headers['Location'], 'https://example.com/path')
        self.assertTrue(any(x['code'] == code for x in request('/api/links')[2]))
        self.assertEqual(request('/api/links/' + code, 'PUT', {'original_url': 'https://example.org/new'})[0], 200)
        self.assertEqual(request('/s/' + code)[1]['Location'], 'https://example.org/new')
        self.assertEqual(request('/api/links/' + code, 'DELETE')[0], 204)
        self.assertEqual(request('/s/' + code)[0], 404)
    def test_alias_conflict_validation_auth(self):
        alias = 'test-' + str(time.time_ns()); self.create(alias=alias)
        self.assertEqual(request('/api/links', 'POST', {'original_url': 'https://example.com', 'alias': alias}, token=self.other_token)[0], 409)
        for payload in [{'original_url': 'javascript:alert(1)'}, {'original_url': 'https://example.com', 'alias': 'bad space'}, {'original_url': 'https://example.com', 'expires_at': '2020-01-01T00:00:00Z'}]:
            self.assertEqual(request('/api/links', 'POST', payload)[0], 422)
        self.assertEqual(request('/api/links', auth=False)[0], 401)
        self.assertEqual(request('/api/links', 'POST', {'original_url': 'https://example.com'}, auth=False)[0], 401)
    def test_expiration_even_on_cache_hit(self):
        row = self.create(expires_at=(datetime.now(timezone.utc) + timedelta(seconds=2)).isoformat())
        self.assertEqual(request(row['short_path'])[0], 302)
        time.sleep(2.2)
        self.assertEqual(request(row['short_path'])[0], 410)
        self.assertEqual(request('/api/links/' + row['code'])[0], 410)
    def test_concurrent_unique_codes(self):
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
            responses = list(executor.map(lambda _: request('/api/links', 'POST', {'original_url': 'https://example.com'}), range(24)))
        self.codes.extend(row['code'] for status, _, row in responses if status == 201)
        self.assertTrue(all(status == 201 for status, _, _ in responses))
        self.assertEqual(len(set(self.codes)), 24)
    def test_gateway_service_routes(self):
        self.assertEqual(request('/health/read')[2]['service'], 'read')
        self.assertEqual(request('/health/write')[2]['service'], 'write')
        read_schema = request('/read/openapi.json')[2]
        write_schema = request('/write/openapi.json')[2]
        self.assertIn('get', read_schema['paths']['/api/links'])
        self.assertNotIn('post', read_schema['paths']['/api/links'])
        self.assertIn('post', write_schema['paths']['/api/links'])
        self.assertNotIn('get', write_schema['paths']['/api/links'])
        self.assertNotIn('/s/{code}', write_schema['paths'])
        self.assertNotIn('/api/auth/register', read_schema['paths'])
        self.assertEqual(request('/docs')[0], 200)
        self.assertEqual(request('/read/docs')[0], 200)
        self.assertEqual(request('/write/docs')[0], 200)

    def test_missing(self):
        self.assertEqual(request('/s/nonexistent-code')[0], 404)
        self.assertEqual(request('/health')[0], 200)

if __name__ == '__main__':
    unittest.main(verbosity=2)
