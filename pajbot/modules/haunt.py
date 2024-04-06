import datetime
import logging
import random
import math
from collections import Counter

import pajbot.exc
import pajbot.models
import pajbot.utils
from pajbot import utils
from pajbot.managers.handler import HandlerManager
from pajbot.models.command import Command, CommandExample
from pajbot.modules import BaseModule, ModuleSetting

log = logging.getLogger(__name__)

class HauntModule(BaseModule):
    ID = __name__.split(".")[-1]
    NAME = "Haunted House"
    DESCRIPTION = "Lets players try and survive in the haunted house for money and prizes"
    CATEGORY = "Game"
    SETTINGS = [
        ModuleSetting(
            key="payout_rate",
            label="Payout rate for winning (bet * rate)",
            type="number",
            required=True,
            placeholder=2,
            constraints={"min_value": 2, "max_value": 500},
        ),
        ModuleSetting(
            key="jackpot",
            label="Jackpot chance, all players survive (chance * 0.01)%",
            type="number",
            required=True,
            placeholder="",
            default=250,
            constraints={"min_value": 0, "max_value": 10000},
        ),
        ModuleSetting(
            key="wipeout",
            label="Total wipeout chance, all players die (chance * 0.01)%",
            type="number",
            required=True,
            placeholder="",
            default=400,
            constraints={"min_value": 0, "max_value": 10000},
        ),
        ModuleSetting(
            key="online_global_cd",
            label="Global cooldown (seconds)",
            type="number",
            required=True,
            placeholder="",
            default=900,
            constraints={"min_value": 300, "max_value": 3600},
        ),
        ModuleSetting(
            key="online_user_cd",
            label="Per-user cooldown (seconds)",
            type="number",
            required=True,
            placeholder="",
            default=30,
            constraints={"min_value": 0, "max_value": 240},
        ),
        ModuleSetting(
            key="min_bet",
            label="Minimum entry payment",
            type="number",
            required=True,
            placeholder="",
            default=1,
            constraints={"min_value": 1, "max_value": 1000000},
        ),
        ModuleSetting(
            key="wait_time",
            label="How long to wait to start the game after first entry (seconds)",
            type="number",
            required=True,
            placeholder="",
            default=60,
            constraints={"min_value": 5, "max_value": 3600},
        ),
        ModuleSetting(
            key="alert_message_when_live",
            label="Message to announce when the game is active again",
            type="text",
            required=True,
            default="Night has fallen. Do you have what it takes to survive? !haunt <points> to find out. barlGB",
            constraints={"min_str_len": 0, "max_str_len": 300},
        ),
        ModuleSetting(
            key="can_execute_with_whisper",
            label="Can execute with whisper",
            type="boolean",
            required=True,
            default=False,
        ),
    ]

    def __init__(self, bot):
        super().__init__(bot)
        self.last_play = None
        self.players = []
        self.output_buffer = ""
        self.output_buffer_args = []

    def load_commands(self, **options):
        self.commands["haunt"] = Command.raw_command(
            self.hauntlol,
            delay_all=self.settings["online_global_cd"],
            delay_user=self.settings["online_user_cd"],
            description="survive the haunted house",
            can_execute_with_whisper=self.settings["can_execute_with_whisper"],
            examples=[
                CommandExample(
                    None,
                    "Enter the haunted house for 150 point bet",
                    chat="user:!haunt 150\n" "bot:barley tripped on the stairs and died before he even got in and lost all his money LUL",
                    description="Bet 150 points that you can survive the haunted house",
                ).parse()
            ],
        )

    def hauntlol(self, bot, source, message, **rest):
        if self.last_play is not None:
            if utils.now() - self.last_play > datetime.timedelta(seconds=self.settings["wait_time"]):
                bot.me("It's still light out!  You need to wait " + datetime.timedelta(seconds=self.settings["wait_time"]) + " to enter the house")
                return False

        bot.me("DEBUG: " + source.name + " is in.")

        self.players.append(source)

        for player in self.players:
            bot.me("DEBUG: " + player.name)

        jackpotchance = self.settings["jackpot"] * 0.01
        wipechance = self.settings["wipeout"] * 0.01
        pushchance = 100 - (jackpotchance + wipechance)
        outcomes = ["jackpot", "wipeout", "push"]

        outcome = random.choices(outcomes, weights=(jackpotchance, wipechance, pushchance), k=1)
        bot.me("DEBUG: outcome: " + outcome[0])
        if outcome[0] == "jackpot":
            bot.me("everyone win :)")
        elif outcome[0] == "wipeout":
            bot.me("everyone lose :)")
        elif outcome[0] == "push":
            for player in self.players:
                if random.randint(0,1):
                    bot.me("DEBUG: " + player.name + " FUCKING DIED")
                else:
                    bot.me("DEBUG: " + player.name + " FUCKING LIVED")

        self.players = []

        bot.me("DEBUG: ok done :)")




#        if message is None:
#            bot.whisper(source, "I didn't recognize your bet! Usage: !slotmachine 150 to bet 150 points")
#            return False
#
#        low_tier_emotes = self.settings["low_tier_emotes"].split()
#        high_tier_emotes = self.settings["high_tier_emotes"].split()
#
#        if len(low_tier_emotes) == 0 or len(high_tier_emotes) == 0:
#            return False
#
#        msg_split = message.split(" ")
#        try:
#            bet = pajbot.utils.parse_points_amount(source, msg_split[0])
#        except pajbot.exc.InvalidPointAmount as e:
#            bot.whisper(source, str(e))
#            return False
#
#        if not source.can_afford(bet):
#            bot.whisper(source, f"You don't have enough points to do a slot machine pull for {bet} points :(")
#            return False
#
#        if bet < self.settings["min_bet"]:
#            bot.whisper(source, f"You have to bet at least {self.settings['min_bet']} point! :(")
#            return False
#
#        # how much of the users point they're expected to get back (basically how much the house yoinks)
#        expected_return = 1.0
#
#        ltsw = self.settings["ltsw"] / 100.0
#        htsw = self.settings["htsw"] / 100.0
#        ltbw = self.settings["ltbw"] / 100.0
#        htbw = self.settings["htbw"] / 100.0
#
#        bet_return, randomized_emotes = pull_lol(
#            low_tier_emotes, high_tier_emotes, bet, expected_return, ltsw, htsw, ltbw, htbw
#        )
#
#        # Calculating the result
#        if bet_return <= 0.0:
#            points = -bet
#        else:
#            points = bet * bet_return
#
#        source.points += points
#
#        arguments = {
#            "bet": bet,
#            "result": points,
#            "user": source.name,
#            "points": source.points,
#            "win": points > 0,
#            "emotes": " ".join(randomized_emotes),
#        }
#
#        if points > 0:
#            out_message = self.get_phrase("message_won", **arguments)
#        else:
#            out_message = self.get_phrase("message_lost", **arguments)
#
#        if self.settings["options_output"] == "4. Combine output in chat":
#            if bot.is_online:
#                self.add_message(bot, arguments)
#            else:
#                bot.me(out_message)
#        if self.settings["options_output"] == "1. Show results in chat":
#            bot.me(out_message)
#        if self.settings["options_output"] == "2. Show results in whispers":
#            bot.whisper(source, out_message)
#        if (
#            self.settings["options_output"]
#            == "3. Show results in chat if it's over X points else it will be whispered."
#        ):
#            if abs(points) >= self.settings["min_show_points"]:
#                bot.me(out_message)
#            else:
#                bot.whisper(source, out_message)
#
#        HandlerManager.trigger("on_slot_machine_finish", user=source, points=points)

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

