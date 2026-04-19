# Fichier : transactions/signals.py

from django.db.models.signals import post_save
from django.dispatch import receiver
from transactions.models import PaiementSolidarite, PaiementInscription
# Utilisez la syntaxe d'importation standard si core est dans votre INSTALLED_APPS
from core.models import FondsSocial, Membre 

@receiver(post_save, sender=PaiementSolidarite)
@receiver(post_save, sender=PaiementInscription)
def handle_paiement_post_save(sender, instance, created, **kwargs):
    """
    Gère la mise à jour du Fonds Social (uniquement pour la Solidarité) 
    et du statut du membre (pour les deux paiements) après la création.
    """
    
    # Nous ne traitons que les NOUVELLES créations (pas les mises à jour) pour l'alimentation
    if not created:
        return 
        
    try:
        # 1. Mise à jour du Fonds Social
        fonds = FondsSocial.get_fonds_actuel()
        
        if fonds and instance.montant > 0:
            montant = instance.montant
            
            # ⚠️ UNIQUEMENT LE PAIEMENT DE SOLIDARITÉ ALIMENTE LE FONDS SOCIAL
            if sender == PaiementSolidarite:
                description = f"Solidarité {instance.membre.numero_membre} (Session {instance.session.nom})"
                # L'appel à ajouter_montant() doit utiliser la logique atomique (F())
                fonds.ajouter_montant(montant, description) 
                print(f"SIGNAL INFO: Fonds Social alimenté par solidarité de {montant}")
            
            # Le paiement d'inscription n'alimente pas le Fonds Social par défaut.
            
        # 2. Mise à jour du Statut du Membre (Logique de Régularisation)
        membre = instance.membre
        
        # On suppose que calculer_statut_en_regle() vérifie si le membre a assez payé
        if membre.calculer_statut_en_regle():
            # Mise à jour atomique du statut pour éviter les conflits
            if membre.statut != 'EN_REGLE':
                Membre.objects.filter(pk=membre.pk).update(statut='EN_REGLE')
                print(f"SIGNAL INFO: Membre {membre.numero_membre} passé EN_REGLE.")
                
    except Exception as e:
        # Affiche l'erreur complète dans la console du serveur
        import traceback
        traceback.print_exc()
        print(f"ERREUR CRITIQUE dans le signal de paiement: {e}")