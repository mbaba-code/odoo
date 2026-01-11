# -*- coding: utf-8 -*-
from odoo import models, http
from odoo.http import request
from odoo.tools import config
import logging
import psycopg2
import os

_logger = logging.getLogger(__name__)

class IrHttp(models.AbstractModel):
    _inherit = 'ir.http'

    @classmethod
    def _get_master_database(cls):
        """Détecte automatiquement la base maître (odoo_prod) ou autre base contenant saas_client"""
        if hasattr(cls, '_master_db_cache') and cls._master_db_cache:
            return cls._master_db_cache

        # Essayer db_name de config d'abord
        master_db = config.get('db_name')
        if master_db:
            cls._master_db_cache = master_db
            return master_db

        # Essayer variable d'environnement
        master_db = os.environ.get('ODOO_DEFAULT_DB')
        if master_db:
            cls._master_db_cache = master_db
            return master_db

        # Sinon, scan des bases pour trouver celle avec saas_client
        db_host = os.environ.get('SAAS_DB_HOST') or config.get('db_host') or 'localhost'
        db_port = int(os.environ.get('SAAS_DB_PORT') or config.get('db_port') or 5432)
        db_user = os.environ.get('SAAS_DB_USER') or config.get('db_user') or 'odoo'
        db_password = os.environ.get('SAAS_DB_PASSWORD') or config.get('db_password') or ''

        try:
            conn = psycopg2.connect(
                host=db_host, port=db_port, user=db_user,
                password=db_password, database='postgres', connect_timeout=2
            )
            cursor = conn.cursor()
            cursor.execute("""
                SELECT datname FROM pg_database
                WHERE datistemplate = false AND datname != 'postgres'
                ORDER BY datname
            """)
            databases = [row[0] for row in cursor.fetchall()]
            cursor.close()
            conn.close()

            for db in databases:
                try:
                    conn = psycopg2.connect(
                        host=db_host, port=db_port, user=db_user,
                        password=db_password, database=db, connect_timeout=2
                    )
                    cur = conn.cursor()
                    cur.execute("""
                        SELECT EXISTS (
                            SELECT FROM information_schema.tables
                            WHERE table_name = 'saas_client'
                        )
                    """)
                    if cur.fetchone()[0]:
                        cls._master_db_cache = db
                        cur.close()
                        conn.close()
                        _logger.info(f"[SAAS] Base maître détectée automatiquement: {db}")
                        return db
                    cur.close()
                    conn.close()
                except Exception:
                    continue
        except Exception as e:
            _logger.warning(f"[SAAS] Impossible de détecter base maître: {str(e)}")

        return None

    @classmethod
    def _check_database_access(cls, db_name):
        """Vérifie si l'accès à la base client est autorisé"""
        if not db_name:
            return True
        master_db = cls._get_master_database()
        if not master_db:
            return True

        if db_name in [master_db, 'postgres', 'template0', 'template1']:
            return True

        db_host = os.environ.get('SAAS_DB_HOST') or config.get('db_host') or 'localhost'
        db_port = int(os.environ.get('SAAS_DB_PORT') or config.get('db_port') or 5432)
        db_user = os.environ.get('SAAS_DB_USER') or config.get('db_user') or 'odoo'
        db_password = os.environ.get('SAAS_DB_PASSWORD') or config.get('db_password') or ''

        try:
            conn = psycopg2.connect(
                host=db_host, port=db_port, user=db_user,
                password=db_password, database=master_db, connect_timeout=5
            )
            cursor = conn.cursor()
            cursor.execute("""
                SELECT database_state, subscription_state
                FROM saas_client
                WHERE database_name = %s
                LIMIT 1
            """, (db_name,))
            result = cursor.fetchone()
            cursor.close()
            conn.close()
            if result:
                database_state, subscription_state = result
                if database_state in ['suspended', 'terminated'] or subscription_state in ['cancelled', 'expired']:
                    _logger.warning(f"[SAAS] Accès refusé à {db_name}")
                    return False
        except Exception as e:
            _logger.error(f"[SAAS] Erreur vérification accès base {db_name}: {str(e)}")
            return True  # fail-open

        return True

    @classmethod
    def _get_db_from_request(cls, httprequest):
        """
        Mappe sous-domaine → DB et force la session pour éviter le database selector
        """
        # 1️⃣ Si db_name est défini dans la config, utiliser directement
        db_name = config.get('db_name')
        if db_name:
            if hasattr(httprequest, 'session'):
                httprequest.session.db = db_name
            _logger.debug(f"[SAAS] DB forcée depuis config: {db_name}")
            return db_name

        # 2️⃣ Extraire sous-domaine
        host = httprequest.environ.get('HTTP_HOST', '').split(':')[0]
        parts = host.split('.')
        subdomain = parts[0] if parts else ''

        master_db = cls._get_master_database()

        # 3️⃣ Vérifier si c’est un client SaaS actif
        if subdomain.startswith('onedesk_client_'):
            try:
                db_host = os.environ.get('SAAS_DB_HOST') or config.get('db_host') or 'localhost'
                db_port = int(os.environ.get('SAAS_DB_PORT') or config.get('db_port') or 5432)
                db_user = os.environ.get('SAAS_DB_USER') or config.get('db_user') or 'odoo'
                db_password = os.environ.get('SAAS_DB_PASSWORD') or config.get('db_password') or ''

                conn = psycopg2.connect(
                    host=db_host, port=db_port, user=db_user,
                    password=db_password, database=master_db, connect_timeout=5
                )
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT database_name
                    FROM saas_client
                    WHERE subdomain = %s
                      AND database_state = 'active'
                    LIMIT 1
                """, (subdomain,))
                result = cursor.fetchone()
                cursor.close()
                conn.close()
                if result:
                    db_name = result[0]
                    if hasattr(httprequest, 'session'):
                        httprequest.session.db = db_name
                    _logger.debug(f"[SAAS] Subdomain '{subdomain}' → DB client: {db_name}")
                    return db_name
            except Exception as e:
                _logger.error(f"[SAAS] Erreur mapping subdomain '{subdomain}': {str(e)}")

        # 4️⃣ Fallback → base maître
        if master_db:
            if hasattr(httprequest, 'session'):
                httprequest.session.db = master_db
            _logger.debug(f"[SAAS] Fallback vers base maître: {master_db}")
            return master_db

        # 5️⃣ Dernier fallback → méthode parent
        return super()._get_db_from_request(httprequest)

    @classmethod
    def _dispatch(cls, endpoint):
        # Forcer la base dans la session pour éviter database selector
        if not hasattr(request, 'session') or not request.session.db:
            master_db = cls._get_master_database() or config.get('db_name')
            if master_db and hasattr(request, 'session'):
                request.session.db = master_db
                _logger.debug(f"[SAAS] Base forcée dans session au dispatch: {master_db}")

        # Vérifier l’accès à la base
        db_name = getattr(request, 'db', None)
        if db_name and not cls._check_database_access(db_name):
            return request.render('onedesk_core.database_suspended_template', {
                'database_name': db_name
            }, status=403)

        return super()._dispatch(endpoint)

    @classmethod
    def _authenticate(cls, endpoint):
        result = super()._authenticate(endpoint)
        # Forcer base maître si session vide
        if hasattr(request, 'session') and not request.session.db:
            master_db = cls._get_master_database() or config.get('db_name')
            if master_db:
                request.session.db = master_db
                _logger.debug(f"[SAAS] Base forcée dans _authenticate: {master_db}")
        return result
