#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script Odoo Shell pour réparer l'état du module onedesk_core

À exécuter avec: ./odoo-bin shell -d base2 -c debian/odoo.conf < fix_module_odoo_shell.py
"""

print("=" * 80)
print("🔧 RÉPARATION DE L'ÉTAT DU MODULE onedesk_core via Odoo Shell")
print("=" * 80)

# Trouver le module onedesk_core
module = env['ir.module.module'].search([('name', '=', 'onedesk_core')], limit=1)

if not module:
    print("❌ Module onedesk_core non trouvé!")
    exit(1)

print(f"\n📋 État actuel du module:")
print(f"   Nom: {module.name}")
print(f"   État: {module.state}")
print(f"   Version: {module.latest_version}")

# Réinitialiser l'état si nécessaire
if module.state in ('to upgrade', 'to install', 'to remove'):
    print(f"\n🔄 Réinitialisation de l'état: {module.state} → installed")
    module.write({'state': 'installed'})
    env.cr.commit()
    print("   ✅ État réinitialisé")
else:
    print(f"\n✅ État '{module.state}' correct, pas de modification nécessaire")

# Vérifier les dépendances
print("\n📦 Vérification des dépendances:")
dependencies = env['ir.module.module.dependency'].search([('module_id', '=', module.id)])

for dep in dependencies:
    dep_module = env['ir.module.module'].search([('name', '=', dep.name)], limit=1)
    if dep_module:
        status = "✅" if dep_module.state == 'installed' else "❌"
        print(f"   {status} {dep.name}: {dep_module.state}")
    else:
        print(f"   ⚠️ {dep.name}: NON TROUVÉ")

print("\n" + "=" * 80)
print("✅ VÉRIFICATION TERMINÉE")
print("=" * 80)
print("\n📋 Pour mettre à jour le module, exécutez:")
print("   ./odoo-bin -u onedesk_core -d base2 -c debian/odoo.conf --stop-after-init")
print()
