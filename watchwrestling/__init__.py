from .matches import Matches


def setup(bot):
    bot.add_cog(Matches(bot))
