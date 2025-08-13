# 🔧 Dépannage des problèmes de build sur Render

## 🚨 Problème : Build bloqué sur Render

### Causes communes

1. **FAISS-CPU** prend beaucoup de temps à compiler
2. **Versions de packages** incompatibles
3. **Timeout** de build (15 minutes max sur le plan gratuit)
4. **Mémoire insuffisante** pendant l'installation

## 🛠️ Solutions

### Solution 1 : Build Command optimisé

Dans Render, utilisez cette Build Command :

```bash
pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt
```

### Solution 2 : Requirements minimal (si FAISS pose problème)

Remplacez temporairement `requirements.txt` par `requirements-minimal.txt` :

```bash
# Dans Render Build Command
pip install --upgrade pip && pip install --no-cache-dir -r requirements-minimal.txt
```

### Solution 3 : Installation par étapes

Build Command avancée :

```bash
pip install --upgrade pip && 
pip install --no-cache-dir numpy==1.24.4 && 
pip install --no-cache-dir discord.py==2.3.2 openai==1.51.2 python-dotenv==1.0.0 && 
pip install --no-cache-dir google-api-python-client==2.149.0 google-auth==2.35.0 && 
pip install --no-cache-dir faiss-cpu==1.8.0
```

### Solution 4 : Sans FAISS (déploiement rapide)

Si FAISS continue de poser problème, le bot peut fonctionner sans :

1. Utilisez `requirements-minimal.txt`
2. Le bot affichera un message d'erreur pour `/lore` mais `/setup` fonctionnera
3. Vous pourrez ajouter FAISS plus tard

## 📊 Monitoring du build

### Logs à surveiller

```
✅ Bon signe :
- "Collecting discord.py==2.3.2"
- "Successfully installed discord.py-2.3.2"
- "Building wheels for faiss-cpu"

❌ Problème :
- "ERROR: Failed building wheel for faiss-cpu"
- "Killed" (manque de mémoire)
- Timeout après 15 minutes
```

### Temps d'installation typiques

- Discord.py : ~30 secondes
- OpenAI : ~10 secondes  
- Google APIs : ~45 secondes
- **FAISS-CPU : 3-8 minutes** ⚠️
- Numpy : ~1 minute

## 🚀 Déploiement d'urgence

Si vous devez déployer rapidement :

1. **Commentez FAISS** dans requirements.txt :
   ```
   # faiss-cpu==1.8.0  # Temporairement désactivé
   ```

2. **Déployez** sans recherche vectorielle

3. **Réactivez FAISS** plus tard quand vous avez le temps

## 🔄 Alternatives à FAISS

Si FAISS continue de poser problème, vous pouvez :

1. **Utiliser une recherche simple** par mots-clés
2. **Passer à un service externe** comme Pinecone
3. **Utiliser ChromaDB** (plus léger)

## 📞 Support Render

Si le problème persiste :

1. Vérifiez les [Status de Render](https://status.render.com/)
2. Contactez le support avec les logs de build
3. Essayez de redéployer (parfois ça marche au 2e essai)

## ⚡ Build Command recommandée finale

```bash
pip install --upgrade pip --no-cache-dir && pip install --no-cache-dir numpy==1.24.4 discord.py==2.3.2 openai==1.51.2 python-dotenv==1.0.0 google-api-python-client==2.149.0 google-auth==2.35.0 requests==2.31.0 && pip install --no-cache-dir faiss-cpu==1.8.0
```

Cette commande installe les packages critiques en premier, puis FAISS en dernier.
