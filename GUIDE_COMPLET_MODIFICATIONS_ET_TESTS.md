# 📋 Guide Complet: Modifications et Tests avec Swagger

## 🎯 Vue d'Ensemble des Modifications

Nous avons implémenté **3 fonctionnalités majeures** dans votre système de mutuelle:

1. **Nouvelle Logique "EN RÈGLE"** avec période de grâce
2. **Activation/Désactivation de Membres** 
3. **Correction de la Redistribution des Intérêts**

---

## 🔄 1. NOUVELLE LOGIQUE "EN RÈGLE" - Période de Grâce

### 📖 Concept
Au lieu d'évaluer immédiatement les membres, le système applique une **période de grâce de 3 mois** au début de chaque exercice.

### 🎯 Règles Implémentées

#### Phase 1: Début d'Exercice
- **Tous les membres** → `EN_REGLE` automatiquement
- **Durée**: 3 mois (90 jours) depuis `exercice.date_debut`

#### Phase 2: Période de Grâce (0-3 mois)
- **Statut**: Tous restent `EN_REGLE`
- **Emprunts**: ✅ Autorisés
- **Épargne**: ✅ Libre (sans restriction)
- **Évaluation**: ❌ Aucune

#### Phase 3: Après Période de Grâce (3+ mois)
- **Évaluation normale** selon 4 critères:
  1. ✅ Solidarité à jour
  2. ✅ Renflouement à jour
  3. ✅ Inscription terminée
  4. ✅ Emprunt < 100 FCFA restant

### 🔧 Fichiers Modifiés
- `core/models.py` → `peut_definir_statuts_membre()` + `initialiser_statuts_nouvel_exercice()`
- `core/utils.py` → `calculer_donnees_membre_completes()`
- `transactions/models.py` → `Emprunt.save()` + `PaiementSolidarite.save()`
- `administration/views.py` → Création paiements inscription

---

## 👤 2. ACTIVATION/DÉSACTIVATION DE MEMBRES

### 📖 Concept
Permettre aux administrateurs d'activer/désactiver des membres avec impact sur la redistribution des intérêts.

### 🎯 Fonctionnalités Implémentées

#### Désactivation d'un Membre
- **Route**: `POST /api/core/membres/{id}/desactiver/`
- **Permission**: Administrateur uniquement
- **Validations**:
  - Membre pas déjà désactivé
  - Aucun emprunt en cours (`EN_COURS` ou `EN_RETARD`)
- **Effet**: `membre.actif = False`

#### Activation d'un Membre
- **Route**: `POST /api/core/membres/{id}/activer/`
- **Permission**: Administrateur uniquement
- **Validation**: Membre pas déjà actif
- **Effet**: `membre.actif = True`

#### Impact sur les Intérêts
- **Redistribution**: Seuls les membres `actif=True` reçoivent les intérêts
- **Épargne**: Les membres inactifs gardent leur épargne mais ne gagnent plus d'intérêts

### 🔧 Fichiers Modifiés
- `core/views.py` → Actions `desactiver()` + `activer()` dans `MembreViewSet`
- `core/models.py` → Correction `is_actif` property
- `transactions/models.py` → `distribuer_interets_precomptes()` filtre sur `actif=True`

---

## 💰 3. CORRECTION REDISTRIBUTION DES INTÉRÊTS

### 📖 Concept
S'assurer que seuls les membres actifs reçoivent les intérêts lors de la création d'emprunts.

### 🎯 Logique Corrigée
```python
# Avant: tous_membres = Membre.objects.all()
# Après: tous_membres = Membre.objects.filter(actif=True)
```

### 🔄 Processus de Redistribution
1. **Création d'emprunt** → Calcul de la cagnotte (intérêts précomptés)
2. **Filtrage** → Seuls les membres `actif=True` avec épargne > 0
3. **Répartition** → Au prorata de l'épargne de chaque membre actif
4. **Double enregistrement**:
   - `Interet` → Historique/traçabilité
   - `EpargneTransaction` → Flux financier réel

---

## 🧪 TESTS AVEC SWAGGER

### 🔧 Configuration Swagger (si pas encore fait)

#### 1. Installation
```bash
pip install drf-yasg
```

#### 2. Configuration dans `settings.py`
```python
INSTALLED_APPS = [
    # ... autres apps
    'drf_yasg',
]
```

