from django.db import models
from users.models import Utilisateur
from orders.models import Ville


class Reparation(models.Model):
    """
    Dossier de réparation.
    Agrégat principal : appareil + diagnostic + devis + pièces + tests + collecte.
    """
    class SourceDemande(models.TextChoices):
        BOUTIQUE = 'BOUTIQUE', 'Boutique'
        SITE_WEB = 'SITE_WEB', 'Site web'
        TELEPHONE = 'TELEPHONE', 'Téléphone'
        AUTRE = 'AUTRE', 'Autre'

    class TypePriseEnCharge(models.TextChoices):
        DEPOT = 'DEPOT', 'Dépôt en boutique'
        COLLECTE = 'COLLECTE', 'Collecte à domicile'

    class Statut(models.TextChoices):
        RECUE = 'RECUE', 'Reçue'
        DIAGNOSTIC = 'DIAGNOSTIC', 'Diagnostic'
        DEVIS_EN_ATTENTE = 'DEVIS_EN_ATTENTE', 'Devis en attente'
        DEVIS_ENVOYE = 'DEVIS_ENVOYE', 'Devis envoyé'
        DEVIS_ACCEPTE = 'DEVIS_ACCEPTE', 'Devis accepté'
        DEVIS_REFUSE = 'DEVIS_REFUSE', 'Devis refusé'
        EN_REPARATION = 'EN_REPARATION', 'En réparation'
        TEST = 'TEST', 'Test'
        PRETE = 'PRETE', 'Prête'
        EN_ATTENTE_RESTITUTION = 'EN_ATTENTE_RESTITUTION', 'En attente de restitution'
        RESTITUEE = 'RESTITUEE', 'Restituée'
        ANNULEE = 'ANNULEE', 'Annulée'

    id_reparation = models.BigAutoField(primary_key=True)
    id_utilisateur = models.ForeignKey(
        Utilisateur,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_column='id_utilisateur',
        related_name='reparations',
    )
    reference = models.CharField(max_length=50, unique=True)
    nom_client = models.CharField(max_length=200)
    telephone_client = models.CharField(max_length=30)
    email_client = models.EmailField(max_length=255, null=True, blank=True)
    source_demande = models.CharField(
        max_length=30,
        choices=SourceDemande.choices,
        default=SourceDemande.BOUTIQUE,
    )
    type_prise_en_charge = models.CharField(
        max_length=30,
        choices=TypePriseEnCharge.choices,
        default=TypePriseEnCharge.DEPOT,
    )
    statut = models.CharField(
        max_length=40,
        choices=Statut.choices,
        default=Statut.RECUE,
    )
    date_reception = models.DateTimeField(auto_now_add=True)
    date_cloture = models.DateTimeField(null=True, blank=True)
    commentaire = models.TextField(null=True, blank=True)

    class Meta:
        db_table = 'reparation'
        managed = False
        verbose_name = 'Réparation'
        verbose_name_plural = 'Réparations'
        ordering = ['-date_reception']

    def __str__(self):
        return f"{self.reference} – {self.nom_client}"


class AppareilReparation(models.Model):
    """Informations de l'appareil déposé pour réparation."""
    id_appareil_reparation = models.BigAutoField(primary_key=True)
    id_reparation = models.OneToOneField(
        Reparation,
        on_delete=models.CASCADE,
        db_column='id_reparation',
        related_name='appareil',
    )
    marque = models.CharField(max_length=100)
    modele = models.CharField(max_length=150)
    imei = models.CharField(max_length=50, null=True, blank=True)
    numero_serie = models.CharField(max_length=100, null=True, blank=True)
    couleur = models.CharField(max_length=50, null=True, blank=True)
    etat_physique_entree = models.TextField()
    accessoires_deposes = models.TextField(null=True, blank=True)
    motif_depot = models.TextField()
    code_verrouillage = models.CharField(max_length=255, null=True, blank=True)
    date_creation = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'appareil_reparation'
        managed = False
        verbose_name = 'Appareil en réparation'
        verbose_name_plural = 'Appareils en réparation'

    def __str__(self):
        return f"{self.marque} {self.modele}"


