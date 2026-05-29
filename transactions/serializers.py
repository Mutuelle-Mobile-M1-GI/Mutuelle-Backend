from rest_framework import serializers
from decimal import Decimal
from django.db import models
from .models import (
    PaiementInscription, PaiementSolidarite, EpargneTransaction,
    Emprunt, Remboursement, AssistanceAccordee, Renflouement,
    PaiementRenflouement, PenaliteEmprunt, RepartitionRenflouementExercice
)
from core.models import DépenseExercice, ConfigurationMutuelle
from core.serializers import MembreSimpleSerializer, SessionSerializer, TypeAssistanceSerializer
import logging
from rest_framework.response import Response
from rest_framework import status

logger = logging.getLogger(__name__)

class PaiementInscriptionSerializer(serializers.ModelSerializer):
    """
    Serializer pour les paiements d'inscription (une seule tranche par membre).
    """
    membre_info = MembreSimpleSerializer(source='membre', read_only=True)
    session_nom = serializers.CharField(source='session.nom', read_only=True)
    montant_inscription_du = serializers.DecimalField(
        max_digits=12, decimal_places=2, read_only=True, required=False
    )

    class Meta:
        model = PaiementInscription
        fields = [
            'id', 'membre', 'membre_info', 'montant', 'montant_inscription_du',
            'date_paiement', 'session', 'session_nom', 'notes'
        ]

    def validate(self, data):
        """Un seul paiement d'inscription par membre et montant complet requis."""
        # Vérifier qu'un membre n'a pas déjà payé son inscription
        if self.instance is None and data.get('membre'):
            if PaiementInscription.objects.filter(membre=data['membre']).exists():
                raise serializers.ValidationError({
                    'membre': "Ce membre a déjà effectué son paiement d'inscription. "
                              "L'inscription se fait en une seule tranche."
                })
        
        # Vérifier que le montant payé est égal au montant d'inscription configuré
        if data.get('montant'):
            config = ConfigurationMutuelle.get_configuration()
            montant_requis = config.montant_inscription
            
            if data['montant'] < montant_requis:
                raise serializers.ValidationError({
                    'montant': f"Le paiement d'inscription doit être complet. "
                              f"Montant requis: {montant_requis:,.0f} FCFA. "
                              f"Vous avez payé: {data['montant']:,.0f} FCFA."
                })
        
        return data


class PaiementSolidariteSerializer(serializers.ModelSerializer):
    """
    Serializer pour les paiements de solidarité (paiement unique à vie).
    Expose pour chaque enregistrement :
    - montant_paye_total       : total cumulé payé par le membre (toutes sessions)
    - montant_restant_solidarite : ce qu'il reste à payer pour compléter la solidarité
    - solidarite_terminee      : True si la solidarité est complètement réglée
    """
    membre_info = MembreSimpleSerializer(source='membre', read_only=True)
    session_nom = serializers.CharField(source='session.nom', read_only=True)

    # ── Champs calculés pour la barre de progression frontend ──────────────
    montant_paye_total = serializers.SerializerMethodField()
    montant_restant_solidarite = serializers.SerializerMethodField()
    solidarite_terminee = serializers.SerializerMethodField()

    class Meta:
        model = PaiementSolidarite
        fields = [
            'id', 'membre', 'membre_info', 'session', 'session_nom',
            'montant', 'montant_solidarite_du', 'date_paiement', 'notes',
            'montant_paye_total', 'montant_restant_solidarite', 'solidarite_terminee',
        ]
        extra_kwargs = {
            'montant_solidarite_du': {'required': False, 'read_only': True},
        }

    # ── get_montant_paye_total ───────────────────────────────────────────────
    def get_montant_paye_total(self, obj):
        """
        Total cumulé de tous les paiements de solidarité de ce membre (toutes sessions confondues).
        """
        from django.db.models import Sum
        from decimal import Decimal
        total = PaiementSolidarite.objects.filter(
            membre=obj.membre,
        ).aggregate(total=Sum('montant'))['total'] or Decimal('0')
        return total

    # ── get_montant_restant_solidarite ──────────────────────────────────────
    def get_montant_restant_solidarite(self, obj):
        """
        Montant restant à payer pour compléter la solidarité à vie.
        Retourne 0 si la solidarité est déjà complète.
        """
        from django.db.models import Sum
        from decimal import Decimal
        config = ConfigurationMutuelle.get_configuration()
        montant_du = config.montant_solidarite
        total_paye = PaiementSolidarite.objects.filter(
            membre=obj.membre
        ).aggregate(total=Sum('montant'))['total'] or Decimal('0')
        return max(montant_du - total_paye, Decimal('0'))

    # ── get_solidarite_terminee ─────────────────────────────────────────────
    def get_solidarite_terminee(self, obj):
        """True si la solidarité est entièrement payée."""
        return obj.membre.solidarite_terminee

    # ── create ──────────────────────────────────────────────────────────────
    def create(self, validated_data):
        """
        Crée un paiement de solidarité.
        montant_solidarite_du = montant configuré actuellement (rempli dans le modèle).
        """
        return super().create(validated_data)

    def validate(self, data):
        membre = data.get('membre') or (self.instance.membre if self.instance else None)
        if membre and not membre.inscription_terminee:
            raise serializers.ValidationError(
                "Le membre n'a pas terminé son inscription. "
                "Le paiement de solidarité est interdit tant que l'inscription n'est pas complète."
            )
        return data

