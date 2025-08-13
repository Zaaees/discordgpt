# 🚀 Déploiement sur Render - Guide Complet

## ✅ Corrections apportées

Votre bot a été corrigé pour résoudre les problèmes de déploiement sur Render :

- ✅ **Erreur 429 (Rate Limited)** : Système de retry automatique
- ✅ **Credentials Google Drive** : Support des variables d'environnement
- ✅ **Gestion d'erreurs** : Logs améliorés et gestion robuste
- ✅ **Healthcheck** : Serveur HTTP pour Render

## 📋 Étapes de déploiement

### 1. Préparer les credentials Google Drive

```bash
python encode_credentials.py encode
```

Cela génère deux options :
- **Base64** (recommandé) : `GOOGLE_CREDENTIALS_B64=...`
- **JSON direct** : `GOOGLE_CREDENTIALS_JSON="..."`

### 2. Créer le service sur Render

1. Aller sur [render.com](https://render.com)
2. **New** → **Web Service**
3. Connecter votre repository GitHub
4. Configuration :
   - **Build Command** : `pip install -r requirements.txt`
   - **Start Command** : `python main.py`
   - **Instance Type** : Starter (gratuit)

### 3. Variables d'environnement

Dans l'onglet **Environment** de Render, ajouter :

#### 🔑 Obligatoires
```
DISCORD_TOKEN=votre_token_discord_ici
DISCORD_GUILD_ID=123456789012345678
OPENAI_API_KEY=sk-...
```

#### ⚙️ Optionnelles
```
OPENAI_MODEL=gpt-4
OPENAI_EMBED_MODEL=text-embedding-ada-002
```

#### 📁 Google Drive (choisir UNE option)

**Option A - Base64** (plus simple) :
```
GOOGLE_CREDENTIALS_B64=ewogICJ0eXBlIjogInNlcnZpY2VfYWNjb3VudCIsC...
```

**Option B - JSON direct** :
```
GOOGLE_CREDENTIALS_JSON={"type":"service_account","project_id":"..."}
```

**Autres variables Drive** :
```
DRIVE_FILE_ID=1ABC...
DRIVE_FOLDER_ID=1DEF...
```

### 4. Déployer

Une fois les variables configurées, cliquez sur **Deploy** ou poussez un commit.

## 🔍 Vérification

### Logs de démarrage attendus
```
[2025-08-13 14:00:00] [INFO] Démarrage du bot Discord de Lore RP
[2025-08-13 14:00:00] [INFO] Healthcheck HTTP actif sur 0.0.0.0:10000
[2025-08-13 14:00:01] [INFO] Credentials Google Drive chargés depuis GOOGLE_CREDENTIALS_B64
[2025-08-13 14:00:01] [INFO] Service Google Drive initialisé avec succès
[2025-08-13 14:00:02] [INFO] Tentative de connexion 1/5
[2025-08-13 14:00:03] [INFO] Bot connecté et prêt.
```

### Tests Discord
1. Le bot apparaît **en ligne** sur Discord
2. Commande `/setup` disponible (admin uniquement)
3. Commande `/lore` disponible

## 🛠️ Dépannage

### Rate Limiting (429)
- Le bot retry automatiquement avec backoff exponentiel
- Attendre 30s-5min entre les tentatives
- Vérifier que le token Discord est valide

### Google Drive ne fonctionne pas
- Vérifier que le JSON est valide avec `python test_config.py`
- S'assurer que le service account a accès au Drive
- Le bot fonctionne sans Google Drive (index local uniquement)

### Problèmes de mémoire
- Passer à une instance Render plus puissante
- Réduire `MAX_CHUNK_CHARS` dans le code si nécessaire

### Bot ne répond pas
- Vérifier les logs dans Render
- S'assurer que `DISCORD_GUILD_ID` est correct
- Vérifier les permissions du bot sur Discord

## 📞 Support

Si vous rencontrez des problèmes :
1. Vérifiez les logs dans Render
2. Testez la config avec `python test_config.py`
3. Vérifiez que toutes les variables d'environnement sont définies

## 🎯 Commandes utiles

```bash
# Tester la configuration
python test_config.py

# Encoder les credentials
python encode_credentials.py encode votre-fichier.json

# Décoder pour vérifier
python encode_credentials.py decode "base64_string_here"
```

---

**✨ Votre bot est maintenant prêt pour Render !**
