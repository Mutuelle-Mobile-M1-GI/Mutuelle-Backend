import sqlite3
conn = sqlite3.connect('db.sqlite3')
cursor = conn.cursor()
sql = "DELETE FROM django_migrations WHERE app='transactions' AND name='0010_remove_paiementinscription_unique_paiement_inscription_par_membre_and_more'"
cursor.execute(sql)
conn.commit()
conn.close()
print('Done')
