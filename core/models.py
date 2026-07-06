from django.db import models
from django.core.validators import MinValueValidator
from django.conf import settings
import uuid
from django.db.models import F 
from django.utils import timezone
from decimal import Decimal, ROUND_HALF_UP
from django.db.models import Sum, Q
from Backend.settings import MUTUELLE_DEFAULTS
from datetime import datetime, timedelta
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from django.db import models
import uuid
import re
from django.db import models, transaction
from django.core.exceptions import ValidationError

class DépenseExercice(models.Model):
    """
    ✅ NOUVEAU: Enregistre les dépenses du fonds social durant l'exercice
    
    Chaque dépense (assistance, collation) crée une entrée ici.
    À la fin de l'exercice, les renflouements sont créés selon ces dépenses.
    """
    TYPE_CHOICES = [
        ('ASSISTANCE', 'Assistance'),
        ('COLLATION', 'Collation'),
        ('AUTRE', 'Autre'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    exercice = models.ForeignKey('Exercice', on_delete=models.CASCADE, related_name='depenses', verbose_name="Exercice")
    type_depense = models.CharField(max_length=15, choices=TYPE_CHOICES, verbose_name="Type de dépense")
    montant = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)], verbose_name="Montant (FCFA)")
    description = models.TextField(verbose_name="Description")
    session = models.ForeignKey('Session', on_delete=models.SET_NULL, null=True, blank=True, related_name='depenses')
    beneficiaire = models.ForeignKey('Membre', on_delete=models.SET_NULL, null=True, blank=True, related_name='aides_reçues', verbose_name="Bénéficiaire (si applicable)")
    date_creation = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Dépense d'exercice"
        verbose_name_plural = "Dépenses d'exercice"
        ordering = ['-date_creation']
    
    def __str__(self):
        return f"{self.type_depense} - {self.montant:,.0f} FCFA ({self.exercice.nom})"

class ConfigurationMutuelle(models.Model):
    """
    Configuration globale de la mutuelle (paramètres modifiables)
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    montant_inscription = models.DecimalField(
        max_digits=12, decimal_places=2, default=MUTUELLE_DEFAULTS["INSCRIPTION_AMOUNT"],
        validators=[MinValueValidator(0)],
        verbose_name="Montant inscription (FCFA)"
    )
    montant_solidarite = models.DecimalField(
        max_digits=12, decimal_places=2, default=MUTUELLE_DEFAULTS["SOLIDARITE_AMOUNT"],
        validators=[MinValueValidator(0)],
        verbose_name="Montant solidarité par session (FCFA)"
    )
    taux_interet = models.DecimalField(
        max_digits=5, decimal_places=2, default=MUTUELLE_DEFAULTS["INTEREST_RATE"],
        validators=[MinValueValidator(0)],
        verbose_name="Taux d'intérêt (%)"
    )
    duree_exercice_mois = models.IntegerField(
        default=MUTUELLE_DEFAULTS["EXERCISE_DURATION_MONTHS"],
        validators=[MinValueValidator(1)],
        verbose_name="Durée exercice (mois)"
    )
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Configuration Mutuelle"
        verbose_name_plural = "Configurations Mutuelle"
    
    def __str__(self):
        return f"Configuration Mutuelle (Modifiée le {self.date_modification.date()})"
    
    @classmethod
    def get_configuration(cls):
        """Retourne la configuration actuelle ou en crée une par défaut"""
        config = cls.objects.first()
        if not config:
            config = cls.objects.create()
        return config
    
class Interet(models.Model):
    """
    Table stockant les gains générés par les intérêts des emprunts,
    redistribués au prorata de l'épargne des membres.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Bénéficiaire de la part d'intérêt
    membre = models.ForeignKey(
        'Membre', 
        on_delete=models.CASCADE, 
        related_name='gains_interets',
        verbose_name="Membre bénéficiaire"
    )
    
    # L'emprunt qui a généré cet intérêt
    emprunt_source = models.ForeignKey(
        'transactions.Emprunt',
        on_delete=models.CASCADE,
        related_name='redistributions',
        verbose_name="Emprunt source",
        null=True,
        blank=True
    )
    
    # Contexte temporel
    exercice = models.ForeignKey(
        'Exercice', 
        on_delete=models.CASCADE, 
        verbose_name="Exercice"
    )
    session = models.ForeignKey(
        'Session', 
        on_delete=models.CASCADE, 
        verbose_name="Session de distribution"
    )
    
    # Données financières
    montant = models.DecimalField(
        max_digits=12, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name="Montant perçu (FCFA)"
    )
    
    # Trçabilité
    date_distribution = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Intérêt redistribué"
        verbose_name_plural = "Intérêts redistribués"
        ordering = ['-date_distribution']

    def __str__(self):
        return f"Gain {self.montant:,.0f} FCFA - {self.membre.utilisateur.nom_complet} (Session {self.session.nom})"

