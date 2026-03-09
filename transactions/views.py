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
    PaiementRenflouement
)
from .serializers import (
    PaiementInscriptionSerializer, PaiementSolidariteSerializer,
    EpargneTransactionSerializer, EmpruntSerializer, RemboursementSerializer,
    AssistanceAccordeeSerializer, RenflouementSerializer,
    PaiementRenflouementSerializer, StatistiquesTransactionsSerializer
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
                print(f"   - En règle: {membre.is_en_regle}")
                
                # Vérifier si le membre peut emprunter
                if membre.statut != 'EN_REGLE':
                    error_msg = f"Le membre {membre.numero_membre} n'est pas en règle (statut: {membre.statut})"
                    print(f"❌ ERREUR MEMBRE: {error_msg}")
                    return Response({
                        'error': 'Membre non éligible',
                        'details': error_msg,
                        'membre_statut': membre.statut
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