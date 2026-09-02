from django.db import models
from django.contrib.auth.hashers import make_password, check_password
from django.utils.crypto import salted_hmac


class Utilisateur(models.Model):
    """
    Modèle correspondant à la table `utilisateur` du schéma SQL.
    Compatible avec le système de session Django.
    """

    class Role(models.TextChoices):
        CLIENT = 'CLIENT', 'Client'
        ADMIN = 'ADMIN', 'Administrateur'

    id_utilisateur = models.BigAutoField(primary_key=True)

    nom = models.CharField(max_length=100)
    prenom = models.CharField(max_length=100)

    email = models.EmailField(
        max_length=255,
        null=True,
        blank=True,
    )

    telephone = models.CharField(
        max_length=30,
        null=True,
        blank=True,
    )

    mot_de_passe_hash = models.CharField(max_length=255)

    role = models.CharField(
        max_length=30,
        choices=Role.choices,
        default=Role.CLIENT,
    )

    actif = models.BooleanField(default=True)

    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'utilisateur'
        managed = False
        verbose_name = 'Utilisateur'
        verbose_name_plural = 'Utilisateurs'
        ordering = ['-date_creation']

    def __str__(self):
        return f"{self.prenom} {self.nom} ({self.email or self.telephone})"

    # ------------------------------------------------------------------
    # Compatibilité avec le système d'authentification / session Django
    # ------------------------------------------------------------------

    @property
    def is_authenticated(self):
        return True

    @property
    def is_anonymous(self):
        return False

    @property
    def is_active(self):
        return self.actif

    def get_session_auth_hash(self):
        """
        Hash utilisé par Django pour invalider la session
        si le mot de passe change.
        """
        key_salt = "django.contrib.auth.models.AbstractBaseUser.get_session_auth_hash"
        return salted_hmac(
            key_salt,
            self.mot_de_passe_hash,
            algorithm="sha256",
        ).hexdigest()

    # ------------------------------------------------------------------
    # Gestion du mot de passe
    # ------------------------------------------------------------------

    def set_password(self, raw_password: str) -> None:
        self.mot_de_passe_hash = make_password(raw_password)

    def check_password(self, raw_password: str) -> bool:
        return check_password(raw_password, self.mot_de_passe_hash)

    @property
    def is_admin(self) -> bool:
        return self.role == self.Role.ADMIN and self.actif

    @property
    def is_client(self) -> bool:
        return self.role == self.Role.CLIENT and self.actif

    @property
    def is_staff(self):
        """Requis par Django admin. Seuls les ADMIN y ont accès."""
        return self.role == self.Role.ADMIN and self.actif

    @property
    def is_superuser(self):
        return self.role == self.Role.ADMIN and self.actif

    def has_perm(self, perm, obj=None):
        return self.is_admin

    def has_module_perms(self, app_label):
        return self.is_admin

    def get_username(self):
        """Utilisé par Django admin / auth."""
        return self.email or self.telephone or str(self.pk)