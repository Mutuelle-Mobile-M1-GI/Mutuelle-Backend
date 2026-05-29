# 📘 Guide API — Fonctionnalité Retrait d'Épargne

> **À destination du développeur frontend**  
> Base URL : `http://localhost:8000/api/transactions`

---

## 🔐 Authentification

Toutes les requêtes nécessitent un token JWT dans le header :

```
Authorization: Bearer <access_token>
```

**Obtenir un token :**
```http
POST /api/token/
Content-Type: application/json

{
  "email": "ton@email.com",
  "password": "tonpassword"
}
```

**Réponse :**
```json
{
  "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

---

## 📋 Endpoints disponibles

| Méthode | URL | Description |
|---------|-----|-------------|
| `GET` | `/retraits-epargne/` | Lister tous les retraits |
| `POST` | `/retraits-epargne/` | Créer une demande de retrait |
| `GET` | `/retraits-epargne/{id}/` | Détail d'un retrait |
| `PATCH` | `/retraits-epargne/{id}/` | Modifier un retrait (EN_ATTENTE uniquement) |
| `DELETE` | `/retraits-epargne/{id}/` | Supprimer un retrait (EN_ATTENTE uniquement) |
| `POST` | `/retraits-epargne/{id}/approuver/` | Approuver un retrait |
| `POST` | `/retraits-epargne/{id}/rejeter/` | Rejeter un retrait |
| `GET` | `/retraits-epargne/par_membre/` | Retraits d'un membre |
| `GET` | `/retraits-epargne/epargne_disponible/` | Solde épargne d'un membre |

---

## 📌 Détail des endpoints

---

### 1. Vérifier l'épargne disponible d'un membre
> ⚠️ **À appeler AVANT d'afficher le formulaire de retrait** pour connaître le solde max autorisé.

```http
GET /retraits-epargne/epargne_disponible/?membre_id={uuid}
```

**Réponse 200 :**
```json
{
  "membre_id": "2c31b276-e435-4d51-b55e-cfe822fc3af1",
  "numero_membre": "ENS-0001",
  "epargne_disponible": 127301.59
}
```

**Erreur 400 :**
```json
{
  "error": "Le paramètre 'membre_id' est requis."
}
```

---

### 2. Créer une demande de retrait

```http
POST /retraits-epargne/
Content-Type: application/json

{
  "membre": "2c31b276-e435-4d51-b55e-cfe822fc3af1",
  "session": "uuid-de-la-session",
  "montant": 50000,
  "motif": "Besoin personnel"
}
```

**Réponse 201 :**
```json
{
  "id": "uuid-du-retrait",
  "membre": "2c31b276-...",
  "membre_info": {
    "id": "2c31b276-...",
    "numero_membre": "ENS-0001",
    "nom": "Ousseini Mouhamadou"
  },
  "session": "uuid-session",
  "session_nom": "Session Mars 2026",
  "montant": "50000.00",
  "statut": "EN_ATTENTE",
  "statut_display": "En attente",
  "motif": "Besoin personnel",
  "notes_admin": "",
  "date_demande": "2026-05-28T23:00:00Z",
  "date_traitement": null,
  "epargne_disponible": 127301.59,
  "epargne_transaction": null,
  "epargne_transaction_info": null
}
```

**Erreur 400 — Montant supérieur à l'épargne :**
```json
{
  "montant": [
    "Le montant demandé (500 000 FCFA) dépasse l'épargne disponible (127 302 FCFA)."
  ]
}
```

---

### 3. Lister les retraits

```http
GET /retraits-epargne/
```

**Filtres disponibles :**

| Paramètre | Type | Exemple |
|-----------|------|---------|
| `membre` | UUID | `?membre=uuid` |
| `statut` | string | `?statut=EN_ATTENTE` |
| `session` | UUID | `?session=uuid` |
| `date_min` | date | `?date_min=2026-01-01` |
| `date_max` | date | `?date_max=2026-12-31` |
| `montant_min` | number | `?montant_min=10000` |
| `montant_max` | number | `?montant_max=100000` |

**Exemple :**
```http
GET /retraits-epargne/?statut=EN_ATTENTE&membre=uuid
```

---

### 4. Retraits d'un membre spécifique

```http
GET /retraits-epargne/par_membre/?membre_id={uuid}
```

**Réponse 200 :** Liste des retraits du membre.

---

### 5. Approuver un retrait

```http
POST /retraits-epargne/{id}/approuver/
Content-Type: application/json

