# 📚 Documentation Frontend - Paiement Renflouement avec Épargne

## 🎯 Vue d'ensemble

Cette nouvelle fonctionnalité permet aux membres de **payer leurs renflouements en utilisant leur épargne personnelle**. C'est une alternative au paiement en espèces ou par virement.

---

## 📱 Intégration API

### Endpoint

```
POST /api/transactions/renflouements/<id>/payer_avec_epargne/
```

### Format de la Requête

```json
{
  "montant": 50000.00,
  "notes": "Paiement partiel - 1ère tranche"
}
```

### Paramètres

| Paramètre | Type | Requis | Description |
|-----------|------|--------|-------------|
| `id` | UUID | ✅ Oui | ID du renflouement (dans l'URL) |
| `montant` | Decimal | ❌ Non | Montant en FCFA. **Si absent = payer le solde entier** |
| `notes` | String | ❌ Non | Notes/justification du paiement |

### Réponse de Succès (201 Created)

```json
{
  "success": true,
  "message": "Renflouement payé avec succès! 50000.00 FCFA débité de l'épargne",
  "paiement": {
    "id": "uuid",
    "montant": "50000.00",
    "montant_caisse_inscription": "35000.00",
    "montant_fonds_social": "15000.00",
    "ratio_caisse_utilise": "70.00",
    "ratio_fonds_utilise": "30.00",
    "date_paiement": "2026-05-27T12:30:45Z"
  },
  "renflouement": {
    "id": "uuid",
    "montant_du": "100000.00",
    "montant_paye": "50000.00",
    "montant_restant": "50000.00",
    "is_solde": false,
    "pourcentage_paye": 50
  },
  "epargne_transaction": {
    "id": "uuid",
    "type_transaction": "RETRAIT_PRET",
    "montant": "-50000.00",
    "date_transaction": "2026-05-27T12:30:45Z"
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

### Réponses d'Erreur

#### 400 - Épargne insuffisante
```json
{
  "success": false,
  "error": "Épargne insuffisante. Disponible: 30000.00 FCFA, Nécessaire: 50000.00 FCFA"
}
```

#### 400 - Montant invalide
```json
{
  "success": false,
  "error": "Le montant à payer doit être supérieur à 0"
}
```

#### 400 - Montant dépasse le dû
```json
{
  "success": false,
  "error": "Le montant dépasse ce qui est dû. Montant restant: 50000.00 FCFA"
}
```

#### 400 - Aucune session active
```json
{
  "success": false,
  "error": "Aucune session active trouvée"
}
```

---

## 🖥️ Composants Frontend à Implémenter

### 1. Bouton "Payer avec Épargne"

Doit être visible sur la page de détail d'un renflouement, si:
- ✅ Le renflouement n'est pas soldé
- ✅ Le membre a assez d'épargne
- ✅ Une session est active

```jsx
<button 
  onClick={handlePayerAvecEpargne}
  className="btn btn-success"
  disabled={renflouement.is_solde || epargneDisponible < montantMin}
>
  💰 Payer avec Épargne
</button>
```

### 2. Modal de Paiement

Affiche un formulaire avec:

```jsx
<Modal title="Payer un Renflouement avec Épargne">
  <div className="form-group">
    <label>Montant dû</label>
    <input 
      type="text" 
      value={renflouement.montant_du} 
      disabled 
    />
  </div>
  
  <div className="form-group">
    <label>Montant payé</label>
    <input 
      type="text" 
      value={renflouement.montant_paye} 
      disabled 
    />
  </div>
  
  <div className="alert alert-info">
    <strong>💎 Épargne disponible:</strong> {epargneDisponible} FCFA
  </div>
  
  <div className="form-group">
    <label>Montant à payer *</label>
    <input 
      type="number"
      placeholder="Laisser vide pour payer le solde entier"
      value={montantPartiel}
      onChange={(e) => setMontantPartiel(e.target.value)}
      max={renflouement.montant_restant}
      max={epargneDisponible}
    />
    <small className="text-muted">
      Max: {Math.min(renflouement.montant_restant, epargneDisponible)} FCFA
    </small>
  </div>
  
  <div className="form-group">
    <label>Notes (optionnel)</label>
    <textarea 
      placeholder="Ex: Paiement de la 1ère tranche"
      value={notes}
      onChange={(e) => setNotes(e.target.value)}
    />
  </div>
  
  <button onClick={submitPaiement} className="btn btn-primary">
    Confirmer le paiement
  </button>
</Modal>
```

### 3. Validation Côté Client

```javascript
// Valider avant d'envoyer
function validerPaiement() {
  const montant = parseFloat(montantPartiel) || renflouement.montant_restant;
  
  // Montant valide
  if (montant <= 0) {
    showError("Le montant doit être > 0");
    return false;
  }
  
  // Ne dépasse pas le dû
  if (montant > renflouement.montant_restant) {
    showError(`Montant max: ${renflouement.montant_restant} FCFA`);
    return false;
  }
  
  // Épargne suffisante
  if (montant > epargneDisponible) {
    showError(`Épargne insuffisante. Disponible: ${epargneDisponible} FCFA`);
    return false;
  }
  
  return true;
}
```

### 4. Fonction de Paiement

```javascript
async function payerAvecEpargne(renflouementId) {
  try {
    setLoading(true);
    
    const montant = montantPartiel 
      ? parseFloat(montantPartiel) 
      : undefined; // undefined = payer le solde entier
    
    const body = {
      montant: montant,
      notes: notes
    };
    
    // Validation client
    if (!validerPaiement()) {
      setLoading(false);
      return;
    }
    
    // Appel API
    const response = await fetch(
      `/api/transactions/renflouements/${renflouementId}/payer_avec_epargne/`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify(body)
      }
    );
    
    if (!response.ok) {
      const error = await response.json();
      showError(error.error || "Erreur lors du paiement");
      return;
    }
    
    const data = await response.json();
    
    // Succès
    showSuccess(data.message);
    
    // Afficher le résumé
    displayResume(data.resume);
    
    // Rafraîchir les données
    await fetchRenflouement(renflouementId);
    
    // Fermer le modal après 2 secondes
    setTimeout(() => closeModal(), 2000);
    
  } catch (error) {
    showError(error.message);
  } finally {
    setLoading(false);
  }
}
```

### 5. Affichage du Résumé

```jsx
function displayResume(resume) {
  return (
    <div className="alert alert-success">
      <h5>✅ Paiement effectué avec succès!</h5>
      
      <table className="table table-sm mt-3">
        <tbody>
          <tr>
            <td>Épargne avant</td>
            <td className="text-right"><strong>{resume.epargne_avant} FCFA</strong></td>
          </tr>
          <tr>
            <td>Montant utilisé</td>
            <td className="text-right text-danger">-{resume.epargne_utilisee} FCFA</td>
          </tr>
          <tr>
            <td>Épargne après</td>
            <td className="text-right"><strong>{resume.epargne_apres} FCFA</strong></td>
          </tr>
          <tr className="border-top">
            <td>Renflouement payé</td>
            <td className="text-right text-success">+{resume.montant_paye} FCFA</td>
          </tr>
          <tr>
            <td>Montant restant</td>
            <td className="text-right"><strong>{resume.montant_reste} FCFA</strong></td>
          </tr>
          {resume.renflouement_solde && (
            <tr className="bg-success text-white">
              <td><strong>✓ RENFLOUEMENT SOLDÉ</strong></td>
              <td className="text-right"><strong>100%</strong></td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
```

---

## 🔄 Flux Complet d'Utilisation

### Scénario: Membre paye un renflouement en 3 tranches

```
┌─────────────────────────────────────────────────────────────┐
│ ÉTAT INITIAL                                                │
├─────────────────────────────────────────────────────────────┤
│ Renflouement:  150 000 FCFA dû (0% payé)                   │
│ Épargne:       200 000 FCFA disponible                      │
└─────────────────────────────────────────────────────────────┘
              ↓
    Membre clique "Payer avec Épargne"
              ↓
┌─────────────────────────────────────────────────────────────┐
│ PAIEMENT 1: 50 000 FCFA                                     │
├─────────────────────────────────────────────────────────────┤
│ ✅ Montant payé: 50 000 FCFA                                │
│ ✅ Épargne restante: 150 000 FCFA                           │
│ ✅ Renflouement: 50 000/150 000 (33% payé)                  │
└─────────────────────────────────────────────────────────────┘
              ↓
    Membre clique à nouveau "Payer avec Épargne"
              ↓
┌─────────────────────────────────────────────────────────────┐
│ PAIEMENT 2: 50 000 FCFA                                     │
├─────────────────────────────────────────────────────────────┤
│ ✅ Montant payé: 50 000 FCFA                                │
│ ✅ Épargne restante: 100 000 FCFA                           │
│ ✅ Renflouement: 100 000/150 000 (67% payé)                 │
└─────────────────────────────────────────────────────────────┘
              ↓
    Membre clique une 3ème fois (sans montant = solde)
              ↓
┌─────────────────────────────────────────────────────────────┐
│ PAIEMENT 3: 50 000 FCFA (le solde)                          │
├─────────────────────────────────────────────────────────────┤
│ ✅ Montant payé: 50 000 FCFA                                │
│ ✅ Épargne restante: 50 000 FCFA                            │
│ ✅ Renflouement: 150 000/150 000 (100% SOLDÉ ✓)           │
└─────────────────────────────────────────────────────────────┘
```

---

## 📊 Affichage des Données

### Liste des Renflouements

Ajouter ces colonnes:

| Colonne | Affichage | Style |
|---------|-----------|-------|
| Montant dû | 150 000 FCFA | Normal |
| Montant payé | 50 000 FCFA | Vert si payé, Rouge sinon |
| Restant | 100 000 FCFA | 🔴 Rouge si > 0, 🟢 Vert si soldé |
| Barre de progression | ████░░░░░░ (50%) | Dynamique |
| Action | "Payer avec Épargne" | Bouton vert |

### Exemple de Tableau

```jsx
<table className="table">
  <thead>
    <tr>
      <th>Cause</th>
      <th>Montant Dû</th>
      <th>Montant Payé</th>
      <th>Restant</th>
      <th>Progression</th>
      <th>Actions</th>
    </tr>
  </thead>
  <tbody>
    {renflouements.map(r => (
      <tr key={r.id}>
        <td>{r.cause}</td>
        <td>{r.montant_du} FCFA</td>
        <td className="text-success">{r.montant_paye} FCFA</td>
        <td className={r.montant_restant > 0 ? "text-danger" : "text-success"}>
          {r.montant_restant} FCFA
        </td>
        <td>
          <div className="progress">
            <div 
              className={`progress-bar ${r.pourcentage_paye >= 100 ? 'bg-success' : 'bg-warning'}`}
              style={{width: `${r.pourcentage_paye}%`}}
            >
              {r.pourcentage_paye.toFixed(0)}%
            </div>
          </div>
        </td>
        <td>
          {!r.is_solde && (
            <button 
              onClick={() => openPaymentModal(r.id)}
              className="btn btn-sm btn-success"
            >
              💰 Payer
            </button>
          )}
          {r.is_solde && (
            <span className="badge bg-success">✓ Soldé</span>
          )}
        </td>
      </tr>
    ))}
  </tbody>
</table>
```

---

## 🔐 Validations Important

### À Faire Côté Frontend

1. ✅ Vérifier montant > 0
2. ✅ Vérifier montant ≤ montant_restant
3. ✅ Vérifier épargne ≥ montant
4. ✅ Afficher un message de confirmation
5. ✅ Afficher un loader pendant l'envoi

### À Faire Côté Backend (API)

1. ✅ Vérifier toutes les validations
2. ✅ Créer la transaction atomiquement
3. ✅ Mettre à jour le renflouement
4. ✅ Enregistrer la transaction d'épargne
5. ✅ Alimenter les caisses

---

## 📞 Support & Gestion d'Erreurs

### Messages d'Erreur Courants

```javascript
const errorMessages = {
  'Épargne insuffisante': '💎 Vous n\'avez pas assez d\'épargne pour ce paiement',
  'Le montant dépasse ce qui est dû': '⚠️ Vous ne pouvez pas payer plus que ce qui est dû',
  'Le montant à payer doit être supérieur à 0': '⚠️ Le montant doit être positif',
  'Aucune session active trouvée': '🔴 Aucune session active actuellement',
  'Objet non trouvé': '❌ Ce renflouement n\'existe pas'
};
```

### Gestion des Erreurs

```javascript
try {
  // Appel API
  const response = await fetch(...);
  
  if (!response.ok) {
    const error = await response.json();
    const userMessage = errorMessages[error.error] || error.error;
    showError(userMessage);
    return;
  }
  
  // Success
  showSuccess('Paiement effectué avec succès!');
  
} catch (error) {
  showError('Erreur réseau: ' + error.message);
}
```

---

## 🧪 Test dans Postman/Insomnia

### 1. Paiement Partiel

```bash
POST http://localhost:8000/api/transactions/renflouements/{id}/payer_avec_epargne/
Content-Type: application/json

{
  "montant": 50000,
  "notes": "1ère tranche"
}
```

**Réponse attendue:** 201 Created avec les détails du paiement

### 2. Paiement Complet

```bash
POST http://localhost:8000/api/transactions/renflouements/{id}/payer_avec_epargne/
Content-Type: application/json

{
  "notes": "Solde final"
}
```

**Réponse attendue:** 201 Created avec `is_solde: true`

---

## 📋 Checklist d'Implémentation

- [ ] Récupérer l'ID du renflouement
- [ ] Afficher le bouton "Payer avec Épargne"
- [ ] Créer le modal de paiement
- [ ] Implémenter la validation côté client
- [ ] Implémenter l'appel API
- [ ] Afficher le résumé du paiement
- [ ] Rafraîchir les données après paiement
- [ ] Gérer les erreurs correctement
- [ ] Tester avec différents montants
- [ ] Tester le scénario complet (3 tranches)

---

## 🎨 Design Tips

- 💰 Utiliser un gradient **vert** pour l'épargne
- 🔴 Utiliser du **rouge** pour les montants restants
- 🟢 Utiliser du **vert** pour les paiements réussis
- ⚠️ Afficher un **badge jaune** pour les paiements partiels
- ✅ Afficher un **badge vert** pour les renflouements soldés

---

## 📞 FAQ

**Q: Comment savoir si je peux payer avec épargne?**  
R: Votre épargne doit être ≥ au montant que vous voulez payer.

**Q: Je peux payer en plusieurs fois?**  
R: Oui! Vous pouvez faire plusieurs paiements partiels jusqu'à solder le renflouement.

**Q: Mon épargne disparaît quand je paie?**  
R: Oui, elle est utilisée pour payer le renflouement. Vous pouvez remplir votre épargne via des dépôts.

**Q: Je peux annuler un paiement?**  
R: Non, une fois envoyé, le paiement est définitif. Contactez l'admin si besoin.

**Q: Où va mon argent quand je paie?**  
R: Il est réparti entre la caisse inscription (70%) et le fonds social (30%) selon les ratios de l'exercice.