class Diagnostic(models.Model):
    """Diagnostic technique réalisé sur un appareil."""
    id_diagnostic = models.BigAutoField(primary_key=True)
    id_reparation = models.ForeignKey(
        Reparation,
        on_delete=models.CASCADE,
        db_column='id_reparation',
        related_name='diagnostics',
    )
    id_technicien = models.ForeignKey(
        Utilisateur,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_column='id_technicien',
    )
    description_probleme = models.TextField()
    constat = models.TextField()
    recommandation = models.TextField(null=True, blank=True)
    cout_estime = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    date_diagnostic = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'diagnostic'
        managed = False
        verbose_name = 'Diagnostic'
        verbose_name_plural = 'Diagnostics'

    def __str__(self):
        return f"Diagnostic {self.id_reparation.reference}"


class Devis(models.Model):
    """
    Devis de réparation.
    total = sous_total + frais_collecte - remise (contrôlé en SQL).
    """
    class Statut(models.TextChoices):
        BROUILLON = 'BROUILLON', 'Brouillon'
        ENVOYE = 'ENVOYE', 'Envoyé'
        ACCEPTE = 'ACCEPTE', 'Accepté'
        REFUSE = 'REFUSE', 'Refusé'
        EXPIRE = 'EXPIRE', 'Expiré'
        ANNULE = 'ANNULE', 'Annulé'

    id_devis = models.BigAutoField(primary_key=True)
    id_reparation = models.ForeignKey(
        Reparation,
        on_delete=models.CASCADE,
        db_column='id_reparation',
        related_name='devis',
    )
    reference = models.CharField(max_length=50, unique=True)
    sous_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    frais_collecte = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    remise = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    statut = models.CharField(
        max_length=30,
        choices=Statut.choices,
        default=Statut.BROUILLON,
    )
    date_creation = models.DateTimeField(auto_now_add=True)
    date_envoi = models.DateTimeField(null=True, blank=True)
    date_acceptation = models.DateTimeField(null=True, blank=True)
    date_expiration = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'devis'
        managed = False
        verbose_name = 'Devis'
        verbose_name_plural = 'Devis'
        ordering = ['-date_creation']

    def __str__(self):
        return f"{self.reference} – {self.total} FCFA"


class LigneDevis(models.Model):
    """Ligne détaillée d'un devis (main d'œuvre, pièce, service…)."""
    class TypeLigne(models.TextChoices):
        MAIN_D_OEUVRE = 'MAIN_D_OEUVRE', "Main d'œuvre"
        PIECE = 'PIECE', 'Pièce'
        SERVICE = 'SERVICE', 'Service'
        AUTRE = 'AUTRE', 'Autre'

    id_ligne_devis = models.BigAutoField(primary_key=True)
    id_devis = models.ForeignKey(
        Devis,
        on_delete=models.CASCADE,
        db_column='id_devis',
        related_name='lignes',
    )
    designation = models.CharField(max_length=255)
    type_ligne = models.CharField(max_length=30, choices=TypeLigne.choices)
    quantite = models.PositiveIntegerField(default=1)
    prix_unitaire = models.DecimalField(max_digits=12, decimal_places=2)
    remise = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        db_table = 'ligne_devis'
        managed = False
        verbose_name = 'Ligne de devis'
        verbose_name_plural = 'Lignes de devis'

    def __str__(self):
        return f"{self.designation} x {self.quantite}"


class PieceUtilisee(models.Model):
    """Pièces réellement utilisées pendant la réparation."""
    id_piece_utilisee = models.BigAutoField(primary_key=True)
    id_reparation = models.ForeignKey(
        Reparation,
        on_delete=models.CASCADE,
        db_column='id_reparation',
        related_name='pieces',
    )
    designation = models.CharField(max_length=255)
    reference_piece = models.CharField(max_length=100, null=True, blank=True)
    quantite = models.PositiveIntegerField(default=1)
    cout_unitaire = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    observation = models.TextField(null=True, blank=True)
    date_utilisation = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'piece_utilisee'
        managed = False
        verbose_name = 'Pièce utilisée'
        verbose_name_plural = 'Pièces utilisées'

    def __str__(self):
        return f"{self.designation} x {self.quantite}"


