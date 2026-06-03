# Flux des Caisses : Inscription et Fonds Social

## Vue d'ensemble

Le système utilise **deux caisses distinctes** pour séparer les flux financiers :

1. **Caisse Inscription** : Dédiée aux paiements d'inscription des membres
2. **Fonds Social** : Alimenté par les solidarités et renflouements, utilisé pour les assistances

## 🏦 CAISSE INSCRIPTION

### Structure
- **Modèle** : `CaisseInscription`
- **Portée** : Une caisse par exercice
- **Montant** : `montant_total` (Decimal)
- **Historique** : `MouvementCaisseInscription`

### ➕ ENTRÉES (Sources d'alimentation)

#### 1. Paiements d'inscription des membres
**Source** : `PaiementInscription.save()`
```python
# Lors de la création d'un paiement d'inscription
montant_pour_caisse = min(montant_payé, montant_inscription_du)
caisse.ajouter_montant(montant_pour_caisse, description=f"Inscription {numero_membre}")
```

**Détails** :
- Seule la partie "due" alimente la caisse (pas les surplus)
- Les surplus vont directement en épargne personnelle
- Un seul paiement par membre (contrainte unique)

**Exemple** :
- Inscription due : 50 000 FCFA
- Membre paie : 70 000 FCFA
- → Caisse inscription : +50 000 FCFA
- → Épargne membre : +20 000 FCFA (surplus)

### ➖ SORTIES (Utilisations)

#### 1. Collations de session
**Source** : `Session._retirer_collation_fonds_social()`
```python
if self.montant_collation > 0:
    caisse.retirer_montant(
        self.montant_collation,
        f"Collation Session {self.nom} - {self.date_session}"
    )
```

#### 2. Autres dépenses de session
**Source** : `Session._retirer_collation_fonds_social()`
```python
if self.montant_autre_depense > 0:
    caisse.retirer_montant(
        self.montant_autre_depense,
        f"Autre dépense Session {self.nom} - {motif}"
    )
```

**Note** : Ces retraits créent automatiquement des `DépenseExercice` pour traçabilité.

### 📊 Mouvements tracés
Chaque opération crée un `MouvementCaisseInscription` :
- **Type** : 'ENTREE' ou 'SORTIE'
- **Montant** : Montant de l'opération
- **Description** : Détail de l'opération
- **Date** : Horodatage automatique

---

## 💰 FONDS SOCIAL

### Structure
- **Modèle** : `FondsSocial`
- **Portée** : Un fonds par exercice
- **Montant** : `montant_total` (Decimal)
- **Historique** : `MouvementFondsSocial`

### ➕ ENTRÉES (Sources d'alimentation)

#### 1. Paiements de solidarité
**Source** : Signal `post_save` sur `PaiementSolidarite`
```python
@receiver(post_save, sender=PaiementSolidarite)
def handle_paiement_post_save(sender, instance, created, **kwargs):
    if created and sender == PaiementSolidarite:
        fonds.ajouter_montant(instance.montant, description=f"Solidarité {numero_membre}")
```

**Détails** :
- Alimentation automatique via signal Django
- Chaque paiement de solidarité alimente le fonds
- Utilise la logique atomique avec `F()` pour éviter les conflits

#### 2. Paiements de renflouement
**Source** : `PaiementRenflouement.save()`
```python
if is_new:
    fonds = FondsSocial.get_fonds_actuel()
    if fonds:
        desc = f"Renflouement {membre.numero_membre} - {cause}"
        fonds.ajouter_montant(self.montant, description=desc)
```

**Détails** :
- Alimentation lors de la création d'un paiement de renflouement
- Contribue à reconstituer le fonds après utilisation

#### 3. Solidarités directes (alternative)
**Source** : `PaiementSolidarite.save()` (méthode alternative)
```python
if is_new:
    fonds = FondsSocial.get_fonds_actuel()
    if fonds:
        desc = f"Solidarité {membre.numero_membre} - Session {session.nom}"
        fonds.ajouter_montant(self.montant, description=desc)
```

### ➖ SORTIES (Utilisations)

#### 1. Assistances accordées aux membres
**Source** : `AssistanceAccordee._traiter_paiement_assistance()`
```python
if not fonds.retirer_montant(
    self.montant,
    f"Assistance {self.type_assistance.nom} pour {self.membre.numero_membre}"
):
    # Échec si fonds insuffisant
    return False
```

**Détails** :
- Vérification automatique de la disponibilité des fonds
- Échec de l'opération si fonds insuffisant
- Traçabilité complète de l'assistance accordée

### 📊 Mouvements tracés
Chaque opération crée un `MouvementFondsSocial` :
- **Type** : 'ENTREE' ou 'SORTIE'
- **Montant** : Montant de l'opération
- **Description** : Détail de l'opération
- **Date** : Horodatage automatique

---

## 🔄 FLUX RÉSUMÉ

### Caisse Inscription
```
ENTRÉES:
├── Paiements inscription membres → +montant_dû
│
SORTIES:
├── Collations sessions → -montant_collation
└── Autres dépenses sessions → -montant_autre_depense
```

### Fonds Social
```
ENTRÉES:
├── Paiements solidarité → +montant_solidarité
└── Paiements renflouement → +montant_renflouement
│
SORTIES:
└── Assistances accordées → -montant_assistance
```

## 🔍 MÉTHODES D'ACCÈS

### Obtenir la caisse/fonds actuel
```python
# Caisse inscription de l'exercice en cours
caisse = CaisseInscription.get_caisse_actuelle()

# Fonds social de l'exercice en cours
fonds = FondsSocial.get_fonds_actuel()
```

### Consulter l'historique
```python
# Mouvements de la caisse inscription
mouvements_caisse = caisse.mouvements.all().order_by('-date_mouvement')

# Mouvements du fonds social
mouvements_fonds = fonds.mouvements.all().order_by('-date_mouvement')
```

### Opérations sécurisées
```python
# Ajout atomique (utilise F() pour éviter les conflits)
caisse.ajouter_montant(montant, "Description")
fonds.ajouter_montant(montant, "Description")

# Retrait avec vérification
if caisse.retirer_montant(montant, "Description"):
    print("Retrait réussi")
else:
    print("Fonds insuffisants")
```

## 🛡️ SÉCURITÉ ET INTÉGRITÉ

### Atomicité
- Utilisation de `F()` pour les mises à jour atomiques
- Transactions Django pour les opérations complexes
- Vérification des soldes avant retrait

### Traçabilité
- Chaque mouvement est enregistré avec description
- Horodatage automatique
- Lien vers l'opération source

### Validation
- Vérification des montants positifs
- Contrôle des soldes disponibles
- Gestion des erreurs avec logs détaillés

## 📈 UTILISATION POUR REPORTING

Ces deux caisses permettent de générer :
- **Bilans financiers** par exercice
- **Suivi des dépenses** (collations, assistances)
- **Analyse des contributions** (inscriptions, solidarités)
- **Historique complet** des mouvements
- **Alertes** en cas de fonds insuffisants