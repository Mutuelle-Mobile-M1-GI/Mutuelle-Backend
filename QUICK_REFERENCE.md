# ⚡ Quick Reference - Renflouement Stats

## 🎯 The Change in 30 Seconds

**Before:** Need 2+ API calls to get exercise stats  
**After:** Stats included in `/core/exercices/` response

---

## 📱 Use in Components

### Display Exercise Stats

```javascript
import { useExercises } from "hooks/useListData";

function RenflouementList() {
  const { data: exercices } = useExercises();
  
  return exercices?.map(exe => (
    <View key={exe.id}>
      <Text>{exe.nom}</Text>
      
      {/* ✅ Stats now available directly */}
      <Text>À collecter: {formatCurrency(exe.renflouement_stats.montant_total_du)}</Text>
      <Text>Collecté: {formatCurrency(exe.renflouement_stats.montant_total_paye)}</Text>
      <Text>Restant: {formatCurrency(exe.renflouement_stats.montant_total_restant)}</Text>
      <Text>Taux: {exe.renflouement_stats.taux_recouvrement.toFixed(0)}%</Text>
    </View>
  ));
}
```

---

## 📊 Data Structure

```javascript
exercise.renflouement_stats = {
  montant_total_du: 500000,        // FCFA - Total to collect
  montant_total_paye: 200000,      // FCFA - Total paid
  montant_total_restant: 300000,   // FCFA - Still needed
  taux_recouvrement: 40.0,         // % - Collection rate
  nombre_renflouements: 5,         // Count - Total renflouements
  nombre_soldes: 2,                // Count - Fully paid ones
}
```

---

## 🔧 Common Patterns

### Progress Bar
```javascript
const progress = exe.renflouement_stats.montant_total_paye / 
                 exe.renflouement_stats.montant_total_du;
```

### Status Color
```javascript
const color = exe.renflouement_stats.montant_total_restant <= 0 
  ? '#10B981' (green)    // Fully paid
  : '#EF4444';           // Still owed
```

### Summary Text
```javascript
const summary = `${exe.renflouement_stats.nombre_soldes}/${exe.renflouement_stats.nombre_renflouements} members paid`;
```

---

## 🚀 Simple Example

```javascript
const ExerciceCard = ({ exercise }) => {
  const s = exercise.renflouement_stats || {};
  
  return (
    <Card>
      <Title>{exercise.nom}</Title>
      
      <Row>
        <Stat label="To Collect" value={s.montant_total_du || 0} />
        <Stat label="Collected" value={s.montant_total_paye || 0} />
      </Row>
      
      <ProgressBar progress={s.montant_total_paye / (s.montant_total_du || 1)} />
      
      <Footer>
        {s.nombre_soldes}/{s.nombre_renflouements} paid
      </Footer>
    </Card>
  );
};
```

---

## ✅ Testing Checklist

- [ ] Stats showing on exercise list
- [ ] Amounts displaying correctly
- [ ] Progress bars working
- [ ] Status colors correct
- [ ] "Paid" count accurate
- [ ] EN_COURS exercises show 0 stats
- [ ] TERMINE exercises show actual stats

---

## 🐛 Debugging

### Check data exists
```javascript
console.log(exercise.renflouement_stats);
// Should see all 6 fields
```

### Check values make sense
```javascript
console.assert(
  exercise.renflouement_stats.montant_total_paye <= 
  exercise.renflouement_stats.montant_total_du
);
```

### Check percentage
```javascript
const rate = (s.montant_total_paye / s.montant_total_du) * 100;
console.assert(rate >= 0 && rate <= 100);
```

---

## 📞 When to Use Each Endpoint

| Need | Endpoint | Why |
|------|----------|-----|
| List with stats | `/core/exercices/` | Already included |
| Member details | `/exercice_detail/?id=x` | Click exercise |
| Member history | `/par_membre/?id=x` | Click member |
| Quick stats | `/statistiques/?id=x` | Lightweight option |

---

## 💾 Remember

- ✅ Stats auto-updated when payments made
- ✅ All amounts in FCFA (integers)
- ✅ Percentages are 0-100
- ✅ Safe to use directly (no null checks needed)
- ✅ No extra API calls required

---

**That's it! You're ready to go! 🚀**
