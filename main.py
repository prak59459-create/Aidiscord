import os
import asyncio
import discord
from mcp.server.fastmcp import FastMCP

DISCORD_TOKEN = os.getenv("DISCORD_BOT_TOKEN")

mcp = FastMCP("Discord-Server-Builder", host="0.0.0.0")

intents = discord.Intents.default()
intents.guilds = True
intents.members = True
intents.message_content = True

client = discord.Client(intents=intents)
bot_ready = asyncio.Event()

@client.event
async def on_ready():
    print(f"Logged in to Discord as {client.user}")
    bot_ready.set()

async def ensure_bot_ready():
    if not client.is_ready():
        asyncio.create_task(client.start(DISCORD_TOKEN))
        await bot_ready.wait()

# ==========================================
# 1. チャンネル & カテゴリー管理ツール
# ==========================================

@mcp.tool()
async def create_category(guild_id: str, category_name: str) -> str:
    """Discordサーバーに新しいカテゴリーを作成します。"""
    await ensure_bot_ready()
    guild = client.get_guild(int(guild_id))
    if not guild:
        return "指定されたサーバーが見つかりません。"
    
    category = await guild.create_category(category_name)
    return f"カテゴリー『{category.name}』(ID: {category.id}) を作成しました。"

@mcp.tool()
async def create_channel(guild_id: str, channel_name: str, channel_type: str = "text", category_id: str = None, topic: str = None) -> str:
    """指定されたサーバーにテキストまたはボイスチャンネルを作成します。"""
    await ensure_bot_ready()
    guild = client.get_guild(int(guild_id))
    if not guild:
        return "指定されたサーバーが見つかりません。"

    category = guild.get_channel(int(category_id)) if category_id else None

    if channel_type == "text":
        ch = await guild.create_text_channel(channel_name, category=category, topic=topic)
    elif channel_type == "voice":
        ch = await guild.create_voice_channel(channel_name, category=category)
    else:
        return "channel_type は 'text' または 'voice' を指定してください。"

    return f"チャンネル『{ch.name}』(ID: {ch.id}) を作成しました。"

@mcp.tool()
async def delete_channel(guild_id: str, channel_id: str) -> str:
    """指定されたチャンネルを削除します。"""
    await ensure_bot_ready()
    guild = client.get_guild(int(guild_id))
    if not guild:
        return "指定されたサーバーが見つかりません。"
    
    channel = guild.get_channel(int(channel_id))
    if not channel:
        return "指定されたチャンネルが見つかりません。"

    name = channel.name
    await channel.delete()
    return f"チャンネル『{name}』を削除しました。"

@mcp.tool()
async def list_channels(guild_id: str) -> str:
    """サーバー内の現在のチャンネル・カテゴリー一覧を取得します。"""
    await ensure_bot_ready()
    guild = client.get_guild(int(guild_id))
    if not guild:
        return "指定されたサーバーが見つかりません。"

    channels_info = []
    for ch in guild.channels:
        channels_info.append(f"- {ch.name} (Type: {ch.type}, ID: {ch.id})")
    
    return "\n".join(channels_info)

# ==========================================
# 2. ロール（役職）管理ツール
# ==========================================

@mcp.tool()
async def create_role(guild_id: str, role_name: str, color_hex: str = None, mentionable: bool = True) -> str:
    """新しいロール（役職）を作成します。color_hexはカラーコード（例: #FF0000）"""
    await ensure_bot_ready()
    guild = client.get_guild(int(guild_id))
    if not guild:
        return "指定されたサーバーが見つかりません。"

    color = discord.Color.default()
    if color_hex:
        try:
            color_hex = color_hex.lstrip('#')
            color = discord.Color(int(color_hex, 16))
        except ValueError:
            pass

    role = await guild.create_role(name=role_name, color=color, mentionable=mentionable)
    return f"ロール『{role.name}』(ID: {role.id}) を作成しました。"

@mcp.tool()
async def assign_role(guild_id: str, user_id: str, role_id: str) -> str:
    """指定したメンバーにロールを付与します。"""
    await ensure_bot_ready()
    guild = client.get_guild(int(guild_id))
    if not guild:
        return "指定されたサーバーが見つかりません。"

    member = guild.get_member(int(user_id))
    if not member:
        return "指定されたメンバーが見つかりません。"

    role = guild.get_role(int(role_id))
    if not role:
        return "指定されたロールが見つかりません。"

    await member.add_roles(role)
    return f"メンバー『{member.name}』にロール『{role.name}』を付与しました。"

@mcp.tool()
async def list_roles(guild_id: str) -> str:
    """サーバー内のロール一覧を取得します。"""
    await ensure_bot_ready()
    guild = client.get_guild(int(guild_id))
    if not guild:
        return "指定されたサーバーが見つかりません。"

    roles_info = [f"- {role.name} (ID: {role.id})" for role in guild.roles]
    return "\n".join(roles_info)

# ==========================================
# 3. メッセージ管理ツール
# ==========================================

@mcp.tool()
async def send_message(guild_id: str, channel_id: str, content: str) -> str:
    """指定したチャンネルにメッセージを送信します。"""
    await ensure_bot_ready()
    guild = client.get_guild(int(guild_id))
    if not guild:
        return "指定されたサーバーが見つかりません。"

    channel = guild.get_channel(int(channel_id))
    if not channel or not isinstance(channel, discord.TextChannel):
        return "指定されたテキストチャンネルが見つかりません。"

    msg = await channel.send(content)
    return f"チャンネル『{channel.name}』にメッセージを送信しました。(Message ID: {msg.id})"

# ==========================================
# 4. 起動処理
# ==========================================

if __name__ == "__main__":
    import uvicorn
    
    port = int(os.getenv("PORT", 8000))
    app = mcp.sse_app()

    uvicorn.run(app, host="0.0.0.0", port=port)
