#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de Migration: Multi-Company → Multi-Database

Ce script extrait une company d'une base Odoo multi-company existante
et crée une base de données dédiée pour cette company.

Usage:
    python3 extract_company_to_database.py \\
        --source-db onedesk_production \\
        --company-id 2 \\
        --target-db onedesk_client_2

Auteur: OneDesk DevOps Team
Date: 2025-12-18
"""

import argparse
import sys
import subprocess
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import logging

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def extract_company_to_database(source_db, company_id, target_db, db_config=None):
    """
    Extrait une company de source_db et crée une nouvelle base target_db

    Args:
        source_db (str): Nom de la base source (ex: onedesk_production)
        company_id (int): ID de la company à extraire
        target_db (str): Nom de la nouvelle base (ex: onedesk_client_1)
        db_config (dict): Configuration PostgreSQL (host, port, user, password)
    """

    if db_config is None:
        db_config = {
            'host': 'localhost',
            'port': 5432,
            'user': 'odoo',
            'password': '',
        }

    logger.info(f"🔄 Migration de Company {company_id} de {source_db} vers {target_db}")
    logger.info("=" * 80)

    try:
        # Étape 1: Créer la base cible
        logger.info("📦 Étape 1/7: Création de la base cible...")
        create_target_database(target_db, db_config)

        # Étape 2: Copier le schéma complet
        logger.info("📐 Étape 2/7: Copie du schéma (structure des tables)...")
        copy_database_schema(source_db, target_db, db_config)

        # Étape 3: Copier les données système
        logger.info("👥 Étape 3/7: Copie des données système...")
        copy_system_data(source_db, target_db, company_id, db_config)

        # Étape 4: Copier les données de la company
        logger.info("📊 Étape 4/7: Copie des données de la company...")
        copy_company_data(source_db, target_db, company_id, db_config)

        # Étape 5: Nettoyer et transformer
        logger.info("🧹 Étape 5/7: Nettoyage et transformation...")
        cleanup_and_transform(target_db, company_id, db_config)

        # Étape 6: Réinitialiser les séquences
        logger.info("🔢 Étape 6/7: Réinitialisation des séquences...")
        reset_sequences(target_db, db_config)

        # Étape 7: Vérifications finales
        logger.info("✅ Étape 7/7: Vérifications finales...")
        verify_migration(target_db, db_config)

        logger.info("=" * 80)
        logger.info(f"✅ Migration terminée avec succès!")
        logger.info(f"   Base créée: {target_db}")
        logger.info(f"   Company migrée: ID {company_id}")
        logger.info(f"   Prête à l'emploi!")

    except Exception as e:
        logger.error(f"❌ Erreur lors de la migration: {str(e)}", exc_info=True)
        sys.exit(1)


def create_target_database(target_db, db_config):
    """Crée la base PostgreSQL cible"""
    conn = psycopg2.connect(
        host=db_config['host'],
        port=db_config['port'],
        user=db_config['user'],
        password=db_config['password'],
        database='postgres',
    )
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cursor = conn.cursor()

    try:
        # Vérifier si existe déjà
        cursor.execute("SELECT 1 FROM pg_database WHERE datname = %s", (target_db,))
        if cursor.fetchone():
            raise Exception(f"La base {target_db} existe déjà!")

        # Créer la base
        cursor.execute(f'CREATE DATABASE "{target_db}" ENCODING \'UTF8\' TEMPLATE template0')
        logger.info(f"   ✓ Base {target_db} créée")

    finally:
        cursor.close()
        conn.close()


def copy_database_schema(source_db, target_db, db_config):
    """Copie le schéma complet (structure) de source vers target"""

    # Dump du schéma uniquement (--schema-only)
    dump_cmd = [
        'pg_dump',
        '-h', db_config['host'],
        '-p', str(db_config['port']),
        '-U', db_config['user'],
        '-d', source_db,
        '--schema-only',
        '--no-owner',
        '--no-privileges',
        '-f', '/tmp/schema.sql'
    ]

    result = subprocess.run(dump_cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise Exception(f"Erreur pg_dump: {result.stderr}")

    # Restaurer le schéma
    restore_cmd = [
        'psql',
        '-h', db_config['host'],
        '-p', str(db_config['port']),
        '-U', db_config['user'],
        '-d', target_db,
        '-f', '/tmp/schema.sql'
    ]

    result = subprocess.run(restore_cmd, capture_output=True, text=True)
    if result.returncode != 0:
        logger.warning(f"Avertissement lors de la restauration: {result.stderr}")

    logger.info("   ✓ Schéma copié")


def copy_system_data(source_db, target_db, company_id, db_config):
    """Copie les données système (indépendantes de la company)"""

    # Tables système à copier intégralement
    system_tables = [
        'ir_module_module',
        'ir_module_module_dependency',
        'ir_model',
        'ir_model_fields',
        'ir_model_constraint',
        'ir_model_relation',
        'ir_model_access',
        'ir_rule',
        'ir_ui_view',
        'ir_ui_menu',
        'ir_act_window',
        'ir_act_server',
        'ir_cron',
        'res_groups',
        'res_groups_users_rel',
        'res_country',
        'res_country_state',
        'res_currency',
        'res_currency_rate',
        'res_lang',
    ]

    source_conn = psycopg2.connect(
        host=db_config['host'],
        port=db_config['port'],
        user=db_config['user'],
        password=db_config['password'],
        database=source_db,
    )

    target_conn = psycopg2.connect(
        host=db_config['host'],
        port=db_config['port'],
        user=db_config['user'],
        password=db_config['password'],
        database=target_db,
    )

    source_cursor = source_conn.cursor()
    target_cursor = target_conn.cursor()

    try:
        for table in system_tables:
            try:
                # Vérifier si la table existe
                source_cursor.execute(f"""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables
                        WHERE table_name = '{table}'
                    )
                """)

                if not source_cursor.fetchone()[0]:
                    continue

                # Copier les données
                source_cursor.execute(f"SELECT * FROM {table}")
                rows = source_cursor.fetchall()

                if rows:
                    # Obtenir les colonnes
                    colnames = [desc[0] for desc in source_cursor.description]
                    cols = ', '.join(colnames)
                    placeholders = ', '.join(['%s'] * len(colnames))

                    # Vider la table cible d'abord
                    target_cursor.execute(f"TRUNCATE TABLE {table} CASCADE")

                    # Insérer dans la cible
                    insert_query = f"INSERT INTO {table} ({cols}) VALUES ({placeholders})"
                    target_cursor.executemany(insert_query, rows)

                    logger.info(f"   ✓ {table}: {len(rows)} lignes copiées")

            except Exception as e:
                logger.warning(f"   ⚠ {table}: {str(e)}")

        target_conn.commit()

    finally:
        source_cursor.close()
        target_cursor.close()
        source_conn.close()
        target_conn.close()


def copy_company_data(source_db, target_db, company_id, db_config):
    """Copie les données de la company spécifique"""

    # Tables avec company_id à filtrer
    company_tables = [
        ('res_company', 'id'),  # (table, champ de filtrage)
        ('res_users', 'company_id'),
        ('res_partner', 'company_id'),
        ('account_move', 'company_id'),
        ('account_payment', 'company_id'),
        ('account_journal', 'company_id'),
        ('account_account', 'company_id'),
        ('sale_order', 'company_id'),
        ('sale_order_line', 'company_id'),
        ('purchase_order', 'company_id'),
        ('crm_lead', 'company_id'),
        ('product_template', 'company_id'),
        ('product_product', 'company_id'),
        ('website_website', 'company_id'),
        ('website_page', 'company_id'),
        ('website_menu', 'company_id'),
        ('mail_message', None),  # Pas de company_id, on copie tout
        ('mail_followers', None),
        ('ir_attachment', 'company_id'),
    ]

    # Tables OneDesk spécifiques
    onedesk_tables = [
        ('onedesk_property', 'company_id'),
        ('onedesk_unit', 'company_id'),
        ('onedesk_reservation', 'company_id'),
        ('onedesk_seasonal_price', 'company_id'),
        ('onedesk_task', 'company_id'),
        ('onedesk_document', 'company_id'),
    ]

    all_tables = company_tables + onedesk_tables

    source_conn = psycopg2.connect(
        host=db_config['host'],
        port=db_config['port'],
        user=db_config['user'],
        password=db_config['password'],
        database=source_db,
    )

    target_conn = psycopg2.connect(
        host=db_config['host'],
        port=db_config['port'],
        user=db_config['user'],
        password=db_config['password'],
        database=target_db,
    )

    source_cursor = source_conn.cursor()
    target_cursor = target_conn.cursor()

    try:
        for table, company_field in all_tables:
            try:
                # Vérifier si la table existe
                source_cursor.execute(f"""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables
                        WHERE table_name = '{table}'
                    )
                """)

                if not source_cursor.fetchone()[0]:
                    continue

                # Construire la requête de sélection
                if company_field == 'id':
                    # Cas spécial pour res_company
                    where_clause = f"WHERE id = {company_id}"
                elif company_field:
                    where_clause = f"WHERE {company_field} = {company_id} OR {company_field} IS NULL"
                else:
                    # Pas de filtrage
                    where_clause = ""

                # Copier les données de cette company
                source_cursor.execute(f"SELECT * FROM {table} {where_clause}")
                rows = source_cursor.fetchall()

                if rows:
                    colnames = [desc[0] for desc in source_cursor.description]
                    cols = ', '.join(colnames)
                    placeholders = ', '.join(['%s'] * len(colnames))

                    # Vider la table cible d'abord
                    target_cursor.execute(f"TRUNCATE TABLE {table} CASCADE")

                    # Insérer
                    insert_query = f"INSERT INTO {table} ({cols}) VALUES ({placeholders}) ON CONFLICT DO NOTHING"
                    target_cursor.executemany(insert_query, rows)

                    logger.info(f"   ✓ {table}: {len(rows)} lignes copiées")

            except Exception as e:
                logger.warning(f"   ⚠ {table}: {str(e)}")

        target_conn.commit()

    finally:
        source_cursor.close()
        target_cursor.close()
        source_conn.close()
        target_conn.close()


def cleanup_and_transform(target_db, company_id, db_config):
    """Nettoie et transforme la base cible"""

    conn = psycopg2.connect(
        host=db_config['host'],
        port=db_config['port'],
        user=db_config['user'],
        password=db_config['password'],
        database=target_db,
    )

    cursor = conn.cursor()

    try:
        # 1. Faire de la company extraite LA company principale (ID=1)
        logger.info("   → Transformation de la company en company principale...")

        if company_id != 1:
            # Supprimer l'ancienne company ID=1 si elle existe
            cursor.execute("DELETE FROM res_company WHERE id = 1 AND id != %s", (company_id,))

            # Remapper la company vers ID=1
            cursor.execute("UPDATE res_company SET id = 1 WHERE id = %s", (company_id,))

            # Remapper toutes les références company_id
            company_tables = [
                'res_users', 'res_partner', 'account_move', 'account_payment',
                'account_journal', 'sale_order', 'crm_lead', 'product_template',
                'onedesk_property', 'onedesk_unit', 'onedesk_reservation',
            ]

            for table in company_tables:
                try:
                    cursor.execute(f"""
                        UPDATE {table}
                        SET company_id = 1
                        WHERE company_id = %s
                    """, (company_id,))
                except Exception as e:
                    logger.warning(f"   ⚠ Remapping {table}: {str(e)}")

        # 2. Supprimer les autres companies
        logger.info("   → Suppression des autres companies...")
        cursor.execute("DELETE FROM res_company WHERE id != 1")

        # 3. Nettoyer les record rules multi-tenant (plus nécessaires)
        logger.info("   → Suppression des record rules multi-tenant...")
        cursor.execute("""
            DELETE FROM ir_rule
            WHERE name LIKE '%Premium Manager%'
               OR name LIKE '%Multi-tenant%'
               OR name LIKE '%Own Company%'
        """)

        # 4. Normaliser les company_id
        logger.info("   → Normalisation des company_id...")

        # Partners système → company_id = NULL
        cursor.execute("""
            UPDATE res_partner
            SET company_id = NULL
            WHERE name IN ('Administrator', 'OdooBot', 'Public user', 'Portal')
        """)

        # 5. Supprimer les données SaaS (modèles de gestion SaaS)
        logger.info("   → Suppression des données SaaS de gestion...")
        saas_tables = ['saas_client', 'saas_plan', 'saas_database', 'saas_metric', 'saas_alert']
        for table in saas_tables:
            try:
                cursor.execute(f"TRUNCATE TABLE {table} CASCADE")
            except Exception:
                pass

        conn.commit()
        logger.info("   ✓ Nettoyage et transformation terminés")

    except Exception as e:
        conn.rollback()
        raise Exception(f"Erreur lors du nettoyage: {str(e)}")

    finally:
        cursor.close()
        conn.close()


def reset_sequences(target_db, db_config):
    """Réinitialise les séquences PostgreSQL"""

    conn = psycopg2.connect(
        host=db_config['host'],
        port=db_config['port'],
        user=db_config['user'],
        password=db_config['password'],
        database=target_db,
    )

    cursor = conn.cursor()

    try:
        # Réinitialiser toutes les séquences
        cursor.execute("""
            SELECT 'SELECT SETVAL(' ||
                   quote_literal(quote_ident(sequence_namespace.nspname) || '.' || quote_ident(class_sequence.relname)) ||
                   ', COALESCE(MAX(' || quote_ident(pg_attribute.attname) || '), 1)) FROM ' ||
                   quote_ident(table_namespace.nspname) || '.' || quote_ident(class_table.relname) || ';'
            FROM pg_depend
            INNER JOIN pg_class AS class_sequence ON class_sequence.oid = pg_depend.objid
            INNER JOIN pg_class AS class_table ON class_table.oid = pg_depend.refobjid
            INNER JOIN pg_attribute ON pg_attribute.attrelid = class_table.oid
                AND pg_depend.refobjsubid = pg_attribute.attnum
            INNER JOIN pg_namespace AS sequence_namespace ON sequence_namespace.oid = class_sequence.relnamespace
            INNER JOIN pg_namespace AS table_namespace ON table_namespace.oid = class_table.relnamespace
            WHERE class_sequence.relkind = 'S'
        """)

        for row in cursor.fetchall():
            try:
                cursor.execute(row[0])
            except Exception:
                pass

        conn.commit()
        logger.info("   ✓ Séquences réinitialisées")

    finally:
        cursor.close()
        conn.close()


def verify_migration(target_db, db_config):
    """Vérifie que la migration s'est bien passée"""

    conn = psycopg2.connect(
        host=db_config['host'],
        port=db_config['port'],
        user=db_config['user'],
        password=db_config['password'],
        database=target_db,
    )

    cursor = conn.cursor()

    checks = []

    try:
        # Vérifier qu'il n'y a qu'une seule company
        cursor.execute("SELECT COUNT(*) FROM res_company")
        company_count = cursor.fetchone()[0]
        checks.append(('Une seule company', company_count == 1))

        # Vérifier que la company principale a l'ID 1
        cursor.execute("SELECT id FROM res_company LIMIT 1")
        result = cursor.fetchone()
        main_company_id = result[0] if result else None
        checks.append(('Company principale = ID 1', main_company_id == 1))

        # Vérifier qu'il y a au moins un utilisateur
        cursor.execute("SELECT COUNT(*) FROM res_users WHERE active = True")
        user_count = cursor.fetchone()[0]
        checks.append(('Utilisateurs actifs > 0', user_count > 0))

        # Vérifier qu'il y a des données métier
        cursor.execute("SELECT COUNT(*) FROM res_partner WHERE company_id = 1 OR company_id IS NULL")
        partner_count = cursor.fetchone()[0]
        checks.append(('Partners de la company', partner_count > 0))

        # Afficher les résultats
        logger.info("")
        logger.info("   Résultats des vérifications:")
        all_passed = True
        for check_name, check_result in checks:
            status = "✅" if check_result else "❌"
            logger.info(f"      {status} {check_name}")
            if not check_result:
                all_passed = False

        if not all_passed:
            raise Exception("Certaines vérifications ont échoué!")

    finally:
        cursor.close()
        conn.close()


