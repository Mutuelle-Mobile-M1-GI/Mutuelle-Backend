# Documentation Frontend : Endpoint Membres

**Endpoint:** `GET /api/core/membres/`

Cet endpoint est le cœur de l'application frontend pour l'affichage de l'annuaire des membres et de leurs tableaux de bord. Il retourne une liste paginée contenant à la fois les informations de base des membres **et** la totalité de leur situation financière calculée en temps réel.

## Structure globale de la réponse (Pagination)

La réponse utilise la pagination standard de Django REST Framework :

```json
{
  "count": 3,
  "next": null,
  "previous": null,
  "results": [ ... ]
}
```
- `count` (number) : Le nombre total de membres correspondants aux filtres appliqués.
- `next` / `previous` (string | null) : Les URLs (chaînes de caractères) pour naviguer vers la page suivante ou précédente. Pratique pour l'implémentation de composants de type "Load More" ou "Pagination".
- `results` (array) : Le tableau contenant les objets [Membre](file:///home/darren/Bureau/projet/Mutuelle-Backend/core/views.py#436-539).

---

## Modèle de Données d'un Membre (Objet dans `results`)

Chaque objet dans le tableau `results` est structuré en 3 parties principales : les informations propres au membre, les informations liées à son compte utilisateur, et le bloc très riche détaillé sous la clé [donnees_financieres](file:///home/darren/Bureau/projet/Mutuelle-Backend/core/serializers.py#232-238).

### 1. Informations de Base et Système

| Champ | Type | Description |
|-------|------|-------------|
| [id](file:///home/darren/Bureau/projet/Mutuelle-Backend/core/serializers.py#308-314) | `uuid` | L'identifiant unique du membre. |
| `numero_membre` | `string` | Le matricule ou numéro d'identification (ex: "ENS-0001"). |
| `date_inscription` | `string` (YYYY-MM-DD) | La date d'inscription formatée. |
| `statut` | `string` | Le statut actuel du membre (ex: `"NON_DEFINI"`, `"EN_REGLE"`, etc.). |
| `exercice_inscription_nom` | `string` | Le nom de l'exercice fiscal au moment de l'inscription. |
| `session_inscription_nom` | `string` | Le nom de la session au moment de l'inscription. |
| [is_en_regle](file:///home/darren/Bureau/projet/Mutuelle-Backend/core/views.py#488-492) | `boolean` | Indique de manière stricte si le membre est en règle avec la mutuelle (aucune dette exigée en retard). |
| `date_creation` / `date_modification` | `string` (ISO 8601) | Dates systèmes de l'enregistrement en base de données. |

### 2. Objet `utilisateur` (Profil Utilisateur)

Contient les informations d'authentification et de contact de l'utilisateur associé au membre :
- [id](file:///home/darren/Bureau/projet/Mutuelle-Backend/core/serializers.py#308-314) : UUID de l'utilisateur.
- `username`, `email`, `telephone` : Informations de contact de base.
- `first_name`, `last_name`, [nom_complet](file:///home/darren/Bureau/projet/Mutuelle-Backend/core/views.py#482-487) : Identité pour l'affichage (utilisez de préférence [nom_complet](file:///home/darren/Bureau/projet/Mutuelle-Backend/core/views.py#482-487)).
- `role` : Rôle dans le système (ex: `"MEMBRE"`, `"ADMIN"`).
- `photo_profil_url` : URL de l'avatar (peut être `null`).
- `is_active` : Indique si le compte est actif pour se connecter à l'application.

### 3. Objet [donnees_financieres](file:///home/darren/Bureau/projet/Mutuelle-Backend/core/serializers.py#232-238) (Le Cœur du Dashboard Frontend)

C'est **cet objet que le frontend utilisera prioritairement** pour dessiner les tableaux de bord individuels, les cartes de profil et les widgets récapitulatifs.

#### A. Inscription ([inscription](file:///home/darren/Bureau/projet/Mutuelle-Backend/core/views.py#512-523))
- `montant_total_inscription` : Prix d'inscription fixé par la configuration globale.
- `montant_paye_inscription` : Ce que le membre a réellement déposé pour son inscription.
- `montant_restant_inscription` : Reste à payer (vaut `0` si totalement soldé).
- [inscription_complete](file:///home/darren/Bureau/projet/Mutuelle-Backend/core/views.py#512-523) (boolean) : Facilite grandement l'affichage d'un badge "Inscription Validée" ou "En attente".
- `pourcentage_inscription` : Idéal pour alimenter le `value` d'une jauge de progression circulaire (attention, ce pourcentage peut dépasser 100% si un trop perçu a eu lieu, ex: 104%).

#### B. Solidarité ([solidarite](file:///home/darren/Bureau/projet/Mutuelle-Backend/core/serializers.py#83-92))
- `montant_solidarite_base` : La cotisation due spécifiquement pour la session courante.
- `montant_reporte` : La dette accumulée lors des sessions ou des exercices précédents impayés.
- `total_solidarite_payee` : Montant total jamais versé par le membre au titre de la solidarité.
- `dette_solidarite_cumul` : Total cumulé qu'il reste à payer aujourd'hui.
- `solidarite_a_jour` (boolean) : Raccourci backend hyper utile pour afficher un simple icône vert/rouge.

#### C. Épargne ([epargne](file:///home/darren/Bureau/projet/Mutuelle-Backend/transactions/serializers.py#234-241))
- `epargne_base` : Total des dépôts "simples" effectués.
- `interets_recus` : Les dividendes gagnées au fil du temps.
- `epargne_totale` : L'argent net disponible aujourd'hui dans le portefeuille virtuel du membre (prend en compte les dépôts, moins les retraits faits pour des cautions/emprunts).
- `epargne_plus_interets` : Montant consolidé de l'épargne avec les intérêts (`epargne_totale` + `interets_recus`).

#### D. Emprunt ([emprunt](file:///home/darren/Bureau/projet/Mutuelle-Backend/transactions/serializers.py#256-264))
Très complet pour dessiner une carte ou un widget interactif "Mon Prêt" :
- `a_emprunt_en_cours` (boolean) : Permet, côté UI, de faire un rendu conditionnel ([if](file:///home/darren/Bureau/projet/Mutuelle-Backend/core/views.py#657-662) / `v-if`) exclusif pour afficher le bloc "Emprunt en cours". S'il vaut false, affichez "Faire une demande de prêt".
- `montant_emprunt_en_cours` : Le capital brut initialement emprunté.
- `montant_total_a_rembourser` : Capital + Intérêts calculés.
- `montant_deja_rembourse` : Ce qui a déjà été reversé en remboursement à la caisse.
- `montant_restant_a_rembourser` : La dette ferme restante du prêt en cours.
- `pourcentage_rembourse` : Idéal pour une `<progress-bar>`.
- `montant_max_empruntable` : Indique dynamiquement combien le membre a le droit de demander aujourd'hui (calculé sur base d'un coefficient sur son épargne existante).

#### E. Renflouement ([renflouement](file:///home/darren/Bureau/projet/Mutuelle-Backend/transactions/serializers.py#325-333))
Obligations exceptionnelles de refinancement de la caisse mutuelle :
- `total_renflouement_du` : Somme exigée historiquement.
- `solde_renflouement_du` : Reste à payer.
- `renflouement_a_jour` (boolean) : Badge d'état visuel (vert ou rouge).

#### F. Résumé Financier (`resume_financier`)
La synthèse absolue pour le Header d'un Dashboard membre :
- `patrimoine_total` : Tout ce que le membre possède en actifs dans la mutuelle (ex. `6000`).
- `obligations_totales` : Tout ce que le membre **DOIT** à la mutuelle (Dettes solidarité cumulées + Dettes d'emprunts + Dettes de Renflouements = ex. `329400`).
- `situation_nette` : Indique la richesse apparente globale du membre (`patrimoine_total`).

---

## Interfaces TypeScript Recommandées pour le Frontend

Copiez ces interfaces dans un fichier `types/membre.ts` de votre projet React / Angular / Vue pour un typage statique rapide et robuste :

```typescript
export interface Utilisateur {
  id: string;
  username: string;
  email: string;
  first_name: string;
  last_name: string;
  nom_complet: string;
  telephone: string;
  role: string;
  photo_profil_url: string | null;
  is_active: boolean;
}

export interface DonneesFinancieres {
  membre_info: {
    numero_membre: string;
    nom_complet: string;
    en_regle: boolean;
    // ... champs annexes raccourcis
  };
  inscription: {
    montant_total_inscription: number;
    montant_paye_inscription: number;
    montant_restant_inscription: number;
    inscription_complete: boolean;
    pourcentage_inscription: number;
  };
  solidarite: {
    montant_solidarite_base: number;
    dette_solidarite_cumul: number;
    total_solidarite_payee: number;
    solidarite_a_jour: boolean;
    // ...
  };
  epargne: {
    epargne_base: number;
    epargne_totale: number;
    interets_recus: number;
    epargne_plus_interets: number;
    // ...
  };
  emprunt: {
    a_emprunt_en_cours: boolean;
    montant_emprunt_en_cours: number;
    montant_restant_a_rembourser: number;
    pourcentage_rembourse: number;
    montant_max_empruntable: number;
    // ...
  };
  renflouement: {
    total_renflouement_du: number;
    solde_renflouement_du: number;
    renflouement_a_jour: boolean;
  };
  resume_financier: {
    patrimoine_total: number;
    obligations_totales: number;
    situation_nette: number;
  };
}

export interface Membre {
  id: string;
  numero_membre: string;
  date_inscription: string;
  statut: string;
  is_en_regle: boolean;
  exercice_inscription_nom: string;
  session_inscription_nom: string;
  utilisateur: Utilisateur;
  donnees_financieres: DonneesFinancieres;
}

export interface PaginatedMembresResponse {
  count: number;
  next: string | null;
  previous: string | null;
  results: Membre[];
}
```
