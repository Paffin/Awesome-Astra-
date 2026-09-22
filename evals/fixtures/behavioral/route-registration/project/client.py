from app import request

def health_status():
    return request('/health')[1]['status']
