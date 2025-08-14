# Bot Discord de Lore RP - main.py

import os
import io
import json
import asyncio
import functools
import logging
from datetime import datetime, timedelta

import discord
from discord import app_commands

from openai import OpenAI
import numpy as np
import threading  # mini serveur HTTP pour Render Web
import base64  # pour décoder des credentials en base64 si fournis

# Google Drive API
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload

from dotenv import load_dotenv

# Charger les variables d'environnement (.env)
load_dotenv()
print("Environment loaded successfully")
import sys
sys.stdout.flush()

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    force=True
)
logger = logging.getLogger(__name__)
logger.info("Logger initialized")

# Vérifier la disponibilité de PyNaCl pour le support vocal
try:
    import nacl
except ImportError:
    logger.warning("PyNaCl is not installed, voice will NOT be supported")
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
OPENAI_MODEL = os.getenv('OPENAI_MODEL', 'gpt-4')
OPENAI_EMBED_MODEL = os.getenv('OPENAI_EMBED_MODEL', 'text-embedding-ada-002')
GOOGLE_CREDENTIALS_PATH = os.getenv('GOOGLE_CREDENTIALS_PATH')
DRIVE_FILE_ID = os.getenv('DRIVE_FILE_ID')
DRIVE_FOLDER_ID = os.getenv('DRIVE_FOLDER_ID')
DISCORD_GUILD_ID = os.getenv('DISCORD_GUILD_ID')

# Configurations diverses
SCENE_BREAK_HOURS = 6  # Seuil de séparation des scènes en heures (changement temporel notable)
MAX_CHUNK_CHARS = 4000  # Taille approx. des segments de texte pour l'indexation (en caractères)

# Initialiser le client OpenAI
openai_client = OpenAI(api_key=OPENAI_API_KEY)

# Variables pour Google Drive (initialisation lazy)
drive_service = None
_drive_credentials = None
_drive_init_attempted = False

def get_drive_service():
    """Initialise et retourne le service Google Drive de manière lazy"""
    global drive_service, _drive_credentials, _drive_init_attempted

    if _drive_init_attempted:
        return drive_service

    _drive_init_attempted = True
    logger.info("Initialisation du service Google Drive...")

    try:
        creds = None
        GOOGLE_CREDENTIALS_JSON = os.getenv('GOOGLE_CREDENTIALS_JSON')
        GOOGLE_CREDENTIALS_B64 = os.getenv('GOOGLE_CREDENTIALS_B64')
        GOOGLE_CREDENTIALS_PATH = os.getenv('GOOGLE_CREDENTIALS_PATH')

        if GOOGLE_CREDENTIALS_JSON and GOOGLE_CREDENTIALS_JSON.strip():
            logger.info("Tentative d'utilisation de GOOGLE_CREDENTIALS_JSON...")
            try:
                data_str = GOOGLE_CREDENTIALS_JSON.strip()
                # Si la valeur est en base64, tenter le décodage. Sinon, garder tel quel.
                try:
                    decoded = base64.b64decode(data_str, validate=True).decode('utf-8')
                    data_str = decoded
                except Exception:
                    pass

                # Corriger les séquences d'échappement dans le JSON (notamment \\n -> \n)
                data_str = data_str.replace('\\n', '\n').replace('\\t', '\t').replace('\\r', '\r')

                info = json.loads(data_str)
                creds = service_account.Credentials.from_service_account_info(
                    info,
                    scopes=["https://www.googleapis.com/auth/drive"]
                )
            except Exception as e:
                logger.error(f"Erreur lors de l'utilisation de GOOGLE_CREDENTIALS_JSON: {e}")
                logger.error(f"Contenu reçu (premiers 200 chars): {GOOGLE_CREDENTIALS_JSON[:200]}...")
        elif GOOGLE_CREDENTIALS_B64:
            logger.info("Tentative d'utilisation de GOOGLE_CREDENTIALS_B64...")
            try:
                decoded = base64.b64decode(GOOGLE_CREDENTIALS_B64).decode('utf-8')
                info = json.loads(decoded)
                creds = service_account.Credentials.from_service_account_info(
                    info,
                    scopes=["https://www.googleapis.com/auth/drive"]
                )
            except Exception as e:
                logger.error(f"Erreur lors du décodage de GOOGLE_CREDENTIALS_B64: {e}")
        elif GOOGLE_CREDENTIALS_PATH:
            logger.info("Tentative d'utilisation de GOOGLE_CREDENTIALS_PATH...")
            creds = service_account.Credentials.from_service_account_file(
                GOOGLE_CREDENTIALS_PATH,
                scopes=["https://www.googleapis.com/auth/drive"]
            )

        if creds:
            logger.info("Credentials trouvés, construction du service Drive...")
            drive_service = build('drive', 'v3', credentials=creds)
            logger.info("Service Google Drive configuré avec succès")
        else:
            logger.warning("Aucun credential Google Drive valide trouvé - fonctionnalité désactivée")
    except Exception as e:
        logger.error(f"Impossible d'initialiser le service Google Drive - {e}")

    return drive_service
