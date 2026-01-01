# -*- coding: utf-8 -*-
from odoo import models
from odoo.http import request
from odoo.exceptions import AccessDenied
import logging

_logger = logging.getLogger(__name__)

class IrHttp(models.AbstractModel):
    _inherit = 'ir.http'

    @classmethod
    def _get_master_database(cls):
        """
        Détecte automatiquement la base de données maître (SaaS Manager)
        en cherchant quelle base contient la table saas_client

        Priorité:
        1. Cache (pour performance)
        2. Base actuelle (si elle contient saas_client)
        3. Scan de toutes les bases PostgreSQL
        """
        import psycopg2
        from odoo.tools import config
        import os

        # Cache pour éviter de recalculer à chaque requête
        if not hasattr(cls, '_master_db_cache'):
            cls._master_db_cache = None

        # Retourner le cache si disponible
        if cls._master_db_cache:
            return cls._master_db_cache

        try:
            # Récupérer credentials de manière sécurisée
            db_host = os.environ.get('SAAS_DB_HOST') or config.get('db_host') or 'localhost'
            db_port = os.environ.get('SAAS_DB_PORT') or config.get('db_port') or '5432'
            db_user = os.environ.get('SAAS_DB_USER') or config.get('db_user') or 'odoo'
            db_password = os.environ.get('SAAS_DB_PASSWORD') or config.get('db_password') or ''

            # 1. Essayer d'abord la base actuelle
            if hasattr(request, 'db') and request.db:
                try:
                    conn = psycopg2.connect(
                        host=db_host,
                        port=int(db_port),
                        user=db_user,
                        password=db_password,
                        database=request.db,
                        connect_timeout=2,
                    )
                    cursor = conn.cursor()
                    try:
                        # Vérifier si la table saas_client existe
                        cursor.execute("""
                            SELECT EXISTS (
                                SELECT FROM information_schema.tables
                                WHERE table_name = 'saas_client'
                            )
                        """)
                        if cursor.fetchone()[0]:
                            cls._master_db_cache = request.db
                            _logger.info(f"[SAAS] Base maître détectée automatiquement: {request.db}")
                            return request.db
                    finally:
                        cursor.close()
                        conn.close()
                except:
                    pass

            # 2. Sinon, lister toutes les bases et chercher celle avec saas_client
            try:
                conn = psycopg2.connect(
                    host=db_host,
                    port=int(db_port),
                    user=db_user,
                    password=db_password,
                    database='postgres',
                    connect_timeout=2,
                )
                cursor = conn.cursor()
                try:
                    # Lister toutes les bases (sauf templates et postgres)
                    cursor.execute("""
                        SELECT datname FROM pg_database
                        WHERE datistemplate = false
                        AND datname != 'postgres'
                        ORDER BY datname
                    """)
                    databases = [row[0] for row in cursor.fetchall()]
                finally:
                    cursor.close()
                    conn.close()

                # Tester chaque base pour trouver celle avec saas_client
                for db_name in databases:
                    try:
                        conn = psycopg2.connect(
                            host=db_host,
                            port=int(db_port),
                            user=db_user,
                            password=db_password,
                            database=db_name,
                            connect_timeout=2,
                        )
                        cursor = conn.cursor()
                        try:
                            cursor.execute("""
                                SELECT EXISTS (
                                    SELECT FROM information_schema.tables
                                    WHERE table_name = 'saas_client'
                                )
                            """)
                            if cursor.fetchone()[0]:
                                cls._master_db_cache = db_name
                                _logger.info(f"[SAAS] Base maître détectée automatiquement: {db_name}")
                                return db_name
                        finally:
                            cursor.close()
                            conn.close()
                    except:
                        continue

            except:
                pass

        except Exception as e:
            _logger.debug(f"[SAAS] Erreur détection base maître: {str(e)}")

        # Si aucune base trouvée, désactiver la vérification
        return None

    @classmethod
    def _check_database_access(cls, db_name):
        """
        Vérifie si l'accès à une base de données client est autorisé
        Bloque l'accès si la base est suspendue ou terminée
        """
        if not db_name:
            return True

        # Obtenir le nom de la base maître
        master_db = cls._get_master_database()

        # Si pas de base maître configurée, désactiver la vérification
        if not master_db:
            return True

        # Liste des bases maîtres (toujours autorisées)
        master_databases = [master_db, 'postgres', 'template0', 'template1']
        if db_name in master_databases:
            return True

        try:
            import psycopg2
            from odoo.tools import config
            import os

            # Récupérer credentials de manière sécurisée
            db_host = os.environ.get('SAAS_DB_HOST') or config.get('db_host') or 'localhost'
            db_port = os.environ.get('SAAS_DB_PORT') or config.get('db_port') or '5432'
            db_user = os.environ.get('SAAS_DB_USER') or config.get('db_user') or 'odoo'
            db_password = os.environ.get('SAAS_DB_PASSWORD') or config.get('db_password') or ''

            # Connexion à la base maître pour vérifier l'état
            conn = psycopg2.connect(
                host=db_host,
                port=int(db_port),
                user=db_user,
                password=db_password,
                database=master_db,
                connect_timeout=5,
            )

            cursor = conn.cursor()

            try:
                # Vérifier l'état de la base client
                cursor.execute("""
                    SELECT database_state, subscription_state
                    FROM saas_client
                    WHERE database_name = %s
                    LIMIT 1
                """, (db_name,))

                result = cursor.fetchone()

                if result:
                    database_state, subscription_state = result

                    # Bloquer si suspendu ou terminé
                    if database_state in ['suspended', 'terminated']:
                        _logger.warning(f"[SAAS] Accès refusé à {db_name} - État: {database_state}")
                        return False

                    # Bloquer si abonnement annulé ou expiré
                    if subscription_state in ['cancelled', 'expired']:
                        _logger.warning(f"[SAAS] Accès refusé à {db_name} - Abonnement: {subscription_state}")
                        return False

            finally:
                cursor.close()
                conn.close()

        except Exception as e:
            _logger.error(f"[SAAS] Erreur vérification accès base {db_name}: {str(e)}")
            # En cas d'erreur, on autorise (fail-open) pour ne pas bloquer le système
            return True

        return True

    @classmethod
    def _dispatch(cls, endpoint):
        """
        Override pour vérifier l'état de la base avant chaque requête
        """
        # Vérifier l'accès à la base de données
        db_name = request.db if hasattr(request, 'db') else None

        if db_name and not cls._check_database_access(db_name):
            # Base suspendue ou terminée - Logger l'accès refusé
            try:
                # Obtenir la base maître pour l'audit
                master_db = cls._get_master_database()
                if master_db:
                    import psycopg2
                    from odoo.tools import config
                    import os

                    db_host = os.environ.get('SAAS_DB_HOST') or config.get('db_host') or 'localhost'
                    db_port = os.environ.get('SAAS_DB_PORT') or config.get('db_port') or '5432'
                    db_user = os.environ.get('SAAS_DB_USER') or config.get('db_user') or 'odoo'
                    db_password = os.environ.get('SAAS_DB_PASSWORD') or config.get('db_password') or ''

                    conn = psycopg2.connect(
                        host=db_host, port=int(db_port),
                        user=db_user, password=db_password,
                        database=master_db, connect_timeout=2
                    )
                    cursor = conn.cursor()

                    # Trouver le client_id
                    cursor.execute("SELECT id FROM saas_client WHERE database_name = %s LIMIT 1", (db_name,))
                    result = cursor.fetchone()
                    client_id = result[0] if result else None

                    # Récupérer l'IP
                    ip_address = request.httprequest.environ.get('HTTP_X_FORWARDED_FOR')
                    if ip_address:
                        ip_address = ip_address.split(',')[0].strip()
                    else:
                        ip_address = request.httprequest.environ.get('REMOTE_ADDR')

                    # Logger l'accès refusé
                    if client_id:
                        cursor.execute("""
                            INSERT INTO saas_audit_log (
                                action, timestamp, client_id, database_name,
                                ip_address, status, create_date, write_date
                            ) VALUES (%s, NOW(), %s, %s, %s, %s, NOW(), NOW())
                        """, ('access_denied', client_id, db_name, ip_address, 'warning'))

                    conn.commit()
                    cursor.close()
                    conn.close()

            except Exception as e:
                _logger.debug(f"[SAAS AUDIT] Erreur log accès refusé: {str(e)}")

            return request.render('onedesk_core.database_suspended_template', {
                'database_name': db_name,
            }, status=403)

        return super()._dispatch(endpoint)

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
                master_db = httprequest.session.get('force_db') or cls._get_master_database()
                if master_db:
                    _logger.debug(f"[SAAS] Subdomain '{subdomain}' → Base maître: {master_db}")
                    return master_db

            # Obtenir la base maître pour la recherche
            master_db = cls._get_master_database()
            if not master_db:
                # Si pas de base maître configurée, utiliser le fallback Odoo
                return super()._get_db_from_request(httprequest)

            # Sinon, chercher le mapping subdomain → database_name
            try:
                # Méthode 1: Chercher dans un cache Redis (optimal pour la production)
                # Pour cet exemple, on utilise PostgreSQL direct

                import psycopg2
                from odoo.tools import config
                import os

                # Récupérer credentials de manière sécurisée
                db_host = os.environ.get('SAAS_DB_HOST') or config.get('db_host') or 'localhost'
                db_port = os.environ.get('SAAS_DB_PORT') or config.get('db_port') or '5432'
                db_user = os.environ.get('SAAS_DB_USER') or config.get('db_user') or 'odoo'
                db_password = os.environ.get('SAAS_DB_PASSWORD') or config.get('db_password') or ''

                # Connexion à la base maître pour récupérer le mapping
                conn = psycopg2.connect(
                    host=db_host,
                    port=int(db_port),
                    user=db_user,
                    password=db_password,
                    database=master_db,  # Base maître détectée dynamiquement
                    connect_timeout=5,
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

        # SÉCURITÉ: En mode SaaS, TOUJOURS retourner la base maître au lieu du sélecteur
        # Cela empêche l'affichage du database selector aux clients publics
        master_db = httprequest.session.get('force_db') or cls._get_master_database()
        if master_db:
            _logger.debug(f"[SAAS SECURITY] Fallback vers base maître: {master_db} (empêche database selector)")
            return master_db

        # Si vraiment aucune base trouvée, fallback Odoo (ne devrait jamais arriver)
        return super()._get_db_from_request(httprequest)

