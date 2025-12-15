# -*- coding: utf-8 -*-
"""
Migration 19.0.1.0.2: Corriger incohérences company_id entre users et partners

Cette migration corrige AUTOMATIQUEMENT toutes les incohérences existantes
dans la base de données sans intervention manuelle.
"""

import logging

_logger = logging.getLogger(__name__)

def migrate(cr, version):
    """Corriger les company_id des partners pour tous les utilisateurs"""
    from odoo import api, SUPERUSER_ID

    env = api.Environment(cr, SUPERUSER_ID, {})

    _logger.info("=" * 80)
    _logger.info("MIGRATION 19.0.1.0.2: Correction company_id users/partners")
    _logger.info("=" * 80)

    # 1. CORRIGER LES PARTNERS DES UTILISATEURS
    _logger.info("\n1️⃣ Correction des partners des utilisateurs...")

    # Trouver tous les users avec incohérence partner.company_id != user.company_id
    all_users = env['res.users'].search([
        ('partner_id', '!=', False),
        ('company_id', '!=', False),
    ])

    corrected_count = 0
    for user in all_users:
        if user.partner_id.company_id != user.company_id:
            old_company = user.partner_id.company_id.name if user.partner_id.company_id else 'None'
            _logger.info(f"   🔧 User: {user.name} (ID: {user.id})")
            _logger.info(f"      Partner: {user.partner_id.name} (ID: {user.partner_id.id})")
            _logger.info(f"      Old company: {old_company}")
            _logger.info(f"      New company: {user.company_id.name}")

            user.partner_id.write({
                'company_id': user.company_id.id
            })
            corrected_count += 1

    _logger.info(f"   ✅ Corrigé {corrected_count} partners sur {len(all_users)} utilisateurs")

    # 2. METTRE LES PARTNERS SYSTÈME EN GLOBAL (company_id = False)
    _logger.info("\n2️⃣ Correction des partners système (global)...")

    # Liste des partners qui doivent être globaux
    system_partner_names = [
        'Administrator',
        'OdooBot',
        'Public user',
        'Portal',
    ]

    system_count = 0
    for partner_name in system_partner_names:
        partner = env['res.partner'].search([('name', '=', partner_name)], limit=1)
        if partner and partner.company_id:
            _logger.info(f"   🔧 {partner.name} (ID: {partner.id})")
            _logger.info(f"      Old company: {partner.company_id.name}")
            _logger.info(f"      New company: False (global)")

            partner.write({'company_id': False})
            system_count += 1

    _logger.info(f"   ✅ {system_count} partners système mis en global")

    # 3. VÉRIFIER LES COMPANY_IDS DES PREMIUM MANAGERS
    _logger.info("\n3️⃣ Vérification company_ids des Premium Managers...")

    try:
        premium_group = env.ref('onedesk_core.group_onedesk_premium_manager')
        premium_users = env['res.users'].search([
            ('groups_id', 'in', [premium_group.id])
        ])

        restricted_count = 0
        for user in premium_users:
            if user.company_id and set(user.company_ids.ids) != {user.company_id.id}:
                _logger.info(f"   🔧 {user.name} (ID: {user.id})")
                _logger.info(f"      Old companies: {user.company_ids.mapped('name')}")
                _logger.info(f"      New companies: [{user.company_id.name}]")

                user.write({
                    'company_ids': [(6, 0, [user.company_id.id])]
                })
                restricted_count += 1

        _logger.info(f"   ✅ {restricted_count} Premium Managers restreints à UNE company")

    except Exception as e:
        _logger.warning(f"   ⚠️ Groupe Premium Manager non trouvé: {e}")

    # 4. STATISTIQUES FINALES
    _logger.info("\n" + "=" * 80)
    _logger.info("📊 STATISTIQUES:")
    _logger.info(f"   - Partners utilisateurs corrigés: {corrected_count}")
    _logger.info(f"   - Partners système globalisés: {system_count}")
    _logger.info(f"   - Premium Managers restreints: {restricted_count if 'restricted_count' in locals() else 0}")
    _logger.info("=" * 80)
    _logger.info("✅ MIGRATION TERMINÉE - Toutes les incohérences corrigées automatiquement")
    _logger.info("=" * 80)
