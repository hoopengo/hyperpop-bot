import asyncio
import random
from typing import List

import nextcord
import nextwave
from nextcord.ext import application_checks, commands, tasks

from ..config import PLAYLIST_URL


class ExtendedList:
    def __init__(self, size: int, *elements) -> None:
        self.extend_list = list(elements)
        self.size = size

    def add(self, element) -> bool:
        try:
            if len(self.extend_list) >= self.size:
                print(1)
                for _ in range(0, len(self.extend_list) - self.size + 1):
                    print(2)
                    print(self.extend_list.pop(0))

            self.extend_list.append(element)
            print(element)
            return True
        except Exception as err:
            print(err)
            return False

    def __call__(self):
        return self.extend_list

    def __str__(self) -> str:
        return str(self.extend_list)


class Player(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.bot = client

        self.bot.loop.create_task(self._connect_nodes())

        self.playlist = None
        self.extended = ExtendedList(5)

    def _get_random_track(
        self,
        tracks: List[nextwave.YouTubeTrack],
    ) -> nextwave.YouTubeTrack:
        songs = tracks.copy()
        for v, song in enumerate(songs):
            if song.identifier in self.extended():
                songs.pop(v)

        try:
            track = random.choice(songs)
        except Exception as err:
            print(err)
        else:
            self.extended.add(track.identifier)
            print(self.extended)
            return track

    async def _parse_playlist(self):
        playlist = await nextwave.YouTubeTrack.search(
            query=PLAYLIST_URL,
        )
        playlist_lenght = len(playlist.tracks)

        self.extended = ExtendedList(int(playlist_lenght // 1.5))
        return playlist

    async def _get_playlist(self) -> nextwave.YouTubePlaylist:
        if self.playlist is None:
            self.playlist = await self._parse_playlist()
            self._playlist_update_loop.start()

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

    async def _connect_nodes(self):
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
        await self._play_music(player)

    @commands.Cog.listener()
    async def on_nextwave_track_end(
        self,
        player: nextwave.Player,
        track: nextwave.Track,
        reason: str,
    ):
        print(reason)
        await self._play_music(player)

    async def _play_music(self, player: nextwave.Player):
        playlist = await self._get_playlist()
        track = self._get_random_track(
            playlist.tracks,
        )
        print(
            f"{player.guild.name}:{player.guild.id} started {track.title}, \
{track.uri}"
        )

        try:
            await player.play(track)
        except Exception as err:
            print(err)
            await self._play_music(player)

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
        await self._play_music(player)

    @commands.Cog.listener()
    async def on_wavelink_track_exception(
        self,
        player: nextwave.Player,
        track: nextwave.Track,
        exception,
    ):
        await asyncio.sleep(60)
        await self._play_music(player)

    @application_checks.has_guild_permissions(administrator=True)
    @nextcord.slash_command(name="join", description="Бот начинает играть")
    async def _join(self, inter: nextcord.Interaction):
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

            await self._play_music(vp)

        else:
            try:
                await inter.guild.voice_client.move_to(
                    inter.user.voice.channel,
                )
            except Exception:
                await inter.send("❌ Бот не может подключится к этому каналу!")

    @application_checks.has_guild_permissions(administrator=True)
    @nextcord.slash_command(name="leave", description="Бот выходит из канала")
    async def _leave(self, interaction: nextcord.Interaction):
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

    @application_checks.has_guild_permissions(administrator=True)
    @nextcord.slash_command(name="skip", description="Бот скипает этот трек")
    async def _skip(self, interaction: nextcord.Interaction):
        if interaction.guild.voice_client is None:
            return await interaction.send(
                embed=nextcord.Embed(
                    description="❌ Бот не проигрывает музыку!",
                    color=0xB53737,
                )
            )

        try:
            await interaction.guild.voice_client.stop()
        except Exception as err:
            print(err)

        await interaction.send(
            embed=nextcord.Embed(
                description="📻 Песня скипнута!",
                color=0xB53737,
            )
        )

    @application_checks.has_guild_permissions(administrator=True)
    @nextcord.slash_command(name="pause", description="Бот паузит трек")
    async def _pause(self, interaction: nextcord.Interaction):
        if interaction.guild.voice_client is None:
            return await interaction.send(
                embed=nextcord.Embed(
                    description="❌ Бот не проигрывает музыку!",
                    color=0xB53737,
                )
            )

        try:
            await interaction.guild.voice_client.pause()
        except Exception as err:
            print(err)

        await interaction.send(
            embed=nextcord.Embed(
                description="📻 Песня была поставлена на паузу!",
                color=0xB53737,
            )
        )

    @application_checks.has_guild_permissions(administrator=True)
    @nextcord.slash_command(name="resume", description="Бот продолжает трек")
    async def _resume(self, interaction: nextcord.Interaction):
        if interaction.guild.voice_client is None:
            return await interaction.send(
                embed=nextcord.Embed(
                    description="❌ Бот не проигрывает музыку!",
                    color=0xB53737,
                )
            )

        try:
            await interaction.guild.voice_client.resume()
        except Exception as err:
            print(err)

        await interaction.send(
            embed=nextcord.Embed(
                description="📻 Песня была востановлена!",
                color=0xB53737,
            )
        )

    @tasks.loop(minutes=2)
    async def _playlist_update_loop(self):
        self.playlist = await self._parse_playlist()


def setup(client: commands.Bot):
    client.add_cog(Player(client))
