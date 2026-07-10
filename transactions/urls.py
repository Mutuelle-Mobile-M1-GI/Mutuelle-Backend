from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'paiements-inscription', views.PaiementInscriptionViewSet)
router.register(r'paiements-solidarite', views.PaiementSolidariteViewSet)
router.register(r'epargne-transactions', views.EpargneTransactionViewSet)
router.register(r'emprunts', views.EmpruntViewSet)
router.register(r'remboursements', views.RemboursementViewSet)
router.register(r'assistances', views.AssistanceAccordeeViewSet)
router.register(r'renflouements', views.RenflouementViewSet)
router.register(r'paiements-renflouement', views.PaiementRenflouementViewSet)
# Nouveaux endpoints pour les pénalités
router.register(r'penalites-emprunt', views.PenaliteEmpruntViewSet)
router.register(r'emprunts-suivi', views.EmpruntDetailViewSet, basename='emprunt-suivi')
# Nouveaux endpoints pour les renflouements proportionnels
router.register(r'repartitions-renflouement', views.RepartitionRenflouementExerciceViewSet)
router.register(r'renflouements-proportionnels', views.RenflouementProportionnelViewSet, basename='renflouement-proportionnel')
router.register(r'paiements-renflouement-proportionnels', views.PaiementRenflouementProportionnelViewSet, basename='paiement-renflouement-proportionnel')
#Endpoints retrait epargne
# Dans le router
router.register(r'retraits-epargne', views.RetraitEpargneViewSet)

urlpatterns = [
    # 1. On intercepte l'URL des statistiques d'épargne AVANT que le router ne cherche un ID
    path('epargne-transactions/statistiques/', 
        views.EpargneTransactionViewSet.as_view({'get': 'statistiques'}), 
        name='epargne-stats'),
    
    # 2. On intercepte l'URL pour récupérer les assistances par membre
    path('assistances/par_membre/', 
        views.AssistanceAccordeeViewSet.as_view({'get': 'par_membre'}), 
        name='assistances-par-membre'),
    
    # 3. Endpoints spécifiques pour les pénalités
    path('penalites-emprunt/statistiques/', 
        views.PenaliteEmpruntViewSet.as_view({'get': 'statistiques'}), 
        name='penalites-stats'),
    
    path('penalites-emprunt/par_emprunt/', 
        views.PenaliteEmpruntViewSet.as_view({'get': 'par_emprunt'}), 
        name='penalites-par-emprunt'),
    
    # 4. Endpoint pour l'historique complet d'un emprunt
    path('emprunts-suivi/<uuid:pk>/historique_complet/', 
        views.EmpruntDetailViewSet.as_view({'get': 'historique_complet'}), 
        name='emprunt-historique-complet'),
    
    # 5. Endpoints spécifiques pour les renflouements proportionnels
    path('repartitions-renflouement/calculer_renflouements/', 
        views.RepartitionRenflouementExerciceViewSet.as_view({'post': 'calculer_renflouements'}), 
        name='calculer-renflouements'),
    
    path('renflouements/<uuid:pk>/payer_avec_epargne/',
        views.RenflouementViewSet.as_view({'post': 'payer_avec_epargne'}),
        name='payer-renflouement-epargne'),
    
    path('renflouements-proportionnels/proportionnels/', 
        views.RenflouementProportionnelViewSet.as_view({'get': 'proportionnels'}), 
        name='renflouements-proportionnels'),
    
    path('renflouements-proportionnels/anciens/', 
        views.RenflouementProportionnelViewSet.as_view({'get': 'anciens'}), 
        name='renflouements-anciens'),
    
    path('renflouements-proportionnels/statistiques_proportionnelles/', 
        views.RenflouementProportionnelViewSet.as_view({'get': 'statistiques_proportionnelles'}), 
        name='stats-renflouements-proportionnels'),
    
    path('paiements-renflouement-proportionnels/avec_repartition/', 
        views.PaiementRenflouementProportionnelViewSet.as_view({'get': 'avec_repartition'}), 
        name='paiements-avec-repartition'),
    
    path('paiements-renflouement-proportionnels/par_exercice/', 
        views.PaiementRenflouementProportionnelViewSet.as_view({'get': 'par_exercice'}), 
        name='paiements-par-exercice'),

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
    
    # 6. On inclut le reste des routes automatiques
    path('', include(router.urls)),
]