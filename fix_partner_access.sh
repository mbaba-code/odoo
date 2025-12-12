#!/bin/bash
# Script de diagnostic et correction pour les erreurs d'accès res.partner

echo "=========================================="
echo "🔍 DIAGNOSTIC RÈGLES D'ACCÈS RES.PARTNER"
echo "=========================================="
echo ""

# 1. Vérifier si le code est à jour
echo "📦 1. Vérification du code..."
cd /home/user/odoo
git status

echo ""
echo "=========================================="
echo "🔧 CORRECTION À APPLIQUER DANS ODOO"
echo "=========================================="
echo ""

cat << 'EOF'
⚠️  IMPORTANT: Les modifications du code ne sont PAS automatiquement
appliquées dans Odoo. Vous devez mettre à jour le module!

📋 ÉTAPES À SUIVRE:

1. 🔄 Redémarrer Odoo
   sudo systemctl restart odoo
   # OU si vous utilisez un script:
   ./odoo-bin restart

2. 🔧 Mettre à jour le module OneDesk Core
   a) Interface Web:
      - Allez dans: Apps (Applications)
      - Recherchez: "OneDesk Core"
      - Cliquez sur: ⋮ (trois points) → Mettre à jour
      - Confirmez la mise à jour

   b) OU en ligne de commande:
      ./odoo-bin -u onedesk_core -d votre_base --stop-after-init

3. ✅ Vérifier que les règles sont chargées
   Paramètres → Technique → Sécurité → Règles d'enregistrement
   Cherchez: "Property Manager - Company Partners"
   Vérifiez: domain_force doit contenir:
   ['|', ('company_id', '=', False), ('company_id', '=', user.company_id.id)]

========================================
🔍 DIAGNOSTIC SUPPLÉMENTAIRE (si ça ne marche toujours pas)
========================================

Si après mise à jour vous avez toujours l'erreur, exécutez dans le shell Odoo:

# Diagnostic 1: Vérifier le contact problématique
contact = env['res.partner'].sudo().browse(1755)
print(f"Contact ID: {contact.id}")
print(f"Nom: {contact.name}")
print(f"Email: {contact.email}")
print(f"Company ID: {contact.company_id}")
print(f"Company Name: {contact.company_id.name if contact.company_id else 'AUCUNE (partagé)'}")

# Diagnostic 2: Vérifier l'administrateur
admin = env['res.users'].browse(2)
print(f"\nAdmin ID: {admin.id}")
print(f"Nom: {admin.name}")
print(f"Company ID: {admin.company_id}")
print(f"Company Name: {admin.company_id.name}")
print(f"Groupes: {[g.name for g in admin.groups_id]}")

# Diagnostic 3: Vérifier les règles actives
rules = env['ir.rule'].search([
    ('model_id.model', '=', 'res.partner'),
    ('groups', 'in', admin.groups_id.ids)
])
print(f"\n📋 Règles actives pour res.partner:")
for rule in rules:
    print(f"  - {rule.name}: {rule.domain_force}")

# SOLUTION SI COMPANY_ID DIFFÉRENT:
# Si le contact a company_id=X et l'admin company_id=Y:
if contact.company_id and contact.company_id != admin.company_id:
    print("\n⚠️  PROBLÈME DÉTECTÉ:")
    print(f"Le contact appartient à: {contact.company_id.name}")
    print(f"L'admin appartient à: {admin.company_id.name}")
    print("\n✅ SOLUTIONS:")
    print("1. Mettre le contact sans company (partagé):")
    print("   contact.sudo().write({'company_id': False})")
    print("2. OU donner l'accès multi-company à l'admin")
    print("3. OU ajouter l'admin au groupe System (accès tout)")

EOF

echo ""
echo "=========================================="
echo "🚀 COMMANDES RAPIDES"
echo "=========================================="
echo ""
echo "# Redémarrer Odoo:"
echo "sudo systemctl restart odoo"
echo ""
echo "# Mise à jour module (ligne de commande):"
echo "cd /home/user/odoo"
echo "./odoo-bin -u onedesk_core -d VOTRE_BASE --stop-after-init"
echo ""
echo "# Shell Odoo pour diagnostic:"
echo "./odoo-bin shell -d VOTRE_BASE"
echo ""
