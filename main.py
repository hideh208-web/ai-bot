
import os
import asyncio
import logging
import tracemalloc
import json
import google.generativeai as genai
import discord
from discord import app_commands
from discord.ext import commands

tracemalloc.start()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load tokens from config.json
try:
    with open('config.json', 'r') as f:
        config = json.load(f)
    
    discord_token = config.get('discord_token')
    if not discord_token or discord_token.strip() == "":
        raise ValueError("Discord token not found in config.json")
        
    gemini_api_key = config.get('gemini_api_key')
    if not gemini_api_key or gemini_api_key.strip() == "":
        raise ValueError("Gemini API key not found in config.json")
        
    logger.info("Successfully loaded config.json")
except Exception as e:
    logger.error(f"Config loading error: {str(e)}")
    raise

# Configure Gemini
try:
    genai.configure(api_key=gemini_api_key)
    gemini_model = genai.GenerativeModel('gemini-1.5-flash')
except Exception as e:
    print(f"Error configuring Gemini: {str(e)}")
    exit(1)

intents = discord.Intents.all()
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

@xevfx.event
async def on_message(message):
    if message.author.bot:
        return

    config = load_channel_config()
    channel_id = config["channels"].get(str(message.guild.id))

    if channel_id and message.channel.id == channel_id:
        # Regular response in configured channel
        async with message.channel.typing():
            try:
                response = await asyncio.to_thread(
                    gemini_model.generate_content,
                    message.content
                )
                response_text = response.text if hasattr(response, 'text') else str(response)

                if len(response_text) <= 1900:
                    await message.reply(response_text)
                else:
                    chunks = [response_text[i:i+1900] for i in range(0, len(response_text), 1900)]
                    for i, chunk in enumerate(chunks):
                        await message.reply(f"{chunk}\n(Part {i+1}/{len(chunks)})")
            except Exception as e:
                await message.reply(f"Error: {str(e)}")
    elif message.content.startswith(xevfx.user.mention):
        # Response when pinged in other channels
        async with message.channel.typing():
            try:
                content = message.content.replace(xevfx.user.mention, '').strip()
                response = await asyncio.to_thread(
                    gemini_model.generate_content,
                    content
                )
                response_text = response.text if hasattr(response, 'text') else str(response)

                if len(response_text) <= 1900:
                    await message.reply(response_text)
                else:
                    chunks = [response_text[i:i+1900] for i in range(0, len(response_text), 1900)]
                    for i, chunk in enumerate(chunks):
                        await message.reply(f"{chunk}\n(Part {i+1}/{len(chunks)})")
            except Exception as e:
                await message.reply(f"Error: {str(e)}")

    await xevfx.process_commands(message)

xevfx.run(discord_token)
