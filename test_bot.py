#!/usr/bin/env python3
"""
Simple test script to verify the bot can start and connect
"""

import os
import sys
import asyncio
import logging
from dotenv import load_dotenv
import discord

# Load environment
load_dotenv()
print("Environment loaded", flush=True)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    force=True
)
logger = logging.getLogger(__name__)
logger.info("Test bot starting...")

# Get token
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
DISCORD_GUILD_ID = os.getenv('DISCORD_GUILD_ID')

if not DISCORD_TOKEN:
    logger.error("DISCORD_TOKEN not found in environment")
    sys.exit(1)

# Setup bot
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True

bot = discord.Client(
    intents=intents,
    heartbeat_timeout=60.0,
    guild_ready_timeout=10.0,
    max_messages=1000,
    chunk_guilds_at_startup=False,
    member_cache_flags=discord.MemberCacheFlags.none()
)

@bot.event
async def on_ready():
    logger.info(f"{bot.user} is connected and ready!")
    logger.info(f"Connected to {len(bot.guilds)} guilds")
    
    # Test for 30 seconds then disconnect
    await asyncio.sleep(30)
    logger.info("Test completed, disconnecting...")
    await bot.close()

@bot.event
async def on_connect():
    logger.info("Connected to Discord")

@bot.event
async def on_disconnect():
    logger.info("Disconnected from Discord")

async def main():
    try:
        logger.info("Starting bot connection test...")
        await bot.start(DISCORD_TOKEN)
    except Exception as e:
        logger.error(f"Error: {e}")
        raise
    finally:
        if not bot.is_closed():
            await bot.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
        logger.info("Test completed successfully")
    except KeyboardInterrupt:
        logger.info("Test interrupted by user")
    except Exception as e:
        logger.error(f"Test failed: {e}")
        sys.exit(1)
