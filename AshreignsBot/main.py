import discord
from discord.ext import commands
import os
import asyncio
import sys
from datetime import timedelta

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

warnings = {}

OWNER_ID = int(os.environ["OWNER_ID"])


def is_owner():
    async def predicate(ctx):
        if ctx.author.id != OWNER_ID:
            await ctx.send("❌ Only the bot owner can use this command.")
            return False
        return True
    return commands.check(predicate)


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")
    print("------")


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        await ctx.send("Unknown command. Use `!help` to see available commands.")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"Missing argument: `{error.param.name}`.")
    elif isinstance(error, commands.BadArgument):
        await ctx.send("Invalid argument provided.")
    elif isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ You don't have permission to use this command.")
    elif isinstance(error, commands.CheckFailure):
        pass
    else:
        await ctx.send("An unexpected error occurred.")
        raise error


@bot.command(name="restart")
@is_owner()
async def restart(ctx):
    await ctx.send("🔄 Restarting bot...")
    await bot.close()
    os.execv(sys.executable, [sys.executable] + sys.argv)


@bot.command(name="clear")
@commands.has_permissions(manage_messages=True)
async def clear(ctx, amount: int = 5):
    if amount < 1 or amount > 100:
        await ctx.send("Please provide a number between 1 and 100.")
        return
    deleted = await ctx.channel.purge(limit=amount + 1)
    msg = await ctx.send(f"Deleted {len(deleted) - 1} message(s).")
    await msg.delete(delay=3)


@bot.command(name="mute")
@commands.has_permissions(moderate_members=True)
async def mute(ctx, member: discord.Member, duration: int = 10, unit: str = "m", *, reason: str = "No reason provided"):
    units = {"s": 1, "m": 60, "h": 3600, "d": 86400}
    if unit not in units:
        await ctx.send("Invalid time unit. Use `s` (seconds), `m` (minutes), `h` (hours), or `d` (days).")
        return
    seconds = duration * units[unit]
    if seconds > 2419200:
        await ctx.send("Timeout cannot exceed 28 days (Discord limit).")
        return
    until = discord.utils.utcnow() + timedelta(seconds=seconds)
    await member.timeout(until, reason=reason)
    await ctx.send(f"🔇 **{member}** has been muted for **{duration}{unit}**. Reason: {reason}")


@bot.command(name="unmute")
@commands.has_permissions(moderate_members=True)
async def unmute(ctx, member: discord.Member):
    await member.timeout(None)
    await ctx.send(f"🔊 **{member}** has been unmuted.")


@bot.command(name="userinfo")
async def userinfo(ctx, member: discord.Member = None):
    member = member or ctx.author
    roles = [role.mention for role in member.roles if role.name != "@everyone"]
    embed = discord.Embed(title=f"User Info — {member}", color=member.color)
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.add_field(name="ID", value=member.id, inline=True)
    embed.add_field(name="Nickname", value=member.nick or "None", inline=True)
    embed.add_field(name="Account Created", value=member.created_at.strftime("%b %d, %Y"), inline=True)
    embed.add_field(name="Joined Server", value=member.joined_at.strftime("%b %d, %Y"), inline=True)
    embed.add_field(name=f"Roles ({len(roles)})", value=" ".join(roles) if roles else "None", inline=False)
    await ctx.send(embed=embed)


@bot.command(name="serverinfo")
async def serverinfo(ctx):
    guild = ctx.guild
    embed = discord.Embed(title=f"Server Info — {guild.name}", color=discord.Color.blurple())
    if guild.icon:
        embed.set_thumbnail(url=guild.icon.url)
    embed.add_field(name="Owner", value=guild.owner.mention, inline=True)
    embed.add_field(name="Server ID", value=guild.id, inline=True)
    embed.add_field(name="Created", value=guild.created_at.strftime("%b %d, %Y"), inline=True)
    embed.add_field(name="Members", value=guild.member_count, inline=True)
    embed.add_field(name="Channels", value=len(guild.channels), inline=True)
    embed.add_field(name="Roles", value=len(guild.roles), inline=True)
    await ctx.send(embed=embed)


@bot.command(name="poll")
async def poll(ctx, *, question: str):
    embed = discord.Embed(title="📊 Poll", description=question, color=discord.Color.gold())
    embed.set_footer(text=f"Asked by {ctx.author.display_name}")
    msg = await ctx.send(embed=embed)
    await msg.add_reaction("👍")
    await msg.add_reaction("👎")
    await ctx.message.delete()


@bot.command(name="warn")
@commands.has_permissions(kick_members=True)
async def warn(ctx, member: discord.Member, *, reason: str = "No reason provided"):
    key = (ctx.guild.id, member.id)
    warnings.setdefault(key, []).append(reason)
    count = len(warnings[key])
    await ctx.send(f"⚠️ **{member}** has been warned. Reason: {reason}\nTotal warnings: **{count}**")


@bot.command(name="warnings")
async def show_warnings(ctx, member: discord.Member):
    key = (ctx.guild.id, member.id)
    user_warnings = warnings.get(key, [])
    if not user_warnings:
        await ctx.send(f"**{member}** has no warnings.")
        return
    embed = discord.Embed(title=f"Warnings — {member}", color=discord.Color.orange())
    for i, reason in enumerate(user_warnings, 1):
        embed.add_field(name=f"Warning {i}", value=reason, inline=False)
    await ctx.send(embed=embed)


