import logging
from . import models
from . import controllers

_logger = logging.getLogger(__name__)


def post_init_hook(env):
    """Valide la configuration du module au démarrage"""
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

