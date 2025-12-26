from django.db import models
from django.core.validators import MinValueValidator
from django.conf import settings
import uuid
from decimal import Decimal, ROUND_HALF_UP
from django.db.models import Sum, Q
from Backend.settings import MUTUELLE_DEFAULTS
from datetime import datetime, timedelta
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from django.db import models
import uuid
from django.db import models, transaction
from django.core.exceptions import ValidationError

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
    coefficient_emprunt_max = models.IntegerField(
        default=MUTUELLE_DEFAULTS["LOAN_MULTIPLIER"],
        validators=[MinValueValidator(1)],
        verbose_name="Coefficient multiplicateur max pour emprunts"
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
        Calcule automatiquement la date_fin si elle n'est pas fournie
        """
        # ✅ Générer le nom automatiquement si pas fourni
        if not self.nom:
            year = self.date_debut.year if self.date_debut else datetime.now().year
            self.nom = f"Exercice {year}"
        
        # ✅ Calculer date_fin automatiquement si pas fournie
        if self.date_debut and not self.date_fin:
            try:
                # Récupérer la configuration actuelle
                config = ConfigurationMutuelle.get_configuration()
                duree_mois = config.duree_exercice_mois
                
                # Calculer date de fin en ajoutant la durée en mois
                self.date_fin = self.date_debut + relativedelta(months=duree_mois)
                
                print(f"✅ Date de fin calculée automatiquement: {self.date_fin} (durée: {duree_mois} mois)")
                
            except Exception as e:
                print(f"❌ Erreur calcul date_fin: {e}")
                # Fallback: ajouter 12 mois par défaut
                self.date_fin = self.date_debut + relativedelta(months=12)
                print(f"🔄 Fallback: date_fin = {self.date_fin} (12 mois par défaut)")
        
        super().save(*args, **kwargs)
    
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
    
    def save(self, *args, **kwargs):
        """
        ✅ VERSION ATOMIQUE : Tout réussit ou rien n'est enregistré
        
        Ordre des opérations :
        1. Générer le nom si nécessaire
        2. Assigner l'exercice si nécessaire
        3. Marquer l'ancienne session comme TERMINEE si nécessaire
        4. VÉRIFIER le fonds social AVANT de sauvegarder (si collation > 0)
        5. Sauvegarder la session
        6. Créer les renflouements
        7. Retirer l'argent du fonds social
        
        ⚠️ Si n'importe quelle étape échoue, TOUT est annulé (rollback)
        """
        old_statut = None
        is_new = self.pk is None
        
        # ✅ Générer nom automatiquement si pas fourni
        if not self.nom:
            if self.date_session:
                mois_fr = [
                    "Janvier", "Février", "Mars", "Avril", "Mai", "Juin",
                    "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"
                ]
                mois = mois_fr[self.date_session.month - 1]
                self.nom = f"Session {mois} {self.date_session.year}"
            else:
                from django.utils import timezone
                now = timezone.now()
                self.nom = f"Session {now.strftime('%B %Y')}"
        
        # ✅ Obtenir l'ancien statut SEULEMENT si l'instance existe déjà
        if not is_new:
            try:
                old_instance = Session.objects.get(pk=self.pk)
                old_statut = old_instance.statut
            except Session.DoesNotExist:
                is_new = True
                old_statut = None
        
        # ✅ Assigner l'exercice en cours si pas spécifié
        if not self.exercice_id and not self.exercice:
            exercice_en_cours = Exercice.get_exercice_en_cours()
            if exercice_en_cours:
                self.exercice = exercice_en_cours
            else:
                from datetime import date
                exercice, created = Exercice.objects.get_or_create(
                    statut='EN_COURS',
                    defaults={
                        'nom': f'Exercice {date.today().year}',
                        'date_debut': date.today(),
                        'statut': 'EN_COURS'
                    }
                )
                self.exercice = exercice
        
        # ✅ VÉRIFIER SI C'EST LA PREMIÈRE SESSION (table vide)
        is_first_session = Session.objects.count() == 0
        
        if is_first_session:
            print(f"⚠️ PREMIÈRE SESSION DE LA TABLE : Pas de traitement de collation")
        
        # ✅ VÉRIFIER LE FONDS SOCIAL AVANT DE COMMENCER LA TRANSACTION
        # Si la collation est > 0 ET ce n'est pas la première session, on vérifie AVANT de créer quoi que ce soit
        if is_new and self.statut == 'EN_COURS' and self.montant_collation > 0 and not is_first_session:
            from core.models import FondsSocial
            
            fonds = FondsSocial.get_fonds_actuel()
            if not fonds:
                raise ValidationError(
                    "❌ IMPOSSIBLE DE CRÉER LA SESSION : Aucun fonds social actuel trouvé"
                )
            
            if fonds.montant_total < self.montant_collation:
                raise ValidationError(
                    f"❌ IMPOSSIBLE DE CRÉER LA SESSION : Fonds social insuffisant.\n"
                    f"   Disponible : {fonds.montant_total:,.0f} FCFA\n"
                    f"   Nécessaire : {self.montant_collation:,.0f} FCFA\n"
                    f"   Manque : {self.montant_collation - fonds.montant_total:,.0f} FCFA"
                )
            
            print(f"✅ Vérification fonds social OK : {fonds.montant_total:,.0f} FCFA disponible")
        
        # 🔒 TRANSACTION ATOMIQUE : Tout réussit ou tout échoue
        with transaction.atomic():
            # ✅ Marquer l'ancienne session EN_COURS comme TERMINEE
            if is_new and self.statut == 'EN_COURS':
                previous_current_session = Session.objects.filter(
                    exercice=self.exercice,
                    statut='EN_COURS'
                ).exclude(pk=self.pk).first()
                
                if previous_current_session:
                    previous_current_session.statut = 'TERMINEE'
                    previous_current_session.save(update_fields=['statut'])
                    print(f"📝 Session précédente {previous_current_session.nom} marquée comme TERMINEE")
            
            # ✅ SAUVEGARDER LA SESSION
            super().save(*args, **kwargs)
            print(f"✅ Session {self.nom} sauvegardée en base")
            
            # ✅ TRAITER LA COLLATION (si nécessaire ET ce n'est pas la première session)
            if is_new and self.statut == 'EN_COURS' and self.montant_collation > 0 and not is_first_session:
                print(f"🎯 Traitement collation : {self.montant_collation:,.0f} FCFA")
                
                # 1. Créer les renflouements D'ABORD
                if not self._creer_renflouement_collation():
                    raise ValidationError(
                        "❌ ÉCHEC : Impossible de créer les renflouements de collation"
                    )
                
                # 2. Retirer du fonds social ENSUITE
                if not self._retirer_collation_fonds_social():
                    raise ValidationError(
                        "❌ ÉCHEC : Impossible de retirer la collation du fonds social"
                    )
                
                print(f"✅ Collation traitée avec succès : {self.montant_collation:,.0f} FCFA")
                
        self.mettre_a_jour_statuts_membres()

    def mettre_a_jour_statuts_membres(self):
        """
        Met à jour le statut (EN_REGLE / NON_EN_REGLE) de tous les membres
        si leur statut est désormais définissable.
        """
        from core.models import Membre
        from django.db import transaction

        membres = Membre.objects.exclude(statut='SUSPENDU')

        print(f"🔄 Mise à jour des statuts pour {membres.count()} membres")

        with transaction.atomic():
            for membre in membres:
                peut_definir_statuts = Membre.peut_definir_statuts_membre(membre)

                if not peut_definir_statuts:
                    # ⏳ On ne touche pas au statut
                    print(
                        f"⏳ {membre.numero_membre} : "
                        f"statut non définissable → {membre.statut}"
                    )
                    continue

                est_en_regle = membre.calculer_statut_en_regle()

                nouveau_statut = 'EN_REGLE' if est_en_regle == 'EN_REGLE' else 'NON_EN_REGLE'

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
        

    
    def _creer_renflouement_collation(self):
        """
        Crée les renflouements pour la collation
        
        pour l'instant on va considerer que tout le monde participe au renflouement

        Returns:
            bool: True si succès, False si échec
        """
        try:
            from core.models import Membre
            from transactions.models import Renflouement
            
            membres_en_regle = Membre.objects.filter(
                date_inscription__lte=self.date_session
            )
            
            nombre_membres = membres_en_regle.count()
            if nombre_membres == 0:
                print("⚠️ ATTENTION : Aucun membre pour le renflouement de collation")
                return False
            
            montant_par_membre = (Decimal(str(self.montant_collation)) / nombre_membres).quantize(
                Decimal('0.01'), rounding=ROUND_HALF_UP
            )
            
            print(f"👥 {nombre_membres} membres en règle → {montant_par_membre:,.0f} FCFA chacun")
            
            renflouements_crees = 0
            for membre in membres_en_regle:
                try:
                    renflouement, created = Renflouement.objects.get_or_create(
                        membre=membre,
                        session=self,
                        type_cause='COLLATION',
                        defaults={
                            'montant_du': montant_par_membre,
                            'cause': f"Collation Session {self.nom} - {self.date_session}",
                        }
                    )
                    if created:
                        renflouements_crees += 1
                        print(f"   ✅ Renflouement créé pour {membre.numero_membre}")
                    else:
                        print(f"   ⚠️ Renflouement déjà existant pour {membre.numero_membre}")
                        
                except Exception as e:
                    print(f"   ❌ Erreur création renflouement pour {membre.numero_membre}: {e}")
                    raise  # ✅ RELANCER pour faire échouer la transaction
            
            if renflouements_crees == 0 and nombre_membres > 0:
                print("⚠️ Aucun nouveau renflouement créé (peut-être déjà existants)")
            else:
                print(f"✅ {renflouements_crees} renflouements créés avec succès")
            
            return True
            
        except Exception as e:
            print(f"❌ ERREUR dans _creer_renflouement_collation: {e}")
            return False
    
    def _retirer_collation_fonds_social(self):
        """
        Retire le montant de la collation du fonds social
        
        Returns:
            bool: True si succès, False si échec
        """
        try:
            from core.models import FondsSocial
            
            fonds = FondsSocial.get_fonds_actuel()
            if not fonds:
                print("❌ ERREUR : Aucun fonds social actuel trouvé")
                return False
            
            print(f"💰 Fonds social avant retrait : {fonds.montant_total:,.0f} FCFA")
            
            # Retirer le montant
            if not fonds.retirer_montant(
                self.montant_collation,
                f"Collation Session {self.nom} - {self.date_session}"
            ):
                print(f"❌ ERREUR : Échec du retrait de {self.montant_collation:,.0f} FCFA")
                return False
            
            print(f"💰 Fonds social après retrait : {fonds.montant_total:,.0f} FCFA")
            print(f"✅ {self.montant_collation:,.0f} FCFA retirés du fonds social")
            return True
            
        except Exception as e:
            print(f"❌ ERREUR dans _retirer_collation_fonds_social: {e}")
            return False
    
    def clean(self):
        """Validation personnalisée"""
        from django.core.exceptions import ValidationError
        
        # Vérifier qu'il n'y a pas déjà une session EN_COURS pour cet exercice
        if self.statut == 'EN_COURS' and self.exercice:
            existing = Session.objects.filter(
                exercice=self.exercice,
                statut='EN_COURS'
            ).exclude(pk=self.pk).first()
            
            if existing:
                raise ValidationError({
                    'statut': f'Il y a déjà une session en cours pour cet exercice: {existing.nom}'
                })

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
        ('SUSPENDU', 'Suspendu'),
        ('NON_DEFINI', 'Non defini'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    utilisateur = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='membre_profile')
    numero_membre = models.CharField(max_length=20, unique=True, verbose_name="Numéro de membre")
    date_inscription = models.DateField(verbose_name="Date d'inscription")
    statut = models.CharField(max_length=15, choices=STATUS_CHOICES, default='NON_DEFINI', verbose_name="Statut")
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

    class Meta:
        verbose_name = "Membre"
        verbose_name_plural = "Membres"
        ordering = ['-date_inscription']
    
    def __str__(self):
        return f"{self.numero_membre} - {self.utilisateur.nom_complet}"
    
    @property
    def is_en_regle(self):
        return self.statut == 'EN_REGLE'
    

    def calculer_epargne_totale(self):
        """Calcule l'épargne totale du membre"""
        from transactions.models import EpargneTransaction
        
        transactions = EpargneTransaction.objects.filter(membre=self)
        
        depots = transactions.filter(type_transaction='DEPOT').aggregate(
            total=Sum('montant'))['total'] or Decimal('0')
        
        retraits = transactions.filter(type_transaction='RETRAIT_PRET').aggregate(
            total=Sum('montant'))['total'] or Decimal('0')
        
        interets = transactions.filter(type_transaction='AJOUT_INTERET').aggregate(
            total=Sum('montant'))['total'] or Decimal('0')
        
        retours = transactions.filter(type_transaction='RETOUR_REMBOURSEMENT').aggregate(
            total=Sum('montant'))['total'] or Decimal('0')
        
        return depots - retraits + interets + retours
    
    def get_donnees_completes(self):
        """Retourne toutes les données financières du membre"""
        from core.utils import calculer_donnees_membre_completes
        return calculer_donnees_membre_completes(self)
    
    def peut_emprunter(self, montant):
        """Vérifie si le membre peut emprunter un montant donné"""
        from core.models import ConfigurationMutuelle
        from transactions.models import Emprunt
        
        # Vérifier qu'il n'a pas d'emprunt en cours
        if Emprunt.objects.filter(membre=self, statut='EN_COURS').exists():
            return False, "Vous avez déjà un emprunt en cours"
        
        # Vérifier qu'il est en règle
        if not self.is_en_regle:
            return False, "Vous devez être en règle pour emprunter"
        
        # Vérifier le montant maximum
        config = ConfigurationMutuelle.get_configuration()
        epargne_totale = self.calculer_epargne_totale()
        montant_max = epargne_totale * config.coefficient_emprunt_max
        
        if montant > montant_max:
            return False, f"Montant maximum empruntable: {montant_max:,.0f} FCFA"
        
        return True, "Emprunt autorisé"
    
    def calculer_statut_en_regle(self):
        """Calcule si le membre est en règle selon tous les critères"""
        donnees = self.get_donnees_completes()
        return donnees['membre_info']['en_regle']
    
    def save(self, *args, **kwargs):
        if not self.numero_membre:
            # Génération automatique du numéro de membre
            last_member = Membre.objects.order_by('numero_membre').last()
            if last_member:
                last_number = int(last_member.numero_membre.split('-')[-1])
                self.numero_membre = f"ENS-{last_number + 1:04d}"
            else:
                self.numero_membre = "ENS-0001"
        super().save(*args, **kwargs)
    
    @classmethod
    def peut_definir_statuts_membre(cls, membre):
        """
        Détermine si on peut attribuer un statut (EN_REGLE / NON_EN_REGLE)
        à un membre donné.

        Règle :
        - Le membre doit avoir vécu AU MOINS 2 sessions
        - Sessions ≥ session d'inscription
        - Sessions TERMINÉES ou EN_COURS
        """
        from core.models import Session

        sessions_membre = Session.objects.filter(
            date_session__gte=membre.session_inscription.date_session,
            statut__in=['TERMINEE', 'EN_COURS']
        ).order_by('date_session')

        nombre_sessions = sessions_membre.count()

        if nombre_sessions > 2:
            print(
                f"✅ Membre {membre.numero_membre} : "
                f"{nombre_sessions} sessions → Statut définissable"
            )
            return True
        else:
            print(
                f"⏳ Membre {membre.numero_membre} : "
                f"{nombre_sessions} session(s) → Statut NON définissable"
            )
            return False



    def update_inscription_terminee(self):
        """
        ✅ NOUVELLE MÉTHODE <-
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
        """Ajoute un montant au fonds social"""
        self.montant_total += montant
        self.save()
        
        # Log de l'opération
        MouvementFondsSocial.objects.create(
            fonds_social=self,
            type_mouvement='ENTREE',
            montant=montant,
            description=description
        )
        print(f"Fonds Social: +{montant:,.0f} FCFA - {description}")
    
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