@bot.command(name="clearwarnings")
@commands.has_permissions(kick_members=True)
async def clearwarnings(ctx, member: discord.Member):
    key = (ctx.guild.id, member.id)
    warnings.pop(key, None)
    await ctx.send(f"✅ Cleared all warnings for **{member}**.")


@bot.command(name="kick")
@commands.has_permissions(kick_members=True)
async def kick(ctx, member: discord.Member, *, reason: str = "No reason provided"):
    await member.kick(reason=reason)
    await ctx.send(f"👢 **{member}** has been kicked. Reason: {reason}")


@bot.command(name="ban")
@commands.has_permissions(ban_members=True)
async def ban(ctx, member: discord.Member, *, reason: str = "No reason provided"):
    await member.ban(reason=reason)
    await ctx.send(f"🔨 **{member}** has been permanently banned. Reason: {reason}")


@bot.command(name="tempban")
@commands.has_permissions(ban_members=True)
async def tempban(ctx, member: discord.Member, duration: int, unit: str = "m", *, reason: str = "No reason provided"):
    units = {"s": 1, "m": 60, "h": 3600, "d": 86400}
    if unit not in units:
        await ctx.send("Invalid time unit. Use `s` (seconds), `m` (minutes), `h` (hours), or `d` (days).")
        return
    seconds = duration * units[unit]
    await member.ban(reason=f"[Tempban] {reason}")
    await ctx.send(f"⏱️ **{member}** has been banned for **{duration}{unit}**. Reason: {reason}")
    await asyncio.sleep(seconds)
    await ctx.guild.unban(member)
    await ctx.send(f"✅ **{member}**'s temporary ban has expired. They can rejoin.")


@bot.command(name="unban")
@commands.has_permissions(ban_members=True)
async def unban(ctx, *, target: str):
    banned = [entry async for entry in ctx.guild.bans()]
    match = None

    if target.isdigit():
        match = next((entry for entry in banned if entry.user.id == int(target)), None)
    else:
        target_lower = target.lower().lstrip("@")
        match = next(
            (entry for entry in banned
             if entry.user.name.lower() == target_lower
             or str(entry.user).lower() == target_lower),
            None
        )

    if match is None:
        await ctx.send(f"❌ No banned user found matching `{target}`.")
        return

    await ctx.guild.unban(match.user)
    await ctx.send(f"✅ **{match.user}** (ID: {match.user.id}) has been unbanned.")


@bot.command(name="banlist")
@commands.has_permissions(ban_members=True)
async def banlist(ctx):
    banned = [entry async for entry in ctx.guild.bans()]
    if not banned:
        await ctx.send("No users are currently banned.")
        return
    embed = discord.Embed(title=f"🔨 Ban List — {len(banned)} user(s)", color=discord.Color.red())
    for entry in banned[:25]:
        embed.add_field(
            name=str(entry.user),
            value=f"ID: {entry.user.id}\nReason: {entry.reason or 'No reason provided'}",
            inline=False
        )
    if len(banned) > 25:
        embed.set_footer(text=f"Showing 25 of {len(banned)} banned users.")
    await ctx.send(embed=embed)


@bot.command(name="announce")
@commands.has_permissions(manage_messages=True)
async def announce(ctx, channel: discord.TextChannel, *, message: str):
    embed = discord.Embed(description=message, color=discord.Color.dark_blue())
    embed.set_author(name=ctx.guild.name, icon_url=ctx.guild.icon.url if ctx.guild.icon else None)
    embed.set_footer(text=f"Announced by {ctx.author.display_name}")
    await channel.send(embed=embed)
    await ctx.message.delete()



@bot.command(name="commands")
async def command_list(ctx):
    embed = discord.Embed(title="📋 Bot Commands", color=discord.Color.blurple())
    embed.add_field(name="General", value=(
        "`!ping` — Check latency\n"
        "`!hello` — Bot greets you\n"
        "`!userinfo [@user]` — Show user details\n"
        "`!serverinfo` — Show server details\n"
        "`!poll <question>` — Create a yes/no poll\n"
        "`!commands` — Show this list"
    ), inline=False)
    embed.add_field(name="Moderation", value=(
        "`!clear [1-100]` — Delete messages\n"
        "`!mute @user [dur] [s/m/h/d]` — Timeout a user\n"
        "`!unmute @user` — Remove timeout\n"
        "`!warn @user [reason]` — Warn a user\n"
        "`!warnings @user` — View user warnings\n"
        "`!clearwarnings @user` — Clear warnings\n"
        "`!kick @user [reason]` — Kick a user\n"
        "`!ban @user [reason]` — Permanently ban\n"
        "`!tempban @user [dur] [s/m/h/d]` — Timed ban\n"
        "`!unban <name or ID>` — Unban a user\n"
        "`!banlist` — Show all bans"
    ), inline=False)
    embed.add_field(name="Admin", value=(
        "`!announce #channel <msg>` — Post announcement\n"
        "`!restart` — Restart bot (owner only)"
    ), inline=False)
    await ctx.send(embed=embed)


@bot.command(name="ping")
async def ping(ctx):
    await ctx.send(f"Pong! Latency: {round(bot.latency * 1000)}ms")


@bot.command(name="hello")
async def hello(ctx):
    await ctx.send(f"Hello, {ctx.author.mention}!")


bot.run(os.environ["bot_token"])
