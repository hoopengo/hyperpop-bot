import asyncio
from random import randint
from typing import List

import nextcord
import nextwave
from nextcord.ext import application_checks, commands

from ..config import PLAYLIST_URL


class ExtendedList:
    def __init__(self, size: int, *elements) -> None:
        self.extend_list = list(elements)
        self.size = size

    def add(self, element) -> bool:
        try:
            if len(self.extend_list) >= self.size:
                for _ in range(0, len(self.extend_list) - self.size):
                    self.extend_list.pop(-1)

            self.extend_list.append(element)
            return True
        except Exception:
            return False

    def __call__(self):
        return self.extend_list

    def __str__(self) -> str:
        return str(self.extend_list)


def get_random_track(
    tracks: List[nextwave.YouTubeTrack], extended: ExtendedList
) -> nextwave.YouTubeTrack:
    for song in tracks:
        if song.identifier in extended():
            tracks.remove(song)

    track_number = randint(0, len(tracks) - 1)
    try:
        track = tracks[track_number]
    except Exception as err:
        print(err)

    extended.add(track.identifier)

    return track


class Player(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.bot = client

        self.bot.loop.create_task(self.connect_nodes())

        self.playlist = None
        self.extended = ExtendedList(5)

    async def get_playlist(self) -> nextwave.YouTubePlaylist:
        if self.playlist is None:
            self.playlist = await nextwave.YouTubeTrack.search(
                query=PLAYLIST_URL,
            )
            playlist_lenght = len(self.playlist.tracks)

            self.extended = ExtendedList(int(playlist_lenght // 1.5))

        return self.playlist

    @commands.Cog.listener()
    async def on_voice_state_update(
        self,
        member: nextcord.Member,
        before: nextcord.VoiceState,
        after: nextcord.VoiceState,
    ):
        if member.id == self.bot.user.id:
            if after.channel is None:
                try:
                    await member.guild.voice_client.stop()
                    await member.guild.voice_client.disconnect()
                except Exception:
                    pass

                print(
                    f"{member.guild.name}:{member.guild.id} player has been\
stoped!"
                )

    async def connect_nodes(self):
        """Connect to our Lavalink nodes."""
        await self.bot.wait_until_ready()

        await nextwave.NodePool.create_node(
            bot=self.bot,
            host="www.lavalinknodepublic.ml",
            port=443,
            password="mrextinctcodes",
            https=True,
        )

    @commands.Cog.listener()
    async def on_nextwave_websocket_closed(
        self,
        player: nextwave.Player,
        reason,
        code,
    ):
        await asyncio.sleep(60)
        await self.play_mus(player)

    @commands.Cog.listener()
    async def on_nextwave_track_end(
        self,
        player: nextwave.Player,
        track: nextwave.Track,
        reason: str,
    ):
        await self.play_mus(player)

    async def play_mus(self, player: nextwave.Player):
        playlist = await self.get_playlist()
        track = get_random_track(
            playlist.tracks,
            self.extended,
        )
        print(
            f"{player.guild.name}:{player.guild.id} started {track.title}, \
{track.uri}"
        )

        try:
            await player.play(track)
        except Exception as err:
            print(err)
            await self.play_mus(player)

    @commands.Cog.listener()
    async def on_nextwave_node_ready(self, node: nextwave.Node):
        """Event fired when a node has finished connecting."""
        print(f"Node: <{node.identifier}> is ready!")

    @commands.Cog.listener()
    async def on_wavelink_track_stuck(
        self,
        player: nextwave.Player,
        track: nextwave.Track,
        threshold,
    ):
        await asyncio.sleep(60)
        await self.play_mus(player)

    @commands.Cog.listener()
    async def on_wavelink_track_exception(
        self,
        player: nextwave.Player,
        track: nextwave.Track,
        exception,
    ):
        await asyncio.sleep(60)
        await self.play_mus(player)

    @application_checks.has_guild_permissions(administrator=True)
    @nextcord.slash_command(name="join", description="Бот начинает играть")
    async def join(self, inter: nextcord.Interaction):
        if inter.user.voice is None:
            emb = nextcord.Embed(
                description="❌ Вы не в голосовом канале!", color=0xB53737
            )
            return await inter.send(embed=emb)

        if not inter.guild.voice_client:
            try:
                vp: nextwave.Player = await inter.user.voice.channel.connect(
                    cls=nextwave.Player,
                    reconnect=True,
                )
            except Exception:
                await inter.send("❌ Бот не может подключится к этому каналу!")

            await inter.send(
                embed=nextcord.Embed(
                    description="📻 Прослушивание начато!",
                    color=0xFD45B5,
                )
            )

            await self.play_mus(vp)

        else:
            try:
                await inter.guild.voice_client.move_to(
                    inter.user.voice.channel,
                )
            except Exception:
                await inter.send("❌ Бот не может подключится к этому каналу!")

    @application_checks.has_guild_permissions(administrator=True)
    @nextcord.slash_command(name="leave", description="Бот выходит из канала")
    async def leave(self, interaction: nextcord.Interaction):
        if interaction.guild.voice_client is None:
            return await interaction.send(
                embed=nextcord.Embed(
                    description="❌ Бот не проигрывает музыку!",
                    color=0xB53737,
                )
            )

        try:
            await interaction.guild.voice_client.stop()
            await interaction.guild.voice_client.disconnect()
        except Exception:
            pass

        await interaction.send(
            embed=nextcord.Embed(
                description="📻 Прослушивание приостановлено!",
                color=0xB53737,
            )
        )


def setup(client):
    client.add_cog(Player(client))
