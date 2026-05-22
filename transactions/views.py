from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django_filters import rest_framework as filters
from django.db import models
from django.db.models import Sum, Q, F
from decimal import Decimal
import logging
from rest_framework.response import Response
from rest_framework import status
from django.db import models, transaction
import logging
from rest_framework.response import Response
from rest_framework import status
import logging
from decimal import Decimal, InvalidOperation
from django.db import transaction
from django.utils import timezone
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Sum, Q, DecimalField
from django.db.models.functions import Coalesce  # <--- C'est cette ligne qu'il te manque

logger = logging.getLogger(__name__)

logger = logging.getLogger(__name__)



from core.models import Membre, Session, TypeAssistance
from .models import (
    PaiementInscription, PaiementSolidarite, EpargneTransaction,
    Emprunt, Remboursement, AssistanceAccordee, Renflouement,
    PaiementRenflouement, PenaliteEmprunt, RepartitionRenflouementExercice
)
from .serializers import (
    PaiementInscriptionSerializer, PaiementSolidariteSerializer,
    EpargneTransactionSerializer, EmpruntSerializer, RemboursementSerializer,
    AssistanceAccordeeSerializer, RenflouementSerializer,
    PaiementRenflouementSerializer, StatistiquesTransactionsSerializer,
    PenaliteEmpruntSerializer, EmpruntDetailAvecPenalitesSerializer,
    RepartitionRenflouementExerciceSerializer
)
from authentication.permissions import IsAdministrateur, IsAdminOrReadOnly

class PaiementInscriptionFilter(filters.FilterSet):
    """
    Filtres ultra-complets pour les paiements d'inscription
    """
    # Filtres membre
    membre = filters.UUIDFilter()
    membre_numero = filters.CharFilter(field_name='membre__numero_membre', lookup_expr='icontains')
    membre_nom = filters.CharFilter(method='filter_membre_nom')
    membre_email = filters.CharFilter(field_name='membre__utilisateur__email', lookup_expr='icontains')
    membre_statut = filters.ChoiceFilter(field_name='membre__statut', choices=models.Model.choices if hasattr(models.Model, 'choices') else [])
    
    # Filtres session
    session = filters.UUIDFilter()
    session_nom = filters.CharFilter(field_name='session__nom', lookup_expr='icontains')
    exercice = filters.UUIDFilter(field_name='session__exercice')
    exercice_nom = filters.CharFilter(field_name='session__exercice__nom', lookup_expr='icontains')
    
    # Filtres montants
    montant = filters.NumberFilter()
    montant_min = filters.NumberFilter(field_name='montant', lookup_expr='gte')
    montant_max = filters.NumberFilter(field_name='montant', lookup_expr='lte')
    montant_range = filters.RangeFilter(field_name='montant')
    
    # Filtres dates
    date_paiement = filters.DateFromToRangeFilter()
    date_paiement_after = filters.DateFilter(field_name='date_paiement', lookup_expr='gte')
    date_paiement_before = filters.DateFilter(field_name='date_paiement', lookup_expr='lte')
    month = filters.NumberFilter(field_name='date_paiement', lookup_expr='month')
    year = filters.NumberFilter(field_name='date_paiement', lookup_expr='year')
    today = filters.BooleanFilter(method='filter_today')
    this_week = filters.BooleanFilter(method='filter_this_week')
    this_month = filters.BooleanFilter(method='filter_this_month')
    this_year = filters.BooleanFilter(method='filter_this_year')
    
    # Filtres avancés
    has_notes = filters.BooleanFilter(method='filter_has_notes')
    
    class Meta:
        model = PaiementInscription
        fields = {
            'montant': ['exact', 'gte', 'lte', 'gt', 'lt'],
            'date_paiement': ['exact', 'gte', 'lte', 'year', 'month', 'day'],
            'notes': ['icontains'],
        }
    
    def filter_membre_nom(self, queryset, name, value):
        return queryset.filter(
            Q(membre__utilisateur__first_name__icontains=value) |
            Q(membre__utilisateur__last_name__icontains=value)
        )
    
    def filter_today(self, queryset, name, value):
        from django.utils import timezone
        if value:
            today = timezone.now().date()
            return queryset.filter(date_paiement__date=today)
        return queryset
    
    def filter_this_week(self, queryset, name, value):
        from django.utils import timezone
        from datetime import timedelta
        if value:
            now = timezone.now()
            week_start = now - timedelta(days=now.weekday())
            return queryset.filter(date_paiement__gte=week_start)
        return queryset
    
    def filter_this_month(self, queryset, name, value):
        from django.utils import timezone
        if value:
            now = timezone.now()
            return queryset.filter(
                date_paiement__year=now.year,
                date_paiement__month=now.month
            )
        return queryset
    
    def filter_this_year(self, queryset, name, value):
        from django.utils import timezone
        if value:
            return queryset.filter(date_paiement__year=timezone.now().year)
        return queryset
    
    def filter_has_notes(self, queryset, name, value):
        if value:
            return queryset.exclude(notes='')
        return queryset.filter(notes='')

class PaiementInscriptionViewSet(viewsets.ModelViewSet):
    """
    ViewSet pour les paiements d'inscription
    """
    queryset = PaiementInscription.objects.select_related(
        'membre__utilisateur', 'session__exercice'
    ).all()
    serializer_class = PaiementInscriptionSerializer
    filterset_class = PaiementInscriptionFilter
    search_fields = [
        'membre__numero_membre', 'membre__utilisateur__first_name',
        'membre__utilisateur__last_name', 'session__nom', 'notes'
    ]
    ordering_fields = ['date_paiement', 'montant', 'membre__numero_membre']
    ordering = ['-date_paiement']
    permission_classes = [AllowAny]



class PaiementSolidariteFilter(filters.FilterSet):
    """
    Filtres pour les paiements de solidarité
    """
    # Mêmes filtres que PaiementInscription + spécifiques
    membre = filters.UUIDFilter()
    membre_numero = filters.CharFilter(field_name='membre__numero_membre', lookup_expr='icontains')
    membre_nom = filters.CharFilter(method='filter_membre_nom')
    session = filters.UUIDFilter()
    session_nom = filters.CharFilter(field_name='session__nom', lookup_expr='icontains')
    session_en_cours = filters.BooleanFilter(method='filter_session_en_cours')
    
    montant_min = filters.NumberFilter(field_name='montant', lookup_expr='gte')
    montant_max = filters.NumberFilter(field_name='montant', lookup_expr='lte')
    
    date_paiement = filters.DateFromToRangeFilter()
    this_month = filters.BooleanFilter(method='filter_this_month')
    this_year = filters.BooleanFilter(method='filter_this_year')
    
    class Meta:
        model = PaiementSolidarite
        fields = {
            'montant': ['exact', 'gte', 'lte'],
            'date_paiement': ['exact', 'gte', 'lte', 'year', 'month'],
        }
    
    def filter_membre_nom(self, queryset, name, value):
        return queryset.filter(
            Q(membre__utilisateur__first_name__icontains=value) |
            Q(membre__utilisateur__last_name__icontains=value)
        )
    
    def filter_session_en_cours(self, queryset, name, value):
        if value:
            return queryset.filter(session__statut='EN_COURS')
        return queryset.exclude(session__statut='EN_COURS')
    
    def filter_this_month(self, queryset, name, value):
        from django.utils import timezone
        if value:
            now = timezone.now()
            return queryset.filter(
                date_paiement__year=now.year,
                date_paiement__month=now.month
            )
        return queryset
    
    def filter_this_year(self, queryset, name, value):
        from django.utils import timezone
        if value:
            return queryset.filter(date_paiement__year=timezone.now().year)
        return queryset

class PaiementSolidariteViewSet(viewsets.ModelViewSet):
    """
    ViewSet pour les paiements de solidarité
    """
    queryset = PaiementSolidarite.objects.select_related(
        'membre__utilisateur', 'session'
    ).all()
    serializer_class = PaiementSolidariteSerializer
    filterset_class = PaiementSolidariteFilter
    search_fields = [
        'membre__numero_membre', 'membre__utilisateur__first_name',
        'membre__utilisateur__last_name', 'session__nom'
    ]
    ordering_fields = ['date_paiement', 'montant', 'session__date_session']
    ordering = ['-date_paiement']
    permission_classes = [AllowAny]

