#!/usr/bin/env python3
"""
Créer un website pour la company du Premium Manager
À exécuter: ./odoo-bin shell -d VOTRE_BASE < create_premium_website.py
"""

print("=" * 80)
print("🏗️ CRÉATION WEBSITE POUR PREMIUM MANAGER")
print("=" * 80)

# 1. Trouver l'utilisateur Premium Test
premium_user = env['res.users'].sudo().search([('login', 'ilike', 'premium')], limit=1)

if not premium_user:
    print("\n❌ Aucun utilisateur Premium trouvé!")
    print("   Créez d'abord un utilisateur avec le login contenant 'premium'")
else:
    print(f"\n✅ Utilisateur trouvé: {premium_user.name} (ID: {premium_user.id})")
    print(f"   Company: {premium_user.company_id.name} (ID: {premium_user.company_id.id})")
    
    # 2. Vérifier si un website existe déjà pour cette company
    existing_website = env['website'].sudo().search([
        ('company_id', '=', premium_user.company_id.id)
    ], limit=1)
    
    if existing_website:
        print(f"\n✅ Website existant trouvé: {existing_website.name} (ID: {existing_website.id})")
    else:
        print(f"\n⚙️ Création d'un nouveau website pour {premium_user.company_id.name}...")
        
        new_website = env['website'].sudo().create({
            'name': f'Site {premium_user.company_id.name}',
            'company_id': premium_user.company_id.id,
            'domain': '',
        })
        
        env.cr.commit()
        print(f"✅ Website créé: {new_website.name} (ID: {new_website.id})")
    
    # 3. Vérifier tous les websites
    print(f"\n{'=' * 80}")
    print("📋 LISTE DE TOUS LES WEBSITES:")
    print(f"{'=' * 80}\n")
    
    all_websites = env['website'].sudo().search([])
    for w in all_websites:
        company_name = w.company_id.name if w.company_id else "PARTAGÉ (aucune company)"
        print(f"   • {w.name} (ID: {w.id}) → Company: {company_name}")
    
    # 4. Test d'accès pour Premium Test
    print(f"\n{'=' * 80}")
    print(f"🔍 TEST D'ACCÈS POUR {premium_user.name}")
    print(f"{'=' * 80}\n")
    
    premium_env = env(user=premium_user.id)
    
    try:
        accessible_websites = premium_env['website'].search([])
        print(f"✅ {premium_user.name} peut accéder à {len(accessible_websites)} website(s):")
        for w in accessible_websites:
            company_name = w.company_id.name if w.company_id else "PARTAGÉ"
            print(f"      • {w.name} (ID: {w.id}) - {company_name}")
    except Exception as e:
        print(f"❌ Erreur: {e}")

print(f"\n{'=' * 80}")
print("✅ TERMINÉ!")
print(f"{'=' * 80}")
