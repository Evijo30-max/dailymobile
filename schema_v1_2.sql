-- ============================================================
-- PROJET E-COMMERCE + RÉPARATION
-- SCHÉMA POSTGRESQL COMPLET
-- ============================================================
-- Version : 1.2
--
-- OBJECTIF
-- --------
-- Ce fichier crée le schéma relationnel complet de l'application :
-- catalogue, variantes, stock, commandes, livraisons, paiements,
-- réparations, promotions, notifications et audit.
--
-- IMPORTANT
-- ---------
-- 1. Les montants utilisent NUMERIC, jamais FLOAT.
-- 2. Les informations historiques d'une commande/réparation sont
--    volontairement copiées dans des tables "snapshot".
-- 3. Les règles métier complexes sont contrôlées par PostgreSQL
--    lorsque cela est pertinent, et devront aussi être contrôlées
--    côté Django.
-- 4. Ce script est une reconstruction technique cohérente du MLD
--    validé ensemble. Les quelques choix non retrouvables mot pour
--    mot dans l'ancien dictionnaire sont signalés par "CHOIX TECHNIQUE".
-- ============================================================

BEGIN;

-- ============================================================
-- 0. EXTENSIONS / FONCTIONS COMMUNES
-- ============================================================

-- pgcrypto permet notamment de générer des UUID si nous en avons
-- besoin plus tard. Le modèle utilise principalement BIGINT pour
-- les clés internes, mais l'extension reste utile côté PostgreSQL.
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Fonction commune pour maintenir automatiquement date_modification.
CREATE OR REPLACE FUNCTION fn_set_date_modification()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    NEW.date_modification = NOW();
    RETURN NEW;
END;
$$;


-- ============================================================
-- 1. UTILISATEURS
-- ============================================================

CREATE TABLE utilisateur (
    id_utilisateur      BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    nom                 VARCHAR(100) NOT NULL,
    prenom              VARCHAR(100) NOT NULL,
    email               VARCHAR(255),
    telephone           VARCHAR(30),
    mot_de_passe_hash   VARCHAR(255) NOT NULL,
    role                VARCHAR(30) NOT NULL DEFAULT 'CLIENT',
    actif               BOOLEAN NOT NULL DEFAULT TRUE,
    date_creation       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    date_modification   TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT ck_utilisateur_role
        CHECK (role IN ('CLIENT', 'ADMIN')),

    CONSTRAINT ck_utilisateur_contact
        CHECK (email IS NOT NULL OR telephone IS NOT NULL)
);

CREATE UNIQUE INDEX uq_utilisateur_email_ci
    ON utilisateur (LOWER(email))
    WHERE email IS NOT NULL;

CREATE UNIQUE INDEX uq_utilisateur_telephone
    ON utilisateur (telephone)
    WHERE telephone IS NOT NULL;

CREATE TRIGGER trg_utilisateur_date_modification
BEFORE UPDATE ON utilisateur
FOR EACH ROW
EXECUTE FUNCTION fn_set_date_modification();


-- ============================================================
-- 2. VILLES
-- ============================================================

CREATE TABLE ville (
    id_ville             BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    nom                   VARCHAR(100) NOT NULL,
    code                  VARCHAR(20),
    actif                 BOOLEAN NOT NULL DEFAULT TRUE,
    date_creation         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    date_modification     TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT uq_ville_nom UNIQUE (nom)
);

CREATE UNIQUE INDEX uq_ville_code
    ON ville (code)
    WHERE code IS NOT NULL;

CREATE TRIGGER trg_ville_date_modification
BEFORE UPDATE ON ville
FOR EACH ROW
EXECUTE FUNCTION fn_set_date_modification();


-- ============================================================
-- 3. ADRESSES
-- ============================================================

CREATE TABLE adresse (
    id_adresse          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_utilisateur      BIGINT NOT NULL,
    id_ville            BIGINT NOT NULL,
    nom_destinataire    VARCHAR(200) NOT NULL,
    telephone           VARCHAR(30) NOT NULL,
    quartier            VARCHAR(150) NOT NULL,
    adresse_detail      TEXT NOT NULL,
    point_repere        VARCHAR(255),
    instructions        TEXT,
    est_principale      BOOLEAN NOT NULL DEFAULT FALSE,
    date_creation       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    date_modification   TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT fk_adresse_utilisateur
        FOREIGN KEY (id_utilisateur)
        REFERENCES utilisateur(id_utilisateur)
        ON DELETE CASCADE,

    CONSTRAINT fk_adresse_ville
        FOREIGN KEY (id_ville)
        REFERENCES ville(id_ville)
        ON DELETE RESTRICT
);

CREATE INDEX idx_adresse_utilisateur
    ON adresse(id_utilisateur);

CREATE INDEX idx_adresse_ville
    ON adresse(id_ville);

CREATE UNIQUE INDEX uq_adresse_principale_utilisateur
    ON adresse(id_utilisateur)
    WHERE est_principale = TRUE;

CREATE TRIGGER trg_adresse_date_modification
BEFORE UPDATE ON adresse
FOR EACH ROW
EXECUTE FUNCTION fn_set_date_modification();


-- ============================================================
-- 4. MARQUES
-- ============================================================

CREATE TABLE marque (
    id_marque           BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    nom                 VARCHAR(100) NOT NULL,
    description         TEXT,
    actif               BOOLEAN NOT NULL DEFAULT TRUE,
    date_creation       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    date_modification   TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT uq_marque_nom UNIQUE (nom)
);

CREATE TRIGGER trg_marque_date_modification
BEFORE UPDATE ON marque
FOR EACH ROW
EXECUTE FUNCTION fn_set_date_modification();


-- ============================================================
-- 5. CATÉGORIES
-- ============================================================

CREATE TABLE categorie (
    id_categorie        BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_categorie_parent BIGINT,
    nom                 VARCHAR(150) NOT NULL,
    description         TEXT,
    slug                VARCHAR(180) NOT NULL,
    actif               BOOLEAN NOT NULL DEFAULT TRUE,
    date_creation       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    date_modification   TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT fk_categorie_parent
        FOREIGN KEY (id_categorie_parent)
        REFERENCES categorie(id_categorie)
        ON DELETE SET NULL,

    CONSTRAINT uq_categorie_slug UNIQUE (slug)
);

CREATE INDEX idx_categorie_parent
    ON categorie(id_categorie_parent);

CREATE TRIGGER trg_categorie_date_modification
BEFORE UPDATE ON categorie
FOR EACH ROW
EXECUTE FUNCTION fn_set_date_modification();


-- ============================================================
-- 6. PRODUITS PARENTS
-- ============================================================

CREATE TABLE produit (
    id_produit          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_marque           BIGINT NOT NULL,
    nom                 VARCHAR(255) NOT NULL,
    description         TEXT,
    slug                VARCHAR(280) NOT NULL,
    actif               BOOLEAN NOT NULL DEFAULT TRUE,
    date_creation       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    date_modification   TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT fk_produit_marque
        FOREIGN KEY (id_marque)
        REFERENCES marque(id_marque)
        ON DELETE RESTRICT,

    CONSTRAINT uq_produit_slug UNIQUE (slug)
);

CREATE INDEX idx_produit_marque
    ON produit(id_marque);

CREATE TRIGGER trg_produit_date_modification
BEFORE UPDATE ON produit
FOR EACH ROW
EXECUTE FUNCTION fn_set_date_modification();


-- ============================================================
-- 7. PRODUIT_CATEGORIE
-- ============================================================
-- Une relation N,N : un produit peut appartenir à plusieurs
-- catégories et une catégorie peut contenir plusieurs produits.

CREATE TABLE produit_categorie (
    id_produit      BIGINT NOT NULL,
    id_categorie    BIGINT NOT NULL,

    PRIMARY KEY (id_produit, id_categorie),

    CONSTRAINT fk_produit_categorie_produit
        FOREIGN KEY (id_produit)
        REFERENCES produit(id_produit)
        ON DELETE CASCADE,

    CONSTRAINT fk_produit_categorie_categorie
        FOREIGN KEY (id_categorie)
        REFERENCES categorie(id_categorie)
        ON DELETE CASCADE
);


-- ============================================================
-- 8. VARIANTES
-- ============================================================

CREATE TABLE variante (
    id_variante          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_produit           BIGINT NOT NULL,
    nom                  VARCHAR(255) NOT NULL,
    sku                  VARCHAR(100),
    description          TEXT,
    actif                BOOLEAN NOT NULL DEFAULT TRUE,
    date_creation        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    date_modification    TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT fk_variante_produit
        FOREIGN KEY (id_produit)
        REFERENCES produit(id_produit)
        ON DELETE CASCADE
);

CREATE UNIQUE INDEX uq_variante_sku
    ON variante(sku)
    WHERE sku IS NOT NULL;

CREATE INDEX idx_variante_produit
    ON variante(id_produit);

