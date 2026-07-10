# 🔄 Changements Backend - Renflouements Screen

## 📝 Résumé des changements

### 1. ✅ Enrichissement de `/core/exercices/` avec stats de renflouement

**Date:** Juillet 2026  
**Fichier modifié:** `core/serializers.py` - `ExerciceSerializer`

### Qu'est-ce qui a changé ?

L'endpoint `GET /core/exercices/` retourne maintenant pour **chaque exercice** les statistiques de renflouement :

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "nom": "ARNO",
  "date_debut": "2026-01-01",
  "date_fin": "2026-12-31",
  "statut": "TERMINE",
  "description": "Exercice 2026",
  "is_en_cours": false,
  "nombre_sessions": 5,
  "fonds_social_info": {
    "montant_total": 50000,
    "derniere_modification": "2026-07-06T10:00:00Z"
  },
  "renflouement_stats": {
    "montant_total_du": 500000,          ✅ NOUVEAU
    "montant_total_paye": 200000,        ✅ NOUVEAU
    "montant_total_restant": 300000,     ✅ NOUVEAU
    "taux_recouvrement": 40,             ✅ NOUVEAU
    "nombre_renflouements": 5,           ✅ NOUVEAU
    "nombre_soldes": 2                   ✅ NOUVEAU
  },
  "date_creation": "2026-01-01T00:00:00Z",
  "date_modification": "2026-07-06T10:00:00Z"
}
```

---

## 🎯 Comment ça fonctionne ?

### Backend Logic

```python
def get_renflouement_stats(self, obj):
    # 1. Récupérer TOUS les renflouements de cet exercice
    #    (filtrés par type_cause='RENFLOUEMENT_FIN_EXERCICE')
    
    # 2. Aggréger les montants:
    #    - montant_total_du = SUM(montant_du)
    #    - montant_total_paye = SUM(montant_paye)
    
    # 3. Calculer les dérivés:
    #    - montant_total_restant = montant_total_du - montant_total_paye
    #    - taux_recouvrement = (montant_total_paye / montant_total_du) * 100
    
    # 4. Compter:
    #    - nombre_renflouements = total créés
    #    - nombre_soldes = renflouements où montant_paye >= montant_du
```

---

## 📊 Impact sur le Frontend

### Avant (Old Way)

```javascript
// 1 appel pour les exercices
GET /core/exercices/
// Pas de stats, le frontend doit les calculer

// N appels pour avoir les stats de chaque exercice
GET /transactions/renflouements/?exercice_id=X
GET /transactions/renflouements/?exercice_id=Y
GET /transactions/renflouements/?exercice_id=Z
```

**Total:** 1 + N appels

### Après (New Way - Optimized)

```javascript
// 1 appel ONLY - stats incluses
GET /core/exercices/
// Response includes renflouement_stats for each exercise

// Stats de chaque exercice sont DANS la liste
```

**Total:** 1 appel (pour la liste) + appels pour détails si needed

---

## 🚀 Utilisation Frontend

### 1. Récupérer la liste avec stats

```javascript
import { useExercises } from "../../hooks/useListData";

function RenflouementScreen() {
  const { data: exercices } = useExercises();
  
  // Chaque exercice a maintenant les stats
  exercices?.forEach(exe => {
    console.log(exe.renflouement_stats.montant_total_du);
    console.log(exe.renflouement_stats.montant_total_paye);
    console.log(exe.renflouement_stats.taux_recouvrement);
  });
}
```

### 2. Afficher les stats dans la liste

```javascript
const ExerciceSimpleCard = ({ item }) => {
  const stats = item.renflouement_stats;
  
  return (
    <View>
      <Text>{item.nom}</Text>
      
      {/* ✅ Maintenant vous pouvez utiliser stats directement */}
      <Text>À collecter: {formatCurrency(stats.montant_total_du)}</Text>
      <Text>Collecté: {formatCurrency(stats.montant_total_paye)}</Text>
      <Text>Restant: {formatCurrency(stats.montant_total_restant)}</Text>
      <Text>Taux: {stats.taux_recouvrement.toFixed(0)}%</Text>
    </View>
  );
};
```

### 3. Enrichir le dashboard avec ces données

```javascript
const exercicesWithStats = useMemo(() => {
  return exercices.map((exe) => ({
    ...exe,
    // Stats DÉJÀ incluses maintenant !
    // Plus besoin de calculer ou fetcher séparément
  }));
}, [exercices]);

