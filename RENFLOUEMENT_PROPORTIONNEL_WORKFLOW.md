# Système de Renflouement Proportionnel

## Vue d'ensemble

Le nouveau système de renflouement proportionnel remplace l'ancien système où tous les renflouements allaient uniquement au fonds social. Désormais, les renflouements sont répartis proportionnellement entre la **caisse inscription** et le **fonds social** selon les sorties réelles de chaque caisse.

## 🔄 Workflow complet

### 1. **Calcul de fin d'exercice**

#### Étape 1 : Calcul des sorties
```
Sorties caisse inscription = Somme(collations + autres dépenses sessions)
Sorties fonds social = Somme(assistances accordées)
Total sorties = Sorties caisse + Sorties fonds
```

#### Étape 2 : Calcul des ratios
```
Ratio caisse inscription = (Sorties caisse / Total sorties) × 100
Ratio fonds social = (Sorties fonds / Total sorties) × 100
```

**Exemple :**
- Sorties caisse inscription : 70 000 FCFA
- Sorties fonds social : 30 000 FCFA
- Total : 100 000 FCFA
- **Ratio caisse : 70%**
- **Ratio fonds : 30%**

#### Étape 3 : Calcul du montant par membre
```
Montant par membre = Total sorties / Nombre de membres EN_REGLE
```

**Exemple :**
- Total sorties : 100 000 FCFA
- Membres en règle : 10
- **Montant par membre : 10 000 FCFA**

#### Étape 4 : Attribution à TOUS les membres
**TOUS les membres actifs** (en règle ET non en règle) reçoivent un renflouement du même montant.

**Exemple :**
- Total sorties : 100 000 FCFA
- Membres en règle : 10
- **Montant par membre : 10 000 FCFA**
- **TOUS les 20 membres actifs** payent 10 000 FCFA
- **Total collecté : 20 × 10 000 = 200 000 FCFA**

### 2. **Paiement des renflouements**

Quand un membre paie son renflouement, le montant est automatiquement réparti :

**Exemple de paiement de 5 000 FCFA :**
```
Montant vers caisse inscription = 5 000 × 70% = 3 500 FCFA
Montant vers fonds social = 5 000 × 30% = 1 500 FCFA
```

### 3. **Traçabilité complète**

Chaque paiement enregistre :
- Montant total payé
- Montant vers caisse inscription
- Montant vers fonds social
- Ratios utilisés
- Date et session

## 📊 Modèles de données

### `RepartitionRenflouementExercice`
Stocke les calculs de fin d'exercice :
```python
{
    'exercice': 'Exercice 2025-2026',
    'total_sorties_caisse_inscription': 70000.00,
    'total_sorties_fonds_social': 30000.00,
    'total_sorties_global': 100000.00,
    'ratio_caisse_inscription': 70.00,
    'ratio_fonds_social': 30.00,
    'nombre_membres_en_regle': 10,
    'nombre_membres_non_en_regle': 10,
    'montant_par_membre': 10000.00,
    'formule_calcul': '100,000 FCFA ÷ 10 membres en règle = 10,000 FCFA par membre'
}
```

### `Renflouement` (modifié)
Nouveaux champs pour le système proportionnel :
```python
{
    'exercice_renflouement': 'UUID de l\'exercice',
    'ratio_caisse_inscription': 70.00,
    'ratio_fonds_social': 30.00,
    'montant_du': 10000.00,
    'cause': 'Renflouement proportionnel fin d\'exercice...'
}
```

### `PaiementRenflouement` (modifié)
Nouveaux champs pour tracer la répartition :
```python
{
    'montant': 5000.00,
    'montant_caisse_inscription': 3500.00,
    'montant_fonds_social': 1500.00,
    'ratio_caisse_utilise': 70.00,
    'ratio_fonds_utilise': 30.00
}
```

## 🔧 API Endpoints

### 1. Calculer les renflouements de fin d'exercice
```http
POST /api/transactions/repartitions-renflouement/calculer_renflouements/
Content-Type: application/json

{
    "exercice_id": "uuid-exercice"
}
```

