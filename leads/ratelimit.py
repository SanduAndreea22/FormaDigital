from functools import wraps

from django.conf import settings
from django.core.cache import cache
from django.http import HttpResponse


def client_ip(request):
    """Client address. Behind the platform proxy the last X-Forwarded-For entry is the one the
    proxy itself appended; earlier entries can be forged by the visitor."""
    if not settings.DEBUG:
        forwarded = request.META.get('HTTP_X_FORWARDED_FOR', '')
        if forwarded:
            return forwarded.split(',')[-1].strip()
    return request.META.get('REMOTE_ADDR', '')


def rate_limit(scope, limit, window_seconds):
    """Allow at most `limit` POSTs per client per window. Every attempt counts, valid or not."""

    def decorator(view):
        @wraps(view)
        def wrapper(request, *args, **kwargs):
            key = f'rl:{scope}:{client_ip(request)}'
            cache.add(key, 0, window_seconds)
            try:
                count = cache.incr(key)
            except ValueError:  # key expired between add and incr
                cache.set(key, 1, window_seconds)
                count = 1
            if count > limit:
                return HttpResponse('Too many requests. Please try again later.', status=429, content_type='text/plain')
            return view(request, *args, **kwargs)

        return wrapper

    return decorator
