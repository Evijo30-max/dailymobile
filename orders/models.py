from django.db import models
from users.models import Utilisateur
from catalogue.models import OffreProduit


class Ville(models.Model):
    """Villes desservies pour la livraison (administrables)."""
    id_ville = models.BigAutoField(primary_key=True)
    nom = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=20, null=True, blank=True)
    actif = models.BooleanField(default=True)
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'ville'
        managed = False
        verbose_name = 'Ville'
        verbose_name_plural = 'Villes'
        ordering = ['nom']

    def __str__(self):
        return self.nom


class Adresse(models.Model):
    """Adresses enregistrées d'un utilisateur."""
    id_adresse = models.BigAutoField(primary_key=True)
    id_utilisateur = models.ForeignKey(
        Utilisateur,
        on_delete=models.CASCADE,
        db_column='id_utilisateur',
        related_name='adresses',
    )
    id_ville = models.ForeignKey(
        Ville,
        on_delete=models.RESTRICT,
        db_column='id_ville',
    )
    nom_destinataire = models.CharField(max_length=200)
    telephone = models.CharField(max_length=30)
    quartier = models.CharField(max_length=150)
    adresse_detail = models.TextField()
    point_repere = models.CharField(max_length=255, null=True, blank=True)
    instructions = models.TextField(null=True, blank=True)
    est_principale = models.BooleanField(default=False)
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'adresse'
        managed = False
        verbose_name = 'Adresse'
        verbose_name_plural = 'Adresses'

    def __str__(self):
        return f"{self.nom_destinataire} – {self.quartier}, {self.id_ville}"


class Panier(models.Model):
    """Panier d'un utilisateur. Un seul panier ACTIF autorisé."""
    class Statut(models.TextChoices):
        ACTIF = 'ACTIF', 'Actif'
        ABANDONNE = 'ABANDONNE', 'Abandonné'
        CONVERTI = 'CONVERTI', 'Converti'

    id_panier = models.BigAutoField(primary_key=True)
    id_utilisateur = models.ForeignKey(
        Utilisateur,
        on_delete=models.CASCADE,
        db_column='id_utilisateur',
        related_name='paniers',
    )
    statut = models.CharField(
        max_length=30,
        choices=Statut.choices,
        default=Statut.ACTIF,
    )
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'panier'
        managed = False
        verbose_name = 'Panier'
        verbose_name_plural = 'Paniers'

    def __str__(self):
        return f"Panier {self.id_panier} – {self.id_utilisateur}"


class LignePanier(models.Model):
    """Ligne d'un panier (offre + quantité)."""
    id_ligne_panier = models.BigAutoField(primary_key=True)
    id_panier = models.ForeignKey(
        Panier,
        on_delete=models.CASCADE,
        db_column='id_panier',
        related_name='lignes',
    )
    id_offre = models.ForeignKey(
        OffreProduit,
        on_delete=models.RESTRICT,
        db_column='id_offre',
    )
    quantite = models.PositiveIntegerField(default=1)
    prix_unitaire = models.DecimalField(max_digits=12, decimal_places=2)
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'ligne_panier'
        managed = False
        verbose_name = 'Ligne de panier'
        verbose_name_plural = 'Lignes de panier'
        unique_together = (('id_panier', 'id_offre'),)

    def __str__(self):
        return f"{self.id_offre} x {self.quantite}"


