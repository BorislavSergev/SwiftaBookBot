import discord
from discord.ext import commands
import os
import asyncio
import speech_recognition as sr
from pydub import AudioSegment
from pydub.playback import play

class VoiceSupport(commands.Cog):
    def __init__(self, bot: discord.Bot):
        self.bot = bot
        self.audio_file = "voices/welcome.mp3"
        self.support_channels = {1279780845250416700, 987654321098765432}  # Replace with your actual channel IDs

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        if after.channel is None:
            return  # User left a channel, do nothing

        if after.channel.id in self.support_channels and not member.bot:
            if self.bot.voice_clients:
                for vc in self.bot.voice_clients:
                    if vc.guild == member.guild:
                        await vc.move_to(after.channel)
                        await self.play_audio_and_listen(vc)
                        return
            
            vc = await after.channel.connect()
            await self.play_audio_and_listen(vc)

    async def play_audio_and_listen(self, vc):
        # Explicitly specify the path to the FFmpeg executable
        ffmpeg_executable = "C:/ffmpeg-master-latest-win64-gpl/bin/ffmpeg.exe"  # Update this path
        audio_source = discord.FFmpegPCMAudio(self.audio_file, executable=ffmpeg_executable)
        vc.play(audio_source, after=lambda e: print(f'Player error: {e}') if e else None)

        # Wait for the audio to finish playing
        while vc.is_playing():
            await asyncio.sleep(1)

        # Start listening to user input
        await self.listen_for_speech(vc)

    async def listen_for_speech(self, vc):
        recognizer = sr.Recognizer()

        with sr.AudioFile(self.audio_file) as source:  # Replace with actual audio input from Discord
            print("Listening...")
            audio_data = recognizer.record(source)
            try:
                text = recognizer.recognize_google(audio_data)
                print(f"Recognized: {text}")
                await self.process_command(vc, text)
            except sr.UnknownValueError:
                print("Google Speech Recognition could not understand audio")
            except sr.RequestError as e:
                print(f"Could not request results from Google Speech Recognition service; {e}")

    async def process_command(self, vc, text):
        # Process the recognized text and respond accordingly
        if "hello" in text.lower():
            await vc.guild.text_channels[0].send("Hi there! How can I assist you today?")
        # Add more command processing as needed

    @commands.command()
    async def join(self, ctx: commands.Context):
        if ctx.author.voice:
            channel = ctx.author.voice.channel
            if not ctx.voice_client:
                await channel.connect()
                await ctx.send(f'Joined {channel}')
            else:
                await ctx.voice_client.move_to(channel)
                await ctx.send(f'Moved to {channel}')
        else:
            await ctx.send('You are not connected to a voice channel.')

    @commands.command()
    async def leave(self, ctx: commands.Context):
        if ctx.voice_client:
            await ctx.voice_client.disconnect()
            await ctx.send('Disconnected from the voice channel.')
        else:
            await ctx.send('I am not connected to any voice channel.')

def setup(bot: discord.Bot):
    bot.add_cog(VoiceSupport(bot))
