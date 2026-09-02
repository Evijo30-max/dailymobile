from django.urls import path
from .views import (
    PanierView, AjouterAuPanierView,
    ModifierLignePanierView, SupprimerLignePanierView,
    CheckoutView, MesCommandesView,
)

urlpatterns = [
    path('panier/', PanierView.as_view(), name='panier'),
    path('panier/ajouter/', AjouterAuPanierView.as_view(), name='panier-ajouter'),
    path('panier/lignes/<int:id_ligne>/', ModifierLignePanierView.as_view(), name='panier-modifier-ligne'),
    path('panier/lignes/<int:id_ligne>/supprimer/', SupprimerLignePanierView.as_view(), name='panier-supprimer-ligne'),
    path('checkout/', CheckoutView.as_view(), name='checkout'),
    path('mes-commandes/', MesCommandesView.as_view(), name='mes-commandes'),
]