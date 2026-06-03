# Règle d'inscription et paiements de solidarité / épargne

## Objectif

Bloquer les paiements de solidarité et les opérations d'épargne pour un membre dont l'inscription n'est pas terminée.

## Fichiers modifiés

### `transactions/serializers.py`

- `PaiementSolidariteSerializer.validate()`
  - vérifie si `membre.inscription_terminee` est `False`
  - renvoie un message clair lorsqu'un membre tente de payer la solidarité sans inscription terminée

- `EpargneTransactionSerializer.validate()`
  - vérifie si `membre.inscription_terminee` est `False`
  - renvoie un message clair lorsqu'un membre tente une opération d'épargne sans inscription terminée

### `transactions/models.py`

- `PaiementSolidarite.clean()`
  - ajoute une validation modèle pour interdire le paiement de solidarité si l'inscription n'est pas terminée

- `EpargneTransaction.clean()`
  - ajoute une validation modèle pour interdire la création d'une transaction d'épargne si l'inscription n'est pas terminée

- `PaiementSolidarite.save()`
  - appelle `self.full_clean()` avant de sauvegarder pour garantir la validation modèle
  - calcule `montant_solidarite_du` automatiquement si nécessaire

## Message d'erreur API attendu

Lorsque la règle n'est pas respectée, l'API doit renvoyer un `400 Bad Request` avec un message explicite.

### Solidarité

- `Le membre n'a pas terminé son inscription. Le paiement de solidarité est interdit tant que l'inscription n'est pas complète.`

### Épargne

- `Le membre n'a pas terminé son inscription. Il ne peut pas effectuer d'opérations d'épargne tant que l'inscription n'est pas complète.`

## Indications pour les développeurs frontend

1. Lors du POST vers `/api/transactions/paiements-solidarite/` ou `/api/transactions/epargne-transactions/`, traiter le code HTTP `400` comme une erreur métier légitime.
2. Lire le message d'erreur dans la réponse JSON et l'afficher dans l'UI.
   - Exemple de libération standard :
     - `response.data` ou `error.response.data`
3. Ne pas afficher seulement `Bad Request`.
   - Afficher le message d'erreur exact provenant de l'API.
4. Pour l'expérience utilisateur :
   - si l'erreur concerne un membre non inscrit, afficher un libellé clair tel que :
     - `Ce membre doit terminer son inscription avant de pouvoir payer la solidarité.`
     - `Ce membre doit terminer son inscription avant de pouvoir effectuer une épargne.`
5. Vérifier en frontend si la requête a échoué pour `400`, puis afficher dans un composant d'alerte ou de validation côté formulaire.

## Tests recommandés

- Créer un membre avec `inscription_terminee = False` et tenter un paiement de solidarité.
- Vérifier que l'API renvoie `400` et que le message exact est présent.
- Créer un membre avec `inscription_terminee = False` et tenter une transaction d'épargne.
- Vérifier que l'API renvoie `400` et que le message exact est présent.
- Vérifier qu'un membre avec `inscription_terminee = True` peut effectuer les opérations normalement.
