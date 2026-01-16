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
            'nom': 'Mariage',
            'montant': Decimal('500000.00'),
            'description': 'Assistance financière en cas de mariage du membre.',
            'actif': True
        },
        {
            'nom': 'Décès',
            'montant': Decimal('1500000.00'),
            'description': "Soutien financier en cas de décès d'un membre ou d'un ayant droit.",
            'actif': True
        },
        {
            'nom': 'Naissance',
            'montant': Decimal('300000.00'),
            'description': "Prime de naissance pour le nouveau-né d'un membre.",
            'actif': True
        },
        {
            'nom': 'Sinistre',
            'montant': Decimal('2000000.00'),
            'description': "Aide exceptionnelle en cas de sinistre majeur (incendie, inondation, etc.).",
            'actif': False # Exemple de type désactivé
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