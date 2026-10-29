from django.conf import settings

# The site ships no scripts and no third-party assets, so the policy can be strict.
CSP = (
    "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; "
    "font-src 'self'; form-action 'self'; frame-ancestors 'none'; base-uri 'self'; object-src 'none'"
)
PERMISSIONS_POLICY = 'camera=(), microphone=(), geolocation=(), payment=(), usb=(), interest-cohort=()'


class SecurityHeadersMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        response.headers.setdefault('Permissions-Policy', PERMISSIONS_POLICY)
        # Django's admin has its own inline assets; keep the strict policy off it.
        if not request.path.startswith('/' + settings.ADMIN_URL):
            response.headers.setdefault('Content-Security-Policy', CSP)
        return response
