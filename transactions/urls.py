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

urlpatterns = [
    # 1. On intercepte l'URL des statistiques AVANT que le router ne cherche un ID
    path('epargne-transactions/statistiques/', 
        views.EpargneTransactionViewSet.as_view({'get': 'statistiques'}), 
        name='epargne-stats'),
    
    # 2. On inclut le reste des routes automatiques
    path('', include(router.urls)),
]