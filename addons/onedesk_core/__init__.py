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