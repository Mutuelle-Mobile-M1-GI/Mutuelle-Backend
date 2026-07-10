# 📊 API Response Examples - Renflouements

## 1. GET /core/exercices/ - List Exercises with Stats

### Request
```bash
curl -X GET "http://localhost:8000/api/core/exercices/" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Response (2 exercises - one with renflouements, one without)

```json
{
  "count": 2,
  "results": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "nom": "ARNO",
      "statut": "TERMINE",
      "date_debut": "2026-01-01",
      "date_fin": "2026-12-31",
      "description": "Exercice 2026",
      "is_en_cours": false,
      "nombre_sessions": 5,
      "fonds_social_info": {
        "montant_total": 300000,
        "derniere_modification": "2026-07-06T10:00:00Z"
      },
      "renflouement_stats": {
        "montant_total_du": 500000,
        "montant_total_paye": 200000,
        "montant_total_restant": 300000,
        "taux_recouvrement": 40.0,
        "nombre_renflouements": 5,
        "nombre_soldes": 2
      },
      "emprunt_tiers": false,
      "date_creation": "2026-01-01T00:00:00Z",
      "date_modification": "2026-07-06T15:30:00Z"
    },
    {
      "id": "660e8400-e29b-41d4-a716-446655440001",
      "nom": "2027",
      "statut": "EN_COURS",
      "date_debut": "2027-01-01",
      "date_fin": "2027-12-31",
      "description": "Exercice 2027",
      "is_en_cours": true,
      "nombre_sessions": 2,
      "fonds_social_info": {
        "montant_total": 0,
        "derniere_modification": null
      },
      "renflouement_stats": {
        "montant_total_du": 0,
        "montant_total_paye": 0,
        "montant_total_restant": 0,
        "taux_recouvrement": 0.0,
        "nombre_renflouements": 0,
        "nombre_soldes": 0
      },
      "emprunt_tiers": false,
      "date_creation": "2026-12-15T00:00:00Z",
      "date_modification": "2026-12-15T00:00:00Z"
    }
  ]
}
```

---

## 2. GET /transactions/renflouements/exercice_detail/?exercice_id=xxx

### Request
```bash
curl -X GET "http://localhost:8000/api/transactions/renflouements/exercice_detail/?exercice_id=550e8400-e29b-41d4-a716-446655440000" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Response - Exercise Detail with Members

