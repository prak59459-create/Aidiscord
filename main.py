import os
import asyncio
from datetime import datetime, timedelta
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


@client.event
async def on_interaction(interaction: discord.Interaction):
    """ボタンが押された時、custom_idからロールを判定して自動付与する。
    Bot再起動後も動作する(Viewの再登録が不要な実装)。"""
    if interaction.type != discord.InteractionType.component:
        return

    custom_id = interaction.data.get("custom_id", "") if interaction.data else ""
    if not custom_id.startswith("verify_role:"):
        return

    role_id_str = custom_id.split(":", 1)[1]
    guild = interaction.guild
    if not guild:
        return

    role = guild.get_role(int(role_id_str))
    if not role:
        await interaction.response.send_message("対象のロールが見つかりませんでした。運営に連絡してください。", ephemeral=True)
        return

    member = interaction.user
    if role in member.roles:
        await interaction.response.send_message(f"すでに『{role.name}』を持っています。", ephemeral=True)
    else:
        await member.add_roles(role)
        await interaction.response.send_message(f"『{role.name}』を付与しました!ようこそ🎉", ephemeral=True)


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


@mcp.tool()
async def move_channel_to_category(guild_id: str, channel_id: str, category_id: str) -> str:
    """既存チャンネルを指定カテゴリーに移動します(認証チャンネルの整理などに)。"""
    await ensure_bot_ready()
    guild = client.get_guild(int(guild_id))
    if not guild:
        return "指定されたサーバーが見つかりません。"
    channel = guild.get_channel(int(channel_id))
    category = guild.get_channel(int(category_id))
    if not channel:
        return "指定されたチャンネルが見つかりません。"
    if not category or not isinstance(category, discord.CategoryChannel):
        return "指定されたカテゴリーが見つかりません。"
    await channel.edit(category=category)
    return f"チャンネル『{channel.name}』を『{category.name}』に移動しました。"


@mcp.tool()
async def edit_channel(
    guild_id: str,
    channel_id: str,
    new_name: str = None,
    new_topic: str = None,
    slowmode_seconds: int = None,
) -> str:
    """既存チャンネルの名前・トピック・スロークモードを変更します。"""
    await ensure_bot_ready()
    guild = client.get_guild(int(guild_id))
    if not guild:
        return "指定されたサーバーが見つかりません。"
    channel = guild.get_channel(int(channel_id))
    if not channel:
        return "指定されたチャンネルが見つかりません。"

    kwargs = {}
    if new_name:
        kwargs["name"] = new_name
    if new_topic is not None and hasattr(channel, "topic"):
        kwargs["topic"] = new_topic
    if slowmode_seconds is not None and hasattr(channel, "slowmode_delay"):
        kwargs["slowmode_delay"] = slowmode_seconds
    if not kwargs:
        return "変更する項目がありません。"

    await channel.edit(**kwargs)
    return f"チャンネル『{channel.name}』を更新しました。"


@mcp.tool()
async def delete_category(guild_id: str, category_id: str) -> str:
    """指定カテゴリーを削除します(中のチャンネルは別途削除が必要です)。"""
    await ensure_bot_ready()
    guild = client.get_guild(int(guild_id))
    if not guild:
        return "指定されたサーバーが見つかりません。"
    category = guild.get_channel(int(category_id))
    if not category or not isinstance(category, discord.CategoryChannel):
        return "指定されたカテゴリーが見つかりません。"
    name = category.name
    await category.delete()
    return f"カテゴリー『{name}』を削除しました。"


@mcp.tool()
async def purge_messages(guild_id: str, channel_id: str, limit: int = 10) -> str:
    """直近のメッセージをまとめて削除します(荒らし・スパム対策)。"""
    await ensure_bot_ready()
    guild = client.get_guild(int(guild_id))
    if not guild:
        return "指定されたサーバーが見つかりません。"
    channel = guild.get_channel(int(channel_id))
    if not channel or not isinstance(channel, discord.TextChannel):
        return "指定されたテキストチャンネルが見つかりません。"
    deleted = await channel.purge(limit=limit)
    return f"『{channel.name}』でメッセージを{len(deleted)}件削除しました。"


