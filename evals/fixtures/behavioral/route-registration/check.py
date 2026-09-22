import sys
sys.path.insert(0, sys.argv[1])
import app
import client
assert app.request('/health') == (200, {'status': 'ok'})
assert app.request('/ready') == (200, {'ready': True})
assert app.request('/missing') == (404, {'error': 'not_found'})
assert client.health_status() == 'ok'
assert client.is_ready() is True
print('Readiness reaches application dispatcher and public client without health regression.')
# The client must use the public dispatcher and respect its response.
import importlib
calls = []
def controlled_request(path):
    calls.append(path)
    return 200, {'ready': False}
app.request = controlled_request
client = importlib.reload(client)
assert client.is_ready() is False
assert calls == ['/ready']
