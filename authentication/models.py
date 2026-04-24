from django.contrib.auth.models import AbstractUser
from django.db import models
from django.core.validators import RegexValidator
import uuid

class Utilisateur(AbstractUser):
    """
    Modèle utilisateur personnalisé pour la mutuelle
    """
    ROLE_CHOICES = [
        ('MEMBRE', 'Membre'),
        ('SECRETAIRE_GENERALE', 'Secrétaire Générale'),
        ('TRESORIER', 'Trésorier'),
        ('PRESIDENT', 'Président'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True, verbose_name="Email")
    telephone = models.CharField(
        max_length=15,
        validators=[RegexValidator(r'^\+?1?\d{9,15}$', 'Numéro de téléphone valide requis.')],
        verbose_name="Téléphone"
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='MEMBRE', verbose_name="Rôle")
    photo_profil = models.ImageField(upload_to='profiles/', null=True, blank=True, verbose_name="Photo de profil")
    date_creation = models.DateTimeField(auto_now_add=True, verbose_name="Date de création")
    date_modification = models.DateTimeField(auto_now=True, verbose_name="Dernière modification")
    is_active = models.BooleanField(default=True, verbose_name="Actif")

    # Champs requis pour AbstractUser
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name']

    class Meta:
        verbose_name = "Utilisateur"
        verbose_name_plural = "Utilisateurs"
        ordering = ['-date_creation']

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.email})"

    @property
    def nom_complet(self):
        return f"{self.first_name} {self.last_name}"

    @property
    def is_membre(self):
        return self.role == 'MEMBRE'

    @property
    def is_administrateur(self):
        # Gardé pour compatibilité — pointe vers Secrétaire Générale
        return self.role == 'SECRETAIRE_GENERALE'

    @property
    def is_secretaire_generale(self):
        return self.role == 'SECRETAIRE_GENERALE'

    @property
    def is_tresorier(self):
        return self.role == 'TRESORIER'

    @property
    def is_president(self):
        return self.role == 'PRESIDENT'

    @property
    def is_bureau(self):
        """True si l'utilisateur fait partie du bureau (SG, Trésorier, Président)"""
        return self.role in ['SECRETAIRE_GENERALE', 'TRESORIER', 'PRESIDENT']

    @property
    def can_write(self):
        """Seul la Secrétaire Générale peut modifier les données"""
        return self.role == 'SECRETAIRE_GENERALE'
