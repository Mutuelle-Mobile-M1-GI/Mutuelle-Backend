from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Sum
from .models import (
    ConfigurationMutuelle, Exercice, Session, TypeAssistance,
    Membre, FondsSocial, MouvementFondsSocial,
    CaisseInscription, MouvementCaisseInscription,
    SolidariteExerciceReport
)

@admin.register(ConfigurationMutuelle)
class ConfigurationMutuelleAdmin(admin.ModelAdmin):
    list_display = (
        'montant_inscription_formate', 'montant_solidarite_formate', 
        'taux_interet_formate', 'date_modification'
    )
    readonly_fields = ('date_creation', 'date_modification')
    
    fieldsets = (
        ('Montants de base', {
            'fields': ('montant_inscription', 'montant_solidarite')
        }),
        ('Durée', {
            'fields': ('duree_exercice_mois',)
        }),
        ('Historique', {
            'fields': ('date_creation', 'date_modification'),
            'classes': ('collapse',)
        })
    )
    
    def montant_inscription_formate(self, obj):
        return f"{obj.montant_inscription:,.0f} FCFA"
    montant_inscription_formate.short_description = 'Inscription'
    
    def montant_solidarite_formate(self, obj):
        return f"{obj.montant_solidarite:,.0f} FCFA"
    montant_solidarite_formate.short_description = 'Solidarité'
    
    def taux_interet_formate(self, obj):
        return f"{obj.taux_interet}%"
    taux_interet_formate.short_description = 'Taux d\'intérêt'

@admin.register(Exercice)
class ExerciceAdmin(admin.ModelAdmin):
    list_display = ('nom', 'periode', 'statut_formate', 'nombre_sessions', 'date_creation')
    list_filter = ('statut', 'date_debut')
    search_fields = ('nom', 'description')
    readonly_fields = ('date_creation', 'date_modification')
    
    def periode(self, obj):
        return f"{obj.date_debut} → {obj.date_fin}"
    periode.short_description = 'Période'
    
    def statut_formate(self, obj):
        colors = {
            'EN_COURS': 'green',
            'TERMINE': 'gray',
            'PLANIFIE': 'blue'
        }
        color = colors.get(obj.statut, 'black')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color, obj.get_statut_display()
        )
    statut_formate.short_description = 'Statut'
    
    def nombre_sessions(self, obj):
        return obj.sessions.count()
    nombre_sessions.short_description = 'Sessions'

@admin.register(Session)
class SessionAdmin(admin.ModelAdmin):
    list_display = (
        'nom', 'exercice_nom', 'date_session', 'montant_collation_formate', 
        'statut_formate', 'nombre_membres'
    )
    list_filter = ('statut', 'exercice', 'date_session')
    search_fields = ('nom', 'description')
    readonly_fields = ('date_creation', 'date_modification')
    
    def exercice_nom(self, obj):
        return obj.exercice.nom
    exercice_nom.short_description = 'Exercice'
    
    def montant_collation_formate(self, obj):
        if obj.montant_collation > 0:
            return f"{obj.montant_collation:,.0f} FCFA"
        return "Aucune"
    montant_collation_formate.short_description = 'Collation'
    
    def statut_formate(self, obj):
        colors = {
            'EN_COURS': 'green',
            'TERMINEE': 'gray',
            'PLANIFIEE': 'blue'
        }
        color = colors.get(obj.statut, 'black')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color, obj.get_statut_display()
        )
    statut_formate.short_description = 'Statut'
    
    def nombre_membres(self, obj):
        return obj.nouveaux_membres.count()
    nombre_membres.short_description = 'Nouveaux membres'

