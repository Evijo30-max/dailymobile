from django.contrib import admin
from .models import Utilisateur


@admin.register(Utilisateur)
class UtilisateurAdmin(admin.ModelAdmin):
    list_display = ('id_utilisateur', 'nom', 'prenom', 'email', 'telephone', 'role', 'actif', 'date_creation')
    list_filter = ('role', 'actif')
    search_fields = ('nom', 'prenom', 'email', 'telephone')
    readonly_fields = ('date_creation', 'date_modification')