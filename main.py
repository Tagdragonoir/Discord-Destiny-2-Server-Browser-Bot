from lxml import html
import requests
import asyncio
import discord
from discord.ext import commands, tasks
import urllib.parse

HEADERS = {"X-API-Key": 'INSERT API KEY HERE'}
TOKEN = 'INSERT BOT TOKEN HERE'
bot = commands.Bot(command_prefix="--")


async def search_player_by_bungie_name_from_api(bungie_name):
    global HEADERS
    search_url = f"https://www.bungie.net/Platform/Destiny2/SearchDestinyPlayer/-1/{urllib.parse.quote(bungie_name)}/"
    res = requests.get(search_url, headers=HEADERS).json()
    member = res['Response'][0]

    return member['membershipType'], member['membershipId']


async def get_lobby_data_from_api(membership=()):
    global HEADERS
    get_profile_url = f"https://www.bungie.net/Platform/Destiny2/{membership[0]}/Profile/{membership[1]}/?components=1000"

    res = requests.get(get_profile_url, headers=HEADERS).json()

    # len(res['partyMembers']), len(res['partyMembers']) + res['joinability']['openSlots']
    return res['Response']['profileTransitoryData']['data']


class Lobby:
    def __init__(self, bungie_name, instigator_discord_id, voice_channel):
        self.leader_bungie_name = bungie_name
        self.instigator_discord_id = instigator_discord_id
        self.inactive_counter = 0
        self.max_inactivity_count = 5
        self.leader_membership = None
        try:
            int(voice_channel)
            self.voice_channel = f"<#{voice_channel}>"
        except:
            self.voice_channel = voice_channel

    async def display(self, called_by_auto_roster=False):
        lobby_data = await get_lobby_data_from_api(self.leader_membership)
        if called_by_auto_roster:
            if len(lobby_data['partyMembers']) == 1:
                self.inactive_counter += 1
                if self.inactive_counter == self.max_inactivity_count:
                    super.inactive.append(self.instigator_discord_id)
            else:
                self.inactive_counter = 0
        return f"{self.leader_bungie_name}\tCapacity: {len(lobby_data['partyMembers'])}/{len(lobby_data['partyMembers']) + lobby_data['joinability']['openSlots']}\tVoice Channel: {self.voice_channel}\tScore: {lobby_data['currentActivity']['score']} - {lobby_data['currentActivity']['highestOpposingFactionScore']}"

    async def leadership_transfer(self, new_leader_discord_id, new_leader_bungie_name):
        self.instigator_discord_id = new_leader_discord_id
        self.leader_bungie_name = new_leader_bungie_name
        await self.get_new_membership_data()

    async def get_new_membership_data(self):
        self.leader_membership = await search_player_by_bungie_name_from_api(self.leader_bungie_name)

    def __eq__(self, other):
        return self.leader_bungie_name == other.leader_bungie_name and self.instigator_discord_id == other.leader_bungie_name


class Roster:
    def __init__(self):
        self.lobbies = {}
        self.inactive = []

    async def add_lobby(self, bungie_name, instigator_discord_id, voice_channel):
        if instigator_discord_id in self.lobbies:
            return 'You already the leader of an active lobby, please close this lobby before opening a new one'
        try:
            await search_player_by_bungie_name_from_api(bungie_name)
        except Exception as e:
            return 'Unable to create a lobby, please ensure that you entered the correct bungie name and that your fireteam is in a joinable location'

        self.lobbies[instigator_discord_id] = Lobby(bungie_name, instigator_discord_id, voice_channel)
        await self.lobbies[instigator_discord_id].get_new_membership_data()
        return "Lobby successfully created"

    def remove_lobby(self, instigator_discord_id):
        if instigator_discord_id not in self.lobbies:
            return 'You do not currently leading any lobby'

        del self.lobbies[instigator_discord_id]
        return 'Lobby successfully closed'

    async def transfer_lobby(self, new_leader_discord_id, new_leader_bungie_name, instigator_discord_id):
        if instigator_discord_id not in self.lobbies:
            return 'You do not currently leading any lobby'
        if new_leader_discord_id in self.lobbies:
            return 'Targeted player is already leading a lobby'
        if new_leader_discord_id == instigator_discord_id:
            return 'You are trying to transfer your own lobby to yourself'
        try:
            await search_player_by_bungie_name_from_api(new_leader_bungie_name)
        except Exception as e:
            return 'Unable to transfer lobby, please ensure that you entered the correct target bungie name and that their fireteam is in a joinable location'
        self.lobbies[new_leader_discord_id] = self.lobbies[instigator_discord_id]
        del self.lobbies[instigator_discord_id]
        await self.lobbies[new_leader_discord_id].leadership_transfer(new_leader_discord_id, new_leader_bungie_name)
        return 'Transfer successfully completed'

    async def display(self, called_by_auto_roster=False):
        if called_by_auto_roster:
            for lobby in self.inactive:
                self.remove_lobby(lobby)
        msg = 'Available lobbies:'
        for lobby_id in self.lobbies:
            lobby = await self.lobbies[lobby_id].display(called_by_auto_roster)
            msg += f"\n\t\t-\t{lobby}"
        return msg


roster = Roster()
auto_roster_channel = None
auto_roster_message = None

@bot.command(name='ping')
async def ping(ctx):
    await ctx.send('<#639272029463248908>')


@bot.command(name='create-lobby', aliases=['create_lobby'])
async def create_lobby(ctx, bungie_name, voice_channel=None):
    await ctx.send(await roster.add_lobby(bungie_name, ctx.author.id, voice_channel))


@bot.command(name='close-lobby', aliases=['close_lobby'])
async def close_lobby(ctx):
    await ctx.send(roster.remove_lobby(ctx.author.id))


@bot.command(name='transfer-lobby', aliases=['transfer_lobby'])
async def transfer_lobby(ctx, new_leader_mention: discord.Member, new_leader_bungie_name):
    await ctx.send(await roster.transfer_lobby(new_leader_mention.id, new_leader_bungie_name, ctx.author.id))


@bot.command(name='roster')
@commands.has_permissions(administrator=True)
async def display(ctx):
    await ctx.send(await roster.display())


@bot.command(name='set-roster-channel')
@commands.has_permissions(administrator=True)
async def set_roster_channel(ctx):
    global auto_roster_channel
    auto_roster_channel = ctx.channel
    await ctx.send('Channel successfully set as auto roster location')


@tasks.loop(minutes=2.0)
async def auto_refresh():
    global auto_roster_channel
    global auto_roster_message
    if auto_roster_channel:
        if auto_roster_message:
            await auto_roster_message.edit(content= await roster.display(True))
        else:
            auto_roster_message = await auto_roster_channel.send(await roster.display(True))


if __name__ == '__main__':
    auto_refresh.start()
    bot.run(TOKEN)