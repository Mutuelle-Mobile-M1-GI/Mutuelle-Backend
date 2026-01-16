from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django_filters import rest_framework as filters
from django.db import models
from .models import (
    ConfigurationMutuelle, Exercice, Session, TypeAssistance, 
    Membre, FondsSocial, EmpruntCoefficientTier
)
from .serializers import (
    ConfigurationMutuelleSerializer, ExerciceSerializer, SessionSerializer,
    TypeAssistanceSerializer, MembreSerializer, FondsSocialSerializer,
    DonneesAdministrateurSerializer,EmpruntCoefficientTierSerializer
)
from .utils import calculer_donnees_administrateur
from authentication.permissions import IsAdministrateur, IsAdminOrReadOnly

class ConfigurationMutuelleFilter(filters.FilterSet):
    """
    Filtres pour la configuration
    """
    montant_inscription_min = filters.NumberFilter(field_name='montant_inscription', lookup_expr='gte')
    montant_inscription_max = filters.NumberFilter(field_name='montant_inscription', lookup_expr='lte')
    montant_solidarite_min = filters.NumberFilter(field_name='montant_solidarite', lookup_expr='gte')
    montant_solidarite_max = filters.NumberFilter(field_name='montant_solidarite', lookup_expr='lte')
    taux_interet_min = filters.NumberFilter(field_name='taux_interet', lookup_expr='gte')
    taux_interet_max = filters.NumberFilter(field_name='taux_interet', lookup_expr='lte')
    
    class Meta:
        model = ConfigurationMutuelle
        fields = {
            'montant_inscription': ['exact', 'gte', 'lte'],
            'montant_solidarite': ['exact', 'gte', 'lte'],
            'taux_interet': ['exact', 'gte', 'lte'],
            'duree_exercice_mois': ['exact', 'gte', 'lte'],
        }

class ConfigurationMutuelleViewSet(viewsets.ModelViewSet):
    """
    ViewSet pour la configuration (admin seulement pour modification)
    """
    queryset = ConfigurationMutuelle.objects.all()
    serializer_class = ConfigurationMutuelleSerializer
    filterset_class = ConfigurationMutuelleFilter
    permission_classes = [IsAdminOrReadOnly]
    
    @action(detail=False, methods=['get'], permission_classes=[AllowAny])
    def current(self, request):
        """
        Retourne la configuration actuelle
        """
        config = ConfigurationMutuelle.get_configuration()
        serializer = self.get_serializer(config)
        return Response(serializer.data)

class ExerciceFilter(filters.FilterSet):
    """
    Filtres ultra-complets pour les exercices
    """
    nom = filters.CharFilter(lookup_expr='icontains')
    statut = filters.ChoiceFilter(choices=Exercice.STATUS_CHOICES)
    date_debut = filters.DateFromToRangeFilter()
    date_fin = filters.DateFromToRangeFilter()
    date_debut_after = filters.DateFilter(field_name='date_debut', lookup_expr='gte')
    date_debut_before = filters.DateFilter(field_name='date_debut', lookup_expr='lte')
    date_fin_after = filters.DateFilter(field_name='date_fin', lookup_expr='gte')
    date_fin_before = filters.DateFilter(field_name='date_fin', lookup_expr='lte')
    
    # Filtres avancés
    is_current = filters.BooleanFilter(method='filter_is_current')
    has_sessions = filters.BooleanFilter(method='filter_has_sessions')
    year = filters.NumberFilter(method='filter_year')
    duration_days = filters.NumberFilter(method='filter_duration_days')
    
    class Meta:
        model = Exercice
        fields = {
            'nom': ['exact', 'icontains', 'istartswith'],
            'statut': ['exact'],
            'date_debut': ['exact', 'gte', 'lte', 'year', 'month'],
            'date_fin': ['exact', 'gte', 'lte', 'year', 'month'],
            'date_creation': ['exact', 'gte', 'lte'],
        }
    
    def filter_is_current(self, queryset, name, value):
        if value:
            return queryset.filter(statut='EN_COURS')
        return queryset.exclude(statut='EN_COURS')
    
    def filter_has_sessions(self, queryset, name, value):
        if value:
            return queryset.filter(sessions__isnull=False).distinct()
        return queryset.filter(sessions__isnull=True)
    
    def filter_year(self, queryset, name, value):
        return queryset.filter(date_debut__year=value)
    
    def filter_duration_days(self, queryset, name, value):
        # Filtrer par durée en jours (approximative)
        return queryset.extra(
            where=["date_fin - date_debut <= %s"],
            params=[value]
        )

