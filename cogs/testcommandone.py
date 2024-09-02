import discord
from discord.commands import SlashCommandGroup, option, slash_command
from discord.ext import commands
from discord.ui import View, Select


class TestCommancOne(commands.Cog):
    def __init__(self, bot_: discord.Bot):
        self.bot = bot_

    @commands.slash_command(description="A normal slash command example")
    async def test(self, ctx: discord.ApplicationContext):
        embed = discord.Embed(
        title="My Amazing Embed",
        description="Embeds are super easy, barely an inconvenience.",
        color=discord.Colour.blurple(), # Pycord provides a class with default colors you can choose from
        )
        embed.add_field(name="A Normal Field", value="A really nice field with some information. **The description as well as the fields support markdown!**")

        embed.add_field(name="Inline Field 1", value="Inline Field 1", inline=True)
        embed.add_field(name="Inline Field 2", value="Inline Field 2", inline=True)
        embed.add_field(name="Inline Field 3", value="Inline Field 3", inline=True)
 
        embed.set_footer(text="Footer! No markdown here.") # footers can have icons too
        embed.set_author(name="Pycord Team", icon_url="https://example.com/link-to-my-image.png")
        embed.set_thumbnail(url="https://example.com/link-to-my-thumbnail.png")
        embed.set_image(url="https://example.com/link-to-my-banner.png")
 
        await ctx.respond("Hello! Here's a cool embed.", embed=embed) # Send the embed with some text

def setup(bot):
    bot.add_cog(TestCommancOne(bot))
