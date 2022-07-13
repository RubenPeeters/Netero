
from datetime import datetime
from cogs.owner import MY_GUILD
import discord
from discord.ext import commands
from discord import app_commands

# system information
import platform
import re
import uuid
import socket
import cpuinfo
import psutil

# utils
from .utils import time
from .utils.embed import FooterEmbed
from .views.button import TestButton


class Stats(commands.Cog):
    """Statistics about the bot and its usage."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot: commands.Bot = bot

    def get_bot_uptime(self, *, brief=False):
        return time.human_timedelta(self.bot.uptime, accuracy=None, brief=brief, suffix=False)

    @commands.hybrid_command(name="uptime")
    async def uptime(self, ctx):
        """Tells you how long the bot has been up for."""
        await ctx.reply(content=f'Uptime: **{self.get_bot_uptime()}**')

    # @commands.hybrid_command(name="ui", hidden=True)
    # async def ui(self, ctx):
    #     """Discord UI testing."""
    #     view = discord.ui.View()
    #     button = TestButton(self.bot)
    #     input = discord.ui.TextInput(label="Test input")
    #     options = discord.SelectOption(label='Test 1', value='test-1')
    #     select = discord.ui.Select(options=[options])
    #     view.add_item(button)
    #     # view.add_item(input)
    #     # view.add_item(select)
    #     await ctx.reply(content=f'Test message', view=view)

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


async def setup(bot):
    cog = Stats(bot)
    await bot.add_cog(cog)