class EpargneTransactionFilter(filters.FilterSet):
    """
    Filtres pour les transactions d'épargne
    """
    membre = filters.UUIDFilter()
    membre_numero = filters.CharFilter(field_name='membre__numero_membre', lookup_expr='icontains')
    membre_nom = filters.CharFilter(method='filter_membre_nom')
    
    type_transaction = filters.ChoiceFilter(choices=EpargneTransaction.TYPE_CHOICES)
    type_depot = filters.BooleanFilter(method='filter_type_depot')
    type_retrait = filters.BooleanFilter(method='filter_type_retrait')
    type_interet = filters.BooleanFilter(method='filter_type_interet')
    
    montant_min = filters.NumberFilter(field_name='montant', lookup_expr='gte')
    montant_max = filters.NumberFilter(field_name='montant', lookup_expr='lte')
    montant_positif = filters.BooleanFilter(method='filter_montant_positif')
    montant_negatif = filters.BooleanFilter(method='filter_montant_negatif')
    
    session = filters.UUIDFilter()
    session_nom = filters.CharFilter(field_name='session__nom', lookup_expr='icontains')
    
    date_transaction = filters.DateFromToRangeFilter()
    this_month = filters.BooleanFilter(method='filter_this_month')
    this_year = filters.BooleanFilter(method='filter_this_year')
    
    class Meta:
        model = EpargneTransaction
        fields = {
            'type_transaction': ['exact'],
            'montant': ['exact', 'gte', 'lte', 'gt', 'lt'],
            'date_transaction': ['exact', 'gte', 'lte', 'year', 'month'],
        }
    
    def filter_membre_nom(self, queryset, name, value):
        return queryset.filter(
            Q(membre__utilisateur__first_name__icontains=value) |
            Q(membre__utilisateur__last_name__icontains=value)
        )
    
    def filter_type_depot(self, queryset, name, value):
        if value:
            return queryset.filter(type_transaction='DEPOT')
        return queryset.exclude(type_transaction='DEPOT')
    
    def filter_type_retrait(self, queryset, name, value):
        if value:
            return queryset.filter(type_transaction='RETRAIT_PRET')
        return queryset.exclude(type_transaction='RETRAIT_PRET')
    
    def filter_type_interet(self, queryset, name, value):
        if value:
            return queryset.filter(type_transaction='AJOUT_INTERET')
        return queryset.exclude(type_transaction='AJOUT_INTERET')
    
    def filter_montant_positif(self, queryset, name, value):
        if value:
            return queryset.filter(montant__gt=0)
        return queryset.filter(montant__lte=0)
    
    def filter_montant_negatif(self, queryset, name, value):
        if value:
            return queryset.filter(montant__lt=0)
        return queryset.filter(montant__gte=0)
    
    def filter_this_month(self, queryset, name, value):
        from django.utils import timezone
        if value:
            now = timezone.now()
            return queryset.filter(
                date_transaction__year=now.year,
                date_transaction__month=now.month
            )
        return queryset
    
    def filter_this_year(self, queryset, name, value):
        from django.utils import timezone
        if value:
            return queryset.filter(date_transaction__year=timezone.now().year)
        return queryset

