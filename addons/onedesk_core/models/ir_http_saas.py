# -*- coding: utf-8 -*-
from odoo import models
from odoo.http import request
import logging

_logger = logging.getLogger(__name__)

class IrHttp(models.AbstractModel):
    _inherit = 'ir.http'

    @classmethod
    def _get_db_from_request(cls, httprequest):
        """
        Override pour mapper sous-domaine → nom de base de données

        Exemples:
        - clienta.onedesk.com → onedesk_client_1_clienta
        - clientb.onedesk.com → onedesk_client_2_clientb
        - app.onedesk.com → onedesk_core (base maître)
        """

        # Récupérer le Host header
        host = httprequest.environ.get('HTTP_HOST', '').split(':')[0]

        # Extraire le sous-domaine
        parts = host.split('.')

        if len(parts) >= 2:
            subdomain = parts[0]

            # Si c'est "app" ou "www" ou vide, c'est la base maître
            if subdomain in ['app', 'www', 'admin', '']:
                master_db = httprequest.session.get('force_db') or 'onedesk_core'
                _logger.debug(f"[SAAS] Subdomain '{subdomain}' → Base maître: {master_db}")
                return master_db

            # Sinon, chercher le mapping subdomain → database_name
            try:
                # Méthode 1: Chercher dans un cache Redis (optimal pour la production)
                # Pour cet exemple, on utilise PostgreSQL direct

                import psycopg2
                from odoo.tools import config

                # Connexion à la base maître pour récupérer le mapping
                conn = psycopg2.connect(
                    host=config.get('db_host', 'localhost'),
                    port=int(config.get('db_port', '5432')),
                    user=config.get('db_user', 'odoo'),
                    password=config.get('db_password', ''),
                    database='onedesk_core',  # Base maître
                )

                cursor = conn.cursor()

                try:
                    # Chercher le client avec ce subdomain
                    cursor.execute("""
                        SELECT database_name
                        FROM saas_client
                        WHERE subdomain = %s
                          AND database_state = 'active'
                        LIMIT 1
                    """, (subdomain,))

                    result = cursor.fetchone()

                    if result:
                        database_name = result[0]
                        _logger.debug(f"[SAAS] Subdomain '{subdomain}' → Database: {database_name}")
                        return database_name
                    else:
                        _logger.warning(f"[SAAS] Subdomain '{subdomain}' non trouvé dans saas_client")

                finally:
                    cursor.close()
                    conn.close()

            except Exception as e:
                _logger.error(f"[SAAS] Erreur lors du mapping subdomain '{subdomain}': {str(e)}")

        # Fallback sur le comportement par défaut d'Odoo
        return super()._get_db_from_request(httprequest)
