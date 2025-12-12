# -*- coding: utf-8 -*-
"""Migration 19.0.1.0.0: Auto-configuration des Premium Managers existants"""

import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """Auto-configure tous les utilisateurs Premium Manager existants"""
    from odoo import api, SUPERUSER_ID

    env = api.Environment(cr, SUPERUSER_ID, {})

    _logger.info("=" * 80)
    _logger.info("MIGRATION: Auto-configuration Premium Managers")
    _logger.info("=" * 80)

    try:
        # Trouver le groupe Premium Manager
        try:
            premium_group = env.ref('onedesk_core.group_onedesk_premium_manager')
        except:
            _logger.info("ℹ️ Groupe Premium Manager non trouvé, skip auto-configuration")
            return

        # Trouver tous les utilisateurs qui ont ce groupe
        premium_users = env['res.users'].sudo().search([
            ('groups_id', 'in', [premium_group.id])
        ])

        if not premium_users:
            _logger.info("ℹ️ Aucun utilisateur Premium Manager à configurer")
            return

        _logger.info(f"🔧 Auto-configuration de {len(premium_users)} utilisateur(s) Premium Manager...")

        # Groupes requis
        required_groups_xml_ids = [
            'base.group_erp_manager',           # Settings
            'sales_team.group_sale_manager',    # CRM
            'website.group_website_designer',   # Website
            'account.group_account_manager',    # Accounting
            'base.group_partner_manager',       # Contacts
        ]

        configured_count = 0
        for user in premium_users:
            _logger.info(f"\n👤 Configuration de {user.name} (ID: {user.id})...")
            groups_added = []

            # 1. Ajouter les groupes manquants
            for xml_id in required_groups_xml_ids:
                try:
                    group = env.ref(xml_id)
                    if group not in user.groups_id:
                        user.sudo().write({'groups_id': [(4, group.id)]})
                        groups_added.append(group.name)
                        _logger.info(f"  ✓ Groupe ajouté: {group.name}")
                except Exception as e:
                    _logger.warning(f"  ⚠️ Impossible d'ajouter le groupe {xml_id}: {e}")

            # 2. Assurer que l'utilisateur a une company
            if not user.company_id:
                default_company = env['res.company'].sudo().search([], limit=1)
                if default_company:
                    user.sudo().write({
                        'company_id': default_company.id,
                        'company_ids': [(6, 0, [default_company.id])]
                    })
                    _logger.info(f"  ✓ Company assignée: {default_company.name}")
            else:
                # Restreindre à SA company uniquement
                if set(user.company_ids.ids) != {user.company_id.id}:
                    user.sudo().write({
                        'company_ids': [(6, 0, [user.company_id.id])]
                    })
                    _logger.info(f"  ✓ Accès restreint à: {user.company_id.name}")

            # 3. Créer le website pour la company si besoin
            if user.company_id:
                existing_website = env['website'].sudo().search([
                    ('company_id', '=', user.company_id.id)
                ], limit=1)

                if not existing_website:
                    unique_domain = f'company-{user.company_id.id}.local'
                    new_website = env['website'].sudo().create({
                        'name': f'Site {user.company_id.name}',
                        'company_id': user.company_id.id,
                        'domain': unique_domain,
                    })
                    _logger.info(f"  ✓ Website créé: {new_website.name} (ID: {new_website.id})")
                else:
                    _logger.info(f"  ℹ️ Website existe déjà: {existing_website.name}")

            if groups_added or not existing_website:
                configured_count += 1

        _logger.info(f"\n✅ Migration terminée: {configured_count}/{len(premium_users)} utilisateur(s) configuré(s)")

    except Exception as e:
        _logger.error(f"❌ Erreur lors de la migration: {e}", exc_info=True)

    _logger.info("=" * 80)