CREATE TRIGGER trg_variante_date_modification
BEFORE UPDATE ON variante
FOR EACH ROW
EXECUTE FUNCTION fn_set_date_modification();


-- ============================================================
-- 9. IMAGES PRODUIT
-- ============================================================

CREATE TABLE image_produit (
    id_image_produit     BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_produit           BIGINT NOT NULL,
    url                  TEXT NOT NULL,
    texte_alternatif     VARCHAR(255),
    ordre_affichage      INTEGER NOT NULL DEFAULT 0,
    est_principale       BOOLEAN NOT NULL DEFAULT FALSE,
    date_creation       TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT fk_image_produit
        FOREIGN KEY (id_produit)
        REFERENCES produit(id_produit)
        ON DELETE CASCADE,

    CONSTRAINT ck_image_produit_ordre
        CHECK (ordre_affichage >= 0)
);

CREATE INDEX idx_image_produit_produit
    ON image_produit(id_produit);

CREATE UNIQUE INDEX uq_image_produit_principale
    ON image_produit(id_produit)
    WHERE est_principale = TRUE;


-- ============================================================
-- 10. IMAGES VARIANTE
-- ============================================================

CREATE TABLE image_variante (
    id_image_variante    BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_variante          BIGINT NOT NULL,
    url                  TEXT NOT NULL,
    texte_alternatif     VARCHAR(255),
    ordre_affichage      INTEGER NOT NULL DEFAULT 0,
    est_principale       BOOLEAN NOT NULL DEFAULT FALSE,
    date_creation        TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT fk_image_variante
        FOREIGN KEY (id_variante)
        REFERENCES variante(id_variante)
        ON DELETE CASCADE,

    CONSTRAINT ck_image_variante_ordre
        CHECK (ordre_affichage >= 0)
);

CREATE INDEX idx_image_variante_variante
    ON image_variante(id_variante);

CREATE UNIQUE INDEX uq_image_variante_principale
    ON image_variante(id_variante)
    WHERE est_principale = TRUE;


-- ============================================================
-- 11. CARACTÉRISTIQUES
-- ============================================================
-- Exemple : stockage, RAM, couleur, taille d'écran, etc.

CREATE TABLE caracteristique (
    id_caracteristique   BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    nom                  VARCHAR(100) NOT NULL,
    unite                VARCHAR(50),
    actif                BOOLEAN NOT NULL DEFAULT TRUE,
    date_creation        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    date_modification    TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT uq_caracteristique_nom UNIQUE (nom)
);

CREATE TRIGGER trg_caracteristique_date_modification
BEFORE UPDATE ON caracteristique
FOR EACH ROW
EXECUTE FUNCTION fn_set_date_modification();


-- ============================================================
-- 12. VARIANTE_CARACTERISTIQUE
-- ============================================================

CREATE TABLE variante_caracteristique (
    id_variante          BIGINT NOT NULL,
    id_caracteristique   BIGINT NOT NULL,
    valeur               VARCHAR(255) NOT NULL,

    PRIMARY KEY (id_variante, id_caracteristique),

    CONSTRAINT fk_vc_variante
        FOREIGN KEY (id_variante)
        REFERENCES variante(id_variante)
        ON DELETE CASCADE,

    CONSTRAINT fk_vc_caracteristique
        FOREIGN KEY (id_caracteristique)
        REFERENCES caracteristique(id_caracteristique)
        ON DELETE CASCADE
);


-- ============================================================
-- 13. ÉTATS DES PRODUITS
-- ============================================================
-- Utilisé notamment pour les appareils d'occasion.
-- Exemple : BON_ETAT, TRES_BON_ETAT, COMME_NEUF.

CREATE TABLE etat_produit (
    id_etat_produit      BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    code                 VARCHAR(50) NOT NULL,
    nom                  VARCHAR(100) NOT NULL,
    description          TEXT,
    actif                BOOLEAN NOT NULL DEFAULT TRUE,
    date_creation        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    date_modification    TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT uq_etat_produit_code UNIQUE (code)
);

CREATE TRIGGER trg_etat_produit_date_modification
BEFORE UPDATE ON etat_produit
FOR EACH ROW
EXECUTE FUNCTION fn_set_date_modification();


-- ============================================================
-- 14. EMPLACEMENTS DE STOCK
-- ============================================================

CREATE TABLE emplacement_stock (
    id_emplacement_stock BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    nom                 VARCHAR(150) NOT NULL,
    description         TEXT,
    actif               BOOLEAN NOT NULL DEFAULT TRUE,
    date_creation       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    date_modification   TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT uq_emplacement_stock_nom UNIQUE (nom)
);

CREATE TRIGGER trg_emplacement_stock_date_modification
BEFORE UPDATE ON emplacement_stock
FOR EACH ROW
EXECUTE FUNCTION fn_set_date_modification();


-- ============================================================
-- 15. UNITÉS PHYSIQUES
-- ============================================================
-- Une unité représente un appareil physique individualisé.
-- C'est particulièrement important pour l'occasion.
-- L'état métier est porté par la FK id_etat_produit : on évite
-- volontairement de dupliquer cette information dans une colonne
-- type_etat.
--
-- Exemple :
-- iPhone 13 #A possède son propre IMEI et son propre état.

CREATE TABLE unite_produit (
    id_unite_produit    BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_variante         BIGINT NOT NULL,
    id_etat_produit     BIGINT,
    id_emplacement_stock BIGINT,
    numero_serie        VARCHAR(100),
    imei                VARCHAR(50),
    statut              VARCHAR(30) NOT NULL DEFAULT 'EN_STOCK',
    observation         TEXT,
    date_entree         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    date_sortie         TIMESTAMPTZ,

    CONSTRAINT fk_unite_variante
        FOREIGN KEY (id_variante)
        REFERENCES variante(id_variante)
        ON DELETE RESTRICT,

    CONSTRAINT fk_unite_etat
        FOREIGN KEY (id_etat_produit)
        REFERENCES etat_produit(id_etat_produit)
        ON DELETE RESTRICT,

    CONSTRAINT fk_unite_emplacement
        FOREIGN KEY (id_emplacement_stock)
        REFERENCES emplacement_stock(id_emplacement_stock)
        ON DELETE SET NULL,


    CONSTRAINT ck_unite_statut
        CHECK (statut IN (
            'EN_STOCK',
            'RESERVEE',
            'VENDUE',
            'SORTIE',
            'RETOURNEE',
            'HORS_SERVICE'
        ))
);

CREATE UNIQUE INDEX uq_unite_imei
    ON unite_produit(imei)
    WHERE imei IS NOT NULL;

CREATE UNIQUE INDEX uq_unite_numero_serie
    ON unite_produit(numero_serie)
    WHERE numero_serie IS NOT NULL;

CREATE INDEX idx_unite_variante
    ON unite_produit(id_variante);

CREATE INDEX idx_unite_emplacement
    ON unite_produit(id_emplacement_stock);


-- ============================================================
-- 16. OFFRES PRODUIT
-- ============================================================
-- Une offre est ce qui est réellement vendu au client.
--
-- NEUF :
--   id_unite_produit peut être NULL.
--
-- OCCASION :
--   l'offre représente une unité physique individualisée.
--   id_unite_produit doit donc être renseigné.

CREATE TABLE offre_produit (
    id_offre            BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_variante         BIGINT NOT NULL,
    id_unite_produit    BIGINT,
    type_offre          VARCHAR(20) NOT NULL,
    prix_vente          NUMERIC(12,2) NOT NULL,
    prix_compare        NUMERIC(12,2),
    quantite_disponible INTEGER NOT NULL DEFAULT 0,
    actif               BOOLEAN NOT NULL DEFAULT TRUE,
    date_creation       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    date_modification   TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT fk_offre_variante
        FOREIGN KEY (id_variante)
        REFERENCES variante(id_variante)
        ON DELETE RESTRICT,

    CONSTRAINT fk_offre_unite
        FOREIGN KEY (id_unite_produit)
        REFERENCES unite_produit(id_unite_produit)
        ON DELETE RESTRICT,

    CONSTRAINT ck_offre_type
        CHECK (type_offre IN ('NEUF', 'OCCASION')),

    CONSTRAINT ck_offre_prix
        CHECK (prix_vente >= 0),

    CONSTRAINT ck_offre_prix_compare
        CHECK (prix_compare IS NULL OR prix_compare >= prix_vente),

    CONSTRAINT ck_offre_quantite
        CHECK (quantite_disponible >= 0),

    -- Une offre OCCASION représente une unité physique précise.
    -- Une offre NEUF reste quantifiée au niveau de la variante :
    -- elle ne doit donc pas pointer vers une unité individualisée.
    CONSTRAINT ck_offre_type_unite_coherence
        CHECK (
            (type_offre = 'OCCASION' AND id_unite_produit IS NOT NULL)
            OR
            (type_offre = 'NEUF' AND id_unite_produit IS NULL)
        )
);

