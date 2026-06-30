from django.test import TestCase
from django.contrib.auth import get_user_model
from datetime import date, timedelta
from decimal import Decimal

from core.models import Exercice, Session, Membre, ConfigurationMutuelle
from transactions.models import EpargneTransaction, RetraitEpargne


class ExerciceStatusTransitionTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user_en_regle = User.objects.create_user(username='enregle', password='pass')
        self.user_non_en_regle = User.objects.create_user(username='nonenregle', password='pass')
        self.config = ConfigurationMutuelle.get_configuration()
        self.config.montant_solidarite = Decimal('1000')
        self.config.save()

    def test_resume_financier_prend_en_compte_le_retrait_epargne(self):
        User = get_user_model()
        user = User.objects.create_user(username='patrimoine', password='pass')
        exercice = Exercice.objects.create(
            nom='Exercice Test',
            date_debut=date.today(),
            date_fin=date.today() + timedelta(days=365),
            statut='EN_COURS'
        )
        session = Session.objects.create(
            exercice=exercice,
            date_session=date.today(),
            statut='EN_COURS'
        )
        membre = Membre.objects.create(
            utilisateur=user,
            date_inscription=date.today(),
            exercice_inscription=exercice,
            session_inscription=session
        )

        EpargneTransaction.objects.create(
            membre=membre,
            type_transaction='DEPOT',
            montant=Decimal('100000.00'),
            session=session,
            notes='Dépôt initial'
        )
        EpargneTransaction.objects.create(
            membre=membre,
            type_transaction='RETRAIT_EPARGNE',
            montant=Decimal('-30000.00'),
            session=session,
            notes='Retrait test'
        )
        RetraitEpargne.objects.create(
            membre=membre,
            session=session,
            montant=Decimal('30000.00'),
            motif='Retrait test'
        )

        donnees = membre.get_donnees_completes()

        self.assertEqual(
            donnees['resume_financier']['patrimoine_total'],
            Decimal('70000.00')
        )
        self.assertEqual(
            donnees['resume_financier']['situation_nette'],
            Decimal('70000.00')
        )

    def test_first_exercice_sets_all_members_en_regle(self):
        exercice = Exercice.objects.create(
            nom='Exercice 1',
            date_debut=date.today(),
            statut='EN_COURS'
        )
        session = Session.objects.create(
            exercice=exercice,
            date_session=date.today(),
            statut='EN_COURS'
        )
        membre_a = Membre.objects.create(
            utilisateur=self.user_en_regle,
            date_inscription=date.today(),
            exercice_inscription=exercice,
            session_inscription=session
        )
        membre_b = Membre.objects.create(
            utilisateur=self.user_non_en_regle,
            date_inscription=date.today(),
            exercice_inscription=exercice,
            session_inscription=session
        )

        self.assertEqual(membre_a.statut, 'EN_REGLE')
        self.assertEqual(membre_b.statut, 'EN_REGLE')

    def test_second_exercice_preserves_previous_status(self):
        exercice1 = Exercice.objects.create(
            nom='Exercice 1',
            date_debut=date.today(),
            statut='EN_COURS'
        )
        session1 = Session.objects.create(
            exercice=exercice1,
            date_session=date.today(),
            statut='EN_COURS'
        )
        membre_en_regle = Membre.objects.create(
            utilisateur=self.user_en_regle,
            date_inscription=date.today(),
            exercice_inscription=exercice1,
            session_inscription=session1,
            statut='EN_REGLE'
        )
        membre_non_en_regle = Membre.objects.create(
            utilisateur=self.user_non_en_regle,
            date_inscription=date.today(),
            exercice_inscription=exercice1,
            session_inscription=session1,
            statut='NON_EN_REGLE'
        )

        # Créer le nouvel exercice, ceci doit marquer l'ancien exercice terminé
        exercice2 = Exercice.objects.create(
            nom='Exercice 2',
            date_debut=date.today() + timedelta(days=365),
            statut='EN_COURS'
        )

        membre_en_regle.refresh_from_db()
        membre_non_en_regle.refresh_from_db()

        self.assertEqual(membre_en_regle.statut, 'EN_REGLE')
        self.assertEqual(membre_non_en_regle.statut, 'NON_EN_REGLE')
        self.assertEqual(Exercice.objects.get(pk=exercice1.pk).statut, 'TERMINE')
        self.assertEqual(Session.objects.get(pk=session1.pk).statut, 'TERMINEE')
