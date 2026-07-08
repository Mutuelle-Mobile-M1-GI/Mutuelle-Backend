# 📊 Guide Complet des Renflouements - Frontend

## 📌 Vue d'ensemble

Les **renflouements** sont les dépenses de l'exercice que les membres doivent rembourser collectivement. Ce guide explique comment les afficher et les tracer.

---

## 🎯 Concepts clés

### Qu'est-ce qu'un renflouement ?

Un renflouement = **Une part des dépenses de l'exercice** attribuée à un membre.

**Formule:**
```
Montant par membre = Total dépenses ÷ Nombre de membres EN_REGLE

Exemple:
- Total dépenses : 500 000 FCFA
- Membres en règle : 5
- Montant par membre : 100 000 FCFA
- Tous les 6 membres (5 EN_REGLE + 1 NON_EN_REGLE) payent 100 000 FCFA
```

### Répartition du renflouement

Le montant est **réparti entre** :
- **Caisse inscription** : Collations + autres dépenses (ex: 40%)
- **Fonds social** : Assistances (ex: 60%)

---

## 🔌 Les 3 Endpoints Principaux

### 1️⃣ Statistiques globales (Léger & Rapide)

```
GET /api/transactions/renflouements/statistiques/?exercice_id={id}
```

**Retourne:** Juste les chiffres clés d'un exercice

**Réponse:**
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
    "total_du": 500000,          ← Les dépenses totales
    "total_paye": 200000,        ← Ce qui a été payé
    "montant_restant": 300000    ← Ce qui manque
  },
  "pourcentages": {
    "taux_recouvrement": 40      ← 40% des dépenses collectées
  }
}
```

**Cas d'usage:**
- Dashboard avec 10+ exercices
- Résumés rapides
- Tableaux de synthèse

---

### 2️⃣ Détail complet d'un exercice (Tous les membres)

```
GET /api/transactions/renflouements/exercice_detail/?exercice_id={id}
```

**Retourne:** Tous les membres + leurs paiements + stats

**Réponse:**
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
        "id": "...",
        "numero_membre": "ENS-001",
        "nom_complet": "Jean Dupont",
        "statut": "EN_REGLE"
      },
      "renflouement": {
        "id": "...",
        "montant_du": 100000,
        "montant_paye": 100000,
        "montant_restant": 0,
        "pourcentage_paye": 100
      },
      "paiements": [
        {
          "id": "...",
          "montant": 100000,
          "montant_caisse_inscription": 40000,
          "montant_fonds_social": 60000,
          "date_paiement": "2026-07-06T10:00:00Z",
          "notes": "Paiement complet"
        }
      ],
      "totals": {
        "montant_du": 100000,
        "montant_paye": 100000,
        "montant_restant": 0,
        "pourcentage_paye": 100
      }
    },
    // ... autres membres
  ],
  "statistiques_globales": {
    "nombre_membres": 5,
    "nombre_membres_soldes": 2,
    "nombre_membres_partiels": 1,
    "nombre_membres_non_payes": 2,
    "montant_total_du": 500000,
    "montant_total_paye": 200000,
    "montant_total_restant": 300000,
    "taux_recouvrement": 40
  }
}
```

**Cas d'usage:**
- Afficher tous les membres d'un exercice
- Voir qui a payé et qui n'a pas payé
- Détails complets pour rapports

---

### 3️⃣ Historique d'un membre (Tous les exercices)

```
GET /api/transactions/renflouements/par_membre/?membre_id={id}
```

**Retourne:** Tous les exercices du membre + cumul

**Réponse:**
```json
{
  "membre": {
    "id": "...",
    "numero_membre": "ENS-001",
    "nom_complet": "Jean Dupont",
    "statut": "EN_REGLE"
  },
  "renflouements_par_exercice": [
    {
      "exercice": "2027",
      "exercice_id": "...",
      "montant_du": 80000,
      "montant_paye": 80000,
      "montant_restant": 0,
      "pourcentage_paye": 100
    },
    {
      "exercice": "ARNO",
      "exercice_id": "...",
      "montant_du": 100000,
      "montant_paye": 100000,
      "montant_restant": 0,
      "pourcentage_paye": 100
    }
  ],
  "cumuls_totaux": {
    "total_du": 180000,           ← Ce qu'il a dû payer au total
    "total_paye": 180000,         ← Ce qu'il a payé au total
    "montant_restant": 0,         ← Ce qu'il reste à payer
    "pourcentage_paye": 100,
    "nombre_exercices": 2
  }
}
```

**Cas d'usage:**
- Profil complet d'un membre
- Historique de tous ses renflouements
- Voir s'il est à jour ou en retard

---

## 📊 Exemple d'affichage Frontend

### Vue 1: Dashboard (Stats globales)

