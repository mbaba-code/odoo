# -*- coding: utf-8 -*-
from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)


class ResUsers(models.Model):
    _inherit = 'res.users'

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

        # Check if groups were modified
        if 'group_ids' in vals or 'groups_id' in vals:
            for user in self:
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
