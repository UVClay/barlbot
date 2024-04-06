import logging
import random

from pajbot.models.command import Command, CommandExample
from pajbot.modules import BaseModule, ModuleSetting
from pajbot.modules.basic import BasicCommandsModule
from pajbot.modules.linkchecker import find_unique_urls

log = logging.getLogger(__name__)


class CoinFlipModule(BaseModule):
    ID = __name__.split(".")[-1]
    NAME = "Coin Flip"
    DESCRIPTION = "flip a coin xd"
    CATEGORY = "Feature"
    PARENT_MODULE = BasicCommandsModule
    SETTINGS = [
        ModuleSetting(
            key="global_cd",
            label="Global cooldown (seconds)",
            type="number",
            required=True,
            placeholder="",
            default=15,
            constraints={"min_value": 0, "max_value": 240},
        ),
        ModuleSetting(
            key="user_cd",
            label="Per-user cooldown (seconds)",
            type="number",
            required=True,
            placeholder="",
            default=30,
            constraints={"min_value": 0, "max_value": 240},
        ),
    ]

    @staticmethod
    def flip(bot, source, message, **rest):
        # TODO: add emote support later
        #if not message:
        #    return False

        lolw = random.randint(0, 1)
        # TODO: add strings to module settings
        if lolw == 0:
            bot.say(f"{source} flips a coin and it lands on heads FrankerZ")
        else:
            bot.say(f"{source} flips a coin and it lands on tails ZreknarF")

    def load_commands(self, **options):
        self.commands["flip"] = Command.raw_command(
            self.flip,
            delay_all=self.settings["global_cd"],
            delay_user=self.settings["user_cd"],
            description="Flip a coin",
            command="flip",
            examples=[
                CommandExample(
                    None,
                    "Flip a coin",
                    chat="user:!flip UVClay flips a coin and it lands on heads FrankerZ",
                    description="",
                ).parse(),
                CommandExample(
                    None,
                    "Flip a coin",
                    chat="user:!flip UVClay flips a coin and it lands on tails ZreknarF",
                    description="",
                ).parse(),
            ],
        )
