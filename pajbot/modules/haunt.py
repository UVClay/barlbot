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
            key="sabotage",
            label="Chance for one player to sabotage everyone else (chance * 0.01)%",
            type="number",
            required=True,
            placeholder="",
            default=5,
            constraints={"min_value": 0, "max_value": 10000},
        ),
        ModuleSetting(
            key="online_global_cd",
            label="Event cooldown (how long between !haunt in seconds)",
            type="number",
            required=True,
            placeholder="",
            default=900,
            constraints={"min_value": 1, "max_value": 3600},
            # XXX: CHANGE ME BACK
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
            default=90,
            constraints={"min_value": 5, "max_value": 3600},
        ),
        ModuleSetting(
            key="start_join_message",
            label="Message to announce when the first player joins | Available arguments: {user}, {bet}",
            type="text",
            required=True,
            default="{user} is going in the haunted house. barlS Join them with !haunt <bones>!",
            constraints={"min_str_len": 0, "max_str_len": 300},
        ),
        ModuleSetting(
            key="join_message",
            label="Message to announce when another player joins the game | Avaialble arguments: {user}, {bet}",
            type="text",
            required=True,
            default="{user} is in! barlGB",
            constraints={"min_str_len": 0, "max_str_len": 300},
        ),
        ModuleSetting(
            key="alert_message_when_live",
            label="Message to announce when the game is active again",
            type="text",
            required=True,
            default="Brave souls wanted! Count Charles is terrorizing the village of Liloleman. Type !haunt <bones> to embark on the quest to banish the Count in his Manor. barlGB",
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
        self.debug = True
        self.last_play = None
        self.loading = False
        self.players = {}
        self.output_buffer = ""
        self.output_buffer_args = []

    def load_commands(self, **options):
        self.commands["haunt"] = Command.raw_command(
            self.hauntjoin,
            delay_all=0,
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

    def get_random_message(self, messages):
        if len(messages) > 1:
            return messages[random.randint(0, (len(messages) - 1))]
        else:
            return messages[0]

    def haunt_results(self, bot):
        sabotagechange = self.settings["sabotage"] * 0.01
        pushchance = 100 - sabotagechange
        outcomes = ["sabotage", "push"]

        outcome = random.choices(outcomes, weights=(sabotagechange, pushchance), k=1)

        win_messages = [
            " narrowly escaped the haunt, their survival a testament to their courage. The town rewards them, but the Count's shadow looms darkly on the horizon... barlHype"
            ]

        loss_messages = [
            " found themselves cornered in the kitchen by the Count. Looks like 'hero' is on the menu tonight, boys! Better luck next time. barlFood",
            " thought they evaded the Count's grasp in his dungeons, instead, with a sickening crunch, they found themselves split in half by one of the many traps below. Ouch. barlSaad",
            " sought refuge in the library, good call! That was until the the shadows of the manor found new blood, dragging them into an endless, black abyss. Oof. barlGB",
            " hid under the bed in the master bedroom, unfortunate for them, that's where the giant trapdoor spider had made it's nest. Tough break. barlS",
            " sought refuge inside the greenhouse, however thorned vines quickly ensnare them, dragging them into the gaping maw of a behemoth sized Venus flytrap. Rough luck, indeed. barlGB"
        ]

        wipe_messages = [
            "The group faced the Count's manor united in purpose. But the darkness proved too powerful, claiming them all. Their valiant effort ended in tragedy, their names forever etched in Liloleman's lore. barlMadn"
        ]
    
        sabotage_messages = [
            "Upon entering the mansion, one of you felt an eerie sensation enveloping them as the Count's malevolent influence clouding over their mind. \
            Before they knew it, {PLAYER} was horrified to find themselves standing over the bloodied remains of their allies. \
            It's not all bad though, this grim turn of events meant they wouldn't need to share any of the reward. Enjoy, killer. barlMadn",
            "While the rest of the brave adventurers entered the manor, {PLAYER} claimed they would catch up with everyone in a moment. The door slams shut \
            and our adventurers find themselves trapped as their supposed compatriot sets fire to the house, killing everyone inside and taking the reward for themselves. \
            Enjoy the payout, traitor. barlSaad"
        ]

        jackpot_messages = [
            "All have emerged victorious! With unwavering dedication and courage, Count Charles has been banished from his haunted manor. Liloleman can finally breathe easy! For now... barlMadn"
        ]

        if not len(self.players) == 1:
            # Only trigger sabotage if more than 1 player
            if outcome[0] == "sabotage":
                keys = list(self.players)
                sus = keys[random.randint(0, len(self.players) - 1)]
                bot.me(self.get_random_message(sabotage_messages).replace("{PLAYER}", sus.name))
                suswinnings = 0
                for player in self.players:
                    suswinnings += self.players[player]
                    if player.name is not sus:
                        player.points -= self.players[player]
                        HandlerManager.trigger("on_haunt_finish", user=player, points=player.points)
                
                sus.points += suswinnings
                HandlerManager.trigger("on_haunt_finish", user=sus, points=sus.points)

                bot.me(self.get_random_message(wipe_messages))
        else:
            # Standard RNG for win loss
            winloss = []
            for player in self.players:
                winloss.append(random.randint(0,1))
            
            if not all(x == winloss[0] for x in winloss):
                # Check if everyone rolled the same for jackpot/group wipe
                i = 0
                winners = []
                losers = []
                for player in self.players:
                    if winloss[i]:
                        winners.append(player)
                    else:
                        losers.append(player)
                    i += 1

                winner_buffer = ""
                for winner in winners:
                    winner.points += self.players[winner] * 2
                    HandlerManager.trigger("on_haunt_finish", user=winner, points=winner.points)
                    winner_buffer += winner + " +(" + (self.players[winner] * 2) + ") "
                
                loser_buffer = ""
                for loser in losers:
                    log.debug(f"Loser = {loser.name} Points = -{self.players[loser]}")
                    loser.points -= self.players[loser]
                    loser_buffer += loser 

                bot.me("Winners: " + winner_buffer)
                bot.me("Losers: " + loser_buffer)

            else:
                # Jackpot
                if winloss[0]:
                    bot.me(self.get_random_message(jackpot_messages))
                    winner_buffer = ""
                    for player in self.players:
                        log.debug(f"Winner = {player.name} Points = {self.players[player] * 2}")
                        winner_buffer += winner + " +(" + (self.players[winner] * 2) + ") "
                        player.points += self.players[player] * 2
                        HandlerManager.trigger("on_haunt_finish", user=player, points=player.points)

                    bot.me(winner_buffer)

                else:
                # Group wipe
                    bot.me(self.get_random_message(wipe_messages))
                    loser_buffer = ""
                    for player in self.players:
                        log.debug(f"Loser = {loser.name} Points = -{self.players[loser]}")
                        player.points -= self.players[player]
                        loser_buffer += player.name + " -(" + self.players[player] + ")"
                        HandlerManager.trigger("on_haunt_finish", user=player, points=player.points)

                    bot.me(loser_buffer)

        self.last_play = utils.now()
        bot.execute_delayed(self.settings["online_global_cd"], bot.me, self.get_phrase("alert_message_when_live"))
        self.players = {} 
        self.loading = False

    def hauntjoin(self, bot, source, message, **rest):
        if not self.loading:
            if self.last_play is not None:
                playtime = utils.now() - self.last_play
                if playtime < datetime.timedelta(seconds=self.settings["online_global_cd"]):
                    # TODO: add string to module settings
                    remtime = str(datetime.timedelta(seconds=self.settings["online_global_cd"]) - playtime).split('.')[0]
                    bot.me("It's still light out! You need to wait " + remtime.split(':')[1] + ':' + remtime.split(':')[2] + " to enter the house again.")
                    return False
                else:
                    self.loading = True
        
        try:
            int(message)
        except ValueError:
            bot.me(source.name + ": You need to bet some bones to enter the house. barlOk")
            return False
        else:
            msg_split = message.split(" ")
            try:
                bet = pajbot.utils.parse_points_amount(source, msg_split[0])
            except pajbot.exc.InvalidPointAmount as e:
                bot.whisper(source, str(e))
                return False

        arguments = {
            "bet": bet,
            "user": source.name,
        }

        if not self.players:
            self.players[source] = bet
            out_message = self.get_phrase("start_join_message", **arguments)
            source.points -= bet
            bot.execute_delayed(self.settings["wait_time"], self.haunt_results, bot)

        else:
            self.players[source] = bet
            source.points -= bet
            out_message = self.get_phrase("join_message", **arguments)

        bot.me(out_message)        


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