@mcp.tool()
async def create_thread(guild_id: str, channel_id: str, thread_name: str, message_content: str = None) -> str:
    """指定テキストチャンネルにスレッドを作成します。"""
    await ensure_bot_ready()
    guild = client.get_guild(int(guild_id))
    if not guild:
        return "指定されたサーバーが見つかりません。"
    channel = guild.get_channel(int(channel_id))
    if not channel or not isinstance(channel, discord.TextChannel):
        return "指定されたテキストチャンネルが見つかりません。"
    thread = await channel.create_thread(name=thread_name, type=discord.ChannelType.public_thread)
    if message_content:
        await thread.send(message_content)
    return f"スレッド『{thread.name}』(ID: {thread.id}) を作成しました。"


@mcp.tool()
async def set_channel_permission(
    guild_id: str,
    channel_id: str,
    role_id: str,
    allow: list[str] = None,
    deny: list[str] = None,
) -> str:
    """
    指定チャンネルの、指定ロールに対する権限を設定します。
    allow/deny には discord.Permissions の属性名を文字列で渡します。
    例: allow=["view_channel","send_messages"], deny=["view_channel"]
    よく使う権限名: view_channel, send_messages, connect, speak,
                   manage_messages, manage_channels, kick_members,
                   ban_members, moderate_members
    """
    await ensure_bot_ready()
    guild = client.get_guild(int(guild_id))
    if not guild:
        return "指定されたサーバーが見つかりません。"
    channel = guild.get_channel(int(channel_id))
    if not channel:
        return "指定されたチャンネルが見つかりません。"
    role = guild.get_role(int(role_id))
    if not role:
        return "指定されたロールが見つかりません。"

    overwrite = channel.overwrites_for(role)
    if allow:
        for perm in allow:
            if hasattr(overwrite, perm):
                setattr(overwrite, perm, True)
    if deny:
        for perm in deny:
            if hasattr(overwrite, perm):
                setattr(overwrite, perm, False)

    await channel.set_permissions(role, overwrite=overwrite)
    return f"チャンネル『{channel.name}』のロール『{role.name}』への権限を更新しました。"


@mcp.tool()
async def hide_channel_from_everyone(guild_id: str, channel_id: str) -> str:
    """@everyone からチャンネルを見えなくします(未認証者を締め出す等に便利)。"""
    await ensure_bot_ready()
    guild = client.get_guild(int(guild_id))
    if not guild:
        return "指定されたサーバーが見つかりません。"
    channel = guild.get_channel(int(channel_id))
    if not channel:
        return "指定されたチャンネルが見つかりません。"

    overwrite = channel.overwrites_for(guild.default_role)
    overwrite.view_channel = False
    await channel.set_permissions(guild.default_role, overwrite=overwrite)
    return f"チャンネル『{channel.name}』を@everyoneから非表示にしました。"


# ==========================================
# 2. ロール(役職)管理ツール
# ==========================================

@mcp.tool()
async def create_role(guild_id: str, role_name: str, color_hex: str = None, mentionable: bool = True) -> str:
    """新しいロール(役職)を作成します。color_hexはカラーコード(例: #FF0000)"""
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


@mcp.tool()
async def edit_role(
    guild_id: str,
    role_id: str,
    new_name: str = None,
    color_hex: str = None,
    hoist: bool = None,
    mentionable: bool = None,
) -> str:
    """既存ロールの名前・色・メンバー一覧での表示・メンション可否を変更します。"""
    await ensure_bot_ready()
    guild = client.get_guild(int(guild_id))
    if not guild:
        return "指定されたサーバーが見つかりません。"
    role = guild.get_role(int(role_id))
    if not role:
        return "指定されたロールが見つかりません。"

    kwargs = {}
    if new_name:
        kwargs["name"] = new_name
    if color_hex:
        kwargs["color"] = discord.Color(int(color_hex.lstrip("#"), 16))
    if hoist is not None:
        kwargs["hoist"] = hoist
    if mentionable is not None:
        kwargs["mentionable"] = mentionable
    if not kwargs:
        return "変更する項目がありません。"

    await role.edit(**kwargs)
    return f"ロール『{role.name}』を更新しました。"


@mcp.tool()
async def delete_role(guild_id: str, role_id: str) -> str:
    """指定ロールを削除します。"""
    await ensure_bot_ready()
    guild = client.get_guild(int(guild_id))
    if not guild:
        return "指定されたサーバーが見つかりません。"
    role = guild.get_role(int(role_id))
    if not role:
        return "指定されたロールが見つかりません。"
    name = role.name
    await role.delete()
    return f"ロール『{name}』を削除しました。"