class ExerciceViewSet(viewsets.ModelViewSet):
    """
    ViewSet pour les exercices avec filtres complets
    """
    queryset = Exercice.objects.all()
    serializer_class = ExerciceSerializer
    filterset_class = ExerciceFilter
    search_fields = ['nom', 'description']
    ordering_fields = ['date_debut', 'date_fin', 'date_creation', 'nom']
    ordering = ['-date_debut']
    permission_classes = [IsAdminOrReadOnly]
    
    @action(detail=False, methods=['get'], permission_classes=[AllowAny])
    def current(self, request):
        """
        Retourne l'exercice en cours
        """
        print("RECHERCHE DE L'EXO EN COURS ...")
        exercice = Exercice.get_exercice_en_cours()
        if exercice:
            serializer = self.get_serializer(exercice)
            return Response(serializer.data)
        return Response({'detail': 'Aucun exercice en cours'}, status=404)

class SessionFilter(filters.FilterSet):
    """
    Filtres ultra-complets pour les sessions
    """
    nom = filters.CharFilter(lookup_expr='icontains')
    exercice = filters.UUIDFilter()
    exercice_nom = filters.CharFilter(field_name='exercice__nom', lookup_expr='icontains')
    statut = filters.ChoiceFilter(choices=Session.STATUS_CHOICES)
    date_session = filters.DateFromToRangeFilter()
    date_session_after = filters.DateFilter(field_name='date_session', lookup_expr='gte')
    date_session_before = filters.DateFilter(field_name='date_session', lookup_expr='lte')
    
    # Filtres sur montants
    montant_collation_min = filters.NumberFilter(field_name='montant_collation', lookup_expr='gte')
    montant_collation_max = filters.NumberFilter(field_name='montant_collation', lookup_expr='lte')
    has_collation = filters.BooleanFilter(method='filter_has_collation')
    
    # Filtres avancés
    is_current = filters.BooleanFilter(method='filter_is_current')
    month = filters.NumberFilter(field_name='date_session', lookup_expr='month')
    year = filters.NumberFilter(field_name='date_session', lookup_expr='year')
    this_month = filters.BooleanFilter(method='filter_this_month')
    this_year = filters.BooleanFilter(method='filter_this_year')
    
    class Meta:
        model = Session
        fields = {
            'nom': ['exact', 'icontains'],
            'statut': ['exact'],
            'date_session': ['exact', 'gte', 'lte', 'year', 'month'],
            'montant_collation': ['exact', 'gte', 'lte'],
            'date_creation': ['exact', 'gte', 'lte'],
        }
    
    def filter_has_collation(self, queryset, name, value):
        if value:
            return queryset.filter(montant_collation__gt=0)
        return queryset.filter(montant_collation=0)
    
    def filter_is_current(self, queryset, name, value):
        if value:
            return queryset.filter(statut='EN_COURS')
        return queryset.exclude(statut='EN_COURS')
    
    def filter_this_month(self, queryset, name, value):
        from django.utils import timezone
        if value:
            now = timezone.now()
            return queryset.filter(
                date_session__year=now.year,
                date_session__month=now.month
            )
        return queryset
    
    def filter_this_year(self, queryset, name, value):
        from django.utils import timezone
        if value:
            return queryset.filter(date_session__year=timezone.now().year)
        return queryset

