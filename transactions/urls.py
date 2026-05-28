# ============================================================
# MODIFICATION dans transactions/urls.py
# Ajouter les 3 lignes marquées ↓ NEW
# ============================================================

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'paiements-inscription',  views.PaiementInscriptionViewSet)
router.register(r'paiements-solidarite',   views.PaiementSolidariteViewSet)
router.register(r'epargne-transactions',   views.EpargneTransactionViewSet)
router.register(r'emprunts',               views.EmpruntViewSet)
router.register(r'remboursements',         views.RemboursementViewSet)
router.register(r'assistances',            views.AssistanceAccordeeViewSet)
router.register(r'renflouements',          views.RenflouementViewSet)
router.register(r'paiements-renflouement', views.PaiementRenflouementViewSet)
router.register(r'retraits-epargne',       views.RetraitEpargneViewSet)   # ↓ NEW

urlpatterns = [
    # Existant - stats épargne
    path('epargne-transactions/statistiques/',
         views.EpargneTransactionViewSet.as_view({'get': 'statistiques'}),
         name='epargne-stats'),

    # Existant - assistances par membre
    path('assistances/par_membre/',
         views.AssistanceAccordeeViewSet.as_view({'get': 'par_membre'}),
         name='assistances-par-membre'),

    # ↓ NEW – actions custom retraits
    path('retraits-epargne/par_membre/',
         views.RetraitEpargneViewSet.as_view({'get': 'par_membre'}),
         name='retraits-par-membre'),

    path('retraits-epargne/epargne_disponible/',
         views.RetraitEpargneViewSet.as_view({'get': 'epargne_disponible'}),
         name='retraits-epargne-disponible'),

    path('retraits-epargne/<pk>/approuver/',
         views.RetraitEpargneViewSet.as_view({'post': 'approuver'}),
         name='retrait-approuver'),

    path('retraits-epargne/<pk>/rejeter/',
         views.RetraitEpargneViewSet.as_view({'post': 'rejeter'}),
         name='retrait-rejeter'),

    # Routes automatiques (toujours en dernier)
    path('', include(router.urls)),
]