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

    # ✅ NOUVEAU : Snapshot des épargnes au moment de l'emprunt
    epargnes_snapshot = models.JSONField(
        default=dict, blank=True, null=True,
        verbose_name="Épargnes snapshot à la création",
        help_text="Enregistre les épargnes de chaque membre au moment de l'emprunt pour les redistributions futures"
    )
    
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
        if not self.montant_total_a_rembourser:
            return 0
        return max(0, self.montant_total_a_rembourser - self.montant_rembourse)
    
    @property
    def montant_interets(self):
        """Calcule le montant des intérêts"""
        if not self.montant_total_a_rembourser:
            return 0
        return self.montant_total_a_rembourser - self.montant_emprunte
    
    @property
    def pourcentage_rembourse(self):
        """Calcule le pourcentage remboursé"""
        if not self.montant_total_a_rembourser or self.montant_total_a_rembourser == 0:
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
        
        # Priorité 2: Maintenir le statut EN_RETARD si une pénalité a déjà été appliquée.
        if self.statut == 'EN_RETARD' or (hasattr(self, 'penalites') and self.penalites.exists()):
            nouveau_statut = 'EN_RETARD'
            print(f"   ⚠️ Emprunt marqué en retard (pénalités existantes) -> {nouveau_statut}")
            return nouveau_statut

        # Priorité 3: Vérifier si en retard par date
        if self.is_en_retard:
            nouveau_statut = 'EN_RETARD'
            print(f"   ⚠️ Emprunt en retard de {self.jours_de_retard} jours -> {nouveau_statut}")
            return nouveau_statut
        
        # Priorité 4: En cours par défaut
        nouveau_statut = 'EN_COURS'
        print(f"   🔄 Emprunt en cours normal -> {nouveau_statut}")
        return nouveau_statut
    
    #redistribution des 15k de penalite

    def _redistribuer_penalite(self, montant_a_redistribuer, tag_palier):
        """
        Redistribue la pénalité aux membres qui AVAIENT une épargne
        au moment de la création de l'emprunt (utilise le snapshot)
        """
        if montant_a_redistribuer <= 0:
            return

        # ✅ UTILISER LE SNAPSHOT AU LIEU DE L'ÉPARGNE ACTUELLE
        if not self.epargnes_snapshot:
            print("⚠️ Aucun snapshot d'épargne trouvé. Annulation de la redistribution.")
            return

        total_global = Decimal('0')
        epargnes_snapshot_list = []

        # Convertir le snapshot JSON en données exploitables
        for membre_id_str, data in self.epargnes_snapshot.items():
            try:
                epargne = Decimal(data['epargne']) if isinstance(data['epargne'], str) else Decimal(data['epargne'])
                if epargne > 0:
                    total_global += epargne
                    epargnes_snapshot_list.append({
                        'membre_id': membre_id_str,
                        'numero': data['numero'],
                        'epargne': epargne
                    })
            except (ValueError, KeyError) as e:
                print(f"⚠️ Erreur conversion snapshot: {e}")
                continue

        if total_global <= 0:
            print("⚠️ Aucune épargne dans le snapshot trouvée, redistribution annulée.")
            return

        print(f"📊 Redistribution pénalité {tag_palier}: Total épargne snapshot = {total_global:,.0f} FCFA")

        with transaction.atomic():
            for item in epargnes_snapshot_list:
                try:
                    membre = Membre.objects.get(id=item['membre_id'])
                    part = (item['epargne'] / total_global) * montant_a_redistribuer
                    part = part.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

                    if part > 0:
                        Interet.objects.create(
                            membre=membre,
                            emprunt_source=self,
                            exercice=self.session_emprunt.exercice,
                            session=self.session_emprunt,
                            montant=part
                        )
                        EpargneTransaction.objects.create(
                            membre=membre,
                            type_transaction='AJOUT_INTERET',
                            montant=part,
                            session=self.session_emprunt,
                            notes=(
                                f"Pénalité retard {tag_palier} sur prêt de "
                                f"{self.membre.numero_membre}: {part:,.0f} FCFA "
                                f"(basé sur épargne snapshot: {item['epargne']:,.0f} FCFA)"
                            )
                        )
                        print(f"   ✅ {item['numero']}: +{part:,.0f} FCFA (épargne snapshot: {item['epargne']:,.0f})")
                except Membre.DoesNotExist:
                    print(f"⚠️ Membre {item['numero']} introuvable (snapshot)")
                    continue

        print(f"✅ Redistribution de {montant_a_redistribuer:,.0f} FCFA ({tag_palier}) terminée.")
    
    def _redistribuer_penalite_au_remboursement(self):
        """
        Redistribue la pénalité UNIQUEMENT quand l'emprunt est complètement remboursé.
        Redistribue le total: montant_interet_taux + montant_penalite_fixe
        """
        # Vérifier s'il existe une pénalité
        penalite = PenaliteEmprunt.objects.filter(emprunt=self).first()
        
        if not penalite:
            print(f"✅ Pas de pénalité appliquée pour cet emprunt, rien à redistribuer.")
            return
        
        # Calculer le total de la pénalité à redistribuer
        montant_total_penalite = penalite.montant_interet_taux + penalite.montant_penalite_fixe
        
        if montant_total_penalite <= 0:
            print(f"⚠️ Montant de pénalité = 0, rien à redistribuer.")
            return
        
        print(f"🎯 Redistribution pénalité au remboursement: {montant_total_penalite:,.0f} FCFA")
        
        # Utiliser le snapshot pour la redistribution
        if not self.epargnes_snapshot:
            print("⚠️ Aucun snapshot d'épargne trouvé. Pas de redistribution.")
            return
        
        total_global = Decimal('0')
        epargnes_snapshot_list = []
        
        # Convertir le snapshot JSON en données exploitables
        for membre_id_str, data in self.epargnes_snapshot.items():
            try:
                epargne = Decimal(data['epargne']) if isinstance(data['epargne'], str) else Decimal(data['epargne'])
                if epargne > 0:
                    total_global += epargne
                    epargnes_snapshot_list.append({
                        'membre_id': membre_id_str,
                        'numero': data['numero'],
                        'epargne': epargne
                    })
            except (ValueError, KeyError) as e:
                print(f"⚠️ Erreur conversion snapshot: {e}")
                continue
        
        if total_global <= 0:
            print("⚠️ Aucune épargne dans le snapshot trouvée, redistribution annulée.")
            return
        
        print(f"📊 Total épargne snapshot = {total_global:,.0f} FCFA")
        
        with transaction.atomic():
            for item in epargnes_snapshot_list:
                try:
                    membre = Membre.objects.get(id=item['membre_id'])
                    part = (item['epargne'] / total_global) * montant_total_penalite
                    part = part.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                    
                    if part > 0:
                        Interet.objects.create(
                            membre=membre,
                            emprunt_source=self,
                            exercice=self.session_emprunt.exercice,
                            session=self.session_emprunt,
                            montant=part
                        )
                        EpargneTransaction.objects.create(
                            membre=membre,
                            type_transaction='AJOUT_INTERET',
                            montant=part,
                            session=self.session_emprunt,
                            notes=(
                                f"Pénalité retard redistribuée au remboursement sur prêt de "
                                f"{self.membre.numero_membre}: {part:,.0f} FCFA "
                                f"(basé sur épargne snapshot: {item['epargne']:,.0f} FCFA)"
                            )
                        )
                        print(f"   ✅ {item['numero']}: +{part:,.0f} FCFA (épargne snapshot: {item['epargne']:,.0f})")
                except Membre.DoesNotExist:
                    print(f"⚠️ Membre {item['numero']} introuvable (snapshot)")
                    continue
        
        print(f"✅ Redistribution pénalité au remboursement ({montant_total_penalite:,.0f} FCFA) terminée.")
    
    #recalcul des pourcentages apres chaque 3 sessions
    def capitaliser_interets_retard(self):
        from core.models import ConfigurationMutuelle, Session
        from decimal import Decimal
        import datetime

        # 1. On compte les sessions TERMINEES strictement après l'octroi
        sessions_passees = Session.objects.filter(
            date_session__gt=self.session_emprunt.date_session,
            statut='TERMINEE'
        ).count()

        print(f"🔍 Audit {self.membre}: {sessions_passees} sessions écoulées")

        # 2. Condition Modulo 3 (Tous les 3, 6, 9... mois)
        if sessions_passees > 0 and sessions_passees % 3 == 0 and self.statut != 'REMBOURSE':
            
            # SECURITÉ : Vérifier si ce palier précis a déjà été appliqué
            tag_palier = f"Palier-{sessions_passees}"
            
            if PenaliteEmprunt.objects.filter(emprunt=self, palier=tag_palier).exists():
                print(f"⏭️ Palier {sessions_passees} déjà facturé. Repos.")
                return False

            config = ConfigurationMutuelle.objects.first()
            if not config or config.taux_interet <= 0:
                return False
            
            # 3. Calcul de la pénalité sur le RESTE à payer
            taux = config.taux_interet / Decimal('100')
            reste = self.montant_total_a_rembourser - self.montant_rembourse
            
            if reste > 0:
                PENALITE_FIXE = Decimal('15000')
                penalite_taux = reste * taux
                penalite_totale = penalite_taux + PENALITE_FIXE

                # ✅ NOUVEAU: Créer l'enregistrement de pénalité AVANT de modifier l'emprunt
                session_actuelle = Session.objects.filter(statut='EN_COURS').first()
                if not session_actuelle:
                    print("⚠️ Aucune session en cours pour enregistrer la pénalité")
                    return False

                penalite_record = PenaliteEmprunt.objects.create(
                    emprunt=self,
                    type_penalite='RETARD_PALIER',
                    palier=f"Palier-{sessions_passees}",
                    sessions_ecoulees=sessions_passees,
                    montant_reste_avant=reste,
                    taux_applique=config.taux_interet,
                    montant_interet_taux=penalite_taux,
                    montant_penalite_fixe=PENALITE_FIXE,
                    session_application=session_actuelle,
                    # appliquee_par sera NULL pour les pénalités automatiques
                )

                # Mise à jour de l'emprunt
                self.montant_total_a_rembourser += penalite_totale
                self.statut = 'EN_RETARD'

                # ✅ Ajouter une note pour l'historique
                date_str = datetime.datetime.now().strftime("%d/%m/%Y")
                note_entree = f"\n[{date_str}] Pénalité appliquée: +{penalite_totale:,.0f} FCFA (voir détails pénalité ID: {penalite_record.id})"
                self.notes = (self.notes or "") + note_entree

                # Enregistrer directement pour éviter de réévaluer le statut
                super(Emprunt, self).save()
                # ⚠️ NE PAS redistribuer ici - on redistribuera seulement à REMBOURSE

                print(f"💰 SUCCÈS : +{penalite_totale:,.0f} FCFA ajoutés")
                print(f"📋 Pénalité enregistrée avec ID: {penalite_record.id}")
                print(f"⏳ Redistribution = lors du remboursement complet")
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
                interet_retenu = interet_retenu.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                
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

            # ✅ ÉTAPE 5bis: Enregistrement snapshot des épargnes (NOUVEAU)
            if is_new and not self.epargnes_snapshot:
                print(f"   📸 Enregistrement snapshot des épargnes...")
                from core.models import Membre  # Import local pour éviter les conflits
                self.epargnes_snapshot = {}
                tous_membres = Membre.objects.filter(actif=True).exclude(id=self.membre.id)
                for m in tous_membres:
                    epargne = m.calculer_epargne_pure()
                    if epargne > 0:
                        self.epargnes_snapshot[str(m.id)] = {
                            'numero': m.numero_membre,
                            'epargne': str(epargne)
                        }
                        print(f"     - {m.numero_membre}: {epargne:,.0f} FCFA")

            # 🔧 ÉTAPE 6: Validations de sécurité
            if self.montant_emprunte <= 0:
                raise ValueError(f"Montant décaissé invalide: {self.montant_emprunte}")

            # 🔧 ÉTAPE 7: Sauvegarde réelle en base de données
            print(f"   💾 Sauvegarde en base de données...")
            super().save(*args, **kwargs)
            
            # � ÉTAPE 7bis: Redistribution pénalité au remboursement (NOUVEAU)
            # Si le statut passe à REMBOURSE, on redistribue la pénalité
            if self.statut == 'REMBOURSE':
                print(f"   🎯 Emprunt complètement remboursé → Redistribution pénalité...")
                self._redistribuer_penalite_au_remboursement()
            
            # �🚀 ÉTAPE 8: Redistribution des intérêts (Seulement à la création)
            if is_new:
                print(f"   💰 Lancement de la redistribution des intérêts...")
                self.distribuer_interets_precomptes()
            
            # 🔧 ÉTAPE 9: Mise à jour du statut du membre (En règle ou non)
            # ✅ NOUVELLE LOGIQUE: Période de grâce de 3 mois par exercice
            try:
                from core.models import Membre
                peut_definir_statuts = Membre.peut_definir_statuts_membre(membre=self.membre)
                
                if not peut_definir_statuts:
                    # Période de grâce: membre reste EN_REGLE
                    print("⏳ EMPRUNT: Période de grâce → membre reste EN_REGLE")
                    self.membre.statut = 'EN_REGLE'
                    self.membre.save()
                else:
                    # Après période de grâce: évaluation normale
                    if self.membre.calculer_statut_en_regle():
                        print("✅ EMPRUNT: Membre en règle après période de grâce")
                        self.membre.statut = 'EN_REGLE'
                        self.membre.save()
                    else:
                        print("❌ EMPRUNT: Membre non en règle après période de grâce")
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
    
        tous_membres = Membre.objects.filter(actif=True)
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
                print(f"   Dépense enregistrée: {self.montant:,.0f} FCFA")
            else:
                print("  Aucun exercice EN_COURS pour enregistrer la dépense")
        except Exception as e:
            print(f"Erreur lors de l'enregistrement de la dépense: {e}")
        
        print(f"Assistance payée: {self.montant:,.0f} FCFA prélevés du fonds social")
        print(f"  Dépense enregistrée pour renflouement en fin d'exercice")


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
    session = models.ForeignKey(Session, on_delete=models.CASCADE, related_name='renflouements', null=True, blank=True)
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
    
    # ✅ NOUVEAUX CHAMPS pour le renflouement proportionnel
    exercice_renflouement = models.ForeignKey(
        'core.Exercice', 
        on_delete=models.CASCADE, 
        related_name='renflouements_fin_exercice',
        null=True, blank=True,
        verbose_name="Exercice de renflouement",
        help_text="Exercice pour lequel ce renflouement a été calculé"
    )
    ratio_caisse_inscription = models.DecimalField(
        max_digits=5, decimal_places=2, 
        null=True, blank=True,
        verbose_name="Ratio caisse inscription (%)",
        help_text="Pourcentage des paiements qui va à la caisse inscription"
    )
    ratio_fonds_social = models.DecimalField(
        max_digits=5, decimal_places=2, 
        null=True, blank=True,
        verbose_name="Ratio fonds social (%)",
        help_text="Pourcentage des paiements qui va au fonds social"
    )
    
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
        montant_du = self.montant_du or Decimal('0')
        montant_paye = self.montant_paye or Decimal('0')
        return montant_du - montant_paye
    
    @property
    def is_solde(self):
        """Vérifie si le renflouement est soldé"""
        if self.montant_du is None:
            return False
        return self.montant_paye >= self.montant_du

    
    @property
    def pourcentage_paye(self):
        """Calcule le pourcentage payé"""
        if not self.montant_du or self.montant_du == 0:
            return 100
        return (self.montant_paye / self.montant_du) * 100
    
    def calculer_repartition_paiement(self, montant_paiement):
        """
        Calcule la répartition d'un paiement selon les ratios définis
        
        Args:
            montant_paiement (Decimal): Montant du paiement à répartir
            
        Returns:
            dict: {
                'caisse_inscription': Decimal,
                'fonds_social': Decimal,
                'total': Decimal
            }
        """
        if not self.ratio_caisse_inscription or not self.ratio_fonds_social:
            # Ancien système : tout va au fonds social
            return {
                'caisse_inscription': Decimal('0'),
                'fonds_social': montant_paiement,
                'total': montant_paiement
            }
        
        # Nouveau système proportionnel
        montant_caisse = (montant_paiement * self.ratio_caisse_inscription) / Decimal('100')
        montant_fonds = (montant_paiement * self.ratio_fonds_social) / Decimal('100')
        
        # Arrondir pour éviter les problèmes de précision
        montant_caisse = montant_caisse.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        montant_fonds = montant_fonds.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        
        return {
            'caisse_inscription': montant_caisse,
            'fonds_social': montant_fonds,
            'total': montant_caisse + montant_fonds
        }