class EpargneTransactionSerializer(serializers.ModelSerializer):
    """
    Serializer pour les transactions d'épargne
    """
    membre_info = MembreSimpleSerializer(source='membre', read_only=True)
    session_nom = serializers.CharField(source='session.nom', read_only=True)
    type_transaction_display = serializers.CharField(source='get_type_transaction_display', read_only=True)
    
    class Meta:
        model = EpargneTransaction
        fields = [
            'id', 'membre', 'membre_info', 'type_transaction', 'type_transaction_display',
            'montant', 'session', 'session_nom', 'date_transaction', 'notes'
        ]
    
    def validate(self, data):
        membre = data.get('membre') or (self.instance.membre if self.instance else None)
        if membre and not membre.inscription_terminee:
            raise serializers.ValidationError(
                "Le membre n'a pas terminé son inscription. "
                "Il ne peut pas effectuer d'opérations d'épargne tant que l'inscription n'est pas complète."
            )
        return data

    def create(self, validated_data):
        return super().create(validated_data)

class EmpruntSerializer(serializers.ModelSerializer):
    """
    Serializer pour les emprunts AVEC TOUS LES CALCULS et validations
    """
    membre_info = MembreSimpleSerializer(source='membre', read_only=True)
    session_nom = serializers.CharField(source='session_emprunt.nom', read_only=True)
    statut_display = serializers.CharField(source='get_statut_display', read_only=True)
    
    # Calculs automatiques
    montant_restant_a_rembourser = serializers.ReadOnlyField()
    montant_interets = serializers.ReadOnlyField()
    pourcentage_rembourse = serializers.ReadOnlyField()
    montant_net_a_verser = serializers.SerializerMethodField()
    
    # Nouveaux champs calculés
    is_en_retard = serializers.ReadOnlyField()
    jours_de_retard = serializers.ReadOnlyField()
    jours_restants = serializers.ReadOnlyField()
    
    # Détails des remboursements
    remboursements_details = serializers.SerializerMethodField()
    
    class Meta:
        model = Emprunt
        fields = [
            'id', 'membre', 'membre_info', 'montant_emprunte', 'taux_interet','montant_net_a_verser',
            'montant_total_a_rembourser', 'montant_rembourse', 'montant_restant_a_rembourser',
            'montant_interets', 'pourcentage_rembourse', 'session_emprunt', 'session_nom',
            'date_emprunt', 'statut', 'statut_display', 'notes', 'remboursements_details','is_en_retard', 'jours_de_retard', 'jours_restants'
        ]
        extra_kwargs = {
            'session_emprunt': {'required': False},
            'notes': {'required': False, 'allow_blank': True},
            'date_emprunt': {'required': False},
            'taux_interet': {'required': False},
            'montant_total_a_rembourser': {'required': False},
            'date_remboursement_max': {'required': False},  # 🔧 AJOUTÉ

        }
    
    def get_montant_net_a_verser(self, obj):
        """Calcule ce que le membre reçoit réellement en main propre"""
        if obj.montant_emprunte and obj.taux_interet:
            interets = (obj.montant_emprunte * obj.taux_interet) / Decimal('100')
            return obj.montant_emprunte - interets
        return obj.montant_emprunte
    
    def validate_montant_emprunte(self, value):
        """Validation du montant d'emprunt"""
        print(f"🔍 VALIDATION MONTANT: {value}")
        
        if value <= 0:
            raise serializers.ValidationError("Le montant doit être positif")
        
        # Vérifier un montant maximum absolu (sécurité)
        if value > Decimal('10000000'):  # 10 millions
            raise serializers.ValidationError("Montant trop élevé")
        
        print(f"✅ Montant validé: {value}")
        return value
    
    def validate_membre(self, value):
        """Validation du membre"""
        print(f"🔍 VALIDATION MEMBRE: {value}")
        
        if not value:
            raise serializers.ValidationError("Membre requis")
        
        # Vérifier que le membre existe et est en règle
        if value.statut != 'EN_REGLE':
            raise serializers.ValidationError(f"Le membre {value.numero_membre} n'est pas en règle")
        
        print(f"✅ Membre validé: {value.numero_membre}")
        return value
    
    def validate(self, data):
        """Validation croisée : Vérification du coefficient d'épargne"""
        membre = data.get('membre')
        montant_demande = data.get('montant_emprunte')
        
        if membre and montant_demande:
            # Utilise la méthode qu'on a mise dans le modèle Membre précédemment
            peut_emprunter, message = membre.peut_emprunter(montant_demande)
            if not peut_emprunter:
                raise serializers.ValidationError({"montant_emprunte": message})
        
        return data
    
    def get_remboursements_details(self, obj):
        """Détails des remboursements avec gestion d'erreurs"""
        try:
            remboursements = obj.remboursements.all()
            return RemboursementSerializer(remboursements, many=True).data
        except Exception as e:
            print(f"❌ Erreur remboursements_details: {e}")
            return []


