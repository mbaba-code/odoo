# OneDesk Core - Module de Gestion des Intégrations de Réservation

## 📋 Vue d'ensemble

**OneDesk Core** est un module Odoo qui centralise la gestion des réservations provenant de multiples plateformes de location de vacances (Airbnb, Booking.com, VRBO, etc.). Il synchronise automatiquement les réservations avec le calendrier Odoo et crée des tâches automatiques pour le personnel.

## ✨ Fonctionnalités principales

- **🔗 Multi-plateforme**: Support natif d'Airbnb, Booking.com, VRBO/Abritel
- **🔐 Sécurité OAuth 2.0**: Authentification sécurisée avec tokens chiffrés
- **🔄 Synchronisation bidirectionnelle**: Réservations ↔ Calendrier Odoo
- **📅 Automatisation des tâches**: Check-in/Check-out automatiques
- **📊 Monitoring**: Logs détaillés et statistiques par intégration
- **🧩 Flexibilité**: Support OAuth, iCal, CSV

## 🚀 Installation

### 1. Dépendances Python

```bash
pip install cryptography requests icalendar
```

### 2. Configuration Odoo (odoo.conf)

```ini
# Sécurité: Clé de chiffrement pour les tokens OAuth
# Générez avec: python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'
onedesk_encryption_key = <votre_clé_fernet_ici>
```

### 3. Installation du module

```bash
# Via Odoo studio ou en ligne de commande:
python odoo-bin -d <database> -i onedesk_core
```

## ⚙️ Configuration initiale

### Étape 1: Configurer les providers (platfromes)

Les providers (Airbnb, Booking.com, VRBO) sont **pré-configurés** mais nécessitent vos identifiants API.

**Allez à**: Intégrations → Configuration plateformes

Pour chaque provider, entrez:
- **Client ID** (application ID)
- **Client Secret** (secret API)
- Instructions spécifiques par plateforme ci-dessous

### Étape 2: Créer une intégration

**Allez à**: Intégrations → Nouvelles Intégrations

1. **Nom**: Ex. "Airbnb - Maison à Paris"
2. **Plateforme**: Sélectionnez (Airbnb, Booking.com, etc.)
3. **Méthode**: OAuth 2.0 (recommandé) ou iCal
4. **Propriété par défaut**: Sélectionnez la propriété gérée

### Étape 3: Connecter via OAuth

1. Cliquez sur **"Connecter"** dans l'intégration
2. Vous serez redirigé vers la plateforme (Airbnb, Booking.com, etc.)
3. Autorisez l'accès
4. OneDesk confirmera la connexion et lancera la première synchronisation

## 📖 Guide par plateforme

### 🏠 Airbnb

#### Obtenir les identifiants API

1. Allez à https://www.airbnb.com/developer/apps
2. Créez une nouvelle application
3. Configurez le redirect URI: `https://votre-odoo.com/onedesk/integration/oauth/callback`
4. Copiez:
   - **Client ID**
   - **Client Secret**

#### Configuration OneDesk

- **Plateforme**: Airbnb
- **Client ID**: Votre Airbnb Client ID
- **Client Secret**: Votre Airbnb Secret
- **Méthode**: OAuth 2.0

### 🏨 Booking.com

#### Obtenir les identifiants API

1. Allez à https://partner.booking.com/en/support/accounts/bconnect
2. Créez une connexion API
3. Configurez le redirect URI: `https://votre-odoo.com/onedesk/integration/oauth/callback`
4. Copiez les credentials

#### Configuration OneDesk

- **Plateforme**: Booking.com
- **Client ID**: Votre Booking Client ID
- **Client Secret**: Votre Booking Secret
- **Méthode**: OAuth 2.0

### 🌍 VRBO/Abritel

VRBO ne supporte que **iCal**. Utilisez l'URL du flux iCal de VRBO.

#### Configuration OneDesk

- **Plateforme**: VRBO/Abritel
- **Méthode**: iCal URL
- **URL iCal**: Copiez l'URL du flux iCal depuis VRBO

## 📊 Synchronisation

### Automatique (Cron)

Les réservations sont synchronisées **toutes les 15 minutes** automatiquement si:
- L'intégration est en état **"Connecté"**
- L'option **"Sync automatique"** est activée
- Le fréquence est respectée

### Manuel

Pour forcer une synchronisation immédiate:
1. Allez à l'intégration
2. Cliquez sur **"Synchroniser maintenant"**

### Monitoring