# Petit serveur HTTP de healthcheck pour Render Web (port $PORT)
def start_healthcheck_server():
    try:
        port_str = os.getenv("PORT")
        if not port_str:
            return
        port = int(port_str)
        from http.server import BaseHTTPRequestHandler, HTTPServer
        class H(BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b"OK")
            def log_message(self, *args):
                # Silence le logging HTTP par défaut
                pass
        srv = HTTPServer(("0.0.0.0", port), H)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        logger.info(f"Healthcheck HTTP actif sur 0.0.0.0:{port}")
    except Exception as e:
        logger.error(f"Impossible de démarrer le healthcheck HTTP: {e}")

# Structures de données globales
scenes_data = []        # Liste des scènes (RP) et entrées de lore info
faiss_index = None      # Index vectoriel FAISS
index_id_to_scene = []  # Mapping des indices de vecteur vers (scene_id, chunk_text)

# Nettoyer les noms de salons/catégories en supprimant les balises [RP], [HRP], [INFO]
def clean_name(name: str) -> str:
    if name is None:
        return ""
    for tag in ["[RP]", "[HRP]", "[INFO]"]:
        name = name.replace(tag, "")
    return name.strip()

# Fonction utilitaire pour obtenir l'embedding d'un texte (via l'API OpenAI)
def get_embedding(text: str):
    # Appel d'OpenAI API pour générer l'embedding d'un texte
    result = openai_client.embeddings.create(model=OPENAI_EMBED_MODEL, input=text)
    embedding = result.data[0].embedding
    return embedding

# Fonction utilitaire pour poser une question à GPT (OpenAI ChatCompletion)
def ask_gpt(messages, model=OPENAI_MODEL):
    # Appel de l'API OpenAI ChatCompletion avec les messages fournis
    response = openai_client.chat.completions.create(model=model, messages=messages)
    answer = response.choices[0].message.content
    return answer

# Charger l'index vectoriel et les données de scènes depuis Google Drive ou local
def load_index_data():
    global scenes_data, faiss_index, index_id_to_scene
    logger.info("Début du chargement de l'index...")

    # Si un fichier local existe, on l'utilise en priorité
    if os.path.exists("lore_index.zip"):
        logger.info("Fichier lore_index.zip trouvé localement.")
        zip_path = "lore_index.zip"
    else:
        logger.info("Fichier lore_index.zip non trouvé localement.")
        zip_path = None
        # Tenter de télécharger le fichier d'index depuis Google Drive si configuré
        drive_service = get_drive_service()
        if drive_service:
            logger.info("Tentative de téléchargement depuis Google Drive...")
            try:
                file_id = DRIVE_FILE_ID
                # Si FILE_ID n'est pas fourni, chercher un fichier par nom dans le dossier
                if not file_id:
                    query = "name='lore_index.zip'"
                    if DRIVE_FOLDER_ID:
                        query += f" and '{DRIVE_FOLDER_ID}' in parents"
                    results = drive_service.files().list(q=query, spaces='drive', fields="files(id, name)", pageSize=1).execute()
                    files = results.get('files', [])
                    if files:
                        file_id = files[0]['id']
                if file_id:
                    try:
                        request = drive_service.files().get_media(fileId=file_id)
                        fh = io.BytesIO()
                        downloader = MediaIoBaseDownload(fh, request)
                        done = False
                        while not done:
                            status, done = downloader.next_chunk()
                        fh.seek(0)
                        with open("lore_index.zip", "wb") as f:
                            f.write(fh.read())
                        zip_path = "lore_index.zip"
                        logger.info("Index téléchargé depuis Google Drive.")
                    except Exception as e:
                        logger.error(f"Échec du téléchargement de l'index depuis Google Drive: {e}")
                else:
                    logger.warning("Aucun ID de fichier trouvé pour l'index sur Google Drive")
            except Exception as e:
                logger.error(f"Erreur lors de l'accès à Google Drive: {e}")
        else:
            logger.info("Service Google Drive non configuré.")

    # Si on a un zip, l'extraire
    if zip_path:
        logger.info(f"Extraction du fichier {zip_path}...")
        import zipfile
        try:
            with zipfile.ZipFile(zip_path, 'r') as zipf:
                zipf.extractall(".")
            logger.info("Extraction réussie.")

            # Charger les données JSON des scènes
            logger.info("Chargement de scenes.json...")
            with open("scenes.json", "r", encoding="utf-8") as f:
                scenes_data = json.load(f)
            logger.info(f"scenes.json chargé avec {len(scenes_data)} scènes.")

            # Charger l'index FAISS
            logger.info("Chargement de l'index FAISS...")
            try:
                faiss = __import__('faiss')  # import dynamique pour éviter erreur si module non chargé
                faiss_index = faiss.read_index("index.faiss")
                if faiss_index is None:
                    logger.warning("L'index FAISS chargé est None - fichier probablement corrompu.")
                    faiss_index = None
                    return
                logger.info(f"Index FAISS chargé avec {faiss_index.ntotal} vecteurs.")
            except ImportError as e:
                logger.warning(f"FAISS non disponible: {e}")
                faiss_index = None
                # Ne pas retourner ici, continuer sans FAISS
            except Exception as e:
                logger.error(f"Erreur lors du chargement de l'index FAISS: {e}")
                faiss_index = None
                # Ne pas retourner ici, continuer sans FAISS

            # Reconstruire la table de correspondance index->scene/chunk
            logger.info("Reconstruction de la table de correspondance...")
            index_id_to_scene = []
            for scene in scenes_data:
                # Pour chaque scène, ajouter soit ses chunks, soit la scène entière
                if scene.get("chunks"):
                    for chunk in scene["chunks"]:
                        index_id_to_scene.append((scene["id"], chunk))
                else:
                    index_id_to_scene.append((scene["id"], None))
            logger.info(f"Table de correspondance créée avec {len(index_id_to_scene)} entrées.")
            logger.info(f"{len(scenes_data)} scènes/entrées lore chargées depuis l'index existant.")

        except Exception as e:
            logger.error(f"Erreur lors du chargement de l'index local: {e}")
            import traceback
            traceback.print_exc()
            scenes_data = []
            index_id_to_scene = []
            faiss_index = None
    else:
        logger.info("Aucun fichier d'index disponible.")
        scenes_data = []
        index_id_to_scene = []
        faiss_index = None

