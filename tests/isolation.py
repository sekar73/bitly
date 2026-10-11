"""Local-only failure drill. Restores both services and deletes its own test data."""
import secrets
import subprocess
import time
from integration import BASE, request

if BASE != 'http://localhost:8000':
    raise SystemExit('This drill targets only the default local Compose stack.')

def compose(*args):
    subprocess.run(['docker', 'compose', *args], check=True, capture_output=True)

def ready(service):
    for _ in range(30):
        if request('/health/'+service, auth=False)[0] == 200:
            return
        time.sleep(1)
    raise AssertionError(service+' did not recover')

credentials = {'email': 'isolation-'+str(time.time_ns())+'@example.com', 'password': secrets.token_urlsafe(24)}
status, _, session = request('/api/auth/register', 'POST', credentials, auth=False)
assert status == 201, status
token = session['access_token']
user_id = int(session['user']['id'])
try:
    status, _, link = request('/api/links', 'POST', {'original_url':'https://example.com/isolation'}, token=token)
    assert status == 201, status
    # Warm the redirect cache before stopping the writer.
    assert request(link['short_path'], auth=False)[0] == 302
    compose('stop', 'write')
    assert request('/health/write', auth=False)[0] in (502, 503, 504)
    assert request('/health/read', auth=False)[0] == 200
    assert request(link['short_path'], auth=False)[0] == 302
    assert request('/api/links/'+link['code'], auth=False)[0] == 200
    assert request('/api/links', token=token)[0] == 200
    assert request('/api/links', 'POST', {'original_url':'https://example.com'}, token=token)[0] in (502, 503, 504)
    assert request('/', auth=False)[0] == 200
    compose('start', 'write')
    ready('write')
    compose('stop', 'read')
    assert request('/health/read', auth=False)[0] in (502, 503, 504)
    assert request('/health/write', auth=False)[0] == 200
    assert request('/api/auth/login', 'POST', credentials, auth=False)[0] == 200
    assert request('/api/links', 'POST', {'original_url':'https://example.com/write-only'}, token=token)[0] == 201
    assert request('/', auth=False)[0] == 200
    print('PASS: reads survive a writer outage; authentication/writes survive a reader outage; gateway serves the UI in both.')
finally:
    compose('start', 'write', 'read')
    ready('write')
    ready('read')
    compose('exec', '-T', 'postgres', 'psql', '-U', 'bitly', '-d', 'bitly', '-v', 'ON_ERROR_STOP=1', '-c',
            'DELETE FROM urls WHERE created_by=%d; DELETE FROM users WHERE id=%d;' % (user_id, user_id))
