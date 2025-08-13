#!/bin/bash

# Script de build personnalisé pour Render
echo "🚀 Début du build personnalisé..."

# Mettre à jour pip
echo "📦 Mise à jour de pip..."
pip install --upgrade pip

# Installer les dépendances système si nécessaire
echo "🔧 Installation des dépendances système..."

# Installer les packages Python par étapes pour éviter les conflits
echo "📚 Installation des packages de base..."
pip install --no-cache-dir numpy==1.24.4

echo "📚 Installation de Discord.py..."
pip install --no-cache-dir discord.py==2.3.2

echo "📚 Installation d'OpenAI..."
pip install --no-cache-dir openai==1.51.2

echo "📚 Installation des utilitaires..."
pip install --no-cache-dir python-dotenv==1.0.0 requests==2.31.0

echo "📚 Installation de Google APIs..."
pip install --no-cache-dir google-auth==2.35.0
pip install --no-cache-dir google-api-python-client==2.149.0

echo "📚 Installation de FAISS (peut prendre du temps)..."
pip install --no-cache-dir faiss-cpu==1.8.0

echo "✅ Build terminé avec succès!"