# Sauvegarder l'index vectoriel et les données de scènes localement et sur Drive
def save_index_data():
    global scenes_data, faiss_index
    # Sauvegarder scenes_data en JSON
    with open("scenes.json", "w", encoding="utf-8") as f:
        json.dump(scenes_data, f, ensure_ascii=False, indent=2)
    # Sauvegarder l'index FAISS
    faiss = __import__('faiss')
    faiss.write_index(faiss_index, "index.faiss")
    # Créer un zip de scenes.json et index.faiss
    import zipfile
    with zipfile.ZipFile("lore_index.zip", "w", zipfile.ZIP_DEFLATED) as zipf:
        zipf.write("scenes.json")
        zipf.write("index.faiss")
    # Uploader sur Google Drive si configuré
    drive_service = get_drive_service()
    if drive_service:
        try:
            file_id = DRIVE_FILE_ID
            # Vérifier si le fichier existe déjà (par ID ou par nom)
            if file_id:
                # Mise à jour du fichier existant par ID
                media = MediaFileUpload("lore_index.zip", mimetype="application/zip", resumable=True)
                drive_service.files().update(fileId=file_id, media_body=media).execute()
            else:
                # Rechercher par nom dans le dossier (au cas où)
                query = "name='lore_index.zip'"
                if DRIVE_FOLDER_ID:
                    query += f" and '{DRIVE_FOLDER_ID}' in parents"
                results = drive_service.files().list(q=query, fields="files(id)", pageSize=1).execute()
                files = results.get('files', [])
                if files:
                    file_id = files[0]['id']
                if file_id:
                    media = MediaFileUpload("lore_index.zip", mimetype="application/zip", resumable=True)
                    drive_service.files().update(fileId=file_id, media_body=media).execute()
                else:
                    # Créer un nouveau fichier sur Drive
                    file_metadata = {'name': 'lore_index.zip'}
                    if DRIVE_FOLDER_ID:
                        file_metadata['parents'] = [DRIVE_FOLDER_ID]
                    media = MediaFileUpload("lore_index.zip", mimetype="application/zip", resumable=True)
                    drive_service.files().create(body=file_metadata, media_body=media).execute()
            logger.info("Index sauvegardé sur Google Drive.")
        except Exception as e:
            logger.error(f"Échec de la sauvegarde sur Google Drive: {e}")

# L'index sera chargé au démarrage du bot dans la fonction main()

# Configurer les intents (lecture du contenu des messages requise)
intents = discord.Intents.default()
intents.message_content = True  # pour accéder au contenu des messages
intents.guilds = True

