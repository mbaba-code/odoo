import logging
from . import models
from . import controllers

_logger = logging.getLogger(__name__)


def post_init_hook(env):
    """Valide la configuration du module et migre les données au démarrage"""
    from odoo.tools import config

    encryption_key = config.get('onedesk_encryption_key')

    if not encryption_key:
        _logger.warning(
            "⚠️ AVERTISSEMENT SÉCURITÉ: "
            "Pas de clé de chiffrement configurée pour OneDesk!\n"
            "Les tokens OAuth seront stockés en clair.\n"
            "Pour sécuriser, ajoutez cette ligne à odoo.conf:\n"
            "onedesk_encryption_key = <clé Fernet générée avec: python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'>"
        )

    # Migration: Assigner les anciens partenaires sans company_id à la compagnie par défaut
    _migrate_partners_without_company(env)

    # Auto-configuration: Configurer automatiquement tous les Premium Managers existants
    _auto_configure_existing_premium_managers(env)


def _migrate_partners_without_company(env):
    """Assigne les anciens partenaires sans company_id à une compagnie par défaut"""
    try:
        Partner = env['res.partner'].sudo()
        Company = env['res.company'].sudo()

        # Trouver les partenaires sans company_id (avec sudo() pour contourner les ir.rules)
        partners_without_company = Partner.search([('company_id', '=', False)])

        if not partners_without_company:
            _logger.info("✅ Aucun partenaire sans company_id à migrer")
            return

        # Récupérer la compagnie par défaut (première compagnie ou créer une)
        default_company = Company.search([], limit=1)
        if not default_company:
            _logger.warning("⚠️ Aucune compagnie trouvée, création d'une compagnie par défaut")
            default_company = Company.create({
                'name': 'Compagnie par défaut',
                'is_onedesk_client': False,
            })

        # Assigner tous les anciens partenaires à la compagnie par défaut
        partners_without_company.write({'company_id': default_company.id})

        _logger.info(
            f"✅ Migration complète: {len(partners_without_company)} partenaires assignés à {default_company.name}"
        )
    except Exception as e:
        _logger.error(f"❌ Erreur lors de la migration des partenaires: {e}")


def _auto_configure_existing_premium_managers(env):
    """Configure automatiquement tous les utilisateurs Premium Manager existants"""
    try:
        # Trouver le groupe Premium Manager
        try:
            premium_group = env.ref('onedesk_core.group_onedesk_premium_manager')
        except:
            _logger.info("ℹ️ Groupe Premium Manager non trouvé, skip auto-configuration")
            return

        # Trouver tous les utilisateurs qui ont ce groupe
        # Note: Pour les Many2many, utiliser '=' au lieu de 'in'
        premium_users = env['res.users'].sudo().search([
            ('groups_id', '=', premium_group.id)
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
            groups_added = []

            # 1. Ajouter les groupes manquants
            for xml_id in required_groups_xml_ids:
                try:
                    group = env.ref(xml_id)
                    if group not in user.groups_id:
                        user.sudo().write({'groups_id': [(4, group.id)]})
                        groups_added.append(group.name)
                except Exception as e:
                    _logger.warning(f"⚠️ Impossible d'ajouter le groupe {xml_id}: {e}")

            # 2. Assurer que l'utilisateur a une company
            if not user.company_id:
                default_company = env['res.company'].sudo().search([], limit=1)
                if default_company:
                    user.sudo().write({
                        'company_id': default_company.id,
                        'company_ids': [(6, 0, [default_company.id])]  # ONLY this company!
                    })
                    _logger.info(f"  ✓ Company assignée: {default_company.name}")
            else:
                # Ensure company_ids contains ONLY the user's company (not admin's companies)
                if set(user.company_ids.ids) != {user.company_id.id}:
                    user.sudo().write({
                        'company_ids': [(6, 0, [user.company_id.id])]  # Replace with ONLY user's company
                    })
                    _logger.info(f"  ✓ Accès restreint à la company: {user.company_id.name}")

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
                    _logger.info(f"  ✓ Website créé: {new_website.name}")

            if groups_added:
                _logger.info(f"  ✓ {user.name}: {len(groups_added)} groupe(s) ajouté(s)")
                configured_count += 1

        _logger.info(f"✅ Auto-configuration terminée: {configured_count}/{len(premium_users)} utilisateur(s) configuré(s)")

    except Exception as e:
        _logger.error(f"❌ Erreur lors de l'auto-configuration des Premium Managers: {e}")