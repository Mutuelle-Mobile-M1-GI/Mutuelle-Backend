#!/usr/bin/env python
"""
Script de création de membres et utilisateurs dans la mutuelle.

Usage:
    python scripts/create_members.py

Ce script vous permet de créer un ou plusieurs membres avec leurs utilisateurs associés.
Il gère automatiquement:
- Création de l'utilisateur (email unique, téléphone valide)
- Création du profil de membre
- Attribution automatique du numéro de membre
- Configuration de l'exercice et session d'inscription
"""
import os
import sys
from datetime import date
from decimal import Decimal


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(PROJECT_ROOT)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Backend.settings')

import django
django.setup()

from core.models import Exercice, Session, Membre
from django.contrib.auth import get_user_model
from django.db import transaction

User = get_user_model()


def create_user_and_member(
    email,
    username,
    first_name,
    last_name,
    telephone,
    password='000000',
    role='MEMBRE',
    exercice=None,
    session=None,
    statut='NON_DEFINI'
):
    """
    Crée un utilisateur et son profil de membre associé.
    
    Args:
        email (str): Email unique de l'utilisateur
        username (str): Nom d'utilisateur (doit être unique)
        first_name (str): Prénom
        last_name (str): Nom
        telephone (str): Numéro de téléphone (format: +2251234567890)
        password (str): Mot de passe (défaut: '000000')
        role (str): 'MEMBRE' ou 'ADMINISTRATEUR' (défaut: 'MEMBRE')
        exercice (Exercice): Exercice d'inscription (optionnel, prend l'exercice EN_COURS)
        session (Session): Session d'inscription (optionnel, prend la session EN_COURS)
        statut (str): Statut du membre ('NON_DEFINI', 'EN_REGLE', 'NON_EN_REGLE', 'SUSPENDU')
    
    Returns:
        tuple: (utilisateur, membre, created) où created est bool indiquant si créé
    """
    
    # Obtenir ou créer l'exercice
    if exercice is None:
        exercice = Exercice.get_exercice_en_cours()
        if not exercice:
            print("❌ Aucun exercice EN_COURS disponible. Créez-en un d'abord.")
            return None, None, False
    
    # Obtenir ou créer la session
    if session is None:
        session = Session.get_session_en_cours()
        if not session:
            session, _ = Session.objects.get_or_create(
                exercice=exercice,
                defaults={
                    'date_session': date.today(),
                    'nom': f'Session {date.today().month}/{date.today().year}'
                }
            )
    
    try:
        with transaction.atomic():
            # Créer l'utilisateur
            utilisateur, user_created = User.objects.get_or_create(
                email=email,
                defaults={
                    'username': username,
                    'first_name': first_name,
                    'last_name': last_name,
                    'telephone': telephone,
                    'role': role,
                    'is_active': True
                }
            )
            
            # Définir le mot de passe
            utilisateur.set_password(password)
            utilisateur.first_name = first_name
            utilisateur.last_name = last_name
            utilisateur.telephone = telephone
            utilisateur.role = role
            utilisateur.save()
            
            if user_created:
                print(f"✅ Utilisateur créé: {email}")
            else:
                print(f"ℹ️  Utilisateur {email} existe déjà. Profil et mot de passe mis à jour...")
            
            # Créer ou récupérer le profil de membre
            membre, member_created = Membre.objects.get_or_create(
                utilisateur=utilisateur,
                defaults={
                    'date_inscription': date.today(),
                    'statut': statut,
                    'exercice_inscription': exercice,
                    'session_inscription': session,
                    'inscription_terminee': False
                }
            )
            
            if not member_created:
                print(f"ℹ️  Membre {email} existe déjà. Statut mis à jour...")
                membre.statut = statut
                membre.save()
            
            status_msg = "✅ CRÉÉ" if user_created or member_created else "ℹ️  EXISTE"
            print(f"{status_msg} | {utilisateur.nom_complet} ({email})")
            print(f"   Numéro membre: {membre.numero_membre}")
            print(f"   Mot de passe: {password}")
            print(f"   Rôle: {role} | Statut: {statut}")
            print(f"   Exercice: {exercice.nom} | Session: {session.nom if hasattr(session, 'nom') else 'N/A'}")
            
            return utilisateur, membre, user_created or member_created
    
    except Exception as e:
        print(f"❌ ERREUR lors de la création de {email}: {str(e)}")
        return None, None, False


