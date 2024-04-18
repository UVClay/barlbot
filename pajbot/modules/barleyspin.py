import datetime
import logging
import random
from collections import Counter, namedtuple

import pajbot.exc
import pajbot.models
import pajbot.utils
from pajbot import utils
from pajbot.managers.handler import HandlerManager
from pajbot.models.command import Command, CommandExample
from pajbot.modules import BaseModule, ModuleSetting

log = logging.getLogger(__name__)

# pull_lol returns the: (bet_return, emotes)
#def pull_lol(**slotargs):
#    slot_options = []
#    for e in death_emotes:
#        slot_options += [e] * 2
#    for e in low_tier_emotes:
#        slot_options += [e] * 3
#    for e in high_tier_emotes:
#        slot_options += [e]
#
#    randomized_emotes = random.choices(slot_options, k=3)
#
#    # figure out results of these randomized emotes xd
#    bet_return = 0.0
#    result_msg = "won"
#
#    emote_counts = Counter(randomized_emotes)
#
#    for emote_name in emote_counts:
#        emote_count = emote_counts[emote_name]
#
#        if emote_count <= 1:
#            bet_return = 0.5
#            continue
#
#        if emote_count == 2:
#            # return money if death
#            if emote_name in death_emotes:
#                bet_return = 0.75
#            # small win
#            elif emote_name in low_tier_emotes:
#                bet_return += ltsw
#            else:
#                bet_return += htsw
#
#        if emote_count == 3:
#            # big win
#            if emote_name in death_emotes:
#                result_msg = "lost"
#                continue
#            elif emote_name in low_tier_emotes:
#                bet_return += ltbw
#            else:
#                result_msg = "jackpot"
#                bet_return += htbw
#
#    return bet_return, randomized_emotes, result_msg

