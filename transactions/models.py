from logging import config
from django.db import models
from django.core.validators import MinValueValidator
from django.conf import settings
from decimal import Decimal, ROUND_HALF_UP
import uuid
from django.db import transaction
from core.models import Membre, Session, Exercice, TypeAssistance,Interet,FondsSocial
from decimal import Decimal, ROUND_HALF_UP
from django.db.models import Sum, Q
from django.utils import timezone
import uuid
from datetime import date, timedelta
from django.db import models
from django.core.validators import MinValueValidator
from django.utils import timezone

class PaiementInscription(models.Model):
    """
    Paiements d'inscription par tranche
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    membre = models.ForeignKey(Membre, on_delete=models.CASCADE, related_name='paiements_inscription')
    montant = models.DecimalField(
        max_digits=12, decimal_places=2,
        validators=[MinValueValidator(0)],
        verbose_name="Montant payé (FCFA)"
    )
    # ✅ NOUVEAU CHAMP qui va stocker le montant total de l'inscrption que le membre va devoir payer
    montant_inscription_du = models.DecimalField(
        max_digits=12, decimal_places=2,
        validators=[MinValueValidator(0)],
        verbose_name="Montant total dû pour l'inscription (FCFA)",
        help_text="Montant configuré au moment de l'inscription du membre"
    )
    date_paiement = models.DateTimeField(auto_now_add=True, verbose_name="Date de paiement")
    session = models.ForeignKey(Session, on_delete=models.CASCADE, related_name='paiements_inscription', verbose_name="Session")
    notes = models.TextField(blank=True, verbose_name="Notes")
    
    class Meta:
        verbose_name = "Paiement d'inscription"
        verbose_name_plural = "Paiements d'inscription"
        ordering = ['-date_paiement']
        
    def save(self, *args, **kwargs):
        # Sauvegarde et alimentation du fonds social en transaction
        with transaction.atomic():
            is_new = getattr(self, '_state', None) and getattr(self._state, 'adding', True)
            if is_new and self.montant and self.montant > 0:
                try:
                    fonds = FondsSocial.get_fonds_actuel()
                    if fonds:
                        desc = f"Inscription {self.membre.numero_membre} - Session {self.session.nom}"
                        fonds.ajouter_montant(self.montant, description=desc)
                    else:
                        print("Aucun fonds social actuel trouvé pour l'inscription")
                except Exception as e:
                    print(f"Erreur alimentation fonds pour inscription: {e}")
            
            is_new = self.pk is None
            # ✅ LOGIC AMÉLIORÉE: Gérer le montant_inscription_du
            if is_new:
                # Pour le premier paiement, enregistrer le montant actuel de la config
                premier_paiement = PaiementInscription.objects.filter(
                    membre=self.membre
                ).exists()

                if not premier_paiement:
                    # C'est le PREMIER paiement d'inscription de ce membre
                    from core.models import ConfigurationMutuelle
                    config = ConfigurationMutuelle.get_configuration()
                    self.montant_inscription_du = config.montant_inscription
                    print(f"📝 Premier paiement inscription: montant dû = {self.montant_inscription_du}")
                else:
                    # C'est un paiement suivant, récupérer le montant du premier paiement
                    self.montant_inscription_du = premier_paiement.montant_inscription_du
                    print(f"📝 Paiement suivant: montant dû = {self.montant_inscription_du}")

            super().save(*args, **kwargs)

            # ✅ Mettre à jour le statut inscription_terminee du membre
            if is_new:
                print('%%%%%%%%%%%mise a jour de insctiption_termine')
                self.membre.update_inscription_terminee()
                print(self.membre.update_inscription_terminee())
                self.membre.save()

            # Alimenter le fonds social
#             if is_new:
#                 from core.models import FondsSocial
#                 fonds = FondsSocial.get_fonds_actuel()
#                 if fonds:
#                     fonds.ajouter_montant(
#                         self.montant,
#                         f"Inscription {self.membre.numero_membre} - Session {self.session.nom}"
#                     )
    
    
    def __str__(self):
        return f"{self.membre.numero_membre} - {self.montant:,.0f} FCFA ({self.date_paiement.date()})"
    
class PaiementSolidarite(models.Model):
    """
    Paiements de solidarité (fonds social) par session
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    membre = models.ForeignKey(Membre, on_delete=models.CASCADE, related_name='paiements_solidarite')
    session = models.ForeignKey(Session, on_delete=models.CASCADE, related_name='paiements_solidarite')
    montant = models.DecimalField(
        max_digits=12, decimal_places=2,
        validators=[MinValueValidator(0)],
        verbose_name="Montant payé (FCFA)"
    )
    # ✅ NOUVEAU CHAMP pour stocker le montant total de la solidarite que le membre va devoir payer
    montant_solidarite_du = models.DecimalField(
        max_digits=12, decimal_places=2,
        validators=[MinValueValidator(0)],
        verbose_name="Montant dû pour cette session (FCFA)",
        help_text="Montant configuré au moment du paiement de cette session"
    )
    date_paiement = models.DateTimeField(auto_now_add=True, verbose_name="Date de paiement")
    notes = models.TextField(blank=True, verbose_name="Notes")
    
    class Meta:
        verbose_name = "Paiement de solidarité"
        verbose_name_plural = "Paiements de solidarité"
        ordering = ['-date_paiement']
        # ❌ RETIRER unique_together car on peut payer en plusieurs fois
        # unique_together = [['membre', 'session']]
        
    def save(self, *args, **kwargs):
        # Sauvegarde et alimentation du fonds social en transaction
        with transaction.atomic():
            is_new = getattr(self, '_state', None) and getattr(self._state, 'adding', True)
            super().save(*args, **kwargs)

            if is_new and self.montant and self.montant > 0:
                try:
                    fonds = FondsSocial.get_fonds_actuel()
                    if fonds:
                        desc = f"Solidarité {self.membre.numero_membre} - Session {self.session.nom}"
                        fonds.ajouter_montant(self.montant, description=desc)
                        print(f"Debug: ajout effectué {self.montant}")
                    else:
                        print("Aucun fonds social actuel trouvé pour enregistrer la solidarité.")
                except Exception as e:
                    print(f"Erreur lors de l'alimentation du fonds social: {e}")
                    
            is_new = self.pk is None

            # ✅ LOGIC AMÉLIORÉE: Enregistrer le montant dû au moment du paiement
            if is_new and not self.montant_solidarite_du:
                from core.models import ConfigurationMutuelle
                config = ConfigurationMutuelle.get_configuration()
                self.montant_solidarite_du = config.montant_solidarite
                print(f"💰 Solidarité session {self.session.nom}: montant dû = {self.montant_solidarite_du}")

            # ✅ CORRECTION: Ne mettre à jour le statut que si on peut définir les statuts (≥3 sessions)
            try:
                from core.models import Membre
                peut_definir_statuts = Membre.peut_definir_statuts_membre(membre=self.membre)

                if peut_definir_statuts and self.membre.calculer_statut_en_regle():
                    self.membre.statut = 'EN_REGLE'
                    self.membre.save()
                elif peut_definir_statuts:
                    # Si on peut définir les statuts mais membre n'est pas en règle
                    self.membre.statut = 'NON_EN_REGLE'
                    self.membre.save()
            except Exception as e:
                print(f"Erreur de calcul de statut en règle: {e}")
                pass
        
    
    def __str__(self):
        return f"{self.membre.numero_membre} - Session {self.session.nom} - {self.montant:,.0f} FCFA"

