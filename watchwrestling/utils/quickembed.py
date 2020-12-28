import discord

color = {
    "None": 0x36393F,
    "red": 0xFF0000,
    "blue": 0x0080FF,
    "green": 0x80FF00,
    "white": 0xFFFFFF,
    "black": 0x000000,
    "orange": 0xFF8000,
    "yellow": 0xFFFF00,
}


def filler(embed, desc, footer, user):
    if user:
        if user.discord.bot:
            embed.set_author(name=desc, icon_url=user.discord.avatar_url)
        elif user.is_registered:
            embed.set_author(
                name="{0.discord.display_name} ({0.username})".format(user),
                icon_url=user.discord.avatar_url,
                url=user.url,
            )
        else:
            embed.set_author(name=user.discord, icon_url=user.discord.avatar_url)
            embed.set_footer(text="User not registered.")
        embed.description = desc
        if footer:
            embed.set_footer(text=footer)
    else:
        embed.set_author(name="Notification")

    embed.description = desc
    return embed


def general(desc, footer=None, user=None):
    embed = discord.Embed(color=color["blue"])
    embed = filler(embed=embed, desc=desc, footer=footer, user=user)
    return embed


def info(desc, footer=None, user=None):
    embed = discord.Embed(color=color["white"])
    embed = filler(embed=embed, desc=desc, footer=footer, user=user)
    return embed


def error(desc, footer=None, user=None):
    embed = discord.Embed(color=color["red"])
    embed = filler(embed=embed, desc=desc, footer=footer, user=user)
    return embed


def success(desc, footer=None, user=None):
    embed = discord.Embed(color=color["green"])
    embed = filler(embed=embed, desc=desc, footer=footer, user=user)
    return embed


def question(desc, footer=None, user=None):
    embed = discord.Embed(color=color["yellow"])
    embed = filler(embed=embed, desc=desc, footer=footer, user=user)
    return embed


def notice(desc, footer=None, user=None):
    embed = discord.Embed(color=color["orange"])
    embed = filler(embed=embed, desc=desc, footer=footer, user=user)
    return embed
