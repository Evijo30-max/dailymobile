from django.urls import path
from .views import CatalogueListWebView, CatalogueDetailWebView

urlpatterns = [
    path('', CatalogueListWebView.as_view(), name='web-catalogue'),
    path('produit/<slug:slug>/', CatalogueDetailWebView.as_view(), name='web-produit-detail'),
]