class EpargneTransaction(models.Model):
    """
    Transactions d'épargne (dépôts et retraits pour prêts)
    """
    TYPE_CHOICES = [
        ('DEPOT', 'Dépôt'),
        ('RETRAIT_PRET', 'Retrait pour prêt'),
        ('AJOUT_INTERET', 'Ajout d\'intérêt'),
        ('RETOUR_REMBOURSEMENT', 'Retour de remboursement'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    membre = models.ForeignKey(Membre, on_delete=models.CASCADE, related_name='transactions_epargne')
    type_transaction = models.CharField(max_length=20, choices=TYPE_CHOICES, verbose_name="Type de transaction")
    montant = models.DecimalField(
        max_digits=12, decimal_places=2,
        verbose_name="Montant (FCFA)"
    )
    session = models.ForeignKey(Session, on_delete=models.CASCADE, related_name='transactions_epargne')
    date_transaction = models.DateTimeField(auto_now_add=True, verbose_name="Date de transaction")
    notes = models.TextField(blank=True, verbose_name="Notes")
    
    class Meta:
        verbose_name = "Transaction d'épargne"
        verbose_name_plural = "Transactions d'épargne"
        ordering = ['-date_transaction']
    
    def __str__(self):
        signe = "+" if self.montant >= 0 else ""
        return f"{self.membre.numero_membre} - {self.get_type_transaction_display()} - {signe}{self.montant:,.0f} FCFA"




class Emprunt(models.Model):
    """
    Emprunts effectués par les membres
    """
    STATUS_CHOICES = [
        ('EN_COURS', 'En cours'),
        ('REMBOURSE', 'Remboursé'),
        ('EN_RETARD', 'En retard'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    membre = models.ForeignKey(Membre, on_delete=models.CASCADE, related_name='emprunts')
    montant_emprunte = models.DecimalField(
        max_digits=12, decimal_places=2,
        validators=[MinValueValidator(0)],
        verbose_name="Montant emprunté (FCFA)"
    )
    taux_interet = models.DecimalField(
        max_digits=5, decimal_places=2,
        verbose_name="Taux d'intérêt (%)"
    )
    montant_total_a_rembourser = models.DecimalField(
        max_digits=12, decimal_places=2,
        verbose_name="Montant total à rembourser (FCFA)"
    )
    montant_rembourse = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        verbose_name="Montant déjà remboursé (FCFA)"
    )
    session_emprunt = models.ForeignKey(Session, on_delete=models.CASCADE, related_name='emprunts')
    date_emprunt = models.DateTimeField(auto_now_add=True, verbose_name="Date d'emprunt")
    date_remboursement_max = models.DateField(
        null=True, blank=True,
        verbose_name="Date de Remboursement maximale",
        help_text="Si non renseignée, sera automatiquement fixée à 2 mois après la date d'emprunt"
    )
    statut = models.CharField(max_length=15, choices=STATUS_CHOICES, default='EN_COURS', verbose_name="Statut")
    notes = models.TextField(blank=True, verbose_name="Notes")
    
    # Champs de suivi automatique
    date_creation = models.DateTimeField(auto_now_add=True, verbose_name="Date de création")
    date_modification = models.DateTimeField(auto_now=True, verbose_name="Dernière modification")
    
    class Meta:
        verbose_name = "Emprunt"
        verbose_name_plural = "Emprunts"
        ordering = ['-date_emprunt']
        indexes = [
            models.Index(fields=['statut', 'date_remboursement_max']),
            models.Index(fields=['membre', 'statut']),
        ]
    
    def __str__(self):
        return f"{self.membre.numero_membre} - {self.montant_emprunte:,.0f} FCFA ({self.statut})"
    
    @property
    def montant_restant_a_rembourser(self):
        """Calcule le montant restant à rembourser"""
        return max(0, self.montant_total_a_rembourser - self.montant_rembourse)
    
    @property
    def montant_interets(self):
        """Calcule le montant des intérêts"""
        return self.montant_total_a_rembourser - self.montant_emprunte
    
    @property
    def pourcentage_rembourse(self):
        """Calcule le pourcentage remboursé"""
        if self.montant_total_a_rembourser == 0:
            return 0
        return min(100, (self.montant_rembourse / self.montant_total_a_rembourser) * 100)
    
    @property
    def is_en_retard(self):
        """Vérifie si l'emprunt est en retard"""
        if self.statut == 'REMBOURSE':
            return False
        
        if not self.date_remboursement_max:
            return False
            
        today = timezone.now().date()
        return today > self.date_remboursement_max
    
    @property
    def jours_de_retard(self):
        """Calcule le nombre de jours de retard"""
        if not self.is_en_retard:
            return 0
            
        today = timezone.now().date()
        return (today - self.date_remboursement_max).days
    
    @property
    def jours_restants(self):
        """Calcule le nombre de jours restants avant échéance"""
        if self.statut == 'REMBOURSE' or not self.date_remboursement_max:
            return None
            
        today = timezone.now().date()
        diff = (self.date_remboursement_max - today).days
        return max(0, diff)
    
    def _calculer_date_remboursement_max_auto(self):
        """Calcule automatiquement la date max de remboursement (2 mois après emprunt)"""
        if self.date_emprunt:
            date_emprunt = self.date_emprunt.date() if hasattr(self.date_emprunt, 'date') else self.date_emprunt
            return date_emprunt + timedelta(days=60)  # 2 mois = 60 jours
        return None
    
    def _calculer_montant_total_auto(self):
        return self.montant_emprunte 
    
    def _determiner_statut_auto(self):
        """Détermine automatiquement le statut basé sur les remboursements et dates"""
        print(f"🔍 Détermination statut pour emprunt {self.id}")
        print(f"   - Montant remboursé: {self.montant_rembourse}")
        print(f"   - Montant total: {self.montant_total_a_rembourser}")
        print(f"   - Date max: {self.date_remboursement_max}")
        print(f"   - Statut actuel: {self.statut}")
        
        # Priorité 1: Vérifier si complètement remboursé
        if self.montant_rembourse >= self.montant_total_a_rembourser:
            nouveau_statut = 'REMBOURSE'
            print(f"   ✅ Emprunt complètement remboursé -> {nouveau_statut}")
            return nouveau_statut
        
        # Priorité 2: Vérifier si en retard
        if self.is_en_retard:
            nouveau_statut = 'EN_RETARD'
            print(f"   ⚠️ Emprunt en retard de {self.jours_de_retard} jours -> {nouveau_statut}")
            return nouveau_statut
        
        # Priorité 3: En cours par défaut
        nouveau_statut = 'EN_COURS'
        print(f"   🔄 Emprunt en cours normal -> {nouveau_statut}")
        return nouveau_statut
    
    def capitaliser_interets_retard(self):
        from core.models import ConfigurationMutuelle, Session
        from decimal import Decimal
        import datetime

    # 1. On compte les sessions TERMINEES après l'octroi du prêt
        query_sessions = Session.objects.filter(
            date_session__gt=self.session_emprunt.date_session,
            statut='TERMINEE'
        )
        sessions_passees = query_sessions.count()

        print(f"🔍 Audit Emprunt {self.membre}: Sessions écoulées={sessions_passees}")

    # 2. Condition : On applique l'intérêt UNIQUEMENT toutes les 3 sessions
    # (3, 6, 9, 12...) et seulement si sessions_passees > 0
        if sessions_passees > 0 and sessions_passees % 3 == 0 and self.statut != 'REMBOURSE':
        
        # --- SÉCURITÉ : Éviter d'ajouter plusieurs fois pour la même session ---
        # On vérifie si on n'a pas déjà ajouté une pénalité pour ce "palier" de sessions
            label_palier = f"Palier {sessions_passees} sessions"
            if label_palier in (self.notes or ""):
                print(f"⏭️ Saut : Pénalité déjà appliquée pour le palier {sessions_passees}")
                return False

            config = ConfigurationMutuelle.objects.first()
            if not config:
                return False
            
            taux = config.taux_interet / Decimal('100')
            reste = self.montant_total_a_rembourser - self.montant_rembourse
        
            if reste > 0:
                penalite = reste * taux
                self.montant_total_a_rembourser += penalite
                self.statut = 'EN_RETARD'
            
                horodatage = datetime.datetime.now().strftime("%d/%m/%Y")
            # On ajoute le nom du palier dans la note pour le suivi
                self.notes = (self.notes or "") + f"\n[{horodatage}] {label_palier}: +{penalite} FCFA"
            
                self.save()
                print(f"💰 Pénalité palier {sessions_passees} appliquée : +{penalite} FCFA")
                return True
            
        return False
    
    def save(self, *args, **kwargs):
        """Sauvegarde avec escompte : le membre reçoit le net et doit le nominal."""
        print(f"🔍 SAVE EMPRUNT - Début pour {getattr(self, 'id', 'NOUVEAU')}")
        
        try:
            # On vérifie si c'est une création AVANT de modifier les montants
            is_new = self._state.adding 
            
            if is_new:
                # --- LOGIQUE D'ESCOMPTE ---
                # On part du montant envoyé par le frontend (ex: 100 000)
                nominal_demande = self.montant_emprunte 
                
                # Calcul de la retenue (3% de 100 000 = 3 000)
                interet_retenu = (nominal_demande * self.taux_interet) / Decimal('100')
                
                # MISE À JOUR DES CHAMPS :
                # 1. La dette totale est le montant nominal (100 000)
                self.montant_total_a_rembourser = nominal_demande
                
                # 2. Le montant "emprunté" devient le net décaissé (97 000)
                # C'est ce montant qui impactera la caisse/épargne
                self.montant_emprunte = nominal_demande - interet_retenu
                
                print(f"   ✅ Application Escompte : Nominal {nominal_demande} | Net décaissé {self.montant_emprunte} | Intérêt {interet_retenu}")

            # 🔧 ÉTAPE 2: Sécurité - Date d'emprunt
            if not self.date_emprunt:
                self.date_emprunt = timezone.now()
            
            # 🔧 ÉTAPE 3: Calcul de l'échéance (2 mois par défaut)
            if not self.date_remboursement_max:
                self.date_remboursement_max = self._calculer_date_remboursement_max_auto()
            
            # 🔧 ÉTAPE 4: Sécurité des remboursements
            if self.montant_rembourse < 0:
                self.montant_rembourse = 0
            
            # 🔧 ÉTAPE 5: Détermination du statut (EN_COURS, REMBOURSE, etc.)
            self.statut = self._determiner_statut_auto()
            
            # 🔧 ÉTAPE 6: Validations de sécurité
            if self.montant_emprunte <= 0:
                raise ValueError(f"Montant décaissé invalide: {self.montant_emprunte}")

            # 🔧 ÉTAPE 7: Sauvegarde réelle en base de données
            print(f"   💾 Sauvegarde en base de données...")
            super().save(*args, **kwargs)
            
            # 🚀 ÉTAPE 8: Redistribution des intérêts (Seulement à la création)
            if is_new:
                print(f"   💰 Lancement de la redistribution des intérêts...")
                self.distribuer_interets_precomptes()
            
            # 🔧 ÉTAPE 9: Mise à jour du statut du membre (En règle ou non)
            try:
                from core.models import Membre
                peut_definir_statuts = Membre.peut_definir_statuts_membre(membre=self.membre)
                
                if peut_definir_statuts and self.membre.calculer_statut_en_regle():
                    print("SAUVEGARDE DE L'EMPRUNT ON VA VOIR SI IL EST EN REGLE ET IL L'EST ")
                    self.membre.statut = 'EN_REGLE'
                    self.membre.save()
                elif peut_definir_statuts:
                    print("SAUVEGARDE DE L'EMPRUNT ON VA VOIR SI IL EST EN REGLE ET NE L'EST PAS DU TOUT ! ")
                    self.membre.statut = 'NON_EN_REGLE'
                    self.membre.save()
            except Exception as e:
                print(f"Erreur de calcul de statut en règle: {e}")
                pass
                
            print(f"   ✅ EMPRUNT SAUVÉ AVEC SUCCÈS")

        except Exception as e:
            print(f"   ❌ ERREUR LORS DE LA SAUVEGARDE: {e}")
            import traceback
            print(f"   ❌ Traceback: {traceback.format_exc()}")
            raise
        
    @classmethod
    def verifier_retards_globaux(cls):
        """Méthode utilitaire pour vérifier tous les emprunts en retard"""
        print("🔍 VÉRIFICATION GLOBALE DES RETARDS")
        
        emprunts_actifs = cls.objects.filter(statut__in=['EN_COURS', 'EN_RETARD'])
        emprunts_modifies = 0
        
        for emprunt in emprunts_actifs:
            ancien_statut = emprunt.statut
            # Re-déclencher la logique de save sans modifier les données
            emprunt.save()
            
            if ancien_statut != emprunt.statut:
                emprunts_modifies += 1
                print(f"   🔄 Emprunt {emprunt.id}: {ancien_statut} -> {emprunt.statut}")
        
        print(f"   ✅ Vérification terminée: {emprunts_modifies} emprunts mis à jour")
        return emprunts_modifies
    
    def clean(self):
        """Validation Django pour l'admin"""
        from django.core.exceptions import ValidationError
        
        if self.montant_emprunte and self.montant_emprunte <= 0:
            raise ValidationError({'montant_emprunte': 'Le montant emprunté doit être positif'})
        
        if self.taux_interet and self.taux_interet < 0:
            raise ValidationError({'taux_interet': 'Le taux d\'intérêt ne peut pas être négatif'})
        
        if self.montant_rembourse and self.montant_rembourse < 0:
            raise ValidationError({'montant_rembourse': 'Le montant remboursé ne peut pas être négatif'})
        
        if self.date_remboursement_max and self.date_emprunt:
            date_emprunt = self.date_emprunt.date() if hasattr(self.date_emprunt, 'date') else self.date_emprunt
            if self.date_remboursement_max <= date_emprunt:
                raise ValidationError({
                    'date_remboursement_max': 'La date de remboursement maximale doit être postérieure à la date d\'emprunt'
                })
    def distribuer_interets_precomptes(self):
    
        from django.db import transaction
        from core.models import Interet
    # On importe EpargneTransaction ici pour éviter les imports circulaires
        from transactions.models import EpargneTransaction
    
    # 1. Calcul de la cagnotte par différence (Dette 100k - Net 97k = 3000)
    # C'est plus précis que de refaire le calcul du pourcentage
        cagnotte = self.montant_total_a_rembourser - self.montant_emprunte
    
        if cagnotte <= 0:
            return

    # 2. Obtenir l'épargne globale
        total_global = Decimal('0')
        epargnes_membres = []
    
        tous_membres = Membre.objects.all()
        for m in tous_membres:
            e = m.calculer_epargne_pure()
            if e > 0:
                total_global += e
                epargnes_membres.append({'membre': m, 'montant': e})
    
        if total_global > 0:
            with transaction.atomic():
                for item in epargnes_membres:
                # Calcul au prorata
                    part = (item['montant'] / total_global) * cagnotte
                    part = part.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                
                    if part > 0:
                    # A. Création dans la table Interet (Historique des gains)
                        Interet.objects.create(
                            membre=item['membre'],
                            emprunt_source=self,
                            exercice=self.session_emprunt.exercice,
                            session=self.session_emprunt,
                            montant=part
                        )
                    
                    # B. Création dans EpargneTransaction (Flux financier réel)
                    # C'est cette ligne qui sera lue par calculer_epargne_pure
                        EpargneTransaction.objects.create(
                            membre=item['membre'],
                            type_transaction='AJOUT_INTERET',
                            montant=part, # Montant positif
                            session=self.session_emprunt,
                            notes=f"Intérêt perçu sur prêt de {self.membre.numero_membre}"
                        )
                print(f"✅ Redistribution de {cagnotte:,.0f} FCFA et mise à jour des épargnes terminées.")


class Remboursement(models.Model):
    """
    Remboursements par tranche des emprunts
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    emprunt = models.ForeignKey(Emprunt, on_delete=models.CASCADE, related_name='remboursements')
    montant = models.DecimalField(
        max_digits=12, decimal_places=2,
        validators=[MinValueValidator(0)],
        verbose_name="Montant remboursé (FCFA)"
    )
    session = models.ForeignKey(Session, on_delete=models.CASCADE, related_name='remboursements')
    date_remboursement = models.DateTimeField(auto_now_add=True, verbose_name="Date de remboursement")
    notes = models.TextField(blank=True, verbose_name="Notes")
    
    montant_capital = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        verbose_name="Part capital du remboursement"
    )
    montant_interet = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        verbose_name="Part intérêt du remboursement"
    )
    
    class Meta:
        verbose_name = "Remboursement"
        verbose_name_plural = "Remboursements"
        ordering = ['-date_remboursement']
    
    def __str__(self):
        return f"{self.emprunt.membre.numero_membre} - {self.montant:,.0f} FCFA ({self.date_remboursement.date()})"
    
    def save(self, *args, **kwargs):
        # Déterminer si c'est une création avant de sauvegarder
        is_new = self._state.adding
        
        # 1. Garder ta logique de calcul capital/intérêt
        if not self.montant_capital and not self.montant_interet:
            self._calculer_repartition_capital_interet()
        
        # 2. Sauvegarde standard
        super().save(*args, **kwargs)
        
        # 3. Garder ta mise à jour de l'emprunt
        self.emprunt.montant_rembourse = sum(
            r.montant for r in self.emprunt.remboursements.all()
        )
        self.emprunt.save()

        # 4. AJOUT : Création de la ligne dans EpargneTransaction pour le Trésor
        if is_new:
            try:
                # Import local pour éviter les erreurs d'import circulaire
                from .models import EpargneTransaction
                
                EpargneTransaction.objects.create(
                    membre=self.emprunt.membre,
                    session=self.session,
                    montant=self.montant,
                    type_transaction='RETOUR_REMBOURSEMENT',
                    notes=f"Auto: Retour de fonds (Remboursement prêt #{self.emprunt.id})",
                    date_transaction=self.date_remboursement
                )
                print(f"💰 Trésor mis à jour : +{self.montant} FCFA")
            except Exception as e:
                print(f"❌ Erreur création EpargneTransaction: {e}")

        # 5. Garder ta logique de statut membre
        try:
            from core.models import Membre
            if self.emprunt.membre.calculer_statut_en_regle():
                self.emprunt.membre.statut = 'EN_REGLE'
                self.emprunt.membre.save()
        except Exception as e:
            print(f"Erreur de calcul de statut en règle: {e}")
            pass

    def _calculer_repartition_capital_interet(self):
        """Calcule la répartition entre capital et intérêt du remboursement"""
        emprunt = self.emprunt
        capital_restant = emprunt.montant_emprunte - sum(
            r.montant_capital for r in emprunt.remboursements.exclude(id=self.id)
        )
        
        if self.montant <= capital_restant:
            self.montant_capital = self.montant
            self.montant_interet = Decimal('0')
        else:
            self.montant_capital = capital_restant
            self.montant_interet = self.montant - capital_restant
    

class AssistanceAccordee(models.Model):
    """
    Assistances accordées aux membres
    """
    STATUS_CHOICES = [
        ('DEMANDEE', 'Demandée'),
        ('APPROUVEE', 'Approuvée'),
        ('PAYEE', 'Payée'),
        ('REJETEE', 'Rejetée'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    membre = models.ForeignKey(Membre, on_delete=models.CASCADE, related_name='assistances_recues')
    type_assistance = models.ForeignKey(TypeAssistance, on_delete=models.CASCADE, related_name='assistances_accordees')
    montant = models.DecimalField(
        max_digits=12, decimal_places=2,
        verbose_name="Montant accordé (FCFA)"
    )
    session = models.ForeignKey(Session, on_delete=models.CASCADE, related_name='assistances_accordees')
    date_demande = models.DateTimeField(auto_now_add=True, verbose_name="Date de demande")
    date_paiement = models.DateTimeField(null=True, blank=True, verbose_name="Date de paiement")
    statut = models.CharField(max_length=15, choices=STATUS_CHOICES, default='PAYEE', verbose_name="Statut")
    justification = models.TextField(verbose_name="Justification")
    notes = models.TextField(blank=True, verbose_name="Notes administratives")
    
    class Meta:
        verbose_name = "Assistance accordée"
        verbose_name_plural = "Assistances accordées"
        ordering = ['-date_demande']
    
    def __str__(self):
        return f"{self.membre.numero_membre} - {self.type_assistance.nom} - {self.montant:,.0f} FCFA"
    
    def save(self, *args, **kwargs):
        old_statut = None
        is_new = self.pk is None
        
        # 🔧 RÉCUPÉRER L'ANCIEN STATUT SEULEMENT SI MODIFICATION
        if not is_new:
            try:
                old_instance = AssistanceAccordee.objects.get(pk=self.pk)
                old_statut = old_instance.statut
            except AssistanceAccordee.DoesNotExist:
                # Cas rare où l'objet a été supprimé entre temps
                is_new = True
        
        # Copier le montant du type d'assistance si pas défini
        if not self.montant and self.type_assistance:
            self.montant = self.type_assistance.montant
        
        # Sauvegarder
        super().save(*args, **kwargs)
        
        # Traiter le paiement si nécessaire
        should_process = (
            self.statut == 'PAYEE' and 
            (is_new or old_statut != 'PAYEE') and
            not hasattr(self, '_assistance_payee_traitee')
        )
        
        if should_process:
            self._traiter_paiement_assistance()
            self._assistance_payee_traitee = True
        
    def _traiter_paiement_assistance(self):
        """
        Traite le paiement d'une assistance:
        1. Prélève du fonds social
        2. Enregistre la dépense (sans créer de renflouement)
        ✅ NOUVEAU: Les renflouements sont créés à la fin de l'exercice
        """
        from core.models import FondsSocial, DépenseExercice
        from django.utils import timezone
        
        # 1. PRÉLEVER DU FONDS SOCIAL
        fonds = FondsSocial.get_fonds_actuel()
        if not fonds:
            print("❌ ERREUR: Aucun fonds social actuel trouvé")
            return
        
        # Vérifier si le fonds a assez d'argent
        if not fonds.retirer_montant(
            self.montant,
            f"Assistance {self.type_assistance.nom} pour {self.membre.numero_membre}"
        ):
            print(f"❌ ERREUR: Fonds social insuffisant pour l'assistance de {self.montant:,.0f} FCFA")
            return
        
        # Mettre à jour la date de paiement
        if not self.date_paiement:
            self.date_paiement = timezone.now()
            super().save(update_fields=['date_paiement'])
        
        # 2. ENREGISTRER LA DÉPENSE (pour calculer les renflouements à la fin)
        try:
            exercice = Exercice.get_exercice_en_cours()
            if exercice:
                DépenseExercice.objects.create(
                    exercice=exercice,
                    type_depense='ASSISTANCE',
                    montant=self.montant,
                    description=f"Assistance {self.type_assistance.nom} pour {self.membre.numero_membre}",
                    session=self.session,
                    beneficiaire=self.membre
                )
                print(f"   📋 Dépense enregistrée: {self.montant:,.0f} FCFA")
            else:
                print("⚠️  Aucun exercice EN_COURS pour enregistrer la dépense")
        except Exception as e:
            print(f"⚠️  Erreur lors de l'enregistrement de la dépense: {e}")
        
        print(f"✅ Assistance payée: {self.montant:,.0f} FCFA prélevés du fonds social")
        print(f"   📋 Dépense enregistrée pour renflouement en fin d'exercice")


class Renflouement(models.Model):
    """
    Renflouements dus par les membres suite aux sorties d'argent
    """
    TYPE_CAUSE_CHOICES = [
        ('ASSISTANCE', 'Assistance'),
        ('COLLATION', 'Collation'),
        ('RENFLOUEMENT_FIN_EXERCICE', 'Renflouement fin d\'exercice'),
        ('AUTRE', 'Autre'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    membre = models.ForeignKey(Membre, on_delete=models.CASCADE, related_name='renflouements')
    session = models.ForeignKey(Session, on_delete=models.CASCADE, related_name='renflouements')
    montant_du = models.DecimalField(
        max_digits=12, decimal_places=2,
        validators=[MinValueValidator(0)],
        verbose_name="Montant dû (FCFA)"
    )
    montant_paye = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        validators=[MinValueValidator(0)],
        verbose_name="Montant payé (FCFA)"
    )
    cause = models.TextField(verbose_name="Cause du renflouement",blank=True)
    type_cause = models.CharField(max_length=40, choices=TYPE_CAUSE_CHOICES, verbose_name="Type de cause")
    date_creation = models.DateTimeField(auto_now_add=True, verbose_name="Date de création")
    date_derniere_modification = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Renflouement"
        verbose_name_plural = "Renflouements"
        ordering = ['-date_creation']
    
    def __str__(self):
        return f"{self.membre.numero_membre} - {self.montant_du:,.0f} FCFA ({self.type_cause})"
    
    @property
    def montant_restant(self):
        """Calcule le montant restant à payer"""
        return self.montant_du - self.montant_paye
    
    @property
    def is_solde(self):
        """Vérifie si le renflouement est soldé"""
        return self.montant_paye >= self.montant_du
    
    @property
    def pourcentage_paye(self):
        """Calcule le pourcentage payé"""
        if self.montant_du == 0:
            return 100
        return (self.montant_paye / self.montant_du) * 100

class PaiementRenflouement(models.Model):
    """
    Paiements de renflouement par tranche
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    renflouement = models.ForeignKey(Renflouement, on_delete=models.CASCADE, related_name='paiements')
    montant = models.DecimalField(
        max_digits=12, decimal_places=2,
        validators=[MinValueValidator(0)],
        verbose_name="Montant payé (FCFA)"
    )
    session = models.ForeignKey(Session, on_delete=models.CASCADE, related_name='paiements_renflouement')
    date_paiement = models.DateTimeField(auto_now_add=True, verbose_name="Date de paiement")
    notes = models.TextField(blank=True, verbose_name="Notes")
    
    class Meta:
        verbose_name = "Paiement de renflouement"
        verbose_name_plural = "Paiements de renflouement"
        ordering = ['-date_paiement']
    
    def __str__(self):
        return f"{self.renflouement.membre.numero_membre} - {self.montant:,.0f} FCFA ({self.date_paiement.date()})"
    
    def save(self, *args, **kwargs):
        # Utiliser un indicateur fiable pour nouvelle instance et une transaction
        is_new = getattr(self._state, 'adding', True)
        from django.db import transaction as _transaction
        from core.models import FondsSocial

        with _transaction.atomic():
            super().save(*args, **kwargs)

            # Mise à jour du montant payé du renflouement (agrégation sûre)
            total = self.renflouement.paiements.aggregate(total=Sum('montant'))['total'] or Decimal('0')
            self.renflouement.montant_paye = total
            self.renflouement.save()

            try:
                if self.renflouement.membre.calculer_statut_en_regle():
                    # Mise à jour atomique
                    Membre.objects.filter(pk=self.renflouement.membre.pk).update(statut='EN_REGLE')
            except Exception as e:
                print(f"Erreur de calcul de statut en règle: {e}")

            # Alimenter le fonds social pour les paiements de renflouement (nouveaux paiements uniquement)
            if is_new and self.montant and self.montant > 0:
                try:
                    fonds = FondsSocial.get_fonds_actuel()
                    if fonds:
                        desc = f"Renflouement {self.renflouement.membre.numero_membre} - {self.renflouement.cause}"
                        fonds.ajouter_montant(self.montant, description=desc)
                        print(f"Debug: renflouement ajouté {self.montant}")
                    else:
                        print("Aucun fonds social actuel trouvé pour renflouement.")
                except Exception as e:
                    print(f"Erreur lors de l'alimentation du fonds social (renflouement): {e}")
        
        is_new = self.pk is None
        # Mise à jour du montant payé du renflouement
        self.renflouement.montant_paye = sum(
            p.montant for p in self.renflouement.paiements.all()
        )
        self.renflouement.save()
        try:
            if self.renflouement.membre.calculer_statut_en_regle() :
                self.renflouement.membre.statut = 'EN_REGLE'
                self.renflouement.membre.save()
        except :
            print(f"Erreur de calcul de sttus en regle  ")
            pass
                