@mcp.tool()
async def remove_role(guild_id: str, user_id: str, role_id: str) -> str:
    """指定メンバーからロールを剥奪します(assign_roleの逆)。"""
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
    await member.remove_roles(role)
    return f"メンバー『{member.name}』からロール『{role.name}』を剥奪しました。"


@mcp.tool()
async def get_role_members(guild_id: str, role_id: str) -> str:
    """指定ロールを持つメンバー一覧を取得します。"""
    await ensure_bot_ready()
    guild = client.get_guild(int(guild_id))
    if not guild:
        return "指定されたサーバーが見つかりません。"
    role = guild.get_role(int(role_id))
    if not role:
        return "指定されたロールが見つかりません。"
    if not role.members:
        return f"『{role.name}』を持つメンバーはいません。"
    return "\n".join(f"- {m.name} (ID: {m.id})" for m in role.members)


@mcp.tool()
async def set_role_permissions(guild_id: str, role_id: str, permissions: list[str]) -> str:
    """
    ロールにサーバー権限セットを付与します(モデレーターロールに実権を持たせる用)。
    例: ["kick_members","ban_members","manage_messages","moderate_members","manage_channels"]
    """
    await ensure_bot_ready()
    guild = client.get_guild(int(guild_id))
    if not guild:
        return "指定されたサーバーが見つかりません。"
    role = guild.get_role(int(role_id))
    if not role:
        return "指定されたロールが見つかりません。"

    perms = discord.Permissions()
    applied = []
    for p in permissions:
        if hasattr(perms, p):
            setattr(perms, p, True)
            applied.append(p)

    await role.edit(permissions=perms)
    return f"ロール『{role.name}』に権限({', '.join(applied)})を付与しました。"


@mcp.tool()
async def create_role_button_message(
    guild_id: str,
    channel_id: str,
    role_id: str,
    button_label: str,
    message_content: str = None,
) -> str:
    """
    ボタン付きメッセージを送信し、押すと自動でロールが付与される「本物のボタン認証」を実現します。
    (このファイル冒頭の on_interaction が処理を受け取ります)
    """
    await ensure_bot_ready()
    guild = client.get_guild(int(guild_id))
    if not guild:
        return "指定されたサーバーが見つかりません。"
    channel = guild.get_channel(int(channel_id))
    if not channel:
        return "指定されたチャンネルが見つかりません。"
    role = guild.get_role(int(role_id))
    if not role:
        return "指定されたロールが見つかりません。"

    view = discord.ui.View(timeout=None)
    view.add_item(discord.ui.Button(
        label=button_label,
        style=discord.ButtonStyle.success,
        custom_id=f"verify_role:{role_id}",
    ))

    msg = await channel.send(
        content=message_content or f"下のボタンを押すと『{role.name}』が付与されます。",
        view=view,
    )
    return f"チャンネル『{channel.name}』にボタン付きメッセージを送信しました。(Message ID: {msg.id})"


# ==========================================
# 3. メンバー・モデレーション管理ツール
# ==========================================

@mcp.tool()
async def kick_member(guild_id: str, user_id: str, reason: str = None) -> str:
    """指定メンバーをサーバーからキックします。"""
    await ensure_bot_ready()
    guild = client.get_guild(int(guild_id))
    if not guild:
        return "指定されたサーバーが見つかりません。"
    member = guild.get_member(int(user_id))
    if not member:
        return "指定されたメンバーが見つかりません。"
    await member.kick(reason=reason)
    return f"メンバー『{member.name}』をキックしました。"


@mcp.tool()
async def ban_member(guild_id: str, user_id: str, reason: str = None) -> str:
    """指定メンバーをサーバーからBANします。"""
    await ensure_bot_ready()
    guild = client.get_guild(int(guild_id))
    if not guild:
        return "指定されたサーバーが見つかりません。"
    member = guild.get_member(int(user_id))
    if not member:
        return "指定されたメンバーが見つかりません。"
    await member.ban(reason=reason)
    return f"メンバー『{member.name}』をBANしました。"


