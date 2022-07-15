from __future__ import annotations
import asyncio
from collections import Counter
import re
import textwrap
import traceback
from typing import TYPE_CHECKING, Any, Optional, TypedDict
from typing_extensions import Annotated

from datetime import datetime, timezone

import asyncpg
import discord
from discord.ext import commands, tasks, menus

# system information
import platform
import cpuinfo
import psutil
import logging

# utils
from .utils import time, db
from .utils.embed import FooterEmbed

if TYPE_CHECKING:
    from .utils.context import Context


log = logging.getLogger(__name__)


class DataBatchEntry(TypedDict):
    guild: Optional[int]
    channel: int
    author: int
    used: str
    prefix: str
    command: str
    failed: bool


class GatewayHandler(logging.Handler):
    def __init__(self, cog: Stats):
        self.cog: Stats = cog
        super().__init__(logging.INFO)

    def filter(self, record: logging.LogRecord) -> bool:
        return record.name == 'discord.gateway' or 'Shard ID' in record.msg or 'Websocket closed ' in record.msg

    def emit(self, record: logging.LogRecord) -> None:
        self.cog.add_record(record)


class Commands(db.Table):
    id = db.PrimaryKeyColumn()

    guild_id = db.Column(db.Integer(big=True), index=True)
    channel_id = db.Column(db.Integer(big=True))
    author_id = db.Column(db.Integer(big=True), index=True)
    used = db.Column(db.Datetime, index=True)
    prefix = db.Column(db.String)
    command = db.Column(db.String, index=True)
    failed = db.Column(db.Boolean, index=True)


_INVITE_REGEX = re.compile(
    r'(?:https?:\/\/)?discord(?:\.gg|\.com|app\.com\/invite)?\/[A-Za-z0-9]+')


def censor_invite(obj: Any, *, _regex=_INVITE_REGEX) -> str:
    return _regex.sub('[censored-invite]', str(obj))


