# Vérification des websites visibles par Premium Manager

user = env['res.users'].browse(5)  # Jeo booby

print(f"Utilisateur: {user.name}")
print(f"Company: {user.company_id.name}")
print(f"Company IDs: {[c.name for c in user.company_ids]}")

# Voir ce que l'utilisateur peut voir (avec ses règles)
print(f"\n📋 WEBSITES VISIBLES PAR L'UTILISATEUR:")
websites = env['website'].sudo(user.id).search([])
for site in websites:
    company = site.company_id.name if site.company_id else "AUCUNE"
    print(f"  - {site.name} (ID: {site.id}, Company: {company})")

print(f"\nTotal: {len(websites)} site(s) visible(s)")

# Voir TOUS les websites en mode admin
print(f"\n📋 TOUS LES WEBSITES (mode admin):")
all_sites = env['website'].sudo().search([])
for site in all_sites:
    company = site.company_id.name if site.company_id else "AUCUNE"
    print(f"  - {site.name} (ID: {site.id}, Company: {company})")

print(f"\nTotal: {len(all_sites)} site(s) au total")