class TopEpargnantSerializer(serializers.Serializer):
    """Serializer pour afficher les membres dans le Top Epargne"""
    nom_complet = serializers.CharField(source='utilisateur.nom_complet')
    numero_membre = serializers.CharField()
    epargne_reelle = serializers.SerializerMethodField()

    def get_epargne_reelle(self, obj):
        # On ne prend QUE les types qui sont de l'épargne positive
        types_valides = ['DEPOT', 'AJOUT_INTERET', 'RETOUR_REMBOURSEMENT']
        total = obj.transactions_epargne.filter(
            type_transaction__in=types_valides
        ).aggregate(total=models.Sum('montant'))['total'] or Decimal('0')
        return total
    
class RemboursementSerializer(serializers.ModelSerializer):
    """
    Serializer pour les remboursements
    """
    emprunt_info = serializers.SerializerMethodField()
    session_nom = serializers.CharField(source='session.nom', read_only=True)
    
    class Meta:
        model = Remboursement
        fields = [
            'id', 'emprunt', 'emprunt_info', 'montant', 'montant_capital',
            'montant_interet', 'session', 'session_nom', 'date_remboursement', 'notes'
        ]
    
    def get_emprunt_info(self, obj):
        return {
            'id': str(obj.emprunt.id),
            'membre_numero': obj.emprunt.membre.numero_membre,
            'membre_nom': obj.emprunt.membre.utilisateur.nom_complet,
            'montant_emprunte': obj.emprunt.montant_emprunte,
            'montant_total_a_rembourser': obj.emprunt.montant_total_a_rembourser
        }

