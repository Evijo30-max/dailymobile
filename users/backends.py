from django.contrib.auth.backends import BaseBackend
from django.db.models import Q
from .models import Utilisateur


class EmailOrTelephoneBackend(BaseBackend):
    """
    Backend d'authentification custom.
    Permet de se connecter avec email OU téléphone + mot de passe.
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        """
        `username` peut être un email ou un numéro de téléphone.
        """
        if username is None or password is None:
            return None

        username = username.strip()

        try:
            # Recherche insensible à la casse pour l'email
            utilisateur = Utilisateur.objects.get(
                Q(email__iexact=username) | Q(telephone=username)
            )
        except Utilisateur.DoesNotExist:
            return None
        except Utilisateur.MultipleObjectsReturned:
            # Cas anormal : on refuse par sécurité
            return None

        # Vérifie que le compte est actif
        if not utilisateur.actif:
            return None

        # Vérifie le mot de passe
        if utilisateur.check_password(password):
            return utilisateur

        return None

    def get_user(self, user_id):
        try:
            return Utilisateur.objects.get(pk=user_id)
        except Utilisateur.DoesNotExist:
            return None