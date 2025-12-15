#!/usr/bin/env python3
"""
Script de diagnostic pour tester l'envoi d'emails de signature
À exécuter depuis le shell Odoo : odoo shell -c odoo.conf
"""

import logging
_logger = logging.getLogger(__name__)

def test_signature_email():
    """Tester l'envoi d'email de signature"""

    print("\n" + "="*60)
    print("TEST DIAGNOSTIC - EMAILS DE SIGNATURE")
    print("="*60 + "\n")

    # 1. Vérifier la configuration SMTP
    print("1️⃣ Vérification serveur SMTP...")
    IrMailServer = env['ir.mail_server']
    mail_servers = IrMailServer.sudo().search([])

    if not mail_servers:
        print("❌ PROBLÈME: Aucun serveur SMTP configuré!")
        print("   → Allez dans: Paramètres → Techniques → Email → Serveurs de messagerie sortante")
        return False
    else:
        for server in mail_servers:
            print(f"✅ Serveur SMTP trouvé: {server.name}")
            print(f"   - Host: {server.smtp_host}:{server.smtp_port}")
            print(f"   - User: {server.smtp_user}")
            print(f"   - Encryption: {server.smtp_encryption}")

    # 2. Vérifier le template email
    print("\n2️⃣ Vérification template email...")
    try:
        template = env.ref('onedesk_core.email_template_signature_request')
        print(f"✅ Template trouvé: {template.name}")
        print(f"   - Modèle: {template.model}")
        print(f"   - Email From: {template.email_from}")
        print(f"   - Email To: {template.email_to}")
    except Exception as e:
        print(f"❌ PROBLÈME: Template non trouvé! {e}")
        return False

    # 3. Chercher un document en signature
    print("\n3️⃣ Recherche documents en signature...")
    Document = env['onedesk.document']
    docs = Document.sudo().search([('status', '=', 'pending_signature')], limit=1)

    if not docs:
        print("⚠️  Aucun document en attente de signature")
        print("   Créez un document et envoyez-le en signature d'abord")
        return False

    doc = docs[0]
    print(f"✅ Document trouvé: {doc.name} (ID: {doc.id})")

    # 4. Vérifier les signatures
    print("\n4️⃣ Vérification signatures...")
    Signature = env['onedesk.document.signature']
    signatures = Signature.sudo().search([('document_id', '=', doc.id)])

    if not signatures:
        print("❌ PROBLÈME: Aucune signature trouvée pour ce document!")
        return False

    for sig in signatures:
        print(f"\n   Signature #{sig.id}:")
        print(f"   - Signataire: {sig.signer_name} ({sig.signer_email})")
        print(f"   - Statut: {sig.status}")

        # Vérifier s'il y a des messages (emails)
        messages = env['mail.message'].sudo().search([
            ('res_id', '=', sig.id),
            ('model', '=', 'onedesk.document.signature')
        ])
        print(f"   - Messages: {len(messages)} message(s)")

        # Vérifier s'il y a des mails dans la queue
        mails = env['mail.mail'].sudo().search([
            ('res_id', '=', sig.id),
            ('model', '=', 'onedesk.document.signature')
        ])
        print(f"   - Emails en queue: {len(mails)}")
        for mail in mails:
            print(f"     • État: {mail.state}, À: {mail.email_to}")
            if mail.failure_reason:
                print(f"     • Erreur: {mail.failure_reason}")

    # 5. Test d'envoi manuel
    print("\n5️⃣ Test envoi manuel...")
    test_sig = signatures[0]

    try:
        print(f"   Tentative d'envoi à {test_sig.signer_email}...")
        mail_id = template.send_mail(test_sig.id, force_send=True)
        print(f"✅ Email envoyé! (mail_id={mail_id})")

        # Vérifier le statut
        mail = env['mail.mail'].sudo().browse(mail_id)
        print(f"   - État du mail: {mail.state}")
        if mail.failure_reason:
            print(f"   - Erreur: {mail.failure_reason}")

    except Exception as e:
        print(f"❌ Erreur lors de l'envoi: {e}")
        import traceback
        traceback.print_exc()
        return False

    print("\n" + "="*60)
    print("FIN DU DIAGNOSTIC")
    print("="*60 + "\n")

    return True

# Exécuter le test
if __name__ == '__main__':
    test_signature_email()
