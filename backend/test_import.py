import sys
sys.path.insert(0, '.')

try:
    from app.api.routes.messaging_accounts import router
    print('SUCCESS: Router imported')
    print('Prefix:', router.prefix)
    print('Number of routes:', len(router.routes))
    for route in router.routes:
        if hasattr(route, 'path'):
            print(f'  Route: {route.path}')
except Exception as e:
    print(f'ERROR: {e}')
    import traceback
    traceback.print_exc()
