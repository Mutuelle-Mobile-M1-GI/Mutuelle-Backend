
from django.db import migrations
from decimal import Decimal

def populate_montants_dus(apps, schema_editor):
    """
    Remplit les nouveaux champs avec les valeurs de la configuration actuelle
    """
    ConfigurationMutuelle = apps.get_model('core', 'ConfigurationMutuelle')
    PaiementInscription = apps.get_model('transactions', 'PaiementInscription')
    PaiementSolidarite = apps.get_model('transactions', 'PaiementSolidarite')
    Membre = apps.get_model('core', 'Membre')
    
    # Récupérer la configuration
    config = ConfigurationMutuelle.objects.first()
    if not config:
        print("⚠️ Aucune configuration trouvée, création avec valeurs par défaut...")
        config = ConfigurationMutuelle.objects.create()
    
    print(f"📋 Configuration: Inscription={config.montant_inscription}, Solidarité={config.montant_solidarite}")
    
    # 1. Remplir montant_inscription_du pour tous les paiements d'inscription
    print("\n📝 Migration des paiements d'inscription...")
    paiements_inscription = PaiementInscription.objects.all()
    count = 0
    for paiement in paiements_inscription:
        paiement.montant_inscription_du = config.montant_inscription
        # ⚠️ NE PAS utiliser update_fields dans les migrations de données
        paiement.save()
        count += 1
    print(f"   ✅ {count} paiements d'inscription mis à jour")
    
    # 2. Remplir montant_solidarite_du pour tous les paiements de solidarité
    print("\n💰 Migration des paiements de solidarité...")
    paiements_solidarite = PaiementSolidarite.objects.all()
    count = 0
    for paiement in paiements_solidarite:
        paiement.montant_solidarite_du = config.montant_solidarite
        # ⚠️ NE PAS utiliser update_fields dans les migrations de données
        paiement.save()
        count += 1
    print(f"   ✅ {count} paiements de solidarité mis à jour")
    
    # 3. Calculer inscription_terminee pour tous les membres
    print("\n🎓 Calcul du statut inscription_terminee...")
    membres = Membre.objects.all()
    count_termine = 0
    count_non_termine = 0
    
    for membre in membres:
        # Récupérer tous les paiements d'inscription du membre
        paiements = PaiementInscription.objects.filter(membre=membre)
        
        if not paiements.exists():
            membre.inscription_terminee = False
            count_non_termine += 1
        else:
            # Montant total payé
            total_paye = sum(p.montant for p in paiements)
            # Montant dû (du premier paiement)
            montant_du = paiements.order_by('date_paiement').first().montant_inscription_du
            
            # Vérifier si terminé
            membre.inscription_terminee = (total_paye >= montant_du)
            
            if membre.inscription_terminee:
                count_termine += 1
            else:
                count_non_termine += 1
        
        # ⚠️ NE PAS utiliser update_fields dans les migrations de données
        membre.save()
    
    print(f"   ✅ {count_termine} membres avec inscription terminée")
    print(f"   ⏳ {count_non_termine} membres avec inscription en cours")
    print("\n🎉 Migration des données terminée!")

def reverse_populate_montants_dus(apps, schema_editor):
    """
    Fonction de retour arrière (optionnelle)
    """
    print("⚠️ Retour arrière de la migration de données...")
    # Ne rien faire de spécial, les champs seront supprimés par la migration inverse

class Migration(migrations.Migration):

    dependencies = [
        ('core', '0005_add_inscription_terminee'),  # ⚠️ DOIT être après l'ajout du champ
        ('transactions', '0006_add_montant_dus'),     # ⚠️ DOIT être après l'ajout des champs
    ]

    operations = [
        migrations.RunPython(
            populate_montants_dus,
            reverse_populate_montants_dus
        ),
    ]