**Réponse :**
```json
{
    "message": "Renflouements proportionnels créés avec succès",
    "result": {
        "total_sorties_caisse": "70000.00",
        "total_sorties_fonds": "30000.00",
        "total_sorties_global": "100000.00",
        "ratio_caisse": "70.00",
        "ratio_fonds": "30.00",
        "nombre_membres_en_regle": 10,
        "nombre_membres_non_en_regle": 10,
        "montant_par_membre": "10000.00",
        "renflouements_crees": 10
    },
    "repartition": {
        "id": "uuid-repartition",
        "formule_calcul": "100,000 FCFA ÷ 10 membres en règle = 10,000 FCFA par membre",
        "detail_ratios": "Caisse inscription: 70,000 FCFA (70%) | Fonds social: 30,000 FCFA (30%)"
    }
}
```

### 2. Lister les renflouements proportionnels
```http
GET /api/transactions/renflouements-proportionnels/proportionnels/
```

### 3. Simuler un paiement
```http
GET /api/transactions/renflouements-proportionnels/{id}/simulation_paiement/?montant=5000
```

**Réponse :**
```json
{
    "renflouement_id": "uuid-renflouement",
    "membre": "ENS-0001",
    "montant_simule": "5000.00",
    "repartition": {
        "caisse_inscription": "3500.00",
        "fonds_social": "1500.00",
        "total": "5000.00"
    },
    "detail": {
        "caisse_inscription": "3,500 FCFA (70%)",
        "fonds_social": "1,500 FCFA (30%)",
        "total": "5,000 FCFA"
    },
    "montant_restant_apres": "5000.00"
}
```

### 4. Paiements avec répartition
```http
GET /api/transactions/paiements-renflouement-proportionnels/avec_repartition/
```

### 5. Statistiques proportionnelles
```http
GET /api/transactions/renflouements-proportionnels/statistiques_proportionnelles/
```

## 🎯 Avantages du nouveau système

### 1. **Équité financière**
- Chaque caisse est renflouée proportionnellement à ses sorties
- Plus de déséquilibre entre les caisses

### 2. **Transparence totale**
- Calculs basés sur les données réelles
- Formules de calcul enregistrées et consultables
- Traçabilité complète de chaque paiement

### 3. **Flexibilité**
- Ratios calculés automatiquement selon les dépenses réelles
- Adaptation automatique aux variations d'usage des caisses

### 4. **Compatibilité**
- Ancien système préservé pour les renflouements existants
- Migration progressive sans perte de données

## 📈 Exemple concret

### Situation de départ
- **Exercice 2025-2026**
- Sorties caisse inscription : 140 000 FCFA (collations)
- Sorties fonds social : 60 000 FCFA (assistances)
- Total : 200 000 FCFA
- Membres en règle : 20
- **Membres total actifs : 25**

### Calculs
```
Ratio caisse inscription = 140 000 / 200 000 = 70%
Ratio fonds social = 60 000 / 200 000 = 30%
Montant par membre = 200 000 / 20 membres en règle = 10 000 FCFA
TOUS les 25 membres payent 10 000 FCFA
```

### Renflouements créés
**25 renflouements** de 10 000 FCFA chacun avec ratios 70%/30%
- **Total à collecter : 25 × 10 000 = 250 000 FCFA**
- Renflouement des sorties : 200 000 FCFA
- Excédent/réserve : 50 000 FCFA

### Paiement d'un membre (8 000 FCFA)
```
Vers caisse inscription : 8 000 × 70% = 5 600 FCFA
Vers fonds social : 8 000 × 30% = 2 400 FCFA
Reste à payer : 10 000 - 8 000 = 2 000 FCFA
```

## 🔒 Sécurité et validation

### Contrôles automatiques
- Vérification de l'existence de l'exercice
- Prévention des doublons de répartition
- Validation des montants positifs
- Contrôle des ratios (somme = 100%)

### Atomicité
- Toutes les opérations dans des transactions
- Rollback automatique en cas d'erreur
- Cohérence garantie des données

### Audit trail
- Horodatage de tous les calculs
- Traçabilité de qui a lancé les calculs
- Historique complet des paiements

Ce nouveau système garantit une gestion équitable et transparente des renflouements, avec une répartition automatique basée sur l'utilisation réelle de chaque caisse.