CREATE UNIQUE INDEX uq_offre_unite
    ON offre_produit(id_unite_produit)
    WHERE id_unite_produit IS NOT NULL;

CREATE INDEX idx_offre_variante
    ON offre_produit(id_variante);

CREATE INDEX idx_offre_active
    ON offre_produit(actif);

CREATE TRIGGER trg_offre_produit_date_modification
BEFORE UPDATE ON offre_produit
FOR EACH ROW
EXECUTE FUNCTION fn_set_date_modification();


-- ============================================================
-- 17. STOCK_VARIANTE
-- ============================================================
-- Stock quantitatif des produits neufs par variante et emplacement.

CREATE TABLE stock_variante (
    id_variante          BIGINT NOT NULL,
    id_emplacement_stock BIGINT NOT NULL,
    quantite             INTEGER NOT NULL DEFAULT 0,
    seuil_alerte         INTEGER NOT NULL DEFAULT 0,
    date_modification    TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    PRIMARY KEY (id_variante, id_emplacement_stock),

    CONSTRAINT fk_stock_variante_variante
        FOREIGN KEY (id_variante)
        REFERENCES variante(id_variante)
        ON DELETE CASCADE,

    CONSTRAINT fk_stock_variante_emplacement
        FOREIGN KEY (id_emplacement_stock)
        REFERENCES emplacement_stock(id_emplacement_stock)
        ON DELETE CASCADE,

    CONSTRAINT ck_stock_quantite
        CHECK (quantite >= 0),

    CONSTRAINT ck_stock_seuil
        CHECK (seuil_alerte >= 0)
);

CREATE TRIGGER trg_stock_variante_date_modification
BEFORE UPDATE ON stock_variante
FOR EACH ROW
EXECUTE FUNCTION fn_set_date_modification();


-- ============================================================
-- 18. MOUVEMENTS DE STOCK
-- ============================================================
-- Journal immuable des entrées/sorties/corrections.

CREATE TABLE mouvement_stock (
    id_mouvement        BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_variante         BIGINT,
    id_unite_produit    BIGINT,
    id_emplacement_stock BIGINT,
    id_utilisateur      BIGINT,
    type_mouvement      VARCHAR(30) NOT NULL,
    quantite            INTEGER NOT NULL,
    motif               TEXT,
    reference_operation VARCHAR(100),
    date_mouvement      TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT fk_mouvement_variante
        FOREIGN KEY (id_variante)
        REFERENCES variante(id_variante)
        ON DELETE RESTRICT,

    CONSTRAINT fk_mouvement_unite
        FOREIGN KEY (id_unite_produit)
        REFERENCES unite_produit(id_unite_produit)
        ON DELETE RESTRICT,

    CONSTRAINT fk_mouvement_emplacement
        FOREIGN KEY (id_emplacement_stock)
        REFERENCES emplacement_stock(id_emplacement_stock)
        ON DELETE RESTRICT,

    CONSTRAINT fk_mouvement_utilisateur
        FOREIGN KEY (id_utilisateur)
        REFERENCES utilisateur(id_utilisateur)
        ON DELETE SET NULL,

    CONSTRAINT ck_mouvement_type
        CHECK (type_mouvement IN (
            'ENTREE',
            'SORTIE',
            'RESERVATION',
            'ANNULATION_RESERVATION',
            'RETOUR',
            'AJUSTEMENT'
        )),

    CONSTRAINT ck_mouvement_quantite
        CHECK (quantite > 0),

    CONSTRAINT ck_mouvement_cible
        CHECK (id_variante IS NOT NULL OR id_unite_produit IS NOT NULL)
);

CREATE INDEX idx_mouvement_variante
    ON mouvement_stock(id_variante);

CREATE INDEX idx_mouvement_unite
    ON mouvement_stock(id_unite_produit);

CREATE INDEX idx_mouvement_date
    ON mouvement_stock(date_mouvement);


-- ============================================================
-- 19. PANIER
-- ============================================================

CREATE TABLE panier (
    id_panier           BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_utilisateur      BIGINT NOT NULL,
    statut              VARCHAR(30) NOT NULL DEFAULT 'ACTIF',
    date_creation       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    date_modification   TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT fk_panier_utilisateur
        FOREIGN KEY (id_utilisateur)
        REFERENCES utilisateur(id_utilisateur)
        ON DELETE CASCADE,

    CONSTRAINT ck_panier_statut
        CHECK (statut IN ('ACTIF', 'ABANDONNE', 'CONVERTI'))
);

-- Un seul panier ACTIF par utilisateur.
CREATE UNIQUE INDEX uq_panier_actif_utilisateur
    ON panier(id_utilisateur)
    WHERE statut = 'ACTIF';

CREATE TRIGGER trg_panier_date_modification
BEFORE UPDATE ON panier
FOR EACH ROW
EXECUTE FUNCTION fn_set_date_modification();


-- ============================================================
-- 20. LIGNES DE PANIER
-- ============================================================

CREATE TABLE ligne_panier (
    id_ligne_panier     BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_panier           BIGINT NOT NULL,
    id_offre            BIGINT NOT NULL,
    quantite            INTEGER NOT NULL DEFAULT 1,
    prix_unitaire       NUMERIC(12,2) NOT NULL,
    date_creation       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    date_modification   TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT fk_ligne_panier_panier
        FOREIGN KEY (id_panier)
        REFERENCES panier(id_panier)
        ON DELETE CASCADE,

    CONSTRAINT fk_ligne_panier_offre
        FOREIGN KEY (id_offre)
        REFERENCES offre_produit(id_offre)
        ON DELETE RESTRICT,

    CONSTRAINT uq_ligne_panier_offre
        UNIQUE (id_panier, id_offre),

    CONSTRAINT ck_ligne_panier_quantite
        CHECK (quantite > 0),

    CONSTRAINT ck_ligne_panier_prix
        CHECK (prix_unitaire >= 0)
);

CREATE TRIGGER trg_ligne_panier_date_modification
BEFORE UPDATE ON ligne_panier
FOR EACH ROW
EXECUTE FUNCTION fn_set_date_modification();


-- ============================================================
-- 21. COMMANDES
-- ============================================================

CREATE TABLE commande (
    id_commande         BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_utilisateur      BIGINT NOT NULL,
    reference           VARCHAR(50) NOT NULL,
    sous_total          NUMERIC(12,2) NOT NULL DEFAULT 0,
    remise              NUMERIC(12,2) NOT NULL DEFAULT 0,
    frais_livraison     NUMERIC(12,2) NOT NULL DEFAULT 0,
    total               NUMERIC(12,2) NOT NULL DEFAULT 0,
    mode_reception      VARCHAR(30) NOT NULL,
    statut              VARCHAR(40) NOT NULL DEFAULT 'EN_ATTENTE_PAIEMENT',
    date_creation       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    date_modification   TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT fk_commande_utilisateur
        FOREIGN KEY (id_utilisateur)
        REFERENCES utilisateur(id_utilisateur)
        ON DELETE RESTRICT,

    CONSTRAINT uq_commande_reference
        UNIQUE (reference),

    CONSTRAINT ck_commande_montants
        CHECK (
            sous_total >= 0
            AND remise >= 0
            AND frais_livraison >= 0
            AND total >= 0
        ),

    CONSTRAINT ck_commande_mode_reception
        CHECK (mode_reception IN ('LIVRAISON', 'RETRAIT_BOUTIQUE')),

    CONSTRAINT ck_commande_statut
        CHECK (statut IN (
            'EN_ATTENTE_PAIEMENT',
            'PAYEE',
            'EN_PREPARATION',
            'PRETE',
            'EXPEDIEE',
            'LIVREE',
            'RETIRÉE',
            'ANNULEE',
            'REMBOURSEE'
        ))
);

CREATE INDEX idx_commande_utilisateur
    ON commande(id_utilisateur);

CREATE INDEX idx_commande_statut
    ON commande(statut);

CREATE TRIGGER trg_commande_date_modification
BEFORE UPDATE ON commande
FOR EACH ROW
EXECUTE FUNCTION fn_set_date_modification();


-- ============================================================
-- 22. LIGNES DE COMMANDE
-- ============================================================
-- SNAPSHOT HISTORIQUE.
-- On garde volontairement le nom/prix au moment de l'achat.
-- Une modification future du catalogue ne doit pas modifier
-- l'historique d'une ancienne commande.