class SessionViewSet(viewsets.ModelViewSet):
    """
    ViewSet pour les sessions avec filtres complets
    """
    queryset = Session.objects.all()
    serializer_class = SessionSerializer
    filterset_class = SessionFilter
    search_fields = ['nom', 'description', 'exercice__nom']
    ordering_fields = ['date_session', 'date_creation', 'nom', 'montant_collation']
    ordering = ['-date_session']
    permission_classes = [IsAdminOrReadOnly]
    
    def perform_create(self, serializer):
        """
        Personnalisé : appelé APRÈS la validation, AVANT la sauvegarde lors d'un POST
        
        Respecte la logique complète de Session.save() du modèle :
        1. Auto-génère le nom si pas fourni
        2. Assigne l'exercice en cours si pas fourni
        3. Gère les sessions EN_COURS (une seule par exercice)
        4. Traite la collation si montant > 0 et statut = EN_COURS
        """
        print("=" * 100)
        print("🔍 CRÉATION DE SESSION - perform_create()")
        print(f"📡 Données reçues: {serializer.validated_data}")
        print("=" * 50)
        
        # Vérifier que l'exercice est assigné
        if 'exercice' not in serializer.validated_data or not serializer.validated_data.get('exercice'):
            exercice_actuel = Exercice.get_exercice_en_cours()
            if exercice_actuel:
                serializer.validated_data['exercice'] = exercice_actuel
                print(f"✅ Exercice auto-assigné: {exercice_actuel.nom}")
            else:
                print("⚠️ ATTENTION: Aucun exercice en cours trouvé")
        
        # Laisser le modèle.save() gérer toute la logique métier
        # (nom auto-généré, gestion sessions EN_COURS, collation, renflouements, etc.)
        print("✅ Appel de serializer.save() → Session.save() du modèle prendra le relais")
        try:
            serializer.save()
            
            print(f"✅ Session créée avec succès:")
            print(f"   - Nom: {serializer.instance.nom}")
            print(f"   - Exercice: {serializer.instance.exercice.nom}")
            print(f"   - Statut: {serializer.instance.statut}")
            print(f"   - Collation: {serializer.instance.montant_collation}")
            print("=" * 100)
        except Exception as e:
            print(f"❌ ERREUR CRÉATION SESSION: {e}")
            print("=" * 100)
            # ✅ Relancer l'exception pour que DRF la gère correctement
            from rest_framework.exceptions import ValidationError
            raise ValidationError({
                'detail': str(e)
            })
    
    @action(detail=False, methods=['get'], permission_classes=[AllowAny])
    def current(self, request):
        """
        Retourne la session en cours
        """
        session = Session.get_session_en_cours()
        if session:
            serializer = self.get_serializer(session)
            return Response(serializer.data)
        return Response({'detail': 'Aucune session en cours'}, status=404)

