# Guide de déploiement sur Render

## Problèmes identifiés et solutions

### 1. Erreur 429 (Rate Limited)
**Problème** : Discord/Cloudflare bloque temporairement les connexions
**Solution** : Le bot implémente maintenant un système de retry avec backoff exponentiel

### 2. Fichier de credentials manquant
**Problème** : Le chemin `C:/Users/freed/Desktop/Code/citadelle-serveur-23730de87edb.json` n'existe pas sur Render
**Solution** : Utiliser les variables d'environnement

## Étapes de déploiement

### 1. Préparer les credentials Google Drive

Si vous utilisez Google Drive, encodez vos credentials :

```bash
python encode_credentials.py encode citadelle-serveur-23730de87edb.json
```

Copiez la sortie base64 pour l'utiliser dans Render.

### 2. Configurer Render

1. **Créer un nouveau Web Service** sur Render
2. **Connecter votre repository** GitHub
3. **Configuration du service** :
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `python main.py`
   - Instance Type: Starter

### 3. Variables d'environnement sur Render

Dans l'onglet "Environment" de votre service Render, ajoutez :

#### Obligatoires
```
DISCORD_TOKEN=votre_token_discord
DISCORD_GUILD_ID=id_de_votre_serveur
OPENAI_API_KEY=votre_cle_openai
```

#### Optionnelles
```
OPENAI_MODEL=gpt-4
OPENAI_EMBED_MODEL=text-embedding-ada-002
```

#### Google Drive (choisir UNE des deux options)

**Option 1 - Base64 (recommandé)** :
```
GOOGLE_CREDENTIALS_B64=ewogICJ0eXBlIjogInNlcnZpY2VfYWNjb3VudCIsC...
```

**Option 2 - JSON direct (sur une seule ligne)** :
```
GOOGLE_CREDENTIALS_JSON={"type":"service_account","project_id":"...","private_key":"..."}
```

**Autres variables Drive** :
```
DRIVE_FILE_ID=id_du_fichier_drive
DRIVE_FOLDER_ID=id_du_dossier_drive
```

### 4. Déployer

Une fois les variables configurées, Render déploiera automatiquement votre bot.

## Vérification du déploiement

1. **Logs** : Vérifiez les logs dans Render pour voir si le bot se connecte
2. **Discord** : Le bot devrait apparaître en ligne
3. **Commandes** : Testez `/setup` et `/lore`

## Dépannage

### Rate limiting persistant
Si le problème persiste :
1. Vérifiez que votre token Discord est valide
2. Attendez quelques heures avant de redéployer
3. Contactez le support Discord si nécessaire

### Problèmes de mémoire
- Utilisez une instance Render plus puissante
- Réduisez `MAX_CHUNK_CHARS` dans le code

### Google Drive non fonctionnel
- Vérifiez que le JSON des credentials est valide
- Assurez-vous que le service account a accès au Drive
- Le bot fonctionne sans Google Drive (index local uniquement)