CREATE TABLE ligne_commande (
    id_ligne_commande   BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_commande         BIGINT NOT NULL,
    id_offre            BIGINT,
    nom_produit         VARCHAR(255) NOT NULL,
    nom_variante        VARCHAR(255),
    type_offre          VARCHAR(30) NOT NULL,
    prix_unitaire       NUMERIC(12,2) NOT NULL,
    quantite            INTEGER NOT NULL,
    remise              NUMERIC(12,2) NOT NULL DEFAULT 0,
    total               NUMERIC(12,2) NOT NULL,

    CONSTRAINT fk_ligne_commande_commande
        FOREIGN KEY (id_commande)
        REFERENCES commande(id_commande)
        ON DELETE CASCADE,

    CONSTRAINT fk_ligne_commande_offre
        FOREIGN KEY (id_offre)
        REFERENCES offre_produit(id_offre)
        ON DELETE SET NULL,

    CONSTRAINT ck_ligne_commande_quantite
        CHECK (quantite > 0),

    CONSTRAINT ck_ligne_commande_montants
        CHECK (prix_unitaire >= 0 AND remise >= 0 AND total >= 0),

    CONSTRAINT ck_ligne_commande_type
        CHECK (type_offre IN ('NEUF', 'OCCASION'))
);


-- ============================================================
-- 23. ADRESSES DE COMMANDE
-- ============================================================
-- SNAPSHOT historique : cette adresse doit rester celle utilisée
-- au moment de la commande, même si le client modifie son profil.

CREATE TABLE adresse_commande (
    id_adresse_commande BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_commande         BIGINT NOT NULL,
    nom_destinataire    VARCHAR(200) NOT NULL,
    telephone           VARCHAR(30) NOT NULL,
    ville_nom           VARCHAR(100) NOT NULL,
    ville_code          VARCHAR(20),
    quartier            VARCHAR(150) NOT NULL,
    adresse_detail      TEXT NOT NULL,
    point_repere        VARCHAR(255),
    instructions        TEXT,

    CONSTRAINT fk_adresse_commande_commande
        FOREIGN KEY (id_commande)
        REFERENCES commande(id_commande)
        ON DELETE CASCADE,

    CONSTRAINT uq_adresse_commande_commande
        UNIQUE (id_commande)
);


-- ============================================================
-- 24. TARIFS DE LIVRAISON
-- ============================================================

CREATE TABLE tarif_livraison (
    id_tarif            BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_ville            BIGINT NOT NULL,
    montant             NUMERIC(12,2) NOT NULL,
    date_debut          TIMESTAMPTZ NOT NULL,
    date_fin            TIMESTAMPTZ,
    actif               BOOLEAN NOT NULL DEFAULT TRUE,

    CONSTRAINT fk_tarif_livraison_ville
        FOREIGN KEY (id_ville)
        REFERENCES ville(id_ville)
        ON DELETE RESTRICT,

    CONSTRAINT ck_tarif_livraison_montant
        CHECK (montant >= 0),

    CONSTRAINT ck_tarif_livraison_dates
        CHECK (date_fin IS NULL OR date_fin > date_debut)
);

CREATE INDEX idx_tarif_livraison_ville
    ON tarif_livraison(id_ville);


-- ============================================================
-- 25. LIVRAISONS
-- ============================================================

CREATE TABLE livraison (
    id_livraison        BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_commande         BIGINT NOT NULL,
    id_tarif            BIGINT,
    frais               NUMERIC(12,2) NOT NULL DEFAULT 0,
    statut              VARCHAR(30) NOT NULL DEFAULT 'EN_ATTENTE',
    date_creation       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    date_expedition     TIMESTAMPTZ,
    date_livraison      TIMESTAMPTZ,

    CONSTRAINT fk_livraison_commande
        FOREIGN KEY (id_commande)
        REFERENCES commande(id_commande)
        ON DELETE CASCADE,

    CONSTRAINT fk_livraison_tarif
        FOREIGN KEY (id_tarif)
        REFERENCES tarif_livraison(id_tarif)
        ON DELETE SET NULL,

    CONSTRAINT uq_livraison_commande
        UNIQUE (id_commande),

    CONSTRAINT ck_livraison_frais
        CHECK (frais >= 0),

    CONSTRAINT ck_livraison_statut
        CHECK (statut IN (
            'EN_ATTENTE',
            'PREPARATION',
            'EXPEDIEE',
            'EN_TRANSIT',
            'LIVREE',
            'ANNULEE'
        ))
);

CREATE INDEX idx_livraison_statut
    ON livraison(statut);


-- ============================================================
-- 26. HISTORIQUE LIVRAISON
-- ============================================================

CREATE TABLE historique_livraison (
    id_historique      BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_livraison       BIGINT NOT NULL,
    ancien_statut      VARCHAR(30),
    nouveau_statut     VARCHAR(30) NOT NULL,
    commentaire        TEXT,
    date_changement    TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT fk_historique_livraison
        FOREIGN KEY (id_livraison)
        REFERENCES livraison(id_livraison)
        ON DELETE CASCADE
);

CREATE INDEX idx_historique_livraison_date
    ON historique_livraison(id_livraison, date_changement);


-- ============================================================
-- 27. MOYENS DE PAIEMENT
-- ============================================================

CREATE TABLE moyen_paiement (
    id_moyen_paiement   BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    nom                 VARCHAR(100) NOT NULL,
    code                VARCHAR(50) NOT NULL,
    description         TEXT,
    actif               BOOLEAN NOT NULL DEFAULT TRUE,
    date_creation       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    date_modification   TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT uq_moyen_paiement_code UNIQUE (code)
);

CREATE TRIGGER trg_moyen_paiement_date_modification
BEFORE UPDATE ON moyen_paiement
FOR EACH ROW
EXECUTE FUNCTION fn_set_date_modification();


-- ============================================================
-- 28. RÉPARATIONS
-- ============================================================

CREATE TABLE reparation (
    id_reparation          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_utilisateur         BIGINT,
    reference              VARCHAR(50) NOT NULL,
    nom_client             VARCHAR(200) NOT NULL,
    telephone_client       VARCHAR(30) NOT NULL,
    email_client            VARCHAR(255),
    source_demande         VARCHAR(30) NOT NULL DEFAULT 'BOUTIQUE',
    type_prise_en_charge   VARCHAR(30) NOT NULL DEFAULT 'DEPOT',
    statut                 VARCHAR(40) NOT NULL DEFAULT 'RECUE',
    date_reception         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    date_cloture           TIMESTAMPTZ,
    commentaire            TEXT,

    CONSTRAINT fk_reparation_utilisateur
        FOREIGN KEY (id_utilisateur)
        REFERENCES utilisateur(id_utilisateur)
        ON DELETE SET NULL,

    CONSTRAINT uq_reparation_reference
        UNIQUE (reference),

    CONSTRAINT ck_reparation_source
        CHECK (source_demande IN ('BOUTIQUE', 'SITE_WEB', 'TELEPHONE', 'AUTRE')),

    CONSTRAINT ck_reparation_prise
        CHECK (type_prise_en_charge IN ('DEPOT', 'COLLECTE')),

    CONSTRAINT ck_reparation_statut
        CHECK (statut IN (
            'RECUE',
            'DIAGNOSTIC',
            'DEVIS_EN_ATTENTE',
            'DEVIS_ENVOYE',
            'DEVIS_ACCEPTE',
            'DEVIS_REFUSE',
            'EN_REPARATION',
            'TEST',
            'PRETE',
            'EN_ATTENTE_RESTITUTION',
            'RESTITUEE',
            'ANNULEE'
        ))
);

CREATE INDEX idx_reparation_utilisateur
    ON reparation(id_utilisateur);

CREATE INDEX idx_reparation_statut
    ON reparation(statut);


-- ============================================================
-- 29. APPAREILS EN RÉPARATION
-- ============================================================

CREATE TABLE appareil_reparation (
    id_appareil_reparation BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_reparation          BIGINT NOT NULL,
    marque                 VARCHAR(100) NOT NULL,
    modele                 VARCHAR(150) NOT NULL,
    imei                   VARCHAR(50),
    numero_serie           VARCHAR(100),
    couleur                VARCHAR(50),
    etat_physique_entree   TEXT NOT NULL,
    accessoires_deposes    TEXT,
    motif_depot            TEXT NOT NULL,
    code_verrouillage      VARCHAR(255),
    date_creation          TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT fk_appareil_reparation
        FOREIGN KEY (id_reparation)
        REFERENCES reparation(id_reparation)
        ON DELETE CASCADE,

    CONSTRAINT uq_appareil_reparation
        UNIQUE (id_reparation)
);

-- ============================================================
-- 30. DIAGNOSTICS
-- ============================================================
-- Une réparation peut avoir plusieurs diagnostics historisés.
-- C'est volontaire : un diagnostic complémentaire ne détruit
-- pas le diagnostic initial.

CREATE TABLE diagnostic (
    id_diagnostic        BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_reparation        BIGINT NOT NULL,
    id_technicien        BIGINT,
    description_probleme TEXT NOT NULL,
    constat              TEXT NOT NULL,
    recommandation       TEXT,
    cout_estime          NUMERIC(12,2),
    date_diagnostic      TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT fk_diagnostic_reparation
        FOREIGN KEY (id_reparation)
        REFERENCES reparation(id_reparation)
        ON DELETE CASCADE,

    CONSTRAINT fk_diagnostic_technicien
        FOREIGN KEY (id_technicien)
        REFERENCES utilisateur(id_utilisateur)
        ON DELETE SET NULL,

    CONSTRAINT ck_diagnostic_cout
        CHECK (cout_estime IS NULL OR cout_estime >= 0)
);

