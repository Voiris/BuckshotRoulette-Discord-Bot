import os
from random import randint

import discord
from discord import ApplicationContext
from discord import ui
from dotenv import load_dotenv

from buckshot_roulette import Game, make_embed, ALL_ITEMS, zap

bot = discord.Bot(intents=discord.Intents.all())


# TODO: Наручники нельзя использовать, если они были использованы ранее *(на проверку)
async def step(game, interaction: discord.Interaction):
    # TODO: Исправить победу *(на проверку)
    if game.players[0].health <= 0:
        game.winner = game.players[1]
    elif game.players[1].health <= 0:
        game.winner = game.players[0]
    elif len(game.shots.shots) == 0:
        game_message = await game.round_info(interaction)
        embed = game_message.embeds[0].copy()
        embed.description += f"\n\n{game.next_step()}"
        await game_message.edit(embed=embed, view=MainStepView(game))
    elif game.adrenaline_used:
        inventory_view = InventoryView(game)
        description = "Предметы противника для использования:\n"
        for item_id in inventory_view.inventory_set:
            description += f"{ALL_ITEMS[item_id][0]} x{inventory_view.inventory.count(item_id)} ({ALL_ITEMS[item_id][1]})\n"
        await interaction.respond(embed=make_embed("Игра", description), view=inventory_view)
    else:
        await interaction.respond(embed=make_embed("Игра", game.next_step()), view=MainStepView(game))

    if game.winner is not None:
        await interaction.respond(embed=make_embed("Игра", f"{game.winner.user.mention} победил!"),
                                  view=RevengeView(game))


class StepView(ui.View):
    def __init__(self, user, second_user=None, messages=("Ход уже сделан!", "Сейчас не ваш ход!")):
        super().__init__()

        self.is_used = False
        self.user = user
        self.second_user = second_user
        self.messages = messages

    async def __callback_valid(self, interaction: discord.Interaction):
        if not self.is_used and (interaction.user.id == self.user.id or (
                self.second_user is not None and interaction.user.id == self.second_user.id)):
            self.is_used = True
            return True
        elif self.is_used and (self.messages[0] is not None):
            await interaction.respond(self.messages[0], ephemeral=True)
        else:
            await interaction.respond(self.messages[1], ephemeral=True)
        return False

    async def callback_valid(self, interaction: discord.Interaction):
        return await self.__callback_valid(interaction)


# noinspection PyUnusedLocal
class RevengeView(StepView):
    def __init__(self, game: Game):
        super().__init__(game.players[0].user, game.players[1].user, messages=(None, "Вы не участник этого матча!"))

        self.game = game

    @ui.button(label="Реванш")
    async def revenge_callback(self, button: ui.Button, interaction: discord.Interaction):
        if await self.callback_valid(interaction):
            receive_challenge_view = None
            if interaction.user.id == self.game.players[0].user.id:
                receive_challenge_view = ReceiveChallengeView(interaction.user, self.game.players[1].user,
                                                              self.game.max_health)
            elif interaction.user.id == self.game.players[1].user.id:
                receive_challenge_view = ReceiveChallengeView(interaction.user, self.game.players[0].user,
                                                              self.game.max_health)
            await interaction.respond(
                f"{receive_challenge_view.caused.mention}\n\n{receive_challenge_view.caller.mention} "
                f"отправил вам запрос на матч с количеством разрядов: {receive_challenge_view.health} {zap}",
                view=receive_challenge_view)
            await interaction.respond(f"Вы отправили {receive_challenge_view.caused.mention} запрос.", ephemeral=True)


