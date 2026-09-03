from django.db import models


class Marque(models.Model):
    """Marque d'un produit (Apple, Samsung, HP, etc.)."""
    id_marque = models.BigAutoField(primary_key=True)
    nom = models.CharField(max_length=100, unique=True)
    description = models.TextField(null=True, blank=True)
    actif = models.BooleanField(default=True)
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'marque'
        managed = False
        verbose_name = 'Marque'
        verbose_name_plural = 'Marques'
        ordering = ['nom']

    def __str__(self):
        return self.nom


class Categorie(models.Model):
    """Catégorie de produits avec support hiérarchique simple."""
    id_categorie = models.BigAutoField(primary_key=True)
    id_categorie_parent = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sous_categories',
        db_column='id_categorie_parent',
    )
    nom = models.CharField(max_length=150)
    description = models.TextField(null=True, blank=True)
    slug = models.SlugField(max_length=180, unique=True)
    actif = models.BooleanField(default=True)
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'categorie'
        managed = False
        verbose_name = 'Catégorie'
        verbose_name_plural = 'Catégories'
        ordering = ['nom']

    def __str__(self):
        return self.nom


class Produit(models.Model):
    """Produit parent (ex: iPhone 15). Les prix et stocks sont sur les variantes/offres."""
    id_produit = models.BigAutoField(primary_key=True)
    id_marque = models.ForeignKey(
        Marque,
        on_delete=models.RESTRICT,
        db_column='id_marque',
        related_name='produits',
    )
    nom = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)
    slug = models.SlugField(max_length=280, unique=True)
    actif = models.BooleanField(default=True)
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)
    image_url = models.CharField(max_length=500, null=True, blank=True)

    
    categories = models.ManyToManyField(
        Categorie,
        through='ProduitCategorie',
        related_name='produits',
        blank=True,
    )

    class Meta:
        db_table = 'produit'
        managed = False
        verbose_name = 'Produit'
        verbose_name_plural = 'Produits'
        ordering = ['nom']

    def __str__(self):
        return self.nom


class ProduitCategorie(models.Model):
    """Table de liaison N-N Produit ↔ Categorie."""
    id_produit = models.ForeignKey(Produit, on_delete=models.CASCADE, db_column='id_produit')
    id_categorie = models.ForeignKey(Categorie, on_delete=models.CASCADE, db_column='id_categorie')

    class Meta:
        db_table = 'produit_categorie'
        managed = False
        unique_together = (('id_produit', 'id_categorie'),)