# Initialiser le bot Discord avec des paramètres de connexion optimisés
bot = discord.Client(
    intents=intents,
    heartbeat_timeout=90.0,  # Timeout plus long pour les connexions instables
    guild_ready_timeout=15.0,  # Timeout pour la synchronisation des guildes
    max_messages=500,  # Limiter le cache des messages
    chunk_guilds_at_startup=False,  # Ne pas charger tous les membres au démarrage
    member_cache_flags=discord.MemberCacheFlags.none(),  # Désactiver le cache des membres
    connector=None  # Utiliser le connector par défaut d'aiohttp
)
tree = app_commands.CommandTree(bot)

# Commande slash /setup pour indexer le lore du serveur
@tree.command(name="setup", description="Récupère l'historique RP et construit l'index du lore", guild=discord.Object(id=int(DISCORD_GUILD_ID)) if DISCORD_GUILD_ID else None)
async def setup_command(interaction: discord.Interaction):
    global scenes_data, faiss_index, index_id_to_scene
    # Restreindre l'utilisation de /setup aux administrateurs du serveur
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("Désolé, vous n'avez pas la permission d'utiliser cette commande.", ephemeral=True)
        return
    # Accuser réception de la commande (peut prendre du temps)
    await interaction.response.defer(thinking=True, ephemeral=True)
    try:
        guild = interaction.guild
        if guild is None:
            await interaction.followup.send("Erreur : serveur introuvable (guild est None).", ephemeral=True)
            return

        # Dictionnaire des dernières dates traitées par channel (pour mise à jour incrémentale)
        last_processed = {}
        if scenes_data:
            for scene in scenes_data:
                if scene["messages"]:
                    try:
                        last_msg_time = scene["messages"][-1]["time"]
                    except:
                        last_msg_time = None
                    chan_id = scene.get("channel_id")
                    if last_msg_time and chan_id:
                        if chan_id not in last_processed or last_msg_time > last_processed[chan_id]:
                            last_processed[chan_id] = last_msg_time

        new_scenes = []  # liste des nouvelles scènes/entrées extraites
        total_channels = len([c for c in guild.text_channels if ("[RP]" in c.name or (c.category and "[RP]" in c.category.name)) or ("[INFO]" in c.name or (c.category and "[INFO]" in c.category.name)) and not "[HRP]" in c.name])
        processed_channels = 0

        # Parcourir tous les salons texte du serveur pour l'extraction
        for channel in guild.text_channels:
            chan_name = channel.name
            cat_name = channel.category.name if channel.category else ""
            # Identifier les salons RP et INFO à traiter
            is_rp = "[RP]" in chan_name or (channel.category and "[RP]" in cat_name)
            is_info = "[INFO]" in chan_name or (channel.category and "[INFO]" in cat_name)
            is_hrp = "[HRP]" in chan_name  # salons hors-roleplay à ignorer
            if not (is_rp or is_info) or is_hrp:
                continue  # ignorer les salons non pertinents

            # Mise à jour de progression
            processed_channels += 1
            if processed_channels % 5 == 0 or processed_channels == total_channels:
                try:
                    await interaction.edit_original_response(content=f"Traitement des salons... ({processed_channels}/{total_channels})")
                except:
                    pass  # Ignorer les erreurs de mise à jour
            # Récupérer l'historique du salon Discord
            after_date = None
            chan_key = str(channel.id)
            if chan_key in last_processed:
                try:
                    after_date = datetime.fromisoformat(last_processed[chan_key])
                except:
                    after_date = None
            messages = []
            try:
                message_count = 0
                if after_date:
                    # Si on a une date de dernière lecture, récupérer les messages après cette date
                    async for msg in channel.history(limit=None, oldest_first=True, after=after_date):
                        messages.append(msg)
                        message_count += 1
                        # Mise à jour toutes les 1000 messages pour maintenir la connexion
                        if message_count % 1000 == 0:
                            try:
                                await interaction.edit_original_response(content=f"Lecture de #{chan_name}: {message_count} messages...")
                            except:
                                pass
                else:
                    # Récupérer TOUS les messages du salon pour un recensement complet
                    async for msg in channel.history(limit=None, oldest_first=True):
                        messages.append(msg)
                        message_count += 1
                        # Mise à jour toutes les 1000 messages pour maintenir la connexion
                        if message_count % 1000 == 0:
                            try:
                                await interaction.edit_original_response(content=f"Lecture de #{chan_name}: {message_count} messages...")
                            except:
                                pass
            except Exception as e:
                print(f"Impossible de lire l'historique de {chan_name}: {e}")
                continue
            if not messages:
                continue  # pas de nouveaux messages dans ce salon
            if is_rp:
                # Segmentation des messages RP en scènes
                scene_msgs = []
                last_msg_time = None
                for msg in messages:
                    # Ignorer les messages système ou du bot sans contenu pertinent
                    if msg.author.bot and not msg.content:
                        continue
                    # Préparer le texte du message nettoyé
                    content = msg.clean_content
                    if msg.attachments:
                        for att in msg.attachments:
                            content += f" [Attachment: {att.url}]"
                    # Vérifier la condition de rupture de scène (écart de temps)
                    if scene_msgs:
                        delta = msg.created_at - last_msg_time if last_msg_time else timedelta()
                        if delta.total_seconds() > SCENE_BREAK_HOURS * 3600:
                            # ** Nouvelle scène si le délai dépasse le seuil configuré **
                            if scene_msgs:
                                scene = create_scene_object(scene_msgs, cat_name, chan_name, channel_id=channel.id, is_info=False)
                                new_scenes.append(scene)
                            scene_msgs = []
                    # Ajouter le message courant à la scène en cours
                    if scene_msgs == []:
                        # Marquer l'heure de début de la nouvelle scène (date du premier message)
                        scene_start_time = msg.created_at
                    scene_msgs.append({
                        "id": str(msg.id),
                        "author": {"name": msg.author.display_name, "id": str(msg.author.id)},
                        "time": msg.created_at.isoformat(),
                        "content": content
                    })
                    # Mettre à jour le dernier timestamp vu et les participants de la scène en cours
                    last_msg_time = msg.created_at
                # Fin de la boucle messages du salon RP - ajouter la dernière scène accumulée
                if scene_msgs:
                    scene = create_scene_object(scene_msgs, cat_name, chan_name, channel_id=channel.id, is_info=False)
                    new_scenes.append(scene)
            elif is_info:
                # Chaque message d'un salon [INFO] est considéré comme une entrée de lore séparée
                for msg in messages:
                    content = msg.clean_content
                    if msg.attachments:
                        for att in msg.attachments:
                            content += f" [Attachment: {att.url}]"
                    info_entry = {
                        "id": str(msg.id),
                        "channel_id": str(channel.id),
                        "title": None,
                        "type": "info",
                        "location": f"{clean_name(cat_name)} / {clean_name(chan_name)}" if cat_name else clean_name(chan_name),
                        "date": msg.created_at.isoformat(),
                        "participants": [],  # pas de participants multiples pour une info, auteur éventuel non listé
                        "summary": None,
                        "messages": [{
                            "id": str(msg.id),
                            "author": {"name": msg.author.display_name, "id": str(msg.author.id)},
                            "time": msg.created_at.isoformat(),
                            "content": content
                        }]
                    }
                    # Générer un titre pour l'entrée d'info (ex: premières mots ou titre présent dans le contenu)
                    info_entry["title"] = generate_info_title(content, chan_name)
                    new_scenes.append(info_entry)
        # Si aucune nouvelle scène ou entrée n'a été collectée
        if not new_scenes:
            await interaction.followup.send("Aucune nouvelle donnée à indexer.", ephemeral=True)
            return

        # Assigner des ID uniques aux nouvelles scènes AVANT l'indexation
        next_id = (max([s['id'] for s in scenes_data], default=0) + 1) if scenes_data else 1
        for scene in new_scenes:
            scene['id'] = next_id
            next_id += 1
        # Traiter chaque nouvelle scène/entrée
        total_scenes = len(new_scenes)
        processed_scenes = 0

        # Mise à jour de progression
        try:
            await interaction.edit_original_response(content=f"Génération des résumés et indexation... (0/{total_scenes})")
        except:
            pass

        for scene in new_scenes:
            processed_scenes += 1
            if scene["type"] == "rp":
                # Générer un résumé narratif de la scène via GPT
                transcript_text = "\n".join(f'{m["author"]["name"]}: {m["content"]}' for m in scene["messages"])
                prompt = [
                    {"role": "user", "content": f"Voici une scène de jeu de rôle.\n\n{transcript_text}\n\nFais un résumé narratif de cette scène en français en décrivant les événements importants et les personnages présents. Sois concis."}
                ]
                try:
                    summary = await asyncio.get_running_loop().run_in_executor(None, functools.partial(ask_gpt, prompt, OPENAI_MODEL))
                except Exception as e:
                    summary = None
                    print(f"Erreur lors de la génération du résumé: {e}")
                scene["summary"] = summary if summary else ""
                # Générer un titre à partir du résumé (ou à défaut, du nom du lieu)
                scene["title"] = generate_scene_title(scene, default=clean_name(scene["location"]))
            else:
                # Type "info" (pas de résumé auto généré)
                pass

            # Créer les chunks de texte à indexer pour cette scène/entrée
            chunks = []
            text_to_index_list = []
            if scene["type"] == "rp":
                # Découper la transcription complète de la scène en morceaux de taille raisonnable
                full_text = "\n".join(f'{m["author"]["name"]}: {m["content"]}' for m in scene["messages"])
                current_chunk = ""
                for line in full_text.splitlines():
                    if len(current_chunk) + len(line) + 1 <= MAX_CHUNK_CHARS:
                        current_chunk += line + "\n"
                    else:
                        if current_chunk:
                            chunks.append(current_chunk.strip())
                        current_chunk = line + "\n"
                if current_chunk:
                    chunks.append(current_chunk.strip())
                text_to_index_list = chunks
            else:
                # Entrée de lore info : utiliser le contenu du message (scinder si très long)
                info_text = scene["messages"][0]["content"]
                if len(info_text) > MAX_CHUNK_CHARS:
                    parts = info_text.split("\n")
                    current_chunk = ""
                    for part in parts:
                        if len(current_chunk) + len(part) + 1 <= MAX_CHUNK_CHARS:
                            current_chunk += part + "\n"
                        else:
                            if current_chunk:
                                chunks.append(current_chunk.strip())
                            current_chunk = part + "\n"
                    if current_chunk:
                        chunks.append(current_chunk.strip())
                    text_to_index_list = chunks
                else:
                    text_to_index_list = [info_text]

            # Enregistrer les chunks dans la scène (pour référence future lors du chargement)
            if len(text_to_index_list) > 1:
                scene["chunks"] = text_to_index_list
            else:
                scene["chunks"] = []

            # Mise à jour de progression
            if processed_scenes % 10 == 0 or processed_scenes == total_scenes:
                try:
                    await interaction.edit_original_response(content=f"Génération des résumés et indexation... ({processed_scenes}/{total_scenes})")
                except:
                    pass

            # Calculer l'embedding de chaque chunk et l'ajouter à l'index vectoriel
            chunk_count = 0
            for text in text_to_index_list:
                chunk_count += 1
                try:
                    emb = await asyncio.get_running_loop().run_in_executor(None, functools.partial(get_embedding, text))
                except Exception as e:
                    print(f"Erreur lors de l'obtention de l'embedding: {e}")
                    continue
                # Normaliser le vecteur d'embedding (pour l'IP index -> cos similarity)
                norm = sum(x*x for x in emb) ** 0.5
                vec = [x / norm for x in emb] if norm != 0 else emb
                vec = np.array(vec, dtype='float32')
                # Créer l'index FAISS dynamiquement si nécessaire (dimension = taille de l'embedding)
                faiss = __import__('faiss')
                if faiss_index is None:
                    faiss_index = faiss.IndexFlatIP(vec.shape[0])
                # Ajouter le vecteur normalisé à l'index FAISS
                faiss_index.add(vec.reshape(1, -1))
                # Enregistrer le mapping index->scene_id (+ chunk texte pour reconstruire l'extrait)
                index_id_to_scene.append((scene['id'], text))

                # Mise à jour de progression pour les embeddings (toutes les 5 embeddings)
                if chunk_count % 5 == 0:
                    try:
                        await interaction.edit_original_response(content=f"Génération des embeddings... Scène {processed_scenes}/{total_scenes}, chunk {chunk_count}/{len(text_to_index_list)}")
                    except:
                        pass
        # Ajouter les nouvelles scènes/entrées au corpus en mémoire
        for scene in new_scenes:
            scenes_data.append(scene)

        # Mise à jour finale
        try:
            await interaction.edit_original_response(content="Sauvegarde de l'index...")
        except:
            pass

        # Sauvegarder l’index et les données mises à jour
        save_index_data()
        # Répondre à l'interaction une fois terminé
        await interaction.followup.send(f"Index du lore mis à jour avec {len(new_scenes)} nouvelle(s) scène(s)/entrée(s).", ephemeral=True)
    except Exception as e:
        # En cas d'erreur générale lors du setup
        await interaction.followup.send(f"Une erreur s'est produite pendant la construction de l'index : {e}", ephemeral=True)

