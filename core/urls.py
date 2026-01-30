from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'configurations', views.ConfigurationMutuelleViewSet)
router.register(r'exercices', views.ExerciceViewSet)
router.register(r'sessions', views.SessionViewSet)
router.register(r'membres', views.MembreViewSet)
router.register(r'types-assistance', views.TypeAssistanceViewSet)
router.register(r'fonds-social', views.FondsSocialViewSet)
router.register(r'emprunt-tiers', views.EmpruntCoefficientTierViewSet, basename='emprunt-tier')

urlpatterns = [
    path('', include(router.urls)),
    path('donnees-administrateur/', views.donnees_administrateur, name='donnees_administrateur'),
    # Endpoints pour exécuter les scripts en production
    path('scripts/import-members/', views.import_members, name='import_members'),
    path('scripts/initialize-assistance-types/', views.initialize_assistance_types, name='initialize_assistance_types'),
]