#!/usr/bin/env python3
"""
Script pour encoder les credentials Google Drive en base64
Utile pour le déploiement sur des plateformes cloud
"""

import base64
import json
import os
import sys

def encode_credentials_file(file_path):
    """Encode un fichier de credentials JSON en base64"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            credentials_json = f.read()

        # Vérifier que c'est un JSON valide
        credentials_dict = json.loads(credentials_json)

        # Encoder en base64
        encoded = base64.b64encode(credentials_json.encode('utf-8')).decode('utf-8')

        print("=== Option 1: Base64 (recommandé) ===")
        print("GOOGLE_CREDENTIALS_B64=" + encoded)
        print()

        print("=== Option 2: JSON direct (une seule ligne) ===")
        # Créer une version compacte du JSON sur une seule ligne
        compact_json = json.dumps(credentials_dict, separators=(',', ':'))
        # Échapper les guillemets pour les variables d'environnement
        escaped_json = compact_json.replace('"', '\\"')
        print(f'GOOGLE_CREDENTIALS_JSON="{escaped_json}"')
        print()

        print("=== Instructions ===")
        print("1. Copiez l'une des deux lignes ci-dessus")
        print("2. Ajoutez-la à vos variables d'environnement sur Render")
        print("3. L'option Base64 est généralement plus simple à utiliser")

        return encoded
        
    except FileNotFoundError:
        print(f"Erreur : Fichier '{file_path}' non trouvé")
        return None
    except json.JSONDecodeError:
        print(f"Erreur : Le fichier '{file_path}' ne contient pas un JSON valide")
        return None
    except Exception as e:
        print(f"Erreur : {e}")
        return None

def decode_credentials(encoded_string):
    """Décode une chaîne base64 pour vérifier les credentials"""
    try:
        decoded = base64.b64decode(encoded_string).decode('utf-8')
        credentials = json.loads(decoded)
        
        print("Credentials décodés avec succès :")
        print("=" * 50)
        print(f"Type: {credentials.get('type', 'N/A')}")
        print(f"Project ID: {credentials.get('project_id', 'N/A')}")
        print(f"Client Email: {credentials.get('client_email', 'N/A')}")
        print("=" * 50)
        
        return credentials
        
    except Exception as e:
        print(f"Erreur lors du décodage : {e}")
        return None

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage:")
        print(f"  {sys.argv[0]} encode <fichier_credentials.json>")
        print(f"  {sys.argv[0]} decode <string_base64>")
        print(f"  {sys.argv[0]} encode citadelle-serveur-23730de87edb.json")
        sys.exit(1)

    command = sys.argv[1].lower()

    if command == "encode":
        if len(sys.argv) < 3:
            # Essayer avec le fichier par défaut
            default_file = "citadelle-serveur-23730de87edb.json"
            if os.path.exists(default_file):
                print(f"Utilisation du fichier par défaut : {default_file}")
                encode_credentials_file(default_file)
            else:
                print("Erreur : Veuillez spécifier le fichier de credentials")
                print(f"Exemple : {sys.argv[0]} encode {default_file}")
                sys.exit(1)
        else:
            file_path = sys.argv[2]
            encode_credentials_file(file_path)

    elif command == "decode":
        if len(sys.argv) < 3:
            print("Erreur : Veuillez spécifier la chaîne base64")
            sys.exit(1)
        encoded_string = sys.argv[2]
        decode_credentials(encoded_string)

    else:
        print(f"Commande inconnue : {command}")
        print("Utilisez 'encode' ou 'decode'")
        sys.exit(1)
