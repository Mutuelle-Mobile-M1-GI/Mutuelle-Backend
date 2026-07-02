from django.core.management import call_command
from django.db import connection

# Supprimer la migration via Django (compatible PostgreSQL/SQLite)
sql = "DELETE FROM django_migrations WHERE app='transactions' AND name='0010_remove_paiementinscription_unique_paiement_inscription_par_membre_and_more'"

with connection.cursor() as cursor:
    cursor.execute(sql)