class AssistanceAccordeeSerializer(serializers.ModelSerializer):
    """
    Serializer pour les assistances accordées
    """
    membre_info = MembreSimpleSerializer(source='membre', read_only=True)
    type_assistance_info = TypeAssistanceSerializer(source='type_assistance', read_only=True)
    session_nom = serializers.CharField(source='session.nom', read_only=True)
    statut_display = serializers.CharField(source='get_statut_display', read_only=True)
    
    class Meta:
        model = AssistanceAccordee
        fields = [
            'id', 'membre', 'membre_info', 'type_assistance', 'type_assistance_info',
            'montant', 'session', 'session_nom', 'date_demande', 'date_paiement',
            'statut', 'statut_display', 'justification', 'notes'
        ]

class RenflouementSerializer(serializers.ModelSerializer):
    """
    Serializer pour les renflouements AVEC TOUS LES CALCULS
    """
    membre_info = MembreSimpleSerializer(source='membre', read_only=True)
    session_nom = serializers.CharField(source='session.nom', read_only=True)
    type_cause_display = serializers.CharField(source='get_type_cause_display', read_only=True)
    
    # Calculs automatiques
    montant_restant = serializers.ReadOnlyField()
    is_solde = serializers.ReadOnlyField()
    pourcentage_paye = serializers.ReadOnlyField()
    
    # Détails des paiements
    paiements_details = serializers.SerializerMethodField()
    
    class Meta:
        model = Renflouement
        fields = [
            'id', 'membre', 'membre_info', 'session', 'session_nom',
            'montant_du', 'montant_paye', 'montant_restant', 'is_solde',
            'pourcentage_paye', 'cause', 'type_cause', 'type_cause_display',
            'date_creation', 'date_derniere_modification', 'paiements_details'
        ]
    
    def get_paiements_details(self, obj):
        paiements = obj.paiements.all()
        return PaiementRenflouementSerializer(paiements, many=True).data
class PaiementRenflouementSerializer(serializers.ModelSerializer):
    """
    Serializer pour les paiements de renflouement
    """
    renflouement_info = serializers.SerializerMethodField()
    session_nom = serializers.CharField(source='session.nom', read_only=True)
    
    class Meta:
        model = PaiementRenflouement
        fields = [
            'id', 'renflouement', 'renflouement_info', 'montant',
            'session', 'session_nom', 'date_paiement', 'notes'
        ]
    
    def get_renflouement_info(self, obj):
        return {
            'id': str(obj.renflouement.id),
            'membre_numero': obj.renflouement.membre.numero_membre,
            'membre_nom': obj.renflouement.membre.utilisateur.nom_complet,
            'montant_total_du': obj.renflouement.montant_du,
            'cause': obj.renflouement.cause
        }


class StatistiquesTransactionsSerializer(serializers.Serializer):
    """
    Serializer pour les statistiques des transactions
    """
    inscriptions = serializers.DictField()
    solidarites = serializers.DictField()
    # Cette partie doit être alimentée par une logique filtrée dans la View
    epargnes = serializers.DictField() 
    emprunts = serializers.DictField()
    assistances = serializers.DictField()
    renflouements = serializers.DictField()
    # Ajoute ceci pour le classement
    top_epargnants = TopEpargnantSerializer(many=True, read_only=True)


class DépenseExerciceSerializer(serializers.ModelSerializer):
    """
    ✅ NOUVEAU: Serializer pour les dépenses d'exercice
    """
    exercice_nom = serializers.CharField(source='exercice.nom', read_only=True)
    session_nom = serializers.CharField(source='session.nom', read_only=True, allow_null=True)
    beneficiaire_info = MembreSimpleSerializer(source='beneficiaire', read_only=True, allow_null=True)
    
    class Meta:
        model = DépenseExercice
        fields = [
            'id', 'exercice', 'exercice_nom', 'type_depense', 'montant',
            'description', 'session', 'session_nom', 'beneficiaire', 
            'beneficiaire_info', 'date_creation'
        ]
        read_only_fields = ['id', 'date_creation']


