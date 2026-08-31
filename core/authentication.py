from rest_framework.authentication import SessionAuthentication


class CsrfExemptSessionAuthentication(SessionAuthentication):
    """
    SessionAuthentication sans vérification CSRF.
    Utile pour les tests API et les clients qui n'envoient pas de token CSRF.
    """
    def enforce_csrf(self, request):
        return  # on ne fait rien → pas de contrôle CSRF