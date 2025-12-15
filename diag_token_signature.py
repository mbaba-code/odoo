"""
Diagnostic rapide du problème de token
À exécuter via: python3 odoo-bin shell -c odoo.conf -d votre_base
Puis: exec(open('diag_token_signature.py').read())
"""

def diagnostic_token():
    """Diagnostic des tokens de signature"""

    print("\n" + "="*70)
    print("🔍 DIAGNOSTIC TOKEN SIGNATURE")
    print("="*70 + "\n")

    # 1. Vérifier que le champ existe
    print("1️⃣ Vérification du champ access_token...")
    try:
        Signature = env['onedesk.document.signature']

        # Vérifier si le champ existe dans le modèle
        if 'access_token' in Signature._fields:
            print("   ✅ Le champ 'access_token' existe dans le modèle")
        else:
            print("   ❌ Le champ 'access_token' N'EXISTE PAS dans le modèle!")
            print("   → Vous devez mettre à jour le module onedesk_core")
            print("   → Commande: python3 odoo-bin -c odoo.conf -d votre_base -u onedesk_core --stop-after-init")
            return
    except Exception as e:
        print(f"   ❌ Erreur: {e}")
        return

    # 2. Vérifier les signatures
    print("\n2️⃣ Vérification des signatures...")
    all_sigs = Signature.sudo().search([])
    print(f"   Total signatures: {len(all_sigs)}")

    if len(all_sigs) == 0:
        print("   ⚠️  Aucune signature trouvée")
        print("   → Créez une signature de test pour tester le système")
        return

    # 3. Compter celles avec/sans token
    print("\n3️⃣ Analyse des tokens...")
    with_token = Signature.sudo().search([('access_token', '!=', False)])
    without_token = len(all_sigs) - len(with_token)

    print(f"   ✅ Avec token: {len(with_token)}")
    print(f"   ❌ Sans token: {without_token}")

    # 4. Afficher les dernières signatures
    print("\n4️⃣ Dernières signatures créées:")
    recent = Signature.sudo().search([], order='create_date desc', limit=5)

    for sig in recent:
        token_status = "✅ OUI" if sig.access_token else "❌ NON"
        print(f"\n   Signature #{sig.id}:")
        print(f"   - Email: {sig.signer_email}")
        print(f"   - Document: {sig.document_id.name if sig.document_id else 'N/A'}")
        print(f"   - Token: {token_status}")
        if sig.access_token:
            print(f"   - Token value: {sig.access_token[:16]}...")

    # 5. Test de création d'une nouvelle signature
    print("\n5️⃣ Test de création d'une signature...")
    print("   (Annulé après création pour ne pas polluer la base)")

    try:
        # Créer une signature de test
        test_doc = env['onedesk.document'].sudo().search([], limit=1)

        if not test_doc:
            print("   ⚠️  Aucun document trouvé pour le test")
        else:
            # Créer mais ne pas envoyer d'email
            test_sig = Signature.with_context(mail_create_nosubscribe=True).sudo().create({
                'document_id': test_doc.id,
                'signer_email': 'test@example.com',
                'signer_name': 'Test Token',
                'status': 'pending',
            })

            if test_sig.access_token:
                print(f"   ✅ Nouvelle signature créée avec token: {test_sig.access_token[:16]}...")
                print(f"   → Le système fonctionne correctement pour les nouvelles signatures")
            else:
                print(f"   ❌ Nouvelle signature créée SANS token!")
                print(f"   → Problème de configuration du champ")

            # Supprimer la signature de test
            test_sig.sudo().unlink()
            print(f"   🗑️  Signature de test supprimée")

    except Exception as e:
        print(f"   ❌ Erreur lors du test: {e}")

    # 6. Recommandations
    print("\n" + "="*70)
    print("📋 RECOMMANDATIONS")
    print("="*70)

    if without_token > 0:
        print(f"""
⚠️  PROBLÈME DÉTECTÉ: {without_token} signature(s) n'ont pas de token

SOLUTION:
1. Exécutez le script de génération des tokens manquants:
   exec(open('generate_missing_tokens.py').read())

2. Ou manuellement en SQL (si le script ne fonctionne pas):
   UPDATE onedesk_document_signature
   SET access_token = uuid_generate_v4()::text
   WHERE access_token IS NULL OR access_token = '';
""")
    else:
        print("""
✅ TOUT EST OK!

- Toutes les signatures ont un token
- Le système devrait fonctionner correctement

Si vous avez toujours l'erreur "Token manquant":
1. Vérifiez que l'email contient bien le paramètre ?access_token=...
2. Vérifiez les logs Odoo pour voir l'URL complète
3. Testez avec une nouvelle signature
""")

    print("\n" + "="*70)
    print("FIN DU DIAGNOSTIC")
    print("="*70 + "\n")

# Exécuter
diagnostic_token()