@mcp.tool()
async def timeout_member(guild_id: str, user_id: str, minutes: int, reason: str = None) -> str:
    """指定メンバーを一定時間タイムアウト(発言・反応禁止)させます。"""
    await ensure_bot_ready()
    guild = client.get_guild(int(guild_id))
    if not guild:
        return "指定されたサーバーが見つかりません。"
    member = guild.get_member(int(user_id))
    if not member:
        return "指定されたメンバーが見つかりません。"
    await member.timeout(timedelta(minutes=minutes), reason=reason)
    return f"メンバー『{member.name}』を{minutes}分間タイムアウトしました。"


@mcp.tool()
async def unban_member(guild_id: str, user_id: str) -> str:
    """BAN済みユーザーのBANを解除します。"""
    await ensure_bot_ready()
    guild = client.get_guild(int(guild_id))
    if not guild:
        return "指定されたサーバーが見つかりません。"
    user = await client.fetch_user(int(user_id))
    try:
        await guild.unban(user)
    except discord.NotFound:
        return "指定されたユーザーはBANされていません。"
    return f"ユーザー『{user.name}』のBANを解除しました。"


@mcp.tool()
async def set_member_nickname(guild_id: str, user_id: str, nickname: str) -> str:
    """指定メンバーのサーバー内ニックネームを変更します。"""
    await ensure_bot_ready()
    guild = client.get_guild(int(guild_id))
    if not guild:
        return "指定されたサーバーが見つかりません。"
    member = guild.get_member(int(user_id))
    if not member:
        return "指定されたメンバーが見つかりません。"
    await member.edit(nick=nickname)
    return f"『{member.name}』のニックネームを『{nickname}』に変更しました。"


@mcp.tool()
async def move_voice_member(guild_id: str, user_id: str, channel_id: str) -> str:
    """指定メンバーを別のボイスチャンネルに移動させます。"""
    await ensure_bot_ready()
    guild = client.get_guild(int(guild_id))
    if not guild:
        return "指定されたサーバーが見つかりません。"
    member = guild.get_member(int(user_id))
    if not member:
        return "指定されたメンバーが見つかりません。"
    channel = guild.get_channel(int(channel_id))
    if not channel or not isinstance(channel, discord.VoiceChannel):
        return "指定されたボイスチャンネルが見つかりません。"
    await member.move_to(channel)
    return f"『{member.name}』を『{channel.name}』に移動しました。"


@mcp.tool()
async def list_members(guild_id: str, limit: int = 50) -> str:
    """サーバーメンバー一覧(名前・ID・所持ロール)を取得します。"""
    await ensure_bot_ready()
    guild = client.get_guild(int(guild_id))
    if not guild:
        return "指定されたサーバーが見つかりません。"
    members = guild.members[:limit]
    if not members:
        return "メンバーが見つかりません。"
    lines = []
    for m in members:
        role_names = ", ".join(r.name for r in m.roles if r.name != "@everyone")
        lines.append(f"- {m.name} (ID: {m.id}) roles: {role_names or 'なし'}")
    return "\n".join(lines)


# ==========================================
# 4. メッセージ・エンゲージメント管理ツール
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


@mcp.tool()
async def send_embed(
    guild_id: str,
    channel_id: str,
    title: str,
    description: str,
    color_hex: str = "#5865F2",
    footer: str = None,
    image_url: str = None,
) -> str:
    """指定チャンネルに埋め込み(Embed)メッセージを送信します。ルール・案内文を綺麗に見せるのに最適。"""
    await ensure_bot_ready()
    guild = client.get_guild(int(guild_id))
    if not guild:
        return "指定されたサーバーが見つかりません。"
    channel = guild.get_channel(int(channel_id))
    if not channel or not isinstance(channel, discord.TextChannel):
        return "指定されたテキストチャンネルが見つかりません。"

    color_hex = color_hex.lstrip("#")
    try:
        color = discord.Color(int(color_hex, 16))
    except ValueError:
        color = discord.Color.blurple()

    embed = discord.Embed(title=title, description=description, color=color)
    if footer:
        embed.set_footer(text=footer)
    if image_url:
        embed.set_image(url=image_url)

    msg = await channel.send(embed=embed)
    return f"チャンネル『{channel.name}』に埋め込みメッセージを送信しました。(Message ID: {msg.id})"