# Commande slash /lore pour poser une question sur le lore
@tree.command(name="lore", description="Pose une question sur le lore du serveur", guild=discord.Object(id=int(DISCORD_GUILD_ID)) if DISCORD_GUILD_ID else None)
@app_commands.describe(question="Votre question sur le lore")
async def lore_command(interaction: discord.Interaction, question: str):
    await interaction.response.defer(thinking=True)
    # Vérifier que l'index du lore est disponible
    if faiss_index is None or not scenes_data:
        await interaction.followup.send("Le lore n'est pas encore indexé. Veuillez exécuter /setup d'abord.", ephemeral=True)
        return
    try:
        # Obtenir l'embedding de la question utilisateur
        query_emb = await asyncio.get_running_loop().run_in_executor(None, functools.partial(get_embedding, question))
        norm = sum(x*x for x in query_emb) ** 0.5
        query_vec = [x / norm for x in query_emb] if norm != 0 else query_emb
        query_vec = np.array(query_vec, dtype='float32').reshape(1, -1)
        # Rechercher les vecteurs les plus similaires dans l'index
        k = 3  # nombre maximum d'extraits pertinents à récupérer
        faiss = __import__('faiss')
        distances, indices = faiss_index.search(query_vec, k)
        relevant_excerpts = []
        used_scene_ids = set()
        total_chars = 0
        for idx in indices[0]:
            if idx == -1:
                continue
            scene_id, chunk_text = index_id_to_scene[idx]
            scene = next((s for s in scenes_data if s["id"] == scene_id), None)
            if not scene or scene_id in used_scene_ids:
                continue
            used_scene_ids.add(scene_id)
            # Préparer l'extrait de texte correspondant
            if chunk_text:
                excerpt_text = chunk_text
            else:
                excerpt_text = "\n".join(f'{m["author"]["name"]}: {m["content"]}' for m in scene["messages"])
            # Étiqueter l'extrait pour contexte (scène ou info)
            label = f"Scène: {scene.get('title', '(sans titre)')}" if scene["type"] == "rp" else f"Info: {scene.get('title', '(sans titre)')}"
            excerpt = f"{label}\n{excerpt_text}"
            relevant_excerpts.append(excerpt)
            total_chars += len(excerpt)
            if total_chars > 8000:
                break  # limiter la taille totale du contexte envoyé à GPT
        if not relevant_excerpts:
            await interaction.followup.send("Aucune information du lore trouvée pour répondre à la question.", ephemeral=True)
            return
        # Préparer le message de contexte pour GPT
        lore_context = "\n\n".join(relevant_excerpts)
        prompt = [
            {"role": "system", "content": "Tu es un assistant expert du lore de notre jeu de rôle. Réponds aux questions en utilisant uniquement les informations fournies dans le contexte. Ne fais aucune supposition en dehors du contenu donné. Si une information manque pour répondre, indique que tu ne sais pas."},
            {"role": "user", "content": f"Contexte du lore :\n{lore_context}\n\nQuestion : {question}\n\nRéponds en utilisant uniquement le contexte ci-dessus."}
        ]
        # Obtenir la réponse de GPT
        answer = await asyncio.get_running_loop().run_in_executor(None, functools.partial(ask_gpt, prompt, OPENAI_MODEL))
        # Envoyer la réponse dans le canal Discord
        await interaction.followup.send(answer)
    except Exception as e:
        await interaction.followup.send(f"Désolé, une erreur est survenue pendant la recherche de la réponse : {e}", ephemeral=True)

