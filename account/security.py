import time
import logging
from functools import wraps

from django.core.cache import cache
from django.http import HttpResponse

security_logger = logging.getLogger("security")


def _client_ip(request):
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "unknown")


def rate_limit(max_requests, window_seconds, key_prefix, post_only=True):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            if post_only and request.method != "POST":
                return view_func(request, *args, **kwargs)

            bucket = int(time.time() // window_seconds)
            cache_key = f"rate:{key_prefix}:{_client_ip(request)}:{bucket}"
            current = cache.get(cache_key, 0)

            if current >= max_requests:
                security_logger.warning(
                    "Rate limit exceeded for key=%s ip=%s path=%s",
                    key_prefix,
                    _client_ip(request),
                    request.path,
                )
                return HttpResponse(
                    "Too many requests. Please try again later.",
                    status=429,
                )

            cache.set(cache_key, current + 1, timeout=window_seconds)
            return view_func(request, *args, **kwargs)

        return _wrapped

    return decorator
