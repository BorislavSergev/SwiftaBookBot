import discord
from discord.ext import commands
from discord.ui import View, Button, Select
import random
import time
import json
import os

# Load config file
with open("config.json", "r", encoding="utf-8") as file:
    configData = json.load(file)

class TicketSystem(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.tickets_file = "tickets.json"
        self.existing_tickets = {}  # Initialize the existing_tickets attribute

    async def cog_load(self):
        """Load existing tickets from the file on bot start."""
        if os.path.exists(self.tickets_file):
            with open(self.tickets_file, "r", encoding="utf-8") as file:
                self.existing_tickets = json.load(file)
        else:
            self.existing_tickets = {}

    async def cog_unload(self):
        """Save tickets to file before the bot shuts down."""
        with open(self.tickets_file, "w", encoding="utf-8") as file:
            json.dump(self.existing_tickets, file, indent=4)

    @commands.slash_command(name='setup_ticket', description='Sets up the ticket system with a dropdown menu.')
    @commands.has_permissions(administrator=True)
    async def setup_ticket(self, ctx: discord.ApplicationContext):
        """Sets up the ticket system with a dropdown menu."""
        select = Select(
            placeholder='Select a reason for your ticket',
            options=[
                discord.SelectOption(label='Billing', value='billing'),
                discord.SelectOption(label='Account Issues', value='account_issues'),
                discord.SelectOption(label='Payment Issues', value='payment_issues')
            ]
        )

        async def select_callback(interaction: discord.Interaction):
            reason = select.values[0]
            await self.create_ticket_channel(interaction, reason)

        select.callback = select_callback

        embed = discord.Embed(
            title="Create a Ticket",
            description="Please select the reason for your ticket from the dropdown menu below."
        )

        view = View()
        view.add_item(select)

        await ctx.respond(embed=embed, view=view)

    async def create_ticket_channel(self, interaction: discord.Interaction, reason: str):
        """Create a ticket channel and send a welcome message."""
        guild = interaction.guild
        category = discord.utils.get(guild.categories, name="Tickets")
        if not category:
            category = await guild.create_category("Tickets")

        # Generate a unique identifier (timestamp + random number)
        unique_id = int(time.time()) + random.randint(100000, 999999)
        channel_name = f"{reason}-{unique_id}"

        if discord.utils.get(guild.channels, name=channel_name):
            await interaction.response.send_message(f"A ticket with the reason '{reason}' already exists.", ephemeral=True)
            return

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False, send_messages=False, attach_files=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True, attach_files=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, attach_files=True),
        }

        ticket_channel = await guild.create_text_channel(
            name=channel_name,
            category=category,
            overwrites=overwrites
        )

        embed = discord.Embed(
            title="Ticket Created",
            description=f"**Member:** {interaction.user.mention}\n**Reason for opening:** {reason}"
        )
        view = View()
        close_button = Button(style=discord.ButtonStyle.danger, label="Close Ticket")
        view.add_item(close_button)

        # Define the ID of the role that can close tickets
        allowed_role_id = int(configData["staff_role"])  # Ensure this is an integer

        async def close_ticket_callback(interaction: discord.Interaction):
            # Check if the user has the allowed role by ID
            has_permission = any(role.id == allowed_role_id for role in interaction.user.roles)
            if not has_permission:
                # Send a debug message with role IDs and user's roles
                role_ids = [role.id for role in interaction.user.roles]
                await interaction.response.send_message(
                    f"You do not have permission to close this ticket. Your roles: {role_ids}, Required role ID: {allowed_role_id}",
                    ephemeral=True
                )
                return

            # Acknowledge the user's request to close the ticket
            await interaction.response.defer(ephemeral=True)

            # Generate and send the transcript before deleting the channel
            transcript_embed = await self.generate_transcript(ticket_channel)
            transcript_channel = self.bot.get_channel(int(configData["transcript_channel"]))
            if transcript_channel:
                await transcript_channel.send(embed=transcript_embed)

            # Delete the channel after sending the transcript
            await ticket_channel.delete()
            del self.existing_tickets[ticket_channel.id]
            with open(self.tickets_file, "w", encoding="utf-8") as file:
                json.dump(self.existing_tickets, file, indent=4)

            # Follow up with the user after the channel has been deleted
            await interaction.followup.send("Ticket closed and channel deleted.", ephemeral=True)

        close_button.callback = close_ticket_callback

        # Save the ticket channel ID to the file
        self.existing_tickets[ticket_channel.id] = {
            'reason': reason,
            'channel_name': channel_name
        }
        with open(self.tickets_file, "w", encoding="utf-8") as file:
            json.dump(self.existing_tickets, file, indent=4)

        await ticket_channel.send(embed=embed, view=view)
        await interaction.response.send_message(f"Your ticket has been created: {ticket_channel.mention}", ephemeral=True)

    async def generate_transcript(self, channel: discord.TextChannel) -> discord.Embed:
        """Generate a transcript of the chat messages in a channel."""
        messages = await channel.history(limit=200).flatten()  # Adjust the limit as needed

        transcript_content = "\n".join([f"{msg.author}: {msg.content}" for msg in messages if msg.content])

        transcript_embed = discord.Embed(
            title="Ticket Transcript",
            description=transcript_content[:4096]  # Ensure the description doesn't exceed embed length limit
        )
        return transcript_embed

    @commands.Cog.listener()
    async def on_ready(self):
        """Check and restore state for existing tickets when the bot is ready."""
        for channel_id, ticket_info in self.existing_tickets.items():
            channel = self.bot.get_channel(channel_id)
            if channel and isinstance(channel, discord.TextChannel):
                # Re-create ticket embed and view if the channel still exists
                embed = discord.Embed(
                    title="Ticket Recovered",
                    description=f"**Reason for opening:** {ticket_info['reason']}"
                )
                view = View()
                close_button = Button(style=discord.ButtonStyle.danger, label="Close Ticket")
                view.add_item(close_button)
                close_button.callback = self.get_close_ticket_callback(channel_id, ticket_info['reason'])

                await channel.send(embed=embed, view=view)

    def get_close_ticket_callback(self, channel_id: int, reason: str):
        async def close_ticket_callback(interaction: discord.Interaction):
            # Check if the user has the allowed role by ID
            allowed_role_id = int(configData["staff_role"])  # Ensure this is an integer
            has_permission = any(role.id == allowed_role_id for role in interaction.user.roles)
            if not has_permission:
                # Send a debug message with role IDs and user's roles
                role_ids = [role.id for role in interaction.user.roles]
                await interaction.response.send_message(
                    f"You do not have permission to close this ticket. Your roles: {role_ids}, Required role ID: {allowed_role_id}",
                    ephemeral=True
                )
                return

            channel = self.bot.get_channel(channel_id)
            if channel and isinstance(channel, discord.TextChannel):
                # Acknowledge the user's request to close the ticket
                await interaction.response.defer(ephemeral=True)

                # Generate and send the transcript before deleting the channel
                transcript_embed = await self.generate_transcript(channel)
                transcript_channel = self.bot.get_channel(int(configData["transcript_channel"]))
                if transcript_channel:
                    await transcript_channel.send(embed=transcript_embed)

                # Delete the channel after sending the transcript
                await channel.delete()
                del self.existing_tickets[channel_id]
                with open(self.tickets_file, "w", encoding="utf-8") as file:
                    json.dump(self.existing_tickets, file, indent=4)

                # Follow up with the user after the channel has been deleted
                await interaction.followup.send("Ticket closed and channel deleted.", ephemeral=True)

        return close_ticket_callback

def setup(bot: commands.Bot):
    bot.add_cog(TicketSystem(bot))