class Stats(commands.Cog):
    """Statistics about the bot and its usage."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot: commands.Bot = bot
        self.process = psutil.Process()
        self._batch_lock = asyncio.Lock()
        self._data_batch: list[DataBatchEntry] = []
        self.bulk_insert_loop.add_exception_type(
            asyncpg.PostgresConnectionError)
        self.bulk_insert_loop.start()
        self._gateway_queue = asyncio.Queue()
        self.gateway_worker.start()

    def get_bot_uptime(self, *, brief=False):
        return time.human_timedelta(self.bot.uptime, accuracy=None, brief=brief, suffix=False)

    def cog_unload(self):
        self.bulk_insert_loop.stop()
        self.gateway_worker.cancel()

    def add_record(self, record: logging.LogRecord) -> None:
        self._gateway_queue.put_nowait(record)

    def censor_object(self, obj: str | discord.abc.Snowflake) -> str:
        if not isinstance(obj, str) and obj.id in self.bot.blacklist:
            return '[censored]'
        return censor_invite(obj)

    async def notify_gateway_status(self, record: logging.LogRecord) -> None:
        attributes = {'INFO': '\N{INFORMATION SOURCE}',
                      'WARNING': '\N{WARNING SIGN}'}

        emoji = attributes.get(record.levelname, '\N{CROSS MARK}')
        dt = datetime.utcfromtimestamp(record.created)
        msg = textwrap.shorten(
            f'{emoji} [{time.format_dt(dt)}] `{record.message}`', width=1990)
        await self.webhook.send(msg, username='Gateway', avatar_url='https://i.imgur.com/4PnCKB3.png')

    async def bulk_insert(self) -> None:
        query = """INSERT INTO commands (guild_id, channel_id, author_id, used, prefix, command, failed)
                   SELECT x.guild, x.channel, x.author, x.used, x.prefix, x.command, x.failed
                   FROM jsonb_to_recordset($1::jsonb) AS
                   x(guild BIGINT, channel BIGINT, author BIGINT, used TIMESTAMP, prefix TEXT, command TEXT, failed BOOLEAN)
                """

        if self._data_batch:
            await self.bot.pool.execute(query, self._data_batch)
            total = len(self._data_batch)
            if total > 1:
                log.info('Registered %s commands to the database.', total)
            self._data_batch.clear()

    @discord.utils.cached_property
    def webhook(self) -> discord.Webhook:
        wh_id, wh_token = self.bot.config.stat_webhook
        hook = discord.Webhook.partial(
            id=wh_id, token=wh_token, session=self.bot.session)
        return hook

    @tasks.loop(seconds=10.0)
    async def bulk_insert_loop(self):
        async with self._batch_lock:
            await self.bulk_insert()

    @tasks.loop(seconds=0.0)
    async def gateway_worker(self):
        record = await self._gateway_queue.get()
        await self.notify_gateway_status(record)

    async def register_command(self, ctx: Context) -> None:
        if ctx.command is None:
            return

        command = ctx.command.qualified_name
        self.bot.command_stats[command] += 1
        message = ctx.message
        destination = None
        if ctx.guild is None:
            destination = 'Private Message'
            guild_id = None
        else:
            destination = f'#{message.channel} ({message.guild})'
            guild_id = ctx.guild.id

        log.info(
            f'{message.created_at}: {message.author} in {destination}: {message.content}')
        async with self._batch_lock:
            self._data_batch.append(
                {
                    'guild': guild_id,
                    'channel': ctx.channel.id,
                    'author': ctx.author.id,
                    'used': message.created_at.isoformat(),
                    'prefix': ctx.prefix,
                    'command': command,
                    'failed': ctx.command_failed,
                }
            )

    @commands.Cog.listener()
    async def on_command_completion(self, ctx: Context):
        await self.register_command(ctx)

    @commands.Cog.listener()
    async def on_command_error(self, ctx: Context, error: Exception) -> None:
        await self.register_command(ctx)
        if not isinstance(error, (commands.CommandInvokeError, commands.ConversionError)):
            return

        error = error.original
        if isinstance(error, (discord.Forbidden, discord.NotFound, menus.MenuError)):
            return

        e = discord.Embed(title='Command Error', colour=self.bot.color)
        e.add_field(name='Name', value=ctx.command.qualified_name)
        e.add_field(name='Author', value=f'{ctx.author} (ID: {ctx.author.id})')

        fmt = f'Channel: {ctx.channel} (ID: {ctx.channel.id})'
        if ctx.guild:
            fmt = f'{fmt}\nGuild: {ctx.guild} (ID: {ctx.guild.id})'

        e.add_field(name='Location', value=fmt, inline=False)
        e.add_field(name='Content', value=textwrap.shorten(
            ctx.message.content, width=512))

        exc = ''.join(traceback.format_exception(
            type(error), error, error.__traceback__, chain=False))
        e.description = f'```py\n{exc}\n```'
        e.timestamp = discord.utils.utcnow()
        await self.webhook.send(embed=e)

    @commands.hybrid_command(name="uptime")
    async def uptime(self, ctx):
        """Tells you how long the bot has been up for."""
        await ctx.reply(content=f'Uptime: **{self.get_bot_uptime()}**')

    @commands.hybrid_command(name="stats")
    async def stats(self, ctx):
        """Tells you information about the bot itself."""
        if hasattr(self.bot, 'waiting_embed'):
            message = await ctx.send(embed=self.bot.waiting_embed)
        else:
            message = await ctx.send(content='Just a moment...')
        try:
            embed = FooterEmbed(self.bot)

            # statistics
            total_members = sum(1 for _ in self.bot.get_all_members())
            total_online = len({m.id for m in self.bot.get_all_members(
            ) if m.status is not discord.Status.offline})
            total_unique = len(self.bot.users)

            voice_channels = []
            text_channels = []
            for guild in self.bot.guilds:
                voice_channels.extend(guild.voice_channels)
                text_channels.extend(guild.text_channels)

            text = len(text_channels)
            voice = len(voice_channels)
            payload = f'```fix\n{"Members":10}: {total_members}\n{"Channels":10}: {text + voice}\n{"Servers":10}: {str(len(self.bot.guilds) - len(self.bot.emote_servers))}\n{"Uptime":10}: {self.get_bot_uptime(brief=True)}```\n'
            embed.add_field(
                name=f'{"="*15} {"Discord information".center(20)} {"="*15}', value=payload)

            info_embeds = self.System_information()
            info_embeds.append(embed)
            await message.edit(content=None, embeds=info_embeds)
            # await ctx.send(embed=embed)
        except Exception as e:
            await ctx.reply('{}: {}'.format(type(e).__name__, e))

    def get_size(self, bytes, suffix="B"):
        """
        Scale bytes to its proper format
        e.g:
            1253656 => '1.20MB'
            1253656678 => '1.17GB'
        """
        factor = 1024
        for unit in ["", "K", "M", "G", "T", "P"]:
            if bytes < factor:
                return f"{bytes:.2f}{unit}{suffix}"
            bytes /= factor

    def System_information(self):
        system_embed = discord.Embed(color=self.bot.color)
        uname = platform.uname()
        system_payload = f"```fix\n"
        system_payload += f"{'System':10}: {uname.system}\n"
        system_payload += f"{'Node name':10}: {uname.node}\n"
        system_payload += f"{'Release':10}: {uname.release}\n"
        system_payload += f"{'Version':10}: {uname.version}\n"
        system_payload += f"{'Machine':10}: {uname.machine}\n"
        # system_payload += f"{'Processor':10}: {uname.processor}\n"
        system_payload += f"{'Processor':10}: {cpuinfo.get_cpu_info()['brand_raw']}\n"
        # system_payload += f"{'Ip-address':10}: {socket.gethostbyname(socket.gethostname())}\n"
        # system_payload += f"{'Mac-address':10}: {':'.join(re.findall('..', '%012x' % uuid.getnode()))}\n"
        boot_time_timestamp = psutil.boot_time()
        bt = datetime.fromtimestamp(boot_time_timestamp)
        system_payload += f"{'Boot Time':10}: {bt.year}/{bt.month}/{bt.day} {bt.hour}:{bt.minute}:{bt.second}"
        system_payload += f"```"
        system_embed.add_field(
            name=f'{"="*15} {"System Information".center(20)} {"="*15}', value=system_payload)
        # # Boot Time
        # boot_payload = f"```fix\n"
        # boot_time_timestamp = psutil.boot_time()
        # bt = datetime.fromtimestamp(boot_time_timestamp)
        # boot_payload += f"{'Boot Time':10}: {bt.year}/{bt.month}/{bt.day} {bt.hour}:{bt.minute}:{bt.second}"
        # boot_payload += f"```"
        # boot_embed = discord.Embed(color=self.bot.color)
        # boot_embed.add_field(
        #     name=f'{"="*15} {"Boot Time".center(20)} {"="*15}', value=boot_payload)

        # print CPU information
        cpu_embed = discord.Embed(color=self.bot.color)
        cpu_payload = f"```fix\n"
        # number of cores
        cpu_payload += f"{'Physical cores':10}: {psutil.cpu_count(logical=False)}\n"
        cpu_payload += f"{'Total cores':10}: {psutil.cpu_count(logical=True)}\n"
        # CPU frequencies
        cpufreq = psutil.cpu_freq()
        cpu_payload += f"{'Max Frequency':10}: {cpufreq.max:.2f}Mhz\n"
        cpu_payload += f"{'Min Frequency':10}: {cpufreq.min:.2f}Mhz\n"
        cpu_payload += f"{'Current Frequency':10}: {cpufreq.current:.2f}Mhz\n"
        # CPU usage
        cpu_payload += f"{'CPU Usage Per Core'}:\n"
        for i, percentage in enumerate(psutil.cpu_percent(percpu=True, interval=1)):
            cpu_payload += f"{f'Core {i}':10}: {percentage}%\n"
        cpu_payload += f"{'Total CPU Usage'}: {psutil.cpu_percent()}%\n"
        cpu_payload += f"```"
        cpu_embed.add_field(
            name=f'{"="*15} {"CPU Information".center(20)} {"="*15}', value=cpu_payload)

        # # Memory Information
        # print("="*15, "Memory Information", "="*15)
        # # get the memory details
        # svmem = psutil.virtual_memory()
        # print(f"Total: {self.get_size(svmem.total)}")
        # print(f"Available: {self.get_size(svmem.available)}")
        # print(f"Used: {self.get_size(svmem.used)}")
        # print(f"Percentage: {svmem.percent}%")

        # print("="*15, "SWAP", "="*15)
        # # get the swap memory details (if exists)
        # swap = psutil.swap_memory()
        # print(f"Total: {self.get_size(swap.total)}")
        # print(f"Free: {self.get_size(swap.free)}")
        # print(f"Used: {self.get_size(swap.used)}")
        # print(f"Percentage: {swap.percent}%")

        # # Disk Information
        # print("="*15, "Disk Information", "="*15)
        # print("Partitions and Usage:")
        # # get all disk partitions
        # partitions = psutil.disk_partitions()
        # for partition in partitions:
        #     print(f"=== Device: {partition.device} ===")
        #     print(f"  Mountpoint: {partition.mountpoint}")
        #     print(f"  File system type: {partition.fstype}")
        #     try:
        #         partition_usage = psutil.disk_usage(partition.mountpoint)
        #     except PermissionError:
        #         # this can be catched due to the disk that
        #         # isn't ready
        #         continue
        #     print(f"  Total Size: {self.get_size(partition_usage.total)}")
        #     print(f"  Used: {self.get_size(partition_usage.used)}")
        #     print(f"  Free: {self.get_size(partition_usage.free)}")
        #     print(f"  Percentage: {partition_usage.percent}%")
        # # get IO statistics since boot
        # disk_io = psutil.disk_io_counters()
        # print(f"Total read: {self.get_size(disk_io.read_bytes)}")
        # print(f"Total write: {self.get_size(disk_io.write_bytes)}")

        # # Network information
        # print("="*15, "Network Information", "="*15)
        # # get all network interfaces (virtual and physical)
        # if_addrs = psutil.net_if_addrs()
        # for interface_name, interface_addresses in if_addrs.items():
        #     for address in interface_addresses:
        #         print(f"=== Interface: {interface_name} ===")
        #         if str(address.family) == 'AddressFamily.AF_INET':
        #             print(f"  IP Address: {address.address}")
        #             print(f"  Netmask: {address.netmask}")
        #             print(f"  Broadcast IP: {address.broadcast}")
        #         elif str(address.family) == 'AddressFamily.AF_PACKET':
        #             print(f"  MAC Address: {address.address}")
        #             print(f"  Netmask: {address.netmask}")
        #             print(f"  Broadcast MAC: {address.broadcast}")
        # # get IO statistics since boot
        # net_io = psutil.net_io_counters()
        # print(f"Total Bytes Sent: {self.get_size(net_io.bytes_sent)}")
        # print(f"Total Bytes Received: {self.get_size(net_io.bytes_recv)}")
        return [system_embed, cpu_embed]

    @commands.hybrid_command(hidden=True)
    @commands.is_owner()
    async def commandstats(self, ctx: Context, limit: int = 20):
        """Shows command stats.
        Use a negative number for bottom instead of top.
        This is only for the current session.
        """
        counter = self.bot.command_stats
        width = len(max(counter, key=len))
        total = sum(counter.values())

        if limit > 0:
            common = counter.most_common(limit)
        else:
            common = counter.most_common()[limit:]

        output = '\n'.join(f'{k:<{width}}: {c}' for k, c in common)

        await ctx.send(f'```\n{output}\n```')

    @commands.hybrid_command(hidden=True)
    async def socketstats(self, ctx: Context):
        delta = discord.utils.utcnow() - self.bot.uptime
        minutes = delta.total_seconds() / 60
        total = sum(self.bot.socket_stats.values())
        cpm = total / minutes
        await ctx.send(f'{total} socket events observed ({cpm:.2f}/minute):\n{self.bot.socket_stats}')

    async def show_guild_stats(self, ctx, message) -> None:
        lookup = (
            '\N{FIRST PLACE MEDAL}',
            '\N{SECOND PLACE MEDAL}',
            '\N{THIRD PLACE MEDAL}',
            '\N{SPORTS MEDAL}',
            '\N{SPORTS MEDAL}',
        )
        embed = discord.Embed(title='Server Command Stats',
                              colour=self.bot.color)

        # total command uses
        query = "SELECT COUNT(*), MIN(used) FROM commands WHERE guild_id=$1;"
        # type: ignore
        count: tuple[int, datetime.datetime] = await ctx.db.fetchrow(query, ctx.guild.id)

        embed.description = f'{count[0]} commands used.'
        if count[1]:
            timestamp = count[1].replace(tzinfo=timezone.utc)
        else:
            timestamp = discord.utils.utcnow()
        embed.set_footer(
            text='Tracking command usage since').timestamp = timestamp

        query = """SELECT command,
                          COUNT(*) as "uses"
                   FROM commands
                   WHERE guild_id=$1
                   GROUP BY command
                   ORDER BY "uses" DESC
                   LIMIT 5;
                """
        records = await ctx.db.fetch(query, ctx.guild.id)
        value = (
            '\n'.join(f'{lookup[index]}: {command} ({uses} uses)' for (
                index, (command, uses)) in enumerate(records))
            or 'No Commands'
        )

        embed.add_field(name='Top Commands', value=value, inline=True)

        query = """SELECT command,
                          COUNT(*) as "uses"
                   FROM commands
                   WHERE guild_id=$1
                   AND used > (CURRENT_TIMESTAMP - INTERVAL '1 day')
                   GROUP BY command
                   ORDER BY "uses" DESC
                   LIMIT 5;
                """
        records = await ctx.db.fetch(query, ctx.guild.id)
        value = (
            '\n'.join(f'{lookup[index]}: {command} ({uses} uses)' for (
                index, (command, uses)) in enumerate(records))
            or 'No Commands.'
        )
        embed.add_field(name='Top Commands Today', value=value, inline=True)
        embed.add_field(name='\u200b', value='\u200b', inline=True)
        query = """SELECT author_id,
                          COUNT(*) AS "uses"
                   FROM commands
                   WHERE guild_id=$1
                   GROUP BY author_id
                   ORDER BY "uses" DESC
                   LIMIT 5;
                """
        records = await ctx.db.fetch(query, ctx.guild.id)

        value = (
            '\n'.join(
                f'{lookup[index]}: <@!{author_id}> ({uses} bot uses)' for (index, (author_id, uses)) in enumerate(records)
            )
            or 'No bot users.'
        )

        embed.add_field(name='Top Command Users', value=value, inline=True)
        query = """SELECT author_id,
                          COUNT(*) AS "uses"
                   FROM commands
                   WHERE guild_id=$1
                   AND used > (CURRENT_TIMESTAMP - INTERVAL '1 day')
                   GROUP BY author_id
                   ORDER BY "uses" DESC
                   LIMIT 5;
                """
        records = await ctx.db.fetch(query, ctx.guild.id)
        value = (
            '\n'.join(
                f'{lookup[index]}: <@!{author_id}> ({uses} bot uses)' for (index, (author_id, uses)) in enumerate(records)
            )
            or 'No command users.'
        )
        embed.add_field(name='Top Command Users Today',
                        value=value, inline=True)
        await message.edit(embed=embed, content=None)

    async def show_member_stats(self, ctx, member: discord.Member, message) -> None:
        lookup = (
            '\N{FIRST PLACE MEDAL}',
            '\N{SECOND PLACE MEDAL}',
            '\N{THIRD PLACE MEDAL}',
            '\N{SPORTS MEDAL}',
            '\N{SPORTS MEDAL}',
        )
        embed = discord.Embed(title='Command Stats', colour=member.colour)
        embed.set_author(name=str(member), icon_url=member.display_avatar.url)

        # total command uses
        query = "SELECT COUNT(*), MIN(used) FROM commands WHERE guild_id=$1 AND author_id=$2;"
        # type: ignore
        count: tuple[int, datetime.datetime] = await ctx.db.fetchrow(query, ctx.guild.id, member.id)
        embed.description = f'{count[0]} commands used.'
        if count[1]:
            timestamp = count[1].replace(tzinfo=timezone.utc)
        else:
            timestamp = discord.utils.utcnow()
        embed.set_footer(text='First command used').timestamp = timestamp

        query = """SELECT command,
                          COUNT(*) as "uses"
                   FROM commands
                   WHERE guild_id=$1 AND author_id=$2
                   GROUP BY command
                   ORDER BY "uses" DESC
                   LIMIT 5;
                """

        records = await ctx.db.fetch(query, ctx.guild.id, member.id)

        value = (
            '\n'.join(f'{lookup[index]}: {command} ({uses} uses)' for (
                index, (command, uses)) in enumerate(records))
            or 'No Commands'
        )
        embed.add_field(name='Most Used Commands', value=value, inline=False)

        query = """SELECT command,
                          COUNT(*) as "uses"
                   FROM commands
                   WHERE guild_id=$1
                   AND author_id=$2
                   AND used > (CURRENT_TIMESTAMP - INTERVAL '1 day')
                   GROUP BY command
                   ORDER BY "uses" DESC
                   LIMIT 5;
                """

        records = await ctx.db.fetch(query, ctx.guild.id, member.id)

        value = (
            '\n'.join(f'{lookup[index]}: {command} ({uses} uses)' for (
                index, (command, uses)) in enumerate(records))
            or 'No Commands'
        )

        embed.add_field(name='Most Used Commands Today',
                        value=value, inline=False)
        await message.edit(embed=embed, content=None)

    @commands.hybrid_command()
    @commands.guild_only()
    # @commands.cooldown(1, 30.0, type=commands.BucketType.member)
    async def usages(self, ctx, *, member: discord.Member = None):
        """Tells you command usage stats for the server or a member."""
        message = await ctx.send(content='Just a moment...')
        if member is None:
            await self.show_guild_stats(ctx, message)
        else:
            await self.show_member_stats(ctx, member, message)

    @commands.hybrid_group(invoke_without_command=False)
    @commands.guild_only()
    async def usage(self, ctx, *, member: discord.Member = None):
        """Tells you command usage stats for the server or a member."""
        return

    @usage.command(name='global')
    @commands.is_owner()
    async def stats_global(self, ctx: Context):
        """Global all time command statistics."""
        message = await ctx.send(content='Just a moment...')
        query = "SELECT COUNT(*) FROM commands;"
        total: tuple[int] = await ctx.db.fetchrow(query)  # type: ignore
        e = discord.Embed(title='Command Stats',
                          colour=self.bot.color)
        e.description = f'{total[0]} commands used.'

        lookup = (
            '\N{FIRST PLACE MEDAL}',
            '\N{SECOND PLACE MEDAL}',
            '\N{THIRD PLACE MEDAL}',
            '\N{SPORTS MEDAL}',
            '\N{SPORTS MEDAL}',
        )

        query = """SELECT command, COUNT(*) AS "uses"
                   FROM commands
                   GROUP BY command
                   ORDER BY "uses" DESC
                   LIMIT 5;
                """

        records = await ctx.db.fetch(query)
        value = '\n'.join(f'{lookup[index]}: {command} ({uses} uses)' for (
            index, (command, uses)) in enumerate(records))
        e.add_field(name='Top Commands', value=value, inline=False)

        query = """SELECT guild_id, COUNT(*) AS "uses"
                   FROM commands
                   GROUP BY guild_id
                   ORDER BY "uses" DESC
                   LIMIT 5;
                """
        records = await ctx.db.fetch(query)
        value = []
        for (index, (guild_id, uses)) in enumerate(records):
            if guild_id is None:
                guild = 'Private Message'
            else:
                guild = self.censor_object(self.bot.get_guild(
                    guild_id) or f'<Unknown {guild_id}>')

            emoji = lookup[index]
            value.append(f'{emoji}: {guild} ({uses} uses)')
        e.add_field(name='Top Guilds', value='\n'.join(value), inline=False)

        query = """SELECT author_id, COUNT(*) AS "uses"
                   FROM commands
                   GROUP BY author_id
                   ORDER BY "uses" DESC
                   LIMIT 5;
                """
        records = await ctx.db.fetch(query)
        value = []
        for (index, (author_id, uses)) in enumerate(records):
            user = self.censor_object(self.bot.get_user(
                author_id) or f'<Unknown {author_id}>')
            emoji = lookup[index]
            value.append(f'{emoji}: {user} ({uses} uses)')

        e.add_field(name='Top Users', value='\n'.join(value), inline=False)
        await message.edit(embed=e, content=None)

    @usage.command(name='today')
    @commands.is_owner()
    async def stats_today(self, ctx: Context):
        """Global command statistics for the day."""
        message = await ctx.send(content='Just a moment...')
        query = "SELECT failed, COUNT(*) FROM commands WHERE used > (CURRENT_TIMESTAMP - INTERVAL '1 day') GROUP BY failed;"
        total = await ctx.db.fetch(query)
        failed = 0
        success = 0
        question = 0
        for state, count in total:
            if state is False:
                success += count
            elif state is True:
                failed += count
            else:
                question += count

        e = discord.Embed(title='Last 24 Hour Command Stats',
                          colour=self.bot.color)
        e.description = (
            f'{failed + success + question} commands used today. '
            f'({success} succeeded, {failed} failed, {question} unknown)'
        )

        lookup = (
            '\N{FIRST PLACE MEDAL}',
            '\N{SECOND PLACE MEDAL}',
            '\N{THIRD PLACE MEDAL}',
            '\N{SPORTS MEDAL}',
            '\N{SPORTS MEDAL}',
        )

        query = """SELECT command, COUNT(*) AS "uses"
                   FROM commands
                   WHERE used > (CURRENT_TIMESTAMP - INTERVAL '1 day')
                   GROUP BY command
                   ORDER BY "uses" DESC
                   LIMIT 5;
                """

        records = await ctx.db.fetch(query)
        value = '\n'.join(f'{lookup[index]}: {command} ({uses} uses)' for (
            index, (command, uses)) in enumerate(records))
        e.add_field(name='Top Commands', value=value, inline=False)

        query = """SELECT guild_id, COUNT(*) AS "uses"
                   FROM commands
                   WHERE used > (CURRENT_TIMESTAMP - INTERVAL '1 day')
                   GROUP BY guild_id
                   ORDER BY "uses" DESC
                   LIMIT 5;
                """

        records = await ctx.db.fetch(query)
        value = []
        for (index, (guild_id, uses)) in enumerate(records):
            if guild_id is None:
                guild = 'Private Message'
            else:
                guild = self.censor_object(self.bot.get_guild(
                    guild_id) or f'<Unknown {guild_id}>')
            emoji = lookup[index]
            value.append(f'{emoji}: {guild} ({uses} uses)')

        e.add_field(name='Top Guilds', value='\n'.join(value), inline=False)

        query = """SELECT author_id, COUNT(*) AS "uses"
                   FROM commands
                   WHERE used > (CURRENT_TIMESTAMP - INTERVAL '1 day')
                   GROUP BY author_id
                   ORDER BY "uses" DESC
                   LIMIT 5;
                """

        records = await ctx.db.fetch(query)
        value = []
        for (index, (author_id, uses)) in enumerate(records):
            user = self.censor_object(self.bot.get_user(
                author_id) or f'<Unknown {author_id}>')
            emoji = lookup[index]
            value.append(f'{emoji}: {user} ({uses} uses)')

        e.add_field(name='Top Users', value='\n'.join(value), inline=False)
        await message.edit(embed=e, content=None)

    async def send_guild_stats(self, e: discord.Embed, guild: discord.Guild):
        e.add_field(name='Name', value=guild.name)
        e.add_field(name='ID', value=guild.id)
        e.add_field(name='Shard ID', value=guild.shard_id or 'N/A')
        e.add_field(
            name='Owner', value=f'{guild.owner} (ID: {guild.owner_id})')

        bots = sum(m.bot for m in guild.members)
        total = guild.member_count or 1
        e.add_field(name='Members', value=str(total))
        e.add_field(name='Bots', value=f'{bots} ({bots/total:.2%})')

        if guild.icon:
            e.set_thumbnail(url=guild.icon.url)

        if guild.me:
            e.timestamp = guild.me.joined_at

        await self.webhook.send(embed=e)


async def setup(bot):
    if not hasattr(bot, 'command_stats'):
        bot.command_stats = Counter()

    if not hasattr(bot, 'socket_stats'):
        bot.socket_stats = Counter()

    cog = Stats(bot)
    await bot.add_cog(cog)

    bot.gateway_handler = handler = GatewayHandler(cog)
    logging.getLogger().addHandler(handler)
