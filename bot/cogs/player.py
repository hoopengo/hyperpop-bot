from random import randint
from typing import List

import nextcord
import nextwave
from nextcord.ext import commands

from ..config import PLAYLIST_URL


class ExtendedList:
    def __init__(self, size: int, *elements) -> None:
        self.extend_list = list(elements)
        self.size = size

    def add(self, element) -> bool:
        try:
            if len(self.extend_list) >= self.size:
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
    for track in tracks:
        if track in extended():
            tracks.remove(track)

    track_number = randint(0, len(tracks))
    track = tracks[track_number]
    extended.add(track)

    return track


class Player(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.bot = client

        self.bot.loop.create_task(self.connect_nodes())
        self.extended = ExtendedList(5)

    async def connect_nodes(self):
        """Connect to our Lavalink nodes."""
        await self.bot.wait_until_ready()

        await nextwave.NodePool.create_node(
            bot=self.bot,
            host="lavalinkinc.ml",
            port=443,
            password="incognito",
            https=True,
        )

    @commands.Cog.listener()
    async def on_nextwave_track_end(
        self,
        player: nextwave.Player,
        track: nextwave.Track,
        reason: str,
    ):
        await self.play_mus()

    async def play_mus(self):
        if not self.vp.is_playing():
            playlist: nextwave.YouTubePlaylist
            playlist = await nextwave.YouTubeTrack.search(query=PLAYLIST_URL)

            track = get_random_track(playlist.tracks, self.extended)

            try:
                await self.vp.play(track)
            except Exception as err:
                print(err)

    @commands.Cog.listener()
    async def on_nextwave_node_ready(self, node: nextwave.Node):
        """Event fired when a node has finished connecting."""
        print(f"Node: <{node.identifier}> is ready!")

    @nextcord.slash_command(name="join", description="Бот начинает играть")
    async def join(self, inter: nextcord.Interaction):
        if inter.user.voice is None:
            emb = nextcord.Embed(
                description="❌ Вы не в голосовом канале!", color=0xB53737
            )
            return await inter.send(embed=emb)

        if not inter.guild.voice_client:
            self.vp: nextwave.Player = await inter.user.voice.channel.connect(
                cls=nextwave.Player,
                reconnect=True,
            )

            await inter.send(
                embed=nextcord.Embed(
                    description="📻 Прослушивание начато!",
                    color=0xFD45B5,
                )
            )

            await self.play_mus()
        else:
            await self.vp.move_to(inter.user.voice.channel)
            self.vp: nextwave.Player = inter.guild.voice_client

    @nextcord.slash_command(name="leave", description="Бот выходит из канала")
    async def leave(self, interaction: nextcord.Interaction):
        if interaction.guild.voice_client is None:
            return await interaction.send(
                embed=nextcord.Embed(
                    description="❌ Бот не проигрывает музыку!",
                    color=0xB53737,
                )
            )

        await self.vp.stop()
        await interaction.guild.voice_client.disconnect()

        self.is_playing = False

        await interaction.send(
            embed=nextcord.Embed(
                description="📻 Прослушивание приостановлено!",
                color=0xB53737,
            )
        )


def setup(client):
    client.add_cog(Player(client))