def create_multiple_members(members_data, password='000000'):
    """
    Crée plusieurs membres à partir d'une liste de dictionnaires.
    
    Args:
        members_data (list): Liste de dictionnaires avec clés:
            - email (requis)
            - username (requis)
            - first_name (requis)
            - last_name (requis)
            - telephone (requis)
            - role (optionnel, défaut: 'MEMBRE')
            - statut (optionnel, défaut: 'NON_DEFINI')
            - password (optionnel, défaut: '000000')
        password (str): Mot de passe par défaut pour tous les membres (défaut: '000000')
    
    Returns:
        list: Liste des tuples (utilisateur, membre, created)
    """
    results = []
    created_count = 0
    
    # Vérifier qu'il y a au moins un exercice EN_COURS
    exercice = Exercice.get_exercice_en_cours()
    if not exercice:
        print("❌ ERREUR: Aucun exercice EN_COURS disponible.")
        print("   Créez d'abord un exercice EN_COURS dans l'admin Django.")
        return results
    
    session = Session.get_session_en_cours()
    if not session:
        print(f"⚠️  Aucune session EN_COURS. Création automatique...")
        session, _ = Session.objects.get_or_create(
            exercice=exercice,
            defaults={
                'date_session': date.today(),
                'nom': f'Session {date.today().month}/{date.today().year}'
            }
        )
    
    print(f"\n{'='*70}")
    print(f"CRÉATION DE {len(members_data)} MEMBRE(S)")
    print(f"Exercice: {exercice.nom}")
    print(f"Session: {session.nom if hasattr(session, 'nom') else 'N/A'}")
    print(f"{'='*70}\n")
    
    for member_data in members_data:
        # Extraire et valider les données
        email = member_data.get('email')
        username = member_data.get('username')
        first_name = member_data.get('first_name')
        last_name = member_data.get('last_name')
        telephone = member_data.get('telephone')
        role = member_data.get('role', 'MEMBRE')
        statut = member_data.get('statut', 'NON_DEFINI')
        member_password = member_data.get('password', password)
        
        # Validation minimale
        if not all([email, username, first_name, last_name, telephone]):
            print(f"❌ ERREUR: Données incomplètes pour {member_data}")
            continue
        
        # Créer l'utilisateur et membre
        user, membre, created = create_user_and_member(
            email=email,
            username=username,
            first_name=first_name,
            last_name=last_name,
            telephone=telephone,
            password=member_password,
            role=role,
            exercice=exercice,
            session=session,
            statut=statut
        )
        
        if created:
            created_count += 1
        
        results.append((user, membre, created))
    
    print(f"\n{'='*70}")
    print(f"RÉSUMÉ: {created_count} nouveau(x) membre(s) créé(s) sur {len(members_data)}")
    print(f"{'='*70}\n")
    
    return results


def interactive_create(password='000000'):
    """
    Mode interactif pour créer un membre à la fois.
    
    Args:
        password (str): Mot de passe par défaut
    """
    print("\n" + "="*70)
    print("CRÉATION INTERACTIVE DE MEMBRE")
    print("="*70 + "\n")
    
    try:
        email = input("Email: ").strip()
        username = input("Nom d'utilisateur: ").strip()
        first_name = input("Prénom: ").strip()
        last_name = input("Nom: ").strip()
        telephone = input("Téléphone (+2251234567890): ").strip()
        role = input("Rôle (MEMBRE/ADMINISTRATEUR) [MEMBRE]: ").strip().upper() or 'MEMBRE'
        statut = input("Statut (NON_DEFINI/EN_REGLE/NON_EN_REGLE/SUSPENDU) [NON_DEFINI]: ").strip().upper() or 'NON_DEFINI'
        pwd = input(f"Mot de passe [{password}]: ").strip() or password
        
        user, membre, created = create_user_and_member(
            email=email,
            username=username,
            first_name=first_name,
            last_name=last_name,
            telephone=telephone,
            password=pwd,
            role=role,
            statut=statut
        )
        
        if user:
            print(f"\n✅ Membre créé avec succès!")
        else:
            print(f"\n❌ Erreur lors de la création du membre")
    
    except KeyboardInterrupt:
        print("\n\n❌ Création annulée par l'utilisateur")


def main():
    """
    Fonction principale avec exemples de création.
    """
    
    # EXEMPLE 1: Créer un seul membre
    print("EXEMPLE 1: Création d'un seul membre")
    print("-" * 70)
    
    user, membre, created = create_user_and_member(
        email='jean.dupont@example.com',
        username='jean.dupont',
        first_name='Jean',
        last_name='Dupont',
        telephone='+22512345678',
        role='MEMBRE',
        statut='NON_DEFINI'
    )
    
    # EXEMPLE 2: Créer plusieurs membres à la fois
    print("\n\nEXEMPLE 2: Création de plusieurs membres")
    print("-" * 70)
    
    members_data = [
        {
            'email': 'marie.martin@example.com',
            'username': 'marie.martin',
            'first_name': 'Marie',
            'last_name': 'Martin',
            'telephone': '+22587654321',
            'role': 'MEMBRE',
            'statut': 'EN_REGLE'
        },
        {
            'email': 'pierre.bernard@example.com',
            'username': 'pierre.bernard',
            'first_name': 'Pierre',
            'last_name': 'Bernard',
            'telephone': '+22598765432',
            'role': 'ADMINISTRATEUR',
            'statut': 'EN_REGLE'
        },
        {
            'email': 'sophie.robert@example.com',
            'username': 'sophie.robert',
            'first_name': 'Sophie',
            'last_name': 'Robert',
            'telephone': '+22512121212',
            'role': 'MEMBRE',
            'statut': 'NON_EN_REGLE'
        }
    ]
    
    results = create_multiple_members(members_data)
    
    # EXEMPLE 3: Mode interactif (décommenter pour utiliser)
    # interactive_create()


if __name__ == '__main__':
    main()
