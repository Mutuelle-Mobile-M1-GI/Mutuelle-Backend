# 🚀 Frontend Integration Guide - Renflouement Stats

## TL;DR - What Changed

**The `/core/exercices/` endpoint now includes `renflouement_stats` for each exercise.**

No more separate API calls needed to get renflouement stats!

---

## Before vs After

### ❌ OLD WAY (Before)

```javascript
// Step 1: Get exercices
const { data: exercices } = useExercises();

// Step 2: For each exercise, manually fetch renflouement stats
const [stats, setStats] = useState({});
useEffect(() => {
  exercices?.forEach(async (exe) => {
    const res = await fetch(`/api/transactions/renflouements/?exercice_id=${exe.id}`);
    const data = await res.json();
    // Calculate totals manually...
    setStats(prev => ({...prev, [exe.id]: calculatedStats}));
  });
}, [exercices]);

// Step 3: Use the manually calculated stats
// This is slow, error-prone, and requires lots of API calls
```

**Problems:**
- Multiple API calls (1 + N calls)
- Manual calculations in frontend
- Race conditions
- Slow performance

---

### ✅ NEW WAY (After)

```javascript
// Step 1: Get exercices (STATS INCLUDED!)
const { data: exercices } = useExercises();

// Step 2: Use renflouement_stats directly
exercices?.forEach(exe => {
  const stats = exe.renflouement_stats;
  console.log(stats.montant_total_du);      // 500000
  console.log(stats.montant_total_paye);    // 200000
  console.log(stats.taux_recouvrement);     // 40
});

// Done! No extra API calls needed!
```

**Benefits:**
- Single API call for everything
- Stats calculated on backend (more reliable)
- Automatic and fast

---

## API Response Example

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "nom": "ARNO",
  "statut": "TERMINE",
  "date_debut": "2026-01-01",
  "date_fin": "2026-12-31",
  
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

---

## Usage in Components

### 1. Display Stats in Exercise Card

```javascript
const ExerciceSimpleCard = ({ item, onPress }) => {
  const stats = item.renflouement_stats || {};
  
  return (
    <TouchableOpacity style={styles.card} onPress={onPress}>
      <Text>{item.nom}</Text>
      
      {/* ✅ Use stats directly from exercise object */}
      <View style={styles.amounts}>
        <View>
          <Text style={styles.label}>À collecter</Text>
          <Text style={styles.value}>
            {formatCurrency(stats.montant_total_du || 0)}
          </Text>
        </View>
        
        <View>
          <Text style={styles.label}>Collecté</Text>
          <Text style={[styles.value, { color: '#10B981' }]}>
            {formatCurrency(stats.montant_total_paye || 0)}
          </Text>
        </View>
        
        <View>
          <Text style={styles.label}>Restant</Text>
          <Text style={[styles.value, { color: '#EF4444' }]}>
            {formatCurrency(stats.montant_total_restant || 0)}
          </Text>
        </View>
      </View>
      
      {/* Progress Bar */}
      <ProgressBar
        progress={(stats.montant_total_paye || 0) / (stats.montant_total_du || 1)}
        color={stats.montant_total_restant <= 0 ? '#10B981' : '#14B8A6'}
      />
      
      {/* Badge */}
      <Text>
        {stats.nombre_soldes || 0}/{stats.nombre_renflouements || 0} soldés
      </Text>
    </TouchableOpacity>
  );
};
```

### 2. Build Stats Grid

```javascript
const StatCard = ({ title, value, icon, color }) => (
  <View style={[styles.statCard, { borderLeftColor: color }]}>
    <Icon name={icon} color={color} />
    <View>
      <Text style={styles.label}>{title}</Text>
      <Text style={[styles.value, { color }]}>{value}</Text>
    </View>
  </View>
);

function DetailModal({ exercise, onClose }) {
  const stats = exercise?.renflouement_stats || {};
  
  return (
    <Modal visible={true}>
      <View style={styles.statsContainer}>
        <StatCard
          title="À collecter"
          value={formatCurrency(stats.montant_total_du || 0)}
          icon="cash"
          color="#14B8A6"
        />
        
        <StatCard
          title="Collecté"
          value={formatCurrency(stats.montant_total_paye || 0)}
          icon="checkmark-circle"
          color="#10B981"
        />
        
        <StatCard
          title="Restant"
          value={formatCurrency(stats.montant_total_restant || 0)}
          icon="alert-circle"
          color="#EF4444"
        />
        
        <StatCard
          title="Taux"
          value={`${((stats.montant_total_paye || 0) / (stats.montant_total_du || 1) * 100).toFixed(0)}%`}
          icon="trending-up"
          color="#3B82F6"
        />
      </View>
    </Modal>
  );
}
```

### 3. Enrich Your Data Without Extra Calls

```javascript
const exercicesWithStats = useMemo(() => {
  return (exercices || []).map((exe) => ({
    ...exe,
    // Stats ALREADY included!
    stats: exe.renflouement_stats || {
      montant_total_du: 0,
      montant_total_paye: 0,
      montant_total_restant: 0,
      taux_recouvrement: 0,
    },
  }));
}, [exercices]);

// No need for extra fetching!
// No need for manual calculations!
```

