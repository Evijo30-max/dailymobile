from django.shortcuts import render, redirect
from django.contrib import messages
from django.views import View
from django.utils import timezone
import uuid

from .models import Reparation, AppareilReparation


class DemandeReparationWebView(View):
    def get(self, request):
        return render(request, 'repairs/demande.html')

    def post(self, request):
        nom = request.POST.get('nom_client', '').strip()
        telephone = request.POST.get('telephone_client', '').strip()
        email = request.POST.get('email_client', '').strip() or None
        marque = request.POST.get('marque', '').strip()
        modele = request.POST.get('modele', '').strip()
        motif = request.POST.get('motif_depot', '').strip()
        etat = request.POST.get('etat_physique_entree', '').strip() or "Non précisé"
        type_prise = request.POST.get('type_prise_en_charge', 'DEPOT')

        if not all([nom, telephone, marque, modele, motif]):
            messages.error(request, "Veuillez remplir tous les champs obligatoires.")
            return render(request, 'repairs/demande.html')

        reference = f"REP-{timezone.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"

        reparation = Reparation.objects.create(
            id_utilisateur=request.user if request.user.is_authenticated else None,
            reference=reference,
            nom_client=nom,
            telephone_client=telephone,
            email_client=email,
            source_demande='SITE_WEB',
            type_prise_en_charge=type_prise,
            statut='RECUE',
        )

        AppareilReparation.objects.create(
            id_reparation=reparation,
            marque=marque,
            modele=modele,
            etat_physique_entree=etat,
            motif_depot=motif,
        )

        messages.success(
            request,
            f"Demande enregistrée. Référence : {reference}. "
            "Nous vous contacterons bientôt."
        )
        return redirect('web-catalogue')