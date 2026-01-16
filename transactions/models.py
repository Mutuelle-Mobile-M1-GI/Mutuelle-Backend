from django.db import models
from django.core.validators import MinValueValidator
from django.conf import settings
from decimal import Decimal, ROUND_HALF_UP
import uuid
from core.models import Membre, Session, Exercice, TypeAssistance,Interet
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
    date_paiement = models.DateTimeField(auto_now_add=True, verbose_name="Date de paiement")
    session = models.ForeignKey(Session, on_delete=models.CASCADE, related_name='paiements_inscription', verbose_name="Session")
    notes = models.TextField(blank=True, verbose_name="Notes")
    
    class Meta:
        verbose_name = "Paiement d'inscription"
        verbose_name_plural = "Paiements d'inscription"
        ordering = ['-date_paiement']
        
    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)
        
        # Alimenter le fonds social à chaque paiement d'inscription
        if is_new:
            from core.models import FondsSocial
            fonds = FondsSocial.get_fonds_actuel()
            if fonds:
                fonds.ajouter_montant(
                    self.montant,
                    f"Inscription {self.membre.numero_membre} - Session {self.session.nom}"
                )
    
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
    date_paiement = models.DateTimeField(auto_now_add=True, verbose_name="Date de paiement")
    notes = models.TextField(blank=True, verbose_name="Notes")
    
    class Meta:
        verbose_name = "Paiement de solidarité"
        verbose_name_plural = "Paiements de solidarité"
        ordering = ['-date_paiement']
        unique_together = [['membre', 'session']]
        
    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)
        
        try:
            if self.membre.calculer_statut_en_regle() :
                self.membre.statut = 'EN_REGLE'
                self.membre.save()
        except :
            print(f"Erreur de calcul de sttus en regle  ")
            pass
        
        # Alimenter le fonds social à chaque paiement de solidarité
        if is_new:
            from core.models import FondsSocial
            fonds = FondsSocial.get_fonds_actuel()
            if fonds:
                fonds.ajouter_montant(
                    self.montant,
                    f"Solidarité {self.membre.numero_membre} - Session {self.session.nom}"
                )
    
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
                if self.membre.calculer_statut_en_regle():
                    self.membre.statut = 'EN_REGLE'
                else:
                    self.membre.statut = 'NON_EN_REGLE'
                self.membre.save(update_fields=['statut'])
                print(f"   👤 Statut membre mis à jour : {self.membre.statut}")
            except Exception as e:
                print(f"   ⚠️ Erreur calcul statut membre : {e}")

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
    
    # Champs pour la redistribution des intérêts
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
        # Calcul automatique de la répartition capital/intérêt
        if not self.montant_capital and not self.montant_interet:
            self._calculer_repartition_capital_interet()
        
        super().save(*args, **kwargs)
        
        
        
        # Mise à jour du montant remboursé de l'emprunt
        self.emprunt.montant_rembourse = sum(
            r.montant for r in self.emprunt.remboursements.all()
        )
        self.emprunt.save()
        try:
            if self.emprunt.membre.calculer_statut_en_regle() :
                self.emprunt.membre.statut = 'EN_REGLE'
                self.emprunt.membre.save()
        except :
            print(f"Erreur de calcul de sttus en regle  ")
            pass
        
        # Redistribution des intérêts aux membres
        if self.montant_interet > 0:
            self._redistribuer_interets()
    
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
        2. Crée les renflouements pour tous les membres en règle
        """
        from core.models import FondsSocial
        from django.utils import timezone
        
        # 1. PRÉLEVER DU FONDS SOCIAL
        fonds = FondsSocial.get_fonds_actuel()
        if not fonds:
            print("ERREUR: Aucun fonds social actuel trouvé")
            return
        
        # Vérifier si le fonds a assez d'argent
        if not fonds.retirer_montant(
            self.montant,
            f"Assistance {self.type_assistance.nom} pour {self.membre.numero_membre}"
        ):
            print(f"ERREUR: Fonds social insuffisant pour l'assistance de {self.montant:,.0f} FCFA")
            return
        
        # Mettre à jour la date de paiement
        if not self.date_paiement:
            self.date_paiement = timezone.now()
            super().save(update_fields=['date_paiement'])
        
        # 2. CRÉER LES RENFLOUEMENTS
        self._creer_renflouement()
        
        print(f"Assistance payée: {self.montant:,.0f} FCFA prélevés du fonds social")
    
    def _creer_renflouement(self):
        """Crée les renflouements pour tous les membres en règle"""
        # Prendre les membres qui étaient en règle AVANT le paiement de l'assistance
        membres_en_regle = Membre.objects.filter(
            statut='EN_REGLE',
            date_inscription__lte=self.date_paiement or timezone.now()
        )
        
        nombre_membres = membres_en_regle.count()
        if nombre_membres == 0:
            print("ATTENTION: Aucun membre en règle pour le renflouement")
            return
        
        montant_par_membre = (self.montant / nombre_membres).quantize(
            Decimal('0.01'), rounding=ROUND_HALF_UP
        )
        
        renflouements_crees = 0
        for membre in membres_en_regle:
            Renflouement.objects.create(
                membre=membre,
                session=self.session,
                montant_du=montant_par_membre,
                cause=f"Assistance {self.type_assistance.nom} pour {self.membre.numero_membre}",
                type_cause='ASSISTANCE'
            )
            
            renflouements_crees += 1
            try:
                membre.statut='NON_EN_REGLE'
                membre.save()
            except Exception as e:
                print(f"Echec de la MAJ du statut du membre : {e}")
                
                pass
        
        print(f"Renflouement créé: {renflouements_crees} membres - {montant_par_membre:,.0f} FCFA chacun")

class Renflouement(models.Model):
    """
    Renflouements dus par les membres suite aux sorties d'argent
    """
    TYPE_CAUSE_CHOICES = [
        ('ASSISTANCE', 'Assistance'),
        ('COLLATION', 'Collation'),
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
    type_cause = models.CharField(max_length=15, choices=TYPE_CAUSE_CHOICES, verbose_name="Type de cause")
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
        is_new = self.pk is None
        super().save(*args, **kwargs)
        
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
        
        
        # CRUCIAL: Alimenter le fonds social avec le paiement de renflouement
        if is_new:
            from core.models import FondsSocial
            fonds = FondsSocial.get_fonds_actuel()
            if fonds:
                fonds.ajouter_montant(
                    self.montant,
                    f"Renflouement {self.renflouement.membre.numero_membre} - {self.renflouement.cause}"
                )

