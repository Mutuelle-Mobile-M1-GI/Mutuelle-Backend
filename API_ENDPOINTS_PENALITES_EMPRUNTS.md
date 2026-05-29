# API Endpoints - Pénalités d'Emprunts

## Vue d'ensemble

Ce système de traçabilité des pénalités permet une **transparence totale** devant les membres de la mutuelle. Chaque pénalité appliquée est enregistrée avec tous les détails de calcul et peut être consultée via des endpoints dédiés.

## Modèle PenaliteEmprunt

### Champs principaux
- **emprunt** : Référence vers l'emprunt concerné
- **palier** : Identifiant du palier (ex: "Palier-3", "Palier-6")
- **sessions_ecoulees** : Nombre de sessions depuis l'octroi
- **montant_reste_avant** : Montant restant avant application de la pénalité
- **taux_applique** : Taux d'intérêt utilisé pour le calcul
- **montant_interet_taux** : Montant calculé (reste × taux)
- **montant_penalite_fixe** : Pénalité fixe (15 000 FCFA)
- **montant_total_penalite** : Total de la pénalité
- **justification** : Explication détaillée du calcul
- **date_application** : Date d'application de la pénalité
- **appliquee_par** : Utilisateur qui a appliqué (NULL pour automatique)

## Endpoints disponibles

### 1. Liste des pénalités
```
GET /api/transactions/penalites-emprunt/
```

**Filtres disponibles :**
- `emprunt` : UUID de l'emprunt
- `membre_numero` : Numéro du membre (recherche partielle)
- `membre_nom` : Nom du membre (recherche partielle)
- `type_penalite` : Type de pénalité
- `palier` : Palier de la pénalité
- `sessions_ecoulees` : Nombre exact de sessions
- `sessions_ecoulees_min` : Minimum de sessions
- `sessions_ecoulees_max` : Maximum de sessions
- `montant_min` : Montant minimum de pénalité
- `montant_max` : Montant maximum de pénalité
- `date_application` : Date exacte
- `date_application_after` : Après cette date
- `date_application_before` : Avant cette date
- `automatique` : true/false (pénalités automatiques ou manuelles)
- `this_month` : true (pénalités de ce mois)
- `this_year` : true (pénalités de cette année)

**Exemple de réponse :**
```json
{
  "count": 15,
  "results": [
    {
      "id": "uuid-penalite",
      "emprunt": "uuid-emprunt",
      "membre_numero": "ENS-0001",
      "membre_nom": "Jean Dupont",
      "type_penalite": "RETARD_PALIER",
      "type_penalite_display": "Pénalité de retard par palier",
      "palier": "Palier-3",
      "sessions_ecoulees": 3,
      "montant_reste_avant": "150000.00",
      "taux_applique": "5.00",
      "montant_interet_taux": "7500.00",
      "montant_penalite_fixe": "15000.00",
      "montant_total_penalite": "22500.00",
      "formule_calcul": "150,000 × 5% + 15,000 = 22,500 FCFA",
      "date_application": "2026-05-19T10:30:00Z",
      "appliquee_par": null,
      "appliquee_par_nom": null,
      "justification": "Pénalité automatique Palier-3 appliquée après 3 sessions...",
      "emprunt_info": {
        "id": "uuid-emprunt",
        "montant_initial": "100000.00",
        "montant_total_actuel": "122500.00",
        "montant_rembourse": "0.00",
        "montant_restant": "122500.00",
        "statut": "EN_RETARD",
        "jours_retard": 45
      }
    }
  ]
}
```

### 2. Statistiques des pénalités
```
GET /api/transactions/penalites-emprunt/statistiques/
```

**Réponse :**
```json
{
  "total_penalites": 25,
  "montant_total": "450000.00",
  "stats_par_type": {
    "RETARD_PALIER": {
      "label": "Pénalité de retard par palier",
      "count": 23,
      "montant_total": "430000.00"
    },
    "RETARD_MANUEL": {
      "label": "Pénalité manuelle",
      "count": 2,
      "montant_total": "20000.00"
    }
  },
  "stats_par_palier": [
    {
      "palier": "Palier-3",
      "count": 15,
      "montant_total": "300000.00"
    },
    {
      "palier": "Palier-6",
      "count": 8,
      "montant_total": "150000.00"
    }
  ],
  "top_membres_penalites": [
    {
      "emprunt__membre__numero_membre": "ENS-0001",
      "emprunt__membre__utilisateur__first_name": "Jean",
      "emprunt__membre__utilisateur__last_name": "Dupont",
      "count": 3,
      "montant_total": "75000.00"
    }
  ],
  "evolution_mensuelle": [
    {
      "mois": "2026-03-01",
      "count": 5,
      "montant_total": "100000.00"
    }
  ]
}
```

### 3. Pénalités par emprunt
```
GET /api/transactions/penalites-emprunt/par_emprunt/?emprunt_id=uuid-emprunt
```

