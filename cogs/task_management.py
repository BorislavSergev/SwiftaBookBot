import discord
from discord.ext import commands, tasks
from discord.ui import Button, View, Modal, InputText
from datetime import datetime
import json
import os

# Constants
TASKS_FILE_PATH = '../tasks.json'
COMPLETION_CHANNEL_ID = 1280127344245346367  # Replace with your actual completion channel ID

# Helper functions
def load_tasks():
    if not os.path.exists(TASKS_FILE_PATH):
        return {"tasks": []}
    with open(TASKS_FILE_PATH, 'r') as file:
        return json.load(file)

def save_tasks(data):
    with open(TASKS_FILE_PATH, 'w') as file:
        json.dump(data, file, indent=4)

# Task Management Cog
class TaskManagement(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.check_overdue_tasks.start()

    @commands.command()
    async def task(self, ctx, title: str, description: str, assignee: discord.Member, due: str):
        if not ctx.author.guild_permissions.administrator and "Staff" not in [role.name for role in ctx.author.roles]:
            await ctx.send("You do not have permission to use this command.")
            return

        try:
            due_time = datetime.strptime(due, "%H:%M:%S")
        except ValueError:
            await ctx.send("Invalid time format. Please use HH:MM:SS.")
            return

        # Create the task
        tasks_data = load_tasks()
        task_number = len(tasks_data['tasks']) + 1
        channel_name = f"{ctx.author.name}-{task_number}"

        category = discord.utils.get(ctx.guild.categories, name="Tasks")
        if not category:
            category = await ctx.guild.create_category("Tasks")

        overwrites = {
            ctx.guild.default_role: discord.PermissionOverwrite(view_channel=False),
            ctx.author: discord.PermissionOverwrite(view_channel=True),
            assignee: discord.PermissionOverwrite(view_channel=True)
        }

        task_channel = await category.create_text_channel(channel_name, overwrites=overwrites)

        embed = discord.Embed(
            title=title,
            description=description,
            color=discord.Color.blue()
        )
        embed.add_field(name="Assigned to", value=assignee.mention)
        embed.add_field(name="Due", value=due)
        
        view = View()
        delete_button = Button(label="Delete", style=discord.ButtonStyle.danger, custom_id="delete_task")
        review_button = Button(label="Review", style=discord.ButtonStyle.primary, custom_id="review_task")
        view.add_item(delete_button)
        view.add_item(review_button)

        await task_channel.send(embed=embed, view=view)
        await ctx.send(f"Task '{title}' created and assigned to {assignee.mention}.")

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        if interaction.custom_id == "review_task":
            task_channel = interaction.channel
            embed = discord.Embed(
                title="Task Review Requested",
                description=f"{interaction.user.mention} has requested a review for this task.",
                color=discord.Color.yellow()
            )

            view = View()
            reassign_button = Button(label="Re-Assign", style=discord.ButtonStyle.secondary, custom_id="reassign_task")
            complete_button = Button(label="Complete", style=discord.ButtonStyle.success, custom_id="complete_task")
            view.add_item(reassign_button)
            view.add_item(complete_button)

            await task_channel.send(embed=embed, view=view)

        elif interaction.custom_id == "reason_overdue":
            modal = Modal(title="Overdue Reason")
            modal.add_item(InputText(label="Reason", style=discord.InputTextStyle.long))

            async def modal_callback(modal_interaction: discord.Interaction):
                reason = modal.children[0].value
                task_channel = interaction.channel

                embed = discord.Embed(
                    title="Reason for Overdue Task",
                    description=f"Reason provided: {reason}",
                    color=discord.Color.orange()
                )
                embed.add_field(name="Provided by", value=modal_interaction.user.mention)
                await task_channel.send(embed=embed)

                await modal_interaction.response.send_message(f"Reason submitted: {reason}", ephemeral=True)

            modal.callback = modal_callback
            await interaction.response.send_modal(modal)

        elif interaction.custom_id == "reassign_task":
            modal = Modal(title="Re-Assign Task")
            modal.add_item(InputText(label="Reason", style=discord.InputTextStyle.long))

            async def modal_callback(modal_interaction: discord.Interaction):
                reason = modal.children[0].value
                task_channel = interaction.channel

                embed = discord.Embed(
                    title="Task Re-Assigned",
                    description=f"Reason for reassigning the task: {reason}",
                    color=discord.Color.orange()
                )
                embed.add_field(name="Reassigned by", value=modal_interaction.user.mention)
                await task_channel.send(embed=embed)

                await modal_interaction.response.send_message(f"Task has been re-assigned for the following reason: {reason}", ephemeral=True)

            modal.callback = modal_callback
            await interaction.response.send_modal(modal)

        elif interaction.custom_id == "complete_task":
            tasks_data = load_tasks()
            for task in tasks_data['tasks']:
                if task['channel_id'] == interaction.channel.id:
                    task['status'] = "Completed"
                    completed_task = task
                    break
            save_tasks(tasks_data)

            completion_channel = self.bot.get_channel(COMPLETION_CHANNEL_ID)
            if completion_channel:
                embed = discord.Embed(
                    title="Task Completed",
                    description=f"The task '{completed_task['title']}' has been completed.",
                    color=discord.Color.green()
                )
                embed.add_field(name="Description", value=completed_task['description'])
                embed.add_field(name="Assigned to", value=f"<@{completed_task['assignee_id']}>")
                embed.add_field(name="Completed by", value=f"<@{interaction.user.id}>")
                embed.add_field(name="Completion Time", value=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                await completion_channel.send(embed=embed)

            await interaction.response.send_message("Task marked as completed.", ephemeral=True)
            await interaction.channel.delete()

    @tasks.loop(minutes=1)
    async def check_overdue_tasks(self):
        tasks_data = load_tasks()
        now = datetime.now()

        for task in tasks_data.get('tasks', []):
            if task.get('status') == 'Completed':
                continue
            
            try:
                due_time = datetime.strptime(task['due'], "%H:%M:%S").time()
                due_datetime = datetime.combine(now.date(), due_time)
            except ValueError:
                continue

            if now > due_datetime:
                task_channel = self.bot.get_channel(task['channel_id'])
                if task_channel:
                    embed = discord.Embed(
                        title="Task Overdue",
                        description=f"The task '{task['title']}' is overdue!",
                        color=discord.Color.red()
                    )
                    embed.add_field(name="Description", value=task['description'])
                    embed.add_field(name="Assigned to", value=f"<@{task['assignee_id']}>")
                    embed.add_field(name="Due", value=task['due'])

                    reason_button = Button(label="Submit Reason", style=discord.ButtonStyle.secondary, custom_id="reason_overdue")
                    await task_channel.send(embed=embed, view=View().add_item(reason_button))

    @check_overdue_tasks.before_loop
    async def before_check_overdue_tasks(self):
        await self.bot.wait_until_ready()

def setup(bot):
    bot.add_cog(TaskManagement(bot))
