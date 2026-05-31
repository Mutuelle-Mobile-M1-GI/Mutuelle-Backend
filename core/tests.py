from django.test import TestCase
from django.contrib.auth import get_user_model
from datetime import date, timedelta
from decimal import Decimal

from core.models import Exercice, Session, Membre, ConfigurationMutuelle


class ExerciceStatusTransitionTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user_en_regle = User.objects.create_user(username='enregle', password='pass')
        self.user_non_en_regle = User.objects.create_user(username='nonenregle', password='pass')
        self.config = ConfigurationMutuelle.get_configuration()
        self.config.montant_solidarite = Decimal('1000')
        self.config.save()

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