# Fonction utilitaire pour créer un objet de scène RP à partir d'une liste de messages
def create_scene_object(messages, category_name, channel_name, channel_id=None, is_info=False):
    # Construire la liste des participants (auteurs uniques)
    participants = []
    seen_ids = set()
    for m in messages:
        uid = m["author"]["id"]
        if uid not in seen_ids:
            seen_ids.add(uid)
            participants.append({"name": m["author"]["name"], "id": uid})
    location = f"{clean_name(category_name)} / {clean_name(channel_name)}" if category_name else clean_name(channel_name)
    scene_obj = {
        "id": None,
        "channel_id": str(channel_id) if channel_id else None,
        "title": None,
        "type": "rp" if not is_info else "info",
        "location": location,
        "date": messages[0]["time"] if messages else None,
        "participants": participants,
        "summary": None,
        "messages": messages
    }
    return scene_obj

# Générer un titre pour une scène RP à partir de son résumé ou de son lieu par défaut
def generate_scene_title(scene, default="Scène RP"):
    title = ""
    if scene.get("summary"):
        summary = scene["summary"].strip()
        # Prendre la première phrase du résumé si elle est courte
        dot_index = summary.find('.')
        if 0 < dot_index < 80:
            title = summary[:dot_index+1]
        else:
            # Sinon, prendre quelques mots du résumé
            words = summary.split()
            if len(words) > 0:
                short_title = " ".join(words[:5])
                title = (short_title + "...") if len(words) > 5 else short_title
    if not title:
        title = default or scene.get("location", "Scène")
    return title