class MembreFilter(filters.FilterSet):
    """
    Filtres ULTRA-complets pour les membres - LE PLUS IMPORTANT !
    """
    # Filtres utilisateur
    nom_complet = filters.CharFilter(method='filter_nom_complet')
    email = filters.CharFilter(field_name='utilisateur__email', lookup_expr='icontains')
    telephone = filters.CharFilter(field_name='utilisateur__telephone', lookup_expr='icontains')
    first_name = filters.CharFilter(field_name='utilisateur__first_name', lookup_expr='icontains')
    last_name = filters.CharFilter(field_name='utilisateur__last_name', lookup_expr='icontains')
    
    # Filtres membre
    numero_membre = filters.CharFilter(lookup_expr='icontains')
    statut = filters.ChoiceFilter(choices=Membre.STATUS_CHOICES)
    date_inscription = filters.DateFromToRangeFilter()
    date_inscription_after = filters.DateFilter(field_name='date_inscription', lookup_expr='gte')
    date_inscription_before = filters.DateFilter(field_name='date_inscription', lookup_expr='lte')
    
    # Filtres exercice/session
    exercice_inscription = filters.UUIDFilter()
    session_inscription = filters.UUIDFilter()
    exercice_nom = filters.CharFilter(field_name='exercice_inscription__nom', lookup_expr='icontains')
    session_nom = filters.CharFilter(field_name='session_inscription__nom', lookup_expr='icontains')
    
    # Filtres avancés
    is_en_regle = filters.BooleanFilter(method='filter_is_en_regle')
    has_emprunts = filters.BooleanFilter(method='filter_has_emprunts')
    has_emprunts_en_cours = filters.BooleanFilter(method='filter_has_emprunts_en_cours')
    has_renflouements_dus = filters.BooleanFilter(method='filter_has_renflouements_dus')
    inscription_complete = filters.BooleanFilter(method='filter_inscription_complete')
    
    # Filtres temporels
    inscrit_this_month = filters.BooleanFilter(method='filter_inscrit_this_month')
    inscrit_this_year = filters.BooleanFilter(method='filter_inscrit_this_year')
    month_inscription = filters.NumberFilter(field_name='date_inscription', lookup_expr='month')
    year_inscription = filters.NumberFilter(field_name='date_inscription', lookup_expr='year')
    
    class Meta:
        model = Membre
        fields = {
            'numero_membre': ['exact', 'icontains', 'istartswith'],
            'statut': ['exact'],
            'date_inscription': ['exact', 'gte', 'lte', 'year', 'month'],
            'date_creation': ['exact', 'gte', 'lte'],
        }
    
    def filter_nom_complet(self, queryset, name, value):
        return queryset.filter(
            models.Q(utilisateur__first_name__icontains=value) | 
            models.Q(utilisateur__last_name__icontains=value)
        )
    
    def filter_is_en_regle(self, queryset, name, value):
        if value:
            return queryset.filter(statut='EN_REGLE')
        return queryset.exclude(statut='EN_REGLE')
    
    def filter_has_emprunts(self, queryset, name, value):
        if value:
            return queryset.filter(emprunts__isnull=False).distinct()
        return queryset.filter(emprunts__isnull=True)
    
    def filter_has_emprunts_en_cours(self, queryset, name, value):
        if value:
            return queryset.filter(emprunts__statut='EN_COURS').distinct()
        return queryset.exclude(emprunts__statut='EN_COURS')
    
    def filter_has_renflouements_dus(self, queryset, name, value):
        if value:
            return queryset.filter(
                renflouements__montant_paye__lt=models.F('renflouements__montant_du')
            ).distinct()
        return queryset.exclude(
            renflouements__montant_paye__lt=models.F('renflouements__montant_du')
        )
    
    def filter_inscription_complete(self, queryset, name, value):
        from core.models import ConfigurationMutuelle
        config = ConfigurationMutuelle.get_configuration()
        
        if value:
            return queryset.filter(
                paiements_inscription__montant__gte=config.montant_inscription
            ).distinct()
        return queryset.exclude(
            paiements_inscription__montant__gte=config.montant_inscription
        )
    
    def filter_inscrit_this_month(self, queryset, name, value):
        from django.utils import timezone
        if value:
            now = timezone.now()
            return queryset.filter(
                date_inscription__year=now.year,
                date_inscription__month=now.month
            )
        return queryset
    
    def filter_inscrit_this_year(self, queryset, name, value):
        from django.utils import timezone
        if value:
            return queryset.filter(date_inscription__year=timezone.now().year)
        return queryset

class MembreViewSet(viewsets.ModelViewSet):
    """
    ViewSet pour les membres avec TOUS LES CALCULS et filtres complets
    """
    queryset = Membre.objects.select_related('utilisateur', 'exercice_inscription', 'session_inscription').all()
    serializer_class = MembreSerializer
    filterset_class = MembreFilter
    search_fields = [
        'numero_membre', 'utilisateur__first_name', 'utilisateur__last_name',
        'utilisateur__email', 'utilisateur__telephone'
    ]
    ordering_fields = [
        'date_inscription', 'date_creation', 'numero_membre', 
        'utilisateur__first_name', 'utilisateur__last_name'
    ]
    ordering = ['-date_inscription']
    permission_classes = [AllowAny]  # Les données membre sont publiques selon vos specs
    
    @action(detail=True, methods=['get'], permission_classes=[AllowAny])
    def donnees_completes(self, request, pk=None):
        """
        Retourne TOUTES les données financières calculées du membre
        """
        membre = self.get_object()
        donnees = membre.get_donnees_completes()
        return Response(donnees)
    
    @action(detail=False, methods=['get'], permission_classes=[AllowAny])
    def statistiques(self, request):
        """
        Statistiques globales des membres
        """
        total = self.get_queryset().count()
        en_regle = self.get_queryset().filter(statut='EN_REGLE').count()
        non_en_regle = self.get_queryset().filter(statut='NON_EN_REGLE').count()
        suspendus = self.get_queryset().filter(statut='SUSPENDU').count()
        
        return Response({
            'total_membres': total,
            'membres_en_regle': en_regle,
            'membres_non_en_regle': non_en_regle,
            'membres_suspendus': suspendus,
            'pourcentage_en_regle': (en_regle / total * 100) if total > 0 else 0
        })