---

## When to Use Each Endpoint

### Scenario 1: Show List of Exercises with Stats

```
✅ USE: GET /core/exercices/
   - Already includes renflouement_stats
   - Perfect for the main screen
```

### Scenario 2: Show Detailed View of One Exercise with Members

```
✅ USE: GET /transactions/renflouements/exercice_detail/?exercice_id=xxx
   - Get all members and their payments for that exercise
   - Used in the detail modal
```

### Scenario 3: Show Member Profile with All Renflouements

```
✅ USE: GET /transactions/renflouements/par_membre/?membre_id=xxx
   - Get all exercises and renflouements for one member
   - Show cumulative stats across all exercises
```

---

## Data Flow Example

### Screen Load

```
1. useExercises()
   └─> GET /core/exercices/
       └─> Returns: [
             {
               id: "...",
               nom: "ARNO",
               renflouement_stats: {
                 montant_total_du: 500000,
                 montant_total_paye: 200000,
                 ...
               }
             },
             ...
           ]

2. Display ExerciceSimpleCard with stats
   └─> All stats already available!
```

### User Clicks Exercise

```
1. User taps on ARNO exercise
2. Open DetailModal
3. Display stats from ALREADY LOADED data
   └─> stats.montant_total_du, etc.
4. Optional: Fetch exercise_detail for member list
   └─> GET /transactions/renflouements/exercice_detail/?exercice_id=xxx
```

### User Clicks Member

```
1. User taps on member in detail modal
2. Fetch member's all renflouements
   └─> GET /transactions/renflouements/par_membre/?membre_id=xxx
3. Display in separate modal
```

---

## Code Migration Checklist

If you're updating existing code:

- [ ] Remove manual stats fetching loops
- [ ] Remove manual aggregation/calculation code
- [ ] Use `item.renflouement_stats` directly
- [ ] Update useMemo dependencies (should be just `[exercices]` now)
- [ ] Remove useRenflouementPayments() from main list (only use for detail)
- [ ] Test with exercises that have 0 renflouements
- [ ] Test with exercises that are EN_COURS vs TERMINE

---

## Handling Edge Cases

### Empty Stats (No Renflouements)

```javascript
const stats = exercise.renflouement_stats || {
  montant_total_du: 0,
  montant_total_paye: 0,
  montant_total_restant: 0,
  taux_recouvrement: 0,
  nombre_renflouements: 0,
  nombre_soldes: 0,
};

// Safe to use now!
const percentage = stats.taux_recouvrement; // Will be 0, not NaN
```

### Exercise in Progress (EN_COURS)

```javascript
// Exercises that are EN_COURS will have:
// renflouement_stats: { all zeros }

// This is normal! Renflouements are created at exercise CLOSE
if (exercise.statut === 'EN_COURS') {
  // Show "No renflouements yet" message
} else {
  // Show renflouement stats
}
```

### Null/Undefined Check

```javascript
const stats = exercise?.renflouement_stats || {};
const montant_du = stats?.montant_total_du ?? 0;
```

---

## Performance Notes

### ✅ Good

```javascript
// All data is fetched in 1 call
const { data: exercices } = useExercises();

// Render immediately
{exercices?.map(exe => (
  <ExerciceCard stats={exe.renflouement_stats} />
))}
```

### ❌ Bad

```javascript
// DON'T do this anymore!
const { data: exercices } = useExercises();

// DON'T fetch stats for each exercise
useEffect(() => {
  exercices?.forEach(async (exe) => {
    const stats = await fetchRenflouementStats(exe.id);
    // This causes N additional API calls!
  });
}, [exercices]);
```

---

## Support Reference

### Fields Available in `renflouement_stats`

| Field | Type | Description |
|-------|------|-------------|
| `montant_total_du` | float | Total amount to collect (in FCFA) |
| `montant_total_paye` | float | Total amount paid (in FCFA) |
| `montant_total_restant` | float | Total amount remaining (in FCFA) |
| `taux_recouvrement` | float | Collection rate (0-100) |
| `nombre_renflouements` | int | Total renflouements created |
| `nombre_soldes` | int | Renflouements fully paid |

### Format Examples

```javascript
// All amounts in FCFA (French francs)
stats.montant_total_du      // 500000
stats.montant_total_paye    // 200000

// Percentage
stats.taux_recouvrement     // 40 (meaning 40%)

// Counts
stats.nombre_renflouements  // 5
stats.nombre_soldes         // 2
```

---

## Questions?

If something is unclear or not working:

1. Check that your `/core/exercices/` response includes `renflouement_stats`
2. Verify the stats values make sense (due > paid, etc.)
3. Test with different exercise statuses (EN_COURS vs TERMINE)
4. Check console for any undefined/null errors

---

**Last Updated:** July 2026  
**Status:** ✅ Production Ready