class EmpruntCoefficientTier(models.Model):
    exercise = models.ForeignKey(
        'Exercice',
        on_delete=models.CASCADE,
        related_name='emprunt_tiers',
        verbose_name="Exercice"
    )
    min_amount = models.PositiveBigIntegerField(
        verbose_name="Montant minimum (FCFA)",
        validators=[MinValueValidator(0)]
    )
    max_amount = models.PositiveBigIntegerField(
        verbose_name="Montant maximum (FCFA)",
    )
    coefficient = models.DecimalField(
        verbose_name="Coefficient",
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    max_cap = models.PositiveBigIntegerField(
        verbose_name="Plafond absolu (optionnel)",
        null=True,
        blank=True,
        help_text="Ex: 2 000 000 FCFA – seulement pour la première tranche"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Tranche coefficient emprunt"
        verbose_name_plural = "Tranches coefficients emprunt"
        unique_together = ('exercise', 'min_amount')
        ordering = ['min_amount']

    def __str__(self):
        cap = f" (max {self.max_cap:,} FCFA)" if self.max_cap else ""
        return f"{self.min_amount:,} – {self.max_amount:,} × {self.coefficient}{cap}"

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.min_amount >= self.max_amount:
            raise ValidationError("min_amount doit être strictement inférieur à max_amount")




class SolidariteExerciceReport(models.Model):
    """
    Report de solidarité entre exercices.
    Créé automatiquement à la clôture d'un exercice (quand un nouvel exercice EN_COURS est créé).

    - montant_reporte > 0  → dette (le membre n'a pas tout payé sur l'exercice précédent)
    - montant_reporte < 0  → surplus (le membre a trop payé, il bénéficie d'un crédit)
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    membre = models.ForeignKey(
        'Membre', on_delete=models.CASCADE,
        related_name='reports_solidarite',
        verbose_name="Membre"
    )
    exercice_source = models.ForeignKey(
        'Exercice', on_delete=models.CASCADE,
        related_name='reports_solidarite_emis',
        verbose_name="Exercice source (clôturé)"
    )
    exercice_cible = models.ForeignKey(
        'Exercice', on_delete=models.CASCADE,
        related_name='reports_solidarite_recus',
        verbose_name="Exercice cible (nouveau)"
    )
    montant_reporte = models.DecimalField(
        max_digits=12, decimal_places=2,
        verbose_name="Montant reporté (FCFA)",
        help_text="Positif = dette à payer sur le prochain exercice. Négatif = surplus (crédit)."
    )
    date_creation = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Report de solidarité"
        verbose_name_plural = "Reports de solidarité"
        ordering = ['-date_creation']
        unique_together = [['membre', 'exercice_source']]

    def __str__(self):
        nature = "Dette" if self.montant_reporte > 0 else "Surplus"
        return (
            f"{nature} solidarité {self.membre.numero_membre} : "
            f"{abs(self.montant_reporte):,.0f} FCFA "
            f"({self.exercice_source.nom} → {self.exercice_cible.nom})"
        )


class Exercice(models.Model):
    """
    Exercice de la mutuelle (généralement 1 an)
    """
    STATUS_CHOICES = [
        ('EN_COURS', 'En cours'),
        ('TERMINE', 'Terminé'),
        ('PLANIFIE', 'Planifié'),
        ('EN_PREPARATION', 'En préparation'),  # ✅ Ajouté pour nouveaux exercices
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nom = models.CharField(max_length=100, verbose_name="Nom de l'exercice", blank=True, null=True)
    date_debut = models.DateField(verbose_name="Date de début")  # ✅ Retiré auto_now_add
    date_fin = models.DateField(verbose_name="Date de fin", blank=True, null=True)  # ✅ Peut être nulle
    statut = models.CharField(max_length=15, choices=STATUS_CHOICES, default='EN_COURS', verbose_name="Statut")  # ✅ Augmenté max_length
    description = models.TextField(blank=True, verbose_name="Description")
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Exercice"
        verbose_name_plural = "Exercices"
        ordering = ['-date_debut']
        # ✅ Retiré unique_together car date_fin peut être null
    
    def save(self, *args, **kwargs):
        """
        ✅ VERSION ATOMIQUE : Gestion automatique du cycle d'exercice
        
        Quand un nouvel exercice EN_COURS est créé:
        1. Marquer l'exercice EN_COURS précédent comme TERMINE
        2. Marquer la session EN_COURS comme TERMINEE
        3. Calculer automatiquement date_fin si nécessaire
        4. Créer un nouveau FondsSocial avec le même montant que le précédent
        5. Sauvegarder le nouvel exercice
        
        ⚠️ Si n'importe quelle étape échoue, TOUT est annulé (rollback)
        """
        old_statut = None
        is_new = self.pk is None
        
        # ✅ Générer le nom automatiquement si pas fourni
        if not self.nom:
            year = self.date_debut.year if self.date_debut else datetime.now().year
            self.nom = f"Exercice {year}"
        
        # ✅ Obtenir l'ancien statut SEULEMENT si l'instance existe déjà
        if not is_new:
            try:
                old_instance = Exercice.objects.get(pk=self.pk)
                old_statut = old_instance.statut
            except Exercice.DoesNotExist:
                is_new = True
                old_statut = None
        
        # ✅ Calculer date_fin automatiquement si pas fournie
        if self.date_debut and not self.date_fin:
            try:
                config = ConfigurationMutuelle.get_configuration()
                duree_mois = config.duree_exercice_mois
                self.date_fin = self.date_debut + relativedelta(months=duree_mois)
                print(f"✅ Date de fin calculée automatiquement: {self.date_fin} (durée: {duree_mois} mois)")
            except Exception as e:
                print(f"❌ Erreur calcul date_fin: {e}")
                self.date_fin = self.date_debut + relativedelta(months=12)
                print(f"🔄 Fallback: date_fin = {self.date_fin} (12 mois par défaut)")
        
        # 🔒 TRANSACTION ATOMIQUE : Tout réussit ou tout échoue
        previous_current_exercice = None
        with transaction.atomic():
            # ✅ SI C'EST UN NOUVEL EXERCICE AVEC STATUT EN_COURS
            if is_new and self.statut == 'EN_COURS':
                # 1️⃣ CRÉER LES RENFLOUEMENTS DE FIN D'EXERCICE AVANT DE TERMINER L'ANCIEN
                previous_current_exercice = Exercice.objects.filter(
                    statut='EN_COURS'
                ).first()
                exercice_precedent_deja_cloture = False

                if previous_current_exercice:
                    print(f"\n📊 CLÔTURE AUTOMATIQUE DE L'EXERCICE PRÉCÉDENT: {previous_current_exercice.nom}")
                    print(f"{'='*70}")

                    # ✅ APPELER LA CRÉATION DES RENFLOUEMENTS
                    try:
                        result = previous_current_exercice.creer_renflouements_fin_exercice()
                        print(f"✅ Renflouements créés avec succès:")
                        print(f"   - Total sorties: {result['total_sorties_global']:,.0f} FCFA")
                        print(f"   - Nombre de membres EN_REGLE: {result['nombre_membres_en_regle']}")
                        print(f"   - Montant par membre: {result['montant_par_membre']:,.0f} FCFA")
                        print(f"   - Renflouements créés: {result['renflouements_crees']}")
                    except Exception as e:
                        print(f"❌ ERREUR lors de la création des renflouements: {e}")
                        # On continue même si ça échoue (pour ne pas bloquer la création du nouvel exercice)

                    # ✅ APPELER LE REPORT DES SOLIDARITÉS (dette/surplus vers le nouvel exercice)
                    try:
                        result_reports = previous_current_exercice.creer_reports_solidarite(exercice_cible=self)
                        print(f"✅ Reports de solidarité créés: {result_reports['reports_crees']} rapport(s)")
                        print(f"   - Dettes reportées: {result_reports['dettes_reportees']:,.0f} FCFA")
                        print(f"   - Surplus reportés: {result_reports['surplus_reportes']:,.0f} FCFA")
                    except Exception as e:
                        print(f"❌ ERREUR lors de la création des reports de solidarité: {e}")
                        # On continue même si ça échoue

                    # 2️⃣ Marquer l'exercice EN_COURS précédent comme TERMINE
                    previous_current_exercice.statut = 'TERMINE'
                    previous_current_exercice.save(update_fields=['statut', 'date_modification'])
                    print(f"📝 Exercice précédent {previous_current_exercice.nom} marqué comme TERMINE")

                    # 3️⃣ Marquer la session EN_COURS comme TERMINEE
                    current_session = Session.objects.filter(statut='EN_COURS').first()
                    if current_session:
                        current_session.statut = 'TERMINEE'
                        current_session.save(update_fields=['statut', 'date_modification'])
                        print(f"📝 Session courante {current_session.nom} marquée comme TERMINEE")
                else:
                    # Exercice précédent clôturé manuellement (bouton « Terminer l'exercice »)
                    previous_closed = Exercice.objects.filter(
                        statut='TERMINE'
                    ).order_by('-date_modification').first()

                    if previous_closed:
                        previous_current_exercice = previous_closed
                        exercice_precedent_deja_cloture = True
                        print(f"\nℹ️ NOUVEL EXERCICE après clôture manuelle de: {previous_closed.nom}")
                        print(f"{'='*70}")
                        print("ℹ️ Renflouements déjà générés lors de la clôture — pas de régénération")

                        try:
                            result_reports = previous_current_exercice.creer_reports_solidarite(exercice_cible=self)
                            print(f"✅ Reports de solidarité créés: {result_reports['reports_crees']} rapport(s)")
                            print(f"   - Dettes reportées: {result_reports['dettes_reportees']:,.0f} FCFA")
                            print(f"   - Surplus reportés: {result_reports['surplus_reportes']:,.0f} FCFA")
                        except Exception as e:
                            print(f"❌ ERREUR lors de la création des reports de solidarité: {e}")
            
            # ✅ SAUVEGARDER L'EXERCICE
            super().save(*args, **kwargs)
            print(f"✅ Exercice {self.nom} sauvegardé avec statut {self.statut}")
            
            # ✅ TRANSITION D'EXERCICE: Conserver les statuts existants
            # Première exercice → tous EN_REGLE (ce sont les statuts par défaut)
            # Exercices suivants → conserve les statuts (EN_REGLE ou NON_EN_REGLE de l'exercice précédent)
            first_exercice = Exercice.objects.exclude(pk=self.pk).count() == 0
            if is_new and self.statut == 'EN_COURS' and first_exercice:
                # Premier exercice: initialiser tous les membres à EN_REGLE (statut par défaut)
                try:
                    nombre_membres_modifies = Membre.objects.all().update(statut='EN_REGLE')
                    print(f"✅ Premier exercice: Tous les {nombre_membres_modifies} membres remis à EN_REGLE")
                except Exception as e:
                    print(f"❌ ERREUR lors de l'initialisation des statuts: {e}")
                    raise ValidationError(
                        f"❌ IMPOSSIBLE D'INITIALISER LES STATUTS DES MEMBRES\n"
                        f"   {str(e)}"
                    )
            elif is_new and self.statut == 'EN_COURS' and not first_exercice:
                # Exercice suivant: conserver les statuts existants (EN_REGLE/NON_EN_REGLE)
                print(f"✅ Exercice suivant: Statuts des membres conservés (période de grâce sélective)")
            
            # ✅ SI C'EST UN NOUVEL EXERCICE EN_COURS: Dupliquer le FondsSocial
            if is_new and self.statut == 'EN_COURS':
                try:
                    # 3️⃣ Récupérer le FondsSocial de l'exercice précédent
                    ancien_fonds = None
                    if previous_current_exercice:
                        try:
                            ancien_fonds = FondsSocial.objects.get(exercice=previous_current_exercice)
                            montant_a_conserver = ancien_fonds.montant_total
                        except FondsSocial.DoesNotExist:
                            montant_a_conserver = Decimal('0')
                            print(f"⚠️ Aucun FondsSocial trouvé pour {previous_current_exercice.nom}")
                    else:
                        montant_a_conserver = Decimal('0')
                    
                    # 4️⃣ Créer un nouveau FondsSocial pour le nouvel exercice
                    nouveau_fonds, created = FondsSocial.objects.get_or_create(
                        exercice=self,
                        defaults={
                            'montant_total': montant_a_conserver
                        }
                    )
                    
                    if created:
                        print(f"✅ Nouveau FondsSocial créé pour {self.nom}")
                        print(f"   Montant conservé: {montant_a_conserver:,.0f} FCFA")
                        
                        # 5️⃣ Créer une ligne de mouvement pour tracer le transfert
                        if ancien_fonds and montant_a_conserver > 0:
                            MouvementFondsSocial.objects.create(
                                fonds_social=nouveau_fonds,
                                type_mouvement='ENTREE',
                                montant=montant_a_conserver,
                                description=f"Transfert FondsSocial de {previous_current_exercice.nom} à {self.nom}"
                            )
                            print(f"📝 Mouvement FondsSocial enregistré : Transfert de {montant_a_conserver:,.0f} FCFA")
                    else:
                        print(f"⚠️ FondsSocial existant pour {self.nom}")

                    # 6️⃣ Transférer la caisse inscription de l'exercice précédent
                    montant_caisse_conserver = Decimal('0')
                    if previous_current_exercice:
                        try:
                            ancienne_caisse = CaisseInscription.objects.get(exercice=previous_current_exercice)
                            montant_caisse_conserver = ancienne_caisse.montant_total
                        except CaisseInscription.DoesNotExist:
                            montant_caisse_conserver = Decimal('0')
                            print(f"⚠️ Aucune caisse inscription trouvée pour {previous_current_exercice.nom}")

                    nouvelle_caisse, caisse_created = CaisseInscription.objects.get_or_create(
                        exercice=self,
                        defaults={'montant_total': montant_caisse_conserver}
                    )

                    if caisse_created:
                        print(f"✅ Nouvelle caisse inscription créée pour {self.nom}")
                        print(f"   Montant conservé: {montant_caisse_conserver:,.0f} FCFA")
                        if montant_caisse_conserver > 0:
                            MouvementCaisseInscription.objects.create(
                                caisse_inscription=nouvelle_caisse,
                                type_mouvement='ENTREE',
                                montant=montant_caisse_conserver,
                                description=(
                                    f"Transfert caisse inscription de {previous_current_exercice.nom} "
                                    f"à {self.nom}"
                                )
                            )
                            print(f"📝 Mouvement caisse inscription enregistré : Transfert de {montant_caisse_conserver:,.0f} FCFA")
                    else:
                        print(f"⚠️ Caisse inscription existante pour {self.nom}, montant actuel {nouvelle_caisse.montant_total:,.0f} FCFA")
                        
                except Exception as e:
                    print(f"❌ ERREUR lors de la gestion FondsSocial / CaisseInscription: {e}")
                    raise ValidationError(
                        f"❌ IMPOSSIBLE DE CRÉER L'EXERCICE : Erreur FondsSocial\n"
                        f"   {str(e)}"
                    )
    
    def __str__(self):
        date_fin_str = self.date_fin.strftime("%Y-%m-%d") if self.date_fin else "Non définie"
        return f"{self.nom} ({self.date_debut} - {date_fin_str})"
    
    @property
    def is_en_cours(self):
        return self.statut == 'EN_COURS'
    
    @property
    def duree_totale_jours(self):
        """Retourne la durée totale en jours"""
        if self.date_debut and self.date_fin:
            return (self.date_fin - self.date_debut).days
        return None
    
    @property
    def duree_totale_mois(self):
        """Retourne la durée totale en mois (approximative)"""
        if self.date_debut and self.date_fin:
            return relativedelta(self.date_fin, self.date_debut).months + \
                   (relativedelta(self.date_fin, self.date_debut).years * 12)
        return None
    
    @property
    def progress_percentage(self):
        """Retourne le pourcentage de progression de l'exercice"""
        if not self.date_debut or not self.date_fin:
            return 0
        
        today = datetime.now().date()
        if today < self.date_debut:
            return 0
        elif today > self.date_fin:
            return 100
        else:
            total_days = (self.date_fin - self.date_debut).days
            elapsed_days = (today - self.date_debut).days
            return round((elapsed_days / total_days) * 100, 1) if total_days > 0 else 0
    
    @classmethod
    def get_exercice_en_cours(cls):
        """Retourne l'exercice en cours"""
        return cls.objects.filter(statut='EN_COURS').first()
    
    @classmethod
    def get_exercice_actuel(cls):
        """
        Retourne l'exercice correspondant à la date actuelle
        (même s'il n'est pas marqué comme EN_COURS)
        """
        today = datetime.now().date()
        return cls.objects.filter(
            date_debut__lte=today,
            date_fin__gte=today
        ).first()
    
    def activate(self):
        """
        Active cet exercice (désactive les autres)
        """
        if self.can_be_activated():
            # Désactiver tous les autres exercices
            Exercice.objects.filter(statut='EN_COURS').update(statut='TERMINE')
            # Activer celui-ci
            self.statut = 'EN_COURS'
            self.save()
            return True
        return False

    def creer_renflouements_fin_exercice(self):
        """
        ✅ NOUVELLE MÉTHODE: Crée les renflouements proportionnels à la fin de l'exercice
        
        Logique:
        1. Calculer les sorties de la caisse inscription et du fonds social
        2. Calculer les ratios de répartition
        3. Diviser le montant total entre les membres EN_REGLE
        4. Attribuer le même montant aux membres NON_EN_REGLE
        5. Créer les renflouements avec les ratios calculés
        
        Returns:
            dict: Résultats détaillés du calcul
        """
        from transactions.models import Renflouement, RepartitionRenflouementExercice
        
        result = {
            'total_sorties_caisse': Decimal('0'),
            'total_sorties_fonds': Decimal('0'),
            'total_sorties_global': Decimal('0'),
            'ratio_caisse': Decimal('0'),
            'ratio_fonds': Decimal('0'),
            'nombre_membres_en_regle': 0,
            'nombre_membres_non_en_regle': 0,
            'montant_par_membre': Decimal('0'),
            'renflouements_crees': 0,
            'repartition_id': None
        }
        
        print(f"\n📋 CRÉATION DES RENFLOUEMENTS PROPORTIONNELS FIN D'EXERCICE: {self.nom}")
        print(f"{'='*80}")
        
        try:
            with transaction.atomic():
                # 1. Calculer les sorties à partir des DépenseExercice
                # (DépenseExercice est défini localement dans ce fichier)

                
                # Les sorties incluent TOUTES les dépenses de l'exercice
                sorties_total = DépenseExercice.objects.filter(
                    exercice=self
                ).aggregate(total=Sum('montant'))['total'] or Decimal('0')
                
                # Répartition par type (optionnel, pour les ratios)
                sorties_caisse = DépenseExercice.objects.filter(
                    exercice=self,
                    type_depense__in=['COLLATION', 'AUTRE']
                ).aggregate(total=Sum('montant'))['total'] or Decimal('0')
                
                sorties_fonds = DépenseExercice.objects.filter(
                    exercice=self,
                    type_depense='ASSISTANCE'
                ).aggregate(total=Sum('montant'))['total'] or Decimal('0')
                
                result['total_sorties_caisse'] = sorties_caisse
                result['total_sorties_fonds'] = sorties_fonds
                
                print(f"💳 Sorties caisse inscription (collation+autre): {sorties_caisse:,.0f} FCFA")
                print(f"🏦 Sorties fonds social (assistance): {sorties_fonds:,.0f} FCFA")
                
                # 2. Calculer le total et les ratios
                total_sorties = sorties_total
                result['total_sorties_global'] = total_sorties
                
                if total_sorties == 0:
                    print("⚠️  Aucune dépense enregistrée pour cet exercice.")
                    return result
                
                print(f"💰 Total sorties (dépenses): {total_sorties:,.0f} FCFA")
                
                # Calcul des ratios
                ratio_caisse = ((sorties_caisse / total_sorties) * 100).quantize(
                    Decimal('0.01'), rounding=ROUND_HALF_UP
                ) if total_sorties > 0 else Decimal('0')
                ratio_fonds = (Decimal('100.00') - ratio_caisse) if total_sorties > 0 else Decimal('0')
                
                result['ratio_caisse'] = ratio_caisse
                result['ratio_fonds'] = ratio_fonds
                
                print(f"📊 Ratio caisse inscription: {ratio_caisse}%")
                print(f"📊 Ratio fonds social: {ratio_fonds}%")
                
                # 3. Compter les membres
                membres_en_regle = Membre.objects.filter(
                    statut='EN_REGLE', actif=True
                ).count()
                
                membres_non_en_regle = Membre.objects.filter(
                    statut='NON_EN_REGLE', actif=True
                ).count()
                
                membres_total = membres_en_regle + membres_non_en_regle
                
                result['nombre_membres_en_regle'] = membres_en_regle
                result['nombre_membres_non_en_regle'] = membres_non_en_regle
                
                print(f"👥 Membres en règle: {membres_en_regle}")
                print(f"👥 Membres non en règle: {membres_non_en_regle}")
                print(f"👥 Total membres actifs: {membres_total}")
                
                if membres_en_regle == 0:
                    print("⚠️  Aucun membre EN_REGLE pour calculer la répartition.")
                    return result
                
                # 5. Calculer le montant par membre (basé sur les membres en règle)
                montant_par_membre = (total_sorties / membres_en_regle).quantize(
                    Decimal('0.01'), rounding=ROUND_HALF_UP
                )
                
                result['montant_par_membre'] = montant_par_membre
                print(f"💵 Montant par membre: {montant_par_membre:,.0f} FCFA")
                print(f"📐 Formule: {total_sorties:,.0f} ÷ {membres_en_regle} membres en règle = {montant_par_membre:,.0f} FCFA")
                print(f"🎯 TOUS les {membres_total} membres actifs payeront ce montant")
                print(f"💰 Total à collecter: {membres_total} × {montant_par_membre:,.0f} = {membres_total * montant_par_membre:,.0f} FCFA")
                
                # 6. Créer l'enregistrement de répartition pour traçabilité
                repartition = RepartitionRenflouementExercice.objects.create(
                    exercice=self,
                    total_sorties_caisse_inscription=sorties_caisse,
                    total_sorties_fonds_social=sorties_fonds,
                    total_sorties_global=total_sorties,
                    ratio_caisse_inscription=ratio_caisse,
                    ratio_fonds_social=ratio_fonds,
                    nombre_membres_en_regle=membres_en_regle,
                    nombre_membres_non_en_regle=membres_non_en_regle,
                    nombre_membres_total=membres_total,
                    montant_par_membre=montant_par_membre,
                    notes_calcul=f"Calcul automatique fin d'exercice {self.nom}"
                )
                
                result['repartition_id'] = str(repartition.id)
                print(f"📋 Répartition enregistrée avec ID: {repartition.id}")
                
                # 7. Créer les renflouements pour TOUS LES MEMBRES (en règle ET non en règle)
                derniere_session = Session.objects.filter(
                    exercice=self
                ).order_by('-date_session').first()
                
                if not derniere_session:
                    print("⚠️  Aucune session trouvée pour cet exercice.")
                    return result
                
                # ✅ CORRECTION : TOUS les membres actifs doivent payer
                tous_les_membres = Membre.objects.filter(actif=True)
                
                print(f"\n🔄 Création des renflouements pour TOUS les membres...")
                print(f"📊 Logique : {total_sorties:,.0f} FCFA ÷ {membres_en_regle} membres en règle = {montant_par_membre:,.0f} FCFA")
                print(f"👥 TOUS les {tous_les_membres.count()} membres actifs payeront {montant_par_membre:,.0f} FCFA")
                
                for membre in tous_les_membres:
                    # Vérifier que le renflouement n'existe pas déjà
                    exists = Renflouement.objects.filter(
                        membre=membre,
                        exercice_renflouement=self,
                        type_cause='RENFLOUEMENT_FIN_EXERCICE'
                    ).exists()
                    
                    if not exists:
                        Renflouement.objects.create(
                            membre=membre,
                            session=derniere_session,
                            montant_du=montant_par_membre,
                            montant_paye=Decimal('0'),
                            type_cause='RENFLOUEMENT_FIN_EXERCICE',
                            exercice_renflouement=self,
                            ratio_caisse_inscription=ratio_caisse,
                            ratio_fonds_social=ratio_fonds,
                            cause=(
                                f"Renflouement proportionnel fin d'exercice {self.nom}. "
                                f"Répartition: {ratio_caisse}% caisse inscription, {ratio_fonds}% fonds social. "
                                f"Calcul: {total_sorties:,.0f} FCFA ÷ {membres_en_regle} membres en règle = {montant_par_membre:,.0f} FCFA par membre. "
                                f"TOUS les membres actifs payent ce montant."
                            )
                        )
                        result['renflouements_crees'] += 1
                        print(f"   ✅ Renflouement créé pour {membre.numero_membre} ({membre.statut})")
                    else:
                        print(f"   ⚠️  Renflouement déjà existant pour {membre.numero_membre}")
                
                print(f"\n✅ {result['renflouements_crees']} renflouement(s) proportionnel(s) créé(s)")
                print(f"💰 Total à collecter: {tous_les_membres.count()} membres × {montant_par_membre:,.0f} = {tous_les_membres.count() * montant_par_membre:,.0f} FCFA")
                print(f"📊 Répartition future des paiements:")
                print(f"   - {ratio_caisse}% → Caisse inscription")
                print(f"   - {ratio_fonds}% → Fonds social")
                print(f"{'='*80}\n")
                
        except Exception as e:
            print(f"❌ ERREUR lors de la création des renflouements proportionnels: {e}")
            import traceback
            print(traceback.format_exc())
            raise
        
        return result

    def creer_reports_solidarite(self, exercice_cible):
        """
        Calcule et reporte la dette ou le surplus de solidarité de chaque membre
        vers l'exercice suivant (exercice_cible).

        Logique:
        - Pour chaque membre actif de cet exercice (exercice source):
            - Récupérer le montant dû (config.montant_solidarite)
            - Récupérer le total réellement payé
            - Calculer la différence: payé - dû
                * Si diff < 0 → dette (le membre doit encore de l'argent)
                * Si diff > 0 → surplus (crédit pour le prochain exercice)
                * Si diff == 0 → tout est réglé, pas de report nécessaire
        - Créer un SolidariteExerciceReport par membre avec une balance non nulle

        Returns:
            dict: {'reports_crees': int, 'dettes_reportees': Decimal, 'surplus_reportes': Decimal}
        """
        from decimal import Decimal
        from django.db.models import Sum
        from transactions.models import PaiementSolidarite
        from core.models import ConfigurationMutuelle, SolidariteExerciceReport

        result = {
            'reports_crees': 0,
            'dettes_reportees': Decimal('0'),
            'surplus_reportes': Decimal('0'),
        }

        print(f"\n📊 CALCUL DES REPORTS DE SOLIDARITÉ: {self.nom} → {exercice_cible.nom}")
        print(f"{'='*70}")

        config = ConfigurationMutuelle.get_configuration()
        montant_du_exercice = config.montant_solidarite

        membres = Membre.objects.filter(actif=True)

        for membre in membres:
            # Récupérer l'éventuel report que ce membre avait au DEBUT de cet exercice (exercice source)
            # c'est-à-dire le report créé à la fin de l'exercice (N-1) vers cet exercice (N)
            report_precedent = SolidariteExerciceReport.objects.filter(
                membre=membre,
                exercice_cible=self
            ).first()
            
            # Montant reporté (+ = dette, - = surplus)
            montant_report_precedent = report_precedent.montant_reporte if report_precedent else Decimal('0')
            
            # Vrai montant total dû pour cet exercice = config de base + report précédent
            # On utilise max(..., 0) car un gros surplus pourrait rendre le montant dû négatif
            total_due_exercice = max(montant_du_exercice + montant_report_precedent, Decimal('0'))

            # Total payé par ce membre sur CET exercice (exercice source / clôturé)
            total_paye = PaiementSolidarite.objects.filter(
                membre=membre,
                session__exercice=self
            ).aggregate(total=Sum('montant'))['total'] or Decimal('0')

            # Différence: dû - payé
            # positif = dette (a payé moins que prévu), négatif = surplus (a payé plus)
            diff = total_due_exercice - total_paye

            if diff == Decimal('0'):
                # Tout est réglé exactement, pas de report
                continue

            # Vérifier si un report existe déjà pour ce membre/exercice_source
            existing = SolidariteExerciceReport.objects.filter(
                membre=membre,
                exercice_source=self
            ).exists()

            if existing:
                print(f"   ⚠️ Report déjà existant pour {membre.numero_membre}, ignoré")
                continue

            # Créer le report (diff > 0 = dette, diff < 0 = surplus)
            nature = "DETTE" if diff > 0 else "SURPLUS"
            SolidariteExerciceReport.objects.create(
                membre=membre,
                exercice_source=self,
                exercice_cible=exercice_cible,
                montant_reporte=diff,  # positif = dette, négatif = surplus
            )
            result['reports_crees'] += 1

            if diff < 0:
                result['surplus_reportes'] += abs(diff)
                print(f"   ✅ Surplus {membre.numero_membre}: {abs(diff):,.0f} FCFA (crédit)")
            else:
                result['dettes_reportees'] += diff
                print(f"   ⚠️  Dette {membre.numero_membre}: +{diff:,.0f} FCFA")

        print(f"\n✅ {result['reports_crees']} report(s) créé(s)")
        print(f"   Dettes totales: {result['dettes_reportees']:,.0f} FCFA")
        print(f"   Surplus totaux: {result['surplus_reportes']:,.0f} FCFA")
        print(f"{'='*70}\n")

        return result

    def clean(self):
        """
        Validation personnalisée
        """
        from django.core.exceptions import ValidationError
        
        # Vérifier que date_debut n'est pas dans le futur lointain
        if self.date_debut:
            max_future = datetime.now().date() + relativedelta(years=2)
            if self.date_debut > max_future:
                raise ValidationError({
                    'date_debut': 'La date de début ne peut pas être si éloignée dans le futur.'
                })
        
        # Vérifier cohérence des dates si date_fin est fournie
        if self.date_debut and self.date_fin:
            if self.date_fin <= self.date_debut:
                raise ValidationError({
                    'date_fin': 'La date de fin doit être postérieure à la date de début.'
                })
            
            # Vérifier durée raisonnable (entre 1 mois et 5 ans)
            duree_jours = (self.date_fin - self.date_debut).days
            if duree_jours < 30:  # Moins d'un mois
                raise ValidationError({
                    'date_fin': 'La durée de l\'exercice doit être d\'au moins 30 jours.'
                })
            elif duree_jours > 1825:  # Plus de 5 ans
                raise ValidationError({
                    'date_fin': 'La durée de l\'exercice ne peut pas dépasser 5 ans.'
                })

class Session(models.Model):
    """
    Session mensuelle dans un exercice
    """
    STATUS_CHOICES = [
        ('EN_COURS', 'En cours'),
        ('TERMINEE', 'Terminée'),
        ('PLANIFIEE', 'Planifiée'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    exercice = models.ForeignKey(Exercice, on_delete=models.CASCADE, related_name='sessions', verbose_name="Exercice")
    nom = models.CharField(max_length=100, verbose_name="Nom de la session", blank=True, null=True)
    date_session = models.DateField(verbose_name="Date de la session")
    montant_collation = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        validators=[MinValueValidator(0)],
        verbose_name="Montant collation (FCFA)"
    )
    # Nouvelle option : autres dépenses ponctuelles de la session
    montant_autre_depense = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        validators=[MinValueValidator(0)],
        verbose_name="Autre dépense (FCFA)"
    )
    motif_autre_depense = models.TextField(
        blank=True,
        verbose_name="Motif autre dépense"
    )
    statut = models.CharField(max_length=10, choices=STATUS_CHOICES, default='EN_COURS', verbose_name="Statut")
    description = models.TextField(blank=True, verbose_name="Description")
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Session"
        verbose_name_plural = "Sessions"
        ordering = ['-date_session']
        unique_together = [['exercice', 'date_session']]
        constraints = [
            models.UniqueConstraint(
                fields=['exercice'],
                condition=models.Q(statut='EN_COURS'),
                name='unique_session_en_cours_par_exercice'
            )
        ]
    
    def __str__(self):
        return f"{self.nom} - {self.date_session} ({self.exercice.nom})"
    
    @property
    def is_en_cours(self):
        return self.statut == 'EN_COURS'
    
    @classmethod
    def get_session_en_cours(cls):
        """Retourne la session en cours"""
        return cls.objects.filter(statut='EN_COURS').first()
    
    def clean(self):
        """
        Validation allégée pour permettre la transition automatique
        """
        from django.core.exceptions import ValidationError
        
        # On ne bloque plus la création si une session est EN_COURS, 
        # car le save() va s'en occuper. 
        # On vérifie juste qu'on n'essaie pas de modifier une session TERMINEE en EN_COURS manuellement
        if self.pk and self.statut == 'EN_COURS':
            was_terminée = Session.objects.filter(pk=self.pk, statut='TERMINEE').exists()
            if was_terminée:
                raise ValidationError("On ne peut pas réouvrir une session terminée.")


    def save(self, *args, **kwargs):
        from django.db import transaction
        from django.core.exceptions import ValidationError
        from .models import Exercice, FondsSocial
        
        # 1. Détection de l'état initial
        is_new = self.pk is None
        was_en_cours = False
        
        if not is_new:
            try:
                # On récupère la version en base de données avant la modif
                old_version = Session.objects.get(pk=self.pk)
                was_en_cours = (old_version.statut == 'EN_COURS')
            except Session.DoesNotExist:
                is_new = True

        print(f"DEBUG SAVE SESSION: is_new={is_new}, nom={self.nom}, statut={self.statut}")

        # 2. Gestion automatique du nom
        if not self.nom:
            if self.date_session:
                mois_fr = ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin", 
                          "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"]
                self.nom = f"Session {mois_fr[self.date_session.month - 1]} {self.date_session.year}"
            else:
                from django.utils import timezone
                self.nom = f"Session {timezone.now().strftime('%B %Y')}"

        # 3. Assignation de l'exercice par défaut
        if not self.exercice_id and not self.exercice:
            exercice_en_cours = Exercice.get_exercice_en_cours()
            if exercice_en_cours:
                self.exercice = exercice_en_cours
            else:
                from datetime import date
                self.exercice, _ = Exercice.objects.get_or_create(
                    statut='EN_COURS',
                    defaults={'nom': f'Exercice {date.today().year}', 'date_debut': date.today()}
                )

        # 4. Vérification préliminaire du Fonds Social
        is_first_session = (Session.objects.count() == 0) if is_new else False
        
        # On vérifie si on s'apprête à activer une session avec collation / autres dépenses
        if self.statut == 'EN_COURS' and not was_en_cours and not is_first_session:
            montant_total_retrait = (self.montant_collation or 0) + (self.montant_autre_depense or 0)
            if montant_total_retrait > 0:
                # Les dépenses de collations et autres sont payées depuis la caisse d'inscription
                from core.models import CaisseInscription
                caisse = CaisseInscription.get_caisse_actuelle()
                if not caisse or caisse.montant_total < montant_total_retrait:
                    dispo = caisse.montant_total if caisse else 0
                    raise ValidationError(
                        f"❌ Caisse d'inscription insuffisante. "
                        f"Requis: {montant_total_retrait:,.0f} FCFA, Dispo: {dispo:,.0f} FCFA"
                    )
                print(f"✅ Vérification caisse d'inscription OK : {caisse.montant_total:,.0f} FCFA")

        # 5. EXECUTION ATOMIQUE
        with transaction.atomic():
            # Identifier la session précédente EN_COURS pour la fermer
            previous = None
            if self.statut == 'EN_COURS' and not was_en_cours:
                previous = Session.objects.filter(
                    exercice=self.exercice, 
                    statut='EN_COURS'
                ).exclude(pk=self.pk).first()

            # --- SAUVEGARDE RÉELLE ---
            super().save(*args, **kwargs)

            # 6. Actions déclenchées uniquement lors du PASSAGE à 'EN_COURS'
            if self.statut == 'EN_COURS' and not was_en_cours:
                
                # A. Retrait de la collation + autres dépenses éventuelles
                if (self.montant_collation > 0 or self.montant_autre_depense > 0) and not is_first_session:
                    if hasattr(self, '_retirer_collation_fonds_social'):
                        if not self._retirer_collation_fonds_social():
                            raise ValidationError("❌ Échec du retrait de la collation / autres dépenses.")

                # B. Clôture de l'ancienne session
                if previous:
                    Session.objects.filter(pk=previous.pk).update(statut='TERMINEE')
                    print(f"✅ Session précédente {previous.nom} clôturée.")

                # C. CAPITALISATION DES INTÉRÊTS
                try:
                    print("🚀 DÉMARRAGE DU SCAN DES EMPRUNTS...")
                    from transactions.models import Emprunt
                    # On cible uniquement les emprunts qui ne sont pas remboursés
                    emprunts_actifs = Emprunt.objects.exclude(statut='REMBOURSE')
                    
                    count_penalites = 0
                    for emprunt in emprunts_actifs:
                        # La fonction renvoie True si une pénalité a été ajoutée
                        if emprunt.capitaliser_interets_retard():
                            count_penalites += 1
                    print(f"📊 FIN DU SCAN: {count_penalites} pénalités appliquées.")
                except Exception as e:
                    print(f"⚠️ Erreur mineure pendant le scan: {str(e)}")

        # 7. Mise à jour finale des membres (Hors transaction)
        if hasattr(self, 'mettre_a_jour_statuts_membres'):
            self.mettre_a_jour_statuts_membres()
    
        
    @classmethod
    def initialiser_statuts_nouvel_exercice(cls):
        """
        ✅ NOUVELLE MÉTHODE: Initialise tous les membres à EN_REGLE au début d'un exercice
        
        À appeler lors de la création d'un nouvel exercice pour remettre
        tous les membres en règle et démarrer la période de grâce de 3 mois.
        """
        from django.db import transaction
        
        membres = cls.objects.all()
        
        print(f"🔄 Initialisation des statuts pour nouvel exercice: {membres.count()} membres")
        
        with transaction.atomic():
            for membre in membres:
                if membre.statut != 'EN_REGLE':
                    membre.statut = 'EN_REGLE'
                    membre.save()
                    print(f"✅ {membre.numero_membre}: Statut initialisé → EN_REGLE")
        
        print(f"✅ Tous les membres sont maintenant EN_REGLE pour le nouvel exercice")
    
    def mettre_a_jour_statuts_membres(self):
        """
        Met à jour le statut (EN_REGLE / NON_EN_REGLE) de tous les membres
        si leur statut est désormais définissable.
        """
        from core.models import Membre
        from django.db import transaction

        membres = Membre.objects.all()

        print(f"🔄 Mise à jour des statuts pour {membres.count()} membres")

        with transaction.atomic():
            for membre in membres:
                # ✅ NOUVELLE LOGIQUE: Période de grâce de 3 mois par exercice
                peut_definir_statuts = Membre.peut_definir_statuts_membre(membre)
                
                if not peut_definir_statuts:
                    # Période de grâce ou transition: conserver le statut actuel du membre
                    # (On ne force plus EN_REGLE pour éviter d'effacer les dettes de l'exercice précédent)
                    print(f"⏳ {membre.numero_membre}: Statut maintenu durant transition/grâce ({membre.statut})")
                    continue
                
                # Après période de grâce: évaluation normale
                est_en_regle = membre.calculer_statut_en_regle()
                nouveau_statut = 'EN_REGLE' if est_en_regle else 'NON_EN_REGLE'

                if membre.statut != nouveau_statut:
                    print(
                        f"🔁 {membre.numero_membre} : "
                        f"{membre.statut} → {nouveau_statut}"
                    )
                    membre.statut = nouveau_statut
                    membre.save(update_fields=['statut'])
                else:
                    print(
                        f"✅ {membre.numero_membre} : "
                        f"statut inchangé ({membre.statut})"
                    )
        

    def _retirer_collation_fonds_social(self):
        """
        Retire le montant de la collation (et éventuellement une autre dépense)
        du fonds social.
        Enregistre aussi la dépense pour le renflouement de fin d'exercice
        
        Returns:
            bool: True si succès, False si échec
        """
        try:
            from core.models import CaisseInscription
            
            caisse = CaisseInscription.get_caisse_actuelle()
            if not caisse:
                print("❌ ERREUR : Aucune caisse d'inscription actuelle trouvée")
                return False
            
            print(f"💰 Caisse inscription avant retrait : {caisse.montant_total:,.0f} FCFA")
            
            # 1) Retrait collation
            if self.montant_collation > 0:
                if not caisse.retirer_montant(
                    self.montant_collation,
                    f"Collation Session {self.nom} - {self.date_session}"
                ):
                    print(f"❌ ERREUR : Échec du retrait de {self.montant_collation:,.0f} FCFA (collation)")
                    return False
                try:
                    DépenseExercice.objects.create(
                        exercice=self.exercice,
                        type_depense='COLLATION',
                        montant=self.montant_collation,
                        description=f"Collation Session {self.nom} - {self.date_session}",
                        session=self
                    )
                    print(f"   📋 Dépense collation enregistrée: {self.montant_collation:,.0f} FCFA")
                except Exception as e:
                    print(f"⚠️  Erreur lors de l'enregistrement de la dépense collation: {e}")

            # 2) Retrait autre dépense éventuelle
            if self.montant_autre_depense > 0:
                if not caisse.retirer_montant(
                    self.montant_autre_depense,
                    f"Autre dépense Session {self.nom} - {self.date_session} ({self.motif_autre_depense})"
                ):
                    print(f"❌ ERREUR : Échec du retrait de {self.montant_autre_depense:,.0f} FCFA (autre dépense)")
                    return False
                try:
                    DépenseExercice.objects.create(
                        exercice=self.exercice,
                        type_depense='AUTRE',
                        montant=self.montant_autre_depense,
                        description=(
                            f"Autre dépense Session {self.nom} - {self.date_session}: "
                            f"{self.motif_autre_depense}"
                        ),
                        session=self
                    )
                    print(f"   📋 Autre dépense enregistrée: {self.montant_autre_depense:,.0f} FCFA")
                except Exception as e:
                    print(f"⚠️  Erreur lors de l'enregistrement de l'autre dépense: {e}")
            
            print(f"💰 Caisse inscription après retrait : {caisse.montant_total:,.0f} FCFA")
            print(
                f"✅ Retraits session: "
                f"collation={self.montant_collation:,.0f} FCFA, "
                f"autre={self.montant_autre_depense:,.0f} FCFA"
            )
            return True
            
        except Exception as e:
            print(f"❌ ERREUR dans _retirer_collation_fonds_social: {e}")
            return False
    
    

class TypeAssistance(models.Model):
    """
    Types d'assistance disponibles (mariage, décès, etc.)
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nom = models.CharField(max_length=100, unique=True, verbose_name="Nom du type")
    montant = models.DecimalField(
        max_digits=12, decimal_places=2,
        validators=[MinValueValidator(0)],
        verbose_name="Montant (FCFA)"
    )
    description = models.TextField(blank=True, verbose_name="Description")
    actif = models.BooleanField(default=True, verbose_name="Actif")
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Type d'assistance"
        verbose_name_plural = "Types d'assistance"
        ordering = ['nom']
    
    def __str__(self):
        return f"{self.nom} - {self.montant:,.0f} FCFA"

class Membre(models.Model):
    """
    Modèle Membre lié à un Utilisateur
    """
    STATUS_CHOICES = [
        ('EN_REGLE', 'En règle'),
        ('NON_EN_REGLE', 'Non en règle'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    utilisateur = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='membre_profile')
    numero_membre = models.CharField(max_length=20, unique=True, verbose_name="Numéro de membre")
    date_inscription = models.DateField(verbose_name="Date d'inscription")
    statut = models.CharField(max_length=15, choices=STATUS_CHOICES, default='EN_REGLE', verbose_name="Statut")
    exercice_inscription = models.ForeignKey(Exercice, on_delete=models.CASCADE, related_name='nouveaux_membres', verbose_name="Exercice d'inscription")
    session_inscription = models.ForeignKey(Session, on_delete=models.CASCADE, related_name='nouveaux_membres', verbose_name="Session d'inscription")
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)
    #nouveau champ pour indiquer si l'inscription est terminee
    inscription_terminee = models.BooleanField(
        default=False,
        verbose_name="Inscription terminée",
        help_text="True si le membre a payé la totalité de son inscription"
    )
    # Champ solidarité : paiement unique à vie
    solidarite_terminee = models.BooleanField(
        default=False,
        verbose_name="Solidarité terminée",
        help_text="True si le membre a payé la totalité de sa solidarité (une fois dans sa vie)"
    )
    actif=models.BooleanField(
        default=True,
        verbose_name="Membre actif",
        help_text="False si le membre ne fait plus partie de la mutuelle"
    )
    
    actif = models.BooleanField(default=True, verbose_name="Actif")

    class Meta:
        verbose_name = "Membre"
        verbose_name_plural = "Membres"
        ordering = ['-date_inscription']
    
    def __str__(self):
        return f"{self.numero_membre} - {self.utilisateur.nom_complet}"
    
    @property
    def is_en_regle(self):
        return self.statut == 'EN_REGLE'

    @property
    def is_actif(self):
        return self.actif

    def calculer_epargne_pure(self):
   
        from transactions.models import EpargneTransaction
        from django.db.models import Sum
    
    # La méthode la plus robuste : faire la somme de TOUS les montants
    # Si le signe est bien géré en base (-97000 pour un retrait), Sum() fait tout le travail.
        total = EpargneTransaction.objects.filter(membre=self).aggregate(
             solde=Sum('montant')
        )['solde']
    
        return total or Decimal('0.00')

    def calculer_total_gains(self):
        """L'argent gagné via les intérêts (Nouvelle Table)"""
        return self.gains_interets.aggregate(total=Sum('montant'))['total'] or Decimal('0')

    @property
    def solde_total_global(self):
        """Ce que le membre voit sur son compte (Épargne + Gains)"""
        return self.calculer_epargne_pure() + self.calculer_total_gains()
    
    def get_donnees_completes(self):
        """Retourne toutes les données financières du membre"""
        from core.utils import calculer_donnees_membre_completes
        return calculer_donnees_membre_completes(self)
    
    def peut_emprunter(self, montant):
        """Vérifie si le membre peut emprunter un montant donné (nouvelle logique par tranches)"""
        from transactions.models import Emprunt, EpargneTransaction
        from django.db.models import Sum
        from decimal import Decimal

        if not self.is_actif:
            return False, "Ce membre ne fait plus partie de la mutuelle"

        # 1. Vérifier qu'il n'a pas d'emprunt en cours
        if Emprunt.objects.filter(membre=self, statut='EN_COURS').exists():
            return False, "Vous avez déjà un emprunt en cours"

        # 2. ✅ NOUVEAU : Vérifier la disponibilité des fonds dans le trésor
        TYPES_ENTREES_TRESOR = ['DEPOT', 'RETOUR_REMBOURSEMENT']
        
        total_entrees = EpargneTransaction.objects.filter(
            type_transaction__in=TYPES_ENTREES_TRESOR,
            montant__gt=0
        ).aggregate(total=Sum('montant'))['total'] or Decimal('0')
        
        total_sorties = EpargneTransaction.objects.filter(
            type_transaction='RETRAIT_PRET',
            montant__lt=0
        ).aggregate(total=Sum('montant'))['total'] or Decimal('0')
        
        tresor_disponible = total_entrees + total_sorties  # total_sorties est déjà négatif
        
        print(f"🏦 Vérification trésor pour {self.numero_membre}:")
        print(f"   - Entrées: {total_entrees:,.0f} FCFA")
        print(f"   - Sorties: {total_sorties:,.0f} FCFA")
        print(f"   - Disponible: {tresor_disponible:,.0f} FCFA")
        print(f"   - Demandé: {montant:,.0f} FCFA")
        
        if tresor_disponible < montant:
            return False, f"Fonds insuffisants dans le trésor. Disponible: {tresor_disponible:,.0f} FCFA, Demandé: {montant:,.0f} FCFA"

        # 3. Récupérer l'exercice en cours
        exercice = Exercice.get_exercice_en_cours()
        if not exercice:
            return False, "Aucun exercice en cours"

        # 4. Récupérer l'épargne totale du membre
        epargne_totale = self.calculer_epargne_pure()
        if epargne_totale <= 0:
            return False, "Épargne insuffisante"

        # 5. Trouver la tranche correspondante
        tier = exercice.emprunt_tiers.filter(
            min_amount__lte=epargne_totale,
            max_amount__gte=epargne_totale
        ).first()

        if not tier:
            return False, "Aucune règle de coefficient trouvée pour votre épargne"

        # 6. Calculer le montant max selon l'épargne
        montant_max = Decimal(epargne_totale) * tier.coefficient
        if tier.max_cap:
            montant_max = min(montant_max, tier.max_cap)

        if montant > montant_max:
            return False, f"Montant maximum empruntable selon votre épargne: {int(montant_max):,} FCFA"

        # 7. ✅ NOUVEAU : Vérifier que le montant demandé ne dépasse pas les fonds disponibles
        montant_final = min(montant_max, tresor_disponible)
        
        if montant > montant_final:
            return False, f"Montant maximum empruntable (limité par le trésor): {int(montant_final):,} FCFA"

        return True, f"Emprunt autorisé (max épargne: {int(montant_max):,} FCFA, max trésor: {int(tresor_disponible):,} FCFA)"


    
    def calculer_statut_en_regle(self):
        """Calcule si le membre est en règle selon tous les critères"""
        donnees = self.get_donnees_completes()
        return donnees['membre_info']['en_regle']
    
    def save(self, *args, **kwargs):
        if not self.numero_membre:
            # Génération atomique et robuste du numéro de membre
            with transaction.atomic():
                # Verrouille la dernière ligne créée pour réduire les risques de course
                last_member = Membre.objects.select_for_update().order_by('-date_creation').first()
                if last_member and getattr(last_member, 'numero_membre', None):
                    m = re.search(r"(\d+)$", str(last_member.numero_membre))
                    if m:
                        try:
                            start = int(m.group(1)) + 1
                        except Exception:
                            start = 1
                    else:
                        start = 1
                else:
                    start = 1

                # Boucle jusqu'à trouver un numéro non utilisé (protégée par la transaction)
                while True:
                    candidate = f"ENS-{start:04d}"
                    if not Membre.objects.filter(numero_membre=candidate).exists():
                        self.numero_membre = candidate
                        break
                    start += 1
        super().save(*args, **kwargs)
    
    @classmethod
    def peut_definir_statuts_membre(cls, membre):
        """
        ✅ NOUVELLE LOGIQUE: Période de grâce SÉLECTIVE par statut d'exercice précédent

        Règles:
        - Membres EN_REGLE de l'exercice précédent → bénéficient d'une période de grâce de 3 sessions
        - Membres NON_EN_REGLE de l'exercice précédent → PAS de période de grâce, réévaluation immédiate
        - Après 3 sessions: évaluation selon les critères normaux pour tous
        """
        from core.models import Exercice, Session
        from django.utils import timezone

        # Récupérer l'exercice en cours
        exercice_actuel = Exercice.get_exercice_en_cours()
        if not exercice_actuel:
            print(f"⏳ Membre {membre.numero_membre}: Pas d'exercice EN_COURS")
            return False

        # ✅ SI MEMBRE NON_EN_REGLE: PAS DE PÉRIODE DE GRÂCE
        if membre.statut == 'NON_EN_REGLE':
            print(f"❌ Membre {membre.numero_membre}: NON_EN_REGLE, pas de période de grâce → réévaluation immédiate")
            return True

        # ✅ SI MEMBRE EN_REGLE: APPLIQUER PÉRIODE DE GRÂCE
        if membre.statut == 'EN_REGLE':
            # Compter le nombre de sessions terminées dans cet exercice
            sessions_terminees = Session.objects.filter(
                exercice=exercice_actuel,
                statut='TERMINEE'
            ).count()

            # Période de grâce = 3 sessions
            PERIODE_GRACE_SESSIONS = 3

            if sessions_terminees < PERIODE_GRACE_SESSIONS:
                # Encore dans la période de grâce
                sessions_restantes = PERIODE_GRACE_SESSIONS - sessions_terminees
                print(f"⏳ Membre {membre.numero_membre}: EN_REGLE, période de grâce ({sessions_restantes} session(s) restante(s) sur {PERIODE_GRACE_SESSIONS})")
                return False
            else:
                # Période de grâce terminée, on peut évaluer
                print(f"✅ Membre {membre.numero_membre}: EN_REGLE, période de grâce terminée ({sessions_terminees} sessions), évaluation possible")
                return True

        # Fallback (ne devrait pas arriver ici)
        print(f"⚠️  Membre {membre.numero_membre}: Statut inconnu '{membre.statut}'")
        return True





    def update_inscription_terminee(self):
        """
        NOUVELLE MÉTHODE <-
        Met à jour automatiquement le statut inscription_terminee
        """
        from transactions.models import PaiementInscription
        from decimal import Decimal
        
        # Récupérer le premier paiement pour avoir le montant initial
        premier_paiement = PaiementInscription.objects.filter(
            membre=self
        ).order_by('date_paiement').first()
        
        if not premier_paiement:
            self.inscription_terminee = False
            return False
        
        # Montant total dû (depuis le premier paiement)
        montant_total_du = premier_paiement.montant_inscription_du
        
        # Montant total payé
        total_paye = PaiementInscription.objects.filter(
            membre=self
        ).aggregate(total=Sum('montant'))['total'] or Decimal('0')
        
        # Vérifier si inscription terminée
        ancien_statut = self.inscription_terminee
        self.inscription_terminee = (total_paye >= montant_total_du)
        
        if ancien_statut != self.inscription_terminee:
            print(f"🎓 Inscription {self.numero_membre}: {ancien_statut} → {self.inscription_terminee}")
        
        return self.inscription_terminee

    def update_solidarite_terminee(self):
        """
        Met à jour automatiquement solidarite_terminee.
        La solidarité est un paiement unique à vie :
        - cumul de TOUS les paiements de solidarité du membre (toutes sessions confondues).
        - si le cumul >= montant_solidarite config actuel, solidarite_terminee = True.
        """
        from transactions.models import PaiementSolidarite
        from core.models import ConfigurationMutuelle
        from decimal import Decimal

        config = ConfigurationMutuelle.get_configuration()
        montant_total_du = config.montant_solidarite

        total_paye = PaiementSolidarite.objects.filter(
            membre=self
        ).aggregate(total=Sum('montant'))['total'] or Decimal('0')

        ancien_statut = self.solidarite_terminee
        self.solidarite_terminee = (total_paye >= montant_total_du)

        if ancien_statut != self.solidarite_terminee:
            print(f"🤝 Solidarité {self.numero_membre}: {ancien_statut} → {self.solidarite_terminee}")

        return self.solidarite_terminee

class FondsSocial(models.Model):
    """
    Suivi du fonds social total de la mutuelle
    Le fonds social est alimenté par les solidarités et les renflouements
    Il est diminué par les assistances et les collations
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    exercice = models.OneToOneField(Exercice, on_delete=models.CASCADE, related_name='fonds_social')
    montant_total = models.DecimalField(
        max_digits=15, decimal_places=2, default=0,
        verbose_name="Montant total du fonds social (FCFA)"
    )
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Fonds Social"
        verbose_name_plural = "Fonds Sociaux"
    
    def __str__(self):
        return f"Fonds Social {self.exercice.nom} - {self.montant_total:,.0f} FCFA"
    
    @classmethod
    def get_fonds_actuel(cls):
        """Retourne le fonds social de l'exercice en cours"""
        exercice_actuel = Exercice.get_exercice_en_cours()
        if exercice_actuel:
            fonds, created = cls.objects.get_or_create(exercice=exercice_actuel)
            return fonds
        return None
    
    def ajouter_montant(self, montant, description=""):
        """Ajoute un montant au fonds social de manière atomique et crée le mouvement."""
        
        if montant <= 0:
            return

        # 1. MISE À JOUR ATOMIQUE DU SOLDE
        # Nous utilisons update() avec F() pour garantir la sécurité
        FondsSocial.objects.filter(pk=self.pk).update(
            montant_total=F('montant_total') + montant,
            date_modification=timezone.now() # Optionnel, mais bon pour la traçabilité
        )
        
        # Recharger l'instance pour obtenir le nouveau montant total (si besoin pour un log immédiat)
        self.refresh_from_db() 
        
        # 2. Log de l'opération (Création du Mouvement)
        MouvementFondsSocial.objects.create(
            fonds_social=self,
            type_mouvement='ENTREE',
            montant=montant,
            description=description
        )
        
        print(f"Fonds Social (via F()): +{montant:,.0f} FCFA - {description}")
    
    def retirer_montant(self, montant, description=""):
        """Retire un montant du fonds social"""
        if self.montant_total >= montant:
            self.montant_total -= montant
            self.save()
            
            # Log de l'opération
            MouvementFondsSocial.objects.create(
                fonds_social=self,
                type_mouvement='SORTIE',
                montant=montant,
                description=description
            )
            print(f"Fonds Social: -{montant:,.0f} FCFA - {description}")
            return True
        else:
            print(f"ERREUR: Fonds insuffisant. Disponible: {self.montant_total:,.0f}, Demandé: {montant:,.0f}")
            return False

class MouvementFondsSocial(models.Model):
    """
    Historique des mouvements du fonds social
    """
    TYPE_CHOICES = [
        ('ENTREE', 'Entrée'),
        ('SORTIE', 'Sortie'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    fonds_social = models.ForeignKey(FondsSocial, on_delete=models.CASCADE, related_name='mouvements')
    type_mouvement = models.CharField(max_length=10, choices=TYPE_CHOICES)
    montant = models.DecimalField(max_digits=12, decimal_places=2)
    description = models.TextField()
    date_mouvement = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Mouvement Fonds Social"
        verbose_name_plural = "Mouvements Fonds Social"
        ordering = ['-date_mouvement']
    
    def __str__(self):
        signe = "+" if self.type_mouvement == 'ENTREE' else "-"
        return f"{signe}{self.montant:,.0f} FCFA - {self.description[:50]}"


class CaisseInscription(models.Model):
    """
    Caisse dédiée aux paiements d'inscription.
    Les inscriptions n'alimentent plus le fonds social mais cette caisse.
    Une caisse par exercice (comme le FondsSocial).
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    exercice = models.OneToOneField(
        Exercice, on_delete=models.CASCADE, related_name='caisse_inscription'
    )
    montant_total = models.DecimalField(
        max_digits=15, decimal_places=2, default=0,
        verbose_name="Montant total de la caisse inscription (FCFA)"
    )
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Caisse inscription"
        verbose_name_plural = "Caisses inscription"

    def __str__(self):
        return f"Caisse inscription {self.exercice.nom} - {self.montant_total:,.0f} FCFA"

    @classmethod
    def get_caisse_actuelle(cls):
        """Retourne la caisse inscription de l'exercice en cours."""
        exercice_actuel = Exercice.get_exercice_en_cours()
        if exercice_actuel:
            caisse, created = cls.objects.get_or_create(
                exercice=exercice_actuel,
                defaults={'montant_total': Decimal('0')}
            )
            return caisse
        return None

    def ajouter_montant(self, montant, description=""):
        """Ajoute un montant à la caisse inscription de manière atomique et crée le mouvement."""
        if montant <= 0:
            return
        CaisseInscription.objects.filter(pk=self.pk).update(
            montant_total=F('montant_total') + montant,
            date_modification=timezone.now()
        )
        self.refresh_from_db()
        MouvementCaisseInscription.objects.create(
            caisse_inscription=self,
            type_mouvement='ENTREE',
            montant=montant,
            description=description
        )
        print(f"Caisse inscription (via F()): +{montant:,.0f} FCFA - {description}")

    def retirer_montant(self, montant, description=""):
        """Retire un montant de la caisse inscription."""
        if montant <= 0:
            return True

        if self.montant_total >= montant:
            CaisseInscription.objects.filter(pk=self.pk).update(
                montant_total=F('montant_total') - montant,
                date_modification=timezone.now()
            )
            self.refresh_from_db()
            MouvementCaisseInscription.objects.create(
                caisse_inscription=self,
                type_mouvement='SORTIE',
                montant=montant,
                description=description
            )
            print(f"Caisse inscription: -{montant:,.0f} FCFA - {description}")
            return True
        else:
            print(
                f"ERREUR: Caisse inscription insuffisante. Disponible: {self.montant_total:,.0f}, Demandé: {montant:,.0f}"
            )
            return False


class MouvementCaisseInscription(models.Model):
    """Historique des mouvements de la caisse inscription."""
    TYPE_CHOICES = [
        ('ENTREE', 'Entrée'),
        ('SORTIE', 'Sortie'),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    caisse_inscription = models.ForeignKey(
        CaisseInscription, on_delete=models.CASCADE, related_name='mouvements'
    )
    type_mouvement = models.CharField(max_length=10, choices=TYPE_CHOICES)
    montant = models.DecimalField(max_digits=12, decimal_places=2)
    description = models.TextField()
    date_mouvement = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Mouvement caisse inscription"
        verbose_name_plural = "Mouvements caisse inscription"
        ordering = ['-date_mouvement']

    def __str__(self):
        signe = "+" if self.type_mouvement == 'ENTREE' else "-"
        return f"{signe}{self.montant:,.0f} FCFA - {self.description[:50]}"

