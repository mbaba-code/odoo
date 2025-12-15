#!/usr/bin/env python3
"""
Test SMTP complet avec détection d'erreurs
À exécuter : python3 test_smtp_complet.py
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

print("\n" + "="*70)
print("🔍 TEST SMTP COMPLET - DIAGNOSTIC")
print("="*70 + "\n")

# Configuration à tester (REMPLACER PAR TES VRAIES VALEURS)
SMTP_CONFIG = {
    'host': 'smtp.gmail.com',  # Ou ton serveur SMTP
    'port': 587,
    'user': 'REMPLACER@gmail.com',  # TON EMAIL
    'password': 'REMPLACER',  # TON MOT DE PASSE D'APPLICATION
    'use_tls': True,
}

print("📋 Configuration SMTP à tester:")
print(f"   Host: {SMTP_CONFIG['host']}:{SMTP_CONFIG['port']}")
print(f"   User: {SMTP_CONFIG['user']}")
print(f"   TLS: {SMTP_CONFIG['use_tls']}")
print()

# Test 1: Connexion au serveur
print("1️⃣ Test de connexion au serveur SMTP...")
try:
    if SMTP_CONFIG['use_tls']:
        server = smtplib.SMTP(SMTP_CONFIG['host'], SMTP_CONFIG['port'])
        server.ehlo()
        server.starttls()
        server.ehlo()
    else:
        server = smtplib.SMTP_SSL(SMTP_CONFIG['host'], SMTP_CONFIG['port'])

    print("   ✅ Connexion réussie!")
except Exception as e:
    print(f"   ❌ ERREUR DE CONNEXION: {e}")
    print("\n💡 Solutions possibles:")
    print("   - Vérifier le host et le port")
    print("   - Vérifier la connexion internet")
    print("   - Essayer port 465 avec SSL au lieu de 587 TLS")
    exit(1)

# Test 2: Authentification
print("\n2️⃣ Test d'authentification...")
try:
    server.login(SMTP_CONFIG['user'], SMTP_CONFIG['password'])
    print("   ✅ Authentification réussie!")
except smtplib.SMTPAuthenticationError as e:
    print(f"   ❌ ERREUR D'AUTHENTIFICATION: {e}")
    print("\n💡 Solutions possibles:")
    print("   - Pour Gmail: Créer un MOT DE PASSE D'APPLICATION")
    print("     → https://myaccount.google.com/apppasswords")
    print("   - Ne PAS utiliser le mot de passe Gmail normal")
    print("   - Activer 'Accès moins sécurisé' (non recommandé)")
    exit(1)
except Exception as e:
    print(f"   ❌ ERREUR: {e}")
    exit(1)

# Test 3: Envoi d'email de test
print("\n3️⃣ Test d'envoi d'email...")
try:
    msg = MIMEMultipart()
    msg['From'] = SMTP_CONFIG['user']
    msg['To'] = 'merveillesbaba@gmail.com'  # EMAIL DE TEST
    msg['Subject'] = 'Test OneDesk Signature - Diagnostic'

    body = """
    <h2>✅ Test réussi!</h2>
    <p>Si vous recevez cet email, votre serveur SMTP fonctionne correctement.</p>
    <p>Les emails de signature OneDesk devraient maintenant fonctionner.</p>
    """
    msg.attach(MIMEText(body, 'html'))

    server.send_message(msg)
    print("   ✅ Email envoyé avec succès!")
    print(f"\n📧 Vérifiez l'email à: merveillesbaba@gmail.com")
    print("   (Vérifiez aussi les SPAM)")

except Exception as e:
    print(f"   ❌ ERREUR D'ENVOI: {e}")
    print("\n💡 Solutions possibles:")
    print("   - Vérifier que l'email FROM correspond à l'email du compte SMTP")
    exit(1)

# Fermer la connexion
server.quit()

print("\n" + "="*70)
print("✅ TOUS LES TESTS RÉUSSIS!")
print("="*70)
print("\nSi l'email n'arrive pas malgré ces tests:")
print("1. Vérifier les SPAM")
print("2. Attendre quelques minutes")
print("3. Vérifier que l'email n'est pas bloqué par le destinataire")
