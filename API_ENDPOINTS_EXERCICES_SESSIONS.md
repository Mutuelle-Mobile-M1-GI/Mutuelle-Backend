# API Endpoints - Exercices et Sessions
## Modifications et Suppressions

---

## EXERCICES

### 1. Lister tous les exercices
**Endpoint:** `GET /api/core/exercices/`

**Response:**
```json
{
  "count": 2,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": "393ca003-89b5-46fd-ab3c-30e5f1956f05",
      "nom": "Exercice 2026",
      "date_debut": "2026-01-01",
      "date_fin": "2026-12-31",
      "statut": "EN_COURS",
      "description": "Exercice fiscal 2026",
      "is_en_cours": true,
      "nombre_sessions": 2,
      "fonds_social_info": {
        "montant_total": "500000.00",
        "derniere_modification": "2026-03-10T10:30:00Z"
      },
      "emprunt_tiers": [],
      "date_creation": "2026-01-01T00:00:00Z",
      "date_modification": "2026-03-10T10:30:00Z"
    }
  ]
}
```

---

### 2. Récupérer l'exercice en cours
**Endpoint:** `GET /api/core/exercices/current/`

**Response:**
```json
{
  "id": "393ca003-89b5-46fd-ab3c-30e5f1956f05",
  "nom": "Exercice 2026",
  "date_debut": "2026-01-01",
  "date_fin": "2026-12-31",
  "statut": "EN_COURS",
  "description": "Exercice fiscal 2026",
  "is_en_cours": true,
  "nombre_sessions": 2,
  "fonds_social_info": {
    "montant_total": "500000.00",
    "derniere_modification": "2026-03-10T10:30:00Z"
  },
  "emprunt_tiers": [],
  "date_creation": "2026-01-01T00:00:00Z",
  "date_modification": "2026-03-10T10:30:00Z"
}
```

---

### 3. Modifier les paramètres d'un exercice EN_COURS
**Endpoint:** `PATCH /api/core/exercices/{id}/update_params/`

**Paramètres modifiables:**
- `nom` (string, optionnel)
- `description` (string, optionnel)
- `date_debut` (date, optionnel, format: YYYY-MM-DD)
- `date_fin` (date, optionnel, format: YYYY-MM-DD)

**Request Body:**
```json
{
  "nom": "Exercice 2026 - Modifié",
  "description": "Nouvelle description",
  "date_debut": "2026-01-15",
  "date_fin": "2026-12-31"
}
```

**Response (Succès - 200):**
```json
{
  "message": "Exercice modifié avec succès",
  "data": {
    "id": "393ca003-89b5-46fd-ab3c-30e5f1956f05",
    "nom": "Exercice 2026 - Modifié",
    "date_debut": "2026-01-15",
    "date_fin": "2026-12-31",
    "statut": "EN_COURS",
    "description": "Nouvelle description",
    "is_en_cours": true,
    "nombre_sessions": 2,
    "fonds_social_info": {
      "montant_total": "500000.00",
      "derniere_modification": "2026-03-10T10:30:00Z"
    },
    "emprunt_tiers": [],
    "date_creation": "2026-01-01T00:00:00Z",
    "date_modification": "2026-03-10T11:45:00Z"
  }
}
```

**Response (Erreur - 400):**
```json
{
  "error": "Impossible de modifier cet exercice",
  "details": "Seuls les exercices EN_COURS peuvent être modifiés. Statut actuel: TERMINE"
}
```

**Response (Erreur - Aucun paramètre - 400):**
```json
{
  "error": "Aucun paramètre valide fourni",
  "details": "Paramètres autorisés: nom, description, date_debut, date_fin"
}
```

---

### 4. Supprimer un exercice
**Endpoint:** `DELETE /api/core/exercices/{id}/`

**Response (Succès - 200):**
```json
{
  "message": "Exercice \"Exercice 2026\" supprimé avec succès",
  "details": "Aucune session n'était rattachée à cet exercice"
}
```

**Response (Erreur - Sessions rattachées - 400):**
```json
{
  "error": "Impossible de supprimer cet exercice",
  "details": "Des sessions sont rattachées à cet exercice. Supprimez d'abord les sessions.",
  "sessions_count": 2
}
```

---

## SESSIONS

### 1. Lister toutes les sessions
**Endpoint:** `GET /api/core/sessions/`

**Response:**
```json
{
  "count": 2,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": "0a5b34f6-b303-415e-ad36-fc72abeda27e",
      "exercice": "393ca003-89b5-46fd-ab3c-30e5f1956f05",
      "exercice_nom": "Exercice 2026",
      "nom": "Session Mars 2026",
      "date_session": "2026-03-10",
      "montant_collation": "5000.00",
      "statut": "EN_COURS",
      "description": "Session de mars",
      "is_en_cours": true,
      "nombre_membres_inscrits": 15,
      "total_solidarite_collectee": "75000.00",
      "renflouements_generes": "120000.00",
      "date_creation": "2026-03-10T08:00:00Z",
      "date_modification": "2026-03-10T10:30:00Z"
    }
  ]
}
```

---

