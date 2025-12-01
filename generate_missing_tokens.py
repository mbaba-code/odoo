"""
Script pour générer les access_token manquants sur les signatures existantes
À exécuter via: python3 odoo-bin shell -c odoo.conf -d votre_base
Puis: exec(open('generate_missing_tokens.py').read())
"""

def generate_missing_tokens():
    """Génère les access_token manquants pour les signatures existantes"""

    print("\n" + "="*70)
    print("🔧 GÉNÉRATION DES TOKENS MANQUANTS")
    print("="*70 + "\n")

    import uuid

    # Chercher toutes les signatures
    Signature = env['onedesk.document.signature'].sudo()
    all_signatures = Signature.search([])

    print(f"📊 Total de signatures trouvées: {len(all_signatures)}")

    # Compter celles sans token
    missing_token_count = 0
    fixed_count = 0

    for sig in all_signatures:
        if not sig.access_token:
            missing_token_count += 1

            # Générer un nouveau token
            new_token = str(uuid.uuid4())

            try:
                # Utiliser sudo() et write() directement
                sig.sudo().write({'access_token': new_token})
                fixed_count += 1
                print(f"   ✅ Signature #{sig.id} ({sig.signer_email}): token généré")
            except Exception as e:
                print(f"   ❌ Erreur signature #{sig.id}: {e}")

    print(f"\n📈 Résultat:")
    print(f"   - Signatures sans token: {missing_token_count}")
    print(f"   - Tokens générés: {fixed_count}")
    print(f"   - Total signatures avec token: {len(all_signatures) - missing_token_count + fixed_count}")

    # Vérification finale
    print(f"\n🔍 Vérification finale...")
    all_signatures = Signature.search([])
    signatures_with_token = Signature.search([('access_token', '!=', False)])

    print(f"   ✅ {len(signatures_with_token)}/{len(all_signatures)} signatures ont maintenant un token")

    if len(signatures_with_token) == len(all_signatures):
        print(f"\n🎉 SUCCÈS: Toutes les signatures ont un token!")
    else:
        missing = len(all_signatures) - len(signatures_with_token)
        print(f"\n⚠️  ATTENTION: {missing} signature(s) n'ont toujours pas de token")

        # Afficher celles qui n'ont pas de token
        signatures_without_token = Signature.search([
            '|',
            ('access_token', '=', False),
            ('access_token', '=', '')
        ])

        for sig in signatures_without_token:
            print(f"      - Signature #{sig.id}: {sig.signer_email}")

    print("\n" + "="*70)
    print("FIN DU SCRIPT")
    print("="*70 + "\n")

# Exécuter
generate_missing_tokens()
