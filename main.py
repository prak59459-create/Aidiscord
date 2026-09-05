import os
import asyncio
import discord
from mcp.server.fastmcp import FastMCP

# 環境変数からBotトークンを取得
DISCORD_TOKEN = os.getenv("DISCORD_BOT_TOKEN")

# MCPサーバーの初期化
mcp = FastMCP("Discord-Server-Builder")

# Discord Clientの設定
intents = discord.Intents.default()
intents.guilds = True
client = discord.Client(intents=intents)

# Discordのログイン状態管理
bot_ready = asyncio.Event()

@client.event
async def on_ready():
    print(f"Logged in to Discord as {client.user}")
    bot_ready.set()

async def ensure_bot_ready():
    if not client.is_ready():
        asyncio.create_task(client.start(DISCORD_TOKEN))
        await bot_ready.wait()

# --- Claudeから呼び出すツール群 ---

@mcp.tool()
async def create_category(guild_id: int, category_name: str) -> str:
    """Discordサーバーに新しいカテゴリーを作成します。"""
    await ensure_bot_ready()
    guild = client.get_guild(guild_id)
    if not guild:
        return "指定されたサーバーが見つかりません。"
    
    category = await guild.create_category(category_name)
    return f"カテゴリー『{category.name}』(ID: {category.id}) を作成しました。"

@mcp.tool()
async def create_channel(guild_id: int, channel_name: str, channel_type: str = "text", category_id: int = None) -> str:
    """
    指定されたサーバーにテキストまたはボイスチャンネルを作成します。
    channel_type: 'text' または 'voice'
    """
    await ensure_bot_ready()
    guild = client.get_guild(guild_id)
    if not guild:
        return "指定されたサーバーが見つかりません。"

    category = guild.get_channel(category_id) if category_id else None

    if channel_type == "text":
        ch = await guild.create_text_channel(channel_name, category=category)
    elif channel_type == "voice":
        ch = await guild.create_voice_channel(channel_name, category=category)
    else:
        return "channel_type は 'text' または 'voice' を指定してください。"

    return f"チャンネル『{ch.name}』を作成しました。"

@mcp.tool()
async def list_channels(guild_id: int) -> str:
    """サーバー内の現在のチャンネル一覧を取得します。"""
    await ensure_bot_ready()
    guild = client.get_guild(guild_id)
    if not guild:
        return "指定されたサーバーが見つかりません。"

    channels_info = []
    for ch in guild.channels:
        channels_info.append(f"- {ch.name} (Type: {ch.type}, ID: {ch.id})")
    
    return "\n".join(channels_info)

if __name__ == "__main__":
    # MCP SSEサーバーの起動
    mcp.run(transport="sse")