class PaiementRenflouement(models.Model):
    """
    Paiements de renflouement par tranche avec répartition proportionnelle
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    renflouement = models.ForeignKey(Renflouement, on_delete=models.CASCADE, related_name='paiements')
    montant = models.DecimalField(
        max_digits=12, decimal_places=2,
        validators=[MinValueValidator(0)],
        verbose_name="Montant payé (FCFA)"
    )
    
    # ✅ NOUVEAUX CHAMPS pour la traçabilité de la répartition
    montant_caisse_inscription = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        verbose_name="Montant vers caisse inscription (FCFA)",
        help_text="Partie du paiement qui va à la caisse inscription"
    )
    montant_fonds_social = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        verbose_name="Montant vers fonds social (FCFA)",
        help_text="Partie du paiement qui va au fonds social"
    )
    ratio_caisse_utilise = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True,
        verbose_name="Ratio caisse utilisé (%)",
        help_text="Ratio caisse inscription utilisé pour ce paiement"
    )
    ratio_fonds_utilise = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True,
        verbose_name="Ratio fonds utilisé (%)",
        help_text="Ratio fonds social utilisé pour ce paiement"
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
        is_new = getattr(self._state, 'adding', True)
        from django.db import transaction as _transaction
        from core.models import FondsSocial, CaisseInscription

        with _transaction.atomic():
            # ✅ NOUVEAU : Calcul de la répartition avant sauvegarde
            if is_new and self.montant > 0:
                repartition = self.renflouement.calculer_repartition_paiement(self.montant)
                
                self.montant_caisse_inscription = repartition['caisse_inscription']
                self.montant_fonds_social = repartition['fonds_social']
                self.ratio_caisse_utilise = self.renflouement.ratio_caisse_inscription
                self.ratio_fonds_utilise = self.renflouement.ratio_fonds_social
                
                print(f"💰 Répartition paiement renflouement {self.renflouement.membre.numero_membre}:")
                print(f"   - Total: {self.montant:,.0f} FCFA")
                print(f"   - Caisse inscription: {self.montant_caisse_inscription:,.0f} FCFA ({self.ratio_caisse_utilise}%)")
                print(f"   - Fonds social: {self.montant_fonds_social:,.0f} FCFA ({self.ratio_fonds_utilise}%)")

            super().save(*args, **kwargs)

            # Mise à jour du montant payé du renflouement (agrégation sûre)
            total = self.renflouement.paiements.aggregate(total=Sum('montant'))['total'] or Decimal('0')
            self.renflouement.montant_paye = total
            self.renflouement.save()

            # Mise à jour du statut du membre
            try:
                from core.models import Membre  # Import local pour éviter les conflits
                if self.renflouement.membre.calculer_statut_en_regle():
                    Membre.objects.filter(pk=self.renflouement.membre.pk).update(statut='EN_REGLE')
            except Exception as e:
                print(f"Erreur de calcul de statut en règle: {e}")

            # ✅ NOUVEAU : Alimentation proportionnelle des caisses
            if is_new and self.montant > 0:
                try:
                    # Alimentation de la caisse inscription
                    if self.montant_caisse_inscription > 0:
                        caisse = CaisseInscription.get_caisse_actuelle()
                        if caisse:
                            desc = f"Renflouement {self.renflouement.membre.numero_membre} - Part caisse inscription ({self.ratio_caisse_utilise}%)"
                            caisse.ajouter_montant(self.montant_caisse_inscription, description=desc)
                            print(f"✅ Caisse inscription alimentée: +{self.montant_caisse_inscription:,.0f} FCFA")
                    
                    # Alimentation du fonds social
                    if self.montant_fonds_social > 0:
                        fonds = FondsSocial.get_fonds_actuel()
                        if fonds:
                            desc = f"Renflouement {self.renflouement.membre.numero_membre} - Part fonds social ({self.ratio_fonds_utilise}%)"
                            fonds.ajouter_montant(self.montant_fonds_social, description=desc)
                            print(f"✅ Fonds social alimenté: +{self.montant_fonds_social:,.0f} FCFA")
                            
                except Exception as e:
                    print(f"Erreur lors de l'alimentation des caisses (renflouement): {e}")


class RepartitionRenflouementExercice(models.Model):
    """
    Modèle pour stocker les calculs de répartition de renflouement de fin d'exercice
    Permet la traçabilité complète des calculs
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    exercice = models.OneToOneField(
        'core.Exercice',
        on_delete=models.CASCADE,
        related_name='repartition_renflouement',
        verbose_name="Exercice"
    )
    
    # Données de calcul
    total_sorties_caisse_inscription = models.DecimalField(
        max_digits=15, decimal_places=2,
        verbose_name="Total sorties caisse inscription (FCFA)",
        help_text="Somme de toutes les sorties de la caisse inscription"
    )
    total_sorties_fonds_social = models.DecimalField(
        max_digits=15, decimal_places=2,
        verbose_name="Total sorties fonds social (FCFA)",
        help_text="Somme de toutes les sorties du fonds social"
    )
    total_sorties_global = models.DecimalField(
        max_digits=15, decimal_places=2,
        verbose_name="Total sorties global (FCFA)",
        help_text="Somme totale des sorties des deux caisses"
    )
    
    # Ratios calculés
    ratio_caisse_inscription = models.DecimalField(
        max_digits=5, decimal_places=2,
        verbose_name="Ratio caisse inscription (%)",
        help_text="Pourcentage des sorties de la caisse inscription"
    )
    ratio_fonds_social = models.DecimalField(
        max_digits=5, decimal_places=2,
        verbose_name="Ratio fonds social (%)",
        help_text="Pourcentage des sorties du fonds social"
    )
    
    # Données des membres
    nombre_membres_en_regle = models.IntegerField(
        verbose_name="Nombre de membres en règle",
        help_text="Nombre de membres en règle au moment du calcul"
    )
    nombre_membres_non_en_regle = models.IntegerField(
        verbose_name="Nombre de membres non en règle",
        help_text="Nombre de membres non en règle qui devront payer"
    )
    nombre_membres_total = models.IntegerField(
        verbose_name="Nombre total de membres",
        help_text="Nombre total de membres actifs"
    )
    
    # Montant par membre
    montant_par_membre = models.DecimalField(
        max_digits=12, decimal_places=2,
        verbose_name="Montant par membre (FCFA)",
        help_text="Montant que chaque membre non en règle doit payer"
    )
    
    # Métadonnées
    date_calcul = models.DateTimeField(auto_now_add=True, verbose_name="Date de calcul")
    calcule_par = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        verbose_name="Calculé par"
    )
    notes_calcul = models.TextField(
        blank=True,
        verbose_name="Notes de calcul",
        help_text="Détails supplémentaires sur le calcul"
    )
    
    class Meta:
        verbose_name = "Répartition renflouement exercice"
        verbose_name_plural = "Répartitions renflouements exercices"
        ordering = ['-date_calcul']
    
    def __str__(self):
        return f"Répartition {self.exercice.nom} - {self.montant_par_membre:,.0f} FCFA/membre"
    
    @property
    def formule_calcul(self):
        """Retourne la formule de calcul pour affichage"""
        return (
            f"{self.total_sorties_global:,.0f} FCFA ÷ {self.nombre_membres_en_regle} membres en règle = "
            f"{self.montant_par_membre:,.0f} FCFA par membre"
        )
    
    @property
    def detail_ratios(self):
        """Retourne le détail des ratios pour affichage"""
        return (
            f"Caisse inscription: {self.total_sorties_caisse_inscription:,.0f} FCFA ({self.ratio_caisse_inscription}%) | "
            f"Fonds social: {self.total_sorties_fonds_social:,.0f} FCFA ({self.ratio_fonds_social}%)"
        )
                
