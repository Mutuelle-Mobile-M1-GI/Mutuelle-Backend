from rest_framework import serializers
from decimal import Decimal
from django.db import models
# 🦊 CRITIQUE: Un `try` sans `catch` ? C'est comme sauter en parachute sans vérifier s'il y en a un.


from .models import (
    ConfigurationMutuelle, Exercice, Session, TypeAssistance, 
    Membre, FondsSocial, MouvementFondsSocial
)
from authentication.serializers import UtilisateurSerializer
from .utils import calculer_donnees_membre_completes, calculer_donnees_administrateur

class ConfigurationMutuelleSerializer(serializers.ModelSerializer):
    """
    Serializer pour la configuration de la mutuelle
    """
    class Meta:
        model = ConfigurationMutuelle
        fields = '__all__'

class ExerciceSerializer(serializers.ModelSerializer):
    """
    Serializer pour les exercices
    """
    is_en_cours = serializers.ReadOnlyField()
    nombre_sessions = serializers.SerializerMethodField()
    fonds_social_info = serializers.SerializerMethodField()
    
    
    class Meta:
        model = Exercice
        fields = [
            'id', 'nom', 'date_debut', 'date_fin', 'statut', 'description',
            'is_en_cours', 'nombre_sessions', 'fonds_social_info','emprunt_tiers',
            'date_creation', 'date_modification'
        ]
    
    def get_nombre_sessions(self, obj):
        return obj.sessions.count()
    
    def get_fonds_social_info(self, obj):
        try:
            fonds = obj.fonds_social
            return {
                'montant_total': fonds.montant_total,
                'derniere_modification': fonds.date_modification
            }
        except:
            return {'montant_total': Decimal('0'), 'derniere_modification': None}

class SessionSerializer(serializers.ModelSerializer):
    """
    Serializer pour les sessions avec transition automatique
    """
    exercice_nom = serializers.CharField(source='exercice.nom', read_only=True)
    is_en_cours = serializers.ReadOnlyField()
    nombre_membres_inscrits = serializers.SerializerMethodField()
    total_solidarite_collectee = serializers.SerializerMethodField()
    renflouements_generes = serializers.SerializerMethodField()
    
    class Meta:
        model = Session
        fields = [
            'id', 'exercice', 'exercice_nom', 'nom', 'date_session', 
            'montant_collation', 'statut', 'description', 'is_en_cours',
            'nombre_membres_inscrits', 'total_solidarite_collectee',
            'renflouements_generes', 'date_creation', 'date_modification'
        ]

    def validate(self, attrs):
        """
        Validation simple sans modifications de base de données
        """
        return super().validate(attrs)
    
    def get_nombre_membres_inscrits(self, obj):
        # Utilisation de getattr pour éviter les erreurs si la relation n'existe pas
        return getattr(obj, 'nouveaux_membres', Session.objects.none()).count()
    
    def get_total_solidarite_collectee(self, obj):
        from transactions.models import PaiementSolidarite
        from django.db.models import Sum
        from decimal import Decimal
        total = PaiementSolidarite.objects.filter(session=obj).aggregate(
            total=Sum('montant'))['total'] or Decimal('0')
        return total
    
    def get_renflouements_generes(self, obj):
        from django.db.models import Sum
        from decimal import Decimal
        total = obj.renflouements.aggregate(
            total=Sum('montant_du'))['total'] or Decimal('0')
        return total
    
class TypeAssistanceSerializer(serializers.ModelSerializer):
    """
    Serializer pour les types d'assistance
    """
    nombre_assistances_accordees = serializers.SerializerMethodField()
    montant_total_accorde = serializers.SerializerMethodField()
    
    class Meta:
        model = TypeAssistance
        fields = [
            'id', 'nom', 'montant', 'description', 'actif',
            'nombre_assistances_accordees', 'montant_total_accorde',
            'date_creation', 'date_modification'
        ]
    
    def get_nombre_assistances_accordees(self, obj):
        return obj.assistances_accordees.filter(statut='PAYEE').count()
    
    def get_montant_total_accorde(self, obj):
        total = obj.assistances_accordees.filter(statut='PAYEE').aggregate(
            total=models.Sum('montant'))['total'] or Decimal('0')
        return total

class FondsSocialSerializer(serializers.ModelSerializer):
    """
    Serializer pour le fonds social
    """
    exercice_nom = serializers.CharField(source='exercice.nom', read_only=True)
    mouvements_recents = serializers.SerializerMethodField()
    
    class Meta:
        model = FondsSocial
        fields = [
            'id', 'exercice', 'exercice_nom', 'montant_total',
            'mouvements_recents', 'date_creation', 'date_modification'
        ]
    
    def get_mouvements_recents(self, obj):
        mouvements = obj.mouvements.all()[:10]  # 10 derniers mouvements
        return MouvementFondsSocialSerializer(mouvements, many=True).data

class MouvementFondsSocialSerializer(serializers.ModelSerializer):
    """
    Serializer pour les mouvements du fonds social
    """
    class Meta:
        model = MouvementFondsSocial
        fields = '__all__'

