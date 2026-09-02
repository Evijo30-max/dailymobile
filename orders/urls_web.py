from django.urls import path
from .views_web import (
    AjouterPanierWebView, PanierWebView, SupprimerLigneWebView,
    CheckoutWebView, MesCommandesWebView
)

urlpatterns = [
    path('panier/', PanierWebView.as_view(), name='web-panier'),
    path('panier/ajouter/', AjouterPanierWebView.as_view(), name='web-ajouter-panier'),
    path('panier/retirer/<int:id_ligne>/', SupprimerLigneWebView.as_view(), name='web-supprimer-ligne'),
    path('commander/', CheckoutWebView.as_view(), name='web-checkout'),
    path('mes-commandes/', MesCommandesWebView.as_view(), name='web-mes-commandes'),
]