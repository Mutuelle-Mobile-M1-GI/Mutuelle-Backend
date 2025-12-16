#!/usr/bin/env python
"""
Script de simulation : paie l'inscription et affiche le fonds social avant/après.

Usage:
    python scripts/simulate_inscription.py

Le script configure Django, récupère la `ConfigurationMutuelle`, puis utilise
la méthode `ajouter_montant` de `FondsSocial` pour simuler le paiement d'inscription.
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
from transactions.models import PaiementInscription
import uuid


def main():
    config = ConfigurationMutuelle.get_configuration()
    montant = config.montant_inscription

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
        ex = fonds.exercice

    print("Fonds avant :", fonds.montant_total)

    # Créer un utilisateur et membre uniques pour la simulation (évite contraintes UNIQUE)
    User = get_user_model()
    unique = uuid.uuid4().hex[:8]
    username = f"sim_user_ins_{unique}"
    user, created = User.objects.get_or_create(
        username=username,
        defaults={'email': f'{username}@example.test'}
    )
    try:
        user.first_name = 'Sim'
        user.last_name = 'Ins'
        user.save()
    except Exception:
        pass

    ex_for_member = ex
    session_for_member, _ = Session.objects.get_or_create(exercice=ex_for_member, date_session=date.today())
    membre = Membre.objects.create(
        utilisateur=user,
        numero_membre=f'SIM-INS-{unique}',
        date_inscription=date.today(),
        statut='EN_REGLE',
        exercice_inscription=ex_for_member,
        session_inscription=session_for_member
    )

    session = Session.get_session_en_cours() or Session.objects.filter(exercice=fonds.exercice).first() or Session.objects.create(exercice=fonds.exercice, date_session=date.today())

    # Créer le paiement d'inscription via la classe; appeler explicitement save()
    paiement = PaiementInscription(
        membre=membre,
        session=session,
        montant=montant,
        notes='Simulation paiement inscription'
    )
    print("Avant save paiement inscription, pk=", paiement.pk)
    paiement.save()
    print("Après save paiement inscription, pk=", paiement.pk)

    fonds.refresh_from_db()
    print("Fonds après  :", fonds.montant_total)

    # Afficher derniers mouvements pour vérification
    print("\nDerniers mouvements:")
    for m in fonds.mouvements.order_by('-date_mouvement')[:10]:
        print(f"{m.date_mouvement} | {m.type_mouvement} | {m.montant} | {m.description}")


if __name__ == '__main__':
    main()