class TestReparation(models.Model):
    """Tests effectués après réparation."""
    class Resultat(models.TextChoices):
        REUSSI = 'REUSSI', 'Réussi'
        ECHOUE = 'ECHOUE', 'Échoué'
        NON_TESTE = 'NON_TESTE', 'Non testé'

    id_test = models.BigAutoField(primary_key=True)
    id_reparation = models.ForeignKey(
        Reparation,
        on_delete=models.CASCADE,
        db_column='id_reparation',
        related_name='tests',
    )
    id_technicien = models.ForeignKey(
        Utilisateur,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_column='id_technicien',
    )
    type_test = models.CharField(max_length=100)
    resultat = models.CharField(max_length=30, choices=Resultat.choices)
    commentaire = models.TextField(null=True, blank=True)
    date_test = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'test_reparation'
        managed = False
        verbose_name = 'Test de réparation'
        verbose_name_plural = 'Tests de réparation'

    def __str__(self):
        return f"{self.type_test} – {self.resultat}"


class AdresseCollecteReparation(models.Model):
    """Adresse de collecte pour une réparation en mode COLLECTE."""
    id_adresse_collecte = models.BigAutoField(primary_key=True)
    id_reparation = models.OneToOneField(
        Reparation,
        on_delete=models.CASCADE,
        db_column='id_reparation',
        related_name='adresse_collecte',
    )
    nom_contact = models.CharField(max_length=200)
    telephone = models.CharField(max_length=30)
    ville_nom = models.CharField(max_length=100)
    quartier = models.CharField(max_length=150)
    adresse_detail = models.TextField()
    point_repere = models.CharField(max_length=255, null=True, blank=True)
    instructions = models.TextField(null=True, blank=True)

    class Meta:
        db_table = 'adresse_collecte_reparation'
        managed = False
        verbose_name = 'Adresse de collecte'
        verbose_name_plural = 'Adresses de collecte'

    def __str__(self):
        return f"{self.nom_contact} – {self.ville_nom}"


class TarifCollecteReparation(models.Model):
    """Tarif de collecte par ville."""
    id_tarif_collecte = models.BigAutoField(primary_key=True)
    id_ville = models.ForeignKey(
        Ville,
        on_delete=models.RESTRICT,
        db_column='id_ville',
    )
    montant = models.DecimalField(max_digits=12, decimal_places=2)
    date_debut = models.DateTimeField()
    date_fin = models.DateTimeField(null=True, blank=True)
    actif = models.BooleanField(default=True)

    class Meta:
        db_table = 'tarif_collecte_reparation'
        managed = False
        verbose_name = 'Tarif de collecte'
        verbose_name_plural = 'Tarifs de collecte'

    def __str__(self):
        return f"{self.id_ville} – {self.montant} FCFA"


class CollecteReparation(models.Model):
    """Suivi de la collecte d'un appareil."""
    class Statut(models.TextChoices):
        EN_ATTENTE = 'EN_ATTENTE', 'En attente'
        PLANIFIEE = 'PLANIFIEE', 'Planifiée'
        EN_COURS = 'EN_COURS', 'En cours'
        EFFECTUEE = 'EFFECTUEE', 'Effectuée'
        ANNULEE = 'ANNULEE', 'Annulée'
        ECHEC = 'ECHEC', 'Échec'

    id_collecte = models.BigAutoField(primary_key=True)
    id_reparation = models.OneToOneField(
        Reparation,
        on_delete=models.CASCADE,
        db_column='id_reparation',
        related_name='collecte',
    )
    id_adresse_collecte = models.ForeignKey(
        AdresseCollecteReparation,
        on_delete=models.RESTRICT,
        db_column='id_adresse_collecte',
    )
    id_tarif_collecte = models.ForeignKey(
        TarifCollecteReparation,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_column='id_tarif_collecte',
    )
    frais = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    statut = models.CharField(
        max_length=30,
        choices=Statut.choices,
        default=Statut.EN_ATTENTE,
    )
    date_demande = models.DateTimeField(auto_now_add=True)
    date_collecte_prevue = models.DateTimeField(null=True, blank=True)
    date_collecte_effectuee = models.DateTimeField(null=True, blank=True)
    commentaire = models.TextField(null=True, blank=True)

    class Meta:
        db_table = 'collecte_reparation'
        managed = False
        verbose_name = 'Collecte de réparation'
        verbose_name_plural = 'Collectes de réparation'

    def __str__(self):
        return f"Collecte {self.id_reparation.reference} – {self.statut}"