class TypeAssistanceViewSet(viewsets.ModelViewSet):
    """
    ViewSet pour les types d'assistance
    """
    queryset = TypeAssistance.objects.all()
    serializer_class = TypeAssistanceSerializer
    filterset_fields = ['actif', 'montant']
    search_fields = ['nom', 'description']
    ordering_fields = ['nom', 'montant', 'date_creation']
    ordering = ['nom']
    permission_classes = [IsAdminOrReadOnly]

class FondsSocialViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet pour le fonds social (lecture seule)
    """
    queryset = FondsSocial.objects.select_related('exercice').all()
    serializer_class = FondsSocialSerializer
    filterset_fields = ['exercice']
    ordering = ['-date_modification']
    permission_classes = [AllowAny]
    
    @action(detail=False, methods=['get'], permission_classes=[AllowAny])
    def current(self, request):
        """
        Retourne le fonds social actuel
        """
        fonds = FondsSocial.get_fonds_actuel()
        if fonds:
            serializer = self.get_serializer(fonds)
            return Response(serializer.data)
        return Response({'detail': 'Aucun fonds social actuel'}, status=404)

@action(detail=False, methods=['get'], permission_classes=[IsAdministrateur])
def donnees_administrateur(request):
    """
    Vue pour toutes les données administrateur
    """
    donnees = calculer_donnees_administrateur()
    serializer = DonneesAdministrateurSerializer(donnees)
    return Response(serializer.data)

class EmpruntCoefficientTierViewSet(viewsets.ModelViewSet):
    """
    ViewSet pour gérer les tranches de coefficient d'emprunt par exercice
    """
    queryset = EmpruntCoefficientTier.objects.select_related('exercise').all()
    serializer_class = EmpruntCoefficientTierSerializer
    permission_classes = [IsAdminOrReadOnly]  # Admin seulement pour modifier

    def get_queryset(self):
        """
        Par défaut : ne retourne que les tranches de l'exercice en cours
        Avec ?exercise_id=xxx → retourne celles de cet exercice
        """
        exercise_id = self.request.query_params.get('exercise_id')
        if exercise_id:
            return self.queryset.filter(exercise_id=exercise_id).order_by('min_amount')
        
        # Par défaut → exercice en cours
        exercice = Exercice.get_exercice_en_cours()
        if exercice:
            return self.queryset.filter(exercise=exercice).order_by('min_amount')
        return self.queryset.none()

    @action(detail=False, methods=['post'], url_path='bulk-upsert')
    def bulk_upsert(self, request):
        """
        Remplace TOUTES les tranches d'un exercice donné
        Utilisé lors de la création d'un nouvel exercice avec copie/modification
        Body:
        {
            "exercise_id": "uuid-de-lexercice",
            "tiers": [
                { "min_amount": 0, "max_amount": 500000, "coefficient": "6.00", "max_cap": 2500000 },
                ...
            ]
        }
        """
        exercise_id = request.data.get('exercise_id')
        tiers_data = request.data.get('tiers', [])

        if not exercise_id:
            return Response({"detail": "exercise_id est requis"}, status=status.HTTP_400_BAD_REQUEST)
        
        if not isinstance(tiers_data, list) or len(tiers_data) == 0:
            return Response({"detail": "Le champ 'tiers' doit être une liste non vide"}, status=status.HTTP_400_BAD_REQUEST)

        # Suppression des anciennes tranches
        deleted_count, _ = EmpruntCoefficientTier.objects.filter(exercise_id=exercise_id).delete()

        # Création des nouvelles
        serializer = self.get_serializer(data=tiers_data, many=True)
        serializer.is_valid(raise_exception=True)
        instances = serializer.save(exercise_id=exercise_id)

        return Response({
            "detail": f"{len(instances)} tranches créées (supprimées: {deleted_count})",
            "tiers": serializer.data
        }, status=status.HTTP_201_CREATED)