from logging import config
from django.db import models
from django.core.validators import MinValueValidator
from django.conf import settings
from decimal import Decimal, ROUND_HALF_UP
import uuid
from django.db import transaction
from core.models import Membre, Session, Exercice, TypeAssistance, Interet, FondsSocial, CaisseInscription
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
    Paiement d'inscription en une seule tranche par membre.
    Les montants vont dans la caisse inscription (plus dans le fonds social).
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    membre = models.ForeignKey(Membre, on_delete=models.CASCADE, related_name='paiements_inscription')
    montant = models.DecimalField(
        max_digits=12, decimal_places=2,
        validators=[MinValueValidator(0)],
        verbose_name="Montant payé (FCFA)"
    )
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
        constraints = [
            models.UniqueConstraint(fields=['membre'], name='unique_paiement_inscription_par_membre'),
        ]

    def save(self, *args, **kwargs):
        """
        - Un seul paiement d'inscription par membre (contrainte unique).
        - Alimente la caisse inscription uniquement avec la partie DUE.
        - Surplus éventuel versé en épargne personnelle (sans doubler en caisse).
        """
        from core.models import ConfigurationMutuelle

        with transaction.atomic():
            is_new = getattr(self._state, 'adding', True)

            if is_new and PaiementInscription.objects.filter(membre=self.membre).exists():
                from django.core.exceptions import ValidationError
                raise ValidationError(
                    "Ce membre a déjà un paiement d'inscription. L'inscription se fait en une seule tranche."
                )

            # 1) Montant dû = config (une seule tranche)
            if is_new:
                config = ConfigurationMutuelle.get_configuration()
                self.montant_inscription_du = config.montant_inscription
                print(f"📝 Paiement inscription (une tranche): montant dû = {self.montant_inscription_du}")

            # 2) Surplus éventuel (avec une tranche: restant_avant = montant_du)
            surplus_pour_epargne = Decimal('0')
            montant_pour_caisse = Decimal('0')
            if is_new and self.montant and self.montant > 0:
                montant_du = self.montant_inscription_du
                # Part qui règle l'inscription (max = montant_du)
                montant_pour_caisse = min(self.montant, montant_du)
                if self.montant > montant_du:
                    surplus_pour_epargne = self.montant - montant_du
                    print(
                        f"💰 Surplus inscription pour {self.membre.numero_membre} : "
                        f"{surplus_pour_epargne} FCFA (sera versé en épargne)"
                    )

            # 3) Sauvegarde du paiement
            super().save(*args, **kwargs)

            # 4) Alimenter la caisse inscription UNIQUEMENT avec la partie due
            if is_new and montant_pour_caisse and montant_pour_caisse > 0:
                try:
                    caisse = CaisseInscription.get_caisse_actuelle()
                    if caisse:
                        desc = f"Inscription {self.membre.numero_membre} - Session {self.session.nom}"
                        caisse.ajouter_montant(montant_pour_caisse, description=desc)
                    else:
                        print("Aucune caisse inscription actuelle trouvée")
                except Exception as e:
                    print(f"Erreur alimentation caisse inscription: {e}")

            # 5) Mettre à jour inscription_terminee
            if is_new:
                self.membre.update_inscription_terminee()
                self.membre.save()

            # 6) Surplus vers épargne personnelle
            if is_new and surplus_pour_epargne > 0:
                try:
                    EpargneTransaction.objects.create(
                        membre=self.membre,
                        type_transaction='DEPOT',
                        montant=surplus_pour_epargne,
                        session=self.session,
                        notes="Surplus paiement inscription"
                    )
                    print(
                        f"✅ Surplus {surplus_pour_epargne} FCFA ajouté à l'épargne de {self.membre.numero_membre}"
                    )
                except Exception as e:
                    print(f"❌ Erreur épargne surplus inscription: {e}")

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
        verbose_name="Montant dû pour cette exercice (FCFA)",
        help_text="Montant configuré au moment du paiement de cet exercice"
    )
    date_paiement = models.DateTimeField(auto_now_add=True, verbose_name="Date de paiement")
    notes = models.TextField(blank=True, verbose_name="Notes")
    
    class Meta:
        verbose_name = "Paiement de solidarité"
        verbose_name_plural = "Paiements de solidarité"
        ordering = ['-date_paiement']
        # ❌ RETIRER unique_together car on peut payer en plusieurs fois
        # unique_together = [['membre', 'session']]
        
    def clean(self):
        from django.core.exceptions import ValidationError

        if self.membre and not self.membre.inscription_terminee:
            raise ValidationError({
                'membre': (
                    "Le membre n'a pas terminé son inscription. "
                    "Le paiement de solidarité est interdit tant que l'inscription n'est pas complète."
                )
            })

    def save(self, *args, **kwargs):
        """
        Solidarité : paiement unique à vie (comme l'inscription).
        - Le membre paie une seule fois (en une ou plusieurs tranches) jusqu'au montant total.
        - Si le montant de la solidarité augmente dans la config, le membre peut payer le supplément.
        - Tout paiement dépassant le montant restant est rejeté avec un message clair.
        """
        is_new = getattr(self, '_state', None) and getattr(self._state, 'adding', True)

        if is_new:
            from core.models import ConfigurationMutuelle
            from django.core.exceptions import ValidationError
            from django.db.models import Sum

            config = ConfigurationMutuelle.get_configuration()
            montant_solidarite_actuel = config.montant_solidarite

            # Montant dû à vie = montant configuré actuellement
            if not self.montant_solidarite_du:
                self.montant_solidarite_du = montant_solidarite_actuel

            # Total déjà payé par ce membre (TOUTES sessions confondues)
            total_deja_paye = PaiementSolidarite.objects.filter(
                membre=self.membre
            ).aggregate(total=Sum('montant'))['total'] or Decimal('0')

            montant_restant = montant_solidarite_actuel - total_deja_paye

            # Cas 1 : solidarité déjà complète
            if total_deja_paye >= montant_solidarite_actuel:
                raise ValidationError(
                    f"❌ La solidarité de {self.membre.numero_membre} est déjà complète. "
                    f"Montant dû : {montant_solidarite_actuel:,.0f} FCFA — "
                    f"Déjà payé : {total_deja_paye:,.0f} FCFA."
                )

            # Cas 2 : paiement trop élevé (surplus)
            if self.montant > montant_restant:
                raise ValidationError(
                    f"❌ Paiement trop élevé. "
                    f"Montant restant à payer pour la solidarité : {montant_restant:,.0f} FCFA. "
                    f"Vous avez tenté de payer : {self.montant:,.0f} FCFA. "
                    f"Veuillez saisir exactement {montant_restant:,.0f} FCFA ou moins."
                )

        self.full_clean()

        with transaction.atomic():
            super().save(*args, **kwargs)

            if is_new and self.montant and self.montant > 0:
                # Alimenter le fonds social
                try:
                    fonds = FondsSocial.get_fonds_actuel()
                    if fonds:
                        desc = f"Solidarité {self.membre.numero_membre} - Session {self.session.nom}"
                        fonds.ajouter_montant(self.montant, description=desc)
                        print(f"Debug: ajout solidarité fonds social {self.montant}")
                    else:
                        print("Aucun fonds social actuel trouvé pour enregistrer la solidarité.")
                except Exception as e:
                    print(f"Erreur lors de l'alimentation du fonds social: {e}")

                # Mettre à jour solidarite_terminee du membre
                try:
                    self.membre.update_solidarite_terminee()
                    self.membre.save(update_fields=['solidarite_terminee'])
                except Exception as e:
                    print(f"Erreur lors de la mise à jour solidarite_terminee: {e}")

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

    def clean(self):
        from django.core.exceptions import ValidationError

        if self.membre and not self.membre.inscription_terminee:
            raise ValidationError({
                'membre': (
                    "Le membre n'a pas terminé son inscription. "
                    "Il ne peut pas effectuer d'opérations d'épargne tant que l'inscription n'est pas complète."
                )
            })

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class PenaliteEmprunt(models.Model):
    """
    Modèle pour tracer toutes les pénalités appliquées aux emprunts
    Permet une transparence totale pour justifier devant les membres
    """
    TYPE_PENALITE_CHOICES = [
        ('RETARD_PALIER', 'Pénalité de retard par palier'),
        ('RETARD_MANUEL', 'Pénalité manuelle'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    emprunt = models.ForeignKey(Emprunt, on_delete=models.CASCADE, related_name='penalites')
    type_penalite = models.CharField(
        max_length=20, 
        choices=TYPE_PENALITE_CHOICES, 
        default='RETARD_PALIER',
        verbose_name="Type de pénalité"
    )
    
    # Détails de calcul pour transparence
    palier = models.CharField(
        max_length=20, 
        verbose_name="Palier (ex: Palier-3, Palier-6)",
        help_text="Indique à quel palier cette pénalité a été appliquée"
    )
    sessions_ecoulees = models.IntegerField(
        verbose_name="Nombre de sessions écoulées",
        help_text="Nombre de sessions depuis l'octroi de l'emprunt"
    )
    
    # Montants de base pour le calcul
    montant_reste_avant = models.DecimalField(
        max_digits=12, decimal_places=2,
        verbose_name="Montant restant avant pénalité (FCFA)",
        help_text="Le montant qui restait à rembourser avant cette pénalité"
    )
    taux_applique = models.DecimalField(
        max_digits=5, decimal_places=2,
        verbose_name="Taux d'intérêt appliqué (%)",
        help_text="Le taux utilisé pour calculer la pénalité"
    )
    
    # Détail des montants
    montant_interet_taux = models.DecimalField(
        max_digits=12, decimal_places=2,
        verbose_name="Montant intérêt (reste × taux) (FCFA)",
        help_text="Montant calculé: reste_à_payer × taux_intérêt"
    )
    montant_penalite_fixe = models.DecimalField(
        max_digits=12, decimal_places=2,
        default=Decimal('15000'),
        verbose_name="Pénalité fixe (FCFA)",
        help_text="Montant fixe de pénalité (généralement 15 000 FCFA)"
    )
    montant_total_penalite = models.DecimalField(
        max_digits=12, decimal_places=2,
        verbose_name="Total pénalité (FCFA)",
        help_text="Somme: intérêt_taux + pénalité_fixe"
    )
    
    # Informations de traçabilité
    date_application = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Date d'application"
    )
    appliquee_par = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        verbose_name="Appliquée par",
        help_text="Utilisateur qui a déclenché cette pénalité (ou système automatique)"
    )
    session_application = models.ForeignKey(
        Session,
        on_delete=models.CASCADE,
        verbose_name="Session d'application",
        help_text="Session pendant laquelle cette pénalité a été appliquée"
    )
    
    # Justification et notes
    justification = models.TextField(
        blank=True,
        verbose_name="Justification",
        help_text="Explication détaillée de pourquoi cette pénalité a été appliquée"
    )
    notes_complementaires = models.TextField(
        blank=True,
        verbose_name="Notes complémentaires"
    )
    
    class Meta:
        verbose_name = "Pénalité d'emprunt"
        verbose_name_plural = "Pénalités d'emprunts"
        ordering = ['-date_application']
        indexes = [
            models.Index(fields=['emprunt', 'palier']),
            models.Index(fields=['date_application']),
            models.Index(fields=['type_penalite']),
        ]
        # Éviter les doublons de pénalité pour un même palier
        unique_together = ['emprunt', 'palier']
    
    def __str__(self):
        return f"{self.emprunt.membre.numero_membre} - {self.palier} - {self.montant_total_penalite:,.0f} FCFA"
    
    def save(self, *args, **kwargs):
        """Calcul automatique du montant total"""
        self.montant_total_penalite = self.montant_interet_taux + self.montant_penalite_fixe
        
        # Génération automatique de la justification si vide
        if not self.justification:
            self.justification = (
                f"Pénalité automatique {self.palier} appliquée après {self.sessions_ecoulees} sessions. "
                f"Calcul: {self.montant_reste_avant:,.0f} FCFA × {self.taux_applique}% = "
                f"{self.montant_interet_taux:,.0f} FCFA + {self.montant_penalite_fixe:,.0f} FCFA (fixe) = "
                f"{self.montant_total_penalite:,.0f} FCFA total."
            )
        
        super().save(*args, **kwargs)
    
    @property
    def formule_calcul(self):
        """Retourne la formule de calcul pour affichage"""
        return (
            f"{self.montant_reste_avant:,.0f} × {self.taux_applique}% + "
            f"{self.montant_penalite_fixe:,.0f} = {self.montant_total_penalite:,.0f} FCFA"
        )




