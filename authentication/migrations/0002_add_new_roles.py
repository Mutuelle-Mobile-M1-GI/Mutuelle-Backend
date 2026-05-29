from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('authentication', '0001_initial'),
    ]

    operations = [
        # Agrandir max_length pour accueillir SECRETAIRE_GENERALE (20 chars)
        migrations.AlterField(
            model_name='utilisateur',
            name='role',
            field=models.CharField(
                choices=[
                    ('MEMBRE', 'Membre'),
                    ('SECRETAIRE_GENERALE', 'Secrétaire Générale'),
                    ('TRESORIER', 'Trésorier'),
                    ('PRESIDENT', 'Président'),
                ],
                default='MEMBRE',
                max_length=20,
                verbose_name='Rôle',
            ),
        ),
        # Migrer les anciens ADMINISTRATEUR vers SECRETAIRE_GENERALE
        migrations.RunSQL(
            sql="UPDATE authentication_utilisateur SET role = 'SECRETAIRE_GENERALE' WHERE role = 'ADMINISTRATEUR';",
            reverse_sql="UPDATE authentication_utilisateur SET role = 'ADMINISTRATEUR' WHERE role = 'SECRETAIRE_GENERALE';",
        ),
    ]