### 2. Récupérer la session en cours
**Endpoint:** `GET /api/core/sessions/current/`

**Response:**
```json
{
  "id": "0a5b34f6-b303-415e-ad36-fc72abeda27e",
  "exercice": "393ca003-89b5-46fd-ab3c-30e5f1956f05",
  "exercice_nom": "Exercice 2026",
  "nom": "Session Mars 2026",
  "date_session": "2026-03-10",
  "montant_collation": "5000.00",
  "statut": "EN_COURS",
  "description": "Session de mars",
  "is_en_cours": true,
  "nombre_membres_inscrits": 15,
  "total_solidarite_collectee": "75000.00",
  "renflouements_generes": "120000.00",
  "date_creation": "2026-03-10T08:00:00Z",
  "date_modification": "2026-03-10T10:30:00Z"
}
```

---

### 3. Modifier les paramètres d'une session EN_COURS
**Endpoint:** `PATCH /api/core/sessions/{id}/update_params/`

**Paramètres modifiables:**
- `nom` (string, optionnel)
- `description` (string, optionnel)
- `date_session` (date, optionnel, format: YYYY-MM-DD)
- `montant_collation` (decimal, optionnel)

**Request Body:**
```json
{
  "nom": "Session Mars 2026 - Modifiée",
  "description": "Nouvelle description",
  "date_session": "2026-03-15",
  "montant_collation": "7500.00"
}
```

**Response (Succès - 200):**
```json
{
  "message": "Session modifiée avec succès",
  "data": {
    "id": "0a5b34f6-b303-415e-ad36-fc72abeda27e",
    "exercice": "393ca003-89b5-46fd-ab3c-30e5f1956f05",
    "exercice_nom": "Exercice 2026",
    "nom": "Session Mars 2026 - Modifiée",
    "date_session": "2026-03-15",
    "montant_collation": "7500.00",
    "statut": "EN_COURS",
    "description": "Nouvelle description",
    "is_en_cours": true,
    "nombre_membres_inscrits": 15,
    "total_solidarite_collectee": "75000.00",
    "renflouements_generes": "120000.00",
    "date_creation": "2026-03-10T08:00:00Z",
    "date_modification": "2026-03-10T11:45:00Z"
  }
}
```

**Response (Erreur - 400):**
```json
{
  "error": "Impossible de modifier cette session",
  "details": "Seules les sessions EN_COURS peuvent être modifiées. Statut actuel: TERMINEE"
}
```

**Response (Erreur - Aucun paramètre - 400):**
```json
{
  "error": "Aucun paramètre valide fourni",
  "details": "Paramètres autorisés: nom, description, date_session, montant_collation"
}
```

---

### 4. Supprimer une session
**Endpoint:** `DELETE /api/core/sessions/{id}/`

**Response (Succès - 200):**
```json
{
  "message": "Session \"Session Mars 2026\" supprimée avec succès",
  "details": "Aucune opération n'avait été effectuée sur cette session"
}
```

**Response (Erreur - Opérations existantes - 400):**
```json
{
  "error": "Impossible de supprimer cette session",
  "details": "Des opérations ont déjà été effectuées sur cette session",
  "operations": {
    "paiements_inscription": 5,
    "paiements_solidarite": 3,
    "epargnes": 2,
    "emprunts": 1,
    "renflouements": 4,
    "membres_inscrits": 15,
    "total": 30
  }
}
```

---

## RÉSUMÉ DES ENDPOINTS

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| GET | `/api/core/exercices/` | Lister tous les exercices |
| GET | `/api/core/exercices/current/` | Récupérer l'exercice en cours |
| PATCH | `/api/core/exercices/{id}/update_params/` | Modifier un exercice EN_COURS |
| DELETE | `/api/core/exercices/{id}/` | Supprimer un exercice |
| GET | `/api/core/sessions/` | Lister toutes les sessions |
| GET | `/api/core/sessions/current/` | Récupérer la session en cours |
| PATCH | `/api/core/sessions/{id}/update_params/` | Modifier une session EN_COURS |
| DELETE | `/api/core/sessions/{id}/` | Supprimer une session |

---

## NOTES IMPORTANTES

### Permissions
- Tous les endpoints de modification et suppression nécessitent les permissions d'administrateur
- Les endpoints GET sont accessibles en lecture seule

### Validations
- **Modification:** Seuls les exercices/sessions avec le statut `EN_COURS` peuvent être modifiés
- **Suppression exercice:** Impossible si des sessions sont rattachées
- **Suppression session:** Impossible si des opérations ont été effectuées (paiements, épargnes, emprunts, renflouements, membres inscrits)

### Formats de date
- Format attendu: `YYYY-MM-DD` (ex: `2026-03-10`)
- Les dates sont retournées en ISO 8601 avec timezone

### Montants
- Format: Decimal avec 2 décimales
- Exemple: `"5000.00"` ou `7500.50`

### Statuts possibles
- **Exercices:** `EN_COURS`, `TERMINE`, `PLANIFIE`
- **Sessions:** `EN_COURS`, `TERMINEE`, `PLANIFIEE`