class PenaliteEmpruntSerializer(serializers.ModelSerializer):
    """
    Serializer pour les pénalités d'emprunt - Transparence totale
    """
    # Informations sur l'emprunt et le membre
    emprunt_info = serializers.SerializerMethodField()
    membre_numero = serializers.CharField(source='emprunt.membre.numero_membre', read_only=True)
    membre_nom = serializers.CharField(source='emprunt.membre.utilisateur.nom_complet', read_only=True)
    
    # Informations sur la session
    session_info = SessionSerializer(source='session_application', read_only=True)
    
    # Informations sur qui a appliqué la pénalité
    appliquee_par_nom = serializers.CharField(source='appliquee_par.nom_complet', read_only=True, allow_null=True)
    
    # Formule de calcul pour affichage
    formule_calcul = serializers.ReadOnlyField()
    
    # Champs calculés pour l'affichage
    type_penalite_display = serializers.CharField(source='get_type_penalite_display', read_only=True)
    
    class Meta:
        model = PenaliteEmprunt
        fields = [
            'id', 'emprunt', 'emprunt_info', 'membre_numero', 'membre_nom',
            'type_penalite', 'type_penalite_display', 'palier', 'sessions_ecoulees',
            'montant_reste_avant', 'taux_applique', 'montant_interet_taux',
            'montant_penalite_fixe', 'montant_total_penalite', 'formule_calcul',
            'date_application', 'appliquee_par', 'appliquee_par_nom',
            'session_application', 'session_info', 'justification', 'notes_complementaires'
        ]
        read_only_fields = [
            'id', 'montant_total_penalite', 'formule_calcul', 'date_application',
            'emprunt_info', 'membre_numero', 'membre_nom', 'type_penalite_display',
            'appliquee_par_nom', 'session_info'
        ]
    
    def get_emprunt_info(self, obj):
        """Informations résumées sur l'emprunt"""
        return {
            'id': str(obj.emprunt.id),
            'montant_initial': obj.emprunt.montant_emprunte,
            'montant_total_actuel': obj.emprunt.montant_total_a_rembourser,
            'montant_rembourse': obj.emprunt.montant_rembourse,
            'montant_restant': obj.emprunt.montant_restant_a_rembourser,
            'statut': obj.emprunt.statut,
            'date_emprunt': obj.emprunt.date_emprunt,
            'date_echeance': obj.emprunt.date_remboursement_max,
            'jours_retard': obj.emprunt.jours_de_retard if obj.emprunt.is_en_retard else 0
        }


class RepartitionRenflouementExerciceSerializer(serializers.ModelSerializer):
    """
    Serializer pour les répartitions de renflouement de fin d'exercice
    """
    exercice_nom = serializers.CharField(source='exercice.nom', read_only=True)
    calcule_par_nom = serializers.CharField(source='calcule_par.nom_complet', read_only=True, allow_null=True)
    
    # Propriétés calculées
    formule_calcul = serializers.ReadOnlyField()
    detail_ratios = serializers.ReadOnlyField()
    
    class Meta:
        model = RepartitionRenflouementExercice
        fields = [
            'id', 'exercice', 'exercice_nom',
            'total_sorties_caisse_inscription', 'total_sorties_fonds_social', 'total_sorties_global',
            'ratio_caisse_inscription', 'ratio_fonds_social',
            'nombre_membres_en_regle', 'nombre_membres_non_en_regle', 'nombre_membres_total',
            'montant_par_membre', 'formule_calcul', 'detail_ratios',
            'date_calcul', 'calcule_par', 'calcule_par_nom', 'notes_calcul'
        ]
        read_only_fields = [
            'id', 'date_calcul', 'exercice_nom', 'calcule_par_nom', 
            'formule_calcul', 'detail_ratios'
        ]