```
┌─────────────────────────────────────────────────────────┐
│  Exercice: ARNO (TERMINÉ)                              │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  💰 Total à collecter        500 000 FCFA              │
│  ✅ Montant collecté          200 000 FCFA (40%)        │
│  ⏳ Montant restant            300 000 FCFA (60%)        │
│                                                          │
│  👥 Membres soldés: 2/5                                │
│  ⏳ Membres en retard: 3/5                              │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

**Endpoint utilisé:** `statistiques/?exercice_id=...`

---

### Vue 2: Détail de l'exercice

```
┌─────────────────────────────────────────────────────────┐
│  Exercice: ARNO - Détails des paiements               │
├─────────────────────────────────────────────────────────┤
│                                                          │
│ ENS-001 - Jean Dupont        100 000 dû ✅ 100 000 payé│
│ ENS-002 - Marie Martin       100 000 dû  ⏳  50 000 payé│
│ ENS-003 - Pierre Bernard     100 000 dû  ❌   0 payé   │
│ ENS-004 - Sophie Leclerc     100 000 dû  ❌   0 payé   │
│ ENS-005 - Luc Fournier       100 000 dû  ✅ 100 000 payé│
│                                                          │
│ TOTAL                        500 000 dû  200 000 payé  │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

**Endpoint utilisé:** `exercice_detail/?exercice_id=...`

---

### Vue 3: Profil d'un membre

```
┌─────────────────────────────────────────────────────────┐
│  ENS-001 - Jean Dupont                                 │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  Exercice ARNO    100 000 dû  100 000 payé ✅ SOLDÉ   │
│  Exercice 2027     80 000 dû   80 000 payé ✅ SOLDÉ   │
│                                                          │
│  CUMUL TOTAL      180 000 dû  180 000 payé ✅ À JOUR  │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

**Endpoint utilisé:** `par_membre/?membre_id=...`

---

## 🔍 Traçabilité

### Comment tracer un paiement ?

**Scénario:** Un paiement de 50 000 FCFA a été effectué. D'où vient-il ?

**Démarche:**

1. **Appeler `exercice_detail/?exercice_id=xxx`**
   - Trouver le membre qui a payé
   - Voir le montant du paiement (50 000 FCFA)

2. **Vérifier la répartition**
   ```json
   "paiements": [
     {
       "montant": 50000,
       "montant_caisse_inscription": 20000,  (40%)
       "montant_fonds_social": 30000         (60%)
     }
   ]
   ```

3. **Voir l'historique du membre**
   - Appeler `par_membre/?membre_id=xxx`
   - Vérifier ses autres exercices

---

## 📋 Statuts de paiement

| Statut | Condition | Affichage |
|--------|-----------|-----------|
| **SOLDÉ** | `montant_restant <= 0` | ✅ Vert |
| **PARTIEL** | `0 < montant_restant < montant_du` | ⏳ Orange |
| **NON PAYÉ** | `montant_paye == 0` | ❌ Rouge |

---

## 💡 Bonnes pratiques Frontend

### 1. Afficher le contexte

```javascript
// Toujours afficher quel exercice on regarde
<ExerciceHeader nom={exercice.nom} statut={exercice.statut} />
```

### 2. Utiliser les bons endpoints

| Besoin | Endpoint |
|--------|----------|
| Dashboard | `statistiques/` |
| Liste des membres | `exercice_detail/` |
| Profil d'un membre | `par_membre/` |

### 3. Calculer les progressions

```javascript
// Barre de progression
const progress = (montant_paye / montant_du) * 100

// Couleur adaptée
const color = montant_restant <= 0 ? 'green' : montant_paye > 0 ? 'orange' : 'red'
```

### 4. Afficher les cumuls

```javascript
// Pour chaque membre, montrer:
- Montant dû (cet exercice)
- Montant payé (cet exercice)
- Montant restant (cet exercice)
- [OPTIONNEL] Cumul tous exercices
```

---

## 🚀 Exemple d'implémentation

### React Hook pour récupérer les données

```javascript
// Récupérer les stats d'un exercice
const { data: stats } = useRenflouementStats(exerciceId);

// Récupérer le détail complet
const { data: detail } = useExerciceDetail(exerciceId);

// Récupérer l'historique d'un membre
const { data: historique } = useMembrRenflouements(membreId);
```

### Affichage conditionnel

```javascript
{detail?.par_membre.map(item => (
  <MemberCard
    key={item.membre.id}
    member={item.membre}
    montantDu={item.totals.montant_du}
    montantPaye={item.totals.montant_paye}
    montantRestant={item.totals.montant_restant}
    paiements={item.paiements}
    statut={item.totals.montant_restant <= 0 ? 'soldé' : 'partiel'}
  />
))}
```

---

## ⚠️ Points importants

### ✅ À faire

- ✅ Afficher le contexte (quel exercice)
- ✅ Utiliser le bon endpoint selon le besoin
- ✅ Afficher les progressions visuellement
- ✅ Tracer les paiements (voir d'où vient l'argent)
- ✅ Montrer les cumuls par membre

### ❌ À éviter

- ❌ Mélanger les exercices dans une même vue
- ❌ Appeler les 3 endpoints pour une même vue
- ❌ Afficher les montants sans contexte
- ❌ Ne pas montrer qui a payé et qui n'a pas payé

---

## 📞 Support

Si tu as besoin d'autres données ou d'autres endpoints, crée un nouveau endpoint spécifique au lieu de modifier les existants.

**Exemples:**
- Renflouements non payés depuis X jours
- Export PDF d'un exercice
- Historique des modifications (audit)

---

**Version:** 1.0  
**Date:** Juillet 2026  
**Auteur:** Backend Team
