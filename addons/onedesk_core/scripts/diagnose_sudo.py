#!/usr/bin/env python3
# Script de diagnostic sudo pour Odoo
import subprocess
import os
import sys

print("=" * 60)
print("🔍 DIAGNOSTIC SUDO POUR ODOO SAAS")
print("=" * 60)
print()

# 1. Utilisateur actuel
print("1️⃣ Utilisateur Python actuel:")
print(f"   User ID: {os.getuid()}")
print(f"   User: {os.getenv('USER', 'unknown')}")
print(f"   Effective User: {os.geteuid()}")
print()

# 2. Test sudo basique
print("2️⃣ Test sudo basique (whoami):")
try:
    result = subprocess.run(
        ['sudo', '-n', 'whoami'],
        capture_output=True,
        text=True,
        timeout=5
    )
    if result.returncode == 0:
        print(f"   ✅ SUCCESS: {result.stdout.strip()}")
    else:
        print(f"   ❌ FAILED: {result.stderr.strip()}")
        print(f"   Return code: {result.returncode}")
except Exception as e:
    print(f"   ❌ EXCEPTION: {str(e)}")
print()

# 3. Test sudo sur script
print("3️⃣ Test sudo sur script de test:")
script_path = "/home/user/odoo/addons/onedesk_core/scripts/test_client_domain_local.sh"
try:
    result = subprocess.run(
        ['sudo', '-n', script_path],
        capture_output=True,
        text=True,
        timeout=5
    )
    if result.returncode == 0:
        print(f"   ✅ Script accepté par sudo")
        print(f"   Output: {result.stdout[:100]}")
    else:
        print(f"   ❌ Script refusé:")
        print(f"   STDERR: {result.stderr}")
        print(f"   Return code: {result.returncode}")
except Exception as e:
    print(f"   ❌ EXCEPTION: {str(e)}")
print()

# 4. Vérifier permissions sudoers
print("4️⃣ Configuration sudoers:")
sudoers_file = "/etc/sudoers.d/odoo-saas"
if os.path.exists(sudoers_file):
    print(f"   ✅ Fichier existe: {sudoers_file}")
    stat_info = os.stat(sudoers_file)
    print(f"   Permissions: {oct(stat_info.st_mode)[-3:]}")
    print(f"   Owner: {stat_info.st_uid}")
else:
    print(f"   ❌ Fichier manquant: {sudoers_file}")
print()

# 5. Lister permissions sudo
print("5️⃣ Permissions sudo de l'utilisateur actuel:")
try:
    result = subprocess.run(
        ['sudo', '-n', '-l'],
        capture_output=True,
        text=True,
        timeout=5
    )
    if result.returncode == 0:
        lines = result.stdout.split('\n')[:10]
        for line in lines:
            if line.strip():
                print(f"   {line}")
    else:
        print(f"   ❌ Impossible de lister: {result.stderr}")
except Exception as e:
    print(f"   ❌ EXCEPTION: {str(e)}")
print()

# 6. Test exact de la commande Odoo
print("6️⃣ Test commande exacte utilisée par Odoo:")
cmd = ['sudo', '-n', script_path, 'test.local', 'testdb']
print(f"   Commande: {' '.join(cmd)}")
try:
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=5
    )
    print(f"   Return code: {result.returncode}")
    if result.returncode == 0:
        print(f"   ✅ SUCCESS")
        print(f"   Output preview: {result.stdout[:200]}")
    else:
        print(f"   ❌ FAILED")
        print(f"   STDERR: {result.stderr}")
        print(f"   STDOUT: {result.stdout[:200]}")
except Exception as e:
    print(f"   ❌ EXCEPTION: {str(e)}")
print()

print("=" * 60)
print("Fin du diagnostic")
print("=" * 60)
