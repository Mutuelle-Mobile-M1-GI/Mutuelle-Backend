
from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('core', '0004_alter_session_statut'),  # Remplacer par votre dernière migration
    ]

    operations = [
        migrations.AddField(
            model_name='membre',
            name='inscription_terminee',
            field=models.BooleanField(
                default=False,
                help_text="True si le membre a payé la totalité de son inscription",
                verbose_name='Inscription terminée'
            ),
        ),
    ]

