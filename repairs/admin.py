from django.contrib import admin
from .models import (
    Reparation, AppareilReparation, Diagnostic,
    Devis, LigneDevis, PieceUtilisee, TestReparation,
    AdresseCollecteReparation, CollecteReparation, TarifCollecteReparation
)


class AppareilInline(admin.StackedInline):
    model = AppareilReparation
    extra = 0
    max_num = 1


class DiagnosticInline(admin.StackedInline):
    model = Diagnostic
    extra = 0


class DevisInline(admin.TabularInline):
    model = Devis
    extra = 0
    show_change_link = True
    fields = ('reference', 'total', 'statut', 'date_creation')
    readonly_fields = ('reference', 'total', 'date_creation')


class CollecteInline(admin.StackedInline):
    model = CollecteReparation
    extra = 0
    max_num = 1


@admin.register(Reparation)
class ReparationAdmin(admin.ModelAdmin):
    list_display = (
        'reference', 'nom_client', 'telephone_client',
        'type_prise_en_charge', 'statut', 'date_reception'
    )
    list_filter = ('statut', 'type_prise_en_charge', 'source_demande')
    search_fields = ('reference', 'nom_client', 'telephone_client', 'email_client')
    list_editable = ('statut',)
    inlines = [AppareilInline, DiagnosticInline, DevisInline, CollecteInline]
    list_per_page = 25

    fieldsets = (
        ('Client', {
            'fields': ('nom_client', 'telephone_client', 'email_client', 'id_utilisateur')
        }),
        ('Dossier', {
            'fields': ('reference', 'source_demande', 'type_prise_en_charge', 'statut', 'commentaire')
        }),
        ('Dates', {
            'fields': ('date_reception', 'date_cloture')
        }),
    )


@admin.register(Devis)
class DevisAdmin(admin.ModelAdmin):
    list_display = ('reference', 'id_reparation', 'total', 'statut', 'date_creation')
    list_filter = ('statut',)
    search_fields = ('reference', 'id_reparation__reference', 'id_reparation__nom_client')
    list_editable = ('statut',)


@admin.register(CollecteReparation)
class CollecteReparationAdmin(admin.ModelAdmin):
    list_display = ('id_reparation', 'statut', 'frais', 'date_demande')
    list_filter = ('statut',)
    list_editable = ('statut',)


@admin.register(TarifCollecteReparation)
class TarifCollecteReparationAdmin(admin.ModelAdmin):
    list_display = ('id_ville', 'montant', 'actif')
    list_editable = ('montant', 'actif')


@admin.register(Diagnostic)
class DiagnosticAdmin(admin.ModelAdmin):
    list_display = ('id_reparation', 'date_diagnostic', 'cout_estime')
    search_fields = ('id_reparation__reference',)