#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script pour réparer l'état inconsistant du module onedesk_core

Ce script:
1. Se connecte à la base de données Odoo
2. Trouve le module onedesk_core
3. Réinitialise son état à 'installed'
4. Supprime les opérations en attente

Usage:
    python3 fix_module_state.py
"""

import psycopg2
import sys

# Configuration (à adapter selon votre environnement)
DB_CONFIG = {
    'host': '127.0.0.1',
    'port': 5432,
    'user': 'odoo_prod',
    'password': 'MervoProd123!',
    'database': 'base2',  # Base de données problématique
}

def fix_module_state():
    """Répare l'état du module onedesk_core"""

    print("=" * 80)
    print("🔧 RÉPARATION DE L'ÉTAT DU MODULE onedesk_core")
    print("=" * 80)

    try:
        # Connexion à la base
        print(f"\n1️⃣ Connexion à la base {DB_CONFIG['database']}...")
        conn = psycopg2.connect(**DB_CONFIG)
        conn.autocommit = False
        cur = conn.cursor()

        # Vérifier l'état actuel du module
        print("\n2️⃣ Vérification de l'état actuel...")
        cur.execute("""
            SELECT id, name, state, latest_version
            FROM ir_module_module
            WHERE name = 'onedesk_core'
        """)

        result = cur.fetchone()
        if not result:
            print("❌ Module onedesk_core non trouvé dans la base!")
            return False

        module_id, name, current_state, version = result
        print(f"   Module: {name}")
        print(f"   ID: {module_id}")
        print(f"   État actuel: {current_state}")
        print(f"   Version: {version}")

        # Réinitialiser l'état du module
        print("\n3️⃣ Réinitialisation de l'état du module...")

        # Options selon l'état actuel:
        # - Si 'to upgrade' ou 'to install' → mettre en 'installed'
        # - Si 'uninstalled' → laisser tel quel

        if current_state in ('to upgrade', 'to install', 'to remove'):
            new_state = 'installed'
            print(f"   Changement: {current_state} → {new_state}")

            cur.execute("""
                UPDATE ir_module_module
                SET state = %s
                WHERE id = %s
            """, (new_state, module_id))

            print(f"   ✅ État mis à jour: {new_state}")
        else:
            print(f"   ℹ️ État actuel '{current_state}' OK, pas de modification")

        # Supprimer les opérations en attente dans ir_cron
        print("\n4️⃣ Nettoyage des opérations cron en attente...")
        cur.execute("""
            DELETE FROM ir_cron
            WHERE id IN (
                SELECT id FROM ir_cron
                WHERE model = 'ir.module.module'
                AND active = False
            )
        """)
        deleted_cron = cur.rowcount
        print(f"   ✅ {deleted_cron} tâches cron supprimées")

        # Vérifier les dépendances
        print("\n5️⃣ Vérification des dépendances...")
        cur.execute("""
            SELECT d.name, m.state
            FROM ir_module_module_dependency d
            JOIN ir_module_module m ON m.name = d.name
            WHERE d.module_id = %s
        """, (module_id,))

        dependencies = cur.fetchall()
        print(f"   Dépendances ({len(dependencies)}):")

        all_deps_ok = True
        for dep_name, dep_state in dependencies:
            status = "✅" if dep_state == 'installed' else "❌"
            print(f"     {status} {dep_name}: {dep_state}")
            if dep_state != 'installed':
                all_deps_ok = False

        if not all_deps_ok:
            print("\n   ⚠️ ATTENTION: Certaines dépendances ne sont pas installées!")
            print("   Vous devrez peut-être les installer manuellement.")

        # Commit les changements
        print("\n6️⃣ Commit des changements...")
        conn.commit()
        print("   ✅ Changements enregistrés dans la base de données")

        # Fermeture
        cur.close()
        conn.close()

        print("\n" + "=" * 80)
        print("✅ RÉPARATION TERMINÉE AVEC SUCCÈS!")
        print("=" * 80)
        print("\n📋 Prochaines étapes:")
        print("   1. Redémarrer Odoo: sudo systemctl restart odoo")
        print("   2. Vérifier les logs: journalctl -u odoo -f")
        print("   3. Tester le module dans l'interface Odoo")
        print()

        return True

    except psycopg2.Error as e:
        print(f"\n❌ Erreur PostgreSQL: {e}")
        if conn:
            conn.rollback()
        return False
    except Exception as e:
        print(f"\n❌ Erreur: {e}")
        if conn:
            conn.rollback()
        return False
    finally:
        if 'conn' in locals() and conn:
            conn.close()

if __name__ == '__main__':
    success = fix_module_state()
    sys.exit(0 if success else 1)
