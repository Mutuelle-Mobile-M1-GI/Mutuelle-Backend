# Generated manually for unique paiement inscription per member

from decimal import Decimal
from django.db import migrations, models


def consolider_paiements_inscription(apps, schema_editor):
    """
    Pour chaque membre ayant plusieurs PaiementInscription, garde un seul
    enregistrement avec le montant total, puis supprime les autres.
    """
    from django.db.models import Count, Sum

    PaiementInscription = apps.get_model('transactions', 'PaiementInscription')

    # Membres avec plus d'un paiement
    membres_dupliques = (
        PaiementInscription.objects.values('membre')
        .annotate(nb=Count('id'))
        .filter(nb__gt=1)
    )
    for row in membres_dupliques:
        membre_id = row['membre']
        paiements = PaiementInscription.objects.filter(membre_id=membre_id).order_by('date_paiement')
        total = paiements.aggregate(s=Sum('montant'))['s'] or Decimal('0')
        premier = paiements.first()
        # Mettre à jour le premier avec le total
        premier.montant = total
        premier.save()
        # Supprimer les autres
        paiements.exclude(pk=premier.pk).delete()


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('transactions', '0007_alter_paiementinscription_montant_inscription_du_and_more'),
    ]

    operations = [
        migrations.RunPython(consolider_paiements_inscription, noop),
        migrations.AddConstraint(
            model_name='paiementinscription',
            constraint=models.UniqueConstraint(
                fields=['membre'],
                name='unique_paiement_inscription_par_membre'
            ),
        ),
    ]
