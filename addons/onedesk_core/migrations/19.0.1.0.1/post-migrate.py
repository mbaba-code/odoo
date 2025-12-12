# -*- coding: utf-8 -*-
"""Migration: Ajouter implied_ids au groupe Premium Manager existant"""

import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """Mettre à jour le groupe Premium Manager avec implied_ids"""
    from odoo import api, SUPERUSER_ID

    env = api.Environment(cr, SUPERUSER_ID, {})

    _logger.info("=" * 80)
    _logger.info("MIGRATION: Mise à jour groupe Premium Manager avec implied_ids")
    _logger.info("=" * 80)

    try:
        # Trouver le groupe Premium Manager
        premium_group = env.ref('onedesk_core.group_onedesk_premium_manager', raise_if_not_found=False)

        if not premium_group:
            _logger.info("✅ Groupe Premium Manager n'existe pas encore, sera créé par le XML")
            return

        _logger.info(f"📝 Mise à jour du groupe: {premium_group.name} (ID: {premium_group.id})")

        # Groupes requis
        required_groups_refs = [
            'onedesk_core.group_onedesk_property_manager',
            'base.group_erp_manager',
            'sales_team.group_sale_manager',
            'website.group_website_designer',
            'account.group_account_manager',
            'base.group_partner_manager',
        ]

        implied_group_ids = []
        for ref_id in required_groups_refs:
            try:
                group = env.ref(ref_id)
                implied_group_ids.append(group.id)
                _logger.info(f"  ✓ Ajout implied_id: {group.name}")
            except Exception as e:
                _logger.warning(f"  ⚠️ Groupe {ref_id} introuvable: {e}")

        # Mettre à jour les implied_ids (remplacer complètement)
        if implied_group_ids:
            premium_group.write({
                'implied_ids': [(6, 0, implied_group_ids)]
            })
            _logger.info(f"✅ Groupe mis à jour avec {len(implied_group_ids)} implied_ids")

    except Exception as e:
        _logger.error(f"❌ Erreur lors de la migration: {e}", exc_info=True)

    _logger.info("=" * 80)
