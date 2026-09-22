from handlers import health
ROUTES = {'/health': health}

def request(path):
    if path not in ROUTES:
        return 404, {'error': 'not_found'}
    return 200, ROUTES[path]()