#### 3. URLs dans `Backend/urls.py`
```python
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

schema_view = get_schema_view(
   openapi.Info(
      title="Mutuelle API",
      default_version='v1',
      description="API de gestion de mutuelle",
   ),
   public=True,
   permission_classes=[permissions.AllowAny],
)

urlpatterns = [
    # ... autres URLs
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
]
```

### 📋 PLAN DE TESTS COMPLET

#### 🎯 Test 1: Période de Grâce - Nouveau Membre

**Objectif**: Vérifier qu'un nouveau membre est EN_REGLE pendant la période de grâce

**Étapes**:
1. **Créer un membre**
   ```
   POST /api/core/membres/
   {
     "utilisateur": {données utilisateur},
     "date_inscription": "2024-01-15"
   }
   ```

2. **Vérifier le statut**
   ```
   GET /api/core/membres/{membre_id}/
   ```
   **Attendu**: `"statut": "EN_REGLE"`

3. **Vérifier données complètes**
   ```
   GET /api/core/membres/{membre_id}/donnees_completes/
   ```
   **Attendu**: `"membre_info.en_regle": true`

#### 🎯 Test 2: Activation/Désactivation de Membre

**Objectif**: Tester les fonctions d'activation/désactivation

**Prérequis**: Token administrateur

**Étapes**:
1. **Désactiver un membre (sans emprunt)**
   ```
   POST /api/core/membres/{membre_id}/desactiver/
   Authorization: Bearer {admin_token}
   ```
   **Attendu**: 
   ```json
   {
     "message": "Membre M001 désactivé avec succès",
     "membre": {"actif": false, ...}
   }
   ```

2. **Tenter de désactiver avec emprunt en cours**
   - D'abord créer un emprunt:
   ```
   POST /api/transactions/emprunts/
   {
     "membre": "{membre_id}",
     "montant_emprunte": 50000
   }
   ```
   - Puis tenter désactivation:
   ```
   POST /api/core/membres/{membre_id}/desactiver/
   ```
   **Attendu**: 
   ```json
   {
     "error": "Impossible de désactiver un membre avec un emprunt en cours"
   }
   ```

3. **Réactiver le membre**
   ```
   POST /api/core/membres/{membre_id}/activer/
   ```
   **Attendu**: 
   ```json
   {
     "message": "Membre M001 activé avec succès",
     "membre": {"actif": true, ...}
   }
   ```

#### 🎯 Test 3: Redistribution des Intérêts

**Objectif**: Vérifier que seuls les membres actifs reçoivent les intérêts

**Étapes**:
1. **Préparer les données**
   - Membre A: actif avec 100 000 FCFA d'épargne
   - Membre B: inactif avec 50 000 FCFA d'épargne
   - Membre C: actif avec 75 000 FCFA d'épargne

2. **Désactiver le Membre B**
   ```
   POST /api/core/membres/{membre_b_id}/desactiver/
   ```

3. **Créer un emprunt (par Membre D)**
   ```
   POST /api/transactions/emprunts/
   {
     "membre": "{membre_d_id}",
     "montant_emprunte": 100000
   }
   ```
   **Cagnotte attendue**: 3 000 FCFA (3% de 100 000)

4. **Vérifier la redistribution**
   ```
   GET /api/transactions/epargne-transactions/?type_transaction=AJOUT_INTERET
   ```
   **Attendu**:
   - Membre A: reçoit ~1 714 FCFA (100k/175k × 3000)
   - Membre B: ne reçoit RIEN (inactif)
   - Membre C: reçoit ~1 286 FCFA (75k/175k × 3000)

#### 🎯 Test 4: Épargne Libre

**Objectif**: Vérifier qu'on peut épargner indépendamment du statut

**Étapes**:
1. **Membre NON_EN_REGLE qui épargne**
   ```
   POST /api/transactions/epargne-transactions/
   {
     "membre": "{membre_non_en_regle_id}",
     "type_transaction": "DEPOT",
     "montant": 25000,
     "session": "{session_id}"
   }
   ```
   **Attendu**: 201 Created (succès)

2. **Membre inactif qui épargne**
   ```
   POST /api/transactions/epargne-transactions/
   {
     "membre": "{membre_inactif_id}",
     "type_transaction": "DEPOT", 
     "montant": 15000,
     "session": "{session_id}"
   }
   ```
   **Attendu**: 201 Created (succès)

#### 🎯 Test 5: Workflow Complet d'Emprunt

**Objectif**: Tester le workflow complet avec la nouvelle logique

