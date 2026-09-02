from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views import View
from django.db import transaction
from django.utils import timezone
from decimal import Decimal
import uuid


from catalogue.models import OffreProduit
from users.models import Utilisateur
from .models import (
    Panier, LignePanier, Commande, LigneCommande,
    AdresseCommande, Livraison, TarifLivraison
)


def client_required(view_method):
    def wrapper(self, request, *args, **kwargs):
        if not isinstance(request.user, Utilisateur):
            messages.info(request, "Veuillez vous connecter avec un compte client.")
            return redirect('web-login')
        return view_method(self, request, *args, **kwargs)
    return wrapper


def get_or_create_panier_actif(utilisateur):
    panier, _ = Panier.objects.get_or_create(
        id_utilisateur=utilisateur,
        statut='ACTIF',
        defaults={}
    )
    return panier


class AjouterPanierWebView(View):
    @client_required
    def post(self, request):
        id_offre = request.POST.get('id_offre')
        quantite = int(request.POST.get('quantite', 1))

        try:
            offre = OffreProduit.objects.get(pk=id_offre, actif=True)
        except OffreProduit.DoesNotExist:
            messages.error(request, "Offre introuvable.")
            return redirect('web-catalogue')

        if offre.type_offre == 'NEUF' and offre.quantite_disponible < quantite:
            messages.error(request, f"Stock insuffisant ({offre.quantite_disponible} disponible).")
            return redirect(request.META.get('HTTP_REFERER', '/'))

        panier = get_or_create_panier_actif(request.user)
        ligne, created = LignePanier.objects.get_or_create(
            id_panier=panier,
            id_offre=offre,
            defaults={'quantite': quantite, 'prix_unitaire': offre.prix_vente}
        )
        if not created:
            ligne.quantite += quantite
            ligne.save()

        messages.success(request, "Produit ajouté au panier.")
        return redirect('web-panier')


class PanierWebView(View):
    @client_required
    def get(self, request):
        panier = get_or_create_panier_actif(request.user)
        lignes = panier.lignes.select_related('id_offre__id_variante__id_produit').all()
        total = sum((l.quantite * l.prix_unitaire for l in lignes), Decimal('0.00'))
        return render(request, 'orders/panier.html', {
            'panier': panier,
            'lignes': lignes,
            'total': total,
        })


class SupprimerLigneWebView(View):
    @client_required
    def post(self, request, id_ligne):
        try:
            ligne = LignePanier.objects.get(
                pk=id_ligne,
                id_panier__id_utilisateur=request.user,
                id_panier__statut='ACTIF'
            )
            ligne.delete()
            messages.success(request, "Article retiré.")
        except LignePanier.DoesNotExist:
            messages.error(request, "Ligne introuvable.")
        return redirect('web-panier')


class CheckoutWebView(View):
    @client_required
    def get(self, request):
        panier = get_or_create_panier_actif(request.user)
        lignes = list(panier.lignes.all())
        if not lignes:
            messages.error(request, "Votre panier est vide.")
            return redirect('web-panier')
        total = sum((l.quantite * l.prix_unitaire for l in lignes), Decimal('0.00'))
        return render(request, 'orders/checkout.html', {
            'lignes': lignes,
            'total': total,
        })

    @client_required
    @transaction.atomic
    def post(self, request):
        panier = get_or_create_panier_actif(request.user)
        lignes = list(panier.lignes.select_related('id_offre__id_variante__id_produit').all())
        if not lignes:
            messages.error(request, "Panier vide.")
            return redirect('web-panier')

        mode = request.POST.get('mode_reception', 'RETRAIT_BOUTIQUE')
        sous_total = sum((l.quantite * l.prix_unitaire for l in lignes), Decimal('0.00'))
        frais_livraison = Decimal('0.00')

        if mode == 'LIVRAISON':
            ville_nom = request.POST.get('ville_nom', '').strip()
            tarif = TarifLivraison.objects.filter(
                id_ville__nom__iexact=ville_nom, actif=True
            ).order_by('-date_debut').first()
            frais_livraison = tarif.montant if tarif else Decimal('3000.00')

            required = ['nom_destinataire', 'telephone', 'ville_nom', 'quartier', 'adresse_detail']
            for f in required:
                if not request.POST.get(f, '').strip():
                    messages.error(request, "Tous les champs de livraison sont obligatoires.")
                    return redirect('web-checkout')

        total = sous_total + frais_livraison
        reference = f"CMD-{timezone.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"

        commande = Commande.objects.create(
            id_utilisateur=request.user,
            reference=reference,
            sous_total=sous_total,
            remise=Decimal('0.00'),
            frais_livraison=frais_livraison,
            total=total,
            mode_reception=mode,
            statut='EN_ATTENTE_PAIEMENT',
        )

        for ligne in lignes:
            offre = ligne.id_offre
            LigneCommande.objects.create(
                id_commande=commande,
                id_offre=offre,
                nom_produit=offre.id_variante.id_produit.nom,
                nom_variante=offre.id_variante.nom,
                type_offre=offre.type_offre,
                prix_unitaire=ligne.prix_unitaire,
                quantite=ligne.quantite,
                remise=Decimal('0.00'),
                total=ligne.quantite * ligne.prix_unitaire,
            )

        if mode == 'LIVRAISON':
            AdresseCommande.objects.create(
                id_commande=commande,
                nom_destinataire=request.POST.get('nom_destinataire'),
                telephone=request.POST.get('telephone'),
                ville_nom=request.POST.get('ville_nom'),
                quartier=request.POST.get('quartier'),
                adresse_detail=request.POST.get('adresse_detail'),
                point_repere=request.POST.get('point_repere') or None,
                instructions=request.POST.get('instructions') or None,
            )
            Livraison.objects.create(
                id_commande=commande,
                frais=frais_livraison,
                statut='EN_ATTENTE',
            )

        panier.statut = 'CONVERTI'
        panier.save()

        messages.success(request, f"Commande {reference} créée avec succès.")
        return redirect('web-mes-commandes')


class MesCommandesWebView(View):
    @client_required
    def get(self, request):
        commandes = Commande.objects.filter(
            id_utilisateur=request.user
        ).order_by('-date_creation')
        return render(request, 'orders/mes_commandes.html', {
            'commandes': commandes,
        })