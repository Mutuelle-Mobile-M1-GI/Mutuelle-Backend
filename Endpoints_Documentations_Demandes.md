# Documentation des Endpoints Demandés

Ce document détaille les endpoints pour la création d'une session, la récupération des informations complètes d'un membre, et la gestion de la solidarité.

## 1. Création d'une Session

**Endpoint :** `POST /api/core/sessions/`

**Description :** Permet de créer une nouvelle session. Si la nouvelle session est créée avec le statut `EN_COURS`, l'ancienne session en cours (pour le même exercice) sera automatiquement clôturée (statut défini à `TERMINEE`).

**Format de la Requête (Body JSON) :**
```json
{
  "exercice": "uuid-de-lexercice",
  "nom": "Session Avril 2026",
  "date_session": "2026-04-10",
  "montant_collation": "5000.00",
  "montant_autre_depense": "0.00",
  "motif_autre_depense": "",
  "statut": "EN_COURS",
  "description": "Session du mois d'avril"
}
```

**Informations Importantes :**
- **Permissions :** Seuls les administrateurs peuvent créer une session.
- Les autres champs de la session (comme `is_en_cours`, [nombre_membres_inscrits](file:///home/darren/Bureau/projet/Mutuelle-Backend/core/serializers.py#79-82), [total_solidarite_collectee](file:///home/darren/Bureau/projet/Mutuelle-Backend/core/serializers.py#83-92), [renflouements_generes](file:///home/darren/Bureau/projet/Mutuelle-Backend/core/serializers.py#93-99)) sont calculés automatiquement ou sont en lecture seule.

---

## 2. Informations Complètes du Membre

**Endpoint :** `GET /api/core/membres/{id}/donnees_completes/`

**Description :** Retourne **TOUTES** les données financières calculées pour un membre spécifique. C'est le point d'entrée principal pour le Frontend lorsqu'il veut afficher le tableau de bord d'un membre avec ses liquidités, épargnes, emprunts actuels, et son statut au sein de la mutuelle.

**Format de la Réponse :**
La réponse contient un objet JSON détaillé avec l'historique de ses paiements d'inscription, ses paiements de solidarité, son épargne cumulée, le solde de ses éventuels emprunts en cours, et s'il a des renflouements dus.

**Informations Importantes :**
- **Permissions :** Accessible à tous (selon la configuration).

---

## 3. Gestion de la Solidarité (Paiement de Solidarité)

Les endpoints standards sont générés par le routeur pour la gestion de la solidarité (ModelViewSet).

**Endpoint :** `GET /api/transactions/paiements-solidarite/`
- **Description :** Liste tous les paiements de solidarité.
- **Filtres disponibles :** [membre](file:///home/darren/Bureau/projet/Mutuelle-Backend/transactions/views.py#980-1077) (UUID), `membre_numero`, [membre_nom](file:///home/darren/Bureau/projet/Mutuelle-Backend/transactions/views.py#90-95), [session](file:///home/darren/Bureau/projet/Mutuelle-Backend/core/serializers.py#40-42) (UUID), `session_nom`, [session_en_cours](file:///home/darren/Bureau/projet/Mutuelle-Backend/transactions/views.py#184-188) (boolean), `montant_min`, `montant_max`, `date_paiement` (range), [this_month](file:///home/darren/Bureau/projet/Mutuelle-Backend/core/views.py#241-250), [this_year](file:///home/darren/Bureau/projet/Mutuelle-Backend/transactions/views.py#296-301).

**Endpoint :** `POST /api/transactions/paiements-solidarite/`
- **Description :** Enregistre un nouveau paiement de solidarité pour un membre.

**Format de la Requête (Body JSON) :**
```json
{
  "membre": "uuid-du-membre",
  "session": "uuid-de-la-session-concernee",
  "montant": "2000.00",
  "date_paiement": "2026-03-27",
  "notes": "Paiement mensuel de solidarité"
}
```

**Logique Automatique du Backend :**
- Le champ `montant_solidarite_du` est automatiquement géré. S'il s'agit du tout premier paiement de ce membre, le montant dû correspondra à ce qui est défini dans la Configuration Mutuelle. Pour les paiements suivants, le backend récupérera le `montant_solidarite_du` rattaché à son tout premier paiement pour garantir la cohérence d'un exercice à l'autre (même en cas d'augmentation via modification de la configuration globale).

**Endpoint :** `GET /api/transactions/paiements-solidarite/{id}/`
- **Description :** Récupère les détails d'un paiement de solidarité spécifique.

**Endpoint :** `PATCH /api/transactions/paiements-solidarite/{id}/`
- **Description :** Modifie un paiement de solidarité pré-existant (nécessite des droits d'admin/staff).

**Endpoint :** `DELETE /api/transactions/paiements-solidarite/{id}/`
- **Description :** Supprime un annule paiement de solidarité.