@admin.register(Membre)
class MembreAdmin(admin.ModelAdmin):
    list_display = (
        'numero_membre', 'nom_complet', 'email', 'telephone',
        'statut_formate', 'epargne_totale', 'date_inscription'
    )
    list_filter = ('statut', 'exercice_inscription', 'date_inscription')
    search_fields = (
        'numero_membre', 'utilisateur__first_name', 
        'utilisateur__last_name', 'utilisateur__email'
    )
    readonly_fields = ('numero_membre', 'date_creation', 'date_modification', 'epargne_calculee')
    
    fieldsets = (
        ('Informations de base', {
            'fields': ('utilisateur', 'numero_membre', 'statut')
        }),
        ('Inscription', {
            'fields': ('date_inscription', 'exercice_inscription', 'session_inscription')
        }),
        ('Calculs', {
            'fields': ('epargne_calculee',),
            'classes': ('collapse',)
        }),
        ('Historique', {
            'fields': ('date_creation', 'date_modification'),
            'classes': ('collapse',)
        })
    )
    
    def nom_complet(self, obj):
        return obj.utilisateur.nom_complet
    nom_complet.short_description = 'Nom complet'
    
    def email(self, obj):
        return obj.utilisateur.email
    email.short_description = 'Email'
    
    def telephone(self, obj):
        return obj.utilisateur.telephone
    telephone.short_description = 'Téléphone'
    
    def statut_formate(self, obj):
        colors = {
            'EN_REGLE': 'green',
            'NON_EN_REGLE': 'orange'
        }
        color = colors.get(obj.statut, 'black')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color, obj.get_statut_display()
        )
    statut_formate.short_description = 'Statut'
    
    def epargne_totale(self, obj):
        epargne = obj.calculer_epargne_pure()
        return f"{epargne:,.0f} FCFA"
    epargne_totale.short_description = 'Épargne'
    
    def epargne_calculee(self, obj):
        if obj.pk:
            donnees = obj.get_donnees_completes()
            epargne = donnees['epargne']
            return format_html(
                '<strong>Épargne totale:</strong> {} FCFA<br>'
                '<strong>Intérêts reçus:</strong> {} FCFA<br>'
                '<strong>Épargne + Intérêts:</strong> {} FCFA',
                epargne['epargne_totale'],
                epargne['interets_recus'],
                epargne['epargne_plus_interets']
            )
        return "Enregistrez d'abord pour voir les calculs"
    epargne_calculee.short_description = 'Détails épargne'
    
    def get_readonly_fields(self, request, obj=None):
        if obj:  # Si l'objet existe déjà
            return self.readonly_fields + ('utilisateur',)
        return self.readonly_fields

@admin.register(TypeAssistance)
class TypeAssistanceAdmin(admin.ModelAdmin):
    list_display = ('nom', 'montant_formate', 'actif', 'nombre_accordees', 'date_creation')
    list_filter = ('actif', 'date_creation')
    search_fields = ('nom', 'description')
    
    def montant_formate(self, obj):
        return f"{obj.montant:,.0f} FCFA"
    montant_formate.short_description = 'Montant'
    
    def nombre_accordees(self, obj):
        return obj.assistances_accordees.filter(statut='PAYEE').count()
    nombre_accordees.short_description = 'Accordées'

@admin.register(FondsSocial)
class FondsSocialAdmin(admin.ModelAdmin):
    list_display = ('exercice_nom', 'montant_total_formate', 'derniers_mouvements', 'date_modification')
    readonly_fields = ('date_creation', 'date_modification')
    
    def exercice_nom(self, obj):
        return obj.exercice.nom
    exercice_nom.short_description = 'Exercice'
    
    def montant_total_formate(self, obj):
        return str(obj.montant_total) + " FCFA"
       
    montant_total_formate.short_description = 'Montant total'
    
    def derniers_mouvements(self, obj):
        derniers = obj.mouvements.all()[:3]
        html = ""
        for mouvement in derniers:
            color = 'green' if mouvement.type_mouvement == 'ENTREE' else 'red'
            signe = '+' if mouvement.type_mouvement == 'ENTREE' else '-'
            html += format_html(
                '<div style="color: {};">{}{} FCFA</div>',
                color, signe, mouvement.montant
            )
        return format_html(html) if html else "Aucun mouvement"
    derniers_mouvements.short_description = 'Derniers mouvements'

@admin.register(MouvementFondsSocial)
class MouvementFondsSocialAdmin(admin.ModelAdmin):
    list_display = ('fonds_social_exercice', 'type_mouvement_formate', 'montant_formate', 'description_courte', 'date_mouvement')
    list_filter = ('type_mouvement', 'date_mouvement')
    search_fields = ('description',)
    readonly_fields = ('date_mouvement',)
    
    def fonds_social_exercice(self, obj):
        return obj.fonds_social.exercice.nom
    fonds_social_exercice.short_description = 'Exercice'
    
    def type_mouvement_formate(self, obj):
        color = 'green' if obj.type_mouvement == 'ENTREE' else 'red'
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color, obj.get_type_mouvement_display()
        )
    type_mouvement_formate.short_description = 'Type'
    
    def montant_formate(self, obj):
        color = 'green' if obj.type_mouvement == 'ENTREE' else 'red'
        signe = '+' if obj.type_mouvement == 'ENTREE' else '-'
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}{} FCFA</span>',
            color, signe, obj.montant
        )
    montant_formate.short_description = 'Montant'
    
    def description_courte(self, obj):
        return obj.description[:50] + "..." if len(obj.description) > 50 else obj.description
    description_courte.short_description = 'Description'


