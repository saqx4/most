class NoCacheMiddleware:
    """Prevent browsers from caching authenticated pages.

    Without this, HTMX boosted navigations serve stale data because the
    browser returns a cached response instead of hitting the server.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if request.user.is_authenticated:
            response['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
            response['Pragma'] = 'no-cache'
        return response