CREATE INDEX idx_diagnostic_reparation
    ON diagnostic(id_reparation);


-- ============================================================
-- 31. DEVIS
-- ============================================================

CREATE TABLE devis (
    id_devis             BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_reparation        BIGINT NOT NULL,
    reference             VARCHAR(50) NOT NULL,
    sous_total            NUMERIC(12,2) NOT NULL DEFAULT 0,
    frais_collecte        NUMERIC(12,2) NOT NULL DEFAULT 0,
    remise                NUMERIC(12,2) NOT NULL DEFAULT 0,
    total                 NUMERIC(12,2) NOT NULL DEFAULT 0,
    statut                VARCHAR(30) NOT NULL DEFAULT 'BROUILLON',
    date_creation        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    date_envoi            TIMESTAMPTZ,
    date_acceptation     TIMESTAMPTZ,
    date_expiration      TIMESTAMPTZ,

    CONSTRAINT fk_devis_reparation
        FOREIGN KEY (id_reparation)
        REFERENCES reparation(id_reparation)
        ON DELETE CASCADE,

    CONSTRAINT uq_devis_reference
        UNIQUE (reference),

    CONSTRAINT ck_devis_montants
        CHECK (
            sous_total >= 0
            AND frais_collecte >= 0
            AND remise >= 0
            AND total >= 0
        ),

    CONSTRAINT ck_devis_statut
        CHECK (statut IN (
            'BROUILLON',
            'ENVOYE',
            'ACCEPTE',
            'REFUSE',
            'EXPIRE',
            'ANNULE'
        ))
);

CREATE INDEX idx_devis_reparation
    ON devis(id_reparation);

CREATE INDEX idx_devis_statut
    ON devis(statut);

-- Une réparation ne peut avoir qu'un seul devis accepté à la fois.
CREATE UNIQUE INDEX uq_devis_un_seul_accepte
    ON devis(id_reparation)
    WHERE statut = 'ACCEPTE';


-- ============================================================
-- 32. LIGNES DE DEVIS
-- ============================================================

CREATE TABLE ligne_devis (
    id_ligne_devis      BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_devis            BIGINT NOT NULL,
    designation         VARCHAR(255) NOT NULL,
    type_ligne          VARCHAR(30) NOT NULL,
    quantite            INTEGER NOT NULL DEFAULT 1,
    prix_unitaire       NUMERIC(12,2) NOT NULL,
    remise              NUMERIC(12,2) NOT NULL DEFAULT 0,
    total               NUMERIC(12,2) NOT NULL,

    CONSTRAINT fk_ligne_devis_devis
        FOREIGN KEY (id_devis)
        REFERENCES devis(id_devis)
        ON DELETE CASCADE,

    CONSTRAINT ck_ligne_devis_type
        CHECK (type_ligne IN ('MAIN_D_OEUVRE', 'PIECE', 'SERVICE', 'AUTRE')),

    CONSTRAINT ck_ligne_devis_quantite
        CHECK (quantite > 0),

    CONSTRAINT ck_ligne_devis_montants
        CHECK (prix_unitaire >= 0 AND remise >= 0 AND total >= 0)
);


-- ============================================================
-- 33. PIÈCES UTILISÉES
-- ============================================================
-- Nous gardons volontairement un registre simple des pièces
-- effectivement utilisées pendant la réparation.

CREATE TABLE piece_utilisee (
    id_piece_utilisee   BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_reparation       BIGINT NOT NULL,
    designation         VARCHAR(255) NOT NULL,
    reference_piece     VARCHAR(100),
    quantite            INTEGER NOT NULL DEFAULT 1,
    cout_unitaire       NUMERIC(12,2),
    observation         TEXT,
    date_utilisation    TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT fk_piece_utilisee_reparation
        FOREIGN KEY (id_reparation)
        REFERENCES reparation(id_reparation)
        ON DELETE CASCADE,

    CONSTRAINT ck_piece_utilisee_quantite
        CHECK (quantite > 0),

    CONSTRAINT ck_piece_utilisee_cout
        CHECK (cout_unitaire IS NULL OR cout_unitaire >= 0)
);


-- ============================================================
-- 34. TESTS DE RÉPARATION
-- ============================================================

CREATE TABLE test_reparation (
    id_test              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_reparation        BIGINT NOT NULL,
    id_technicien        BIGINT,
    type_test            VARCHAR(100) NOT NULL,
    resultat             VARCHAR(30) NOT NULL,
    commentaire          TEXT,
    date_test            TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT fk_test_reparation
        FOREIGN KEY (id_reparation)
        REFERENCES reparation(id_reparation)
        ON DELETE CASCADE,

    CONSTRAINT fk_test_technicien
        FOREIGN KEY (id_technicien)
        REFERENCES utilisateur(id_utilisateur)
        ON DELETE SET NULL,

    CONSTRAINT ck_test_resultat
        CHECK (resultat IN ('REUSSI', 'ECHOUE', 'NON_TESTE'))
);


-- ============================================================
-- 35. ADRESSES DE COLLECTE RÉPARATION
-- ============================================================

CREATE TABLE adresse_collecte_reparation (
    id_adresse_collecte BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_reparation      BIGINT NOT NULL,
    nom_contact        VARCHAR(200) NOT NULL,
    telephone          VARCHAR(30) NOT NULL,
    ville_nom          VARCHAR(100) NOT NULL,
    quartier           VARCHAR(150) NOT NULL,
    adresse_detail     TEXT NOT NULL,
    point_repere       VARCHAR(255),
    instructions       TEXT,

    CONSTRAINT fk_adresse_collecte_reparation
        FOREIGN KEY (id_reparation)
        REFERENCES reparation(id_reparation)
        ON DELETE CASCADE,

    CONSTRAINT uq_adresse_collecte_reparation
        UNIQUE (id_reparation)
);


-- ============================================================
-- 36. COLLECTES DE RÉPARATION
-- ============================================================

CREATE TABLE collecte_reparation (
    id_collecte          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_reparation        BIGINT NOT NULL,
    id_adresse_collecte  BIGINT NOT NULL,
    id_tarif_collecte    BIGINT,
    frais                NUMERIC(12,2) NOT NULL DEFAULT 0,
    statut               VARCHAR(30) NOT NULL DEFAULT 'EN_ATTENTE',
    date_demande         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    date_collecte_prevue TIMESTAMPTZ,
    date_collecte_effectuee TIMESTAMPTZ,
    commentaire          TEXT,

    CONSTRAINT fk_collecte_reparation
        FOREIGN KEY (id_reparation)
        REFERENCES reparation(id_reparation)
        ON DELETE CASCADE,

    CONSTRAINT fk_collecte_adresse
        FOREIGN KEY (id_adresse_collecte)
        REFERENCES adresse_collecte_reparation(id_adresse_collecte)
        ON DELETE RESTRICT,

    CONSTRAINT ck_collecte_frais
        CHECK (frais >= 0),

    CONSTRAINT ck_collecte_statut
        CHECK (statut IN (
            'EN_ATTENTE',
            'PLANIFIEE',
            'EN_COURS',
            'EFFECTUEE',
            'ANNULEE',
            'ECHEC'
        )),

    CONSTRAINT uq_collecte_reparation
        UNIQUE (id_reparation)
);


-- ============================================================
-- 37. TARIFS DE COLLECTE RÉPARATION
-- ============================================================

CREATE TABLE tarif_collecte_reparation (
    id_tarif_collecte   BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_ville            BIGINT NOT NULL,
    montant             NUMERIC(12,2) NOT NULL,
    date_debut          TIMESTAMPTZ NOT NULL,
    date_fin            TIMESTAMPTZ,
    actif               BOOLEAN NOT NULL DEFAULT TRUE,

    CONSTRAINT fk_tarif_collecte_ville
        FOREIGN KEY (id_ville)
        REFERENCES ville(id_ville)
        ON DELETE RESTRICT,

    CONSTRAINT ck_tarif_collecte_montant
        CHECK (montant >= 0),

    CONSTRAINT ck_tarif_collecte_dates
        CHECK (date_fin IS NULL OR date_fin > date_debut)
);

CREATE INDEX idx_tarif_collecte_ville
    ON tarif_collecte_reparation(id_ville);


-- ============================================================
-- 38. PAIEMENTS
-- ============================================================
-- Un paiement appartient SOIT à une commande, SOIT à une
-- réparation. Jamais aux deux.
--
-- type_paiement permet de distinguer :
--   - PAIEMENT_COMPLET : couvre exactement le reste dû.
--   - ACOMPTE : paiement partiel d'une réparation.
--   - SOLDE : couvre exactement le reste dû d'une réparation.