# TODO: Исправить баг с максимальным количеством предметов *(на проверку)
class InventoryView(StepView):
    def __init__(self, game: Game):
        super().__init__(game.current_player.user)

        self.game = game

        # TODO: Адреналином нельзя взять адреналин *(на проверку)
        # TODO: Адреналин нельзя использовать если у противника нет предметов *(на проверку)
        self.adrenaline_used = self.game.adrenaline_used
        if self.game.adrenaline_used:
            self.inventory = self.game.other_player.inventory
            self.game.adrenaline_used = False
        else:
            self.inventory = self.game.current_player.inventory
        self.inventory_set = set(self.inventory)

        select_options = [
            discord.SelectOption(label="Отмена" + (" (адреналин не вернётся)" if self.adrenaline_used else ""),
                                 description="Отменить использование предмета", value="cancel")]

        for item_id in self.inventory_set:
            if not self.adrenaline_used or item_id != "adrenaline":
                select_options.append(
                    discord.SelectOption(label=ALL_ITEMS[item_id][0], description=ALL_ITEMS[item_id][1], value=item_id))

        select = ui.Select(placeholder="Предметы на выбор, либо отмена", min_values=1, max_values=1,
                           options=select_options)
        select.callback = self.select_callback

        self.children.append(select)

    async def select_callback(self, interaction: discord.Interaction):
        if await self.callback_valid(interaction):
            # noinspection PyUnresolvedReferences
            item_id = self.children[0].values[0]
            if item_id == "beer":
                await self.beer_callback(interaction)
            elif item_id == "magnifier":
                await self.magnifier_callback(interaction)
            elif item_id == "medicine":
                await self.medicine_callback(interaction)
            elif item_id == "telephone":
                await self.telephone_callback(interaction)
            elif item_id == "inverter":
                await self.inverter_callback(interaction)
            elif item_id == "adrenaline":
                await self.adrenaline_callback(interaction)
            elif item_id == "hacksaw":
                await self.hacksaw_callback(interaction)
            elif item_id == "handcuffs":
                await self.handcuffs_callback(interaction)
            elif item_id == "cigarettes":
                await self.cigarettes_callback(interaction)
            await step(self.game, interaction)

    def use_item(self, item_id: str):
        self.inventory.remove(item_id)

    async def beer_callback(self, interaction: discord.Interaction):
        self.use_item("beer")
        await interaction.respond(
            f"{self.game.current_player.user.mention} выбросил {'заряженный' if self.game.shots.shot() else 'холостой'} патрон.")

    async def magnifier_callback(self, interaction: discord.Interaction):
        self.use_item("magnifier")
        await interaction.respond(
            f"{self.game.current_player}.",
            ephemeral=True)
        await interaction.respond(
            f"Вы увидели, что в патроннике находится {'заряженный' if self.game.shots.current_shot() else 'холостой'} патрон.",
            ephemeral=True)

    async def medicine_callback(self, interaction: discord.Interaction):
        description = ""
        if bool(randint(0, 1)):
            last_health = self.game.current_player.health
            self.game.current_player.health += 2
            description += f"{self.game.current_player.user.mention} восстановил {self.game.current_player.health - last_health} {zap}."
        else:
            self.game.current_player.health -= 1
            if self.game.current_player.health == 0:
                self.game.winner = self.game.other_player
            description += f"{self.game.current_player.user.mention} потерял 1 {zap}."
        description += "\n\n" + self.game.players_health()
        self.use_item("medicine")
        await interaction.respond(embed=make_embed("Игра", description))

    async def telephone_callback(self, interaction: discord.Interaction):
        if len(self.game.shots.shots) > 1:
            shot = self.game.shots.get_random_shot()
            self.use_item("telephone")
            await interaction.respond(embed=make_embed(
                "Игра",
                f"Таинственный голос сказал, что {shot[0] + 1} патрон {'заряженный' if shot[1] else 'холостой'}."),
                ephemeral=True)
        else:
            await interaction.respond(
                embed=make_embed("Игра", "Вы не можете использовать телефон, когда в патроннике всего 1 патрон."),
                ephemeral=True)

    async def inverter_callback(self, interaction: discord.Interaction):
        self.game.shots.shots[0] = not self.game.shots.shots[0]
        self.use_item("inverter")
        await interaction.respond(
            f"{self.game.current_player.user.mention} поменял текущий патрон на противоположный.")

    async def adrenaline_callback(self, interaction: discord.Interaction):
        if self.game.adrenaline_used:
            await interaction.respond("Вы уже использовали адреналин.", ephemeral=True)
        elif len(self.game.other_player.inventory) == 0:
            await interaction.respond("Вы не можете использовать адреналин. У противника нет предметов.",
                                      ephemeral=True)
        else:
            self.game.adrenaline_used = True
            self.use_item("adrenaline")
            await interaction.respond(f"{self.game.current_player.user.mention} использовал адреналин.")

    async def hacksaw_callback(self, interaction: discord.Interaction):
        # TODO: Исправить ножовку *(на проверку)
        if self.game.hacksaw_used:
            await interaction.respond("Вы уже использовали ножовку.", ephemeral=True)
        else:
            self.game.hacksaw_used = True
            self.use_item("hacksaw")
            await interaction.respond(
                f"{self.game.current_player.user.mention} использовал ножовку, следующий выстрел нанесёт двойной урон.")

    async def handcuffs_callback(self, interaction: discord.Interaction):
        if self.game.other_player.has_handcuffs or self.game.other_player.has_handcuffs_open:
            await interaction.respond("Вы уже использовали наручники.", ephemeral=True)
        else:
            self.game.other_player.has_handcuffs = True
            self.use_item("handcuffs")
            await interaction.respond(f"{self.game.current_player.user.mention} использовал наручники, "
                                      f"{self.game.other_player.user.mention} пропускает следующий ход.")

    async def cigarettes_callback(self, interaction: discord.Interaction):
        last_health = self.game.current_player.health
        self.game.current_player.health += 1
        # TODO: Добавить Embed *(на проверку)
        # TODO: Исправить бесконечные сигареты *(на проверку)
        self.use_item("cigarettes")
        await interaction.respond(embed=make_embed(
            "Игра",
            f"{self.game.current_player.user.mention} восстановил {self.game.current_player.health - last_health} {zap}.\n\n{self.game.players_health()}"))


