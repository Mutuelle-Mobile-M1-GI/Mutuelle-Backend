# API: Payer un Renflouement avec l'Épargne Personnelle

## Description
Permet à un membre de payer un renflouement en prélevant directement sur son épargne personnelle.

## Endpoint

### URL
```
POST /api/transactions/renflouements/<renflouement_id>/payer_avec_epargne/
```

### Paramètres URL
- `renflouement_id` (UUID, requis): ID du renflouement à payer

## Body de la Requête

```json
{
  "montant": 50000.00,
  "notes": "Paiement depuis l'épargne personnelle"
}
```

### Champs
| Champ | Type | Requis | Description |
|-------|------|--------|-------------|
| `montant` | Decimal | Non | Montant à payer en FCFA. Si absent, le montant restant sera payé entièrement |
| `notes` | String | Non | Notes ou justification du paiement |

## Réponse de Succès (201 Created)

```json
{
  "success": true,
  "message": "Renflouement payé avec succès! 50000.00 FCFA débité de l'épargne",
  "paiement": {
    "id": "uuid-du-paiement",
    "renflouement": "uuid-du-renflouement",
    "montant": "50000.00",
    "montant_caisse_inscription": "35000.00",
    "montant_fonds_social": "15000.00",
    "ratio_caisse_utilise": "70.00",
    "ratio_fonds_utilise": "30.00",
    "session": "uuid-de-la-session",
    "date_paiement": "2026-05-27T12:30:45.123456Z",
    "notes": "Paiement depuis l'épargne personnelle"
  },
  "renflouement": {
    "id": "uuid-du-renflouement",
    "membre": "uuid-du-membre",
    "montant_du": "100000.00",
    "montant_paye": "50000.00",
    "montant_restant": "50000.00",
    "is_solde": false,
    "pourcentage_paye": 50,
    "type_cause": "RENFLOUEMENT_FIN_EXERCICE",
    "cause": "Renflouement fin d'exercice 2025"
  },
  "epargne_transaction": {
    "id": "uuid-de-la-transaction",
    "membre": "uuid-du-membre",
    "type_transaction": "RETRAIT_PRET",
    "montant": "-50000.00",
    "session": "uuid-de-la-session",
    "date_transaction": "2026-05-27T12:30:45.123456Z",
    "notes": "Retrait pour paiement renflouement"
  },
  "resume": {
    "epargne_avant": "150000.00",
    "epargne_utilisee": "50000.00",
    "epargne_apres": "100000.00",
    "montant_du_avant": "100000.00",
    "montant_paye": "50000.00",
    "montant_reste": "50000.00",
    "renflouement_solde": false
  }
}
```

## Réponses d'Erreur

### 400 Bad Request - Montant invalide
```json
{
  "success": false,
  "error": "Le montant à payer doit être supérieur à 0"
}
```

### 400 Bad Request - Montant dépasse le dû
```json
{
  "success": false,
  "error": "Le montant dépasse ce qui est dû. Montant restant: 50000.00 FCFA"
}
```

### 400 Bad Request - Épargne insuffisante
```json
{
  "success": false,
  "error": "Épargne insuffisante. Disponible: 30000.00 FCFA, Nécessaire: 50000.00 FCFA"
}
```

### 400 Bad Request - Pas de session active
```json
{
  "success": false,
  "error": "Aucune session active trouvée"
}
```

### 404 Not Found
```json
{
  "detail": "Not found."
}
```

### 500 Internal Server Error
```json
{
  "success": false,
  "error": "Erreur lors du paiement: [message d'erreur détaillé]"
}
```

## Cas d'Usage

### 1. Payer partiellement un renflouement
```bash
curl -X POST http://localhost:8000/api/transactions/renflouements/550e8400-e29b-41d4-a716-446655440000/payer_avec_epargne/ \
  -H "Content-Type: application/json" \
  -d '{
    "montant": 25000,
    "notes": "Paiement partiel"
  }'
```

### 2. Payer entièrement un renflouement
```bash
curl -X POST http://localhost:8000/api/transactions/renflouements/550e8400-e29b-41d4-a716-446655440000/payer_avec_epargne/ \
  -H "Content-Type: application/json" \
  -d '{
    "notes": "Paiement complet du renflouement"
  }'
```

## Logique Métier

### Processus Transactionnel
1. ✅ Vérification que le renflouement existe
2. ✅ Calcul du montant à payer (ou utilisation du montant fourni)
3. ✅ Vérification que le montant est valide (> 0 et ≤ montant_restant)
4. ✅ Vérification que l'épargne du membre est suffisante
5. ✅ Récupération de la session courante
6. ✅ **Création atomique dans une transaction:**
   - Création d'une `EpargneTransaction` avec type `RETRAIT_PRET` (montant négatif)
   - Création d'un `PaiementRenflouement`
   - Mise à jour automatique du `montant_paye` du renflouement
   - Répartition automatique entre caisse inscription et fonds social
   - Alimentation automatique des caisses

### Répartition du Paiement
Le paiement est réparti proportionnellement selon les ratios définis:
- **Caisse Inscription**: ratio_caisse_inscription%
- **Fonds Social**: ratio_fonds_social%

### Mise à Jour Automatique
Après le paiement:
- ✅ Le statut du renflouement est mis à jour (soldé ou non)
- ✅ Le statut du membre peut être recalculé (EN_REGLE ou NON_EN_REGLE)
- ✅ Les caisses sont alimentées automatiquement
- ✅ Une transaction d'épargne est enregistrée pour traçabilité

## Validations

| Validation | Condition | Message |
|-----------|-----------|---------|
| Montant valide | montant > 0 | "Le montant à payer doit être supérieur à 0" |
| Montant ≤ dû | montant ≤ montant_restant | "Le montant dépasse ce qui est dû..." |
| Épargne suffisante | epargne ≥ montant | "Épargne insuffisante..." |
| Session active | exists(Session.EN_COURS) | "Aucune session active trouvée" |

## Notes Importantes

1. **Transaction Atomique**: L'opération est atomique. En cas d'erreur, tout est annulé.

2. **Épargne Personnelle**: L'épargne utilisée est calculée comme la somme de toutes les `EpargneTransaction` du membre.

3. **Traçabilité Complète**: 
   - Une `EpargneTransaction` enregistre le retrait
   - Un `PaiementRenflouement` enregistre le paiement
   - Les caisses sont alimentées et tracées

4. **Répartition Proportionnelle**: Le montant payé est réparti automatiquement selon les ratios de caisse et fonds social.

5. **Statut du Renflouement**: Le renflouement est marqué comme "soldé" automatiquement si le montant payé >= montant_du.

## Exemple Complet

### Scenario: Membre paye un renflouement en épargne

**État Initial:**
- Renflouement: 100 000 FCFA dû
- Épargne du membre: 150 000 FCFA
- Ratio caisse: 70%, Ratio fonds: 30%

**Requête:**
```bash
POST /api/transactions/renflouements/550e8400-e29b-41d4-a716-446655440000/payer_avec_epargne/
{
  "montant": 50000,
  "notes": "Paiement mensuel"
}
```

**État Final:**
- Renflouement: 50 000 FCFA dû, 50 000 FCFA payé (50% soldé)
- Épargne du membre: 100 000 FCFA
- Caisse inscription: +35 000 FCFA (50 000 × 70%)
- Fonds social: +15 000 FCFA (50 000 × 30%)
- Statut membre: Recalculé automatiquement
