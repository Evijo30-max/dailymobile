from django.contrib import admin
from .models import (
    Marque, Categorie, Produit, ProduitCategorie,
    Variante, Caracteristique, VarianteCaracteristique,
    EtatProduit, EmplacementStock, OffreProduit, UniteProduit
)


class VarianteInline(admin.TabularInline):
    model = Variante
    extra = 1
    fields = ('nom', 'sku', 'actif')
    show_change_link = True


class OffreInline(admin.TabularInline):
    model = OffreProduit
    extra = 1
    fields = ('type_offre', 'prix_vente', 'prix_compare', 'quantite_disponible', 'actif')
    show_change_link = True


class VarianteCaracteristiqueInline(admin.TabularInline):
    model = VarianteCaracteristique
    extra = 1
    autocomplete_fields = ['id_caracteristique']


@admin.register(Marque)
class MarqueAdmin(admin.ModelAdmin):
    list_display = ('nom', 'actif', 'date_creation')
    list_filter = ('actif',)
    search_fields = ('nom',)
    list_editable = ('actif',)


@admin.register(Categorie)
class CategorieAdmin(admin.ModelAdmin):
    list_display = ('nom', 'slug', 'actif')
    list_filter = ('actif',)
    search_fields = ('nom', 'slug')
    prepopulated_fields = {'slug': ('nom',)}
    list_editable = ('actif',)


class ProduitCategorieInline(admin.TabularInline):
    model = ProduitCategorie
    extra = 1
    autocomplete_fields = ['id_categorie']


@admin.register(Produit)
class ProduitAdmin(admin.ModelAdmin):
    list_display = ('nom', 'id_marque', 'slug', 'actif', 'date_creation')
    list_filter = ('actif', 'id_marque')
    search_fields = ('nom', 'slug')
    prepopulated_fields = {'slug': ('nom',)}
    list_editable = ('actif',)
    inlines = [ProduitCategorieInline, VarianteInline]
    autocomplete_fields = ['id_marque']

    fieldsets = (
        (None, {
            'fields': ('nom', 'id_marque', 'slug', 'description', 'actif')
        }),
        ('Image', {
            'fields': ('image_file', 'image_url'),
            'description': 'Uploadez un fichier OU collez une URL directe (jpg/png). Le fichier a la priorité.',
        }),
    )


@admin.register(Variante)
class VarianteAdmin(admin.ModelAdmin):
    list_display = ('nom', 'id_produit', 'sku', 'actif')
    list_filter = ('actif',)
    search_fields = ('nom', 'sku', 'id_produit__nom')
    list_editable = ('actif',)
    inlines = [OffreInline, VarianteCaracteristiqueInline]
    autocomplete_fields = ['id_produit']


@admin.register(Caracteristique)
class CaracteristiqueAdmin(admin.ModelAdmin):
    list_display = ('nom', 'unite', 'actif')
    search_fields = ('nom',)
    list_editable = ('actif',)


@admin.register(EtatProduit)
class EtatProduitAdmin(admin.ModelAdmin):
    list_display = ('code', 'nom', 'actif')
    search_fields = ('code', 'nom')          # ← ajouté
    list_editable = ('actif',)


@admin.register(EmplacementStock)
class EmplacementStockAdmin(admin.ModelAdmin):
    list_display = ('nom', 'actif')
    search_fields = ('nom',)                 # ← ajouté
    list_editable = ('actif',)


@admin.register(OffreProduit)
class OffreProduitAdmin(admin.ModelAdmin):
    list_display = ('id_offre', 'id_variante', 'type_offre', 'prix_vente', 'quantite_disponible', 'actif')
    list_filter = ('type_offre', 'actif')
    search_fields = ('id_variante__nom', 'id_variante__sku')
    list_editable = ('prix_vente', 'quantite_disponible', 'actif')
    autocomplete_fields = ['id_variante', 'id_unite_produit']


@admin.register(UniteProduit)
class UniteProduitAdmin(admin.ModelAdmin):
    list_display = ('id_unite_produit', 'id_variante', 'imei', 'numero_serie', 'statut', 'id_etat_produit')
    list_filter = ('statut', 'id_etat_produit')
    search_fields = ('imei', 'numero_serie')
    autocomplete_fields = ['id_variante', 'id_etat_produit', 'id_emplacement_stock']