# Générer un titre pour une entrée d'info lore à partir de son contenu ou du nom du channel
def generate_info_title(content, channel_name):
    content = content.strip()
    title = ""
    # Chercher un titre implicite dans le contenu (avant un deux-points ou un saut de ligne)
    if ':' in content:
        idx = content.find(':')
        if idx < 60:
            title = content[:idx].strip()
    if not title:
        # Si pas de deux-points, prendre quelques premiers mots
        words = content.split()
        if len(words) > 0:
            title = " ".join(words[:5])
            if len(words) > 5:
                title += "..."
    if not title:
        # En dernier ressort, utiliser le nom du salon sans tag
        title = clean_name(channel_name)
    return title

@bot.event
async def on_ready():
    # Synchroniser les commandes slash (guilde spécifique si ID fourni, sinon global)
    try:
        if DISCORD_GUILD_ID:
            guild_obj = discord.Object(id=int(DISCORD_GUILD_ID))
            await tree.sync(guild=guild_obj)
            logger.info(f"Commandes synchronisées pour la guilde {DISCORD_GUILD_ID}")
        else:
            await tree.sync()
            logger.info("Commandes synchronisées globalement")
    except Exception as e:
        logger.error(f"Erreur de synchronisation des commandes: {e}")
    logger.info(f"{bot.user} est connecté et prêt.")

