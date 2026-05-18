
---

## 📋 Documentation — `GET /api/core/sessions/depenses/`

**Description** : Liste les dépenses de session liées à la création des sessions (collation + autres dépenses), avec totaux agrégés.

**Authentification** : Aucune requise (lecture publique)

---

### Paramètres de filtrage (query params)

| Paramètre | Type | Description |
|-----------|------|-------------|
| [exercice](cci:1://file:///home/darren/Bureau/projet/Mutuelle-Backend/core/models.py:495:4-505:17) | UUID | Filtrer par exercice |
| [session](cci:1://file:///home/darren/Bureau/projet/Mutuelle-Backend/core/views.py:91:4-94:53) | UUID | Filtrer une session précise |
| `type` | string | [collation](cci:1://file:///home/darren/Bureau/projet/Mutuelle-Backend/core/views.py:230:4-233:51) \| `autre` \| `all` (défaut : `all`) |

---

### Réponse (`200 OK`)

```json
{
    "total_collation": 14505.00,
    "total_autre_depense": 5010.00,
    "total_general": 19515.00,
    "nombre_sessions": 19,
    "depenses": [
        {
            "id": "8a76f69b-...",
            "nom": "Session Avril 2026",
            "date_session": "2026-04-26",
            "exercice_id": "246b4f25-...",
            "exercice_nom": "Exercice 2026",
            "montant_collation": "4500.00",
            "montant_autre_depense": "0.00",
            "motif_autre_depense": "",
            "total_depenses": 4500.0
        },
        ...
    ]
}
```

---

### Exemples d'appels

```bash
# Toutes les dépenses (toutes sessions)
GET /api/core/sessions/depenses/

# Dépenses d'un exercice précis
GET /api/core/sessions/depenses/?exercice=246b4f25-0b8b-4922-b37a-506ecfc1f1fd

# Uniquement les sessions avec collation
GET /api/core/sessions/depenses/?type=collation

# Uniquement les sessions avec autre dépense
GET /api/core/sessions/depenses/?type=autre

# Dépenses d'une session précise
GET /api/core/sessions/depenses/?session=8a76f69b-2c26-496c-a410-5b5cebc06c59
```

---

### Champs de la réponse

| Champ | Type | Description |
|-------|------|-------------|
| `total_collation` | Decimal | Somme de toutes les collations filtrées |
| `total_autre_depense` | Decimal | Somme de toutes les autres dépenses filtrées |
| `total_general` | Decimal | Somme totale (collation + autre) |
| [nombre_sessions](cci:1://file:///home/darren/Bureau/projet/Mutuelle-Backend/core/serializers.py:60:4-61:35) | int | Nombre de sessions dans le résultat |
| `depenses[].id` | UUID | ID de la session |
| `depenses[].nom` | string | Nom de la session |
| `depenses[].date_session` | date | Date de la session (`YYYY-MM-DD`) |
| `depenses[].exercice_id` | UUID | ID de l'exercice lié |
| `depenses[].exercice_nom` | string | Nom de l'exercice lié |
| `depenses[].montant_collation` | Decimal | Montant collation (FCFA) |
| `depenses[].montant_autre_depense` | Decimal | Montant autre dépense (FCFA) |
| `depenses[].motif_autre_depense` | string | Motif de l'autre dépense |
| `depenses[].total_depenses` | Decimal | Total = collation + autre dépense |