// Aucun appel API supplémentaire needed!
```

---

## 📋 Endpoints existants (Déjà implémentés dans la précédente phase)

### 1. `/transactions/renflouements/exercice_detail/?exercice_id=xxx`
**Utilité:** Détail complet d'un exercice avec tous les membres et paiements

```json
{
  "exercice": { "id": "...", "nom": "ARNO" },
  "par_membre": [
    {
      "membre": { "nom_complet": "Jean Dupont", "numero_membre": "ENS-001" },
      "montants": { "montant_du": 100000, "montant_paye": 100000 },
      "paiements": [...]
    }
  ],
  "statistiques_globales": { "taux_recouvrement": 100, ... }
}
```

**Quand l'utiliser:** Clic sur un exercice pour voir le détail

---

### 2. `/transactions/renflouements/par_membre/?membre_id=xxx`
**Utilité:** Historique de tous les renflouements d'un membre (tous exercices)

```json
{
  "membre": { "nom_complet": "Jean Dupont", "numero_membre": "ENS-001" },
  "renflouements_par_exercice": [
    { "exercice": "ARNO", "montant_du": 100000, "montant_paye": 100000 },
    { "exercice": "2027", "montant_du": 80000, "montant_paye": 80000 }
  ],
  "cumuls_totaux": {
    "total_du": 180000,
    "total_paye": 180000,
    "pourcentage_paye": 100
  }
}
```

**Quand l'utiliser:** Clic sur un membre pour voir tous ses renflouements

---

## 🧪 Données de Test

### Scénario 1: Exercice avec renflouement

```javascript
// GET /core/exercices/
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "nom": "ARNO",
  "statut": "TERMINE",
  "renflouement_stats": {
    "montant_total_du": 500000,
    "montant_total_paye": 200000,
    "montant_total_restant": 300000,
    "taux_recouvrement": 40,
    "nombre_renflouements": 5,
    "nombre_soldes": 2
  }
}
```

### Scénario 2: Exercice sans renflouement (pas encore clôturé)

```javascript
{
  "id": "...",
  "nom": "2027",
  "statut": "EN_COURS",
  "renflouement_stats": {
    "montant_total_du": 0,
    "montant_total_paye": 0,
    "montant_total_restant": 0,
    "taux_recouvrement": 0,
    "nombre_renflouements": 0,
    "nombre_soldes": 0
  }
}
```

---

## ✅ Checklist d'Intégration Frontend

- [ ] Utiliser `item.renflouement_stats` dans le composant `ExerciceSimpleCard`
- [ ] Afficher les 3 montants (dû, payé, restant)
- [ ] Afficher le taux de recouvrement en pourcentage
- [ ] Afficher le badge "N/M soldés" si pertinent
- [ ] Utiliser `/exercice_detail/` pour le modal détail
- [ ] Utiliser `/par_membre/` pour le profil d'un membre
- [ ] Tester avec des exercices EN_COURS (pas de renflouements)
- [ ] Tester avec des exercices TERMINE (avec renflouements)

---

## 🔍 Vérification

### Comment vérifier que ça marche ?

```bash
# 1. Appeler l'endpoint
curl -X GET http://localhost:8000/api/core/exercices/

# 2. Vérifier que chaque exercice a "renflouement_stats"
# avec montant_total_du, montant_total_paye, etc.

# 3. Vérifier que les montants correspondent à:
#    - DépenseExercice pour total_du
#    - Renflouement.montant_paye pour total_paye
```

---

## 📞 Endpoints de Référence

| Endpoint | Utilité | Paramètres |
|----------|---------|-----------|
| `GET /core/exercices/` | **Liste tous les exercices AVEC stats** | `?search=ARNO`, `?statut=TERMINE` |
| `GET /transactions/renflouements/exercice_detail/` | Détail complet d'un exercice | `exercice_id=xxx` (requis) |
| `GET /transactions/renflouements/par_membre/` | Historique d'un membre | `membre_id=xxx` (requis) |
| `GET /transactions/renflouements/statistiques/` | Stats globales (optionnel) | `exercice_id=xxx` |

---

## 🎓 Notes importantes

### Performance
- `renflouement_stats` est calculé à la volée (pas de cache)
- Pour une liste de 100 exercices, cela peut être un peu lent
- Solution future: Ajouter un cache Redis ou un champ dénormalisé

### Filtrage
- Les stats ne filtrés que par `exercice_renflouement` + `type_cause='RENFLOUEMENT_FIN_EXERCICE'`
- Les autres types de renflouements (manuels, anciennes données) sont ignorés

### Calculs
- Tous les montants en FCFA (nombres entiers)
- Taux de recouvrement en pourcentage (0-100)
- Montant restant = montant_du - montant_paye (peut être négatif si surpayé)

---

**Version:** 1.0  
**Date:** Juillet 2026  
**Statut:** ✅ PRÊT POUR PRODUCTION