class Variante(models.Model):
    """Variante d'un produit (ex: 128 Go Noir). Contient le SKU."""
    id_variante = models.BigAutoField(primary_key=True)
    id_produit = models.ForeignKey(
        Produit,
        on_delete=models.CASCADE,
        db_column='id_produit',
        related_name='variantes',
    )
    nom = models.CharField(max_length=255)
    sku = models.CharField(max_length=100, null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    actif = models.BooleanField(default=True)
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'variante'
        managed = False
        verbose_name = 'Variante'
        verbose_name_plural = 'Variantes'
        ordering = ['nom']

    def __str__(self):
        return f"{self.id_produit.nom} – {self.nom}"


class Caracteristique(models.Model):
    """Caractéristique technique possible (Stockage, RAM, Couleur…)."""
    id_caracteristique = models.BigAutoField(primary_key=True)
    nom = models.CharField(max_length=100, unique=True)
    unite = models.CharField(max_length=50, null=True, blank=True)
    actif = models.BooleanField(default=True)
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'caracteristique'
        managed = False
        verbose_name = 'Caractéristique'
        verbose_name_plural = 'Caractéristiques'
        ordering = ['nom']

    def __str__(self):
        return self.nom


class VarianteCaracteristique(models.Model):
    """
    Valeur d'une caractéristique pour une variante.
    Clé primaire composite (id_variante + id_caracteristique).
    """
    # Django 5.2+ / 6.x : support natif des clés composites
    pk = models.CompositePrimaryKey('id_variante', 'id_caracteristique')

    id_variante = models.ForeignKey(
        Variante,
        on_delete=models.CASCADE,
        db_column='id_variante',
        related_name='caracteristiques',
    )
    id_caracteristique = models.ForeignKey(
        Caracteristique,
        on_delete=models.CASCADE,
        db_column='id_caracteristique',
    )
    valeur = models.CharField(max_length=255)

    class Meta:
        db_table = 'variante_caracteristique'
        managed = False

    def __str__(self):
        return f"{self.id_variante} – {self.id_caracteristique.nom}: {self.valeur}"



class EtatProduit(models.Model):
    """État physique (NEUF, COMME_NEUF, BON_ETAT…)."""
    id_etat_produit = models.BigAutoField(primary_key=True)
    code = models.CharField(max_length=50, unique=True)
    nom = models.CharField(max_length=100)
    description = models.TextField(null=True, blank=True)
    actif = models.BooleanField(default=True)
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'etat_produit'
        managed = False
        verbose_name = 'État produit'
        verbose_name_plural = 'États produits'
        ordering = ['nom']

    def __str__(self):
        return self.nom


class EmplacementStock(models.Model):
    """Emplacement physique de stockage (Rayon A, Magasin, Réserve…)."""
    id_emplacement_stock = models.BigAutoField(primary_key=True)
    nom = models.CharField(max_length=150, unique=True)
    description = models.TextField(null=True, blank=True)
    actif = models.BooleanField(default=True)
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'emplacement_stock'
        managed = False
        verbose_name = 'Emplacement de stock'
        verbose_name_plural = 'Emplacements de stock'
        ordering = ['nom']

    def __str__(self):
        return self.nom


class UniteProduit(models.Model):
    """
    Unité physique individualisée (surtout pour l'occasion).
    Possède un IMEI / numéro de série unique.
    """
    class Statut(models.TextChoices):
        EN_STOCK = 'EN_STOCK', 'En stock'
        RESERVEE = 'RESERVEE', 'Réservée'
        VENDUE = 'VENDUE', 'Vendue'
        SORTIE = 'SORTIE', 'Sortie'
        RETOURNEE = 'RETOURNEE', 'Retournée'
        HORS_SERVICE = 'HORS_SERVICE', 'Hors service'

    id_unite_produit = models.BigAutoField(primary_key=True)
    id_variante = models.ForeignKey(
        Variante,
        on_delete=models.RESTRICT,
        db_column='id_variante',
        related_name='unites',
    )
    id_etat_produit = models.ForeignKey(
        EtatProduit,
        on_delete=models.RESTRICT,
        null=True,
        blank=True,
        db_column='id_etat_produit',
    )
    id_emplacement_stock = models.ForeignKey(
        EmplacementStock,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_column='id_emplacement_stock',
    )
    numero_serie = models.CharField(max_length=100, null=True, blank=True)
    imei = models.CharField(max_length=50, null=True, blank=True)
    statut = models.CharField(
        max_length=30,
        choices=Statut.choices,
        default=Statut.EN_STOCK,
    )
    observation = models.TextField(null=True, blank=True)
    date_entree = models.DateTimeField(auto_now_add=True)
    date_sortie = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'unite_produit'
        managed = False
        verbose_name = 'Unité produit'
        verbose_name_plural = 'Unités produit'

    def __str__(self):
        identifiant = self.imei or self.numero_serie or f"#{self.id_unite_produit}"
        return f"{self.id_variante} – {identifiant}"


class OffreProduit(models.Model):
    """
    Ce qui est réellement vendu au client.
    - NEUF : quantifiée, sans unité individualisée
    - OCCASION : liée à une unité physique précise
    """
    class TypeOffre(models.TextChoices):
        NEUF = 'NEUF', 'Neuf'
        OCCASION = 'OCCASION', 'Occasion'

    id_offre = models.BigAutoField(primary_key=True)
    id_variante = models.ForeignKey(
        Variante,
        on_delete=models.RESTRICT,
        db_column='id_variante',
        related_name='offres',
    )
    id_unite_produit = models.ForeignKey(
        UniteProduit,
        on_delete=models.RESTRICT,
        null=True,
        blank=True,
        db_column='id_unite_produit',
        related_name='offre',
    )
    type_offre = models.CharField(max_length=20, choices=TypeOffre.choices)
    prix_vente = models.DecimalField(max_digits=12, decimal_places=2)
    prix_compare = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    quantite_disponible = models.PositiveIntegerField(default=0)
    actif = models.BooleanField(default=True)
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'offre_produit'
        managed = False
        verbose_name = 'Offre produit'
        verbose_name_plural = 'Offres produit'

    def __str__(self):
        return f"{self.id_variante} – {self.type_offre} – {self.prix_vente} FCFA"


class StockVariante(models.Model):
    """
    Stock quantitatif des produits neufs par variante et emplacement.
    Attention : double source de vérité avec offre_produit.quantite_disponible.
    L'application devra les maintenir synchronisées.
    """
    id_variante = models.ForeignKey(
        Variante,
        on_delete=models.CASCADE,
        db_column='id_variante',
    )
    id_emplacement_stock = models.ForeignKey(
        EmplacementStock,
        on_delete=models.CASCADE,
        db_column='id_emplacement_stock',
    )
    quantite = models.PositiveIntegerField(default=0)
    seuil_alerte = models.PositiveIntegerField(default=0)
    date_modification = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'stock_variante'
        managed = False
        unique_together = (('id_variante', 'id_emplacement_stock'),)
        verbose_name = 'Stock variante'
        verbose_name_plural = 'Stocks variante'

    def __str__(self):
        return f"{self.id_variante} @ {self.id_emplacement_stock} : {self.quantite}"