# noinspection PyUnusedLocal
class ShotgunView(StepView):
    def __init__(self, game: Game):
        super().__init__(game.current_player.user)

        self.game = game

    @ui.button(label="Выстрелить в противника")
    async def enemy_shot(self, button: ui.Button, interaction: discord.Interaction):
        if await self.callback_valid(interaction):
            if self.game.shots.shot():
                self.game.other_player.health -= 1 + int(self.game.hacksaw_used)
                await interaction.respond(embed=make_embed(
                    "Игра",
                    f"Выстрел в противника нанёс {self.game.other_player.user.mention} {1 + int(self.game.hacksaw_used)} урон\n\n{self.game.players_health()}"))
            else:
                await interaction.respond(embed=make_embed("Игра",
                                                           f"{self.game.current_player.user.mention} выстрелили в противника. Выстрел оказался холостым"))
            self.game.primary_step = True
            if self.game.hacksaw_used:
                self.game.hacksaw_used = False
            await step(game=self.game, interaction=interaction)

    @ui.button(label="Выстрелить в себя")
    async def self_shot(self, button: ui.Button, interaction: discord.Interaction):
        if await self.callback_valid(interaction):
            if self.game.shots.shot():
                self.game.current_player.health -= 1 + int(self.game.hacksaw_used)
                self.game.primary_step = True
                await interaction.respond(embed=make_embed(
                    "Игра",
                    f"Выстрел в себя нанёс {self.game.current_player.user.mention} {1 + int(self.game.hacksaw_used)} урон\n\n{self.game.players_health()}"))
            else:
                await interaction.respond(embed=make_embed("Игра",
                                                           f"{self.game.current_player.user.mention} выстрелили в себя. Выстрел оказался холостым"))
            if self.game.hacksaw_used:
                self.game.hacksaw_used = False
            await step(game=self.game, interaction=interaction)


# noinspection PyUnusedLocal
class MainStepView(StepView):
    def __init__(self, game: Game):
        super().__init__(game.current_player.user)

        self.game = game

        self.inventory_view = InventoryView(game)

        if len(self.inventory_view.inventory) == 0:
            self.children: list[ui.Button]
            for child in self.children:
                if child.label == "Использовать предмет":
                    child.disabled = True

    @ui.button(label="Взять дробовик")
    async def take_shotgun(self, button: ui.Button, interaction: discord.Interaction):
        if await self.callback_valid(interaction):
            await interaction.respond(embed=make_embed("Игра", "Выберите в кого стрелять"),
                                      view=ShotgunView(game=self.game))

    @ui.button(label="Использовать предмет")
    async def use_item(self, button: ui.Button, interaction: discord.Interaction):
        if await self.callback_valid(interaction):
            description = "Предметы для использования:\n"
            # TODO: Исправить повтор идентичных предметов *(на проверку)
            for item_id in self.inventory_view.inventory_set:
                description += f"{ALL_ITEMS[item_id][0]} x{self.inventory_view.inventory.count(item_id)} ({ALL_ITEMS[item_id][1]})\n"
            await interaction.respond(embed=make_embed("Игра", description), view=self.inventory_view)

    @ui.button(label="Посмотреть предметы противника")
    async def view_other_player_items(self, button: ui.Button, interaction: discord.Interaction):
        if await self.callback_valid(interaction):
            description = ""
            for item_id in set((inventory := self.game.other_player.inventory)):
                description += f"{ALL_ITEMS[item_id][0]} x{inventory.count(item_id)} ({ALL_ITEMS[item_id][1]})\n"
            if description == "":
                description = "У игрока нет предметов"
            await interaction.respond(
                embed=make_embed(f"Предметы игрока `{self.game.other_player.user.display_name}`", description))
            await step(self.game, interaction)


# noinspection PyUnusedLocal
class ReceiveChallengeView(StepView):
    def __init__(self, caller: discord.Member, caused: discord.Member, health: int):
        super().__init__(caused)
        self.caller = caller
        self.caused = caused
        self.health = health

    @ui.button(label="Принять вызов")
    async def receive_callback(self, button: ui.Button, interaction: discord.Interaction):
        if await self.callback_valid(interaction):
            await interaction.respond("Вы приняли вызов", ephemeral=True)
            game: Game = Game(self.caller, self.caused, randint(0, 1), self.health)
            game_message = await game.round_info(interaction)
            embed = game_message.embeds[0].copy()
            embed.description += f"\n\n{game.next_step()}"
            await game_message.edit(embed=embed, view=MainStepView(game))


@bot.slash_command(name_localizations={"ru": "вызов"})
async def challenge(ctx: ApplicationContext,
                    user: discord.Member = discord.Option(discord.Member, description="Ваш противник"),
                    health: int = discord.Option(int, default=4,
                                                 description=f"Максимальное и начальное количество разрядов")):
    if user.bot:
        await ctx.respond(f"Вы не можете отправить запрос боту.", ephemeral=True)
    elif health < 1:
        await ctx.respond(f"Количество разрядов не может быть меньше `1`.", ephemeral=True)
    else:
        await ctx.respond(
            f"{user.mention}\n\n{ctx.author.mention} отправил вам запрос на матч с количеством разрядов: {health} {zap}",
            view=ReceiveChallengeView(ctx.author, user, health))
        await ctx.respond(f"Вы отправили {user.mention} запрос.", ephemeral=True)


load_dotenv(".env")
bot.run(token=os.environ["TOKEN"])
