import discord
from discord.ext import commands
from discord.ui import Button, View
import configparser
import asyncio
import random

intents = discord.Intents.all()
bot = commands.Bot(command_prefix='!', intents=intents)
config = configparser.ConfigParser()

try:
    config.read('config.ini')
except configparser.Error as e:
    print(f"Error reading configuration file: {e}")
    exit(1)

try:
    token = config.get('Bot', 'Token')
    default_channel_id = int(config.get('Bot', 'Channel'))
except (configparser.NoSectionError, configparser.NoOptionError) as e:
    print(f"Error reading configuration options: {e}")
    exit(1)

class Player:
    def __init__(self, discord_id, name):
        self.discord_id = discord_id
        self.name = name
        self.level = 1
        self.experience = 0
        self.silver = 0
        self.health = 250
        self.max_health = 250

class Monster:
    def __init__(self, name, level):
        self.name = name
        self.level = level
        self.health = level * 20
        self.max_health = level * 20

class MyView(View):
    def __init__(self, author):
        super().__init__(timeout=None)
        self.author = author
        self.update_task = None
        self.player = Player(author.id, author.name)
        self.monsters_killed = 0
        self.monster = None
        self.hunting = False

    async def interaction_check(self, interaction: discord.Interaction):
        return interaction.user == self.author

    async def on_timeout(self):
        pass

    async def update_counter(self):
        self.hunting = True
        try:
            while self.hunting:
                await asyncio.sleep(2)
                if self.monster is None or self.monster.health <= 0:
                    if self.player.level >= 4:
                        await self.message.channel.send("You won!")
                        await self.stop()
                        return

                    self.monster = Monster(random.choice(["Rat", "Boar", "Goblin"]), self.player.level)
                    self.monsters_killed += 1
                    self.player.silver += 5 * self.player.level
                    self.player.experience += 10
                    if self.player.experience >= 100:
                        self.player.level += 1
                        self.player.experience = 0
                        self.player.health = self.player.max_health
                    await self.update_embed()

                else:
                    self.monster.health -= 5 * self.player.level
                    if self.monster.health > 0:
                        self.player.health -= 2 * self.monster.level
                    if self.player.health <= 0:
                        await self.message.channel.send("You have died.")
                        await self.stop()
                        return
                    await self.update_embed()

        except Exception as e:
            print(f"An error occurred during hunting: {e}")
            await self.stop()


    async def update_embed(self):
        embed = self.message.embeds[0]
        monster_name = "🐀" if self.monster.name == "Rat" else "🐗" if self.monster.name == "Boar" else "👺" if self.monster.name == "Goblin" else "?"
        embed.description = (
            "◻️◻️◻️◻️◻️◻️◻️◻️◻️◻️◻️◻️\n"
            f"◻️ㅤLevel: {self.player.level}\n"
            f"◻️ㅤExp: {self.player.experience}\n"
            f"◻️ㅤSilver: {self.player.silver}\n"
            f"◻️ㅤM/Killed: {self.monsters_killed}\n"
            f"◻️◻️◻️◻️◻️◻️◻️◻️◻️◻️◻️◻️\n"
            f"◻️ㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤ\n"
            f"◻️ㅤ👨❤️{self.player.health}ㅤ⚔️ㅤ{monster_name}❤️{self.monster.health if self.monster else 'None'}\n"
            f"◻️ㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤ\n"
            f"◻️◻️◻️◻️◻️◻️◻️◻️◻️◻️◻️◻️\n"
        )
        asyncio.ensure_future(self.message.edit(embed=embed))

    async def stop(self):
        self.hunting = False  
        if self.update_task:
            self.update_task.cancel()
            self.update_task = None
        for item in self.children:
            item.disabled = True
        asyncio.ensure_future(self.message.edit(view=self))

class StartHuntingButton(Button):
    def __init__(self, parent_view):
        super().__init__(style=discord.ButtonStyle.green, label='Start Hunting')
        self.parent_view = parent_view

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        if not self.parent_view.update_task:
            self.parent_view.hunting = True  
            self.parent_view.update_task = asyncio.create_task(self.parent_view.update_counter())
        for item in self.parent_view.children:
            if not isinstance(item, StartHuntingButton):
                item.disabled = True
        await self.parent_view.message.edit(view=self.parent_view)

@bot.event
async def on_ready():
    try:
        print(f"We have logged in as {bot.user}")
    except Exception as e:
        print(f"Error when logging in: {e}")

@bot.event
async def on_message(message):
    try:
        if message.channel.id != default_channel_id:
            return
        print(f"Message from {message.author}: {message.content}")
        await bot.process_commands(message)
    except discord.DiscordException as e:
        print(f"Error processing message: {e}")

@bot.command()
async def hunt(ctx):
    embed = discord.Embed(title="Hunting Game", description='Start the game by clicking the "Start Hunting" button.', color=0x00ff00)
    view = MyView(ctx.author)
    view.add_item(StartHuntingButton(parent_view=view))
    view.message = await ctx.send(content='Hello, welcome to the Hunting Game!', embed=embed, view=view)

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        await ctx.send("Sorry, I don't recognize that command.")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("You're missing some arguments for that command.")
    else:
        await ctx.send("An error occurred while processing your command.")
        print(f"An error occurred while handling command: {error}")

try:
    bot.run(token)
except discord.LoginFailure as e:
    print(f"Authentication error: {e}")
except discord.ConnectionClosed as e:
    print(f"Closed connection: {e}")