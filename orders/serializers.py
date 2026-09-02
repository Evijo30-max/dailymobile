from rest_framework import serializers
from django.db import transaction
from decimal import Decimal

from catalogue.models import OffreProduit
from .models import (
    Panier, LignePanier, Commande, LigneCommande,
    AdresseCommande, Livraison, TarifLivraison, Ville
)


class LignePanierSerializer(serializers.ModelSerializer):
    offre_nom = serializers.SerializerMethodField()
    prix_total = serializers.SerializerMethodField()

    class Meta:
        model = LignePanier
        fields = (
            'id_ligne_panier',
            'id_offre',
            'offre_nom',
            'quantite',
            'prix_unitaire',
            'prix_total',
        )
        read_only_fields = ('prix_unitaire',)

    def get_offre_nom(self, obj):
        try:
            return str(obj.id_offre)
        except Exception:
            return None

    def get_prix_total(self, obj):
        return obj.quantite * obj.prix_unitaire


class PanierSerializer(serializers.ModelSerializer):
    lignes = LignePanierSerializer(many=True, read_only=True)
    total = serializers.SerializerMethodField()

    class Meta:
        model = Panier
        fields = ('id_panier', 'statut', 'lignes', 'total', 'date_modification')

    def get_total(self, obj):
        return sum(
            (ligne.quantite * ligne.prix_unitaire for ligne in obj.lignes.all()),
            Decimal('0.00')
        )


class AjouterAuPanierSerializer(serializers.Serializer):
    id_offre = serializers.IntegerField()
    quantite = serializers.IntegerField(min_value=1, default=1)

    def validate_id_offre(self, value):
        try:
            offre = OffreProduit.objects.get(pk=value, actif=True)
        except OffreProduit.DoesNotExist:
            raise serializers.ValidationError("Offre introuvable ou inactive.")
        return value


class ModifierLignePanierSerializer(serializers.Serializer):
    quantite = serializers.IntegerField(min_value=1)


class CheckoutSerializer(serializers.Serializer):
    """
    Passage de commande.
    """
    mode_reception = serializers.ChoiceField(choices=['LIVRAISON', 'RETRAIT_BOUTIQUE'])

    # Obligatoire uniquement si LIVRAISON
    nom_destinataire = serializers.CharField(required=False, allow_blank=True)
    telephone = serializers.CharField(required=False, allow_blank=True)
    ville_nom = serializers.CharField(required=False, allow_blank=True)
    quartier = serializers.CharField(required=False, allow_blank=True)
    adresse_detail = serializers.CharField(required=False, allow_blank=True)
    point_repere = serializers.CharField(required=False, allow_blank=True)
    instructions = serializers.CharField(required=False, allow_blank=True)

    def validate(self, data):
        if data['mode_reception'] == 'LIVRAISON':
            required = ['nom_destinataire', 'telephone', 'ville_nom', 'quartier', 'adresse_detail']
            for field in required:
                if not data.get(field):
                    raise serializers.ValidationError({
                        field: "Ce champ est obligatoire pour une livraison."
                    })
        return data


class CommandeListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Commande
        fields = (
            'id_commande',
            'reference',
            'total',
            'mode_reception',
            'statut',
            'date_creation',
        )


        