<<<<<<< HEAD
# -*- coding: utf-8 -*-
from odoo import models, fields, api
import logging
=======
import logging
from odoo import models, api, fields
>>>>>>> 3e55d22cdc5e8207ec13690ca33b5b329d25d765

_logger = logging.getLogger(__name__)


class ResUsers(models.Model):
    _inherit = 'res.users'

<<<<<<< HEAD
    def write(self, vals):
        """
        Override write to automatically configure Premium Manager when assigned.

        This method detects when the Premium Manager group is added to a user
        and automatically:
        1. Adds all required implied_ids groups (Settings, CRM, Accounting, etc.)
        2. Creates a website for the user's company if needed
        3. Ensures proper company assignment
        """
        # Avoid infinite recursion: skip if we're already auto-configuring
        if self.env.context.get('skip_premium_auto_config'):
            return super(ResUsers, self).write(vals)

        res = super(ResUsers, self).write(vals)
=======
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
>>>>>>> 3e55d22cdc5e8207ec13690ca33b5b329d25d765

        # Check if groups were modified
        if 'group_ids' in vals or 'groups_id' in vals:
            for user in self:
<<<<<<< HEAD
                self._auto_configure_premium_manager(user)

        return res

    def _auto_configure_premium_manager(self, user):
        """
        Auto-configure a Premium Manager user:
        1. Check if user has Premium Manager group
        2. Add all required groups (implied_ids) if missing
        3. Ensure user has a company
        4. Create website for the company if needed
        """
        # Get Premium Manager group
        try:
            premium_group = self.env.ref('onedesk_core.group_onedesk_premium_manager')
        except:
            return  # Group doesn't exist yet

        # Check if user is Premium Manager
        if premium_group not in user.group_ids:
            return  # Not a Premium Manager, nothing to do

        _logger.info(f"🔧 Auto-configuring Premium Manager: {user.name}")

        # 1. Add required groups (implied_ids) if missing
        required_groups_xml_ids = [
            'base.group_erp_manager',           # Settings
            'sales_team.group_sale_manager',    # CRM
            'website.group_website_designer',   # Website
            'account.group_account_manager',    # Accounting
            'base.group_partner_manager',       # Contacts
        ]

        groups_to_add = []
        for xml_id in required_groups_xml_ids:
            try:
                group = self.env.ref(xml_id)
                if group not in user.group_ids:
                    groups_to_add.append(group.id)
                    _logger.info(f"  ➕ Adding missing group: {group.name}")
            except:
                _logger.warning(f"  ⚠️ Group {xml_id} not found, skipping")

        # Add all missing groups at once (with context to avoid recursion)
        if groups_to_add:
            user.sudo().with_context(skip_premium_auto_config=True).write({
                'group_ids': [(4, gid) for gid in groups_to_add]
            })
            _logger.info(f"  ✅ Added {len(groups_to_add)} missing groups")

        # 2. Ensure user has a company
        if not user.company_id:
            default_company = self.env['res.company'].search([], limit=1)
            if default_company:
                user.sudo().with_context(skip_premium_auto_config=True).write({
                    'company_id': default_company.id,
                    'company_ids': [(6, 0, [default_company.id])]  # ONLY this company!
                })
                _logger.info(f"  ✅ Assigned company: {default_company.name}")
        else:
            # Ensure company_ids contains ONLY the user's company (not admin's companies)
            if set(user.company_ids.ids) != {user.company_id.id}:
                user.sudo().with_context(skip_premium_auto_config=True).write({
                    'company_ids': [(6, 0, [user.company_id.id])]  # Replace with ONLY user's company
                })
                _logger.info(f"  ✅ Restricted access to ONLY company: {user.company_id.name}")

        # 3. Create website for the company if needed
        if user.company_id:
            existing_website = self.env['website'].sudo().search([
                ('company_id', '=', user.company_id.id)
            ], limit=1)

            if not existing_website:
                unique_domain = f'company-{user.company_id.id}.local'
                new_website = self.env['website'].sudo().create({
                    'name': f'Site {user.company_id.name}',
                    'company_id': user.company_id.id,
                    'domain': unique_domain,
                })
                _logger.info(f"  ✅ Created website: {new_website.name} (ID: {new_website.id})")
            else:
                _logger.info(f"  ℹ️ Website already exists: {existing_website.name}")

        _logger.info(f"✅ Premium Manager auto-configuration completed for {user.name}")
=======
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
>>>>>>> 3e55d22cdc5e8207ec13690ca33b5b329d25d765
