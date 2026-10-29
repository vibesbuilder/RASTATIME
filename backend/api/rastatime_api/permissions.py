import functools
from secrets import compare_digest

from django.conf import settings
from django.http import JsonResponse
from rest_framework.permissions import BasePermission
from rest_framework.request import Request

from .core.models import Role

REQUEST_PERMISSION_TYPE_MAP = {
    "GET": "view",
    "HEAD": "view",
    "OPTIONS": "view",
    "POST": "change",
    "PUT": "change",
    "DELETE": "delete",
    "PATCH": "change",
}


def get_own_obj(request, view):
    user = request.user
    if user is None or user.role != Role.HOST:
        return ""
    if request.method == "GET":
        return ""
    qs = view.queryset.all()
    try:
        model_owners = []
        for model in qs:
            owner = model.get_owner()
            if owner not in model_owners:
                model_owners.append(owner)
        if len(model_owners) == 1 and user in model_owners:
            return "own_"
    except AttributeError:
        return ""
    return ""


def get_permission_for_view(request, view):
    try:
        permission_type = REQUEST_PERMISSION_TYPE_MAP[request.method]
        if view.__class__.__name__ == "APIRootView":
            return f"{permission_type}_apiroot"
        model = view.model_permission_name
        own_obj = get_own_obj(request, view)
        return f"{permission_type}_{own_obj}{model}"
    except AttributeError:
        return None


def check_authorization_header(request: Request):
    auth_header = request.headers.get("authorization", "")
    if auth_header.startswith("Api-Key"):
        parts = auth_header.split()
        if len(parts) != 2:
            # RASTATIME 2026-10-28 - "Api-Key" without a value was a 500
            return False
        return compare_digest(parts[1], settings.CONFIG.general.api_key)
    return False


def is_internal_request(request) -> bool:
    """
    RASTATIME 2026-10-25 (role audit S3/S4) - for the plain Django views
    outside the DRF permission system (line-in, sound card, preflight,
    stream status): a valid Api-Key, or a direct call from this machine.

    "Direct" = loopback peer and no X-Forwarded-For.  Waitress trusts the
    local Apache for that header (waitress_serve.PROXY_OPTIONS): it keeps
    it and sets REMOTE_ADDR to the real client.  So everything Apache
    proxies from /api/v2/ needs the Api-Key - a browser in the LAN or on
    the internet is refused, the playout (which calls through Apache from
    this machine) sends its key - while the legacy PHP calling
    127.0.0.1:8765 directly needs none.
    """
    if check_authorization_header(request):
        return True
    peer = str(request.META.get("REMOTE_ADDR", ""))
    if peer.lower().startswith("::ffff:"):
        peer = peer[7:]
    proxied = "HTTP_X_FORWARDED_FOR" in request.META
    return not proxied and (peer == "::1" or peer.startswith("127."))


def internal_only(view):
    """Decorator for the plain Django views: 403 unless is_internal_request()."""

    @functools.wraps(view)
    def wrapper(request, *args, **kwargs):
        if not is_internal_request(request):
            return JsonResponse({"error": "internal callers only"}, status=403)
        return view(request, *args, **kwargs)

    return wrapper


class IsAdminOrOwnUser(BasePermission):
    """
    Implements Django Rest Framework permissions. This is separate from
    Django's standard permission system. For details see
    https://www.django-rest-framework.org/api-guide/permissions/#custom-permissions
    """

    # RASTATIME 2026-10-25 - an anonymous request carries Django's
    # AnonymousUser, whose is_superuser is a plain bool: calling it raised a
    # TypeError (HTTP 500 for /api/v2/users without a login) instead of a
    # refusal.
    @staticmethod
    def _is_admin(user) -> bool:
        return bool(user and user.is_authenticated and user.is_superuser())

    def has_permission(self, request, view):
        return self._is_admin(request.user)

    def has_object_permission(self, request, view, obj):
        if self._is_admin(request.user):
            return True
        return obj.username == request.user


class IsSystemTokenOrUser(BasePermission):
    """
    Implements Django Rest Framework permissions. This is separate from
    Django's standard permission system. For details see
    https://www.django-rest-framework.org/api-guide/permissions/#custom-permissions

    This permission allows services (liquidsoap, 3rd-party, etc) to connect with
    an API-Key header. All standard-users (i.e. not using the API-Key) have their
    permissions checked against Django's standard permission system.
    """

    def has_permission(self, request, view):
        if request.user and request.user.is_authenticated:
            perm = get_permission_for_view(request, view)
            # Required as view_apiroot is a permission not linked to a specific
            # model. This use-case allows users to view the base of the API
            # explorer. Their assigned group permissions determine further access
            # into the explorer.
            if perm == "view_apiroot":
                return True
            return request.user.has_perm(perm)
        return check_authorization_header(request)

    def has_object_permission(self, request, view, obj):
        if request.user and request.user.is_authenticated:
            perm = get_permission_for_view(request, view)
            return request.user.has_perm(perm, obj)
        return check_authorization_header(request)
