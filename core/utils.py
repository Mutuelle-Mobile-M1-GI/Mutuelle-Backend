from decimal import Decimal, ROUND_HALF_UP
from django.db.models import Sum, Q
from django.utils import timezone



def calculer_fonds_social_total():
    """
    Calcule le montant total du fonds social pour l'exercice en cours
    """
    from core.models import FondsSocial
    
    fonds = FondsSocial.get_fonds_actuel()
    if fonds:
        return {
            'montant_total': fonds.montant_total,
            'exercice': fonds.exercice.nom,
            'derniere_modification': fonds.date_modification
        }
    return {
        'montant_total': Decimal('0'),
        'exercice': 'Aucun exercice en cours',
        'derniere_modification': None
    }

def calculer_cumul_epargnes_total():
    """
    Calcule le cumul total des fonds (épargne + gains) de tous les membres
    """
    from core.models import Membre
    from decimal import Decimal
    
    total_tresor = Decimal('0')
    membres_actifs = Membre.objects.filter(statut__in=['EN_REGLE', 'NON_EN_REGLE'])
    
    for membre in membres_actifs:
        # On utilise solde_total_global qui fait : calculer_epargne_pure + calculer_total_gains
        solde_membre = membre.solde_total_global
        total_tresor += solde_membre
    
    return {
        'cumul_total_epargnes': total_tresor,
        'nombre_membres': membres_actifs.count()
    }


def calculer_tresor_disponible():
    """
    ✅ NOUVEAU : Calcule les liquidités réellement disponibles dans le trésor
    pour les emprunts (entrées - sorties)
    """
    from transactions.models import EpargneTransaction
    from django.db.models import Sum
    from decimal import Decimal
    
    TYPES_ENTREES_TRESOR = ['DEPOT', 'RETOUR_REMBOURSEMENT']
    
    total_entrees = EpargneTransaction.objects.filter(
        type_transaction__in=TYPES_ENTREES_TRESOR,
        montant__gt=0
    ).aggregate(total=Sum('montant'))['total'] or Decimal('0')
    
    total_sorties = EpargneTransaction.objects.filter(
        type_transaction__in=['RETRAIT_PRET', 'RETRAIT_RENFLOUEMENT'],
        montant__lt=0
    ).aggregate(total=Sum('montant'))['total'] or Decimal('0')
    
    tresor_disponible = total_entrees + total_sorties  # total_sorties est déjà négatif
    
    return {
        'total_entrees': total_entrees,
        'total_sorties': total_sorties,
        'tresor_disponible': tresor_disponible,
        'peut_emprunter': tresor_disponible > 0
    }

def calculer_donnees_administrateur():
    """
    Calcule toutes les données que l'administrateur doit voir
    """
    fonds_social = calculer_fonds_social_total()
    tresor = calculer_cumul_epargnes_total()
    tresor_disponible = calculer_tresor_disponible()  # ✅ NOUVEAU
    
    # Calcul des montants attendus (emprunts en cours)
    from transactions.models import Emprunt
    emprunts_en_cours = Emprunt.objects.filter(statut='EN_COURS')
    
    montant_attendu_emprunts = sum(
        emprunt.montant_restant_a_rembourser for emprunt in emprunts_en_cours
    )
    
    return {
        'fonds_social': fonds_social,
        'tresor': tresor,
        'tresor_disponible': tresor_disponible,  # ✅ NOUVEAU
        'emprunts_en_cours': {
            'nombre': emprunts_en_cours.count(),
            'montant_total_attendu': montant_attendu_emprunts
        },
        'situation_globale': {
            'liquidites_totales': fonds_social['montant_total'] + tresor['cumul_total_epargnes'],
            'tresor_liquide': tresor_disponible['tresor_disponible'],  # ✅ NOUVEAU
            'engagements_totaux': montant_attendu_emprunts,
            'peut_emprunter': tresor_disponible['peut_emprunter']  # ✅ NOUVEAU
        }
    }

