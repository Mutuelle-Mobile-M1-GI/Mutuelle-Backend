"""
Management command pour gérer le fonds social de manière indépendante
Permet de définir, consulter ou modifier le montant du fonds social
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from core.models import FondsSocial, Exercice, MouvementFondsSocial
from decimal import Decimal


class Command(BaseCommand):
    help = 'Gère le fonds social de la mutuelle (consultation, modification indépendante)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--exercice',
            type=str,
            help='UUID ou nom de l\'exercice (par défaut: exercice en cours)',
        )
        parser.add_argument(
            '--montant',
            type=float,
            help='Nouveau montant du fonds social (en FCFA)',
        )
        parser.add_argument(
            '--operation',
            type=str,
            choices=['set', 'add', 'subtract', 'view'],
            default='view',
            help='Opération à effectuer: set (définir), add (ajouter), subtract (retirer), view (consulter)',
        )
        parser.add_argument(
            '--description',
            type=str,
            default='Modification manuelle du fonds social',
            help='Description de l\'opération',
        )

    def handle(self, *args, **options):
        operation = options.get('operation', 'view')
        exercice_input = options.get('exercice')
        montant = options.get('montant')
        description = options.get('description')

        # Récupérer l'exercice
        try:
            if exercice_input:
                # Essayer par UUID d'abord
                try:
                    exercice = Exercice.objects.get(id=exercice_input)
                except:
                    # Sinon par nom
                    exercice = Exercice.objects.get(nom__icontains=exercice_input)
            else:
                # Exercice en cours par défaut
                exercice = Exercice.get_exercice_en_cours()
                if not exercice:
                    self.stdout.write(
                        self.style.ERROR('❌ Aucun exercice en cours trouvé et aucun exercice spécifié')
                    )
                    return

            self.stdout.write(
                self.style.SUCCESS(f'✅ Exercice sélectionné: {exercice.nom} ({exercice.id})')
            )
        except Exercice.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f'❌ Exercice introuvable: {exercice_input}')
            )
            return

        # Récupérer ou créer le fonds social
        fonds, created = FondsSocial.objects.get_or_create(exercice=exercice)
        
        if created:
            self.stdout.write(
                self.style.WARNING(f'⚠️ Fonds social créé pour cet exercice')
            )

        # Effectuer l'opération demandée
        if operation == 'view':
            self._view_fonds_social(fonds)

        elif operation == 'set':
            if montant is None:
                self.stdout.write(
                    self.style.ERROR('❌ Vous devez spécifier --montant avec --operation set')
                )
                return
            self._set_fonds_social(fonds, montant, description)

        elif operation == 'add':
            if montant is None:
                self.stdout.write(
                    self.style.ERROR('❌ Vous devez spécifier --montant avec --operation add')
                )
                return
            self._add_to_fonds_social(fonds, montant, description)

        elif operation == 'subtract':
            if montant is None:
                self.stdout.write(
                    self.style.ERROR('❌ Vous devez spécifier --montant avec --operation subtract')
                )
                return
            self._subtract_from_fonds_social(fonds, montant, description)

    def _view_fonds_social(self, fonds):
        """Affiche les informations du fonds social"""
        self.stdout.write(self.style.SUCCESS('\n' + '=' * 70))
        self.stdout.write(self.style.SUCCESS('📊 INFORMATIONS DU FONDS SOCIAL'))
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write(f'Exercice: {fonds.exercice.nom}')
        self.stdout.write(f'Montant total: {fonds.montant_total:,.2f} FCFA')
        self.stdout.write(f'Créé le: {fonds.date_creation.strftime("%d/%m/%Y %H:%M:%S")}')
        self.stdout.write(f'Modifié le: {fonds.date_modification.strftime("%d/%m/%Y %H:%M:%S")}')
        
        # Afficher les 10 derniers mouvements
        mouvements = fonds.mouvements.all()[:10]
        if mouvements:
            self.stdout.write(self.style.SUCCESS('\n📋 DERNIERS MOUVEMENTS:'))
            self.stdout.write('-' * 70)
            for mouvement in reversed(mouvements):
                symbole = '➕' if mouvement.type_mouvement == 'ENTREE' else '➖'
                couleur = self.style.SUCCESS if mouvement.type_mouvement == 'ENTREE' else self.style.WARNING
                self.stdout.write(
                    couleur(
                        f'{symbole} {mouvement.montant:>12,.2f} FCFA | '
                        f'{mouvement.date_mouvement.strftime("%d/%m/%Y %H:%M")} | '
                        f'{mouvement.description}'
                    )
                )
        else:
            self.stdout.write(self.style.WARNING('⚠️ Aucun mouvement enregistré'))
        
        self.stdout.write(self.style.SUCCESS('=' * 70 + '\n'))

    def _set_fonds_social(self, fonds, montant, description):
        """Définit le montant du fonds social"""
        montant = Decimal(str(montant))
        ancien_montant = fonds.montant_total
        
        if montant < 0:
            self.stdout.write(
                self.style.ERROR('❌ Le montant ne peut pas être négatif')
            )
            return

        with transaction.atomic():
            fonds.montant_total = montant
            fonds.save()
            
            # Enregistrer le mouvement
            difference = montant - ancien_montant
            type_mouvement = 'ENTREE' if difference >= 0 else 'SORTIE'
            
            MouvementFondsSocial.objects.create(
                fonds_social=fonds,
                type_mouvement=type_mouvement,
                montant=abs(difference),
                description=f'{description} (Ancien: {ancien_montant:,.2f}, Nouveau: {montant:,.2f})'
            )

        self.stdout.write(self.style.SUCCESS('\n' + '=' * 70))
        self.stdout.write(self.style.SUCCESS('✅ FONDS SOCIAL DÉFINI'))
        self.stdout.write('=' * 70)
        self.stdout.write(f'Ancien montant: {ancien_montant:,.2f} FCFA')
        self.stdout.write(f'Nouveau montant: {montant:,.2f} FCFA')
        self.stdout.write(f'Différence: {(montant - ancien_montant):+,.2f} FCFA')
        self.stdout.write(f'Description: {description}')
        self.stdout.write(self.style.SUCCESS('=' * 70 + '\n'))

    def _add_to_fonds_social(self, fonds, montant, description):
        """Ajoute un montant au fonds social"""
        montant = Decimal(str(montant))
        
        if montant <= 0:
            self.stdout.write(
                self.style.ERROR('❌ Le montant à ajouter doit être positif')
            )
            return

        ancien_montant = fonds.montant_total
        
        with transaction.atomic():
            fonds.montant_total += montant
            fonds.save()
            
            # Enregistrer le mouvement
            MouvementFondsSocial.objects.create(
                fonds_social=fonds,
                type_mouvement='ENTREE',
                montant=montant,
                description=description
            )

        self.stdout.write(self.style.SUCCESS('\n' + '=' * 70))
        self.stdout.write(self.style.SUCCESS('✅ MONTANT AJOUTÉ AU FONDS SOCIAL'))
        self.stdout.write('=' * 70)
        self.stdout.write(f'Ancien montant: {ancien_montant:,.2f} FCFA')
        self.stdout.write(f'Montant ajouté: {montant:,.2f} FCFA')
        self.stdout.write(f'Nouveau montant: {fonds.montant_total:,.2f} FCFA')
        self.stdout.write(f'Description: {description}')
        self.stdout.write(self.style.SUCCESS('=' * 70 + '\n'))

    def _subtract_from_fonds_social(self, fonds, montant, description):
        """Retire un montant du fonds social"""
        montant = Decimal(str(montant))
        
        if montant <= 0:
            self.stdout.write(
                self.style.ERROR('❌ Le montant à retirer doit être positif')
            )
            return

        if fonds.montant_total < montant:
            self.stdout.write(
                self.style.ERROR(
                    f'❌ Fonds insuffisant!\n'
                    f'   Disponible: {fonds.montant_total:,.2f} FCFA\n'
                    f'   Demandé: {montant:,.2f} FCFA'
                )
            )
            return

        ancien_montant = fonds.montant_total
        
        with transaction.atomic():
            fonds.montant_total -= montant
            fonds.save()
            
            # Enregistrer le mouvement
            MouvementFondsSocial.objects.create(
                fonds_social=fonds,
                type_mouvement='SORTIE',
                montant=montant,
                description=description
            )

        self.stdout.write(self.style.SUCCESS('\n' + '=' * 70))
        self.stdout.write(self.style.SUCCESS('✅ MONTANT RETIRÉ DU FONDS SOCIAL'))
        self.stdout.write('=' * 70)
        self.stdout.write(f'Ancien montant: {ancien_montant:,.2f} FCFA')
        self.stdout.write(f'Montant retiré: {montant:,.2f} FCFA')
        self.stdout.write(f'Nouveau montant: {fonds.montant_total:,.2f} FCFA')
        self.stdout.write(f'Description: {description}')
        self.stdout.write(self.style.SUCCESS('=' * 70 + '\n'))
