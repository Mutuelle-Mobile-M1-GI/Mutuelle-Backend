from rest_framework.permissions import BasePermission
from rest_framework import permissions

ROLES_BUREAU = ['SECRETAIRE_GENERALE', 'TRESORIER', 'PRESIDENT']
ROLES_LECTURE_SEULE = ['TRESORIER', 'PRESIDENT']


class IsAdministrateur(BasePermission):
    """
    Permission pour la Secrétaire Générale uniquement (anciennement Administrateur).
    Utilisée pour les actions d'écriture/modification.
    """
    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            request.user.role == 'SECRETAIRE_GENERALE'
        )


class IsSecretaireGenerale(BasePermission):
    """Alias explicite pour IsAdministrateur"""
    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            request.user.role == 'SECRETAIRE_GENERALE'
        )


class IsBureau(BasePermission):
    """
    Permission pour tout le bureau (SG + Trésorier + Président).
    Utilisée pour la lecture des données sensibles.
    """
    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            request.user.role in ROLES_BUREAU
        )


class IsMembreOrAdmin(BasePermission):
    """Permission pour les membres ou tout le bureau"""
    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            request.user.role in ['MEMBRE'] + ROLES_BUREAU
        )


class IsOwnerOrAdmin(BasePermission):
    """Permission pour le propriétaire de l'objet ou la Secrétaire Générale"""
    def has_object_permission(self, request, view, obj):
        if request.user.role == 'SECRETAIRE_GENERALE':
            return True

        if hasattr(obj, 'membre'):
            return obj.membre.utilisateur == request.user

        if hasattr(obj, 'utilisateur'):
            return obj.utilisateur == request.user

        if hasattr(obj, 'email'):
            return obj == request.user

        return False


class IsAdminOrReadOnly(BasePermission):
    """
    Lecture pour tout le bureau, écriture pour la Secrétaire Générale seulement.
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        # Lecture autorisée pour tout le bureau
        if request.method in permissions.SAFE_METHODS:
            return request.user.role in ROLES_BUREAU

        # Écriture réservée à la Secrétaire Générale
        return request.user.role == 'SECRETAIRE_GENERALE'