CREATE TABLE paiement (
    id_paiement         BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_commande         BIGINT,
    id_reparation       BIGINT,
    id_moyen_paiement   BIGINT NOT NULL,
    reference_interne  VARCHAR(100) NOT NULL,
    reference_externe  VARCHAR(150),
    montant             NUMERIC(12,2) NOT NULL,
    statut              VARCHAR(30) NOT NULL DEFAULT 'EN_ATTENTE',
    contexte            VARCHAR(30) NOT NULL,
    type_paiement       VARCHAR(30) NOT NULL,
    date_creation       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    date_confirmation  TIMESTAMPTZ,

    CONSTRAINT fk_paiement_commande
        FOREIGN KEY (id_commande)
        REFERENCES commande(id_commande)
        ON DELETE RESTRICT,

    CONSTRAINT fk_paiement_reparation
        FOREIGN KEY (id_reparation)
        REFERENCES reparation(id_reparation)
        ON DELETE RESTRICT,

    CONSTRAINT fk_paiement_moyen
        FOREIGN KEY (id_moyen_paiement)
        REFERENCES moyen_paiement(id_moyen_paiement)
        ON DELETE RESTRICT,

    CONSTRAINT uq_paiement_reference_interne
        UNIQUE (reference_interne),

    CONSTRAINT ck_paiement_montant
        CHECK (montant > 0),

    CONSTRAINT ck_paiement_statut
        CHECK (statut IN (
            'EN_ATTENTE',
            'REUSSI',
            'ECHOUE',
            'ANNULE',
            'EXPIRE'
        )),

    CONSTRAINT ck_paiement_contexte
        CHECK (contexte IN ('COMMANDE', 'REPARATION')),

    CONSTRAINT ck_paiement_type
        CHECK (type_paiement IN (
            'PAIEMENT_COMPLET',
            'ACOMPTE',
            'SOLDE'
        )),

    -- Règle XOR : exactement une cible.
    CONSTRAINT ck_paiement_cible_xor
        CHECK (
            (id_commande IS NOT NULL AND id_reparation IS NULL)
            OR
            (id_commande IS NULL AND id_reparation IS NOT NULL)
        ),

    -- Le contexte doit correspondre à la cible.
    CONSTRAINT ck_paiement_contexte_cible
        CHECK (
            (contexte = 'COMMANDE' AND id_commande IS NOT NULL)
            OR
            (contexte = 'REPARATION' AND id_reparation IS NOT NULL)
        )
);

CREATE INDEX idx_paiement_commande
    ON paiement(id_commande);

CREATE INDEX idx_paiement_reparation
    ON paiement(id_reparation);

CREATE INDEX idx_paiement_statut
    ON paiement(statut);


-- ============================================================
-- 39. REMBOURSEMENTS
-- ============================================================

CREATE TABLE remboursement (
    id_remboursement    BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_paiement         BIGINT NOT NULL,
    montant             NUMERIC(12,2) NOT NULL,
    motif               TEXT NOT NULL,
    statut              VARCHAR(30) NOT NULL DEFAULT 'EN_ATTENTE',
    reference_externe   VARCHAR(150),
    date_creation       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    date_traitement     TIMESTAMPTZ,

    CONSTRAINT fk_remboursement_paiement
        FOREIGN KEY (id_paiement)
        REFERENCES paiement(id_paiement)
        ON DELETE RESTRICT,

    CONSTRAINT ck_remboursement_montant
        CHECK (montant > 0),

    CONSTRAINT ck_remboursement_statut
        CHECK (statut IN (
            'EN_ATTENTE',
            'TRAITE',
            'ECHOUE',
            'ANNULE'
        ))
);


-- ============================================================
-- 40. PROMOTIONS
-- ============================================================

CREATE TABLE promotion (
    id_promotion          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    nom                   VARCHAR(150) NOT NULL,
    code                  VARCHAR(50),
    description           TEXT,
    type_promotion        VARCHAR(30) NOT NULL,
    valeur                NUMERIC(12,2) NOT NULL,
    montant_minimum      NUMERIC(12,2),
    date_debut            TIMESTAMPTZ NOT NULL,
    date_fin              TIMESTAMPTZ NOT NULL,
    utilisation_max       INTEGER,
    utilisation_actuelle INTEGER NOT NULL DEFAULT 0,
    actif                 BOOLEAN NOT NULL DEFAULT TRUE,
    date_creation         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    date_modification     TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT uq_promotion_code
        UNIQUE (code),

    CONSTRAINT ck_promotion_type
        CHECK (type_promotion IN ('POURCENTAGE', 'MONTANT_FIXE')),

    CONSTRAINT ck_promotion_valeur
        CHECK (valeur >= 0),

    CONSTRAINT ck_promotion_minimum
        CHECK (montant_minimum IS NULL OR montant_minimum >= 0),

    CONSTRAINT ck_promotion_dates
        CHECK (date_fin > date_debut),

    CONSTRAINT ck_promotion_utilisation
        CHECK (
            utilisation_max IS NULL OR utilisation_max > 0
        ),

    CONSTRAINT ck_promotion_utilisation_actuelle
        CHECK (utilisation_actuelle >= 0),

    CONSTRAINT ck_promotion_pourcentage
        CHECK (
            type_promotion <> 'POURCENTAGE'
            OR valeur <= 100
        )
);

CREATE TRIGGER trg_promotion_date_modification
BEFORE UPDATE ON promotion
FOR EACH ROW
EXECUTE FUNCTION fn_set_date_modification();


-- ============================================================
-- 41. PROMOTION_OFFRE
-- ============================================================

CREATE TABLE promotion_offre (
    id_promotion       BIGINT NOT NULL,
    id_offre           BIGINT NOT NULL,

    PRIMARY KEY (id_promotion, id_offre),

    CONSTRAINT fk_promotion_offre_promotion
        FOREIGN KEY (id_promotion)
        REFERENCES promotion(id_promotion)
        ON DELETE CASCADE,

    CONSTRAINT fk_promotion_offre_offre
        FOREIGN KEY (id_offre)
        REFERENCES offre_produit(id_offre)
        ON DELETE CASCADE
);


-- ============================================================
-- 42. NOTIFICATIONS
-- ============================================================

CREATE TABLE notification (
    id_notification    BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_utilisateur     BIGINT NOT NULL,
    type               VARCHAR(50) NOT NULL,
    titre              VARCHAR(255) NOT NULL,
    message            TEXT NOT NULL,
    lue                BOOLEAN NOT NULL DEFAULT FALSE,
    date_lecture       TIMESTAMPTZ,
    date_creation      TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT fk_notification_utilisateur
        FOREIGN KEY (id_utilisateur)
        REFERENCES utilisateur(id_utilisateur)
        ON DELETE CASCADE
);

CREATE INDEX idx_notification_utilisateur_lue
    ON notification(id_utilisateur, lue);


-- ============================================================
-- 43. JOURNAL D'ACTIONS
-- ============================================================
-- Journal d'audit administratif.
-- JSONB permet de conserver l'ancien et le nouvel état d'une
-- donnée sans créer une table d'historique pour chaque objet.

CREATE TABLE journal_action (
    id_action           BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_utilisateur      BIGINT,
    action              VARCHAR(100) NOT NULL,
    table_cible         VARCHAR(100),
    id_cible            BIGINT,
    ancienne_valeur     JSONB,
    nouvelle_valeur     JSONB,
    adresse_ip          INET,
    user_agent          TEXT,
    date_action         TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT fk_journal_utilisateur
        FOREIGN KEY (id_utilisateur)
        REFERENCES utilisateur(id_utilisateur)
        ON DELETE SET NULL
);

CREATE INDEX idx_journal_utilisateur
    ON journal_action(id_utilisateur);

CREATE INDEX idx_journal_cible
    ON journal_action(table_cible, id_cible);

CREATE INDEX idx_journal_date
    ON journal_action(date_action);


-- ============================================================
-- 44. INDEX COMPLÉMENTAIRES
-- ============================================================
-- Les FK sont souvent utilisées dans les JOIN.
-- Ces index ne changent pas les règles métier ; ils améliorent
-- principalement les recherches et les performances.

CREATE INDEX idx_produit_categorie_categorie
    ON produit_categorie(id_categorie);

CREATE INDEX idx_variante_caracteristique_caracteristique
    ON variante_caracteristique(id_caracteristique);

CREATE INDEX idx_promotion_offre_offre
    ON promotion_offre(id_offre);

CREATE INDEX idx_ligne_commande_commande
    ON ligne_commande(id_commande);

CREATE INDEX idx_ligne_panier_panier
    ON ligne_panier(id_panier);

CREATE INDEX idx_ligne_devis_devis
    ON ligne_devis(id_devis);

CREATE INDEX idx_piece_utilisee_reparation
    ON piece_utilisee(id_reparation);

CREATE INDEX idx_test_reparation_reparation
    ON test_reparation(id_reparation);

CREATE INDEX idx_collecte_reparation_statut
    ON collecte_reparation(statut);