@mcp.tool()
async def pin_message(guild_id: str, channel_id: str, message_id: str) -> str:
    """指定メッセージをピン留めします。"""
    await ensure_bot_ready()
    guild = client.get_guild(int(guild_id))
    if not guild:
        return "指定されたサーバーが見つかりません。"
    channel = guild.get_channel(int(channel_id))
    if not channel:
        return "指定されたチャンネルが見つかりません。"
    try:
        msg = await channel.fetch_message(int(message_id))
    except discord.NotFound:
        return "指定されたメッセージが見つかりません。"
    await msg.pin()
    return f"メッセージ(ID: {message_id})をピン留めしました。"


@mcp.tool()
async def create_poll(
    guild_id: str,
    channel_id: str,
    question: str,
    options: list[str],
    duration_hours: int = 24,
    multiple_choice: bool = False,
) -> str:
    """指定チャンネルにDiscordネイティブの投票(Poll)を送信します。optionsは最大10個まで。"""
    await ensure_bot_ready()
    guild = client.get_guild(int(guild_id))
    if not guild:
        return "指定されたサーバーが見つかりません。"
    channel = guild.get_channel(int(channel_id))
    if not channel or not isinstance(channel, discord.TextChannel):
        return "指定されたテキストチャンネルが見つかりません。"

    poll = discord.Poll(
        question=question,
        duration=timedelta(hours=duration_hours),
        multiple=multiple_choice,
    )
    for opt in options[:10]:
        poll.add_answer(text=opt)

    msg = await channel.send(poll=poll)
    return f"チャンネル『{channel.name}』に投票を送信しました。(Message ID: {msg.id})"


@mcp.tool()
async def create_emoji(guild_id: str, emoji_name: str, image_url: str) -> str:
    """画像URLからカスタム絵文字を追加します。"""
    await ensure_bot_ready()
    guild = client.get_guild(int(guild_id))
    if not guild:
        return "指定されたサーバーが見つかりません。"

    import aiohttp
    async with aiohttp.ClientSession() as session:
        async with session.get(image_url) as resp:
            if resp.status != 200:
                return "画像の取得に失敗しました。URLを確認してください。"
            image_bytes = await resp.read()

    emoji = await guild.create_custom_emoji(name=emoji_name, image=image_bytes)
    return f"絵文字『{emoji.name}』を追加しました。"


# ==========================================
# 5. 認証・安全設定ツール
# ==========================================

@mcp.tool()
async def set_verification_level(guild_id: str, level: str) -> str:
    """
    サーバー全体の認証レベルを設定します(Discordネイティブ機能)。
    level: none / low / medium / high / highest
      - low: 認証済みメールアドレスが必要
      - medium: Discord登録から5分経過が必要
      - high: サーバー参加から10分経過が必要
      - highest: 認証済み電話番号が必要
    """
    await ensure_bot_ready()
    guild = client.get_guild(int(guild_id))
    if not guild:
        return "指定されたサーバーが見つかりません。"

    level_map = {
        "none": discord.VerificationLevel.none,
        "low": discord.VerificationLevel.low,
        "medium": discord.VerificationLevel.medium,
        "high": discord.VerificationLevel.high,
        "highest": discord.VerificationLevel.highest,
    }
    if level not in level_map:
        return "levelは none/low/medium/high/highest のいずれかを指定してください。"

    await guild.edit(verification_level=level_map[level])
    return f"サーバーの認証レベルを『{level}』に設定しました。"


@mcp.tool()
async def create_automod_keyword_rule(guild_id: str, rule_name: str, banned_words: list[str]) -> str:
    """禁止ワードを検知して自動でメッセージをブロックするAutoModルールを作成します。"""
    await ensure_bot_ready()
    guild = client.get_guild(int(guild_id))
    if not guild:
        return "指定されたサーバーが見つかりません。"

    trigger = discord.AutoModTrigger(
        type=discord.AutoModRuleTriggerType.keyword,
        keyword_filter=banned_words,
    )
    action = discord.AutoModRuleAction(type=discord.AutoModRuleActionType.block_message)

    rule = await guild.create_automod_rule(
        name=rule_name,
        event_type=discord.AutoModRuleEventType.message_send,
        trigger=trigger,
        actions=[action],
        enabled=True,
    )
    return f"AutoModルール『{rule.name}』(ID: {rule.id}) を作成しました。"


# ==========================================
# 6. 連携・運営ツール
# ==========================================

