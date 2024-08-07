import discord

from random import randint, shuffle, choice

embed_color = discord.Color.from_rgb(145, 241, 61)

zap = ":zap:"


def make_embed(title, description="") -> discord.Embed:
    return discord.Embed(title=title, description=description, color=embed_color)


ALL_ITEMS = {
    "beer": ("Пиво", "Передёрните затвор. Извлекает текущий патрон."),
    "magnifier": ("Лупа", "Взгляните на текущий патрон в патроннике."),
    "medicine": ("Просроченное Лекарство", f"50% вероятность вернуть 2 {zap} или же потерять 1 {zap}."),
    "telephone": ("Одноразовый Телефон", "Таинственный голос откроет завесу будущего."),
    "inverter": ("Инвертор", "Меняет текущий патрон в патроннике на противоположный."),
    "adrenaline": ("Адреналин", "Украдите предмет и сразу же его используете."),
    "hacksaw": ("Ножовка", "Дробовик наносит 2 ед. урона."),
    "handcuffs": ("Наручники", "Противник пропускает следующий ход."),
    "cigarettes": ("Сигареты", f"Снимает стресс. Восстановите 1 {zap}.")}


class Player:
    def __init__(self, user, health=4):
        self.user: discord.Member = user
        self.health = health
        self.inventory = []
        self.has_handcuffs = False
        self.has_handcuffs_open = False

    def add_item(self, item_id):
        if len(self.inventory) < 8:
            self.inventory.append(item_id)
            return True
        else:
            return False

    def use_item(self, item_id: str):
        self.inventory.remove(item_id)


class Shots:
    shots_combinations = {
        2: ((1, 1),),
        3: ((1, 2),),
        4: ((1, 3), (2, 2)),
        5: ((3, 2), (2, 3)),
        6: ((3, 3), (2, 4)),
        7: ((3, 4), (4, 3)),
        8: ((4, 4), (3, 5)),
    }

    def __init__(self):
        shots_count = randint(2, 8)
        # False - blank shot, True - live shot
        shots_combination = \
            Shots.shots_combinations[shots_count][randint(0, len(Shots.shots_combinations[shots_count]) - 1)]
        self.shots = [True] * shots_combination[0] + [False] * shots_combination[1]
        shuffle(self.shots)

    def get_random_shot(self):  # Return random shot without first
        return (i := randint(1, len(self.shots) - 1)), self.shots[i]

    def current_shot(self):
        return self.shots[0]

    def get_shuffled(self):
        _list = self.shots.copy()
        shuffle(_list)
        return _list

    def shot(self):
        try:
            return self.shots[0]
        finally:
            self.shots = self.shots[1:]

    def has_shots(self):
        return len(self.shots) > 0


class Game:
    def __init__(self, first_player, second_player, current_player_index, health=4):
        self.max_health = health
        self.players: list[Player] = [Player(first_player, health), Player(second_player, health)]
        self.current_player_index = current_player_index
        self.current_player = self.players[self.current_player_index]
        self.other_player = self.players[abs(self.current_player_index - 1)]
        self.winner = None
        self.shots = None

        self.primary_step = False
        self.hacksaw_used = False
        self.adrenaline_used = False

    def player_health(self, player):
        if player.health < 0:
            player.health = 0
        if player.health > self.max_health:
            player.health = self.max_health
        return f"У игрока {player.user.mention} {player.health} {zap}"
        # f"{'разрядов' if player.health == 0 else 'разряд' if player.health == 1 else 'разряда'}")

    def players_health(self):
        return f"{self.player_health(self.players[0])}\n{self.player_health(self.players[1])}"

    def new_round(self):
        self.shots = Shots()
        items_amount = randint(2, 4)
        output = []
        for i in range(2):
            output.append(f"{self.players[i].user.mention} получил: ")
            items = []
            for _ in range(items_amount):
                item_id = choice(list(ALL_ITEMS.keys()))
                if self.players[i].add_item(item_id):
                    items.append(ALL_ITEMS[item_id][0])
            output[i] += ", ".join(items)
        return "\n".join(output)

    def next_step(self):
        output = ""
        self.other_player.has_handcuffs_open = False
        if self.other_player.has_handcuffs and self.primary_step:
            output += f"Из-за наручников игрок {self.other_player.user.mention} пропускает ход.\n\n"
            self.other_player.has_handcuffs = False
            self.other_player.has_handcuffs_open = True
        elif not self.primary_step:
            pass
        else:
            self.other_player = self.players[self.current_player_index]
            self.current_player_index = abs(self.current_player_index - 1)
            self.current_player = self.players[self.current_player_index]
        output += f"Ход игрока {self.current_player.user.mention}"
        self.adrenaline_used = False
        self.primary_step = False
        return output

    async def round_info(self, interaction: discord.Interaction):
        items = self.new_round()
        return await interaction.respond(embed=make_embed("Игра", f"Все патроны на раунд: "
                                                                  f"{', '.join(tuple((('заряженный' if shot else 'холостой') for shot in self.shots.get_shuffled())))}"
                                                                  f"\n\n{items}\n\n{self.players_health()}"))
