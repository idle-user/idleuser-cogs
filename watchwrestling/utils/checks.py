import discord
from discord.ext import commands


def confirm(author):
    def inner_check(ctx):
        return author == ctx.author and ctx.content.upper() in ["Y", "N"]

    return inner_check


def is_number(author):
    def inner_check(ctx):
        return author == ctx.author and ctx.content.isdigit()

    return inner_check
