#!/usr/bin/env python
"""
Commande Django pour clôturer un exercice et créer les renflouements

Usage:
    python manage.py cloturer_exercice [--exercice-id=<uuid>]
    python manage.py cloturer_exercice --exercice-id=12345678-1234-5678-1234-567812345678
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from core.models import Exercice, Membre
from decimal import Decimal


class Command(BaseCommand):
    help = 'Clôture un exercice et crée les renflouements pour les membres EN_REGLE'

    def add_arguments(self, parser):
        parser.add_argument(
            '--exercice-id',
            type=str,
            help='UUID de l\'exercice à clôturer. Si non fourni, utilise l\'exercice EN_COURS'
        )

    def handle(self, *args, **options):
        exercice_id = options.get('exercice_id')
        
        # Récupérer l'exercice
        if exercice_id:
            try:
                exercice = Exercice.objects.get(id=exercice_id)
            except Exercice.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f'❌ Exercice avec ID {exercice_id} non trouvé')
                )
                return
        else:
            exercice = Exercice.get_exercice_en_cours()
            if not exercice:
                self.stdout.write(
                    self.style.ERROR('❌ Aucun exercice EN_COURS trouvé')
                )
                return
        
        self.stdout.write(
            self.style.SUCCESS(f'\n📋 CLÔTURE DE L\'EXERCICE: {exercice.nom}')
        )
        self.stdout.write('=' * 70)
        
        # Vérifier le statut de l'exercice
        if exercice.statut != 'EN_COURS':
            self.stdout.write(
                self.style.WARNING(f'⚠️  Cet exercice a le statut: {exercice.statut}')
            )
            response = input(f'Voulez-vous continuer? (o/n): ')
            if response.lower() != 'o':
                self.stdout.write(self.style.WARNING('Opération annulée'))
                return
        
        try:
            with transaction.atomic():
                # 1. Créer les renflouements
                result = exercice.creer_renflouements_fin_exercice()
                
                # 2. Mettre à jour le statut de l'exercice
                exercice.statut = 'TERMINE'
                exercice.save()
                self.stdout.write(
                    self.style.SUCCESS(f'✅ Exercice {exercice.nom} marqué comme TERMINÉ')
                )
                
                # 3. Afficher le résumé
                self.stdout.write('\n' + '=' * 70)
                self.stdout.write(self.style.SUCCESS('📊 RÉSUMÉ DE LA CLÔTURE'))
                self.stdout.write('=' * 70)
                self.stdout.write(
                    f'💰 Total des dépenses: {result["total_depenses"]:,.0f} FCFA'
                )
                self.stdout.write(
                    f'👥 Nombre de membres EN_REGLE: {result["nombre_membres"]}'
                )
                self.stdout.write(
                    f'📊 Montant par membre: {result["montant_par_membre"]:,.0f} FCFA'
                )
                self.stdout.write(
                    f'✅ Renflouements créés: {result["renflouements_crees"]}'
                )
                self.stdout.write('=' * 70 + '\n')
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ ERREUR lors de la clôture: {str(e)}')
            )
            raise