class BarleySpinModule(BaseModule):
    ID = __name__.split(".")[-1]
    NAME = "Slot Machine (Barley Spins)"
    DESCRIPTION = "Barley version of the slot machine"
    CATEGORY = "Game"
    SETTINGS = [
        ModuleSetting(
            key="message_won",
            label="Won message | Available arguments: {bet}, {bet_return}, {points}, {user}, {emotes}, {result}",
            type="text",
            required=True,
            placeholder="▬[ {emotes} ]▬ | {result} bones paid out to {user}!",
            default="▬[ {emotes} ]▬ | {result} bones paid out to {user}!",
            constraints={"min_str_len": 10, "max_str_len": 400},
        ),
        ModuleSetting(
            key="message_jackpot",
            label="Jackpot message | Available arguments: {bet}, {points}, {user}, {emotes}",
            type="text",
            required=True,
            placeholder="▬[ {emotes} ]▬ | Big money! Big prizes! I love it! | {points} paid out to {user}!",
            default="▬[ {emotes} ]▬ | Big money! Big prizes! I love it! | {points} paid out to {user}!",
            constraints={"min_str_len": 10, "max_str_len": 400},
        ),
        ModuleSetting(
            key="message_lost",
            label="Lost message | Available arguments: {bet}, {points}, {user}, {emotes}",
            type="text",
            required=True,
            placeholder="▬[ {emotes} ]▬ | NO MONEY {user} barlMadden NO PRIZES barlMadden I HATE IT barl1 barl2",
            default="▬[ {emotes} ]▬ | NO MONEY {user} barlMadden NO PRIZES barlMadden I HATE IT barl1 barl2",
            constraints={"min_str_len": 10, "max_str_len": 400},
        ),
        ModuleSetting(
            key="message_hit",
            label="Hit message | Avaialble arguments: {bet}, {bet_return}, {points}, {user}, {emotes}, {result}",
            type="text",
            required=True,
            placeholder="▬[ {emotes} ]▬ | Woah! Mini jackpot! | {bet_return}x payout! | {result} bones paid out to {user}!",
            default="▬[ {emotes} ]▬ | Woah! Mini jackpot! | {bet_return}x payout! | {result} bones paid out to {user}!",
            constraints={"min_str_len": 10, "max_str_len": 400},
        ),
        ModuleSetting(
            key="death_tier_emotes",
            label="Negative emotes, space-separated.",
            type="text",
            required=True,
            placeholder="FeelsBadMan",
            default="FeelsBadMan",
            constraints={"min_str_len": 1, "max_str_len": 100},
        ),
        ModuleSetting(
            key="death_emote_rate",
            label="Negative emote appearance probability",
            type="float",
            required=True,
            placeholder=1,
            default=1,
            constraints={"fmin_value": 0, "fmax_value": 5},
        ),
        ModuleSetting(
            key="death_emote_payout",
            label="Negative emote payout",
            type="float",
            required=True,
            placeholder=0,
            default=0,
            constraints={"fmin_value": 0, "fmax_value": 5},
        ),
        ModuleSetting(
            key="bottom_tier_emotes",
            label="Bottom tier emotes, space-separated.",
            type="text",
            required=True,
            placeholder="BatChest",
            default="BatChest",
            constraints={"min_str_len": 1, "max_str_len": 100},
        ),
        ModuleSetting(
            key="bottom_emote_rate",
            label="Bottom tier emote appearance probability",
            type="float",
            required=True,
            placeholder=1,
            default=1,
            constraints={"fmin_value": 0, "fmax_value": 5},
        ),
        ModuleSetting(
            key="bottom_emote_payout",
            label="Bottom tier emote payout",
            type="float",
            required=True,
            placeholder=0.5,
            default=0.5,
            constraints={"fmin_value": 0, "fmax_value": 5},
        ),
        ModuleSetting(
            key="low_tier_emotes",
            label="Low tier emotes, space-separated.",
            type="text",
            required=True,
            placeholder="4Head",
            default="4Head",
            constraints={"min_str_len": 1, "max_str_len": 100},
        ),
        ModuleSetting(
            key="low_emote_rate",
            label="Low tier emote appearance probability",
            type="float",
            required=True,
            placeholder=1,
            default=1,
            constraints={"fmin_value": 0, "fmax_value": 5},
        ),
        ModuleSetting(
            key="low_emote_payout",
            label="Low tier emote payout",
            type="float",
            required=True,
            placeholder=1,
            default=1,
            constraints={"fmin_value": 0, "fmax_value": 5},
        ),
        ModuleSetting(
            key="mid_tier_emotes",
            label="Mid tier emotes, space-separated.",
            type="text",
            required=True,
            placeholder="NaM",
            default="NaM",
            constraints={"min_str_len": 1, "max_str_len": 100},
        ),
        ModuleSetting(
            key="mid_emote_rate",
            label="Mid tier emote appearance probability",
            type="float",
            required=True,
            placeholder=1,
            default=1,
            constraints={"fmin_value": 0, "fmax_value": 5},
        ),
        ModuleSetting(
            key="mid_emote_payout",
            label="Mid tier emote payout",
            type="float",
            required=True,
            placeholder=1.5,
            default=1.5,
            constraints={"fmin_value": 0, "fmax_value": 5},
        ),
        ModuleSetting(
            key="high_tier_emotes",
            label="High tier emotes, space-separated",
            type="text",
            required=True,
            placeholder="KKona",
            default="KKona",
            constraints={"min_str_len": 0, "max_str_len": 400},
        ),
        ModuleSetting(
            key="high_emote_rate",
            label="High tier emote appearance probability",
            type="float",
            required=True,
            placeholder=1,
            default=1,
            constraints={"fmin_value": 0, "fmax_value": 5},
        ),
        ModuleSetting(
            key="high_emote_payout",
            label="High tier emote payout",
            type="float",
            required=True,
            placeholder=2,
            default=2,
            constraints={"fmin_value": 0, "fmax_value": 5},
        ),
        ModuleSetting(
            key="god_tier_emotes",
            label="God tier emotes, space-separated.",
            type="text",
            required=True,
            placeholder="DansGame",
            default="DansGame",
            constraints={"min_str_len": 1, "max_str_len": 100},
        ),
        ModuleSetting(
            key="god_emote_rate",
            label="God tier emote appearance probability",
            type="float",
            required=True,
            placeholder=1,
            default=1,
            constraints={"fmin_value": 0, "fmax_value": 5},
        ),
        ModuleSetting(
            key="god_emote_payout",
            label="God tier emote payout",
            type="float",
            required=True,
            placeholder=3,
            default=3,
            constraints={"fmin_value": 0, "fmax_value": 5},
        ),
        ModuleSetting(
            key="giga_tier_emotes",
            label="Giga tier emotes, space-separated. (Tier only unlocked with profile upgrade).",
            type="text",
            required=True,
            placeholder="Kappa",
            default="Kappa",
            constraints={"min_str_len": 1, "max_str_len": 100},
        ),
        ModuleSetting(
            key="giga_emote_rate",
            label="Giga tier emote appearance probability",
            type="float",
            required=True,
            placeholder=1,
            default=1,
            constraints={"fmin_value": 0, "fmax_value": 5},
        ),
        ModuleSetting(
            key="giga_emote_payout",
            label="Giga tier emote payout",
            type="float",
            required=True,
            placeholder=5,
            default=5,
            constraints={"fmin_value": 0, "fmax_value": 5},
        ),
        ModuleSetting(
            key="online_global_cd",
            label="Global cooldown (seconds)",
            type="number",
            required=True,
            placeholder="",
            default=0,
            constraints={"min_value": 0, "max_value": 120},
        ),
        ModuleSetting(
            key="online_user_cd",
            label="Per-user cooldown (seconds)",
            type="number",
            required=True,
            placeholder="",
            default=300,
            constraints={"min_value": 0, "max_value": 600},
        ),
        ModuleSetting(
            key="min_bet",
            label="Minimum bet",
            type="number",
            required=True,
            placeholder="100",
            default=100,
            constraints={"min_value": 1, "max_value": 10000},
        ),
        ModuleSetting(
            key="max_bet",
            label="Maximum bet",
            type="number",
            required=True,
            placeholder="1000",
            default=1000,
            constraints={"min_value": 1, "max_value": 10000},
        ),
        ModuleSetting(
            key="can_execute_with_whisper",
            label="Allow users to use the module from whispers",
            type="boolean",
            required=True,
            default=False,
        ),
        ModuleSetting(
            key="min_show_points",
            label="Min points you need to win or lose (if options 3)",
            type="number",
            required=True,
            placeholder="",
            default=100,
            constraints={"min_value": 1, "max_value": 1000000},
        ),
    ]

    def __init__(self, bot):
        super().__init__(bot)
        self.last_sub = None
        self.output_buffer = ""
        self.output_buffer_args = []
        self.last_add = None

    def load_commands(self, **options):
        self.commands["spin"] = Command.raw_command(
            self.pull,
            delay_all=self.settings["online_global_cd"],
            delay_user=self.settings["online_user_cd"],
            description="play slot machine for points",
            can_execute_with_whisper=self.settings["can_execute_with_whisper"],
            examples=[
                CommandExample(
                    None,
                    "Slots for 150 points",
                    chat="user:!spin 150\n" "bot:▬[ barlAl ▬ barlGB ▬ barlAl ]▬ | 200 bones paid out to UVClay!",
                    description="Play a round of slots for 150 points",
                ).parse()
            ],
        )
        self.commands["smp"] = self.commands["spin"]


    def speen(self):
        """ Returns bet_return, randomized_emotes, result_msg """
        # TODO: add logic for giga spins once shop item is implemented
        Emote = namedtuple('Emote', ['emote', 'tier', 'payout'])

        emote_collection = []
        result_emotes = []
        randomized_emotes = []
        
        tiers = ['death', 'bottom', 'low', 'mid', 'high', 'god']

        for tier in tiers:
            n = 0
            while n < int(self.settings[tier+"_emote_rate"]):
                emote_collection.append(Emote(emote=self.settings[tier+"_tier_emotes"], 
                tier=tier, payout=self.settings[tier+"_emote_payout"]))
                n += 1


        rand1 = random.randint(0, len(emote_collection) - 1)
        rand2 = random.randint(0, len(emote_collection) - 1)
        rand3 = random.randint(0, len(emote_collection) - 1)

        result_emotes.append(emote_collection[rand1])
        result_emotes.append(emote_collection[rand2])
        result_emotes.append(emote_collection[rand3])

        if result_emotes[0].tier == result_emotes[1].tier == result_emotes[2].tier:
            if result_emotes[0].tier == "death":
                bet_return = 0
                result_msg = "lost"
            elif result_emotes[0].tier == "god":
                bet_return = 9
                result_msg = "jackpot"
            else:
                bet_return = (result_emotes[0].payout + result_emotes[1].payout + result_emotes[2].payout) * random.uniform(0.4, 0.8)
                result_msg = "hit"

        else:
            bet_return = (result_emotes[0].payout + result_emotes[1].payout + result_emotes[2].payout) * random.uniform(0.3, 0.7)
            result_msg = "won"

        for emote in result_emotes:
            randomized_emotes.append(emote.emote)

        return bet_return, randomized_emotes, result_msg


    def pull(self, bot, source, message, **rest):
        if message is None:
            return False

        bet = 0

        try:
            int(message)
        except ValueError:
            bet = 150
        else:
            msg_split = message.split(" ")
            try:
                bet = pajbot.utils.parse_points_amount(source, msg_split[0])
            except pajbot.exc.InvalidPointAmount as e:
                bot.whisper(source, str(e))
                return False

        if bet < self.settings["min_bet"]:
            bot.me(f"{source.name}: You have to bet at least {self.settings['min_bet']} bones! barlOk")
            return False
        elif bet > self.settings["max_bet"]:
            bot.me(f"{source.name}: You can only bet {self.settings['max_bet']} bones. barlOk")
            return False
        elif not source.can_afford(bet):
            bot.me(f"{source.name}: You only have {source.points} bones. barlOk")
            return False
        else:
            source.points -= bet

        bet_return, randomized_emotes, result_msg = self.speen()

        if bet_return > 0:
            points = int(round(bet * bet_return))
            source.points += points
        else:
            points = bet

        source.points += points

        arguments = {
            "bet_return": round(bet_return, 2),
            "bet": bet,
            "result": points,
            "user": source.name,
            "points": source.points,
            "win": points > 0,
            "emotes": " ▬ ".join(randomized_emotes),
        }

        if result_msg == "won":
            out_message = self.get_phrase("message_won", **arguments)
        elif result_msg == "lost":
            out_message = self.get_phrase("message_lost", **arguments)
        elif result_msg == "jackpot":
            out_message = self.get_phrase("message_jackpot", **arguments)
        elif result_msg == "hit":
            out_message = self.get_phrase("message_hit", ** arguments)
        
        bot.me(out_message)

        HandlerManager.trigger("on_slot_machine_finish", user=source, points=points)

    def on_tick(self, **rest):
        if self.output_buffer == "":
            return

    def enable(self, bot):
        HandlerManager.add_handler("on_tick", self.on_tick)

    def disable(self, bot):
        HandlerManager.remove_handler("on_tick", self.on_tick)