CREATE INDEX idx_remboursement_paiement
    ON remboursement(id_paiement);


-- ============================================================
-- 45. CONTRAINTES MÉTIER AVANCÉES
-- ============================================================

-- ------------------------------------------------------------
-- 45.1 Une commande ne peut avoir une livraison que si elle
--      utilise le mode LIVRAISON.
-- ------------------------------------------------------------

CREATE OR REPLACE FUNCTION fn_verifier_livraison_commande()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
DECLARE
    v_mode VARCHAR(30);
BEGIN
    SELECT mode_reception
    INTO v_mode
    FROM commande
    WHERE id_commande = NEW.id_commande;

    IF v_mode <> 'LIVRAISON' THEN
        RAISE EXCEPTION
            'La commande % n''est pas configurée pour une livraison.',
            NEW.id_commande;
    END IF;

    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_verifier_livraison_commande
BEFORE INSERT OR UPDATE ON livraison
FOR EACH ROW
EXECUTE FUNCTION fn_verifier_livraison_commande();


-- ------------------------------------------------------------
-- 45.2 Une collecte ne doit exister que pour une réparation
--      configurée en mode COLLECTE.
-- ------------------------------------------------------------

CREATE OR REPLACE FUNCTION fn_verifier_collecte_reparation()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
DECLARE
    v_type VARCHAR(30);
BEGIN
    SELECT type_prise_en_charge
    INTO v_type
    FROM reparation
    WHERE id_reparation = NEW.id_reparation;

    IF v_type <> 'COLLECTE' THEN
        RAISE EXCEPTION
            'La réparation % n''est pas configurée pour une collecte.',
            NEW.id_reparation;
    END IF;

    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_verifier_collecte_reparation
BEFORE INSERT OR UPDATE ON collecte_reparation
FOR EACH ROW
EXECUTE FUNCTION fn_verifier_collecte_reparation();


-- ------------------------------------------------------------
-- 45.3 Une réparation ne peut passer à EN_REPARATION que si
--      un devis est accepté ET qu'un paiement réussi existe.
-- ------------------------------------------------------------
CREATE OR REPLACE FUNCTION fn_verifier_statut_reparation()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
DECLARE
    v_devis_accepte BOOLEAN;
    v_paiement_reussi BOOLEAN;
BEGIN
    IF NEW.statut = 'EN_REPARATION' THEN
        SELECT EXISTS (
            SELECT 1
            FROM devis d
            WHERE d.id_reparation = NEW.id_reparation
              AND d.statut = 'ACCEPTE'
        )
        INTO v_devis_accepte;

        IF NOT v_devis_accepte THEN
            RAISE EXCEPTION
                'La réparation % ne peut passer à EN_REPARATION sans devis accepté.',
                NEW.id_reparation;
        END IF;

        SELECT EXISTS (
            SELECT 1
            FROM paiement p
            WHERE p.id_reparation = NEW.id_reparation
              AND p.statut = 'REUSSI'
        )
        INTO v_paiement_reussi;

        IF NOT v_paiement_reussi THEN
            RAISE EXCEPTION
                'La réparation % ne peut passer à EN_REPARATION sans paiement réussi.',
                NEW.id_reparation;
        END IF;
    END IF;

    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_verifier_statut_reparation
BEFORE UPDATE ON reparation
FOR EACH ROW
EXECUTE FUNCTION fn_verifier_statut_reparation();


-- ------------------------------------------------------------
-- 45.4 Le montant remboursé ne doit jamais dépasser le montant
--      du paiement d'origine, et un remboursement ne peut être
--      créé que pour un paiement réussi.
-- ------------------------------------------------------------
CREATE OR REPLACE FUNCTION fn_verifier_remboursement()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
DECLARE
    v_paiement NUMERIC(12,2);
    v_statut_paiement VARCHAR(30);
    v_deja_rembourse NUMERIC(12,2);
BEGIN
    SELECT montant, statut
    INTO v_paiement, v_statut_paiement
    FROM paiement
    WHERE id_paiement = NEW.id_paiement
    FOR UPDATE;

    IF v_statut_paiement <> 'REUSSI' THEN
        RAISE EXCEPTION
            'Le paiement % doit être REUSSI avant tout remboursement.',
            NEW.id_paiement;
    END IF;

    SELECT COALESCE(SUM(montant), 0)
    INTO v_deja_rembourse
    FROM remboursement
    WHERE id_paiement = NEW.id_paiement
      AND id_remboursement <> COALESCE(NEW.id_remboursement, -1)
      AND statut <> 'ANNULE';

    IF v_deja_rembourse + NEW.montant > v_paiement THEN
        RAISE EXCEPTION
            'Le remboursement dépasse le montant du paiement %. Déjà remboursé: %, nouveau remboursement: %, paiement: %.',
            NEW.id_paiement, v_deja_rembourse, NEW.montant, v_paiement;
    END IF;

    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_verifier_remboursement
BEFORE INSERT OR UPDATE ON remboursement
FOR EACH ROW
EXECUTE FUNCTION fn_verifier_remboursement();


-- ------------------------------------------------------------
-- 45.5 Contrôle des paiements réussis.
--      Le cumul des paiements réussis ne doit jamais dépasser
--      le montant dû de la commande ou du devis accepté.
--      Un verrou transactionnel est utilisé pour éviter qu'un
--      paiement concurrent ne fasse dépasser le plafond.
-- ------------------------------------------------------------
CREATE OR REPLACE FUNCTION fn_verifier_paiement()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
DECLARE
    v_montant_du NUMERIC(12,2);
    v_deja_paye NUMERIC(12,2);
    v_reste NUMERIC(12,2);
BEGIN
    -- Les paiements non réussis ne consomment pas le montant dû.
    IF NEW.statut <> 'REUSSI' THEN
        RETURN NEW;
    END IF;

    IF NEW.id_commande IS NOT NULL THEN
        -- Verrouille la commande pendant cette transaction afin de
        -- sécuriser le calcul en cas de deux paiements simultanés.
        PERFORM pg_advisory_xact_lock(hashtextextended('commande:' || NEW.id_commande::TEXT, 0));

        SELECT total
        INTO v_montant_du
        FROM commande
        WHERE id_commande = NEW.id_commande;

        SELECT COALESCE(SUM(montant), 0)
        INTO v_deja_paye
        FROM paiement
        WHERE id_commande = NEW.id_commande
          AND statut = 'REUSSI'
          AND id_paiement <> COALESCE(NEW.id_paiement, -1);

    ELSE
        PERFORM pg_advisory_xact_lock(hashtextextended('reparation:' || NEW.id_reparation::TEXT, 0));

        SELECT d.total
        INTO v_montant_du
        FROM devis d
        WHERE d.id_reparation = NEW.id_reparation
          AND d.statut = 'ACCEPTE';

        IF v_montant_du IS NULL THEN
            RAISE EXCEPTION
                'Impossible d''enregistrer le paiement : la réparation % ne possède pas de devis accepté.',
                NEW.id_reparation;
        END IF;

        SELECT COALESCE(SUM(montant), 0)
        INTO v_deja_paye
        FROM paiement
        WHERE id_reparation = NEW.id_reparation
          AND statut = 'REUSSI'
          AND id_paiement <> COALESCE(NEW.id_paiement, -1);
    END IF;

    v_reste := v_montant_du - v_deja_paye;

    IF NEW.montant > v_reste THEN
        RAISE EXCEPTION
            'Paiement refusé : montant %, reste à payer %. ',
            NEW.montant, v_reste;
    END IF;

    IF NEW.type_paiement = 'PAIEMENT_COMPLET' AND NEW.montant <> v_reste THEN
        RAISE EXCEPTION
            'Un PAIEMENT_COMPLET doit couvrir exactement le reste à payer (%). Montant reçu: %.',
            v_reste, NEW.montant;
    END IF;

    IF NEW.type_paiement = 'SOLDE' AND NEW.montant <> v_reste THEN
        RAISE EXCEPTION
            'Un paiement SOLDE doit couvrir exactement le reste à payer (%). Montant reçu: %.',
            v_reste, NEW.montant;
    END IF;

    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_verifier_paiement
BEFORE INSERT OR UPDATE ON paiement
FOR EACH ROW
EXECUTE FUNCTION fn_verifier_paiement();


-- ------------------------------------------------------------
-- 45.6 Une offre d'occasion doit pointer vers une unité dont
--      la variante correspond à celle de l'offre.
-- ------------------------------------------------------------
CREATE OR REPLACE FUNCTION fn_verifier_offre_unite_variante()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
DECLARE
    v_variante_unite BIGINT;
BEGIN
    IF NEW.type_offre = 'OCCASION' THEN
        SELECT id_variante
        INTO v_variante_unite
        FROM unite_produit
        WHERE id_unite_produit = NEW.id_unite_produit;

        IF v_variante_unite IS DISTINCT FROM NEW.id_variante THEN
            RAISE EXCEPTION
                'L''unité % n''appartient pas à la variante % de l''offre.',
                NEW.id_unite_produit, NEW.id_variante;
        END IF;
    END IF;

    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_verifier_offre_unite_variante
