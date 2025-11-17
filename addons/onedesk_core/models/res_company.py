from odoo import models, fields, api


class ResCompany(models.Model):
    """Étendre le modèle Company pour supporter OneDesk multi-tenant"""
    _inherit = 'res.company'

    # OneDesk Integration
    is_onedesk_client = fields.Boolean(
        string="Client OneDesk",
        default=False,
        help="Cette Company est un client OneDesk"
    )

    onedesk_client_id = fields.One2many(
        'onedesk.client',
        'company_id',
        string="Profil OneDesk"
    )

    # Customization
    onedesk_primary_color = fields.Char(
        string="Couleur primaire",
        default="#1f77d2",
        help="Couleur principale pour la UI du client"
    )
    onedesk_secondary_color = fields.Char(
        string="Couleur secondaire",
        default="#f0f0f0"
    )

    onedesk_logo = fields.Image(
        string="Logo OneDesk",
        help="Logo affiché sur le portail client"
    )

    # Branding
    onedesk_website_title = fields.Char(
        string="Titre du site web",
        help="Titre affiché sur le portail"
    )

    onedesk_website_description = fields.Text(
        string="Description du site web",
        help="Description courte pour SEO"
    )

    # Notifications
    onedesk_notification_email = fields.Char(
        string="Email des notifications OneDesk",
        help="Email pour les notifications système OneDesk"
    )

    # Isolation tenant
    onedesk_isolated = fields.Boolean(
        string="Mode isolé",
        default=True,
        help="Si activé, les utilisateurs de cette Company ne voient que leurs données"
    )

    # Activity
    onedesk_last_login = fields.Datetime(
        string="Dernière connexion (OneDesk)"
    )
    onedesk_last_backup = fields.Datetime(
        string="Dernière sauvegarde"
    )

    # Features enabled
    onedesk_enable_channel_manager = fields.Boolean(
        string="Gestionnaire multi-canaux activé",
        default=False
    )
    onedesk_enable_accounting = fields.Boolean(
        string="Module comptable activé",
        default=False
    )
    onedesk_enable_analytics = fields.Boolean(
        string="Analytique avancée activée",
        default=False
    )

    @api.model
    def create(self, vals):
        """Créer une nouvelle Company pour OneDesk"""
        company = super().create(vals)

        # Si c'est un client OneDesk, créer le profil client automatiquement
        if vals.get('is_onedesk_client'):
            self.env['onedesk.client'].create({
                'company_id': company.id,
                'owner_partner_id': company.partner_id.id,
            })

        return company

    def _check_onedesk_isolation(self, user):
        """Vérifier si l'utilisateur a accès à cette Company OneDesk"""
        if not self.onedesk_isolated:
            return True

        # Les admins ont accès à tout
        if user.is_admin:
            return True

        # Les autres utilisateurs ne peuvent accéder que leur Company
        return user.company_id.id == self.id

    def get_onedesk_config(self):
        """Retourner la configuration OneDesk de cette Company"""
        return {
            'primary_color': self.onedesk_primary_color,
            'secondary_color': self.onedesk_secondary_color,
            'logo_url': f'/web/image/res.company/{self.id}/onedesk_logo',
            'website_title': self.onedesk_website_title,
            'website_description': self.onedesk_website_description,
            'enable_channel_manager': self.onedesk_enable_channel_manager,
            'enable_accounting': self.onedesk_enable_accounting,
            'enable_analytics': self.onedesk_enable_analytics,
        }

    def update_onedesk_last_activity(self):
        """Mettre à jour l'heure de dernière activité OneDesk"""
        self.onedesk_last_login = fields.Datetime.now()
