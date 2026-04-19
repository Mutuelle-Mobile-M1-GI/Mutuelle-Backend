from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'utilisateurs', views.UtilisateurViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('profile/', views.UtilisateurViewSet.as_view({'get': 'me', 'patch': 'update_profile'}), name='profile'),
    path('change-password/', views.ChangePasswordView.as_view(), name='change_password'),
]