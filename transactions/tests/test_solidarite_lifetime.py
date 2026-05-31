from django.test import TestCase
from django.utils import timezone
from django.contrib.auth import get_user_model
from decimal import Decimal

from core.models import Exercice, Session, ConfigurationMutuelle, Membre
from transactions.models import PaiementSolidarite


class SolidariteLifetimeTest(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username='testuser', email='test@example.com', password='pass')
        today = timezone.now().date()

        # Exercice et session en cours
        self.exercice = Exercice.objects.create(nom='Exercice Test', date_debut=today, statut='EN_COURS')
        self.session = Session.objects.create(exercice=self.exercice, date_session=today, statut='EN_COURS')

        # Membre (numero_membre sera généré automatiquement lors du save)
        self.membre = Membre.objects.create(
            utilisateur=self.user,
            date_inscription=today,
            exercice_inscription=self.exercice,
            session_inscription=self.session
        )

        # Configuration: définir un montant de solidarité explicite
        self.config = ConfigurationMutuelle.get_configuration()
        self.config.montant_solidarite = Decimal('1000')
        self.config.save()

    def test_paiement_complet_met_solidarite_terminee(self):
        # Avant paiement, le flag doit être False
        self.assertFalse(self.membre.solidarite_terminee)

        # Effectuer un paiement couvrant la solidarité
        PaiementSolidarite.objects.create(
            membre=self.membre,
            session=self.session,
            montant=self.config.montant_solidarite,
            montant_solidarite_du=self.config.montant_solidarite
        )

        # Recharger le membre depuis la DB
        self.membre.refresh_from_db()
        self.assertTrue(self.membre.solidarite_terminee)

        # Vérifier que get_donnees_completes expose solidarite_a_jour = True
        donnees = self.membre.get_donnees_completes()
        self.assertTrue(donnees['solidarite']['solidarite_a_jour'])