class Commande(models.Model):
    """
    Commande client.
    total = sous_total - remise + frais_livraison (contrôlé en SQL).
    """
    class ModeReception(models.TextChoices):
        LIVRAISON = 'LIVRAISON', 'Livraison'
        RETRAIT_BOUTIQUE = 'RETRAIT_BOUTIQUE', 'Retrait en boutique'

    class Statut(models.TextChoices):
        EN_ATTENTE_PAIEMENT = 'EN_ATTENTE_PAIEMENT', 'En attente de paiement'
        PAYEE = 'PAYEE', 'Payée'
        EN_PREPARATION = 'EN_PREPARATION', 'En préparation'
        PRETE = 'PRETE', 'Prête'
        EXPEDIEE = 'EXPEDIEE', 'Expédiée'
        LIVREE = 'LIVREE', 'Livrée'
        RETIREE = 'RETIREE', 'Retirée'
        ANNULEE = 'ANNULEE', 'Annulée'
        REMBOURSEE = 'REMBOURSEE', 'Remboursée'

    id_commande = models.BigAutoField(primary_key=True)
    id_utilisateur = models.ForeignKey(
        Utilisateur,
        on_delete=models.RESTRICT,
        db_column='id_utilisateur',
        related_name='commandes',
    )
    reference = models.CharField(max_length=50, unique=True)
    sous_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    remise = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    frais_livraison = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    mode_reception = models.CharField(max_length=30, choices=ModeReception.choices)
    statut = models.CharField(
        max_length=40,
        choices=Statut.choices,
        default=Statut.EN_ATTENTE_PAIEMENT,
    )
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'commande'
        managed = False
        verbose_name = 'Commande'
        verbose_name_plural = 'Commandes'
        ordering = ['-date_creation']

    def __str__(self):
        return f"{self.reference} – {self.total} FCFA"


class LigneCommande(models.Model):
    """
    Ligne de commande (snapshot historique).
    On conserve nom et prix au moment de l'achat.
    """
    id_ligne_commande = models.BigAutoField(primary_key=True)
    id_commande = models.ForeignKey(
        Commande,
        on_delete=models.CASCADE,
        db_column='id_commande',
        related_name='lignes',
    )
    id_offre = models.ForeignKey(
        OffreProduit,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_column='id_offre',
    )
    nom_produit = models.CharField(max_length=255)
    nom_variante = models.CharField(max_length=255, null=True, blank=True)
    type_offre = models.CharField(max_length=30)
    prix_unitaire = models.DecimalField(max_digits=12, decimal_places=2)
    quantite = models.PositiveIntegerField()
    remise = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        db_table = 'ligne_commande'
        managed = False
        verbose_name = 'Ligne de commande'
        verbose_name_plural = 'Lignes de commande'

    def __str__(self):
        return f"{self.nom_produit} x {self.quantite}"


class AdresseCommande(models.Model):
    """Snapshot de l'adresse utilisée au moment de la commande."""
    id_adresse_commande = models.BigAutoField(primary_key=True)
    id_commande = models.OneToOneField(
        Commande,
        on_delete=models.CASCADE,
        db_column='id_commande',
        related_name='adresse',
    )
    nom_destinataire = models.CharField(max_length=200)
    telephone = models.CharField(max_length=30)
    ville_nom = models.CharField(max_length=100)
    ville_code = models.CharField(max_length=20, null=True, blank=True)
    quartier = models.CharField(max_length=150)
    adresse_detail = models.TextField()
    point_repere = models.CharField(max_length=255, null=True, blank=True)
    instructions = models.TextField(null=True, blank=True)

    class Meta:
        db_table = 'adresse_commande'
        managed = False
        verbose_name = 'Adresse de commande'
        verbose_name_plural = 'Adresses de commande'

    def __str__(self):
        return f"{self.nom_destinataire} – {self.ville_nom}"


class TarifLivraison(models.Model):
    """Tarif de livraison par ville (administrable)."""
    id_tarif = models.BigAutoField(primary_key=True)
    id_ville = models.ForeignKey(
        Ville,
        on_delete=models.RESTRICT,
        db_column='id_ville',
        related_name='tarifs_livraison',
    )
    montant = models.DecimalField(max_digits=12, decimal_places=2)
    date_debut = models.DateTimeField()
    date_fin = models.DateTimeField(null=True, blank=True)
    actif = models.BooleanField(default=True)

    class Meta:
        db_table = 'tarif_livraison'
        managed = False
        verbose_name = 'Tarif de livraison'
        verbose_name_plural = 'Tarifs de livraison'

    def __str__(self):
        return f"{self.id_ville} – {self.montant} FCFA"


