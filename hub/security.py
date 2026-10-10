from django.http import HttpResponseForbidden
from django.utils.cache import add_never_cache_headers
from django.utils.deprecation import MiddlewareMixin
from django_otp import devices_for_user


def axes_username(request, credentials=None):
    if credentials and credentials.get("username"):
        return credentials["username"]
    return request.POST.get("auth-username") or request.POST.get("username")


class AccountSecurityMiddleware(MiddlewareMixin):
    """Ferme l'enrôlement initial dès qu'un facteur confirmé existe.

    Le wizard tiers ne vérifie ce cas que dans GET : un POST peut autrement
    ajouter un appareil depuis une ancienne session sans OTP. La vérification
    porte sur chaque étape et chaque nom d'appareil, y compris le QR provisoire.
    La récupération d'un compte configuré utilise ses codes ou la procédure privée.
    """

    def process_request(self, request):
        request._initial_otp_device = request.session.get("otp_device_id")

    def process_view(self, request, view_func, view_args, view_kwargs):
        match = request.resolver_match
        if (match and match.namespace == "two_factor" and match.url_name in {"setup", "qr"}
                and request.user.is_authenticated
                and next(devices_for_user(request.user, confirmed=True), None) is not None):
            return HttpResponseForbidden("Un second facteur est déjà configuré. Utilisez la récupération privée.")

    def process_response(self, request, response):
        match = request.resolver_match
        if (match and match.namespace == "two_factor" and match.url_name == "setup"
                and not request._initial_otp_device and request.session.get("otp_device_id")):
            # L'enrôlement élève une session déjà authentifiée par mot de passe.
            # Le wizard ne fait pas tourner son identifiant : révoquer l'ancien.
            request.session.cycle_key()
        if request.path.startswith(("/admin/", "/account/")):
            add_never_cache_headers(response)
            # Préserver l'origine des formulaires pour la vérification CSRF.
            response["Referrer-Policy"] = "same-origin"
        return response
