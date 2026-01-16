# Script de Gestion du Fonds Social

Ce script permet de gérer le fonds social de manière **indépendante des autres tables**, sans passer par les logiques métier de collation ou d'assistance.

## Installation

Le script est un **Management Command Django** et est prêt à l'emploi. Aucune installation supplémentaire n'est nécessaire.

## Utilisation

### 1️⃣ **Consulter le fonds social actuel (défaut)**

```bash
python manage.py set_fonds_social
```

Affiche :
- Montant total du fonds social
- Date de création et modification
- Historique des 10 derniers mouvements

---

### 2️⃣ **Définir une valeur spécifique** (set)

```bash
# Définir à 100 000 FCFA pour l'exercice en cours
python manage.py set_fonds_social --operation set --montant 100000

# Définir à 500 000 FCFA pour un exercice spécifique
python manage.py set_fonds_social --operation set --montant 500000 --exercice "Exo de test"

# Avec une description personnalisée
python manage.py set_fonds_social --operation set --montant 100000 --description "Ajustement initial du fonds"
```

---

### 3️⃣ **Ajouter un montant** (add)

```bash
# Ajouter 50 000 FCFA
python manage.py set_fonds_social --operation add --montant 50000

# Ajouter avec description
python manage.py set_fonds_social --operation add --montant 50000 --description "Collecte supplémentaire"

# Pour un exercice spécifique
python manage.py set_fonds_social --operation add --montant 50000 --exercice "UUID_OU_NOM"
```

---

### 4️⃣ **Retirer un montant** (subtract)

```bash
# Retirer 25 000 FCFA
python manage.py set_fonds_social --operation subtract --montant 25000

# Avec description
python manage.py set_fonds_social --operation subtract --montant 25000 --description "Correction d'erreur"
```

---

## Options disponibles

| Option | Requis | Description |
|--------|--------|-------------|
| `--operation` | ❌ | `view` (consulter), `set` (définir), `add` (ajouter), `subtract` (retirer). **Défaut: view** |
| `--montant` | ❌ | Montant en FCFA (requis pour set, add, subtract) |
| `--exercice` | ❌ | UUID ou nom de l'exercice. **Défaut: exercice en cours** |
| `--description` | ❌ | Description de l'opération |

---

## Exemples complets

### Exemple 1: Initialiser à zéro
```bash
python manage.py set_fonds_social --operation set --montant 0 --description "Réinitialisation"
```

### Exemple 2: Vérifier l'état après une collation
```bash
python manage.py set_fonds_social
```

### Exemple 3: Corriger après un problème
```bash
# Le fonds avait 100 000 mais une collation a échoué
# Retirer ce qui aurait dû être prélevé:
python manage.py set_fonds_social --operation subtract --montant 45000 --description "Correction collation Session 3"
```

### Exemple 4: Remplir le fonds social complètement
```bash
python manage.py set_fonds_social --operation set --montant 1000000 --description "Approvisionnement annuel"
```

---

## Avantages

✅ **Indépendant** : Ne déclenche pas les logiques de collation, assistance, ou renflouement  
✅ **Transparent** : Chaque opération est enregistrée dans l'historique des mouvements  
✅ **Flexible** : Peut cibler un exercice spécifique  
✅ **Sûr** : Empêche les retraits si le fonds est insuffisant  
✅ **Auditabilité** : Toutes les opérations sont tracées

---

## Résolution de problèmes

### Erreur: "Aucun exercice en cours trouvé"
→ Créez un exercice EN_COURS ou spécifiez l'UUID d'un exercice existant avec `--exercice`

### Erreur: "Exercice introuvable"
→ Vérifiez le nom de l'exercice (case-insensitive) ou utilisez son UUID

### Erreur: "Fonds insuffisant"
→ Normal ! Le script ne permet pas les retraits si le fonds est insuffisant. Vérifiez le montant.

---

## Notes techniques

- Les montants sont stockés en `Decimal` pour la précision
- Chaque opération crée un enregistrement `MouvementFondsSocial` pour l'audit
- Les opérations sont atomiques (tout ou rien)
- Compatible avec la validation existante du fonds social