@admin.register(SolidariteExerciceReport)
class SolidariteExerciceReportAdmin(admin.ModelAdmin):
    """
    Admin pour visualiser les reports de solidarité entre exercices.
    """
    list_display = (
        'membre_numero', 'exercice_source_nom', 'exercice_cible_nom',
        'montant_reporte_formate', 'nature_report', 'date_creation'
    )
    list_filter = ('exercice_source', 'exercice_cible')
    search_fields = ('membre__numero_membre', 'membre__utilisateur__first_name', 'membre__utilisateur__last_name')
    readonly_fields = ('date_creation',)
    ordering = ('-date_creation',)

    def membre_numero(self, obj):
        return obj.membre.numero_membre
    membre_numero.short_description = 'Membre'

    def exercice_source_nom(self, obj):
        return obj.exercice_source.nom
    exercice_source_nom.short_description = 'Exercice clôturé'

    def exercice_cible_nom(self, obj):
        return obj.exercice_cible.nom
    exercice_cible_nom.short_description = 'Exercice suivant'

    def montant_reporte_formate(self, obj):
        montant = obj.montant_reporte
        if montant > 0:
            return format_html(
                '<span style="color: orange; font-weight: bold;">+{:,.0f} FCFA</span>',
                montant
            )
        elif montant < 0:
            return format_html(
                '<span style="color: green; font-weight: bold;">{:,.0f} FCFA (crédit)</span>',
                montant
            )
        return "0 FCFA"
    montant_reporte_formate.short_description = 'Montant reporté'

    def nature_report(self, obj):
        if obj.montant_reporte > 0:
            return format_html('<span style="color: orange;">📌 Dette</span>')
        elif obj.montant_reporte < 0:
            return format_html('<span style="color: green;">✅ Surplus (crédit)</span>')
        return "✅ Soldé"
    nature_report.short_description = 'Nature'


@admin.register(CaisseInscription)
class CaisseInscriptionAdmin(admin.ModelAdmin):
    list_display = ('exercice_nom', 'montant_total_formate', 'derniers_mouvements', 'date_modification')
    readonly_fields = ('date_creation', 'date_modification')

    def exercice_nom(self, obj):
        return obj.exercice.nom
    exercice_nom.short_description = 'Exercice'

    def montant_total_formate(self, obj):
        return f"{obj.montant_total:,.0f} FCFA"
    montant_total_formate.short_description = 'Montant total'

    def derniers_mouvements(self, obj):
        from django.utils.safestring import mark_safe
        derniers = obj.mouvements.all()[:3]
        html = ""
        for mouvement in derniers:
            color = 'green' if mouvement.type_mouvement == 'ENTREE' else 'red'
            signe = '+' if mouvement.type_mouvement == 'ENTREE' else '-'
            html += format_html(
                '<div style="color: {};">{}{} FCFA</div>',
                color, signe, mouvement.montant
            )
        return mark_safe(html) if html else "Aucun mouvement"
    derniers_mouvements.short_description = 'Derniers mouvements'


@admin.register(MouvementCaisseInscription)
class MouvementCaisseInscriptionAdmin(admin.ModelAdmin):
    list_display = ('caisse_exercice', 'type_mouvement_formate', 'montant_formate', 'description_courte', 'date_mouvement')
    list_filter = ('type_mouvement', 'date_mouvement')
    search_fields = ('description',)
    readonly_fields = ('date_mouvement',)

    def caisse_exercice(self, obj):
        return obj.caisse_inscription.exercice.nom
    caisse_exercice.short_description = 'Exercice'

    def type_mouvement_formate(self, obj):
        color = 'green' if obj.type_mouvement == 'ENTREE' else 'red'
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color, obj.get_type_mouvement_display()
        )
    type_mouvement_formate.short_description = 'Type'

    def montant_formate(self, obj):
        color = 'green' if obj.type_mouvement == 'ENTREE' else 'red'
        signe = '+' if obj.type_mouvement == 'ENTREE' else '-'
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}{} FCFA</span>',
            color, signe, obj.montant
        )
    montant_formate.short_description = 'Montant'

    def description_courte(self, obj):
        return obj.description[:50] + "..." if len(obj.description) > 50 else obj.description
    description_courte.short_description = 'Description'