BEFORE INSERT OR UPDATE ON offre_produit
FOR EACH ROW
EXECUTE FUNCTION fn_verifier_offre_unite_variante();


-- ------------------------------------------------------------
-- 45.7 Un produit doit toujours avoir au moins une variante.
--      Le contrôle est différé à la fin de la transaction pour
--      permettre INSERT produit puis INSERT variante dans la
--      même transaction.
-- ------------------------------------------------------------
CREATE OR REPLACE FUNCTION fn_verifier_produit_avec_variante()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
DECLARE
    v_produit BIGINT;
BEGIN
    v_produit := CASE
        WHEN TG_OP = 'DELETE' THEN OLD.id_produit
        ELSE NEW.id_produit
    END;

    IF NOT EXISTS (
        SELECT 1
        FROM variante
        WHERE id_produit = v_produit
    ) THEN
        RAISE EXCEPTION
            'Le produit % doit posséder au moins une variante.',
            v_produit;
    END IF;

    IF TG_OP = 'DELETE' THEN
        RETURN OLD;
    END IF;
    RETURN NEW;
END;
$$;

CREATE CONSTRAINT TRIGGER trg_produit_doit_avoir_variante
AFTER INSERT OR UPDATE ON produit
DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW
EXECUTE FUNCTION fn_verifier_produit_avec_variante();

CREATE CONSTRAINT TRIGGER trg_variante_produit_non_vide
AFTER DELETE OR UPDATE ON variante
DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW
EXECUTE FUNCTION fn_verifier_produit_avec_variante();


-- ------------------------------------------------------------
-- 45.8 Cohérence livraison / mode de réception.
--      Une commande LIVRAISON doit posséder livraison + adresse.
--      Une commande RETRAIT_BOUTIQUE ne doit pas en posséder.
-- ------------------------------------------------------------
CREATE OR REPLACE FUNCTION fn_verifier_coherence_livraison_commande()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
DECLARE
    v_commande BIGINT;
    v_mode VARCHAR(30);
    v_livraison BOOLEAN;
    v_adresse BOOLEAN;
BEGIN
    v_commande := COALESCE(NEW.id_commande, OLD.id_commande);

    SELECT mode_reception
    INTO v_mode
    FROM commande
    WHERE id_commande = v_commande;

    SELECT EXISTS (SELECT 1 FROM livraison WHERE id_commande = v_commande)
    INTO v_livraison;

    SELECT EXISTS (SELECT 1 FROM adresse_commande WHERE id_commande = v_commande)
    INTO v_adresse;

    IF v_mode = 'LIVRAISON' AND (NOT v_livraison OR NOT v_adresse) THEN
        RAISE EXCEPTION
            'La commande % en mode LIVRAISON doit avoir une livraison et une adresse.',
            v_commande;
    END IF;

    IF v_mode = 'RETRAIT_BOUTIQUE' AND (v_livraison OR v_adresse) THEN
        RAISE EXCEPTION
            'La commande % en mode RETRAIT_BOUTIQUE ne doit avoir ni livraison ni adresse de livraison.',
            v_commande;
    END IF;

    IF TG_OP = 'DELETE' THEN
        RETURN OLD;
    END IF;
    RETURN NEW;
END;
$$;

CREATE CONSTRAINT TRIGGER trg_coherence_livraison_commande
AFTER INSERT OR UPDATE ON commande
DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW
EXECUTE FUNCTION fn_verifier_coherence_livraison_commande();

CREATE CONSTRAINT TRIGGER trg_coherence_adresse_commande
AFTER INSERT OR UPDATE OR DELETE ON adresse_commande
DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW
EXECUTE FUNCTION fn_verifier_coherence_livraison_commande();

CREATE CONSTRAINT TRIGGER trg_coherence_livraison
AFTER INSERT OR UPDATE OR DELETE ON livraison
DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW
EXECUTE FUNCTION fn_verifier_coherence_livraison_commande();


-- ------------------------------------------------------------
-- 45.9 Cohérence collecte / type de prise en charge.
--      Une réparation COLLECTE doit avoir collecte + adresse.
--      Une réparation DEPOT ne doit pas en avoir.
-- ------------------------------------------------------------
CREATE OR REPLACE FUNCTION fn_verifier_coherence_collecte_reparation()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
DECLARE
    v_reparation BIGINT;
    v_type VARCHAR(30);
    v_collecte BOOLEAN;
    v_adresse BOOLEAN;
BEGIN
    v_reparation := COALESCE(NEW.id_reparation, OLD.id_reparation);

    SELECT type_prise_en_charge
    INTO v_type
    FROM reparation
    WHERE id_reparation = v_reparation;

    SELECT EXISTS (SELECT 1 FROM collecte_reparation WHERE id_reparation = v_reparation)
    INTO v_collecte;

    SELECT EXISTS (SELECT 1 FROM adresse_collecte_reparation WHERE id_reparation = v_reparation)
    INTO v_adresse;

    IF v_type = 'COLLECTE' AND (NOT v_collecte OR NOT v_adresse) THEN
        RAISE EXCEPTION
            'La réparation % en mode COLLECTE doit avoir une collecte et une adresse.',
            v_reparation;
    END IF;

    IF v_type = 'DEPOT' AND (v_collecte OR v_adresse) THEN
        RAISE EXCEPTION
            'La réparation % en mode DEPOT ne doit avoir ni collecte ni adresse de collecte.',
            v_reparation;
    END IF;

    IF TG_OP = 'DELETE' THEN
        RETURN OLD;
    END IF;
    RETURN NEW;
END;
$$;

CREATE CONSTRAINT TRIGGER trg_coherence_collecte_reparation
AFTER INSERT OR UPDATE ON reparation
DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW
EXECUTE FUNCTION fn_verifier_coherence_collecte_reparation();

CREATE CONSTRAINT TRIGGER trg_coherence_adresse_collecte
AFTER INSERT OR UPDATE OR DELETE ON adresse_collecte_reparation
DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW
EXECUTE FUNCTION fn_verifier_coherence_collecte_reparation();

CREATE CONSTRAINT TRIGGER trg_coherence_collecte
AFTER INSERT OR UPDATE OR DELETE ON collecte_reparation
DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW
EXECUTE FUNCTION fn_verifier_coherence_collecte_reparation();


-- ============================================================
-- 46. VALIDATION DES MONTANTS D'UNE COMMANDE
-- ============================================================
-- La formule :
--     total = sous_total - remise + frais_livraison
--
-- est suffisamment importante pour être contrôlée côté BDD.
-- Django devra également la contrôler avant l'enregistrement.

CREATE OR REPLACE FUNCTION fn_verifier_total_commande()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    IF NEW.total <> (NEW.sous_total - NEW.remise + NEW.frais_livraison) THEN
        RAISE EXCEPTION
            'Total commande invalide : attendu %, reçu %.',
            (NEW.sous_total - NEW.remise + NEW.frais_livraison),
            NEW.total;
    END IF;

    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_verifier_total_commande
BEFORE INSERT OR UPDATE ON commande
FOR EACH ROW
EXECUTE FUNCTION fn_verifier_total_commande();


-- ============================================================
-- 47. VALIDATION DU TOTAL D'UN DEVIS
-- ============================================================
-- Le total est :
--     sous_total + frais_collecte - remise

CREATE OR REPLACE FUNCTION fn_verifier_total_devis()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    IF NEW.total <> (NEW.sous_total + NEW.frais_collecte - NEW.remise) THEN
        RAISE EXCEPTION
            'Total devis invalide : attendu %, reçu %.',
            (NEW.sous_total + NEW.frais_collecte - NEW.remise),
            NEW.total;
    END IF;

    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_verifier_total_devis
BEFORE INSERT OR UPDATE ON devis
FOR EACH ROW
EXECUTE FUNCTION fn_verifier_total_devis();


-- ============================================================
-- 48. RÈGLES D'INITIALISATION
-- ============================================================
-- Données minimales nécessaires au fonctionnement du système.
-- Elles peuvent être enrichies depuis Django/Admin.

INSERT INTO etat_produit (code, nom, description)
VALUES
    ('NEUF', 'Neuf', 'Produit neuf'),
    ('COMME_NEUF', 'Comme neuf', 'Très bon état, proche du neuf'),
    ('TRES_BON_ETAT', 'Très bon état', 'Produit d’occasion en très bon état'),
    ('BON_ETAT', 'Bon état', 'Produit d’occasion présentant quelques traces normales'),
    ('ETAT_CORRECT', 'État correct', 'Produit fonctionnel avec traces visibles')
ON CONFLICT (code) DO NOTHING;


-- ============================================================
-- FIN DU SCHÉMA
-- ============================================================

COMMIT;