def main():
    parser = argparse.ArgumentParser(
        description='Extrait une company vers une base dédiée',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemples:
  # Migrer Company ID=2 vers une base dédiée
  python3 extract_company_to_database.py \\
      --source-db onedesk_production \\
      --company-id 2 \\
      --target-db onedesk_client_2

  # Avec configuration PostgreSQL personnalisée
  python3 extract_company_to_database.py \\
      --source-db onedesk_production \\
      --company-id 3 \\
      --target-db onedesk_client_3 \\
      --db-host 192.168.1.100 \\
      --db-port 5432 \\
      --db-user postgres \\
      --db-password MyPassword
        """
    )

    parser.add_argument('--source-db', required=True, help='Base source (ex: onedesk_production)')
    parser.add_argument('--company-id', type=int, required=True, help='ID de la company à extraire')
    parser.add_argument('--target-db', required=True, help='Base cible (ex: onedesk_client_1)')

    parser.add_argument('--db-host', default='localhost', help='Hôte PostgreSQL (défaut: localhost)')
    parser.add_argument('--db-port', type=int, default=5432, help='Port PostgreSQL (défaut: 5432)')
    parser.add_argument('--db-user', default='odoo', help='Utilisateur PostgreSQL (défaut: odoo)')
    parser.add_argument('--db-password', default='', help='Mot de passe PostgreSQL')

    args = parser.parse_args()

    db_config = {
        'host': args.db_host,
        'port': args.db_port,
        'user': args.db_user,
        'password': args.db_password,
    }

    extract_company_to_database(
        source_db=args.source_db,
        company_id=args.company_id,
        target_db=args.target_db,
        db_config=db_config
    )


if __name__ == '__main__':
    main()