@mcp.tool()
async def create_invite(
    guild_id: str,
    channel_id: str,
    max_uses: int = 0,
    max_age_seconds: int = 0,
    temporary: bool = False,
) -> str:
    """招待リンクを作成します。max_uses=0で無制限、max_age_seconds=0で無期限。"""
    await ensure_bot_ready()
    guild = client.get_guild(int(guild_id))
    if not guild:
        return "指定されたサーバーが見つかりません。"
    channel = guild.get_channel(int(channel_id))
    if not channel:
        return "指定されたチャンネルが見つかりません。"
    invite = await channel.create_invite(max_uses=max_uses, max_age=max_age_seconds, temporary=temporary)
    return f"招待リンクを作成しました: {invite.url}"


@mcp.tool()
async def create_webhook(guild_id: str, channel_id: str, webhook_name: str) -> str:
    """指定チャンネルにWebhookを作成します(外部通知・お知らせ連携用)。"""
    await ensure_bot_ready()
    guild = client.get_guild(int(guild_id))
    if not guild:
        return "指定されたサーバーが見つかりません。"
    channel = guild.get_channel(int(channel_id))
    if not channel or not isinstance(channel, discord.TextChannel):
        return "指定されたテキストチャンネルが見つかりません。"
    webhook = await channel.create_webhook(name=webhook_name)
    return f"Webhook『{webhook.name}』を作成しました。URL: {webhook.url}"


@mcp.tool()
async def create_scheduled_event(
    guild_id: str,
    name: str,
    description: str,
    start_time_iso: str,
    channel_id: str = None,
) -> str:
    """
    Discordネイティブの予定イベントを作成します(カレンダー表示+参加ボタン自動)。
    start_time_isoはISO8601形式(例: 2026-09-10T20:00:00+09:00)。
    channel_id指定でボイスチャンネルイベント、未指定ならオンライン外部イベント扱い。
    """
    await ensure_bot_ready()
    guild = client.get_guild(int(guild_id))
    if not guild:
        return "指定されたサーバーが見つかりません。"

    try:
        start_time = datetime.fromisoformat(start_time_iso)
    except ValueError:
        return "start_time_isoの形式が不正です。例: 2026-09-10T20:00:00+09:00"

    if channel_id:
        channel = guild.get_channel(int(channel_id))
        if not channel:
            return "指定されたチャンネルが見つかりません。"
        event = await guild.create_scheduled_event(
            name=name,
            description=description,
            start_time=start_time,
            channel=channel,
            entity_type=discord.EntityType.voice,
        )
    else:
        event = await guild.create_scheduled_event(
            name=name,
            description=description,
            start_time=start_time,
            end_time=start_time,
            entity_type=discord.EntityType.external,
            location="オンライン",
        )
    return f"イベント『{event.name}』(ID: {event.id}) を作成しました。"


@mcp.tool()
async def get_server_stats(guild_id: str) -> str:
    """サーバーの基本統計(メンバー数、ブースト状況など)を取得します。"""
    await ensure_bot_ready()
    guild = client.get_guild(int(guild_id))
    if not guild:
        return "指定されたサーバーが見つかりません。"
    return (
        f"サーバー名: {guild.name}\n"
        f"メンバー数: {guild.member_count}\n"
        f"ブースト数: {guild.premium_subscription_count} (Lv.{guild.premium_tier})\n"
        f"チャンネル数: {len(guild.channels)}\n"
        f"ロール数: {len(guild.roles)}\n"
        f"作成日: {guild.created_at.strftime('%Y-%m-%d')}"
    )


@mcp.tool()
async def get_audit_log(guild_id: str, limit: int = 10) -> str:
    """直近の監査ログ(誰が何をしたか)を取得します。Botに「監査ログを表示」権限が必要です。"""
    await ensure_bot_ready()
    guild = client.get_guild(int(guild_id))
    if not guild:
        return "指定されたサーバーが見つかりません。"
    lines = []
    async for entry in guild.audit_logs(limit=limit):
        lines.append(f"- {entry.created_at.strftime('%Y-%m-%d %H:%M')} {entry.user} : {entry.action}")
    return "\n".join(lines) if lines else "監査ログが見つかりません。"


# ==========================================
# 7. 起動処理
# ==========================================

if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", 8000))
    app = mcp.sse_app()

    uvicorn.run(app, host="0.0.0.0", port=port)