**Étapes**:
1. **Vérifier éligibilité**
   ```
   GET /api/core/membres/{membre_id}/donnees_completes/
   ```
   **Vérifier**: `emprunt.montant_max_empruntable > 0`

2. **Créer l'emprunt**
   ```
   POST /api/transactions/emprunts/
   {
     "membre": "{membre_id}",
     "montant_emprunte": 80000
   }
   ```

3. **Vérifier l'emprunt créé**
   ```
   GET /api/transactions/emprunts/{emprunt_id}/
   ```
   **Vérifier**:
   - `montant_emprunte`: 77 600 (net décaissé)
   - `montant_total_a_rembourser`: 80 000
   - `statut`: "EN_COURS"

4. **Vérifier redistribution automatique**
   ```
   GET /api/transactions/epargne-transactions/?type_transaction=AJOUT_INTERET
   ```
   **Vérifier**: Nouvelles transactions d'intérêts pour membres actifs

### 🔍 POINTS DE CONTRÔLE SWAGGER

#### Routes à Tester
```
# Membres
GET    /api/core/membres/
GET    /api/core/membres/{id}/
POST   /api/core/membres/{id}/activer/
POST   /api/core/membres/{id}/desactiver/
GET    /api/core/membres/{id}/donnees_completes/
GET    /api/core/membres/statistiques/

# Emprunts  
GET    /api/transactions/emprunts/
POST   /api/transactions/emprunts/
GET    /api/transactions/emprunts/{id}/

# Épargne
GET    /api/transactions/epargne-transactions/
POST   /api/transactions/epargne-transactions/

# Intérêts (historique)
GET    /api/core/interets/
```

#### Codes de Réponse Attendus
- **200**: Succès (GET, actions réussies)
- **201**: Création réussie (POST)
- **400**: Erreur validation (désactivation avec emprunt)
- **401**: Non authentifié
- **403**: Non autorisé (actions admin)
- **404**: Ressource non trouvée

### 🎯 SCÉNARIOS DE TEST AVANCÉS

#### Scénario A: Changement d'Exercice
1. Créer nouvel exercice
2. Appeler `Membre.initialiser_statuts_nouvel_exercice()`
3. Vérifier que tous les membres sont EN_REGLE
4. Attendre 3 mois (ou modifier date système)
5. Vérifier évaluation normale

#### Scénario B: Membre avec Historique Complexe
1. Membre avec retards de solidarité
2. Période de grâce → reste EN_REGLE
3. Après 3 mois → passe NON_EN_REGLE
4. Régularise sa situation → repasse EN_REGLE

#### Scénario C: Gestion des Intérêts à Grande Échelle
1. 50 membres actifs avec épargnes variées
2. 10 membres inactifs
3. Création de 5 emprunts simultanés
4. Vérifier redistribution proportionnelle correcte

---

## 🚀 COMMANDES UTILES

### Lancer le serveur
```bash
python manage.py runserver
```

### Accéder à Swagger
```
http://localhost:8000/swagger/
```

### Créer un superuser (pour tests admin)
```bash
python manage.py createsuperuser
```

### Obtenir un token admin
```bash
# Via API ou Django shell
python manage.py shell
>>> from rest_framework.authtoken.models import Token
>>> from django.contrib.auth import get_user_model
>>> User = get_user_model()
>>> admin = User.objects.get(is_superuser=True)
>>> token, created = Token.objects.get_or_create(user=admin)
>>> print(token.key)
```

---

## ✅ CHECKLIST DE VALIDATION

### Fonctionnalités de Base
- [ ] Création de membre → statut EN_REGLE pendant période de grâce
- [ ] Épargne libre → aucune restriction de statut
- [ ] Emprunt → validation coefficient + redistribution intérêts
- [ ] Activation/désactivation → impact sur intérêts

### Logique Métier
- [ ] Période de grâce → 3 mois sans évaluation
- [ ] Après période → évaluation selon 4 critères
- [ ] Membres inactifs → pas d'intérêts redistribués
- [ ] Escompte → calcul correct net/nominal

### Sécurité
- [ ] Actions admin → authentification requise
- [ ] Désactivation → bloquée si emprunt en cours
- [ ] Validations → montants, membres, sessions

### Performance
- [ ] Redistribution → transaction atomique
- [ ] Calculs → optimisés avec select_related
- [ ] Logs → informatifs pour debug

---

Ce guide vous donne une roadmap complète pour tester toutes les fonctionnalités implémentées avec Swagger! 🎯