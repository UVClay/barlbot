import datetime
import logging
import random
from collections import Counter

import pajbot.exc
import pajbot.models
import pajbot.utils
from pajbot import utils
from pajbot.managers.handler import HandlerManager
from pajbot.models.command import Command, CommandExample
from pajbot.modules import BaseModule, ModuleSetting

log = logging.getLogger(__name__)

# pull_lol returns the: (bet_return, emotes)
def pull_lol(death_emotes, low_tier_emotes, high_tier_emotes, bet, house_edge, ltsw, htsw, ltbw, htbw):
    slot_options = []
    for e in death_emotes:
        slot_options += [e] * 2
    for e in low_tier_emotes:
        slot_options += [e] * 3
    for e in high_tier_emotes:
        slot_options += [e]

    randomized_emotes = random.choices(slot_options, k=3)

    # figure out results of these randomized emotes xd
    bet_return = 0.0
    result_msg = "won"

    emote_counts = Counter(randomized_emotes)

    for emote_name in emote_counts:
        emote_count = emote_counts[emote_name]

        # TODO: fix slot machine payouts

        if emote_count <= 1:
            bet_return = 0.5
            continue

        if emote_count == 2:
            # return money if death
            if emote_name in death_emotes:
                bet_return = 0.75
            # small win
            elif emote_name in low_tier_emotes:
                bet_return += ltsw
            else:
                bet_return += htsw

        if emote_count == 3:
            # big win
            if emote_name in death_emotes:
                result_msg = "lost"
                continue
            elif emote_name in low_tier_emotes:
                bet_return += ltbw
            else:
                result_msg = "jackpot"
                bet_return += htbw

    return bet_return, randomized_emotes, result_msg

class BarleySpinModule(BaseModule):
    ID = __name__.split(".")[-1]
    NAME = "Slot Machine (Barley Spins)"
    DESCRIPTION = "Barley version of the slot machine"
    CATEGORY = "Game"
    SETTINGS = [
        ModuleSetting(
            key="message_won",
            label="Won message | Available arguments: {bet}, {points}, {user}, {emotes}, {result}",
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
            key="death_emotes",
            label="Negative emotes, space-separated. Negative emtoes appear as often as high tier emotes, but reduce winnings to a 1:1 return or 0.",
            type="text",
            required=True,
            placeholder="FeelsWeirdMan",
            default="FeelsWeirdMan",
            constraints={"min_str_len": 0, "max_str_len": 400},
        ),
        ModuleSetting(
            key="low_tier_emotes",
            label="Low tier emotes, space-separated. Low-tier emote are 3 times as likely to appear as high tier emotes (they get 3 slots compared to high emotes 1 slot per roll)",
            type="text",
            required=True,
            placeholder="KKona 4Head NaM",
            default="KKona 4Head NaM",
            constraints={"min_str_len": 0, "max_str_len": 400},
        ),
        ModuleSetting(
            key="high_tier_emotes",
            label="High tier emotes, space-separated",
            type="text",
            required=True,
            placeholder="OpieOP EleGiggle",
            default="OpieOP EleGiggle",
            constraints={"min_str_len": 0, "max_str_len": 400},
        ),
        ModuleSetting(
            key="ltsw",
            label="Low tier small win (Percentage) 22.6% with 2 low 2 high",
            type="number",
            required=True,
            placeholder="",
            default=125,
            constraints={"min_value": 0, "max_value": 1000000},
        ),
        ModuleSetting(
            key="ltbw",
            label="Low tier big win (Percentage) 0.98% with 2 low 2 high",
            type="number",
            required=True,
            placeholder="",
            default=175,
            constraints={"min_value": 0, "max_value": 1000000},
        ),
        ModuleSetting(
            key="htsw",
            label="High tier small win (Percentage) 0.14% with 2 low 2 high",
            type="number",
            required=True,
            placeholder="",
            default=225,
            constraints={"min_value": 0, "max_value": 1000000},
        ),
        ModuleSetting(
            key="htbw",
            label="High tier big win (Percentage) 0.07% with 2 low 2 high",
            type="number",
            required=True,
            placeholder="",
            default=400,
            constraints={"min_value": 0, "max_value": 1000000},
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
            default=60,
            constraints={"min_value": 0, "max_value": 240},
        ),
        ModuleSetting(
            key="min_bet",
            label="Minimum bet",
            type="number",
            required=True,
            placeholder="",
            default=1,
            constraints={"min_value": 1, "max_value": 1000000},
        ),
        ModuleSetting(
            key="can_execute_with_whisper",
            label="Allow users to use the module from whispers",
            type="boolean",
            required=True,
            default=False,
        ),
        ModuleSetting(
            key="options_output",
            label="Result output options",
            type="options",
            required=True,
            default="1. Show results in chat",
            options=[
                "1. Show results in chat",
                "2. Show results in whispers",
                "3. Show results in chat if it's over X points else it will be whispered.",
            ],
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
                    chat="user:!spin 150\n" "bot:▬[ barlSaad ▬ barlSmile ▬ barlSaad ]▬ | 75.0 bones paid out to UVClay!",
                    description="Do a slot machine pull for 15 points",
                ).parse()
            ],
        )
        self.commands["smp"] = self.commands["spin"]

    def pull(self, bot, source, message, **rest):
        if message is None:
            return False


        death_emotes = self.settings["death_emotes"].split()
        low_tier_emotes = self.settings["low_tier_emotes"].split()
        high_tier_emotes = self.settings["high_tier_emotes"].split()

        if len(low_tier_emotes) == 0 or len(high_tier_emotes) == 0:
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

        if not source.can_afford(bet):
            bot.whisper(source, f"You don't have enough points to spin for {bet} points :(")
            return False

        if bet < self.settings["min_bet"]:
            bot.whisper(source, f"You have to bet at least {self.settings['min_bet']} point! :(")
            return False

        # how much of the users point they're expected to get back (basically how much the house yoinks)
        expected_return = 1.0

        ltsw = self.settings["ltsw"] / 100.0
        htsw = self.settings["htsw"] / 100.0
        ltbw = self.settings["ltbw"] / 100.0
        htbw = self.settings["htbw"] / 100.0

        bet_return, randomized_emotes, result_msg = pull_lol(
            death_emotes, low_tier_emotes, high_tier_emotes, bet, expected_return, ltsw, htsw, ltbw, htbw
        )

        # Calculating the result
        if bet_return <= 0.0:
            points = -bet
        else:
            points = round(bet * bet_return)

        source.points += points

        arguments = {
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
        else:
            out_message = "oh holky fuck uvclay fix it idiot"
        
        if self.settings["options_output"] == "1. Show results in chat":
            bot.me(out_message)
        if self.settings["options_output"] == "2. Show results in whispers":
            bot.whisper(source, out_message)
        if (
            self.settings["options_output"]
            == "3. Show results in chat if it's over X points else it will be whispered."
        ):
            if abs(points) >= self.settings["min_show_points"]:
                bot.me(out_message)
            else:
                bot.whisper(source, out_message)

        HandlerManager.trigger("on_slot_machine_finish", user=source, points=points)

    def on_tick(self, **rest):
        if self.output_buffer == "":
            return

        if self.last_add is None:
            return

        diff = utils.now() - self.last_add

        if diff.seconds > 3:
            self.flush_output_buffer()

    def flush_output_buffer(self):
        msg = self.output_buffer
        self.bot.me(msg)
        self.output_buffer = ""
        self.output_buffer_args = []

    def enable(self, bot):
        HandlerManager.add_handler("on_tick", self.on_tick)

    def disable(self, bot):
        HandlerManager.remove_handler("on_tick", self.on_tick)