class MembreSerializer(serializers.ModelSerializer):
    """
    Serializer pour les membres AVEC TOUTES LES DONNÉES CALCULÉES
    C'est LE serializer le plus important pour le frontend !
    """
    utilisateur = UtilisateurSerializer(read_only=False, required=False)
    exercice_inscription_nom = serializers.CharField(source='exercice_inscription.nom', read_only=True)
    session_inscription_nom = serializers.CharField(source='session_inscription.nom', read_only=True)
    is_en_regle = serializers.ReadOnlyField()
    
    # TOUTES LES DONNÉES FINANCIÈRES CALCULÉES
    donnees_financieres = serializers.SerializerMethodField()
    
    class Meta:
        model = Membre
        fields = [
            'id', 'utilisateur', 'numero_membre', 'date_inscription', 'statut',
            'exercice_inscription', 'exercice_inscription_nom',
            'session_inscription', 'session_inscription_nom',
            'is_en_regle', 'donnees_financieres',
            'date_creation', 'date_modification'
        ]
    
    def create(self, validated_data):
        """
        Crée un Membre avec un Utilisateur imbriqué
        """
        from django.contrib.auth import get_user_model
        from django.db import transaction
        
        User = get_user_model()
        utilisateur_data = validated_data.pop('utilisateur', None)
        
        with transaction.atomic():
            # Créer l'utilisateur si les données sont fournies
            if utilisateur_data:
                # Extraire le mot de passe avant de créer l'utilisateur
                password = utilisateur_data.pop('password', None)
                
                # Créer l'utilisateur
                utilisateur = User.objects.create_user(**utilisateur_data)
                
                # Définir le mot de passe (qui sera hashé)
                if password:
                    utilisateur.set_password(password)
                    utilisateur.save()
                
                validated_data['utilisateur'] = utilisateur
            
            # Créer le Membre
            membre = Membre.objects.create(**validated_data)
        
        return membre
    
    def get_donnees_financieres(self, obj):
        """
        Retourne TOUTES les données financières calculées du membre
        Cette méthode est CRUCIALE car elle expose tout ce que le frontend doit afficher
        """
        return calculer_donnees_membre_completes(obj)

class MembreSimpleSerializer(serializers.ModelSerializer):
    """
    Serializer simplifié pour les références
    """
    nom_complet = serializers.CharField(source='utilisateur.nom_complet', read_only=True)
    email = serializers.CharField(source='utilisateur.email', read_only=True)
    
    class Meta:
        model = Membre
        fields = ['id', 'numero_membre', 'nom_complet', 'email', 'statut']

class DonneesAdministrateurSerializer(serializers.Serializer):
    """
    Serializer pour toutes les données que l'administrateur doit voir
    """
    fonds_social = serializers.DictField()
    tresor = serializers.DictField()
    emprunts_en_cours = serializers.DictField()
    situation_globale = serializers.DictField()
    
    # Statistiques supplémentaires
    statistiques_membres = serializers.SerializerMethodField()
    statistiques_sessions = serializers.SerializerMethodField()
    
    def get_statistiques_membres(self, obj):
        total_membres = Membre.objects.count()
        membres_en_regle = Membre.objects.filter(statut='EN_REGLE').count()
        membres_non_en_regle = Membre.objects.filter(statut='NON_EN_REGLE').count()
        membres_suspendus = Membre.objects.filter(statut='SUSPENDU').count()
        
        return {
            'total': total_membres,
            'en_regle': membres_en_regle,
            'non_en_regle': membres_non_en_regle,
            'suspendus': membres_suspendus,
            'pourcentage_en_regle': (membres_en_regle / total_membres * 100) if total_membres > 0 else 0
        }
    
    def get_statistiques_sessions(self, obj):
        from core.models import Session
        
        total_sessions = Session.objects.count()
        sessions_en_cours = Session.objects.filter(statut='EN_COURS').count()
        sessions_terminees = Session.objects.filter(statut='TERMINEE').count()
        
        return {
            'total': total_sessions,
            'en_cours': sessions_en_cours,
            'terminees': sessions_terminees
        }
from .models import EmpruntCoefficientTier
class EmpruntCoefficientTierSerializer(serializers.ModelSerializer):
    """
    Serializer pour les tranches de coefficient d'emprunt
    Utilisé dans la création d'exercice + paramètres
    """
    class Meta:
        model = EmpruntCoefficientTier
        fields = [
            'id',
            'min_amount',
            'max_amount',
            'coefficient',
            'max_cap',
            'created_at',
            'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']

    def validate(self, attrs):
        if attrs['min_amount'] >= attrs['max_amount']:
            raise serializers.ValidationError(
                "Le montant minimum doit être strictement inférieur au montant maximum"
            )
        return attrs

    # Optionnel : affichage lisible dans les logs/admin
    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['display'] = (
            f"{instance.min_amount:,} → {instance.max_amount:,} "
            f"× {instance.coefficient}"
            + (f" (max {instance.max_cap:,} FCFA)" if instance.max_cap else "")
        )
        return data