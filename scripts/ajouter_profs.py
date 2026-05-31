#!/usr/bin/env python
import os
import sys
from datetime import date

# Configuration de l'environnement Django (conservée de ton script original)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(PROJECT_ROOT)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Backend.settings')

import django
django.setup()

# Import des fonctions de ton script original
# Note : On suppose que ce script est placé au même endroit pour importer les fonctions
from create_members import create_multiple_members

def slugify_name(name):
    """Simplifie le nom pour l'email et l'username."""
    return name.lower().replace(" ", ".").replace("..", ".")

# Liste complète des 60 membres extraits des images
MEMBERS_LIST = [
    ("STEPHANE", "ATOCK"), ("Charles", "AWONO O."), ("Bernabé", "BATCHAKUI"),
    ("TIBI", "BEDA"), ("Didier", "BELOBO BELOBO"), ("JEAN CALVIN", "BIDOUNG"),
    ("DANIEL", "BITANG A ZIEM"), ("Florent", "BIYEME"), ("Thomas", "BOUETOU B."),
    ("Marthe", "BOYOMO O."), ("Anne Marie", "CHANA"), ("Thomas", "DJOTIO"),
    ("Brice", "EKOBO"), ("ELIME", "ELIME"), ("Rémy M.", "ETOUA"),
    ("Bridinette", "FANDIO"), ("FITIME", "FIPPO"), ("Abraham", "KAMMOGNE"),
    ("Joseph", "KENFACK"), ("Bienvenue", "KENMEUGNE"), ("Georges", "KOUAMOU"),
    ("Victor", "KUETCHE K."), ("MARTIAL", "LELE"), ("MINSILI", "LEZIN"),
    ("J.", "MADJADOUMBAYE"), ("LUCIEN", "MANDENG"), ("Serge", "MANI ONANA"),
    ("Marceline", "MANJIA"), ("Théophile", "MBANG"), ("Edwin", "MBINKAR"),
    ("JACQUES", "MBOUS IKONG"), ("Pierre", "MEUKAM"), ("Lucien", "MEVAA"),
    ("Ibrahim", "MOUKOUOP"), ("Chantal", "MVEH"), ("GUEMA", "NDONG"),
    ("C.M.", "NGABIRENG"), ("Jean", "NGANHOU"), ("NGNIKAM", "NGNIKAM"),
    ("Paul S.", "NGOHE-EKAM"), ("RACHEL", "NGONO"), ("GUY MERLIN", "NGOUNOU"),
    ("N. Hippolyte", "NTEDE"), ("G. Raïssa", "ONANENA"), ("CHREPIN", "PETTANG"),
    ("NANA JOYCE", "PETTANG"), ("Jacques", "TAGOUDJEU"), ("Etienne", "TAKOU"),
    ("Hervé", "TALE KALACHI"), ("André", "TALLA"), ("T. Thomas", "TAMO"),
    ("Emmanuel", "TCHOMGO"), ("Théodore", "TCHOTANG"), ("Jean Jules", "TEWA"),
    ("Alain", "TIEDEU"), ("Lauraine", "TIOGNING"), ("Olivier", "VIDEME"),
    ("Joseph", "VOUFO"), ("VALAIRE", "YATAT"), ("Nasser", "YIMEN")
]

def run_import():
    members_data = []
    i = 0
    for first_name, last_name in MEMBERS_LIST:
        # Génération des identifiants
        clean_first = slugify_name(first_name)
        clean_last = slugify_name(last_name)
        username = f"{clean_first}.{clean_last}"[:30] # Limite Django username
        email = f"{clean_first}.{clean_last}@mutuelle.com"
        
        members_data.append({
            'email': email,
            'username': username,
            'first_name': first_name,
            'last_name': last_name,
            'telephone': '+23700000000', # Valeur par défaut
            'role': 'MEMBRE',
            'statut': 'NON_EN_REGLE'
        })

    print(f"🚀 Lancement de l'importation de {len(members_data)} membres...")
    results = create_multiple_members(members_data)
    
    # Petit rapport final
    success = len([r for r in results if r[2]])
    print(f"✅ Terminé : {success} créés, {len(results) - success} déjà existants.")

if __name__ == '__main__':
    run_import()