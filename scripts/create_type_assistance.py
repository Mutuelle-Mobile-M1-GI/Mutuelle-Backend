#!/usr/bin/env python
"""
Script de simulation : Crée ou récupère des instances de TypeAssistance.

Usage:
    python scripts/simulate_assistance_types.py

Le script configure Django et utilise la méthode get_or_create
pour garantir que les types d'assistance de base existent dans la BDD.
"""
import os
import sys
from decimal import Decimal

# --- Configuration de l'environnement Django ---
# Assurez-vous que le chemin racine du projet est correctement défini
# (Ajustez si nécessaire, basé sur votre structure)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(PROJECT_ROOT)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Backend.settings')

import django
django.setup()

# --- Importations des Modèles ---
from core.models import TypeAssistance


def main():
    """
    Exécute la simulation de création/récupération des types d'assistance.
    """
    print("--- Démarrage de la simulation TypeAssistance ---")
    
    # 1. Définition des types d'assistance à initialiser
    types_a_initialiser = [
        {
            'nom': 'Maladie',
            'montant': Decimal('300000.00'),
            'description': "Assistance financière accordée au membre en cas de maladie nécessitant des soins ou une hospitalisation.",
            'actif': True
        },
        {
            'nom': 'Mariage',
            'montant': Decimal('100000.00'),
            'description': "Aide financière octroyée au membre à l’occasion de son mariage.",
            'actif': True
        },
        {
            'nom': 'Promotion',
            'montant': Decimal('50000.00'),
            'description': "Prime accordée au membre suite à une promotion professionnelle ou académique.",
            'actif': True
        },
        {
            'nom': 'Départ en retraite',
            'montant': Decimal('500000.00'),
            'description': "Allocation spéciale versée au membre lors de son départ à la retraite.",
            'actif': True
        },
        {
            'nom': 'Décès membre',
            'montant': Decimal('1000000.00'),
            'description': "Soutien financier accordé à la famille en cas de décès du membre.",
            'actif': True
        },
        {
            'nom': 'Décès conjoint',
            'montant': Decimal('500000.00'),
            'description': "Aide financière versée au membre suite au décès de son conjoint.",
            'actif': True
        },
        {
            'nom': 'Décès enfant',
            'montant': Decimal('300000.00'),
            'description': "Soutien financier accordé au membre en cas de décès de son enfant.",
            'actif': True
        }
    ]
    
    print(f"\nTentative d'initialisation de {len(types_a_initialiser)} types d'assistance:")
    
    # 2. Utilisation de get_or_create pour l'initialisation
    for data in types_a_initialiser:
        nom_type = data['nom']
        
        # Le nom est utilisé comme clé de recherche, les autres champs comme valeurs par défaut
        instance, created = TypeAssistance.objects.get_or_create(
            nom=nom_type,
            defaults={
                'montant': data['montant'],
                'description': data['description'],
                'actif': data['actif']
            }
        )
        
        statut = "Créé" if created else "Existant"
        print(f"[{statut.upper()}]: {instance}")

    # 3. Affichage de la liste complète après simulation
    print("\n--- Récapitulatif des TypeAssistance dans la BDD ---")
    
    tous_les_types = TypeAssistance.objects.all().order_by('nom')
    
    if tous_les_types.exists():
        for i, type_assist in enumerate(tous_les_types, 1):
            statut = "ACTIF" if type_assist.actif else "INACTIF"
            print(f"{i}. {type_assist.nom.ljust(15)} | {type_assist.montant:,.2f} FCFA | Statut: {statut}")
    else:
        print("Aucun TypeAssistance trouvé dans la base de données.")


if __name__ == '__main__':
    main()