**Réponse :**
```json
{
  "emprunt_info": {
    "id": "uuid-emprunt",
    "membre": {
      "numero": "ENS-0001",
      "nom": "Jean Dupont"
    },
    "montant_initial": "100000.00",
    "montant_total_actuel": "145000.00",
    "montant_rembourse": "20000.00",
    "statut": "EN_RETARD",
    "date_emprunt": "2026-01-15T10:00:00Z",
    "nombre_penalites": 2,
    "total_penalites": "45000.00"
  },
  "penalites": [
    {
      "palier": "Palier-3",
      "montant_total_penalite": "22500.00",
      "date_application": "2026-04-15T10:00:00Z",
      "justification": "Pénalité automatique Palier-3..."
    },
    {
      "palier": "Palier-6",
      "montant_total_penalite": "22500.00",
      "date_application": "2026-07-15T10:00:00Z",
      "justification": "Pénalité automatique Palier-6..."
    }
  ]
}
```

### 4. Suivi détaillé d'un emprunt
```
GET /api/transactions/emprunts-suivi/{emprunt_id}/
```

**Réponse complète avec toutes les pénalités et remboursements :**
```json
{
  "id": "uuid-emprunt",
  "membre_info": {
    "numero_membre": "ENS-0001",
    "nom_complet": "Jean Dupont"
  },
  "montant_initial_emprunte": "97000.00",
  "montant_emprunte": "97000.00",
  "montant_total_a_rembourser": "145000.00",
  "montant_rembourse": "20000.00",
  "montant_restant_a_rembourser": "125000.00",
  "statut": "EN_RETARD",
  "penalites": [
    {
      "palier": "Palier-3",
      "montant_total_penalite": "22500.00",
      "formule_calcul": "150,000 × 5% + 15,000 = 22,500 FCFA",
      "justification": "Pénalité automatique Palier-3 appliquée après 3 sessions..."
    }
  ],
  "nombre_penalites": 2,
  "total_penalites": "45000.00",
  "remboursements_details": [
    {
      "montant": "20000.00",
      "date_remboursement": "2026-03-01T10:00:00Z"
    }
  ]
}
```

### 5. Historique chronologique complet
```
GET /api/transactions/emprunts-suivi/{emprunt_id}/historique_complet/
```

**Réponse avec timeline complète :**
```json
{
  "emprunt_id": "uuid-emprunt",
  "membre": {
    "numero": "ENS-0001",
    "nom": "Jean Dupont"
  },
  "historique_chronologique": [
    {
      "type": "creation",
      "date": "2026-01-15T10:00:00Z",
      "description": "Création de l'emprunt de 97,000 FCFA",
      "montant": "97000.00",
      "montant_total_apres": "97000.00",
      "details": {
        "taux_interet": "3.00",
        "echeance": "2026-03-15"
      }
    },
    {
      "type": "penalite",
      "date": "2026-04-15T10:00:00Z",
      "description": "Pénalité Palier-3 appliquée",
      "montant": "22500.00",
      "montant_total_apres": "119500.00",
      "details": {
        "palier": "Palier-3",
        "sessions_ecoulees": 3,
        "montant_reste_avant": "97000.00",
        "taux_applique": "5.00",
        "montant_interet_taux": "7500.00",
        "montant_penalite_fixe": "15000.00",
        "formule": "97,000 × 5% + 15,000 = 22,500 FCFA",
        "justification": "Pénalité automatique Palier-3..."
      }
    },
    {
      "type": "remboursement",
      "date": "2026-05-01T10:00:00Z",
      "description": "Remboursement de 20,000 FCFA",
      "montant": "-20000.00",
      "montant_total_apres": "99500.00"
    }
  ],
  "situation_actuelle": {
    "montant_total_a_rembourser": "145000.00",
    "montant_rembourse": "20000.00",
    "montant_restant": "125000.00",
    "statut": "EN_RETARD",
    "pourcentage_rembourse": "13.79",
    "is_en_retard": true,
    "jours_de_retard": 65
  },
  "resume": {
    "nombre_penalites": 2,
    "total_penalites": "45000.00",
    "nombre_remboursements": 1,
    "total_rembourse": "20000.00"
  }
}
```

## Utilisation pour la transparence

### 1. Justification devant les membres
L'endpoint `historique_complet` fournit une timeline complète avec :
- Date exacte de chaque événement
- Formule de calcul détaillée pour chaque pénalité
- Justification automatique générée
- Montants cumulés à chaque étape

### 2. Audit et contrôle
- Toutes les pénalités sont tracées avec leur contexte
- Impossible de "perdre" l'historique des calculs
- Distinction claire entre pénalités automatiques et manuelles
- Statistiques globales pour le suivi de gestion

### 3. Interface utilisateur
Le frontend peut utiliser ces données pour :
- Afficher des graphiques d'évolution
- Générer des rapports PDF justificatifs
- Créer des alertes pour les membres en retard
- Fournir des explications détaillées sur chaque pénalité

## Sécurité et permissions

- **Lecture** : Accessible à tous (transparence)
- **Écriture** : Réservée aux administrateurs
- **Création automatique** : Via le système de pénalités par paliers
- **Audit trail** : Chaque pénalité garde la trace de qui l'a appliquée