- **Logs**: Consultez l'historique dans l'intégration
- **Statistiques**: Total synchronisé, derniers comptes, erreurs
- **État**: draft, connecting, connected, error, expired, disconnected

## 📅 Automatisations

### Lors de la création d'une réservation:

1. **Événement calendrier** est automatiquement créé
   - Nom: `[Réservation] - [Unité]`
   - Dates: Selon la réservation
   - Visibilité: Publique

2. **Tâches automatiques** sont créées (optionnel):
   - Check-in (jour d'arrivée)
   - Check-out (jour de départ)
   - Ménage (avant check-in)
   - Maintenance (si nécessaire)

### Modification d'une réservation:

- L'événement calendrier est mis à jour automatiquement
- Les tâches associées sont mises à jour

### Suppression d'une réservation:

- L'événement calendrier est supprimé
- Les tâches sont supprimées

## 🔧 Options de configuration

### Propriété par défaut

Utilisée si le mapping automatique échoue:
- Utile pour un flux iCal sans informations de propriété

### Création automatique d'unités

Si activée: crée automatiquement les unités manquantes
- Nom: Extrait de la réservation (unit_name, property_name, location)
- Propriété: Propriété par défaut

### Création automatique de contacts

Si activée: crée automatiquement les contacts manquants
- Email: Utilisé comme identifiant unique
- Nom: Nom du client ou email
- Téléphone: Si disponible dans la source

## ⚠️ Dépannage

### Erreur: "Token invalide"

**Cause**: Token expiré ou révoqué
**Solution**:
1. Allez à l'intégration
2. Cliquez sur **"Reconnecter"**
3. Réautorisez l'accès

### Erreur: "État OAuth invalide"

**Cause**: Possible attaque CSRF ou cache navigateur
**Solution**:
1. Videz le cache du navigateur
2. Reconectez via OAuth

### Erreur: "Module icalendar manquant"

**Cause**: `icalendar` non installé
**Solution**:
```bash
pip install icalendar
```

### Pas de synchronisation

**Causes possibles**:
1. Intégration non en état "Connecté" → Vérifiez l'état
2. Sync automatique désactivée → Activez-la
3. Cron job non actif → Vérifiez `Paramètres → Tâches programmées`
4. Pas de clé de chiffrement → Vérifiez odoo.conf

**Solution**: Cliquez sur **"Synchroniser maintenant"** manuellement

### Réservations non importées

**Causes possibles**:
1. Dates invalides → Vérifiez le format iCal
2. Unit introuvable → Activez "Créer unités auto"
3. Contact introuvable → Activez "Créer contacts auto"

## 🛡️ Sécurité

### Chiffrement des tokens

Les tokens OAuth sont chiffrés avec **Fernet** (symétrique) si disponible.
- **Clé**: Définie dans `onedesk_encryption_key` (odoo.conf)
- **Fallback**: Si cryptography absent, tokens stockés en clair (⚠️ dangereux)

### Recommandations

✅ **À faire**:
- Générer et configurer une clé de chiffrement forte
- Utiliser OAuth au lieu de iCal quand possible
- Activer 2FA sur vos comptes de plateforme
- Auditer les logs régulièrement

❌ **À ne pas faire**:
- Partager vos Client ID/Secret
- Stocker les credentials en clair
- Utiliser le même secret pour plusieurs environnements

## 📞 Support

Pour les bugs ou questions:
- Consultez les logs d'intégration
- Vérifiez `odoo.log` pour les erreurs détaillées
- Testez la configuration API de la plateforme

## 📝 Exemple: Configuration complète Airbnb

```
1. Vérifiez les dépendances:
   pip install cryptography requests icalendar

2. Configurez odoo.conf:
   onedesk_encryption_key = EW_xMJWU8-Zs2PxK8q... (votre clé)

3. Créez un app sur https://www.airbnb.com/developer/apps
   - Client ID: a1b2c3d4e5f6
   - Client Secret: xyz789abc123def456
   - Redirect URI: https://odoo.example.com/onedesk/integration/oauth/callback

4. Dans OneDesk → Configuration plateformes → Airbnb:
   - Client ID: a1b2c3d4e5f6
   - Client Secret: xyz789abc123def456

5. Créez une intégration OneDesk:
   - Nom: "Airbnb - Studio Paris"
   - Plateforme: Airbnb
   - Propriété par défaut: Votre propriété

6. Cliquez "Connecter" et autorisez l'accès

7. Vérifiez les logs pour confirmer la synchronisation ✅
```

---

**Version**: 1.0.0
**Auteur**: Merveilles
**License**: LGPL-3