class RenflouementSerializer(serializers.ModelSerializer):
    """
    Serializer pour les renflouements avec support du système proportionnel
    """
    membre_info = MembreSimpleSerializer(source='membre', read_only=True)
    session_info = SessionSerializer(source='session', read_only=True)
    exercice_nom = serializers.CharField(source='exercice_renflouement.nom', read_only=True, allow_null=True)
    
    # Propriétés calculées
    montant_restant = serializers.ReadOnlyField()
    is_solde = serializers.ReadOnlyField()
    pourcentage_paye = serializers.ReadOnlyField()
    
    # Détails des paiements
    paiements_details = serializers.SerializerMethodField()
    
    # Informations sur la répartition proportionnelle
    est_proportionnel = serializers.SerializerMethodField()
    detail_repartition = serializers.SerializerMethodField()
    
    class Meta:
        model = Renflouement
        fields = [
            'id', 'membre', 'membre_info', 'session', 'session_info',
            'montant_du', 'montant_paye', 'montant_restant', 'is_solde', 'pourcentage_paye',
            'cause', 'type_cause', 'exercice_renflouement', 'exercice_nom',
            'ratio_caisse_inscription', 'ratio_fonds_social',
            'est_proportionnel', 'detail_repartition',
            'date_creation', 'date_derniere_modification',
            'paiements_details'
        ]
        read_only_fields = [
            'id', 'montant_restant', 'is_solde', 'pourcentage_paye',
            'date_creation', 'date_derniere_modification',
            'membre_info', 'session_info', 'exercice_nom',
            'est_proportionnel', 'detail_repartition', 'paiements_details'
        ]
    
    def get_est_proportionnel(self, obj):
        """Indique si ce renflouement utilise le système proportionnel"""
        return obj.ratio_caisse_inscription is not None and obj.ratio_fonds_social is not None
    
    def get_detail_repartition(self, obj):
        """Détail de la répartition proportionnelle"""
        if not self.get_est_proportionnel(obj):
            return "Ancien système : 100% fonds social"
        
        return {
            'caisse_inscription': f"{obj.ratio_caisse_inscription}%",
            'fonds_social': f"{obj.ratio_fonds_social}%",
            'description': f"{obj.ratio_caisse_inscription}% caisse inscription, {obj.ratio_fonds_social}% fonds social"
        }
    
    def get_paiements_details(self, obj):
        """Détails des paiements effectués"""
        paiements = obj.paiements.all().order_by('-date_paiement')
        return PaiementRenflouementSerializer(paiements, many=True).data


class PaiementRenflouementSerializer(serializers.ModelSerializer):
    """
    Serializer pour les paiements de renflouement avec traçabilité de la répartition
    """
    renflouement_info = serializers.SerializerMethodField()
    membre_numero = serializers.CharField(source='renflouement.membre.numero_membre', read_only=True)
    membre_nom = serializers.CharField(source='renflouement.membre.utilisateur.nom_complet', read_only=True)
    session_info = SessionSerializer(source='session', read_only=True)
    
    # Détail de la répartition
    repartition_detail = serializers.SerializerMethodField()
    
    class Meta:
        model = PaiementRenflouement
        fields = [
            'id', 'renflouement', 'renflouement_info', 'membre_numero', 'membre_nom',
            'montant', 'montant_caisse_inscription', 'montant_fonds_social',
            'ratio_caisse_utilise', 'ratio_fonds_utilise', 'repartition_detail',
            'session', 'session_info', 'date_paiement', 'notes'
        ]
        read_only_fields = [
            'id', 'montant_caisse_inscription', 'montant_fonds_social',
            'ratio_caisse_utilise', 'ratio_fonds_utilise',
            'date_paiement', 'renflouement_info', 'membre_numero', 'membre_nom',
            'session_info', 'repartition_detail'
        ]
    
    def get_renflouement_info(self, obj):
        """Informations résumées sur le renflouement"""
        return {
            'id': str(obj.renflouement.id),
            'montant_du': obj.renflouement.montant_du,
            'montant_paye': obj.renflouement.montant_paye,
            'montant_restant': obj.renflouement.montant_restant,
            'type_cause': obj.renflouement.type_cause,
            'est_proportionnel': obj.ratio_caisse_utilise is not None
        }
    
    def get_repartition_detail(self, obj):
        """Détail de la répartition de ce paiement"""
        if obj.ratio_caisse_utilise is None:
            return {
                'type': 'ancien_systeme',
                'description': '100% fonds social',
                'caisse_inscription': '0 FCFA (0%)',
                'fonds_social': f'{obj.montant:,.0f} FCFA (100%)'
            }
        
        return {
            'type': 'proportionnel',
            'description': f'{obj.ratio_caisse_utilise}% caisse inscription, {obj.ratio_fonds_utilise}% fonds social',
            'caisse_inscription': f'{obj.montant_caisse_inscription:,.0f} FCFA ({obj.ratio_caisse_utilise}%)',
            'fonds_social': f'{obj.montant_fonds_social:,.0f} FCFA ({obj.ratio_fonds_utilise}%)',
            'formule': f'{obj.montant:,.0f} × {obj.ratio_caisse_utilise}% = {obj.montant_caisse_inscription:,.0f} | {obj.montant:,.0f} × {obj.ratio_fonds_utilise}% = {obj.montant_fonds_social:,.0f}'
        }


