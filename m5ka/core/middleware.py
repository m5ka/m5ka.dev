from django.conf import settings
from django.contrib.auth.views import redirect_to_login
from django.urls import Resolver404, resolve, reverse


class RequireTwoFactorMiddleware:
    """
    Sends admin users who haven't entered a 2FA code this session to do so before
    they can load anything else. Must come after django-otp's OTPMiddleware.
    """

    # what the verification page itself needs to load, sign in or sign out
    allowed_url_names = {
        "verify_2fa",
        "wagtailadmin_login",
        "wagtailadmin_logout",
        "wagtailadmin_javascript_catalog",
        "wagtailadmin_sprite",
    }

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if self.must_verify(request):
            return redirect_to_login(request.get_full_path(), reverse("verify_2fa"))
        return self.get_response(request)

    def must_verify(self, request):
        user = request.user
        if not settings.REQUIRE_2FA or not user.is_authenticated or user.is_verified():
            return False
        if not (user.is_staff or user.has_perm("wagtailadmin.access_admin")):
            return False
        try:
            return resolve(request.path_info).url_name not in self.allowed_url_names
        except Resolver404:
            return True
