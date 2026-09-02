

from django.shortcuts import render, get_object_or_404
from django.views import View
from .models import Produit

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


class CatalogueListWebView(View):
    """Page publique : liste des produits."""

    def get(self, request):
        produits = (
            Produit.objects
            .filter(actif=True)
            .select_related('id_marque')
            .order_by('nom')
        )
        return render(request, 'catalogue/liste.html', {
            'produits': produits,
        })


class CatalogueDetailWebView(View):
    """Page publique : détail d'un produit."""

    def get(self, request, slug):
        produit = get_object_or_404(
            Produit.objects
            .filter(actif=True)
            .select_related('id_marque')
            .prefetch_related('variantes__offres'),
            slug=slug
        )
        return render(request, 'catalogue/detail.html', {
            'produit': produit,
        })
        