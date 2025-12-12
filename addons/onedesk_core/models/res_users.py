import logging
from odoo import models, api, fields

_logger = logging.getLogger(__name__)


class ResUsers(models.Model):
    _inherit = 'res.users'

    @api.model_create_multi
    def create(self, vals_list):
        """Override create to setup Premium Manager users automatically"""
        users = super().create(vals_list)

        for user in users:
            # Setup Premium Manager if needed
            self._setup_premium_manager(user)

        return users

    def write(self, vals):
        """Override write to detect Premium Manager group assignment"""
        res = super().write(vals)

        # Check if groups were modified
        if 'group_ids' in vals or 'groups_id' in vals:
            for user in self:
                self._setup_premium_manager(user)

        return res

    def _setup_premium_manager(self, user):
        """
        Configure automatiquement un utilisateur Premium Manager :
        1. Vérifier qu'il a une company_id
        2. Créer un website pour sa company si nécessaire
        3. Marquer la company comme OneDesk client
        """
        # Vérifier si l'utilisateur est Premium Manager
        premium_group = self.env.ref('onedesk_core.group_onedesk_premium_manager', raise_if_not_found=False)
        if not premium_group:
            return

        # Vérifier si user a ce groupe (utiliser group_ids au lieu de groups_id)
        try:
            is_premium = premium_group.id in user.group_ids.ids
        except AttributeError:
            # Fallback si group_ids n'existe pas
            try:
                is_premium = user.has_group('onedesk_core.group_onedesk_premium_manager')
            except:
                return

        if not is_premium:
            return

        _logger.info(f"🔧 Setup Premium Manager pour {user.name}")

        # 1. S'assurer que l'utilisateur a une company
        if not user.company_id:
            default_company = self.env['res.company'].sudo().search([], limit=1)
            if default_company:
                user.sudo().write({'company_id': default_company.id})
                _logger.info(f"   ✅ Company assignée: {default_company.name}")

        if not user.company_id:
            _logger.warning(f"   ❌ Impossible d'assigner une company à {user.name}")
            return

        # 2. Marquer la company comme client OneDesk
        company = user.company_id
        if not company.is_onedesk_client:
            company.sudo().write({'is_onedesk_client': True})
            _logger.info(f"   ✅ Company {company.name} marquée comme client OneDesk")

        # 3. Créer un website pour cette company si nécessaire
        self._ensure_company_website(company)

    def _ensure_company_website(self, company):
        """
        S'assurer qu'une company a au moins un website
        Sinon, en créer un automatiquement
        """
        # Vérifier si le module website est installé
        if 'website' not in self.env:
            _logger.warning("   ⚠️ Module 'website' non installé")
            return

        # Chercher si un website existe déjà pour cette company
        existing_website = self.env['website'].sudo().search([
            ('company_id', '=', company.id)
        ], limit=1)

        if existing_website:
            _logger.info(f"   ✅ Website existant: {existing_website.name}")
            return

        # Créer un nouveau website pour cette company
        try:
            new_website = self.env['website'].sudo().create({
                'name': f'Site {company.name}',
                'company_id': company.id,
                'domain': '',  # À configurer plus tard
            })
            _logger.info(f"   ✅ Nouveau website créé: {new_website.name} (ID: {new_website.id})")

            # Créer les pages de base (optionnel)
            self._create_default_website_pages(new_website)

        except Exception as e:
            _logger.error(f"   ❌ Erreur création website: {e}")

    def _create_default_website_pages(self, website):
        """Créer les pages de base pour un nouveau website"""
        try:
            # Page d'accueil
            homepage = self.env['website.page'].sudo().create({
                'name': 'Home',
                'website_id': website.id,
                'url': '/',
                'is_published': True,
                'view_id': self.env['ir.ui.view'].sudo().create({
                    'name': f'Homepage {website.name}',
                    'type': 'qweb',
                    'key': f'website.homepage_{website.id}',
                    'arch': '''
                        <t name="Homepage" t-name="website.homepage">
                            <t t-call="website.layout">
                                <div id="wrap" class="oe_structure oe_empty">
                                    <section class="s_cover pt96 pb96">
                                        <div class="container">
                                            <h1 class="text-center">Bienvenue</h1>
                                            <p class="lead text-center">Votre site est prêt à être personnalisé</p>
                                        </div>
                                    </section>
                                </div>
                            </t>
                        </t>
                    ''',
                }).id,
            })
            _logger.info(f"      ✅ Page d'accueil créée")

        except Exception as e:
            _logger.warning(f"      ⚠️ Impossible de créer les pages par défaut: {e}")
