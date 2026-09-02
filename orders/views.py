from django.shortcuts import render

# Create your views here.
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from django.db import transaction
from django.utils import timezone
from decimal import Decimal
import uuid

from catalogue.models import OffreProduit
from .models import (
    Panier, LignePanier, Commande, LigneCommande,
    AdresseCommande, Livraison, TarifLivraison
)
from .serializers import (
    PanierSerializer, AjouterAuPanierSerializer,
    ModifierLignePanierSerializer, CheckoutSerializer
)

from rest_framework import generics
from .serializers import CommandeListSerializer
from .models import Commande

def get_or_create_panier_actif(utilisateur):
    """Retourne le panier ACTIF de l'utilisateur (en crée un s'il n'existe pas)."""
    panier, _ = Panier.objects.get_or_create(
        id_utilisateur=utilisateur,
        statut='ACTIF',
        defaults={}
    )
    return panier


@method_decorator(csrf_exempt, name='dispatch')
class PanierView(APIView):
    """
    GET /api/orders/panier/
    Voir mon panier.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        panier = get_or_create_panier_actif(request.user)
        serializer = PanierSerializer(panier)
        return Response(serializer.data)


@method_decorator(csrf_exempt, name='dispatch')
class AjouterAuPanierView(APIView):
    """
    POST /api/orders/panier/ajouter/
    Body: { "id_offre": 1, "quantite": 1 }
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = AjouterAuPanierSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        offre = OffreProduit.objects.get(pk=serializer.validated_data['id_offre'])
        quantite = serializer.validated_data['quantite']

        # Contrôle stock simple
        if offre.type_offre == 'NEUF' and offre.quantite_disponible < quantite:
            return Response(
                {"detail": f"Stock insuffisant. Disponible : {offre.quantite_disponible}"},
                status=status.HTTP_400_BAD_REQUEST
            )

        panier = get_or_create_panier_actif(request.user)

        ligne, created = LignePanier.objects.get_or_create(
            id_panier=panier,
            id_offre=offre,
            defaults={
                'quantite': quantite,
                'prix_unitaire': offre.prix_vente,
            }
        )

        if not created:
            nouvelle_qte = ligne.quantite + quantite
            if offre.type_offre == 'NEUF' and offre.quantite_disponible < nouvelle_qte:
                return Response(
                    {"detail": f"Stock insuffisant. Disponible : {offre.quantite_disponible}"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            ligne.quantite = nouvelle_qte
            ligne.save()

        return Response(
            {
                "message": "Produit ajouté au panier.",
                "panier": PanierSerializer(panier).data
            },
            status=status.HTTP_200_OK
        )


@method_decorator(csrf_exempt, name='dispatch')
class ModifierLignePanierView(APIView):
    """
    PATCH /api/orders/panier/lignes/<id_ligne>/
    Body: { "quantite": 2 }
    """
    permission_classes = [IsAuthenticated]

    def patch(self, request, id_ligne):
        serializer = ModifierLignePanierSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            ligne = LignePanier.objects.select_related('id_panier', 'id_offre').get(
                pk=id_ligne,
                id_panier__id_utilisateur=request.user,
                id_panier__statut='ACTIF'
            )
        except LignePanier.DoesNotExist:
            return Response({"detail": "Ligne introuvable."}, status=status.HTTP_404_NOT_FOUND)

        quantite = serializer.validated_data['quantite']
        offre = ligne.id_offre

        if offre.type_offre == 'NEUF' and offre.quantite_disponible < quantite:
            return Response(
                {"detail": f"Stock insuffisant. Disponible : {offre.quantite_disponible}"},
                status=status.HTTP_400_BAD_REQUEST
            )

        ligne.quantite = quantite
        ligne.save()

        return Response({
            "message": "Quantité mise à jour.",
            "panier": PanierSerializer(ligne.id_panier).data
        })


@method_decorator(csrf_exempt, name='dispatch')
class SupprimerLignePanierView(APIView):
    """
    DELETE /api/orders/panier/lignes/<id_ligne>/
    """
    permission_classes = [IsAuthenticated]

    def delete(self, request, id_ligne):
        try:
            ligne = LignePanier.objects.select_related('id_panier').get(
                pk=id_ligne,
                id_panier__id_utilisateur=request.user,
                id_panier__statut='ACTIF'
            )
        except LignePanier.DoesNotExist:
            return Response({"detail": "Ligne introuvable."}, status=status.HTTP_404_NOT_FOUND)

        panier = ligne.id_panier
        ligne.delete()

        return Response({
            "message": "Article retiré du panier.",
            "panier": PanierSerializer(panier).data
        })


@method_decorator(csrf_exempt, name='dispatch')
class CheckoutView(APIView):
    """
    POST /api/orders/checkout/
    Transforme le panier actif en commande.
    """
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        serializer = CheckoutSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        utilisateur = request.user

        try:
            panier = Panier.objects.prefetch_related('lignes__id_offre').get(
                id_utilisateur=utilisateur,
                statut='ACTIF'
            )
        except Panier.DoesNotExist:
            return Response({"detail": "Aucun panier actif."}, status=status.HTTP_400_BAD_REQUEST)

        lignes = list(panier.lignes.all())
        if not lignes:
            return Response({"detail": "Le panier est vide."}, status=status.HTTP_400_BAD_REQUEST)

        # Calcul des montants (côté serveur uniquement)
        sous_total = sum((l.quantite * l.prix_unitaire for l in lignes), Decimal('0.00'))
        remise = Decimal('0.00')
        frais_livraison = Decimal('0.00')

        if data['mode_reception'] == 'LIVRAISON':
            # Recherche d'un tarif actif pour la ville (approximation simple par nom)
            tarif = (
                TarifLivraison.objects
                .filter(id_ville__nom__iexact=data['ville_nom'], actif=True)
                .order_by('-date_debut')
                .first()
            )
            if tarif:
                frais_livraison = tarif.montant
            else:
                # Tarif par défaut si la ville n'a pas encore de tarif
                frais_livraison = Decimal('3000.00')

        total = sous_total - remise + frais_livraison

        # Création de la commande
        reference = f"CMD-{timezone.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"

        commande = Commande.objects.create(
            id_utilisateur=utilisateur,
            reference=reference,
            sous_total=sous_total,
            remise=remise,
            frais_livraison=frais_livraison,
            total=total,
            mode_reception=data['mode_reception'],
            statut='EN_ATTENTE_PAIEMENT',
        )

        # Lignes de commande (snapshot)
        for ligne in lignes:
            offre = ligne.id_offre
            LigneCommande.objects.create(
                id_commande=commande,
                id_offre=offre,
                nom_produit=str(offre.id_variante.id_produit.nom),
                nom_variante=offre.id_variante.nom,
                type_offre=offre.type_offre,
                prix_unitaire=ligne.prix_unitaire,
                quantite=ligne.quantite,
                remise=Decimal('0.00'),
                total=ligne.quantite * ligne.prix_unitaire,
            )

        # Adresse + livraison si nécessaire
        if data['mode_reception'] == 'LIVRAISON':
            AdresseCommande.objects.create(
                id_commande=commande,
                nom_destinataire=data['nom_destinataire'],
                telephone=data['telephone'],
                ville_nom=data['ville_nom'],
                quartier=data['quartier'],
                adresse_detail=data['adresse_detail'],
                point_repere=data.get('point_repere') or None,
                instructions=data.get('instructions') or None,
            )
            Livraison.objects.create(
                id_commande=commande,
                frais=frais_livraison,
                statut='EN_ATTENTE',
            )

        # Marquer le panier comme converti
        panier.statut = 'CONVERTI'
        panier.save()

        return Response(
            {
                "message": "Commande créée avec succès.",
                "reference": commande.reference,
                "total": str(commande.total),
                "mode_reception": commande.mode_reception,
                "statut": commande.statut,
            },
            status=status.HTTP_201_CREATED
        )


class MesCommandesView(generics.ListAPIView):
    """
    GET /api/orders/mes-commandes/
    Liste des commandes de l'utilisateur connecté.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = CommandeListSerializer

    def get_queryset(self):
        return (
            Commande.objects
            .filter(id_utilisateur=self.request.user)
            .order_by('-date_creation')
        )