class Livraison(models.Model):
    """Suivi de livraison d'une commande."""
    class Statut(models.TextChoices):
        EN_ATTENTE = 'EN_ATTENTE', 'En attente'
        PREPARATION = 'PREPARATION', 'Préparation'
        EXPEDIEE = 'EXPEDIEE', 'Expédiée'
        EN_TRANSIT = 'EN_TRANSIT', 'En transit'
        LIVREE = 'LIVREE', 'Livrée'
        ANNULEE = 'ANNULEE', 'Annulée'

    id_livraison = models.BigAutoField(primary_key=True)
    id_commande = models.OneToOneField(
        Commande,
        on_delete=models.CASCADE,
        db_column='id_commande',
        related_name='livraison',
    )
    id_tarif = models.ForeignKey(
        TarifLivraison,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_column='id_tarif',
    )
    frais = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    statut = models.CharField(
        max_length=30,
        choices=Statut.choices,
        default=Statut.EN_ATTENTE,
    )
    date_creation = models.DateTimeField(auto_now_add=True)
    date_expedition = models.DateTimeField(null=True, blank=True)
    date_livraison = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'livraison'
        managed = False
        verbose_name = 'Livraison'
        verbose_name_plural = 'Livraisons'

    def __str__(self):
        return f"Livraison {self.id_commande.reference} – {self.statut}"


class MoyenPaiement(models.Model):
    """Moyens de paiement administrables (Mobile Money, Espèces…)."""
    id_moyen_paiement = models.BigAutoField(primary_key=True)
    nom = models.CharField(max_length=100)
    code = models.CharField(max_length=50, unique=True)
    description = models.TextField(null=True, blank=True)
    actif = models.BooleanField(default=True)
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'moyen_paiement'
        managed = False
        verbose_name = 'Moyen de paiement'
        verbose_name_plural = 'Moyens de paiement'

    def __str__(self):
        return self.nom


class Paiement(models.Model):
    """
    Paiement lié SOIT à une commande, SOIT à une réparation (XOR).
    """
    class Statut(models.TextChoices):
        EN_ATTENTE = 'EN_ATTENTE', 'En attente'
        REUSSI = 'REUSSI', 'Réussi'
        ECHOUE = 'ECHOUE', 'Échoué'
        ANNULE = 'ANNULE', 'Annulé'
        EXPIRE = 'EXPIRE', 'Expiré'

    class Contexte(models.TextChoices):
        COMMANDE = 'COMMANDE', 'Commande'
        REPARATION = 'REPARATION', 'Réparation'

    class TypePaiement(models.TextChoices):
        PAIEMENT_COMPLET = 'PAIEMENT_COMPLET', 'Paiement complet'
        ACOMPTE = 'ACOMPTE', 'Acompte'
        SOLDE = 'SOLDE', 'Solde'

    id_paiement = models.BigAutoField(primary_key=True)
    id_commande = models.ForeignKey(
        Commande,
        on_delete=models.RESTRICT,
        null=True,
        blank=True,
        db_column='id_commande',
        related_name='paiements',
    )
    # id_reparation sera ajouté quand on créera le modèle Reparation
    id_reparation = models.BigIntegerField(null=True, blank=True)

    id_moyen_paiement = models.ForeignKey(
        MoyenPaiement,
        on_delete=models.RESTRICT,
        db_column='id_moyen_paiement',
    )
    reference_interne = models.CharField(max_length=100, unique=True)
    reference_externe = models.CharField(max_length=150, null=True, blank=True)
    montant = models.DecimalField(max_digits=12, decimal_places=2)
    statut = models.CharField(
        max_length=30,
        choices=Statut.choices,
        default=Statut.EN_ATTENTE,
    )
    contexte = models.CharField(max_length=30, choices=Contexte.choices)
    type_paiement = models.CharField(max_length=30, choices=TypePaiement.choices)
    date_creation = models.DateTimeField(auto_now_add=True)
    date_confirmation = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'paiement'
        managed = False
        verbose_name = 'Paiement'
        verbose_name_plural = 'Paiements'

    def __str__(self):
        return f"{self.reference_interne} – {self.montant} FCFA"