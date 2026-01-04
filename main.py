import os
import asyncio
import logging
import tracemalloc
import json
from groq import Groq
import discord
from discord import app_commands
from discord.ext import commands

tracemalloc.start()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load tokens
try:
    discord_token = os.environ.get('DISCORD_TOKEN')
    groq_api_key = os.environ.get('GROQ_API_KEY')
    client_id = os.environ.get('CLIENT_ID')
    
    if not discord_token:
        # Fallback to config.json if not in env
        with open('config.json', 'r') as f:
            config = json.load(f)
            discord_token = config.get('discord_token')
            groq_api_key = groq_api_key or config.get('groq_api_key')
            client_id = client_id or config.get('client_id')

    if not discord_token:
        raise ValueError("Discord token not found")
    if not groq_api_key:
        raise ValueError("Groq API key not found")
        
    logger.info("Successfully loaded tokens")
except Exception as e:
    logger.error(f"Token loading error: {str(e)}")
    raise

# Configure Groq
try:
    groq_client = Groq(api_key=groq_api_key)
except Exception as e:
    print(f"Error configuring Groq: {str(e)}")
    exit(1)

# Set intents (disable privileged intents unless enabled in Developer Portal)
intents = discord.Intents.default()
# intents.message_content = True  # Commented out as it requires manual enabling in portal
xevfx = commands.Bot(command_prefix="?", intents=intents)

def load_channel_config():
    try:
        with open('channel_config.json', 'r') as f:
            return json.load(f)
    except:
        return {"channels": {}}

def save_channel_config(guild_id, channel_id):
    config = load_channel_config()
    if channel_id is None:
        if str(guild_id) in config["channels"]:
            del config["channels"][str(guild_id)]
    else:
        config["channels"][str(guild_id)] = channel_id
    with open('channel_config.json', 'w') as f:
        json.dump(config, f)

@xevfx.event
async def on_ready():
    print(f"Logged in as {xevfx.user}")
    if client_id:
        print(f"Client ID: {client_id}")
    await xevfx.tree.sync()
    await xevfx.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="Message | discord.com/invite/9MVAPpfs8D"))

@xevfx.tree.command(name="remove", description="Remove the channel from bot responses")
async def remove(interaction: discord.Interaction):
    try:
        save_channel_config(interaction.guild_id, None)
        await interaction.response.send_message("This channel has been removed from bot responses!", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"Error removing channel: {str(e)}", ephemeral=True)

@xevfx.tree.command(name="setup", description="Set up the channel for bot responses")
async def setup(interaction: discord.Interaction):
    try:
        save_channel_config(interaction.guild_id, interaction.channel_id)
        await interaction.response.send_message("This channel has been set up for bot responses!", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"Error setting up channel: {str(e)}", ephemeral=True)

async def get_ai_response(content):
    try:
        chat_completion = await asyncio.to_thread(
            groq_client.chat.completions.create,
            messages=[
                {
                    "role": "user",
                    "content": content,
                }
            ],
            model="llama-3.3-70b-versatile",
        )
        return chat_completion.choices[0].message.content
    except Exception as e:
        return f"Error: {str(e)}"

@xevfx.event
async def on_message(message):
    if message.author.bot:
        return

    config = load_channel_config()
    channel_id = config["channels"].get(str(message.guild.id))

    if (channel_id and message.channel.id == channel_id) or message.content.startswith(xevfx.user.mention):
        async with message.channel.typing():
            content = message.content
            if message.content.startswith(xevfx.user.mention):
                content = content.replace(xevfx.user.mention, '').strip()
            
            response_text = await get_ai_response(content)

            if len(response_text) <= 1900:
                await message.reply(response_text)
            else:
                chunks = [response_text[i:i+1900] for i in range(0, len(response_text), 1900)]
                for i, chunk in enumerate(chunks):
                    await message.reply(f"{chunk}\n(Part {i+1}/{len(chunks)})")

    await xevfx.process_commands(message)

xevfx.run(discord_token)
