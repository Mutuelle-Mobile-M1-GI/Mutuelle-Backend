from django.test import TestCase
from django.contrib.auth import get_user_model
from datetime import date, timedelta
from decimal import Decimal

from core.models import Exercice, Session, Membre, ConfigurationMutuelle
from transactions.models import Emprunt, PenaliteEmprunt


class EmpruntPenaliteTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.exercice = Exercice.objects.create(
            nom='Exercice Test',
            date_debut=date.today(),
            date_fin=date.today() + timedelta(days=365),
            statut='EN_COURS'
        )
        self.session1 = Session.objects.create(
            exercice=self.exercice,
            date_session=date.today(),
            statut='EN_COURS'
        )
        self.membre = Membre.objects.create(
            utilisateur=self.user,
            date_inscription=date.today(),
            exercice_inscription=self.exercice,
            session_inscription=self.session1
        )
        config, _ = ConfigurationMutuelle.objects.get_or_create(
            defaults={'taux_interet': Decimal('10.00')}
        )
        config.taux_interet = Decimal('10.00')
        config.save()

    def test_penalite_appliquee_apres_trois_sessions(self):
        emprunt = Emprunt.objects.create(
            membre=self.membre,
            montant_emprunte=Decimal('100000'),
            taux_interet=Decimal('10.00'),
            session_emprunt=self.session1
        )

        # Créer trois nouvelles sessions après l'emprunt et les activer.
        active_session = self.session1
        for i in range(2, 6):
            Session.objects.filter(pk=active_session.pk).update(statut='TERMINEE')
            active_session = Session.objects.create(
                exercice=self.exercice,
                date_session=self.session1.date_session + timedelta(days=30 * i),
                statut='EN_COURS'
            )

        emprunt.refresh_from_db()

        # Test 1: Vérifier que la première pénalité (Palier-3) est créée
        penalite_3 = PenaliteEmprunt.objects.filter(emprunt=emprunt, palier='Palier-3').first()
        self.assertIsNotNone(penalite_3, "Une pénalité Palier-3 doit être créée après 3 sessions terminées.")
        
        montant_penalite_3 = penalite_3.montant_interet_taux + penalite_3.montant_penalite_fixe
        self.assertEqual(
            montant_penalite_3,
            Decimal('15000.00'),
            "La pénalité Palier-3 totale doit être 15000 (intérêt + fixe)."
        )
        
        # Test 2: Vérifier montant_total_a_rembourser après Palier-3
        self.assertEqual(
            emprunt.montant_total_a_rembourser,
            Decimal('125000.00'),
            "Le montant total doit être 100000 + 10000 intérêt + 15000 pénalité = 125000."
        )
        
        # Test 3: Vérifier le statut après Palier-3
        self.assertEqual(
            emprunt.statut,
            'EN_RETARD',
            "L'emprunt doit être EN_RETARD après application de la pénalité."
        )
        
        # Test 4: Créer plus de sessions pour atteindre Palier-6
        for i in range(6, 8):
            Session.objects.filter(pk=active_session.pk).update(statut='TERMINEE')
            active_session = Session.objects.create(
                exercice=self.exercice,
                date_session=self.session1.date_session + timedelta(days=30 * i),
                statut='EN_COURS'
            )
        
        emprunt.refresh_from_db()
        
        # Test 5: Vérifier que la deuxième pénalité (Palier-6) est créée
        penalite_6 = PenaliteEmprunt.objects.filter(emprunt=emprunt, palier='Palier-6').first()
        self.assertIsNotNone(penalite_6, "Une pénalité Palier-6 doit être créée après 6 sessions terminées.")
        
        # Test 6: Vérifier qu'on a bien 2 pénalités (une par palier)
        penalites = PenaliteEmprunt.objects.filter(emprunt=emprunt)
        self.assertEqual(
            penalites.count(),
            2,
            "Il doit y avoir 2 pénalités: une à Palier-3 et une à Palier-6."
        )
        
        # Test 7: Vérifier que montant_total_a_rembourser inclut les deux pénalités
        montant_penalite_6 = penalite_6.montant_interet_taux + penalite_6.montant_penalite_fixe
        total_attendu = Decimal('125000.00') + montant_penalite_6
        self.assertEqual(
            emprunt.montant_total_a_rembourser,
            total_attendu,
            "Le montant total doit inclure les pénalités cumulées de tous les paliers."
        )
        
        # Test 8: Pas de redistribution immédiate (aucune EpargneTransaction)
        from transactions.models import EpargneTransaction
        epar_immediates = EpargneTransaction.objects.filter(
            type_transaction='AJOUT_INTERET',
            notes__contains='retard'
        )
        self.assertEqual(
            epar_immediates.count(),
            0,
            "Il ne doit y avoir aucune redistribution immédiate de la pénalité."
        )
        
        # Test 9: Remboursement complet → Redistribution totale
        emprunt.montant_rembourse = emprunt.montant_total_a_rembourser
        emprunt.save()
        
        # Vérifier que le statut est REMBOURSE
        emprunt.refresh_from_db()
        self.assertEqual(
            emprunt.statut,
            'REMBOURSE',
            "Le statut doit passer à REMBOURSE après remboursement complet."
        )
        
        # Test 10: Vérifier que la redistribution de TOUTES les pénalités est faite
        epar_apres_remboursement = EpargneTransaction.objects.filter(
            type_transaction='AJOUT_INTERET',
            notes__contains='redistribuée'
        )
        self.assertGreater(
            epar_apres_remboursement.count(),
            0,
            "Des EpargneTransaction doivent être créées pour la redistribution au remboursement complet."
        )
        
        # Vérifier que le montant redistribué = total de toutes les pénalités
        total_redistributed = sum(
            epar.montant 
            for epar in epar_apres_remboursement
        )
        total_penalites_appliquees = sum(
            p.montant_interet_taux + p.montant_penalite_fixe
            for p in penalites
        )
        self.assertEqual(
            total_redistributed,
            total_penalites_appliquees,
            "Le montant redistribué doit égaler la somme de toutes les pénalités appliquées."
        )