class EmpruntDetailAvecPenalitesSerializer(serializers.ModelSerializer):
    """
    Serializer détaillé pour un emprunt avec toutes ses pénalités
    Utilisé pour le suivi transparent d'un emprunt
    """
    # Informations du membre
    membre_info = MembreSimpleSerializer(source='membre', read_only=True)
    
    # Informations de session
    session_info = SessionSerializer(source='session_emprunt', read_only=True)
    
    # Toutes les pénalités appliquées
    penalites = PenaliteEmpruntSerializer(many=True, read_only=True)
    
    # Statistiques calculées
    nombre_penalites = serializers.SerializerMethodField()
    total_penalites = serializers.SerializerMethodField()
    montant_initial_emprunte = serializers.DecimalField(max_digits=12, decimal_places=2, source='montant_emprunte', read_only=True)
    
    # Propriétés calculées existantes
    montant_restant_a_rembourser = serializers.ReadOnlyField()
    montant_interets = serializers.ReadOnlyField()
    pourcentage_rembourse = serializers.ReadOnlyField()
    is_en_retard = serializers.ReadOnlyField()
    jours_de_retard = serializers.ReadOnlyField()
    jours_restants = serializers.ReadOnlyField()
    
    # Détails des remboursements
    remboursements_details = serializers.SerializerMethodField()
    
    class Meta:
        model = Emprunt
        fields = [
            'id', 'membre_info', 'montant_initial_emprunte', 'montant_emprunte',
            'taux_interet', 'montant_total_a_rembourser', 'montant_rembourse',
            'montant_restant_a_rembourser', 'montant_interets', 'pourcentage_rembourse',
            'session_info', 'date_emprunt', 'date_remboursement_max',
            'statut', 'is_en_retard', 'jours_de_retard', 'jours_restants',
            'notes', 'penalites', 'nombre_penalites', 'total_penalites',
            'remboursements_details', 'date_creation', 'date_modification'
        ]
        read_only_fields = ['id', 'date_creation', 'date_modification']
    
    def get_nombre_penalites(self, obj):
        """Nombre total de pénalités appliquées"""
        return obj.penalites.count()
    
    def get_total_penalites(self, obj):
        """Montant total des pénalités appliquées"""
        return sum(p.montant_total_penalite for p in obj.penalites.all())
    
    def get_remboursements_details(self, obj):
        """Détails des remboursements effectués"""
        from .models import Remboursement
        remboursements = Remboursement.objects.filter(emprunt=obj).order_by('-date_remboursement')
        return RemboursementSerializer(remboursements, many=True).data