"""
Test pour l'endpoint: Payer un renflouement avec l'épargne personnelle
Test: POST /api/transactions/renflouements/<uuid>/payer_avec_epargne/
"""

import json
from decimal import Decimal
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from core.models import Membre, Exercice, Session
from authentication.models import Utilisateur
from transactions.models import (
    Renflouement, PaiementRenflouement, EpargneTransaction
)
import uuid


class PayerRenflouementAvecEpargneTestCase(TestCase):
    """
    Tests pour l'endpoint de paiement de renflouement avec épargne
    """
    
    @classmethod
    def setUpTestData(cls):
        """Préparation des données de test"""
        # 1. Créer un utilisateur
        cls.user = Utilisateur.objects.create_user(
            username='testmember',
            email='test@example.com',
            password='testpass123',
            first_name='Test',
            last_name='Member'
        )
        
        # 2. Créer un exercice
        cls.exercice = Exercice.objects.create(
            nom='Exercice 2025-2026',
            date_debut=timezone.now().date(),
            date_fin=timezone.now().date() + timezone.timedelta(days=365)
        )
        
        # 3. Créer une session
        cls.session = Session.objects.create(
            nom='Session Test',
            exercice=cls.exercice,
            date_session=timezone.now().date(),
            statut='EN_COURS'
        )
        
        # 4. Créer un membre
        cls.membre = Membre.objects.create(
            utilisateur=cls.user,
            numero_membre='TEST001',
            date_inscription=timezone.now().date(),
            statut='EN_REGLE',
            exercice_inscription=cls.exercice,
            session_inscription=cls.session,
            inscription_terminee=True,
            actif=True
        )
        
        # 5. Créer des transactions d'épargne pour le membre (épargne positive)
        for i in range(3):
            EpargneTransaction.objects.create(
                membre=cls.membre,
                type_transaction='DEPOT',
                montant=Decimal('50000.00'),
                session=cls.session,
                notes=f'Dépôt test {i+1}'
            )
        
        # 6. Créer un renflouement
        cls.renflouement = Renflouement.objects.create(
            membre=cls.membre,
            session=cls.session,
            montant_du=Decimal('100000.00'),
            montant_paye=Decimal('0.00'),
            cause='Renflouement fin d\'exercice',
            type_cause='RENFLOUEMENT_FIN_EXERCICE',
            ratio_caisse_inscription=Decimal('70.00'),
            ratio_fonds_social=Decimal('30.00')
        )
    
    def setUp(self):
        """Préparation avant chaque test"""
        self.client = Client()
    
    def test_payer_renflouement_montant_partiel_succes(self):
        """Test: Payer un renflouement avec un montant partiel"""
        print("\n✅ Test 1: Paiement partiel d'un renflouement")
        
        url = reverse('payer-renflouement-epargne', args=[self.renflouement.id])
        data = {
            'montant': 50000.00,
            'notes': 'Paiement partiel test'
        }
        
        response = self.client.post(
            url,
            data=json.dumps(data),
            content_type='application/json'
        )
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json()}")
        
        # Vérifications
        self.assertEqual(response.status_code, 201)
        
        response_data = response.json()
        self.assertTrue(response_data['success'])
        self.assertIn('50000', str(response_data['message']))
        
        # Vérifier que le paiement a été créé
        self.assertEqual(response_data['paiement']['montant'], '50000.00')
        
        # Vérifier que le renflouement a été mis à jour
        self.assertEqual(response_data['renflouement']['montant_paye'], '50000.00')
        self.assertFalse(response_data['renflouement']['is_solde'])
        
        # Vérifier l'épargne
        self.assertEqual(response_data['resume']['epargne_utilisee'], Decimal('50000.00'))
        self.assertEqual(response_data['resume']['epargne_apres'], Decimal('100000.00'))
        
        print("✅ Test réussi!")
    
    def test_payer_renflouement_montant_complet_succes(self):
        """Test: Payer un renflouement entièrement (sans montant spécifié)"""
        print("\n✅ Test 2: Paiement complet d'un renflouement")
        
        url = reverse('payer-renflouement-epargne', args=[self.renflouement.id])
        data = {
            'notes': 'Paiement complet'
        }
        
        response = self.client.post(
            url,
            data=json.dumps(data),
            content_type='application/json'
        )
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json()}")
        
        # Vérifications
        self.assertEqual(response.status_code, 201)
        
        response_data = response.json()
        self.assertTrue(response_data['success'])
        
        # Vérifier que le renflouement est entièrement payé
        self.assertEqual(response_data['renflouement']['montant_paye'], '100000.00')
        self.assertTrue(response_data['renflouement']['is_solde'])
        self.assertEqual(response_data['renflouement']['montant_restant'], '0.00')
        
        print("✅ Test réussi!")
    
    def test_payer_renflouement_epargne_insuffisante(self):
        """Test: Erreur quand l'épargne est insuffisante"""
        print("\n❌ Test 3: Épargne insuffisante")
        
        url = reverse('payer-renflouement-epargne', args=[self.renflouement.id])
        data = {
            'montant': 200000.00,  # Plus que l'épargne disponible (150 000)
            'notes': 'Tentative avec montant excessif'
        }
        
        response = self.client.post(
            url,
            data=json.dumps(data),
            content_type='application/json'
        )
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json()}")
        
        # Vérifications
        self.assertEqual(response.status_code, 400)
        
        response_data = response.json()
        self.assertFalse(response_data['success'])
        self.assertIn('Épargne insuffisante', response_data['error'])
        
        print("✅ Test réussi (erreur attendue détectée)!")
    
    def test_payer_renflouement_montant_invalide(self):
        """Test: Erreur quand le montant est 0 ou négatif"""
        print("\n❌ Test 4: Montant invalide")
        
        url = reverse('payer-renflouement-epargne', args=[self.renflouement.id])
        data = {
            'montant': 0,
            'notes': 'Montant invalide'
        }
        
        response = self.client.post(
            url,
            data=json.dumps(data),
            content_type='application/json'
        )
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json()}")
        
        # Vérifications
        self.assertEqual(response.status_code, 400)
        
        response_data = response.json()
        self.assertFalse(response_data['success'])
        self.assertIn('supérieur à 0', response_data['error'])
        
        print("✅ Test réussi (erreur attendue détectée)!")
    
    def test_payer_renflouement_montant_depasse(self):
        """Test: Erreur quand le montant dépasse ce qui est dû"""
        print("\n❌ Test 5: Montant dépasse ce qui est dû")
        
        url = reverse('payer-renflouement-epargne', args=[self.renflouement.id])
        data = {
            'montant': 150000.00,  # Dépasse 100 000 FCFA
            'notes': 'Montant excessif'
        }
        
        response = self.client.post(
            url,
            data=json.dumps(data),
            content_type='application/json'
        )
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json()}")
        
        # Vérifications
        self.assertEqual(response.status_code, 400)
        
        response_data = response.json()
        self.assertFalse(response_data['success'])
        self.assertIn('dépasse ce qui est dû', response_data['error'])
        
        print("✅ Test réussi (erreur attendue détectée)!")
    
    def test_repartition_paiement_proportionnelle(self):
        """Test: Vérifier que la répartition proportionnelle fonctionne"""
        print("\n✅ Test 6: Répartition proportionnelle")
        
        url = reverse('payer-renflouement-epargne', args=[self.renflouement.id])
        data = {
            'montant': 70000.00,  # 70 000 FCFA
            'notes': 'Test répartition'
        }
        
        response = self.client.post(
            url,
            data=json.dumps(data),
            content_type='application/json'
        )
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json()}")
        
        # Vérifications
        self.assertEqual(response.status_code, 201)
        
        response_data = response.json()
        paiement = response_data['paiement']
        
        # Caisse inscription: 70% de 70 000 = 49 000
        self.assertEqual(paiement['montant_caisse_inscription'], '49000.00')
        
        # Fonds social: 30% de 70 000 = 21 000
        self.assertEqual(paiement['montant_fonds_social'], '21000.00')
        
        print("✅ Test réussi!")
    
    def test_transaction_epargne_creee(self):
        """Test: Vérifier qu'une transaction d'épargne est bien créée"""
        print("\n✅ Test 7: Création de la transaction d'épargne")
        
        # Compter les transactions avant
        transactions_before = EpargneTransaction.objects.filter(
            membre=self.membre,
            type_transaction='RETRAIT_RENFLOUEMENT'
        ).count()
        
        url = reverse('payer-renflouement-epargne', args=[self.renflouement.id])
        data = {
            'montant': 50000.00,
            'notes': 'Test transaction'
        }
        
        response = self.client.post(
            url,
            data=json.dumps(data),
            content_type='application/json'
        )
        
        print(f"Status Code: {response.status_code}")
        
        # Vérifications
        self.assertEqual(response.status_code, 201)
        
        # Compter les transactions après
        transactions_after = EpargneTransaction.objects.filter(
            membre=self.membre,
            type_transaction='RETRAIT_RENFLOUEMENT'
        ).count()
        
        # Une transaction doit avoir été créée
        self.assertEqual(transactions_after, transactions_before + 1)
        
        # Vérifier les détails de la transaction
        nouvelle_transaction = EpargneTransaction.objects.filter(
            membre=self.membre,
            type_transaction='RETRAIT_RENFLOUEMENT'
        ).order_by('-date_transaction').first()
        
        self.assertEqual(nouvelle_transaction.montant, Decimal('-50000.00'))
        
        print("✅ Test réussi!")
    
    def test_renflouement_non_trouve(self):
        """Test: 404 quand le renflouement n'existe pas"""
        print("\n❌ Test 8: Renflouement non trouvé")
        
        fake_id = uuid.uuid4()
        url = reverse('payer-renflouement-epargne', args=[fake_id])
        data = {
            'montant': 50000.00
        }
        
        response = self.client.post(
            url,
            data=json.dumps(data),
            content_type='application/json'
        )
        
        print(f"Status Code: {response.status_code}")
        
        # Vérifications
        self.assertEqual(response.status_code, 404)
        
        print("✅ Test réussi (404 attendu)!")


# ============================================================================
# INSTRUCTIONS POUR EXÉCUTER LES TESTS
# ============================================================================
"""
Pour exécuter ces tests:

1. Exécuter tous les tests de cette classe:
   python manage.py test transactions.tests.PayerRenflouementAvecEpargneTestCase

2. Exécuter un test spécifique:
   python manage.py test transactions.tests.PayerRenflouementAvecEpargneTestCase.test_payer_renflouement_montant_partiel_succes

3. Exécuter avec verbosité:
   python manage.py test transactions.tests.PayerRenflouementAvecEpargneTestCase -v 2

4. Exécuter avec détails complets:
   python manage.py test transactions.tests.PayerRenflouementAvecEpargneTestCase -v 3
"""