def calculer_donnees_membre_completes(membre):
    """
    Calcule TOUTES les données financières d'un membre
    Cette fonction est cruciale car elle retourne toutes les informations
    que le frontend doit afficher selon les spécifications
    ✅ VERSION AMÉLIORÉE avec montants historiques corrects
    """
    from core.models import ConfigurationMutuelle, Session,Exercice
    from transactions.models import (
        PaiementInscription, PaiementSolidarite, EpargneTransaction,
        Emprunt, Renflouement, RetraitEpargne
    )
    
    config = ConfigurationMutuelle.get_configuration()
    session_courante = Session.get_session_en_cours()
    
    # 1. INSCRIPTION ✅ AMÉLIORÉ
    premier_paiement_inscription = PaiementInscription.objects.filter(
        membre=membre
    ).order_by('date_paiement').first()

    if premier_paiement_inscription:
        montant_total_inscription = premier_paiement_inscription.montant_inscription_du
    else:
        montant_total_inscription = config.montant_inscription

    total_paye_inscription = PaiementInscription.objects.filter(
        membre=membre
    ).aggregate(total=Sum('montant'))['total'] or Decimal('0')
    
    inscription_data = {
        'montant_total_inscription': montant_total_inscription,
        'montant_paye_inscription': total_paye_inscription,
        'montant_restant_inscription': max(montant_total_inscription - total_paye_inscription,0),
        'inscription_complete': membre.inscription_terminee,
        'pourcentage_inscription': (total_paye_inscription / montant_total_inscription * 100) 
                                   if montant_total_inscription > 0 else 0
    }
    
    # 2. SOLIDARITÉ (logique LIFETIME)
    # La solidarité est un paiement unique à vie. On se base sur le flag
    # `membre.solidarite_terminee` pour déterminer si la solidarité est à jour.
    solidarite_data = {}

    exercice_courant = Exercice.get_exercice_en_cours()
    # Montant de base de la solidarité (config)
    montant_solidarite_base = config.montant_solidarite

    # Total payé TOUTES sessions confondues (solidarité = paiement à vie)
    total_solidarite_payee = PaiementSolidarite.objects.filter(
        membre=membre
    ).aggregate(total=Sum('montant'))['total'] or Decimal('0')

    # Ne plus utiliser les reports pour déterminer si la solidarité est à jour.
    # On conserve les reports pour l'historique comptable si nécessaire,
    # mais ils n'affectent pas le flag `solidarite_terminee`.
    montant_reporte = Decimal('0')
    total_solidarite_due = montant_solidarite_base

    # Assurer que le flag est à jour en appelant la méthode (ne sauvegarde pas)
    try:
        membre.update_solidarite_terminee()
    except Exception:
        pass

    solidarite_data.update({
        'exercice': exercice_courant.nom if exercice_courant else None,
        'montant_solidarite_base': montant_solidarite_base,
        'montant_reporte': montant_reporte,  # reports non utilisés pour le statut
        'total_solidarite_due': total_solidarite_due,
        'total_solidarite_payee': total_solidarite_payee,
        'dette_solidarite_cumul': max(total_solidarite_due - total_solidarite_payee, Decimal('0')),
        'solidarite_a_jour': membre.solidarite_terminee
    })

    if session_courante:
        solidarite_data.update({
            'montant_solidarite_session_courante': max(total_solidarite_due - total_solidarite_payee, Decimal('0')),
            'montant_paye_session_courante': PaiementSolidarite.objects.filter(
                membre=membre,
                session=session_courante
            ).aggregate(total=Sum('montant'))['total'] or Decimal('0'),
            'montant_restant_session_courante': max(total_solidarite_due - total_solidarite_payee, Decimal('0')),
            'solidarite_session_courante_complete': membre.solidarite_terminee
        })

    
    # 3. ÉPARGNES ET INTÉRÊTS
    transactions_epargne = EpargneTransaction.objects.filter(membre=membre)
    
    epargne_base = transactions_epargne.filter(
        type_transaction='DEPOT'
    ).aggregate(total=Sum('montant'))['total'] or Decimal('0')
    
    retraits_prets = transactions_epargne.filter(
        type_transaction='RETRAIT_PRET'
    ).aggregate(total=Sum('montant'))['total'] or Decimal('0')
    
    interets_recus = transactions_epargne.filter(
        type_transaction='AJOUT_INTERET'
    ).aggregate(total=Sum('montant'))['total'] or Decimal('0')
    
    retours_remboursements = transactions_epargne.filter(
        type_transaction='RETOUR_REMBOURSEMENT'
    ).aggregate(total=Sum('montant'))['total'] or Decimal('0')
    
    epargne_totale = epargne_base + interets_recus

    # Retraits d'épargne effectués (via RetraitEpargne + EpargneTransaction RETRAIT_EPARGNE)
    total_retraits_epargne_model = RetraitEpargne.objects.filter(
        membre=membre
    ).aggregate(total=Sum('montant'))['total'] or Decimal('0')

    total_retraits_epargne_tx = transactions_epargne.filter(
        type_transaction='RETRAIT_EPARGNE'
    ).aggregate(total=Sum('montant'))['total'] or Decimal('0')

    # On prend le max des deux pour éviter le double-comptage
    total_retraits_epargne = max(total_retraits_epargne_model, abs(total_retraits_epargne_tx))

    # NOUVEAU: Retraits pour renflouement (via EpargneTransaction RETRAIT_RENFLOUEMENT)
    total_retraits_renflouement = transactions_epargne.filter(
        type_transaction='RETRAIT_RENFLOUEMENT'
    ).aggregate(total=Sum('montant'))['total'] or Decimal('0')
    total_retraits_renflouement = abs(total_retraits_renflouement)
    
    # Calcul du bilan net (Épargne brute + Intérêts - Retraits - Renflouements)
    # L'utilisateur souhaite finalement que bilan_epargne corresponde à epargne_totale
    bilan_epargne = epargne_totale - total_retraits_renflouement - total_retraits_epargne

    epargne_data = {
        'epargne_base': epargne_base,
        'retraits_pour_prets': retraits_prets,
        'interets_recus': interets_recus,
        'retours_remboursements': retours_remboursements,
        'epargne_totale': bilan_epargne, # Correspondance avec bilan_epargne
        'epargne_plus_interets': epargne_totale, # Retour à la valeur brute épargne+intérêts
        'montant_interets_separe': interets_recus,
        'total_retraits_epargne': total_retraits_epargne,
        'total_retraits_renflouement': total_retraits_renflouement,
        'bilan_epargne': bilan_epargne,
    }
    
    # 4. EMPRUNTS
    emprunt_en_cours = Emprunt.objects.filter(
     membre=membre,
     statut='EN_COURS'
    ).first()

    emprunt_data = {
        'a_emprunt_en_cours': emprunt_en_cours is not None,
        'montant_emprunt_en_cours': emprunt_en_cours.montant_emprunte if emprunt_en_cours else Decimal('0'),
        'montant_total_a_rembourser': emprunt_en_cours.montant_total_a_rembourser if emprunt_en_cours else Decimal('0'),
        'montant_deja_rembourse': emprunt_en_cours.montant_rembourse if emprunt_en_cours else Decimal('0'),
        'montant_restant_a_rembourser': emprunt_en_cours.montant_restant_a_rembourser if emprunt_en_cours else Decimal('0'),
        'pourcentage_rembourse': emprunt_en_cours.pourcentage_rembourse if emprunt_en_cours else 0,
        'nombre_emprunts_total': Emprunt.objects.filter(membre=membre).count(),
        'montant_max_empruntable': Decimal('0')
        }


    montant_max_empruntable = Decimal('0')
    exercice = None  


    if not emprunt_en_cours and epargne_totale > 0:
        exercice = Exercice.get_exercice_en_cours() # Requiert l'import d'Exercice au début de la fonction
    
        if exercice:
        # On cherche la tranche qui correspond à l'épargne actuelle
            tier = exercice.emprunt_tiers.filter(
                min_amount__lte=epargne_totale,
                max_amount__gte=epargne_totale
                ).first()
            if tier:
            # Calcul : Epargne * Coefficient de la tranche
                    montant_calcule = epargne_totale * Decimal(str(tier.coefficient))
            # On applique le plafond (max_cap) s'il existe
                    if tier.max_cap and tier.max_cap > 0:
                        montant_max_empruntable = min(montant_calcule, tier.max_cap)
                    else:
                        montant_max_empruntable = montant_calcule
                    print(f"SUCCESS: Tranche {tier.id} trouvée. Max empruntable: {montant_max_empruntable}")
        else:
            print(f"ERROR: Aucune tranche trouvée pour l'épargne {epargne_totale}")
        emprunt_data['montant_max_empruntable'] = montant_max_empruntable
   
    
    # 5. RENFLOUEMENTS
    renflouements_dus = Renflouement.objects.filter(membre=membre)
    
    total_renflouement_du = renflouements_dus.aggregate(
        total=Sum('montant_du')
    )['total'] or Decimal('0')
    
    total_renflouement_paye = renflouements_dus.aggregate(
        total=Sum('montant_paye')
    )['total'] or Decimal('0')
    
    renflouement_data = {
        'total_renflouement_du': total_renflouement_du,
        'total_renflouement_paye': total_renflouement_paye,
        'solde_renflouement_du': total_renflouement_du - total_renflouement_paye,
        'renflouement_a_jour': total_renflouement_paye >= total_renflouement_du,
        'nombre_renflouements': renflouements_dus.count()
    }
    
    # 6. STATUT GLOBAL "EN RÈGLE"
    # ✅ NOUVELLE LOGIQUE: Période de grâce de 3 mois par exercice
    
    from core.models import Membre
    peut_definir_statuts = Membre.peut_definir_statuts_membre(membre)
    
    if not peut_definir_statuts:
        # Période de grâce: conserver le statut existant du membre
        en_regle = membre.statut == 'EN_REGLE'
        print(f"⏳ Membre {membre.numero_membre}: Période de grâce → maintien du statut {membre.statut}")
    else:
        # Après 3 mois: évaluation selon les critères
        if solidarite_data['solidarite_a_jour']:
            print('✅ Solidarité à jour')
        else:
            print('❌ Solidarité pas à jour')

        en_regle = (
            solidarite_data['solidarite_a_jour'] and
            renflouement_data['renflouement_a_jour'] and
            inscription_data['inscription_complete']
        )
        print(f"✅ Membre {membre.numero_membre}: Évaluation après période de grâce = {en_regle}")
    
    # 7. DONNÉES CONSOLIDÉES
    donnees_completes = {
        'membre_info': {
            'id': str(membre.id),
            'numero_membre': membre.numero_membre,
            'nom_complet': membre.utilisateur.nom_complet,
            'email': membre.utilisateur.email,
            'telephone': membre.utilisateur.telephone,
            'photo_profil_url': membre.utilisateur.photo_profil.url if membre.utilisateur.photo_profil else None,
            'date_inscription': membre.date_inscription,
            'statut': membre.statut,
            'en_regle': en_regle
        },
        'inscription': inscription_data,
        'solidarite': solidarite_data,
        'epargne': epargne_data,
        'emprunt': emprunt_data,
        'renflouement': renflouement_data,
        'resume_financier': {
            'patrimoine_total': bilan_epargne,
            'obligations_totales': (
                inscription_data['montant_restant_inscription'] +
                solidarite_data['dette_solidarite_cumul'] +
                renflouement_data['solde_renflouement_du'] +
                emprunt_data['montant_restant_a_rembourser']
            ),
            'situation_nette': bilan_epargne - emprunt_data['montant_restant_a_rembourser']
        }
    }
    
    print(f"Calcul complet pour {membre.numero_membre}: En règle = {en_regle}")
    return donnees_completes