{
  "notes_admin": "Approuvé après vérification"
}
```

**Réponse 200 :** Le retrait avec `statut: "APPROUVE"` et `epargne_transaction` renseignée.

**Erreur 400 — Déjà traité :**
```json
{
  "error": "Ce retrait est déjà 'Approuvé'."
}
```

**Erreur 400 — Épargne insuffisante :**
```json
{
  "error": "Épargne insuffisante.",
  "epargne_disponible": 51349.21,
  "montant_demande": 100000.0
}
```

---

### 6. Rejeter un retrait

```http
POST /retraits-epargne/{id}/rejeter/
Content-Type: application/json

{
  "notes_admin": "Motif du rejet"
}
```

**Réponse 200 :** Le retrait avec `statut: "REJETE"`.

---

### 7. Modifier un retrait

> ⚠️ Seulement possible si le statut est `EN_ATTENTE`.

```http
PATCH /retraits-epargne/{id}/
Content-Type: application/json

{
  "montant": 30000,
  "motif": "Motif mis à jour"
}
```

---

### 8. Supprimer un retrait

> ⚠️ Seulement possible si le statut est `EN_ATTENTE`.

```http
DELETE /retraits-epargne/{id}/
```

**Réponse 204 :** No content.

**Erreur 400 :**
```json
{
  "error": "Seul un retrait en attente peut être supprimé."
}
```

---

## 🔄 Cycle de vie d'un retrait

```
EN_ATTENTE ──→ APPROUVE
           └──→ REJETE
```

- Un retrait **APPROUVÉ** débite automatiquement l'épargne du membre.
- Un retrait **REJETÉ** ne modifie pas l'épargne.
- Un retrait **APPROUVÉ ou REJETÉ** ne peut plus être modifié ni supprimé.

---

## 💡 Flux recommandé côté frontend

```
1. Membre demande un retrait
   └─→ GET /epargne_disponible/?membre_id= (afficher le solde max dans le formulaire)
   └─→ POST /retraits-epargne/ (soumettre la demande)

2. Admin traite la demande
   └─→ GET /retraits-epargne/?statut=EN_ATTENTE (liste des demandes en attente)
   └─→ POST /retraits-epargne/{id}/approuver/ ou /rejeter/

3. Membre consulte ses retraits
   └─→ GET /retraits-epargne/par_membre/?membre_id=
```

---

## 📦 Structure complète d'un objet `RetraitEpargne`

```json
{
  "id": "uuid",
  "membre": "uuid",
  "membre_info": {
    "id": "uuid",
    "numero_membre": "ENS-0001",
    "nom": "Ousseini Mouhamadou"
  },
  "session": "uuid",
  "session_nom": "Session Mars 2026",
  "montant": "50000.00",
  "statut": "EN_ATTENTE | APPROUVE | REJETE",
  "statut_display": "En attente | Approuvé | Rejeté",
  "motif": "Raison du retrait",
  "notes_admin": "Notes de l'administrateur",
  "date_demande": "2026-05-28T23:00:00Z",
  "date_traitement": "2026-05-28T23:30:00Z | null",
  "epargne_disponible": 127301.59,
  "epargne_transaction": "uuid | null",
  "epargne_transaction_info": {
    "id": "uuid",
    "montant": -50000.0,
    "date": "2026-05-28T23:30:00Z"
  }
}
```

---

## 🧪 Tester avec Swagger

```
http://localhost:8000/api/schema/swagger-ui/
```

Cherche la section **retraits-epargne** pour tester tous les endpoints interactivement.