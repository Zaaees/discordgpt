# Bot Discord de Lore RP

Un bot Discord intelligent qui indexe et recherche dans le lore de votre serveur de jeu de rôle.

## Fonctionnalités

- **Indexation automatique** : Analyse l'historique des salons RP et INFO
- **Recherche intelligente** : Utilise l'IA pour répondre aux questions sur le lore
- **Sauvegarde cloud** : Synchronisation optionnelle avec Google Drive
- **Déploiement facile** : Compatible avec Render et autres plateformes

## Configuration

### Variables d'environnement requises

Copiez `.env.example` vers `.env` et remplissez les valeurs :

```bash
cp .env.example .env
```

#### Discord
- `DISCORD_TOKEN` : Token de votre bot Discord
- `DISCORD_GUILD_ID` : ID de votre serveur Discord

#### OpenAI
- `OPENAI_API_KEY` : Clé API OpenAI
- `OPENAI_MODEL` : Modèle GPT à utiliser (défaut: gpt-4)
- `OPENAI_EMBED_MODEL` : Modèle d'embedding (défaut: text-embedding-ada-002)

#### Google Drive (optionnel)
Pour la sauvegarde cloud de l'index :
- `GOOGLE_CREDENTIALS_JSON` : JSON des credentials de service account
- `DRIVE_FILE_ID` : ID du fichier d'index sur Drive
- `DRIVE_FOLDER_ID` : ID du dossier sur Drive

## Déploiement sur Render

1. **Créer un nouveau Web Service** sur Render
2. **Connecter votre repository** GitHub
3. **Configurer les variables d'environnement** :
   - Aller dans l'onglet "Environment"
   - Ajouter toutes les variables nécessaires
   - Pour `GOOGLE_CREDENTIALS_JSON`, coller directement le JSON complet

4. **Configuration du service** :
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `python main.py`
   - Instance Type: Starter (gratuit)

### Gestion des credentials Google Drive sur Render

**Étape 1** : Encoder vos credentials
```bash
python encode_credentials.py encode votre-fichier-credentials.json
```

**Étape 2** : Choisir une option sur Render

**Option A - Base64 (recommandé)** :
- Variable : `GOOGLE_CREDENTIALS_B64`
- Valeur : La chaîne base64 générée par le script

**Option B - JSON direct** :
- Variable : `GOOGLE_CREDENTIALS_JSON`
- Valeur : Le JSON sur une seule ligne avec guillemets échappés

⚠️ **Important** : Le JSON doit être sur une seule ligne avec les guillemets échappés (`\"`) pour les variables d'environnement.

## Utilisation

### Commandes Discord

- `/setup` : Indexe le lore du serveur (admin uniquement)
- `/lore <question>` : Pose une question sur le lore

### Structure des salons

Le bot traite automatiquement :
- **Salons RP** : Contenant `[RP]` dans le nom ou la catégorie
- **Salons INFO** : Contenant `[INFO]` dans le nom ou la catégorie
- **Ignore** : Salons avec `[HRP]` (hors roleplay)

## Développement local

1. Cloner le repository
2. Installer les dépendances : `pip install -r requirements.txt`
3. Configurer `.env`
4. Lancer : `python main.py`

## Dépannage

### Erreur 429 (Rate Limited)
Le bot implémente un système de retry automatique avec backoff exponentiel.

### Credentials Google Drive
- Vérifiez que le JSON est valide
- Assurez-vous que le service account a accès au Drive
- Utilisez `GOOGLE_CREDENTIALS_JSON` sur Render plutôt que le chemin de fichier

### Problèmes de mémoire
- Utilisez une instance Render plus puissante si nécessaire
- L'index FAISS peut être volumineux pour de gros serveurs
