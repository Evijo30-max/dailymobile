from django.shortcuts import render, get_object_or_404
from django.views import View
from rest_framework import generics
from rest_framework.permissions import AllowAny

from .models import Produit, Categorie, Marque
from .serializers import ProduitListSerializer, ProduitDetailSerializer


# =========================
# API
# =========================

class ProduitListView(generics.ListAPIView):
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


# =========================
# Pages web
# =========================

class CatalogueListWebView(View):
    def get(self, request):
        slug_cat = request.GET.get('categorie')
        marque_id = request.GET.get('marque')

        categories_principales = (
            Categorie.objects
            .filter(actif=True, id_categorie_parent__isnull=True)
            .order_by('nom')
        )

        categorie_active = None
        sous_categories = []
        marques = Marque.objects.filter(actif=True).order_by('nom')
        marque_active = None

        produits = (
            Produit.objects
            .filter(actif=True)
            .select_related('id_marque')
            .order_by('nom')
        )

        if slug_cat:
            categorie_active = get_object_or_404(
                Categorie, slug=slug_cat, actif=True
            )

            # Enfants directs
            sous_categories = list(
                Categorie.objects.filter(
                    actif=True,
                    id_categorie_parent=categorie_active,
                ).order_by('nom')
            )

            if categorie_active.id_categorie_parent_id:
                # On est sur une sous-catégorie → afficher les frères
                parent = categorie_active.id_categorie_parent
                sous_categories = list(
                    Categorie.objects.filter(
                        actif=True,
                        id_categorie_parent=parent,
                    ).order_by('nom')
                )
                produits = produits.filter(categories=categorie_active)

            elif sous_categories:
                # Catégorie parente avec enfants
                ids = [categorie_active.id_categorie] + [
                    c.id_categorie for c in sous_categories
                ]
                produits = produits.filter(
                    categories__id_categorie__in=ids
                ).distinct()

            else:
                produits = produits.filter(categories=categorie_active)

        if marque_id:
            marque_active = get_object_or_404(Marque, pk=marque_id, actif=True)
            produits = produits.filter(id_marque=marque_active)

        # ---------- Navigation (restrictions) ----------
        def get_root(cat):
            current = cat
            while current.id_categorie_parent_id:
                current = current.id_categorie_parent
            return current

        show_subnav_categories = bool(sous_categories)
        show_subnav_marques = False

        if categorie_active:
            root = get_root(categorie_active)
            root_slug = (root.slug or '').lower().strip()

            if root_slug in ('accessoires', 'accessoire'):
                # Types uniquement, pas de marques
                show_subnav_marques = False

            elif root_slug in ('ordinateurs', 'ordinateur'):
                # Parent Ordinateurs → Portable/Fixe seulement
                # Sous-cat Portable/Fixe → marques OK
                show_subnav_marques = bool(categorie_active.id_categorie_parent_id)

            else:
                # Téléphones et autres → marques
                show_subnav_marques = True

        return render(request, 'catalogue/liste.html', {
            'produits': produits,
            'categories_principales': categories_principales,
            'categorie_active': categorie_active,
            'sous_categories': sous_categories,
            'marques': marques,
            'marque_active': marque_active,
            'show_subnav_categories': show_subnav_categories,
            'show_subnav_marques': show_subnav_marques,
        })


class CatalogueDetailWebView(View):
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