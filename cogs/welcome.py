import discord
from discord.ext import commands
import json

file = open("config.json", "r", encoding="utf-8")
configData = json.load(file)
class Welcome(commands.Cog):
    def __init__(self, bot_: discord.Bot):
        self.bot = bot_

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        # Replace ROLE_ID with the actual ID of the role you want to assign
        role_id = 1278665831093370882  # Replace with the ID of your desired role
        role = member.guild.get_role(role_id)
        await member.add_roles(role)
        
        if role:
            try:
                await member.add_roles(role)
                print(f"Assigned role {role.name} to {member.name}")
            except Exception as e:
                print(f"Failed to assign role: {e}")
        else:
            print(f"Role with ID {role_id} not found.")

def setup(bot):
    bot.add_cog(Welcome(bot))
