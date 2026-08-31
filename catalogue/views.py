from django.shortcuts import render

# Create your views here.
from rest_framework import generics
from rest_framework.permissions import AllowAny
from .models import Produit
from .serializers import ProduitListSerializer, ProduitDetailSerializer


class ProduitListView(generics.ListAPIView):
    """
    GET /api/catalogue/produits/
    Liste des produits actifs.
    """
    permission_classes = [AllowAny]
    serializer_class = ProduitListSerializer

    def get_queryset(self):
        return (
            Produit.objects
            .filter(actif=True)
            .select_related('id_marque')
            .order_by('nom')
        )


class ProduitDetailView(generics.RetrieveAPIView):
    """
    GET /api/catalogue/produits/<slug>/
    Détail d'un produit avec ses variantes et offres.
    """
    permission_classes = [AllowAny]
    serializer_class = ProduitDetailSerializer
    lookup_field = 'slug'

    def get_queryset(self):
        return (
            Produit.objects
            .filter(actif=True)
            .select_related('id_marque')
            .prefetch_related(
                'categories',
                'variantes__offres',
                'variantes__caracteristiques__id_caracteristique',
            )
        )