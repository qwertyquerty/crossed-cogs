#Standard Imports
import asyncio
import re

#Discord Imports
import discord

#Redbot Imports
from redbot.core import commands, checks, Config, utils
from redbot.core.utils.chat_formatting import box, pagify
from redbot.core.utils.menus import menu, DEFAULT_CONTROLS

__version__ = "0.0.5" #Working but needs optimization and actual features
__author__ = "Crossedfall"


BaseCog = getattr(commands, "Cog", object)

class PlusRep(BaseCog):
    def __init__(self, bot):
        self.upvote = "👍"
        self.downvote = "👎"
        self.bot = bot
        self.config = Config.get_conf(self, 3656823494, force_registration=True)

        default_guild = {
            "reputation": {},
            "reaction_channels": {}
        }

        self.config.register_guild(**default_guild)


    @commands.guild_only()
    @commands.group()
    async def plusrep(self, ctx):
        """
        PlusRep Commands
        """
        pass

    @commands.admin_or_permissions(administrator=True)
    @plusrep.command()
    async def channel(self, ctx, channel: discord.TextChannel):
        """
        Add/remove a channel from the bot's list of channels to monitor

        The bot will react to every message in this channel, so it's best to ensure that it's not a channel that has frequent discussions
        """
        try:
            channels = await self.config.guild(ctx.guild).reaction_channels()
            if channels.pop(f'{channel.id}', None) is not None:
                await self.config.guild(ctx.guild).reaction_channels.set(channels)
                await ctx.send(f"I will no longer monitor {channel.mention}.")
            else:
                channels[channel.id] = (channel.guild.id, channel.last_message_id)
                await self.config.guild(ctx.guild).reaction_channels.set(channels)
                await ctx.send(f"Understood! I will monitor {channel.mention} for new posts.")

        except(ValueError, TypeError, AttributeError):
            await ctx.send("There was a problem setting the channel. Please check your entry and try again!")
    
    @commands.admin_or_permissions(administrator=True)
    @plusrep.command()
    async def listchannels(self, ctx):
        """
        Generate a list of channels being monitored in the current guild
        """
        channels = await self.config.guild(ctx.guild).reaction_channels()
        msg = "I am currently monitoring: "

        if channels:
            for k in channels.keys():
                channel = discord.utils.get(ctx.guild.channels, id=int(k))
                if channel is not None:
                    msg += f"{channel.mention} "
        
        if msg is "I am currently monitoring: ":
            await ctx.send("I'm not monitoring any channels!")
        else:
            await ctx.send(msg)

    @plusrep.command()
    async def leaderboard(self, ctx):
        """
        Guild reputation leaderboard
        """
        rep = await self.config.guild(ctx.guild).reputation()
        message = await ctx.send("Populating leaderboard....")
        if not rep:
            await message.edit(content="Nobody has any reputation!")
            return
        else:
            sorted_data = sorted(rep.items(), key=lambda x: x[1], reverse=True)
            msg = "{name:33}{score:19}\n".format(name="Name", score="Rep")
            for i, user in enumerate(sorted_data):
                if user[1] == 0:
                    continue
                user_idx = i + 1
                user_obj = await self.bot.fetch_user(user[0])
                if user_obj == ctx.author:
                    name = f"{user_idx}. <<{user_obj.name}>>"
                else:
                    name = f"{user_idx}. {user_obj.name}"
                msg += f"{name:33}{user[1]}\n"
            
            page_list = []
            for page in pagify(msg, delims=["\n"], page_length=1000):
                embed = discord.Embed(
                    color=await ctx.embed_color(), description=(box(page, lang="md"))
                )
                page_list.append(embed)
            await message.edit(content=box(f"[Rep Leaderboard]", lang="ini"))
            await menu(ctx, page_list, DEFAULT_CONTROLS)
            ### Thank you Aik for the above https://github.com/aikaterna/aikaterna-cogs/blob/v3/trickortreat/trickortreat.py#L187 ###

    @commands.is_owner()
    @plusrep.command()
    async def clear(self, ctx):
        """
        Clears ALL rep. Do not use this unless you need to
        """
        await self.config.guild(ctx.guild).reputation.set({})
        await ctx.send("Cleared")
    
    @commands.is_owner()
    @plusrep.command()
    async def tallyrep(self, ctx):
        """
        Command to force a full recount of rep. This will be slow if there are a lot of messages to check
        """
        rep = {}
        channels = (await self.config.guild(ctx.guild).reaction_channels()).keys()
        msg = await ctx.send("Getting rep. This may take a while...")
        for channel in channels:
            try:
                channel = self.bot.get_channel(int(channel))
                async for message in channel.history():
                    if message.author.bot:
                        continue
                    if message.reactions:
                        for reaction in message.reactions:
                            reaction_users = await reaction.users().flatten()
                            if self.bot.user not in reaction_users:
                                continue
                            if str(reaction.emoji) == self.upvote:
                                if f'{message.author.id}' in rep:
                                    rep[f'{message.author.id}'] += reaction.count - 1
                                else:
                                    rep[f'{message.author.id}'] = 0
                                    rep[f'{message.author.id}'] += reaction.count - 1
                                if message.author in reaction_users:
                                    rep[f'{message.author.id}'] -= 1
                            elif str(reaction.emoji) == self.downvote:
                                if f'{message.author.id}' in rep:
                                    rep[f'{message.author.id}'] -= reaction.count - 1
                                    if rep[f'{message.author.id}'] <= 0:
                                        rep[f'{message.author.id}'] = 0
                                else:
                                    rep[f'{message.author.id}'] = 0
                                if message.author in reaction_users:
                                    rep[f'{message.author.id}'] -= 1
            except:
                continue

        await self.config.guild(ctx.guild).reputation.set(rep)
        await msg.edit(content="Rep updated!")                     

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author == self.bot.user:
            return
        if message.guild is None:
            return
        if message.author.bot is True:
            return
        
        url = re.findall(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\), ]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', message.content.lower())
        if not message.attachments and not url:
            return
        
        if f'{message.channel.id}' in (await self.config.guild(message.guild).reaction_channels()).keys():
            await message.add_reaction(self.upvote)
            await message.add_reaction(self.downvote)

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):     
        channel = self.bot.get_channel(id=payload.channel_id)
        try:
            guild = channel.guild
        except AttributeError:
            return
        try:
            message = await channel.fetch_message(id=payload.message_id)
        except AttributeError:
            message = await channel.get_message(id=payload.message_id)
        except discord.errors.NotFound:
            return
        if f'{channel.id}' not in ((await self.config.guild(message.guild).reaction_channels()).keys()):
            return
        member = guild.get_member(message.author.id)
        if message.author.bot:
            return
        if message.author.id == payload.user_id:
            return
        #### Thanks Trusty for the above https://github.com/TrustyJAID/Trusty-cogs/blob/master/starboard/starboard.py#L756 ####
        valid = True
        for reaction in message.reactions:
            reaction_users = await reaction.users().flatten()
            if self.bot.user not in reaction_users:
                valid = False
            else:
                valid = True
        if valid is False:
            return

        if self.upvote == str(payload.emoji):
            rep = await self.config.guild(message.guild).reputation()
            if f'{member.id}' in rep.keys():
                rep[f'{member.id}'] += 1
            else:
                rep[f'{member.id}'] = 1
        elif self.downvote == str(payload.emoji):
            rep = await self.config.guild(message.guild).reputation()
            if f'{member.id}' in rep.keys():
                if rep[f'{member.id}'] <= 0:
                    rep[f'{member.id}'] = 0
                else:
                    rep[f'{member.id}'] -= 1
            else:
                rep[f'{member.id}'] = 0
        else:
            return
        
        await self.config.guild(message.guild).reputation.set(rep)
    
    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload):
        channel = self.bot.get_channel(id=payload.channel_id)
        try:
            guild = channel.guild
        except AttributeError:
            return
        try:
            message = await channel.fetch_message(id=payload.message_id)
        except AttributeError:
            message = await channel.get_message(id=payload.message_id)
        except discord.errors.NotFound:
            return
        if f'{channel.id}' not in ((await self.config.guild(message.guild).reaction_channels()).keys()):
            return
        member = guild.get_member(message.author.id)
        if message.author.bot:
            return
        if message.author.id == payload.user_id:
            return
        #### Thanks Trusty for the above ####
        valid = True
        for reaction in message.reactions:
            reaction_users = await reaction.users().flatten()
            if self.bot.user not in reaction_users:
                valid = False
            else:
                valid = True
        if valid is False:
            return

        if self.upvote == str(payload.emoji):
            rep = await self.config.guild(message.guild).reputation()
            if f'{member.id}' in rep.keys():
                rep[f'{member.id}'] -= 1
            else:
                return
        elif self.downvote == str(payload.emoji):
            rep = await self.config.guild(message.guild).reputation()
            if f'{member.id}' in rep.keys():
                rep[f'{member.id}'] += 1
            else:
                return
        else:
            return
        
        await self.config.guild(message.guild).reputation.set(rep)