#!/usr/bin/env python
"""
Script de simulation : paie la solidarité et affiche le fonds social avant/après.

Usage:
    python scripts/simulate_solidarite.py

Le script configure Django, récupère la `ConfigurationMutuelle`, puis utilise
la méthode `ajouter_montant` de `FondsSocial` pour simuler le paiement.
"""
import os
import sys
from datetime import date


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(PROJECT_ROOT)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Backend.settings')

import django
django.setup()

from core.models import ConfigurationMutuelle, FondsSocial, Exercice, Session, Membre
from django.contrib.auth import get_user_model
from transactions.models import PaiementSolidarite
import uuid


def main():
    config = ConfigurationMutuelle.get_configuration()
    montant = config.montant_solidarite

    # obtenir ou créer le fonds social pour l'exercice en cours
    fonds = FondsSocial.get_fonds_actuel()
    if not fonds:
        ex = Exercice.get_exercice_en_cours()
        if not ex:
            ex = Exercice.objects.create(
                nom=f'Exercice {date.today().year}',
                date_debut=date.today(),
                statut='EN_COURS'
            )
        fonds = FondsSocial.objects.create(exercice=ex, montant_total=0)
    else:
        # si le fonds existe, récupérer son exercice pour créer le membre/session
        ex = fonds.exercice

    print("Fonds avant :", fonds.montant_total)

    # Créer un utilisateur et membre uniques pour la simulation (évite contraintes UNIQUE)
    User = get_user_model()
    unique = uuid.uuid4().hex[:8]
    username = f"sim_user_{unique}"
    user, created = User.objects.get_or_create(
        username=username,
        defaults={'email': f'{username}@example.test'}
    )
    try:
        user.first_name = 'Sim'
        user.last_name = 'Solid'
        user.save()
    except Exception:
        pass

    ex_for_member = ex
    session_for_member, _ = Session.objects.get_or_create(exercice=ex_for_member, date_session=date.today())
    membre = Membre.objects.create(
        utilisateur=user,
        numero_membre=f'SIM-{unique}',
        date_inscription=date.today(),
        statut='EN_REGLE',
        exercice_inscription=ex_for_member,
        session_inscription=session_for_member
    )

    session = Session.get_session_en_cours() or Session.objects.filter(exercice=fonds.exercice).first() or Session.objects.create(exercice=fonds.exercice, date_session=date.today())

    # Créer le paiement de solidarité via la classe; appeler explicitement save()
    paiement = PaiementSolidarite(
        membre=membre,
        session=session,
        montant=montant,
        notes='Simulation paiement solidarité'
    )
    print("Avant save paiement, pk=", paiement.pk)
    paiement.save()
    print("Après save paiement, pk=", paiement.pk)

    # recharger le fonds et afficher
    fonds.refresh_from_db()
    print("Fonds après  :", fonds.montant_total)

    # Afficher derniers mouvements pour vérification
    print("\nDerniers mouvements:")
    for m in fonds.mouvements.order_by('-date_mouvement')[:10]:
        print(f"{m.date_mouvement} | {m.type_mouvement} | {m.montant} | {m.description}")


if __name__ == '__main__':
    main()
