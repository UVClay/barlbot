import logging

from pajbot.managers.db import DBManager
from pajbot.managers.redis import RedisManager
from pajbot.models.command import Command
from pajbot.models.user import User
from pajbot.modules import BaseModule, ModuleSetting
from pajbot.streamhelper import StreamHelper
from pajbot.utils import time_since

log = logging.getLogger(__name__)


class TopModule(BaseModule):
    ID = __name__.split(".")[-1]
    NAME = "Top commands"
    DESCRIPTION = "Commands that show the top X users of something or top X emotes"
    CATEGORY = "Feature"
    SETTINGS = [
        ModuleSetting(
            key="num_top",
            label="How many people we should list",
            type="number",
            required=True,
            placeholder="min 1, max 5",
            default=3,
            constraints={"min_value": 1, "max_value": 10},
        ),
        ModuleSetting(
            key="num_top_emotes",
            label="How many emotes we should list",
            type="number",
            required=True,
            placeholder="min 1, max 10",
            default=5,
            constraints={"min_value": 1, "max_value": 10},
        ),
        ModuleSetting(
            key="excluded_users",
            label="Excluded users, space separated.",
            type="text",
            required=True,
            placeholder="",
            default="",
            constraints={"min_str_len":0, "max_str_len": 100},
        ),
        ModuleSetting(
            key="enable_topchatters",
            label="Enable the !topchatters command (most messages)",
            type="boolean",
            required=True,
            default=False,
        ),
        ModuleSetting(
            key="enable_topwatchers",
            label="Enable the !topwatchers command (most time spent watching the stream)",
            type="boolean",
            required=True,
            default=False,
        ),
        ModuleSetting(
            key="enable_topoffline",
            label="Enable the !topoffline command (most time spent in offline chat)",
            type="boolean",
            required=True,
            default=False,
        ),
        ModuleSetting(
            key="enable_toppoints",
            label="Enable the !toppoints command (most points)",
            type="boolean",
            required=True,
            default=False,
        ),
        ModuleSetting(
            key="enable_topemotes",
            label="Enable the !topemotes command (top used emotes)",
            type="boolean",
            required=True,
            default=False,
        ),
    ]


    def top_chatters(self, bot, **rest):
        data = []
        excluded_users = self.settings["excluded_users"].lower().split()
        limit = int(self.settings["num_top"]) + len(excluded_users)
        with DBManager.create_session_scope() as db_session:
            count = 1
            while count < int(self.settings["num_top"]):
                for user in db_session.query(User).order_by(User.num_lines.desc()).limit(limit):
                    if user.name.lower() not in excluded_users:
                        data.append(f"{user} ({user.num_lines})")
                        count += 1

        bot.say(f"Top {self.settings['num_top']} chatters: {', '.join(data)}")

    def top_watchers(self, bot, **rest):
        data = []
        excluded_users = self.settings["excluded_users"].lower().split()
        limit = int(self.settings["num_top"]) + len(excluded_users)
        with DBManager.create_session_scope() as db_session:
            count = 1
            while count < int(self.settings["num_top"]):
                for user in (
                  db_session.query(User).order_by(User.time_in_chat_online.desc()).limit(limit)
                ):
                    if user.name.lower() not in excluded_users:
                        data.append(f"{user} ({time_since(user.time_in_chat_online.total_seconds(), 0, time_format='short')})")
                        count += 1

        bot.say(f"Top {self.settings['num_top']} watchers: {', '.join(data)}")

    def top_offline(self, bot, **rest):
        data = []
        excluded_users = self.settings["excluded_users"].lower().split()
        limit = int(self.settings["num_top"]) + len(excluded_users)
        with DBManager.create_session_scope() as db_session:
            count = 1
            while count < self.settings["num_top"]:
                for user in (
                    db_session.query(User).order_by(User.time_in_chat_offline.desc()).limit(limit)
                ):
                    if user.name.lower() not in excluded_users:
                        data.append(f"{user} ({time_since(user.time_in_chat_offline.total_seconds(), 0, time_format='short')})")
                        count += 1

        bot.say(f"Top {self.settings['num_top']} offline chatters: {', '.join(data)}")

    def top_points(self, bot, **rest):
        data = []
        excluded_users = self.settings["excluded_users"].lower().split()
        limit = int(self.settings["num_top"]) + len(excluded_users)
        with DBManager.create_session_scope() as db_session:
            count = 1
            while count < self.settings["num_top"]:
                for user in db_session.query(User).order_by(User.points.desc()).limit(limit):
                    if user.name.lower() not in excluded_users:
                        data.append(f"{user} ({user.points})")
                        count += 1

        bot.say(f"Top {self.settings['num_top']} banks: {', '.join(data)}")

    def top_emotes(self, bot, **rest):
        redis = RedisManager.get()
        streamer = StreamHelper.get_streamer()
        num_emotes = self.settings["num_top_emotes"]

        top_emotes = {
            emote: emote_count
            for emote, emote_count in sorted(
                redis.zscan_iter(f"{streamer}:emotes:count"), key=lambda e_ecount_pair: e_ecount_pair[1], reverse=True
            )[:num_emotes]
        }
        if top_emotes:
            top_list_str = ", ".join(f"{emote} ({emote_count:,.0f})" for emote, emote_count in top_emotes.items())
            bot.say(f"Top {num_emotes} emotes: {top_list_str}")
        else:
            bot.say("No emote data available")

    def load_commands(self, **options):
        if self.settings["enable_topchatters"]:
            self.commands["topchatters"] = Command.raw_command(
                self.top_chatters,
                description="list top 10 chatters",
                examples=[
                    CommandExample(
                        None,
                        "List top 10 chatters",
                        chat="user:!topchatters\n" "bot: Top 10 chatters: you (666), me (420)",
                        description="List the top 10 chatters"
                    ).parse()
                ],
            )

        if self.settings["enable_topwatchers"]:
            self.commands["topwatchers"] = Command.raw_command(
                self.top_watchers,
                description="list top 10 watchers",
                examples=[
                    CommandExample(
                        None,
                        "List top 10 watchers",
                        chat="user:!topwatchers\n" "bot: Top 10 watchers: you (66d6h), me (4d20h)",
                        description="List the top 10 watchers"
                    ).parse()
                ],
            )
            self.commands["hrs"] = Command.raw_command(
                self.top_watchers,
                description="list top 10 watchers",
                examples=[
                    CommandExample(
                        None,
                        "List top 10 watchers",
                        chat="user:!hrs\n" "bot: Top 10 watchers: you (66d6h), me (4d20h)",
                        description="List the top 10 watchers"
                    ).parse()
                ],
            )

        if self.settings["enable_topoffline"]:
            self.commands["topoffline"] = Command.raw_command(self.top_offline)

        if self.settings["enable_toppoints"]:
            self.commands["toppoints"] = Command.raw_command(
                self.top_points,
                description="list top 10 banks",
                examples=[
                    CommandExample(
                        None,
                        "List top 10 bank balances",
                        chat="user:!toppoints\n" "bot: Top 10 banks: you (666), me (420)",
                        description="List the top 10 bank balances"
                    ).parse()
                ],
            )
            self.commands["top10"] = Command.raw_command(
                self.top_points,
                description="list top 10 banks",
                examples=[
                    CommandExample(
                        None,
                        "List top 10 bank balances",
                        chat="user:!top10\n" "bot: Top 10 banks: you (666), me (420)",
                        description="List the top 10 banks"
                    ).parse()
                ],
            )

        if self.settings["enable_topemotes"]:
            self.commands["topemotes"] = Command.raw_command(
                self.top_emotes,
                description="list top 10 emotes",
                examples=[
                    CommandExample(
                        None,
                        "List top 10 emotes",
                        chat="user:!topemotes\n" "bot: Top 10 emotes: barlSaad (1337), barlGB (666), CiGrip (420)",
                        description="List the top 10 emotes"
                    ).parse()
                ],
            )
