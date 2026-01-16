
from django.db import migrations, models
import django.core.validators

class Migration(migrations.Migration):

    dependencies = [
        ('transactions', '0003_emprunt_date_creation_emprunt_date_modification_and_more'),  # Remplacer par votre dernière migration
    ]

    operations = [
        # Ajouter montant_inscription_du
        migrations.AddField(
            model_name='paiementinscription',
            name='montant_inscription_du',
            field=models.DecimalField(
                decimal_places=2,
                default=0,  # Temporaire pour permettre la migration
                help_text="Montant total dû pour l'inscription (FCFA)",
                max_digits=12,
                validators=[django.core.validators.MinValueValidator(0)],
                verbose_name='Montant total dû pour inscription (FCFA)'
            ),
            preserve_default=False,  # Enlever le default après migration
        ),
        
        # Ajouter montant_solidarite_du
        migrations.AddField(
            model_name='paiementsolidarite',
            name='montant_solidarite_du',
            field=models.DecimalField(
                decimal_places=2,
                default=0,  # Temporaire pour permettre la migration
                help_text='Montant dû pour cette session (FCFA)',
                max_digits=12,
                validators=[django.core.validators.MinValueValidator(0)],
                verbose_name='Montant dû pour cette session (FCFA)'
            ),
            preserve_default=False,  # Enlever le default après migration
        ),
        
        # Retirer la contrainte unique_together de PaiementSolidarite
        migrations.AlterUniqueTogether(
            name='paiementsolidarite',
            unique_together=set(),
        ),
    ]