```json
{
  "exercice": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "nom": "ARNO",
    "statut": "TERMINE",
    "date_debut": "2026-01-01",
    "date_fin": "2026-12-31"
  },
  "par_membre": [
    {
      "membre": {
        "id": "111e8400-e29b-41d4-a716-446655440000",
        "numero_membre": "ENS-001",
        "nom_complet": "Jean Dupont",
        "statut": "EN_REGLE"
      },
      "renflouement": {
        "id": "aaa-111",
        "montant_du": 100000,
        "montant_paye": 100000,
        "montant_restant": 0,
        "pourcentage_paye": 100.0,
        "date_creation": "2026-01-15",
        "type_cause": "RENFLOUEMENT_FIN_EXERCICE"
      },
      "paiements": [
        {
          "id": "pay-001",
          "montant": 100000,
          "montant_caisse_inscription": 40000,
          "montant_fonds_social": 60000,
          "date_paiement": "2026-06-15T10:00:00Z",
          "notes": "Paiement complet"
        }
      ],
      "totals": {
        "montant_du": 100000,
        "montant_paye": 100000,
        "montant_restant": 0,
        "pourcentage_paye": 100.0
      }
    },
    {
      "membre": {
        "id": "222e8400-e29b-41d4-a716-446655440000",
        "numero_membre": "ENS-002",
        "nom_complet": "Marie Martin",
        "statut": "EN_REGLE"
      },
      "renflouement": {
        "id": "aaa-222",
        "montant_du": 100000,
        "montant_paye": 50000,
        "montant_restant": 50000,
        "pourcentage_paye": 50.0,
        "date_creation": "2026-01-15",
        "type_cause": "RENFLOUEMENT_FIN_EXERCICE"
      },
      "paiements": [
        {
          "id": "pay-002",
          "montant": 50000,
          "montant_caisse_inscription": 20000,
          "montant_fonds_social": 30000,
          "date_paiement": "2026-05-10T14:00:00Z",
          "notes": "Paiement partiel"
        }
      ],
      "totals": {
        "montant_du": 100000,
        "montant_paye": 50000,
        "montant_restant": 50000,
        "pourcentage_paye": 50.0
      }
    },
    {
      "membre": {
        "id": "333e8400-e29b-41d4-a716-446655440000",
        "numero_membre": "ENS-003",
        "nom_complet": "Pierre Bernard",
        "statut": "EN_REGLE"
      },
      "renflouement": {
        "id": "aaa-333",
        "montant_du": 100000,
        "montant_paye": 0,
        "montant_restant": 100000,
        "pourcentage_paye": 0.0,
        "date_creation": "2026-01-15",
        "type_cause": "RENFLOUEMENT_FIN_EXERCICE"
      },
      "paiements": [],
      "totals": {
        "montant_du": 100000,
        "montant_paye": 0,
        "montant_restant": 100000,
        "pourcentage_paye": 0.0
      }
    },
    {
      "membre": {
        "id": "444e8400-e29b-41d4-a716-446655440000",
        "numero_membre": "ENS-004",
        "nom_complet": "Sophie Leclerc",
        "statut": "NON_EN_REGLE"
      },
      "renflouement": {
        "id": "aaa-444",
        "montant_du": 100000,
        "montant_paye": 0,
        "montant_restant": 100000,
        "pourcentage_paye": 0.0,
        "date_creation": "2026-01-15",
        "type_cause": "RENFLOUEMENT_FIN_EXERCICE"
      },
      "paiements": [],
      "totals": {
        "montant_du": 100000,
        "montant_paye": 0,
        "montant_restant": 100000,
        "pourcentage_paye": 0.0
      }
    },
    {
      "membre": {
        "id": "555e8400-e29b-41d4-a716-446655440000",
        "numero_membre": "ENS-005",
        "nom_complet": "Luc Fournier",
        "statut": "EN_REGLE"
      },
      "renflouement": {
        "id": "aaa-555",
        "montant_du": 100000,
        "montant_paye": 100000,
        "montant_restant": 0,
        "pourcentage_paye": 100.0,
        "date_creation": "2026-01-15",
        "type_cause": "RENFLOUEMENT_FIN_EXERCICE"
      },
      "paiements": [
        {
          "id": "pay-005",
          "montant": 100000,
          "montant_caisse_inscription": 40000,
          "montant_fonds_social": 60000,
          "date_paiement": "2026-07-01T09:00:00Z",
          "notes": "Paiement complet"
        }
      ],
      "totals": {
        "montant_du": 100000,
        "montant_paye": 100000,
        "montant_restant": 0,
        "pourcentage_paye": 100.0
      }
    }
  ],
  "statistiques_globales": {
    "nombre_membres": 5,
    "nombre_membres_soldes": 2,
    "nombre_membres_partiels": 1,
    "nombre_membres_non_payes": 2,
    "montant_total_du": 500000,
    "montant_total_paye": 200000,
    "montant_total_restant": 300000,
    "taux_recouvrement": 40.0
  }
}
```

---

## 3. GET /transactions/renflouements/par_membre/?membre_id=xxx

### Request
```bash
curl -X GET "http://localhost:8000/api/transactions/renflouements/par_membre/?membre_id=111e8400-e29b-41d4-a716-446655440000" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Response - Member History Across All Exercises

```json
{
  "membre": {
    "id": "111e8400-e29b-41d4-a716-446655440000",
    "numero_membre": "ENS-001",
    "nom_complet": "Jean Dupont",
    "statut": "EN_REGLE"
  },
  "renflouements_par_exercice": [
    {
      "exercice": "2027",
      "exercice_id": "660e8400-e29b-41d4-a716-446655440001",
      "montant_du": 120000,
      "montant_paye": 120000,
      "montant_restant": 0,
      "pourcentage_paye": 100.0,
      "renflouements": [
        {
          "id": "bbb-111",
          "montant_du": 120000,
          "montant_paye": 120000,
          "montant_restant": 0,
          "pourcentage_paye": 100.0,
          "date_creation": "2027-01-15",
          "cause": "Renflouement proportionnel fin d'exercice 2027"
        }
      ]
    },
    {
      "exercice": "ARNO",
      "exercice_id": "550e8400-e29b-41d4-a716-446655440000",
      "montant_du": 100000,
      "montant_paye": 100000,
      "montant_restant": 0,
      "pourcentage_paye": 100.0,
      "renflouements": [
        {
          "id": "aaa-111",
          "montant_du": 100000,
          "montant_paye": 100000,
          "montant_restant": 0,
          "pourcentage_paye": 100.0,
          "date_creation": "2026-01-15",
          "cause": "Renflouement proportionnel fin d'exercice ARNO"
        }
      ]
    }
  ],
  "cumuls_totaux": {
    "total_du": 220000,
    "total_paye": 220000,
    "montant_restant": 0,
    "pourcentage_paye": 100.0,
    "nombre_exercices": 2
  }
}
```

---

## 4. GET /transactions/renflouements/statistiques/?exercice_id=xxx

### Request
```bash
curl -X GET "http://localhost:8000/api/transactions/renflouements/statistiques/?exercice_id=550e8400-e29b-41d4-a716-446655440000" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Response - Quick Stats (Lightweight)

