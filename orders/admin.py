from django.contrib import admin
from .models import (
    Ville, Adresse, Panier, LignePanier,
    Commande, LigneCommande, AdresseCommande,
    TarifLivraison, Livraison,
    MoyenPaiement, Paiement
)


class LigneCommandeInline(admin.TabularInline):
    model = LigneCommande
    extra = 0
    readonly_fields = ('nom_produit', 'nom_variante', 'type_offre', 'prix_unitaire', 'quantite', 'remise', 'total')
    can_delete = False


class AdresseCommandeInline(admin.StackedInline):
    model = AdresseCommande
    extra = 0
    max_num = 1


class LivraisonInline(admin.StackedInline):
    model = Livraison
    extra = 0
    max_num = 1


@admin.register(Ville)
class VilleAdmin(admin.ModelAdmin):
    list_display = ('nom', 'code', 'actif')
    list_editable = ('actif',)
    search_fields = ('nom', 'code')


@admin.register(Commande)
class CommandeAdmin(admin.ModelAdmin):
    list_display = (
        'reference', 'id_utilisateur', 'total',
        'mode_reception', 'statut', 'date_creation'
    )
    list_filter = ('statut', 'mode_reception', 'date_creation')
    search_fields = (
        'reference',
        'id_utilisateur__nom',
        'id_utilisateur__prenom',
        'id_utilisateur__telephone',
        'id_utilisateur__email',
    )
    readonly_fields = (
        'reference', 'sous_total', 'remise',
        'frais_livraison', 'total',
        'date_creation', 'date_modification'
    )
    list_editable = ('statut',)  # le gérant change le statut directement dans la liste
    inlines = [LigneCommandeInline, AdresseCommandeInline, LivraisonInline]
    list_per_page = 25
    actions = [
        'marquer_payee',
        'marquer_en_preparation',
        'marquer_prete',
        'marquer_retirer_ou_livree',
    ]

    fieldsets = (
        ('Informations générales', {
            'fields': ('reference', 'id_utilisateur', 'mode_reception', 'statut')
        }),
        ('Montants', {
            'fields': ('sous_total', 'remise', 'frais_livraison', 'total')
        }),
        ('Dates', {
            'fields': ('date_creation', 'date_modification')
        }),
    )

    @admin.action(description="Marquer comme PAYÉE")
    def marquer_payee(self, request, queryset):
        updated = queryset.update(statut='PAYEE')
        self.message_user(request, f"{updated} commande(s) marquée(s) comme payée(s).")

    @admin.action(description="Marquer EN PRÉPARATION")
    def marquer_en_preparation(self, request, queryset):
        updated = queryset.update(statut='EN_PREPARATION')
        self.message_user(request, f"{updated} commande(s) en préparation.")

    @admin.action(description="Marquer PRÊTE")
    def marquer_prete(self, request, queryset):
        updated = queryset.update(statut='PRETE')
        self.message_user(request, f"{updated} commande(s) prête(s).")

    @admin.action(description="Marquer RETIRÉE / LIVRÉE")
    def marquer_retirer_ou_livree(self, request, queryset):
        for cmd in queryset:
            if cmd.mode_reception == 'RETRAIT_BOUTIQUE':
                cmd.statut = 'RETIREE'
            else:
                cmd.statut = 'LIVREE'
            cmd.save(update_fields=['statut'])
        self.message_user(request, f"{queryset.count()} commande(s) finalisée(s).")


@admin.register(MoyenPaiement)
class MoyenPaiementAdmin(admin.ModelAdmin):
    list_display = ('nom', 'code', 'actif')
    list_editable = ('actif',)
    search_fields = ('nom', 'code')


@admin.register(Paiement)
class PaiementAdmin(admin.ModelAdmin):
    list_display = ('reference_interne', 'montant', 'statut', 'contexte', 'date_creation')
    list_filter = ('statut', 'contexte', 'type_paiement')
    search_fields = ('reference_interne', 'reference_externe')
    readonly_fields = ('date_creation', 'date_confirmation')


@admin.register(TarifLivraison)
class TarifLivraisonAdmin(admin.ModelAdmin):
    list_display = ('id_ville', 'montant', 'date_debut', 'date_fin', 'actif')
    list_filter = ('actif', 'id_ville')
    list_editable = ('montant', 'actif')


@admin.register(Panier)
class PanierAdmin(admin.ModelAdmin):
    list_display = ('id_panier', 'id_utilisateur', 'statut', 'date_creation')
    list_filter = ('statut',)
    search_fields = ('id_utilisateur__nom', 'id_utilisateur__telephone')


@admin.register(Livraison)
class LivraisonAdmin(admin.ModelAdmin):
    list_display = ('id_commande', 'statut', 'frais', 'date_creation', 'date_livraison')
    list_filter = ('statut',)
    search_fields = ('id_commande__reference',)