class EpargneTransactionViewSet(viewsets.ModelViewSet):
    """
    ViewSet pour les transactions d'épargne
    """
    queryset = EpargneTransaction.objects.select_related(
        'membre__utilisateur', 'session'
    ).all()
    serializer_class = EpargneTransactionSerializer
    filterset_class = EpargneTransactionFilter
    search_fields = [
        'membre__numero_membre', 'membre__utilisateur__first_name',
        'type_transaction', 'notes'
    ]
    ordering_fields = ['date_transaction', 'montant', 'type_transaction']
    ordering = ['-date_transaction']
    permission_classes = [AllowAny]
    
    @action(detail=False, methods=['get'], permission_classes=[AllowAny])
    def statistiques(self, request):
        try:
            # 1. LOGIQUE ÉPARGNE (Fonds propres des membres)
            # Uniquement ce qui appartient au membre
            TYPES_EPARGNE = ['DEPOT', 'AJOUT_INTERET']
            
            # 2. LOGIQUE TRÉSORERIE (Flux de caisse)
            # Inclut les remboursements qui reviennent dans le coffre
            TYPES_ENTREES_TRESOR = ['DEPOT', 'RETOUR_REMBOURSEMENT']
            

            # 3. Calcul de l'Épargne Totale Globale (Dette de la mutuelle envers les membres)
            total_epargne = EpargneTransaction.objects.filter(
                type_transaction__in=TYPES_EPARGNE,
                montant__gt=0
            ).aggregate(total=Sum('montant'))['total'] or Decimal('0')

            # 4. Calcul du Trésor Total (Cash réellement présent dans le coffre)
            # On additionne les entrées (+) et les sorties (déjà stockées en -)
            total_entrees = EpargneTransaction.objects.filter(
                type_transaction__in=TYPES_ENTREES_TRESOR,
                montant__gt=0
            ).aggregate(total=Sum('montant'))['total'] or Decimal('0')
            
            total_sorties = EpargneTransaction.objects.filter(
                type_transaction='RETRAIT_PRET',
                montant__lt=0  # Sécurité : on prend les montants négatifs
            ).aggregate(total=Sum('montant'))['total'] or Decimal('0')
            
            # Trésor = Entrées (ex: 1M) + Sorties (ex: -485k) = 515k
            tresor_total = total_entrees + total_sorties

            tous_les_membres_query = Membre.objects.annotate(
                total_cumule=Coalesce(
                    Sum(
                        'transactions_epargne__montant',
                        filter=Q(
                            transactions_epargne__type_transaction__in=TYPES_EPARGNE,
                            transactions_epargne__montant__gt=0
                        )
                    ),
                    Decimal('0'),
                    output_field=DecimalField()
                )
            ).select_related('utilisateur').order_by('-total_cumule')

            membres_data = []
            for m in tous_les_membres_query:
                # Gestion du nom
                nom = "Membre Inconnu"
                if m.utilisateur:
                    nom = getattr(m.utilisateur, 'nom_complet', None) or \
                          f"{m.utilisateur.first_name} {m.utilisateur.last_name}".strip() or \
                          m.utilisateur.username

                membres_data.append({
                    "id": m.id,
                    "nom": nom,
                    "montant": float(m.total_cumule), # Somme DEPOT + INTERET
                    "numero": m.numero_membre,
                    "statut": str(m.statut) # Convertit le statut (ex: NON_DEFINI) en texte
                })

            return Response({
                "epargne_totale": float(total_epargne),
                "tresor_total": float(tresor_total),
                "tous_les_membres": membres_data, # Liste pour l'onglet Membres
                "top_epargnants": membres_data[:5], # Les 5 meilleurs pour l'Overview
                "total_membres": len(membres_data),
                "transactions_ce_mois": EpargneTransaction.objects.filter(
                    date_transaction__month=timezone.now().month,
                    date_transaction__year=timezone.now().year
                ).count()
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response(
                {"error": "Erreur lors du calcul des stats", "details": str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
            

class EmpruntFilter(filters.FilterSet):
    """
    Filtres ultra-complets pour les emprunts
    """
    membre = filters.UUIDFilter()
    membre_numero = filters.CharFilter(field_name='membre__numero_membre', lookup_expr='icontains')
    membre_nom = filters.CharFilter(method='filter_membre_nom')
    
    statut = filters.ChoiceFilter(choices=Emprunt.STATUS_CHOICES)
    en_cours = filters.BooleanFilter(method='filter_en_cours')
    rembourse = filters.BooleanFilter(method='filter_rembourse')
    en_retard = filters.BooleanFilter(method='filter_en_retard')
    
    # Filtres montants
    montant_emprunte_min = filters.NumberFilter(field_name='montant_emprunte', lookup_expr='gte')
    montant_emprunte_max = filters.NumberFilter(field_name='montant_emprunte', lookup_expr='lte')
    montant_total_min = filters.NumberFilter(field_name='montant_total_a_rembourser', lookup_expr='gte')
    montant_total_max = filters.NumberFilter(field_name='montant_total_a_rembourser', lookup_expr='lte')
    montant_rembourse_min = filters.NumberFilter(field_name='montant_rembourse', lookup_expr='gte')
    montant_rembourse_max = filters.NumberFilter(field_name='montant_rembourse', lookup_expr='lte')
    
    # Filtres taux
    taux_interet_min = filters.NumberFilter(field_name='taux_interet', lookup_expr='gte')
    taux_interet_max = filters.NumberFilter(field_name='taux_interet', lookup_expr='lte')
    
    # Filtres pourcentages
    pourcentage_rembourse_min = filters.NumberFilter(method='filter_pourcentage_min')
    pourcentage_rembourse_max = filters.NumberFilter(method='filter_pourcentage_max')
    presque_rembourse = filters.BooleanFilter(method='filter_presque_rembourse')  # >80%
    peu_rembourse = filters.BooleanFilter(method='filter_peu_rembourse')  # <20%
    
    # Filtres dates
    date_emprunt = filters.DateFromToRangeFilter()
    this_month = filters.BooleanFilter(method='filter_this_month')
    this_year = filters.BooleanFilter(method='filter_this_year')
    
    # Filtres session
    session_emprunt = filters.UUIDFilter()
    session_nom = filters.CharFilter(field_name='session_emprunt__nom', lookup_expr='icontains')
    
    class Meta:
        model = Emprunt
        fields = {
            'statut': ['exact'],
            'montant_emprunte': ['exact', 'gte', 'lte'],
            'montant_total_a_rembourser': ['exact', 'gte', 'lte'],
            'montant_rembourse': ['exact', 'gte', 'lte'],
            'taux_interet': ['exact', 'gte', 'lte'],
            'date_emprunt': ['exact', 'gte', 'lte', 'year', 'month'],
        }
    
    def filter_membre_nom(self, queryset, name, value):
        return queryset.filter(
            Q(membre__utilisateur__first_name__icontains=value) |
            Q(membre__utilisateur__last_name__icontains=value)
        )
    
    def filter_en_cours(self, queryset, name, value):
        if value:
            return queryset.filter(statut='EN_COURS')
        return queryset.exclude(statut='EN_COURS')
    
    def filter_rembourse(self, queryset, name, value):
        if value:
            return queryset.filter(statut='REMBOURSE')
        return queryset.exclude(statut='REMBOURSE')
    
    def filter_en_retard(self, queryset, name, value):
        if value:
            return queryset.filter(statut='EN_RETARD')
        return queryset.exclude(statut='EN_RETARD')
    
    def filter_pourcentage_min(self, queryset, name, value):
        return queryset.filter(
            montant_rembourse__gte=F('montant_total_a_rembourser') * value / 100
        )
    
    def filter_pourcentage_max(self, queryset, name, value):
        return queryset.filter(
            montant_rembourse__lte=F('montant_total_a_rembourser') * value / 100
        )
    
    def filter_presque_rembourse(self, queryset, name, value):
        if value:
            return queryset.filter(
                montant_rembourse__gte=F('montant_total_a_rembourser') * 0.8
            )
        return queryset
    
    def filter_peu_rembourse(self, queryset, name, value):
        if value:
            return queryset.filter(
                montant_rembourse__lte=F('montant_total_a_rembourser') * 0.2
            )
        return queryset
    
    def filter_this_month(self, queryset, name, value):
        from django.utils import timezone
        if value:
            now = timezone.now()
            return queryset.filter(
                date_emprunt__year=now.year,
                date_emprunt__month=now.month
            )
        return queryset
    
    def filter_this_year(self, queryset, name, value):
        from django.utils import timezone
        if value:
            return queryset.filter(date_emprunt__year=timezone.now().year)
        return queryset



class EmpruntViewSet(viewsets.ModelViewSet):
    """
    ViewSet pour les emprunts avec TOUS LES CALCULS
    """
    queryset = Emprunt.objects.select_related(
        'membre__utilisateur', 'session_emprunt'
    ).prefetch_related('remboursements').all()
    serializer_class = EmpruntSerializer
    filterset_class = EmpruntFilter
    search_fields = [
        'membre__numero_membre', 'membre__utilisateur__first_name',
        'membre__utilisateur__last_name', 'notes'
    ]
    ordering_fields = [
        'date_emprunt', 'montant_emprunte', 'montant_total_a_rembourser',
        'montant_rembourse', 'taux_interet'
    ]
    ordering = ['-date_emprunt']
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        print("=" * 80)
        print("🔍 CRÉATION EMPRUNT - DÉBUT")
        print(f"📡 User: {request.user}")
        print(f"📡 Data reçue: {request.data}")
        print(f"📡 Headers: {dict(request.headers)}")
        print(f"📡 Method: {request.method}")
        
        try:
            # 🔧 VALIDATION DES DONNÉES D'ENTRÉE
            data = request.data.copy()
            
            # Vérifier les champs obligatoires
            required_fields = ['membre', 'montant_emprunte']
            missing_fields = []
            
            for field in required_fields:
                if field not in data or not data.get(field):
                    missing_fields.append(field)
            
            if missing_fields:
                error_msg = f"Champs obligatoires manquants: {', '.join(missing_fields)}"
                print(f"❌ ERREUR VALIDATION: {error_msg}")
                return Response({
                    'error': 'Données manquantes',
                    'details': error_msg,
                    'missing_fields': missing_fields,
                    'data_received': data
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # 🔧 VALIDATION DU MEMBRE
            membre_id = data.get('membre')
            print(f"🔍 Vérification membre ID: {membre_id}")
            
            try:
                from core.models import Membre
                membre = Membre.objects.select_related('utilisateur').get(id=membre_id)
                print(f"✅ Membre trouvé: {membre.numero_membre} - {membre.utilisateur.nom_complet}")
                print(f"   - Statut: {membre.statut}")
                print(f"   - Actif: {membre.is_actif}")

                # ✅ NOUVEAU : Tous les membres actifs peuvent emprunter
                if not membre.is_actif:
                    error_msg = f"Le membre {membre.numero_membre} est inactif"
                    print(f"❌ ERREUR MEMBRE INACTIF: {error_msg}")
                    return Response({
                        'error': 'Membre inactif',
                        'details': error_msg
                    }, status=status.HTTP_400_BAD_REQUEST)

                # Vérifier s'il a déjà un emprunt en cours
                emprunt_en_cours = Emprunt.objects.filter(
                    membre=membre,
                    statut__in=['EN_COURS', 'EN_RETARD']
                ).exists()

                if emprunt_en_cours:
                    error_msg = f"Le membre {membre.numero_membre} a déjà un emprunt en cours"
                    print(f"❌ ERREUR EMPRUNT EN COURS: {error_msg}")
                    return Response({
                        'error': 'Emprunt déjà en cours',
                        'details': error_msg
                    }, status=status.HTTP_400_BAD_REQUEST)
                
            except Membre.DoesNotExist:
                error_msg = f"Membre avec ID {membre_id} introuvable"
                print(f"❌ ERREUR MEMBRE: {error_msg}")
                return Response({
                    'error': 'Membre non trouvé',
                    'details': error_msg,
                    'membre_id': membre_id
                }, status=status.HTTP_404_NOT_FOUND)
            except Exception as e:
                print(f"❌ ERREUR RÉCUPÉRATION MEMBRE: {str(e)}")
                return Response({
                    'error': 'Erreur lors de la vérification du membre',
                    'details': str(e)
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
            # 🔧 VALIDATION DU MONTANT
            montant_str = data.get('montant_emprunte')
            print(f"🔍 Validation montant: {montant_str} (type: {type(montant_str)})")
            
            try:
                montant_emprunte = Decimal(str(montant_str))
                print(f"✅ Montant converti: {montant_emprunte}")
                
                if montant_emprunte <= 0:
                    error_msg = "Le montant doit être positif"
                    print(f"❌ ERREUR MONTANT: {error_msg}")
                    return Response({
                        'error': 'Montant invalide',
                        'details': error_msg,
                        'montant_recu': montant_str
                    }, status=status.HTTP_400_BAD_REQUEST)
                
            
                
            except (InvalidOperation, TypeError, ValueError) as e:
                error_msg = f"Montant invalide: {e}"
                print(f"❌ ERREUR CONVERSION MONTANT: {error_msg}")
                return Response({
                    'error': 'Montant invalide',
                    'details': error_msg,
                    'montant_recu': montant_str
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # 🔧 VALIDATION DE LA SESSION
            session_id = data.get('session')
            if not session_id:
                # Auto-assigner la session courante
                from core.models import Session
                current_session = Session.objects.filter(statut='EN_COURS').first()
                if current_session:
                    data['session'] = current_session.id
                    print(f"✅ Session auto-assignée: {current_session.nom}")
                else:
                    error_msg = "Aucune session active disponible"
                    print(f"❌ ERREUR SESSION: {error_msg}")
                    return Response({
                        'error': 'Session manquante',
                        'details': error_msg
                    }, status=status.HTTP_400_BAD_REQUEST)
            else:
                try:
                    from core.models import Session
                    session = Session.objects.get(id=session_id)
                    print(f"✅ Session trouvée: {session.nom}")
                except Session.DoesNotExist:
                    error_msg = f"Session avec ID {session_id} introuvable"
                    print(f"❌ ERREUR SESSION: {error_msg}")
                    return Response({
                        'error': 'Session non trouvée',
                        'details': error_msg,
                        'session_id': session_id
                    }, status=status.HTTP_404_NOT_FOUND)
            
            # 🔧 VÉRIFICATION DES LIQUIDITÉS
            try:
                from core.models import FondsSocial
                fonds = FondsSocial.get_fonds_actuel()
                if fonds:
                    liquidites_disponibles = fonds.montant_total
                    print(f"🔍 Liquidités disponibles: {liquidites_disponibles}")
                    
                    if montant_emprunte > liquidites_disponibles:
                        error_msg = f"Liquidités insuffisantes ({liquidites_disponibles}) pour ce prêt ({montant_emprunte})"
                        print(f"⚠️ ATTENTION LIQUIDITÉS: {error_msg}")
                        # Note: On peut continuer mais alerter l'admin
                else:
                    print("⚠️ Aucun fonds social trouvé")
            except Exception as e:
                print(f"⚠️ Erreur vérification liquidités: {e}")
            
            # 🔧 VALIDATION AVEC SERIALIZER
            print(f"🔍 Data finale pour serializer: {data}")
            serializer = self.get_serializer(data=data)
            
            print(f"🔍 Validation du serializer...")
            if not serializer.is_valid():
                print(f"❌ ERREURS SERIALIZER: {serializer.errors}")
                print(f"❌ ERREURS DÉTAILLÉES:")
                for field, errors in serializer.errors.items():
                    print(f"   - {field}: {errors}")
                
                return Response({
                    'error': 'Données invalides',
                    'details': serializer.errors,
                    'data_received': data
                }, status=status.HTTP_400_BAD_REQUEST)
            
            print(f"✅ Serializer valide, validated_data: {serializer.validated_data}")
            
            # 🔧 CRÉATION AVEC TRANSACTION
            try:
                print("🔍 Début de la création...")
                
                with transaction.atomic():
                    print("🔍 Appel perform_create...")
                    self.perform_create(serializer)
                    
                    emprunt = serializer.instance
                    print(f"✅ Emprunt créé avec succès:")
                    print(f"   - ID: {emprunt.id}")
                    print(f"   - Membre: {emprunt.membre.numero_membre}")
                    print(f"   - Montant: {emprunt.montant_emprunte}")
                    print(f"   - Total à rembourser: {emprunt.montant_total_a_rembourser}")
                    print(f"   - Taux intérêt: {emprunt.taux_interet}%")
                    print(f"   - Session: {emprunt.session_emprunt.nom}")
                    print(f"   - Date: {emprunt.date_emprunt}")
                    print(f"   - Statut: {emprunt.statut}")
                
                print("✅ EMPRUNT CRÉÉ AVEC SUCCÈS")
                print("=" * 80)
                
                return Response(serializer.data, status=status.HTTP_201_CREATED)
                
            except Exception as e:
                print(f"❌ EXCEPTION CRÉATION: {str(e)}")
                print(f"❌ EXCEPTION TYPE: {type(e)}")
                import traceback
                print(f"❌ TRACEBACK COMPLET:")
                print(traceback.format_exc())
                print("=" * 80)
                
                return Response({
                    'error': 'Erreur lors de la création de l\'emprunt',
                    'details': str(e),
                    'type': str(type(e))
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                
        except Exception as e:
            print(f"❌ EXCEPTION GÉNÉRALE: {str(e)}")
            print(f"❌ EXCEPTION TYPE: {type(e)}")
            import traceback
            print(f"❌ TRACEBACK COMPLET:")
            print(traceback.format_exc())
            print("=" * 80)
            
            return Response({
                'error': 'Erreur interne du serveur',
                'details': str(e),
                'type': str(type(e))
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def perform_create(self, serializer):
        """Création personnalisée avec calculs automatiques"""
        print("🔍 PERFORM_CREATE - Début")
        try:
            validated_data = serializer.validated_data
            
            # Auto-assigner la date si manquante
            if 'date_emprunt' not in validated_data:
                validated_data['date_emprunt'] = timezone.now().date()
                print(f"✅ Date auto-assignée: {validated_data['date_emprunt']}")
            
            # 🔧 AUTO-CALCUL DU TAUX D'INTÉRÊT
            if 'taux_interet' not in validated_data or not validated_data.get('taux_interet'):
                from core.models import ConfigurationMutuelle
                config = ConfigurationMutuelle.get_configuration()
                validated_data['taux_interet'] = config.taux_interet
                print(f"✅ Taux d'intérêt auto-assigné: {config.taux_interet}%")
            
            # 🔧 AUTO-CALCUL DU MONTANT TOTAL À REMBOURSER
            if 'montant_total_a_rembourser' not in validated_data or not validated_data.get('montant_total_a_rembourser'):
                montant_emprunte = validated_data['montant_emprunte']
                taux_interet = validated_data['taux_interet']
                
                # Calcul : montant + (montant * taux / 100)
                montant_interets = montant_emprunte * (taux_interet / Decimal('100'))
                montant_total = montant_emprunte + montant_interets
                
                validated_data['montant_total_a_rembourser'] = montant_total
                print(f"✅ Montant total calculé: {montant_emprunte} + {montant_interets} = {montant_total}")
            
            # 🔧 AUTO-ASSIGNATION DE LA SESSION
            if 'session_emprunt' not in validated_data or not validated_data.get('session_emprunt'):
                from core.models import Session
                current_session = Session.objects.filter(statut='EN_COURS').first()
                if current_session:
                    validated_data['session_emprunt'] = current_session
                    print(f"✅ Session auto-assignée: {current_session.nom}")
                else:
                    raise ValueError("Aucune session en cours disponible")
            
            print(f"🔍 Données finales pour création: {validated_data}")
            
            # Sauvegarder avec les données calculées
            instance = serializer.save(**validated_data)
            print(f"✅ PERFORM_CREATE - Instance sauvée: {instance}")
            return instance
            
        except Exception as e:
            print(f"❌ PERFORM_CREATE - Erreur: {e}")
            import traceback
            print(f"❌ PERFORM_CREATE - Traceback: {traceback.format_exc()}")
            raise
        
    
class RenflouementFilter(filters.FilterSet):
    """
    Filtres pour les renflouements
    """
    membre = filters.UUIDFilter()
    membre_numero = filters.CharFilter(field_name='membre__numero_membre', lookup_expr='icontains')
    membre_nom = filters.CharFilter(method='filter_membre_nom')
    
    session = filters.UUIDFilter()
    session_nom = filters.CharFilter(field_name='session__nom', lookup_expr='icontains')
    
    type_cause = filters.ChoiceFilter(choices=Renflouement.TYPE_CAUSE_CHOICES)
    cause_assistance = filters.BooleanFilter(method='filter_cause_assistance')
    cause_collation = filters.BooleanFilter(method='filter_cause_collation')
    
    # Filtres statuts
    solde = filters.BooleanFilter(method='filter_solde')
    non_solde = filters.BooleanFilter(method='filter_non_solde')
    partiellement_paye = filters.BooleanFilter(method='filter_partiellement_paye')
    
    # Filtres montants
    montant_du_min = filters.NumberFilter(field_name='montant_du', lookup_expr='gte')
    montant_du_max = filters.NumberFilter(field_name='montant_du', lookup_expr='lte')
    montant_paye_min = filters.NumberFilter(field_name='montant_paye', lookup_expr='gte')
    montant_paye_max = filters.NumberFilter(field_name='montant_paye', lookup_expr='lte')
    
    # Filtres dates
    date_creation = filters.DateFromToRangeFilter()
    this_month = filters.BooleanFilter(method='filter_this_month')
    this_year = filters.BooleanFilter(method='filter_this_year')
    
    class Meta:
        model = Renflouement
        fields = {
            'type_cause': ['exact'],
            'montant_du': ['exact', 'gte', 'lte'],
            'montant_paye': ['exact', 'gte', 'lte'],
            'date_creation': ['exact', 'gte', 'lte', 'year', 'month'],
        }
    
    def filter_membre_nom(self, queryset, name, value):
        return queryset.filter(
            Q(membre__utilisateur__first_name__icontains=value) |
            Q(membre__utilisateur__last_name__icontains=value)
        )
    
    def filter_cause_assistance(self, queryset, name, value):
        if value:
            return queryset.filter(type_cause='ASSISTANCE')
        return queryset.exclude(type_cause='ASSISTANCE')
    
    def filter_cause_collation(self, queryset, name, value):
        if value:
            return queryset.filter(type_cause='COLLATION')
        return queryset.exclude(type_cause='COLLATION')
    
    def filter_solde(self, queryset, name, value):
        if value:
            return queryset.filter(montant_paye__gte=F('montant_du'))
        return queryset.filter(montant_paye__lt=F('montant_du'))
    
    def filter_non_solde(self, queryset, name, value):
        if value:
            return queryset.filter(montant_paye__lt=F('montant_du'))
        return queryset.filter(montant_paye__gte=F('montant_du'))
    
    def filter_partiellement_paye(self, queryset, name, value):
        if value:
            return queryset.filter(
                montant_paye__gt=0,
                montant_paye__lt=F('montant_du')
            )
        return queryset
    
    def filter_this_month(self, queryset, name, value):
        from django.utils import timezone
        if value:
            now = timezone.now()
            return queryset.filter(
                date_creation__year=now.year,
                date_creation__month=now.month
            )
        return queryset
    
    def filter_this_year(self, queryset, name, value):
        from django.utils import timezone
        if value:
            return queryset.filter(date_creation__year=timezone.now().year)
        return queryset

class RenflouementViewSet(viewsets.ModelViewSet):
    """
    ViewSet pour les renflouements avec TOUS LES CALCULS
    """
    queryset = Renflouement.objects.select_related(
        'membre__utilisateur', 'session'
    ).prefetch_related('paiements').all()
    serializer_class = RenflouementSerializer
    filterset_class = RenflouementFilter
    search_fields = [
        'membre__numero_membre', 'membre__utilisateur__first_name',
        'cause', 'type_cause'
    ]
    ordering_fields = [
        'date_creation', 'montant_du', 'montant_paye', 'type_cause'
    ]
    ordering = ['-date_creation']
    permission_classes = [AllowAny]
    
    @action(detail=False, methods=['get'], permission_classes=[AllowAny])
    def statistiques(self, request):
        """
        Statistiques des renflouements
        """
        queryset = self.get_queryset()
        
        total_renflouements = queryset.count()
        renflouements_soldes = queryset.filter(montant_paye__gte=F('montant_du')).count()
        renflouements_non_soldes = total_renflouements - renflouements_soldes
        
        montant_total_du = queryset.aggregate(
            total=Sum('montant_du'))['total'] or Decimal('0')
        montant_total_paye = queryset.aggregate(
            total=Sum('montant_paye'))['total'] or Decimal('0')
        montant_restant = montant_total_du - montant_total_paye
        
        return Response({
            'nombre_renflouements': {
                'total': total_renflouements,
                'soldes': renflouements_soldes,
                'non_soldes': renflouements_non_soldes
            },
            'montants': {
                'total_du': montant_total_du,
                'total_paye': montant_total_paye,
                'montant_restant': montant_restant
            },
            'pourcentages': {
                'taux_recouvrement': (montant_total_paye / montant_total_du * 100) if montant_total_du > 0 else 0,
                'taux_solde': (renflouements_soldes / total_renflouements * 100) if total_renflouements > 0 else 0
            }
        })

# ViewSets similaires pour les autres modèles...
class RemboursementViewSet(viewsets.ModelViewSet):
    queryset = Remboursement.objects.select_related('emprunt__membre__utilisateur', 'session').all()
    serializer_class = RemboursementSerializer
    filterset_fields = ['emprunt', 'session', 'montant']
    search_fields = ['emprunt__membre__numero_membre', 'notes']
    ordering = ['-date_remboursement']
    permission_classes = [AllowAny]

logger = logging.getLogger(__name__)

class AssistanceAccordeeViewSet(viewsets.ModelViewSet):
    queryset = AssistanceAccordee.objects.select_related(
        'membre__utilisateur', 'type_assistance', 'session'
    ).all()
    serializer_class = AssistanceAccordeeSerializer
    filterset_fields = ['membre', 'type_assistance', 'statut', 'session']
    search_fields = ['membre__numero_membre', 'justification', 'notes']
    ordering = ['-date_demande']
    permission_classes = [AllowAny]

    @action(detail=False, methods=['get'], permission_classes=[AllowAny])
    def par_membre(self, request):
        """
        Récupère toutes les assistances accordées à un membre spécifique
        Paramètre query: membre_id (UUID)
        """
        membre_id = request.query_params.get('membre_id')
        
        if not membre_id:
            return Response(
                {'error': 'Le paramètre membre_id est requis'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            membre = Membre.objects.get(id=membre_id)
        except Membre.DoesNotExist:
            return Response(
                {'error': f'Membre avec l\'ID {membre_id} non trouvé'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Récupérer toutes les assistances du membre
        assistances = AssistanceAccordee.objects.filter(
            membre=membre
        ).select_related('type_assistance', 'session').order_by('-date_demande')
        
        # Calculer les statistiques
        total_assistances = assistances.count()
        montant_total = assistances.aggregate(total=Sum('montant'))['total'] or Decimal('0')
        
        # Grouper par type d'assistance
        assistances_par_type = {}
        for assistance in assistances:
            type_nom = assistance.type_assistance.nom
            if type_nom not in assistances_par_type:
                assistances_par_type[type_nom] = {
                    'type': type_nom,
                    'montant_total': Decimal('0'),
                    'nombre': 0,
                    'assistances': []
                }
            
            assistances_par_type[type_nom]['montant_total'] += assistance.montant
            assistances_par_type[type_nom]['nombre'] += 1
            assistances_par_type[type_nom]['assistances'].append({
                'id': str(assistance.id),
                'montant': float(assistance.montant),
                'type_assistance': assistance.type_assistance.nom,
                'session': assistance.session.nom if assistance.session else None,
                'date_demande': assistance.date_demande,
                'date_paiement': assistance.date_paiement,
                'statut': assistance.statut,
                'justification': assistance.justification,
                'notes': assistance.notes
            })
        
        # Convertir les montants en float pour le JSON
        for type_data in assistances_par_type.values():
            type_data['montant_total'] = float(type_data['montant_total'])
        
        # Grouper par statut
        assistances_par_statut = {}
        for assistance in assistances:
            statut = assistance.get_statut_display()
            if statut not in assistances_par_statut:
                assistances_par_statut[statut] = {
                    'statut': statut,
                    'montant_total': Decimal('0'),
                    'nombre': 0
                }
            
            assistances_par_statut[statut]['montant_total'] += assistance.montant
            assistances_par_statut[statut]['nombre'] += 1
        
        # Convertir les montants en float pour le JSON
        for statut_data in assistances_par_statut.values():
            statut_data['montant_total'] = float(statut_data['montant_total'])
        
        # Sérialiser les assistances
        serializer = self.get_serializer(assistances, many=True)
        
        return Response({
            'membre': {
                'id': str(membre.id),
                'numero_membre': membre.numero_membre,
                'nom_complet': membre.utilisateur.nom_complet if membre.utilisateur else 'Inconnu',
                'email': membre.utilisateur.email if membre.utilisateur else None
            },
            'statistiques': {
                'total_assistances': total_assistances,
                'montant_total': float(montant_total),
                'assistances_par_type': assistances_par_type,
                'assistances_par_statut': assistances_par_statut
            },
            'assistances': serializer.data
        }, status=status.HTTP_200_OK)

    def create(self, request, *args, **kwargs):
        print("ASSISTANCE CREATE - Data reçue:", request.data)
        
        # 🔧 AUTO-AJOUTER LA SESSION COURANTE SI MANQUANTE
        data = request.data.copy()
        if 'session' not in data or not data['session']:
            try:
                from core.models import Session
                current_session = Session.objects.filter(statut='EN_COURS').first()
                if current_session:
                    data['session'] = current_session.id
                    print(f"Session courante ajoutée automatiquement: {current_session.id}")
                else:
                    print("ERREUR: Aucune session active trouvée")
                    return Response({
                        'error': 'Aucune session active disponible'
                    }, status=status.HTTP_400_BAD_REQUEST)
            except Exception as e:
                print(f"ERREUR lors de la récupération de session: {e}")
        
        # 🔍 VÉRIFICATION DES FOREIGN KEYS AVANT CRÉATION
        try:
            print(f"🔍 Vérification membre ID: {data.get('membre')}")
            membre = Membre.objects.get(id=data.get('membre'))
            print(f"✅ Membre trouvé: {membre}")
            
            print(f"🔍 Vérification type_assistance ID: {data.get('type_assistance')}")
            type_assistance = TypeAssistance.objects.get(id=data.get('type_assistance'))
            print(f"✅ Type assistance trouvé: {type_assistance}")
            
            print(f"🔍 Vérification session ID: {data.get('session')}")
            session = Session.objects.get(id=data.get('session'))
            print(f"✅ Session trouvée: {session}")
            
        except Exception as e:
            print(f"❌ ERREUR Foreign Key: {e}")
            return Response({
                'error': f'Objet non trouvé: {str(e)}'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        serializer = self.get_serializer(data=data)
        if not serializer.is_valid():
            print("ASSISTANCE ERRORS:", serializer.errors)
            return Response({
                'error': 'Données invalides',
                'details': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            print("🔍 Début de la création...")
            
            # 🔧 UTILISE UNE TRANSACTION POUR ISOLER L'ERREUR
            with transaction.atomic():
                print("🔍 Appel perform_create...")
                assistance = serializer.save()
                print(f"✅ AssistanceAccordee créée avec ID: {assistance.id}")
                
                # 🔍 VÉRIFICATION POST-CRÉATION
                print("🔍 Vérification post-création...")
                created_assistance = AssistanceAccordee.objects.get(id=assistance.id)
                print(f"✅ Assistance vérifiée: {created_assistance}")
                
            print("✅ ASSISTANCE CREATED:", serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            print(f"❌ ASSISTANCE EXCEPTION: {str(e)}")
            print(f"❌ EXCEPTION TYPE: {type(e)}")
            import traceback
            print(f"❌ TRACEBACK: {traceback.format_exc()}")
            
            return Response({
                'error': 'Erreur lors de la création',
                'details': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
class PaiementRenflouementViewSet(viewsets.ModelViewSet):
    queryset = PaiementRenflouement.objects.select_related(
        'renflouement__membre__utilisateur', 'session'
    ).all()
    serializer_class = PaiementRenflouementSerializer
    filterset_fields = ['renflouement', 'session', 'montant']
    search_fields = ['renflouement__membre__numero_membre', 'notes']
    ordering = ['-date_paiement']
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        print("=" * 60)
        print("🔍 PAIEMENT RENFLOUEMENT CREATE")
        print(f"📡 Data reçue: {request.data}")
        print(f"👤 User: {request.user}")
        print(f"🔗 Headers: {dict(request.headers)}")
        
        # 🔍 VÉRIFICATION DES FOREIGN KEYS AVANT CRÉATION
        data = request.data.copy()
        
        try:
            # Vérifier le renflouement
            if 'renflouement' in data:
                print(f"🔍 Vérification renflouement ID: {data.get('renflouement')}")
                renflouement = Renflouement.objects.get(id=data.get('renflouement'))
                print(f"✅ Renflouement trouvé: {renflouement}")
                print(f"   - Membre: {renflouement.membre.numero_membre}")
                print(f"   - Montant dû: {renflouement.montant_du}")
                print(f"   - Cause: {renflouement.cause}")
            
            # Vérifier la session
            if 'session' in data:
                print(f"🔍 Vérification session ID: {data.get('session')}")
                session = Session.objects.get(id=data.get('session'))
                print(f"✅ Session trouvée: {session}")
            elif not data.get('session'):
                # Auto-assigner la session courante si manquante
                current_session = Session.objects.filter(statut="EN_COURS").first()
                if current_session:
                    data['session'] = current_session.id
                    print(f"✅ Session auto-assignée: {current_session.nom}")
                else:
                    print("❌ Aucune session active trouvée")
                    return Response({
                        'error': 'Aucune session active disponible'
                    }, status=status.HTTP_400_BAD_REQUEST)
            
            # Vérifier le montant
            montant = data.get('montant')
            print(f"🔍 Montant: {montant} (type: {type(montant)})")
            if montant:
                try:
                    montant_decimal = Decimal(str(montant))
                    print(f"✅ Montant converti: {montant_decimal}")
                except Exception as e:
                    print(f"❌ Erreur conversion montant: {e}")
                    return Response({
                        'error': f'Montant invalide: {e}'
                    }, status=status.HTTP_400_BAD_REQUEST)
            
        except Exception as e:
            print(f"❌ ERREUR Foreign Key: {e}")
            print(f"❌ Type erreur: {type(e)}")
            import traceback
            print(f"❌ Traceback: {traceback.format_exc()}")
            return Response({
                'error': f'Objet non trouvé: {str(e)}'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # 🔍 VALIDATION AVEC SERIALIZER
        print(f"🔍 Data finale envoyée au serializer: {data}")
        serializer = self.get_serializer(data=data)
        
        print(f"🔍 Validation du serializer...")
        if not serializer.is_valid():
            print(f"❌ ERREURS SERIALIZER: {serializer.errors}")
            print(f"❌ ERREURS DÉTAILLÉES:")
            for field, errors in serializer.errors.items():
                print(f"   - {field}: {errors}")
            
            return Response({
                'error': 'Données invalides',
                'details': serializer.errors,
                'data_received': data
            }, status=status.HTTP_400_BAD_REQUEST)
        
        print(f"✅ Serializer valide, validated_data: {serializer.validated_data}")
        
        # 🔍 CRÉATION
        try:
            print("🔍 Début de la création...")
            
            # Utiliser une transaction pour isoler l'erreur
            from django.db import transaction
            with transaction.atomic():
                print("🔍 Appel perform_create...")
                self.perform_create(serializer)
                print(f"✅ PaiementRenflouement créé avec succès")
                
            print("✅ PAIEMENT RENFLOUEMENT CREATED:")
            print(f"   Data: {serializer.data}")
            print("=" * 60)
            
            return Response(serializer.data, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            print(f"❌ EXCEPTION CRÉATION: {str(e)}")
            print(f"❌ EXCEPTION TYPE: {type(e)}")
            import traceback
            print(f"❌ TRACEBACK COMPLET:")
            print(traceback.format_exc())
            print("=" * 60)
            
            return Response({
                'error': 'Erreur lors de la création',
                'details': str(e),
                'type': str(type(e))
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class PenaliteEmpruntFilter(filters.FilterSet):
    """
    Filtres pour les pénalités d'emprunt
    """
    # Filtres par emprunt
    emprunt = filters.UUIDFilter()
    membre_numero = filters.CharFilter(field_name='emprunt__membre__numero_membre', lookup_expr='icontains')
    membre_nom = filters.CharFilter(method='filter_membre_nom')
    
    # Filtres par type et palier
    type_penalite = filters.ChoiceFilter(choices=PenaliteEmprunt.TYPE_PENALITE_CHOICES)
    palier = filters.CharFilter(lookup_expr='icontains')
    sessions_ecoulees = filters.NumberFilter()
    sessions_ecoulees_min = filters.NumberFilter(field_name='sessions_ecoulees', lookup_expr='gte')
    sessions_ecoulees_max = filters.NumberFilter(field_name='sessions_ecoulees', lookup_expr='lte')
    
    # Filtres par montant
    montant_min = filters.NumberFilter(field_name='montant_total_penalite', lookup_expr='gte')
    montant_max = filters.NumberFilter(field_name='montant_total_penalite', lookup_expr='lte')
    
    # Filtres par date
    date_application = filters.DateFilter()
    date_application_after = filters.DateFilter(field_name='date_application', lookup_expr='gte')
    date_application_before = filters.DateFilter(field_name='date_application', lookup_expr='lte')
    
    # Filtres par session
    session_application = filters.UUIDFilter()
    
    # Filtres par qui a appliqué
    appliquee_par = filters.UUIDFilter()
    automatique = filters.BooleanFilter(method='filter_automatique')
    
    # Filtres temporels rapides
    this_month = filters.BooleanFilter(method='filter_this_month')
    this_year = filters.BooleanFilter(method='filter_this_year')
    
    class Meta:
        model = PenaliteEmprunt
        fields = [
            'emprunt', 'type_penalite', 'palier', 'sessions_ecoulees',
            'session_application', 'appliquee_par'
        ]
    
    def filter_membre_nom(self, queryset, name, value):
        """Filtre par nom du membre"""
        return queryset.filter(
            Q(emprunt__membre__utilisateur__first_name__icontains=value) |
            Q(emprunt__membre__utilisateur__last_name__icontains=value)
        )
    
    def filter_automatique(self, queryset, name, value):
        """Filtre les pénalités automatiques (appliquee_par = NULL)"""
        if value:
            return queryset.filter(appliquee_par__isnull=True)
        else:
            return queryset.filter(appliquee_par__isnull=False)
    
    def filter_this_month(self, queryset, name, value):
        """Filtre les pénalités de ce mois"""
        if value:
            from django.utils import timezone
            now = timezone.now()
            return queryset.filter(
                date_application__year=now.year,
                date_application__month=now.month
            )
        return queryset
    
    def filter_this_year(self, queryset, name, value):
        """Filtre les pénalités de cette année"""
        if value:
            from django.utils import timezone
            now = timezone.now()
            return queryset.filter(date_application__year=now.year)
        return queryset


class PenaliteEmpruntViewSet(viewsets.ModelViewSet):
    """
    ViewSet pour les pénalités d'emprunt - Transparence totale
    """
    queryset = PenaliteEmprunt.objects.all()
    serializer_class = PenaliteEmpruntSerializer
    permission_classes = [IsAdminOrReadOnly]
    filterset_class = PenaliteEmpruntFilter
    ordering = ['-date_application']
    
    def get_queryset(self):
        """Optimisation des requêtes avec select_related"""
        return PenaliteEmprunt.objects.select_related(
            'emprunt__membre__utilisateur',
            'session_application',
            'appliquee_par'
        ).prefetch_related(
            'emprunt__remboursements'
        )
    
    @action(detail=False, methods=['get'])
    def statistiques(self, request):
        """
        Statistiques globales des pénalités
        """
        queryset = self.filter_queryset(self.get_queryset())
        
        # Statistiques générales
        total_penalites = queryset.count()
        montant_total = queryset.aggregate(
            total=Sum('montant_total_penalite')
        )['total'] or Decimal('0')
        
        # Par type
        stats_par_type = {}
        for type_code, type_label in PenaliteEmprunt.TYPE_PENALITE_CHOICES:
            type_queryset = queryset.filter(type_penalite=type_code)
            stats_par_type[type_code] = {
                'label': type_label,
                'count': type_queryset.count(),
                'montant_total': type_queryset.aggregate(
                    total=Sum('montant_total_penalite')
                )['total'] or Decimal('0')
            }
        
        # Par palier
        stats_par_palier = queryset.values('palier').annotate(
            count=models.Count('id'),
            montant_total=Sum('montant_total_penalite')
        ).order_by('palier')
        
        # Top membres avec le plus de pénalités
        top_membres_penalites = queryset.values(
            'emprunt__membre__numero_membre',
            'emprunt__membre__utilisateur__first_name',
            'emprunt__membre__utilisateur__last_name'
        ).annotate(
            count=models.Count('id'),
            montant_total=Sum('montant_total_penalite')
        ).order_by('-montant_total')[:10]
        
        # Évolution mensuelle
        from django.db.models.functions import TruncMonth
        evolution_mensuelle = queryset.annotate(
            mois=TruncMonth('date_application')
        ).values('mois').annotate(
            count=models.Count('id'),
            montant_total=Sum('montant_total_penalite')
        ).order_by('mois')
        
        return Response({
            'total_penalites': total_penalites,
            'montant_total': montant_total,
            'stats_par_type': stats_par_type,
            'stats_par_palier': list(stats_par_palier),
            'top_membres_penalites': list(top_membres_penalites),
            'evolution_mensuelle': list(evolution_mensuelle)
        })
    
    @action(detail=False, methods=['get'])
    def par_emprunt(self, request):
        """
        Liste des pénalités groupées par emprunt
        """
        emprunt_id = request.query_params.get('emprunt_id')
        if not emprunt_id:
            return Response({
                'error': 'Paramètre emprunt_id requis'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            emprunt = Emprunt.objects.get(id=emprunt_id)
        except Emprunt.DoesNotExist:
            return Response({
                'error': 'Emprunt non trouvé'
            }, status=status.HTTP_404_NOT_FOUND)
        
        penalites = self.get_queryset().filter(emprunt=emprunt)
        serializer = self.get_serializer(penalites, many=True)
        
        # Informations résumées sur l'emprunt
        emprunt_info = {
            'id': str(emprunt.id),
            'membre': {
                'numero': emprunt.membre.numero_membre,
                'nom': emprunt.membre.utilisateur.nom_complet
            },
            'montant_initial': emprunt.montant_emprunte,
            'montant_total_actuel': emprunt.montant_total_a_rembourser,
            'montant_rembourse': emprunt.montant_rembourse,
            'statut': emprunt.statut,
            'date_emprunt': emprunt.date_emprunt,
            'nombre_penalites': penalites.count(),
            'total_penalites': sum(p.montant_total_penalite for p in penalites)
        }
        
        return Response({
            'emprunt_info': emprunt_info,
            'penalites': serializer.data
        })


class EmpruntDetailViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet en lecture seule pour le suivi détaillé des emprunts avec pénalités
    Utilisé pour la transparence devant les membres
    """
    queryset = Emprunt.objects.all()
    serializer_class = EmpruntDetailAvecPenalitesSerializer
    permission_classes = [AllowAny]  # Accessible à tous pour transparence
    
    def get_queryset(self):
        """Optimisation des requêtes"""
        return Emprunt.objects.select_related(
            'membre__utilisateur',
            'session_emprunt'
        ).prefetch_related(
            'penalites__session_application',
            'penalites__appliquee_par',
            'remboursements'
        )
    
    @action(detail=True, methods=['get'])
    def historique_complet(self, request, pk=None):
        """
        Historique complet d'un emprunt : création, pénalités, remboursements
        Parfait pour justifier devant les membres
        """
        emprunt = self.get_object()
        
        # Événements chronologiques
        evenements = []
        
        # 1. Création de l'emprunt
        evenements.append({
            'type': 'creation',
            'date': emprunt.date_emprunt,
            'description': f"Création de l'emprunt de {emprunt.montant_emprunte:,.0f} FCFA",
            'montant': emprunt.montant_emprunte,
            'montant_total_apres': emprunt.montant_emprunte,  # Montant initial
            'details': {
                'taux_interet': emprunt.taux_interet,
                'echeance': emprunt.date_remboursement_max
            }
        })
        
        # 2. Pénalités appliquées
        for penalite in emprunt.penalites.all().order_by('date_application'):
            evenements.append({
                'type': 'penalite',
                'date': penalite.date_application,
                'description': f"Pénalité {penalite.palier} appliquée",
                'montant': penalite.montant_total_penalite,
                'montant_total_apres': None,  # Sera calculé après tri
                'details': {
                    'palier': penalite.palier,
                    'sessions_ecoulees': penalite.sessions_ecoulees,
                    'montant_reste_avant': penalite.montant_reste_avant,
                    'taux_applique': penalite.taux_applique,
                    'montant_interet_taux': penalite.montant_interet_taux,
                    'montant_penalite_fixe': penalite.montant_penalite_fixe,
                    'formule': penalite.formule_calcul,
                    'justification': penalite.justification
                }
            })
        
        # 3. Remboursements effectués
        for remboursement in emprunt.remboursements.all().order_by('date_remboursement'):
            evenements.append({
                'type': 'remboursement',
                'date': remboursement.date_remboursement,
                'description': f"Remboursement de {remboursement.montant:,.0f} FCFA",
                'montant': -remboursement.montant,  # Négatif car c'est un remboursement
                'montant_total_apres': None,  # Sera calculé après tri
                'details': {
                    'notes': remboursement.notes
                }
            })
        
        # Tri chronologique
        evenements.sort(key=lambda x: x['date'])
        
        # Calcul des montants cumulés
        montant_total_courant = Decimal('0')
        for event in evenements:
            if event['type'] == 'creation':
                montant_total_courant = event['montant']
            else:
                montant_total_courant += event['montant']
            event['montant_total_apres'] = montant_total_courant
        
        # Informations actuelles
        info_actuelle = {
            'montant_total_a_rembourser': emprunt.montant_total_a_rembourser,
            'montant_rembourse': emprunt.montant_rembourse,
            'montant_restant': emprunt.montant_restant_a_rembourser,
            'statut': emprunt.statut,
            'pourcentage_rembourse': emprunt.pourcentage_rembourse,
            'is_en_retard': emprunt.is_en_retard,
            'jours_de_retard': emprunt.jours_de_retard if emprunt.is_en_retard else 0
        }
        
        return Response({
            'emprunt_id': str(emprunt.id),
            'membre': {
                'numero': emprunt.membre.numero_membre,
                'nom': emprunt.membre.utilisateur.nom_complet
            },
            'historique_chronologique': evenements,
            'situation_actuelle': info_actuelle,
            'resume': {
                'nombre_penalites': emprunt.penalites.count(),
                'total_penalites': sum(p.montant_total_penalite for p in emprunt.penalites.all()),
                'nombre_remboursements': emprunt.remboursements.count(),
                'total_rembourse': emprunt.montant_rembourse
            }
        })

class RepartitionRenflouementExerciceViewSet(viewsets.ModelViewSet):
    """
    ViewSet pour les répartitions de renflouement de fin d'exercice
    """
    queryset = RepartitionRenflouementExercice.objects.all()
    serializer_class = RepartitionRenflouementExerciceSerializer
    permission_classes = [IsAdminOrReadOnly]
    ordering = ['-date_calcul']
    
    def get_queryset(self):
        """Optimisation des requêtes"""
        return RepartitionRenflouementExercice.objects.select_related(
            'exercice', 'calcule_par'
        )
    
    @action(detail=False, methods=['post'])
    def calculer_renflouements(self, request):
        """
        Endpoint pour calculer et créer les renflouements de fin d'exercice
        """
        exercice_id = request.data.get('exercice_id')
        if not exercice_id:
            return Response({
                'error': 'exercice_id requis'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            from core.models import Exercice
            exercice = Exercice.objects.get(id=exercice_id)
        except Exercice.DoesNotExist:
            return Response({
                'error': 'Exercice non trouvé'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Vérifier si une répartition existe déjà
        if hasattr(exercice, 'repartition_renflouement'):
            return Response({
                'error': 'Une répartition existe déjà pour cet exercice',
                'repartition_existante': RepartitionRenflouementExerciceSerializer(
                    exercice.repartition_renflouement
                ).data
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Lancer le calcul
            result = exercice.creer_renflouements_fin_exercice()
            
            # Récupérer la répartition créée
            repartition = exercice.repartition_renflouement
            repartition.calcule_par = request.user
            repartition.save()
            
            return Response({
                'message': 'Renflouements proportionnels créés avec succès',
                'result': result,
                'repartition': RepartitionRenflouementExerciceSerializer(repartition).data
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            return Response({
                'error': f'Erreur lors du calcul: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['get'])
    def renflouements_associes(self, request, pk=None):
        """
        Liste des renflouements créés pour cette répartition
        """
        repartition = self.get_object()
        
        renflouements = Renflouement.objects.filter(
            exercice_renflouement=repartition.exercice,
            type_cause='RENFLOUEMENT_FIN_EXERCICE'
        ).select_related('membre__utilisateur', 'session')
        
        # Statistiques
        stats = {
            'total_renflouements': renflouements.count(),
            'total_du': sum(r.montant_du for r in renflouements),
            'total_paye': sum(r.montant_paye for r in renflouements),
            'nombre_soldes': renflouements.filter(montant_paye__gte=models.F('montant_du')).count(),
            'nombre_partiels': renflouements.filter(
                montant_paye__gt=0, montant_paye__lt=models.F('montant_du')
            ).count(),
            'nombre_non_payes': renflouements.filter(montant_paye=0).count()
        }
        
        return Response({
            'repartition': RepartitionRenflouementExerciceSerializer(repartition).data,
            'statistiques': stats,
            'renflouements': RenflouementSerializer(renflouements, many=True).data
        })


class RenflouementProportionnelViewSet(viewsets.ModelViewSet):
    """
    ViewSet spécialisé pour les renflouements avec système proportionnel
    """
    queryset = Renflouement.objects.all()
    serializer_class = RenflouementSerializer
    permission_classes = [IsAdminOrReadOnly]
    ordering = ['-date_creation']
    
    def get_queryset(self):
        """Optimisation des requêtes"""
        return Renflouement.objects.select_related(
            'membre__utilisateur', 'session', 'exercice_renflouement'
        ).prefetch_related('paiements')
    
    @action(detail=False, methods=['get'])
    def proportionnels(self, request):
        """
        Liste des renflouements utilisant le système proportionnel
        """
        renflouements = self.get_queryset().filter(
            ratio_caisse_inscription__isnull=False,
            ratio_fonds_social__isnull=False
        )
        
        serializer = self.get_serializer(renflouements, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def anciens(self, request):
        """
        Liste des renflouements utilisant l'ancien système (100% fonds social)
        """
        renflouements = self.get_queryset().filter(
            ratio_caisse_inscription__isnull=True,
            ratio_fonds_social__isnull=True
        )
        
        serializer = self.get_serializer(renflouements, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def simulation_paiement(self, request, pk=None):
        """
        Simule la répartition d'un paiement pour ce renflouement
        """
        renflouement = self.get_object()
        montant = request.query_params.get('montant')
        
        if not montant:
            return Response({
                'error': 'Paramètre montant requis'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            montant = Decimal(montant)
            if montant <= 0:
                raise ValueError("Montant doit être positif")
        except (ValueError, InvalidOperation):
            return Response({
                'error': 'Montant invalide'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Calculer la répartition
        repartition = renflouement.calculer_repartition_paiement(montant)
        
        return Response({
            'renflouement_id': str(renflouement.id),
            'membre': renflouement.membre.numero_membre,
            'montant_simule': montant,
            'repartition': repartition,
            'detail': {
                'caisse_inscription': f"{repartition['caisse_inscription']:,.0f} FCFA ({renflouement.ratio_caisse_inscription or 0}%)",
                'fonds_social': f"{repartition['fonds_social']:,.0f} FCFA ({renflouement.ratio_fonds_social or 100}%)",
                'total': f"{repartition['total']:,.0f} FCFA"
            },
            'montant_restant_apres': max(0, renflouement.montant_restant - montant)
        })
    
    @action(detail=False, methods=['get'])
    def statistiques_proportionnelles(self, request):
        """
        Statistiques sur les renflouements proportionnels
        """
        # Renflouements proportionnels
        proportionnels = self.get_queryset().filter(
            ratio_caisse_inscription__isnull=False
        )
        
        # Renflouements anciens
        anciens = self.get_queryset().filter(
            ratio_caisse_inscription__isnull=True
        )
        
        # Paiements avec répartition
        paiements_proportionnels = PaiementRenflouement.objects.filter(
            ratio_caisse_utilise__isnull=False
        )
        
        # Calculs
        stats_proportionnels = {
            'count': proportionnels.count(),
            'montant_total_du': sum(r.montant_du for r in proportionnels),
            'montant_total_paye': sum(r.montant_paye for r in proportionnels),
        }
        
        stats_anciens = {
            'count': anciens.count(),
            'montant_total_du': sum(r.montant_du for r in anciens),
            'montant_total_paye': sum(r.montant_paye for r in anciens),
        }
        
        # Répartition des paiements proportionnels
        total_caisse = paiements_proportionnels.aggregate(
            total=Sum('montant_caisse_inscription')
        )['total'] or Decimal('0')
        
        total_fonds = paiements_proportionnels.aggregate(
            total=Sum('montant_fonds_social')
        )['total'] or Decimal('0')
        
        return Response({
            'renflouements_proportionnels': stats_proportionnels,
            'renflouements_anciens': stats_anciens,
            'paiements_proportionnels': {
                'count': paiements_proportionnels.count(),
                'total_vers_caisse_inscription': total_caisse,
                'total_vers_fonds_social': total_fonds,
                'total_global': total_caisse + total_fonds
            },
            'exercices_avec_repartition': RepartitionRenflouementExercice.objects.count()
        })


class PaiementRenflouementProportionnelViewSet(viewsets.ModelViewSet):
    """
    ViewSet pour les paiements de renflouement avec traçabilité proportionnelle
    """
    queryset = PaiementRenflouement.objects.all()
    serializer_class = PaiementRenflouementSerializer
    permission_classes = [IsAdminOrReadOnly]
    ordering = ['-date_paiement']
    
    def get_queryset(self):
        """Optimisation des requêtes"""
        return PaiementRenflouement.objects.select_related(
            'renflouement__membre__utilisateur',
            'renflouement__exercice_renflouement',
            'session'
        )
    
    @action(detail=False, methods=['get'])
    def avec_repartition(self, request):
        """
        Liste des paiements avec répartition proportionnelle
        """
        paiements = self.get_queryset().filter(
            ratio_caisse_utilise__isnull=False
        )
        
        serializer = self.get_serializer(paiements, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def par_exercice(self, request):
        """
        Paiements groupés par exercice de renflouement
        """
        exercice_id = request.query_params.get('exercice_id')
        if not exercice_id:
            return Response({
                'error': 'Paramètre exercice_id requis'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        paiements = self.get_queryset().filter(
            renflouement__exercice_renflouement_id=exercice_id
        )
        
        # Statistiques par exercice
        stats = {
            'total_paiements': paiements.count(),
            'montant_total': paiements.aggregate(total=Sum('montant'))['total'] or Decimal('0'),
            'total_caisse_inscription': paiements.aggregate(
                total=Sum('montant_caisse_inscription')
            )['total'] or Decimal('0'),
            'total_fonds_social': paiements.aggregate(
                total=Sum('montant_fonds_social')
            )['total'] or Decimal('0'),
            'paiements_proportionnels': paiements.filter(
                ratio_caisse_utilise__isnull=False
            ).count(),
            'paiements_anciens': paiements.filter(
                ratio_caisse_utilise__isnull=True
            ).count()
        }
        
        return Response({
            'exercice_id': exercice_id,
            'statistiques': stats,
            'paiements': self.get_serializer(paiements, many=True).data
        })