```json
{
  "exercice_contexte": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "nom": "ARNO",
    "statut": "TERMINE"
  },
  "nombre_renflouements": {
    "total": 5,
    "soldes": 2,
    "non_soldes": 3
  },
  "montants": {
    "total_du": 500000,
    "total_paye": 200000,
    "montant_restant": 300000
  },
  "pourcentages": {
    "taux_recouvrement": 40.0,
    "taux_solde": 40.0
  },
  "note": "total_du = dépenses totales de l'exercice (réparties entre les membres)"
}
```

---

## Frontend Data Processing Examples

### Example 1: Transform List for Display

```javascript
const processExercicesForDisplay = (exercices) => {
  return exercices.map(exe => ({
    id: exe.id,
    nom: exe.nom,
    statut: exe.statut,
    
    // Stats for display
    montantDu: exe.renflouement_stats?.montant_total_du || 0,
    montantPaye: exe.renflouement_stats?.montant_total_paye || 0,
    montantRestant: exe.renflouement_stats?.montant_total_restant || 0,
    tauxRecouvrement: exe.renflouement_stats?.taux_recouvrement || 0,
    
    // Display helpers
    progressPercent: (exe.renflouement_stats?.montant_total_paye || 0) / 
                     (exe.renflouement_stats?.montant_total_du || 1) * 100,
    statusColor: exe.renflouement_stats?.montant_total_restant <= 0 ? 'green' : 'orange',
    statusText: exe.renflouement_stats?.montant_total_restant <= 0 ? 'Soldé' : 'En cours',
  }));
};
```

### Example 2: Format Stats for Cards

```javascript
const formatStatsForCard = (stats) => {
  return {
    duText: formatCurrency(stats.montant_total_du || 0),
    payeText: formatCurrency(stats.montant_total_paye || 0),
    restantText: formatCurrency(stats.montant_total_restant || 0),
    tauxText: `${(stats.taux_recouvrement || 0).toFixed(0)}%`,
    nombreSoldes: `${stats.nombre_soldes || 0}/${stats.nombre_renflouements || 0}`,
  };
};
```

### Example 3: Aggregate Across Multiple Exercises

```javascript
const aggregateStats = (exercices) => {
  return exercices.reduce(
    (acc, exe) => ({
      totalDu: acc.totalDu + (exe.renflouement_stats?.montant_total_du || 0),
      totalPaye: acc.totalPaye + (exe.renflouement_stats?.montant_total_paye || 0),
      nombreExercices: acc.nombreExercices + 1,
    }),
    { totalDu: 0, totalPaye: 0, nombreExercices: 0 }
  );
};

// Usage
const aggregated = aggregateStats(exercices);
const tauxGlobal = (aggregated.totalPaye / aggregated.totalDu) * 100;
```

---

## Status Codes & Error Handling

### 200 OK - Successful Response
```json
{
  "count": 2,
  "results": [...]
}
```

### 400 Bad Request - Invalid Parameter
```json
{
  "error": "Paramètre exercice_id requis",
  "details": "Pour utiliser cet endpoint, vous devez fournir le paramètre exercice_id"
}
```

### 404 Not Found - Resource Not Found
```json
{
  "error": "Membre non trouvé",
  "details": "Le membre avec l'ID fourni n'existe pas"
}
```

### 500 Internal Server Error
```json
{
  "error": "Erreur serveur",
  "details": "Une erreur inattendue s'est produite"
}
```

---

## Common Calculations

### Calculate Remaining Amount
```javascript
const remaining = stats.montant_total_du - stats.montant_total_paye;
```

### Calculate Collection Rate
```javascript
const rate = (stats.montant_total_paye / stats.montant_total_du) * 100;
```

### Calculate Members Status Distribution
```javascript
const distribution = {
  fully_paid: stats.nombre_soldes,
  partial: stats.nombre_renflouements - stats.nombre_soldes - unpaid_count,
  unpaid: unpaid_count,
};
```

### Check if Fully Collected
```javascript
const isFullyCollected = stats.montant_total_restant <= 0;
```

---

## Pagination Notes

The `/core/exercices/` endpoint supports pagination:

```bash
# Get first 10 exercises
GET /api/core/exercices/?page=1

# Get next 10
GET /api/core/exercices/?page=2

# Get 20 per page
GET /api/core/exercices/?page_size=20
```

Response includes:
```json
{
  "count": 50,
  "next": "http://localhost:8000/api/core/exercices/?page=2",
  "previous": null,
  "results": [...]
}
```

---

**Last Updated:** July 2026  
**API Version:** v1
