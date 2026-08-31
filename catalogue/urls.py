from django.urls import path
from .views import ProduitListView, ProduitDetailView

urlpatterns = [
    path('produits/', ProduitListView.as_view(), name='produit-list'),
    path('produits/<slug:slug>/', ProduitDetailView.as_view(), name='produit-detail'),
]