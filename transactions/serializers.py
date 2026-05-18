from rest_framework import serializers
from decimal import Decimal
from django.db import models
from .models import (
    PaiementInscription, PaiementSolidarite, EpargneTransaction,
    Emprunt, Remboursement, AssistanceAccordee, Renflouement,
    PaiementRenflouement
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
    Serializer pour les paiements de solidarité.
    Expose également pour chaque enregistrement :
    - montant_paye_exercice_en_cours : ce que le membre a déjà versé sur l'exercice en cours
    - montant_reporte             : dette reportée de l'exercice précédent (SolidariteExerciceReport)
    """
    membre_info = MembreSimpleSerializer(source='membre', read_only=True)
    session_nom = serializers.CharField(source='session.nom', read_only=True)

    # ── Champs calculés pour la barre de progression frontend ──────────────
    montant_paye_exercice_en_cours = serializers.SerializerMethodField()
    montant_reporte = serializers.SerializerMethodField()

    class Meta:
        model = PaiementSolidarite
        fields = [
            'id', 'membre', 'membre_info', 'session', 'session_nom',
            'montant', 'montant_solidarite_du', 'date_paiement', 'notes',
            'montant_paye_exercice_en_cours', 'montant_reporte',
        ]
        extra_kwargs = {
            'montant_solidarite_du': {'required': False, 'read_only': False},
        }

    # ── get_montant_paye_exercice_en_cours ──────────────────────────────────
    def get_montant_paye_exercice_en_cours(self, obj):
        """
        Total des paiements de solidarité de ce membre sur l'exercice en cours.
        """
        from django.db.models import Sum
        from decimal import Decimal
        from core.models import Exercice

        exercice = Exercice.get_exercice_en_cours()
        if not exercice:
            return Decimal('0')

        total = PaiementSolidarite.objects.filter(
            membre=obj.membre,
            session__exercice=exercice,
        ).aggregate(total=Sum('montant'))['total'] or Decimal('0')
        return total

    # ── get_montant_reporte ─────────────────────────────────────────────────
    def get_montant_reporte(self, obj):
        """
        Montant reporté de l'exercice précédent pour ce membre.
        Positif = dette à payer, Négatif = surplus (crédit).
        Retourne 0 s'il n'y a pas de report.
        """
        from decimal import Decimal
        from core.models import Exercice, SolidariteExerciceReport

        exercice = Exercice.get_exercice_en_cours()
        if not exercice:
            return Decimal('0')

        report = SolidariteExerciceReport.objects.filter(
            membre=obj.membre,
            exercice_cible=exercice,
        ).first()
        return report.montant_reporte if report else Decimal('0')

    # ── create ──────────────────────────────────────────────────────────────
    def create(self, validated_data):
        """
        Crée un paiement de solidarité en remplissant montant_solidarite_du.
        Logique :
        - Premier paiement pour ce membre → utiliser montant de la configuration
        - Paiements suivants → utiliser le montant du premier paiement (pour cohérence)
        """
        from core.models import ConfigurationMutuelle

        if 'montant_solidarite_du' not in validated_data or not validated_data.get('montant_solidarite_du'):
            membre = validated_data.get('membre')
            session = validated_data.get('session')

            premier_paiement = PaiementSolidarite.objects.filter(
                membre=membre
            ).order_by('date_paiement').first()

            if not premier_paiement:
                config = ConfigurationMutuelle.get_configuration()
                validated_data['montant_solidarite_du'] = config.montant_solidarite
                print(f"📝 Premier paiement solidarité pour {membre.numero_membre}: montant dû = {validated_data['montant_solidarite_du']} FCFA")
            else:
                validated_data['montant_solidarite_du'] = premier_paiement.montant_solidarite_du
                print(f"📝 Paiement suivant pour {membre.numero_membre} (session {session.nom}): montant dû = {validated_data['montant_solidarite_du']} FCFA (du premier paiement)")

        return super().create(validated_data)

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
    
    def create(self, validated_data):
        # On supprime simplement la logique de solidarité qui n'appartient pas à l'épargne
        # ou on s'assure qu'elle ne bloque pas la création.
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