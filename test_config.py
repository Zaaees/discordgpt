#!/usr/bin/env python3
"""
Script de test pour vérifier la configuration avant le déploiement
"""

import os
import json
import base64
from dotenv import load_dotenv

def test_discord_config():
    """Teste la configuration Discord"""
    print("=== Test Configuration Discord ===")
    
    token = os.getenv('DISCORD_TOKEN')
    guild_id = os.getenv('DISCORD_GUILD_ID')
    
    if not token:
        print("❌ DISCORD_TOKEN manquant")
        return False
    else:
        print("✅ DISCORD_TOKEN présent")
    
    if not guild_id:
        print("⚠️  DISCORD_GUILD_ID manquant (optionnel)")
    else:
        try:
            int(guild_id)
            print("✅ DISCORD_GUILD_ID valide")
        except ValueError:
            print("❌ DISCORD_GUILD_ID invalide (doit être un nombre)")
            return False
    
    return True

def test_openai_config():
    """Teste la configuration OpenAI"""
    print("\n=== Test Configuration OpenAI ===")
    
    api_key = os.getenv('OPENAI_API_KEY')
    model = os.getenv('OPENAI_MODEL', 'gpt-4')
    embed_model = os.getenv('OPENAI_EMBED_MODEL', 'text-embedding-ada-002')
    
    if not api_key:
        print("❌ OPENAI_API_KEY manquant")
        return False
    else:
        print("✅ OPENAI_API_KEY présent")
    
    print(f"✅ Modèle GPT: {model}")
    print(f"✅ Modèle embedding: {embed_model}")
    
    return True

def test_google_drive_config():
    """Teste la configuration Google Drive"""
    print("\n=== Test Configuration Google Drive ===")
    
    creds_json = os.getenv('GOOGLE_CREDENTIALS_JSON')
    creds_b64 = os.getenv('GOOGLE_CREDENTIALS_B64')
    creds_path = os.getenv('GOOGLE_CREDENTIALS_PATH')
    
    has_valid_creds = False
    
    if creds_json:
        try:
            # Tenter de décoder si c'est du base64
            try:
                decoded = base64.b64decode(creds_json, validate=True).decode('utf-8')
                creds_json = decoded
            except:
                pass
            
            json.loads(creds_json)
            print("✅ GOOGLE_CREDENTIALS_JSON valide")
            has_valid_creds = True
        except json.JSONDecodeError:
            print("❌ GOOGLE_CREDENTIALS_JSON invalide (JSON malformé)")
    
    if creds_b64:
        try:
            decoded = base64.b64decode(creds_b64).decode('utf-8')
            json.loads(decoded)
            print("✅ GOOGLE_CREDENTIALS_B64 valide")
            has_valid_creds = True
        except Exception:
            print("❌ GOOGLE_CREDENTIALS_B64 invalide")
    
    if creds_path:
        if os.path.exists(creds_path):
            try:
                with open(creds_path, 'r') as f:
                    json.load(f)
                print(f"✅ GOOGLE_CREDENTIALS_PATH valide: {creds_path}")
                has_valid_creds = True
            except json.JSONDecodeError:
                print(f"❌ Fichier de credentials invalide: {creds_path}")
        else:
            print(f"❌ Fichier de credentials non trouvé: {creds_path}")
    
    if not has_valid_creds:
        print("⚠️  Aucun credential Google Drive valide (fonctionnalité désactivée)")
    
    # Tester les IDs Drive
    file_id = os.getenv('DRIVE_FILE_ID')
    folder_id = os.getenv('DRIVE_FOLDER_ID')
    
    if file_id:
        print(f"✅ DRIVE_FILE_ID: {file_id}")
    else:
        print("⚠️  DRIVE_FILE_ID manquant (optionnel)")
    
    if folder_id:
        print(f"✅ DRIVE_FOLDER_ID: {folder_id}")
    else:
        print("⚠️  DRIVE_FOLDER_ID manquant (optionnel)")
    
    return True

def main():
    """Fonction principale de test"""
    print("Test de configuration pour le bot Discord de Lore RP")
    print("=" * 60)
    
    # Charger les variables d'environnement
    load_dotenv()
    
    # Tests
    discord_ok = test_discord_config()
    openai_ok = test_openai_config()
    drive_ok = test_google_drive_config()
    
    print("\n=== Résumé ===")
    if discord_ok and openai_ok:
        print("✅ Configuration minimale OK - Le bot peut démarrer")
    else:
        print("❌ Configuration incomplète - Le bot ne peut pas démarrer")
        return 1
    
    if drive_ok:
        print("✅ Google Drive configuré")
    else:
        print("⚠️  Google Drive non configuré (fonctionnalité limitée)")
    
    return 0

if __name__ == "__main__":
    exit(main())
