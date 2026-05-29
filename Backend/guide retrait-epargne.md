# 📘 Guide API — Retrait d'Épargne (v2)

> **À destination du développeur frontend**  
> Base URL : `http://localhost:8000/api/transactions`  
> ⚠️ Toutes les opérations sont réservées à l'administrateur

---

## 🔐 Authentification

Toutes les requêtes nécessitent un token JWT :

```
Authorization: Bearer <access_token>
```

**Obtenir un token :**
```http
POST /api/token/
Content-Type: application/json

{
  "email": "admin@email.com",
  "password": "password"
}
```

---

## 📋 Endpoints disponibles

| Méthode | URL | Description |
|---------|-----|-------------|
| `GET` | `/retraits-epargne/` | Lister tous les retraits |
| `POST` | `/retraits-epargne/` | Créer un retrait (débit immédiat) |
| `GET` | `/retraits-epargne/{id}/` | Détail d'un retrait |
| `DELETE` | `/retraits-epargne/{id}/` | Supprimer un retrait |
| `GET` | `/retraits-epargne/par_membre/?membre_id=` | Retraits d'un membre |
| `GET` | `/retraits-epargne/epargne_disponible/?membre_id=` | Solde épargne d'un membre |

> ⚠️ Pas de PUT/PATCH — un retrait ne peut pas être modifié

---

## 📌 Détail des endpoints

---

### 1. Vérifier l'épargne disponible
> Appeler AVANT de créer un retrait pour connaître le solde max autorisé.

```http
GET /retraits-epargne/epargne_disponible/?membre_id={uuid}
```

**Réponse 200 :**
```json
{
  "membre_id": "13abba7a-1a67-4ba0-921b-e83111c21d0b",
  "numero_membre": "ENS-0001",
  "epargne_disponible": 107301.59
}
```

---

### 2. Créer un retrait
> Le retrait est **immédiatement approuvé** et **débite l'épargne** dès la création.  
> Le trésor (caisse des épargnes) est mis à jour automatiquement.

```http
POST /retraits-epargne/
Content-Type: application/json

{
  "membre": "13abba7a-1a67-4ba0-921b-e83111c21d0b",
  "session": "uuid-de-la-session",
  "montant": 20000,
  "motif": "Retrait personnel"
}
```

**Réponse 201 :**
```json
{
  "id": "uuid-du-retrait",
  "membre": "13abba7a-...",
  "membre_info": {
    "id": "13abba7a-...",
    "numero_membre": "ENS-0001",
    "nom": "Ousseini Mouhamadou"
  },
  "session": "uuid-session",
  "session_nom": "Session Mars 2026",
  "montant": "20000.00",
  "motif": "Retrait personnel",
  "date_retrait": "2026-05-29T10:00:00Z",
  "epargne_disponible": 87301.59,
  "epargne_transaction": "uuid-transaction"
}
```

**Erreur 400 — Montant supérieur à l'épargne :**
```json
{
  "error": "Épargne insuffisante.",
  "epargne_disponible": 107301.59,
  "montant_demande": 999999.0
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
| `session` | UUID | `?session=uuid` |
| `date_min` | date | `?date_min=2026-01-01` |
| `date_max` | date | `?date_max=2026-12-31` |
| `montant_min` | number | `?montant_min=10000` |
| `montant_max` | number | `?montant_max=100000` |

---

### 4. Retraits d'un membre

```http
GET /retraits-epargne/par_membre/?membre_id={uuid}
```

**Réponse 200 :** Liste des retraits du membre.

---

### 5. Supprimer un retrait

```http
DELETE /retraits-epargne/{id}/
```

**Réponse 204 :** No content.

---

## 🔄 Fonctionnement

```
Admin crée retrait
      │
      ▼
Vérification épargne disponible
      │
      ├── Insuffisante → Erreur 400
      │
      └── OK → Création EpargneTransaction (-montant)
                      │
                      ▼
              Épargne membre diminue
              Trésor mis à jour
              Retrait enregistré
```

---

## 💡 Flux recommandé côté frontend

```
1. Admin sélectionne un membre
   └─→ GET /epargne_disponible/?membre_id=   → afficher solde max dans le formulaire

2. Admin saisit le montant et valide
   └─→ POST /retraits-epargne/               → retrait créé et épargne débitée immédiatement

3. Afficher la liste des retraits d'un membre
   └─→ GET /par_membre/?membre_id=

4. Vérifier le trésor mis à jour
   └─→ GET /epargne-transactions/statistiques/
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
    "nom": "Nom du membre"
  },
  "session": "uuid",
  "session_nom": "Session Mars 2026",
  "montant": "20000.00",
  "motif": "Motif du retrait",
  "date_retrait": "2026-05-29T10:00:00Z",
  "epargne_disponible": 87301.59,
  "epargne_transaction": "uuid-transaction-liee"
}
```

---

## 🧪 Tester avec Swagger

```
http://localhost:8000/api/schema/swagger-ui/
```

Cherche la section **retraits-epargne**.