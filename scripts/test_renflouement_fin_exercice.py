#!/usr/bin/env python
"""
Script de test pour valider la nouvelle logique des renflouements

Usage:
    python scripts/test_renflouement_fin_exercice.py
"""
import os
import sys
from datetime import date

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(PROJECT_ROOT)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Backend.settings')

import django
django.setup()

from core.models import (
    ConfigurationMutuelle, Exercice, Session, Membre, FondsSocial, DépenseExercice
)
from transactions.models import AssistanceAccordee, TypeAssistance, Renflouement
from django.contrib.auth import get_user_model
from decimal import Decimal

User = get_user_model()


def setup_test_data():
    """Crée les données de test"""
    print("\n" + "="*70)
    print("🔧 SETUP DES DONNÉES DE TEST")
    print("="*70)
    
    # 1. Créer/récupérer l'exercice
    exercice, created = Exercice.objects.get_or_create(
        statut='EN_COURS',
        defaults={
            'nom': 'Exercice Test 2026',
            'date_debut': date(2026, 1, 1),
            'date_fin': date(2026, 12, 31)
        }
    )
    print(f"{'✅' if created else '📌'} Exercice: {exercice.nom}")
    
    # 2. Créer/récupérer le fonds social
    fonds, created = FondsSocial.objects.get_or_create(
        exercice=exercice,
        defaults={'montant_total': Decimal('10000000')}  # 10M FCFA
    )
    print(f"{'✅' if created else '📌'} Fonds social: {fonds.montant_total:,.0f} FCFA")
    
    # 3. Créer une session
    session, created = Session.objects.get_or_create(
        exercice=exercice,
        date_session=date.today(),
        defaults={
            'nom': f'Session Test {date.today()}',
            'statut': 'EN_COURS'
        }
    )
    print(f"{'✅' if created else '📌'} Session: {session.nom}")
    
    # 4. Créer des membres EN_REGLE
    print(f"\n👥 Création de 5 membres EN_REGLE...")
    members = []
    for i in range(5):
        email = f'test_member_{i}@test.com'
        username = f'test_member_{i}'
        
        user, _ = User.objects.get_or_create(
            username=username,
            defaults={
                'email': email,
                'first_name': f'Test{i}',
                'last_name': f'Member{i}',
                'telephone': f'+2250{i}12345678'
            }
        )
        
        membre, created = Membre.objects.get_or_create(
            utilisateur=user,
            defaults={
                'date_inscription': date.today(),
                'statut': 'EN_REGLE',
                'exercice_inscription': exercice,
                'session_inscription': session
            }
        )
        
        if created:
            print(f"   ✅ {membre.numero_membre} ({user.first_name} {user.last_name})")
        else:
            print(f"   📌 {membre.numero_membre} ({user.first_name} {user.last_name})")
        
        members.append(membre)
    
    # 5. Créer un type d'assistance
    type_assistance, created = TypeAssistance.objects.get_or_create(
        nom='Décès',
        defaults={
            'montant': Decimal('500000'),
            'actif': True
        }
    )
    print(f"{'✅' if created else '📌'} Type d'assistance: {type_assistance.nom} ({type_assistance.montant:,.0f} FCFA)")
    
    return {
        'exercice': exercice,
        'fonds': fonds,
        'session': session,
        'members': members,
        'type_assistance': type_assistance
    }


def test_assistance_and_depenses(data):
    """Teste la création d'assistances et l'enregistrement des dépenses"""
    print("\n" + "="*70)
    print("🧪 TEST 1: CRÉATION D'ASSISTANCES ET ENREGISTREMENT DES DÉPENSES")
    print("="*70)
    
    exercice = data['exercice']
    fonds = data['fonds']
    session = data['session']
    members = data['members']
    type_assistance = data['type_assistance']
    
    print(f"\n💰 Fonds social AVANT: {fonds.montant_total:,.0f} FCFA")
    
    # Créer 2 assistances
    assistances = []
    for i in range(2):
        beneficiaire = members[i]
        montant = Decimal('500000')
        
        assistance, created = AssistanceAccordee.objects.get_or_create(
            membre=beneficiaire,
            type_assistance=type_assistance,
            session=session,
            defaults={
                'montant': montant,
                'statut': 'DEMANDEE'
            }
        )
        
        if created:
            # Simuler le paiement
            assistance.statut = 'PAYEE'
            assistance.save()
            assistances.append(assistance)
            print(f"   ✅ Assistance créée et payée pour {beneficiaire.numero_membre}: {montant:,.0f} FCFA")
    
    # Rafraîchir le fonds
    fonds.refresh_from_db()
    print(f"💰 Fonds social APRÈS assistances: {fonds.montant_total:,.0f} FCFA")
    
    # Vérifier les dépenses enregistrées
    depenses = DépenseExercice.objects.filter(
        exercice=exercice,
        type_depense='ASSISTANCE'
    )
    print(f"\n📋 Dépenses enregistrées: {depenses.count()}")
    for depense in depenses:
        print(f"   - {depense.type_depense}: {depense.montant:,.0f} FCFA pour {depense.beneficiaire.numero_membre}")
    
    total_depenses = depenses.aggregate(total=__import__('django.db.models', fromlist=['Sum']).Sum('montant'))['total']
    print(f"   Total: {total_depenses:,.0f} FCFA")
    
    return {
        'assistances': assistances,
        'total_depenses': total_depenses
    }


def test_creer_renflouements(data):
    """Teste la création des renflouements à la fin d'exercice"""
    print("\n" + "="*70)
    print("🧪 TEST 2: CRÉATION DES RENFLOUEMENTS À LA FIN D'EXERCICE")
    print("="*70)
    
    exercice = data['exercice']
    members = data['members']
    
    # Créer les renflouements
    result = exercice.creer_renflouements_fin_exercice()
    
    print(f"\n📊 RÉSUMÉ:")
    print(f"   💰 Total dépenses: {result['total_depenses']:,.0f} FCFA")
    print(f"   👥 Membres EN_REGLE: {result['nombre_membres']}")
    print(f"   📊 Montant par membre: {result['montant_par_membre']:,.0f} FCFA")
    print(f"   ✅ Renflouements créés: {result['renflouements_crees']}")
    
    # Vérifier les renflouements créés
    renflouements = Renflouement.objects.filter(
        type_cause='RENFLOUEMENT_FIN_EXERCICE'
    )
    print(f"\n📋 Renflouements créés en BD: {renflouements.count()}")
    for r in renflouements:
        print(f"   - {r.membre.numero_membre}: {r.montant_du:,.0f} FCFA (statut: {'SOLDÉ' if r.is_solde else 'EN ATTENTE'})")
    
    return result


def main():
    """Fonction principale"""
    print("\n" + "="*70)
    print("🔬 TESTS COMPLETS - NOUVELLE LOGIQUE RENFLOUEMENT")
    print("="*70)
    
    try:
        # Setup
        data = setup_test_data()
        
        # Test 1: Assistances et dépenses
        test1_result = test_assistance_and_depenses(data)
        
        # Test 2: Création des renflouements
        test2_result = test_creer_renflouements(data)
        
        # Résumé final
        print("\n" + "="*70)
        print("✅ TOUS LES TESTS TERMINÉS AVEC SUCCÈS")
        print("="*70 + "\n")
        
    except Exception as e:
        print(f"\n❌ ERREUR: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