@bot.event
async def on_disconnect():
    logger.warning("Bot déconnecté de Discord")

@bot.event
async def on_resumed():
    logger.info("Connexion Discord reprise")

@bot.event
async def on_connect():
    logger.info("Connexion établie avec Discord")

# Fonction pour démarrer le bot avec retry et gestion d'erreurs
async def start_bot_with_retry():
    """Démarre le bot avec logique de retry et gestion des erreurs de connexion"""
    max_retries = 5
    base_delay = 60  # délai de base en secondes (augmenté pour éviter le rate limiting)

    for attempt in range(1, max_retries + 1):
        try:
            logger.info("Démarrage du bot Discord de Lore RP")
            logger.info(f"Tentative de connexion {attempt}/{max_retries}")

            # Fermer toute session existante avant de redémarrer
            if not bot.is_closed():
                await bot.close()
                await asyncio.sleep(5)  # Attendre que la fermeture soit complète

            # Démarrer le bot
            await bot.start(DISCORD_TOKEN)

        except discord.HTTPException as e:
            if e.status == 429:  # Rate limited
                delay = base_delay * (2 ** (attempt - 1))  # Exponential backoff
                logger.warning(f"Rate limité. Attente de {delay} secondes avant la prochaine tentative...")
                await asyncio.sleep(delay)
                continue
            else:
                logger.error(f"Erreur HTTP Discord: {e}")
                if attempt == max_retries:
                    logger.error("Nombre maximum de tentatives atteint. Arrêt du bot.")
                    raise
                await asyncio.sleep(base_delay)
                continue

        except discord.ConnectionClosed as e:
            logger.warning(f"Connexion fermée: {e}")
            if attempt == max_retries:
                logger.error("Nombre maximum de tentatives atteint. Arrêt du bot.")
                raise
            delay = base_delay * (2 ** (attempt - 1))
            logger.info(f"Reconnexion dans {delay} secondes...")
            await asyncio.sleep(delay)
            continue

        except discord.LoginFailure as e:
            logger.error(f"Échec de connexion - Token invalide: {e}")
            raise  # Ne pas retry sur les erreurs de token

        except Exception as e:
            logger.error(f"Erreur inattendue: {e}")
            if attempt == max_retries:
                logger.error("Nombre maximum de tentatives atteint. Arrêt du bot.")
                logger.error(f"Erreur fatale: {e}")
                raise
            delay = base_delay * (2 ** (attempt - 1))
            logger.info(f"Nouvelle tentative dans {delay} secondes...")
            await asyncio.sleep(delay)
            continue

        # Si on arrive ici, la connexion a réussi
        break

    logger.info("Bot connecté avec succès!")

# Fonction principale pour gérer le bot avec gestion d'erreurs
async def main():
    """Fonction principale avec gestion des sessions et cleanup"""
    try:
        # Charger l'index existant au démarrage si possible
        logger.info("Chargement de l'index au démarrage...")
        load_index_data()

        # Démarrer le bot
        await start_bot_with_retry()
    except KeyboardInterrupt:
        logger.info("Arrêt du bot demandé par l'utilisateur")
    except Exception as e:
        logger.error(f"Erreur fatale lors du démarrage: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Cleanup des ressources
        if not bot.is_closed():
            logger.info("Fermeture du bot...")
            await bot.close()
        logger.info("Bot arrêté.")

# Démarrer le bot avec gestion d'erreurs
if __name__ == "__main__":
    start_healthcheck_server()
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Arrêt forcé du programme")
    except Exception as e:
        logger.error(f"Erreur critique: {e}")
        import traceback
        traceback.print_exc()