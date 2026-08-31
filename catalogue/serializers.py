from rest_framework import serializers
from .models import (
    Marque, Categorie, Produit, Variante,
    OffreProduit, VarianteCaracteristique, Caracteristique
)


class MarqueSerializer(serializers.ModelSerializer):
    class Meta:
        model = Marque
        fields = ('id_marque', 'nom')


class CategorieSerializer(serializers.ModelSerializer):
    class Meta:
        model = Categorie
        fields = ('id_categorie', 'nom', 'slug')


class CaracteristiqueSerializer(serializers.ModelSerializer):
    class Meta:
        model = Caracteristique
        fields = ('id_caracteristique', 'nom', 'unite')


class VarianteCaracteristiqueSerializer(serializers.ModelSerializer):
    caracteristique = CaracteristiqueSerializer(source='id_caracteristique', read_only=True)

    class Meta:
        model = VarianteCaracteristique
        fields = ('caracteristique', 'valeur')


class OffreSerializer(serializers.ModelSerializer):
    class Meta:
        model = OffreProduit
        fields = (
            'id_offre',
            'type_offre',
            'prix_vente',
            'prix_compare',
            'quantite_disponible',
            'actif',
        )


class VarianteSerializer(serializers.ModelSerializer):
    offres = OffreSerializer(many=True, read_only=True)
    caracteristiques = VarianteCaracteristiqueSerializer(many=True, read_only=True)

    class Meta:
        model = Variante
        fields = (
            'id_variante',
            'nom',
            'sku',
            'description',
            'actif',
            'caracteristiques',
            'offres',
        )


class ProduitListSerializer(serializers.ModelSerializer):
    """Serializer léger pour la liste des produits."""
    marque = MarqueSerializer(source='id_marque', read_only=True)

    class Meta:
        model = Produit
        fields = (
            'id_produit',
            'nom',
            'slug',
            'description',
            'marque',
            'actif',
        )


class ProduitDetailSerializer(serializers.ModelSerializer):
    """Serializer complet pour le détail d'un produit."""
    marque = MarqueSerializer(source='id_marque', read_only=True)
    categories = CategorieSerializer(many=True, read_only=True)
    variantes = VarianteSerializer(many=True, read_only=True)

    class Meta:
        model = Produit
        fields = (
            'id_produit',
            'nom',
            'slug',
            'description',
            'marque',
            'categories',
            'variantes',
            'actif',
            'date_creation',
        )