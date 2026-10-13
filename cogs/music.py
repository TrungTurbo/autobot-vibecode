import asyncio
import re
import urllib.parse
from dataclasses import dataclass
from typing import Optional

import discord
import requests
import yt_dlp
from discord import app_commands
from discord.ext import commands

# Cấu hình yt-dlp tối ưu cho streaming Discord
YTDL_OPTIONS = {
    "format": "bestaudio/best",
    "extractaudio": True,
    "audioformat": "mp3",
    "outtmpl": "%(extractor)s-%(id)s-%(title)s.%(ext)s",
    "restrictfilenames": True,
    "noplaylist": True,
    "nocheckcertificate": True,
    "ignoreerrors": False,
    "logtostderr": False,
    "quiet": True,
    "no_warnings": True,
    "default_search": "ytsearch",
    "source_address": "0.0.0.0",
}

FFMPEG_OPTIONS = {
    "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
    "options": "-vn",
}

ytdl = yt_dlp.YoutubeDL(YTDL_OPTIONS)


@dataclass
class Song:
    """Thông tin bài hát trong hàng đợi."""
    title: str
    source_url: str        # URL phát trực tiếp (audio stream)
    webpage_url: str       # Link gốc (YouTube / Spotify link)
    duration: int          # Thời lượng tính bằng giây
    thumbnail: str
    requester: discord.Member

    @property
    def duration_formatted(self) -> str:
        """Định dạng thời lượng mm:ss hoặc hh:mm:ss."""
        if not self.duration:
            return "Livestream / Không rõ"
        minutes, seconds = divmod(self.duration, 60)
        hours, minutes = divmod(minutes, 60)
        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        return f"{minutes:02d}:{seconds:02d}"


class GuildMusicPlayer:
    """Quản lý hàng đợi và phát nhạc riêng cho từng server."""

    def __init__(self, bot: commands.Bot, guild_id: int):
        self.bot = bot
        self.guild_id = guild_id
        self.queue: list[Song] = []
        self.current: Optional[Song] = None
        self.voice_client: Optional[discord.VoiceClient] = None
        self.text_channel: Optional[discord.abc.Messageable] = None
        self.loop_single: bool = False
        self.volume: float = 0.5
        self.play_next_event = asyncio.Event()
        self.audio_task: Optional[asyncio.Task] = None

    async def start_loop(self):
        """Vòng lặp phát nhạc liên tục từ hàng đợi."""
        if self.audio_task and not self.audio_task.done():
            return
        self.audio_task = asyncio.create_task(self._player_loop())

    async def _player_loop(self):
        while True:
            self.play_next_event.clear()

            # Nếu không bật loop và hàng đợi hết bài -> đợi hoặc tự động rời kênh
            if not self.loop_single:
                if not self.queue:
                    self.current = None
                    try:
                        # Chờ 3 phút, nếu không có bài mới thì ngắt kết nối
                        await asyncio.wait_for(self.wait_for_song(), timeout=180.0)
                    except asyncio.TimeoutError:
                        if self.voice_client and self.voice_client.is_connected():
                            if self.text_channel:
                                await self.text_channel.send(
                                    "💤 Không còn bài hát nào trong hàng đợi. Bot đã rời kênh thoại để tiết kiệm tài nguyên."
                                )
                            await self.voice_client.disconnect()
                        break
                self.current = self.queue.pop(0)

            # Bắt đầu phát bài hiện tại
            if not self.voice_client or not self.voice_client.is_connected():
                break

            try:
                # Tạo audio source từ stream URL
                audio_source = discord.FFmpegPCMAudio(self.current.source_url, **FFMPEG_OPTIONS)
                transformed_source = discord.PCMVolumeTransformer(audio_source, volume=self.volume)

                def after_playing(error):
                    if error:
                        print(f"[Music Error] {error}")
                    self.bot.loop.call_soon_threadsafe(self.play_next_event.set)

                self.voice_client.play(transformed_source, after=after_playing)

                # Gửi thông báo Now Playing nếu không phải đang lặp lại cùng bài
                if not self.loop_single and self.text_channel:
                    embed = discord.Embed(
                        title="🎶 Đang phát nhạc",
                        description=f"[{self.current.title}]({self.current.webpage_url})",
                        color=discord.Color.green(),
                    )
                    if self.current.thumbnail:
                        embed.set_thumbnail(url=self.current.thumbnail)
                    embed.add_field(name="⏱ Thời lượng", value=self.current.duration_formatted, inline=True)
                    embed.add_field(name="👤 Yêu cầu bởi", value=self.current.requester.mention, inline=True)
                    await self.text_channel.send(embed=embed)

            except Exception as e:
                print(f"[Music Play Exception] {e}")
                if self.text_channel:
                    await self.text_channel.send(f"⚠️ Có lỗi xảy ra khi phát bài `{self.current.title}`: {e}")
                self.play_next_event.set()

            # Chờ bài hát kết thúc
            await self.play_next_event.wait()

    async def wait_for_song(self):
        """Chờ cho đến khi có bài mới được thêm vào queue."""
        while not self.queue:
            await asyncio.sleep(2)

    def stop(self):
        """Dừng phát và dọn sạch hàng đợi."""
        self.queue.clear()
        self.current = None
        self.loop_single = False
        if self.voice_client and self.voice_client.is_playing():
            self.voice_client.stop()
        if self.audio_task:
            self.audio_task.cancel()


class MusicCog(commands.Cog, name="Âm nhạc"):
    """Hệ thống phát nhạc đa nền tảng (YouTube, Spotify,...) cho Discord."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.players: dict[int, GuildMusicPlayer] = {}

    def get_player(self, guild_id: int) -> GuildMusicPlayer:
        """Lấy hoặc tạo MusicPlayer cho server."""
        if guild_id not in self.players:
            self.players[guild_id] = GuildMusicPlayer(self.bot, guild_id)
        return self.players[guild_id]

    async def resolve_query(self, query: str) -> str:
        """
        Xử lý đa nền tảng:
        Nếu là link Spotify -> lấy tiêu đề & nghệ sĩ qua Spotify oEmbed rồi tìm trên YouTube.
        Nếu là từ khóa thường -> giữ nguyên để tìm trên YouTube.
        """
        query = query.strip()

        # Kiểm tra nếu là link Spotify Track
        if "open.spotify.com/track/" in query:
            try:
                # Gọi oEmbed của Spotify không cần API key
                oembed_url = f"https://open.spotify.com/oembed?url={urllib.parse.quote(query)}"
                resp = requests.get(oembed_url, timeout=5)
                if resp.status_code == 200:
                    data = resp.json()
                    track_title = data.get("title", "")
                    # oEmbed title thường có dạng "Tên bài hát"
                    if track_title:
                        return f"ytsearch:{track_title} audio"
            except Exception as e:
                print(f"[Spotify oEmbed Error] {e}")

        # Link thông thường hoặc từ khóa tìm kiếm
        if not (query.startswith("http://") or query.startswith("https://")):
            return f"ytsearch:{query}"
        return query

    async def extract_song_info(self, search_query: str, requester: discord.Member) -> Optional[Song]:
        """Trích xuất metadata bài hát qua yt-dlp trong executor để không block bot."""
        loop = self.bot.loop

        def _extract():
            try:
                data = ytdl.extract_info(search_query, download=False)
                if not data:
                    return None
                # Nếu là kết quả tìm kiếm (entries)
                if "entries" in data:
                    if not data["entries"]:
                        return None
                    data = data["entries"][0]

                stream_url = data.get("url")
                # Nếu không có stream_url trực tiếp, thử lấy từ formats
                if not stream_url and "formats" in data:
                    for f in data["formats"]:
                        if f.get("acodec") != "none" and f.get("vcodec") == "none":
                            stream_url = f.get("url")
                            break

                return Song(
                    title=data.get("title", "Không rõ tiêu đề"),
                    source_url=stream_url or data.get("url", ""),
                    webpage_url=data.get("webpage_url", search_query),
                    duration=int(data.get("duration", 0)),
                    thumbnail=data.get("thumbnail", ""),
                    requester=requester,
                )
            except Exception as e:
                print(f"[Extract Info Error] {e}")
                return None

        return await loop.run_in_executor(None, _extract)

    async def ensure_voice(self, ctx_or_interaction) -> Optional[discord.VoiceClient]:
        """Kiểm tra và kết nối vào kênh thoại của người dùng."""
        user = ctx_or_interaction.user if isinstance(ctx_or_interaction, discord.Interaction) else ctx_or_interaction.author
        guild = ctx_or_interaction.guild

        if not user.voice or not user.voice.channel:
            return None

        target_channel = user.voice.channel
        voice_client: discord.VoiceClient = guild.voice_client

        if voice_client is None:
            voice_client = await target_channel.connect()
        elif voice_client.channel != target_channel:
            await voice_client.move_to(target_channel)

        return voice_client

    # ================= CÁC LỆNH PHÁT NHẠC =================

    # 1. PLAY (Hỗ trợ cả Slash Command và Prefix)
    @app_commands.command(name="play", description="Phát nhạc từ YouTube, Spotify hoặc từ khóa tìm kiếm.")
    @app_commands.describe(query="Tên bài hát hoặc link YouTube / Spotify")
    async def slash_play(self, interaction: discord.Interaction, query: str):
        if not interaction.user.voice or not interaction.user.voice.channel:
            await interaction.response.send_message(
                "❌ Bạn cần tham gia một kênh đàm thoại (Voice Channel) trước!", ephemeral=True
            )
            return

        await interaction.response.defer()
        vc = await self.ensure_voice(interaction)
        if not vc:
            await interaction.followup.send("❌ Không thể kết nối vào kênh đàm thoại!")
            return

        player = self.get_player(interaction.guild_id)
        player.voice_client = vc
        player.text_channel = interaction.channel

        resolved = await self.resolve_query(query)
        song = await self.extract_song_info(resolved, interaction.user)

        if not song:
            await interaction.followup.send(f"❌ Không tìm thấy bài hát nào phù hợp với: `{query}`")
            return

        # Nếu bot đang phát nhạc, thêm vào queue
        if vc.is_playing() or vc.is_paused() or player.current:
            player.queue.append(song)
            embed = discord.Embed(
                title="📝 Đã thêm vào hàng đợi",
                description=f"[{song.title}]({song.webpage_url})",
                color=discord.Color.blue(),
            )
            embed.add_field(name="⏱ Thời lượng", value=song.duration_formatted, inline=True)
            embed.add_field(name="🔢 Vị trí trong hàng", value=f"#{len(player.queue)}", inline=True)
            if song.thumbnail:
                embed.set_thumbnail(url=song.thumbnail)
            await interaction.followup.send(embed=embed)
        else:
            player.queue.append(song)
            await interaction.followup.send(f"🔍 Tìm thấy: **{song.title}**! Bắt đầu phát...")
            await player.start_loop()

    @commands.command(name="play", aliases=["p"])
    async def prefix_play(self, ctx: commands.Context, *, query: str):
        """Lệnh prefix: !play <tên bài hoặc link>"""
        if not ctx.author.voice or not ctx.author.voice.channel:
            await ctx.reply("❌ Bạn cần tham gia một kênh đàm thoại trước!")
            return

        async with ctx.typing():
            vc = await self.ensure_voice(ctx)
            if not vc:
                await ctx.reply("❌ Không thể kết nối vào kênh đàm thoại!")
                return

            player = self.get_player(ctx.guild.id)
            player.voice_client = vc
            player.text_channel = ctx.channel

            resolved = await self.resolve_query(query)
            song = await self.extract_song_info(resolved, ctx.author)

            if not song:
                await ctx.reply(f"❌ Không tìm thấy bài hát nào phù hợp với: `{query}`")
                return

            if vc.is_playing() or vc.is_paused() or player.current:
                player.queue.append(song)
                embed = discord.Embed(
                    title="📝 Đã thêm vào hàng đợi",
                    description=f"[{song.title}]({song.webpage_url})",
                    color=discord.Color.blue(),
                )
                embed.add_field(name="⏱ Thời lượng", value=song.duration_formatted, inline=True)
                embed.add_field(name="🔢 Vị trí trong hàng", value=f"#{len(player.queue)}", inline=True)
                if song.thumbnail:
                    embed.set_thumbnail(url=song.thumbnail)
                await ctx.reply(embed=embed)
            else:
                player.queue.append(song)
                await ctx.reply(f"🔍 Tìm thấy: **{song.title}**! Bắt đầu phát...")
                await player.start_loop()

    # 2. SKIP
    @app_commands.command(name="skip", description="Bỏ qua bài hát đang phát.")
    async def slash_skip(self, interaction: discord.Interaction):
        player = self.get_player(interaction.guild_id)
        if not player.voice_client or not player.voice_client.is_playing():
            await interaction.response.send_message("❌ Hiện không có bài hát nào đang phát!", ephemeral=True)
            return

        player.loop_single = False
        player.voice_client.stop()
        await interaction.response.send_message("⏭ Đã bỏ qua bài hát hiện tại!")

    @commands.command(name="skip", aliases=["s", "next"])
    async def prefix_skip(self, ctx: commands.Context):
        player = self.get_player(ctx.guild.id)
        if not player.voice_client or not player.voice_client.is_playing():
            await ctx.reply("❌ Hiện không có bài hát nào đang phát!")
            return

        player.loop_single = False
        player.voice_client.stop()
        await ctx.reply("⏭ Đã bỏ qua bài hát hiện tại!")

    # 3. PAUSE & RESUME
    @app_commands.command(name="pause", description="Tạm dừng phát nhạc.")
    async def slash_pause(self, interaction: discord.Interaction):
        player = self.get_player(interaction.guild_id)
        if player.voice_client and player.voice_client.is_playing():
            player.voice_client.pause()
            await interaction.response.send_message("⏸ Đã tạm dừng phát nhạc.")
        else:
            await interaction.response.send_message("❌ Không có bài hát nào đang phát để tạm dừng!", ephemeral=True)

    @commands.command(name="pause")
    async def prefix_pause(self, ctx: commands.Context):
        player = self.get_player(ctx.guild.id)
        if player.voice_client and player.voice_client.is_playing():
            player.voice_client.pause()
            await ctx.reply("⏸ Đã tạm dừng phát nhạc.")
        else:
            await ctx.reply("❌ Không có bài hát nào đang phát để tạm dừng!")

    @app_commands.command(name="resume", description="Tiếp tục phát nhạc đang tạm dừng.")
    async def slash_resume(self, interaction: discord.Interaction):
        player = self.get_player(interaction.guild_id)
        if player.voice_client and player.voice_client.is_paused():
            player.voice_client.resume()
            await interaction.response.send_message("▶ Tiếp tục phát nhạc.")
        else:
            await interaction.response.send_message("❌ Không có bài hát nào đang bị tạm dừng!", ephemeral=True)

    @commands.command(name="resume")
    async def prefix_resume(self, ctx: commands.Context):
        player = self.get_player(ctx.guild.id)
        if player.voice_client and player.voice_client.is_paused():
            player.voice_client.resume()
            await ctx.reply("▶ Tiếp tục phát nhạc.")
        else:
            await ctx.reply("❌ Không có bài hát nào đang bị tạm dừng!")

    # 4. STOP / LEAVE
    @app_commands.command(name="stop", description="Dừng phát nhạc, xóa hàng đợi và rời kênh thoại.")
    async def slash_stop(self, interaction: discord.Interaction):
        player = self.get_player(interaction.guild_id)
        player.stop()
        if player.voice_client:
            await player.voice_client.disconnect()
        await interaction.response.send_message("⏹ Đã dừng nhạc và rời kênh thoại.")

    @commands.command(name="stop", aliases=["leave", "disconnect", "dc"])
    async def prefix_stop(self, ctx: commands.Context):
        player = self.get_player(ctx.guild.id)
        player.stop()
        if player.voice_client:
            await player.voice_client.disconnect()
        await ctx.reply("⏹ Đã dừng nhạc và rời kênh thoại.")

    # 5. QUEUE
    @app_commands.command(name="queue", description="Hiển thị danh sách các bài hát đang chờ phát.")
    async def slash_queue(self, interaction: discord.Interaction):
        player = self.get_player(interaction.guild_id)
        embed = self._build_queue_embed(player)
        await interaction.response.send_message(embed=embed)

    @commands.command(name="queue", aliases=["q"])
    async def prefix_queue(self, ctx: commands.Context):
        player = self.get_player(ctx.guild.id)
        embed = self._build_queue_embed(player)
        await ctx.reply(embed=embed)

    def _build_queue_embed(self, player: GuildMusicPlayer) -> discord.Embed:
        embed = discord.Embed(title="📜 Danh sách phát nhạc", color=discord.Color.gold())
        if player.current:
            loop_badge = " 🔂 *(Đang lặp lại)*" if player.loop_single else ""
            embed.description = f"**Đang phát:** [{player.current.title}]({player.current.webpage_url}) (`{player.current.duration_formatted}`){loop_badge}\n"
        else:
            embed.description = "Hiện tại không có bài nào đang phát.\n"

        if not player.queue:
            embed.description += "\n*Hàng đợi đang trống. Dùng `/play` hoặc `!play` để thêm bài!*"
        else:
            embed.description += "\n**Hàng đợi tiếp theo:**\n"
            for idx, s in enumerate(player.queue[:10], start=1):
                embed.description += f"`{idx}.` [{s.title}]({s.webpage_url}) | `{s.duration_formatted}` (bởi {s.requester.mention})\n"
            if len(player.queue) > 10:
                embed.description += f"\n*... và còn {len(player.queue) - 10} bài hát khác.*"

        embed.set_footer(text=f"Tổng số bài trong hàng: {len(player.queue)}")
        return embed

    # 6. NOW PLAYING
    @app_commands.command(name="nowplaying", description="Xem thông tin bài hát đang phát.")
    async def slash_nowplaying(self, interaction: discord.Interaction):
        player = self.get_player(interaction.guild_id)
        if not player.current:
            await interaction.response.send_message("❌ Hiện không có bài hát nào đang phát!", ephemeral=True)
            return

        embed = discord.Embed(
            title="🎶 Đang phát",
            description=f"[{player.current.title}]({player.current.webpage_url})",
            color=discord.Color.purple(),
        )
        if player.current.thumbnail:
            embed.set_thumbnail(url=player.current.thumbnail)
        embed.add_field(name="⏱ Thời lượng", value=player.current.duration_formatted, inline=True)
        embed.add_field(name="👤 Yêu cầu bởi", value=player.current.requester.mention, inline=True)
        embed.add_field(name="🔂 Chế độ lặp", value="Bật" if player.loop_single else "Tắt", inline=True)
        await interaction.response.send_message(embed=embed)

    @commands.command(name="nowplaying", aliases=["np"])
    async def prefix_nowplaying(self, ctx: commands.Context):
        player = self.get_player(ctx.guild.id)
        if not player.current:
            await ctx.reply("❌ Hiện không có bài hát nào đang phát!")
            return

        embed = discord.Embed(
            title="🎶 Đang phát",
            description=f"[{player.current.title}]({player.current.webpage_url})",
            color=discord.Color.purple(),
        )
        if player.current.thumbnail:
            embed.set_thumbnail(url=player.current.thumbnail)
        embed.add_field(name="⏱ Thời lượng", value=player.current.duration_formatted, inline=True)
        embed.add_field(name="👤 Yêu cầu bởi", value=player.current.requester.mention, inline=True)
        embed.add_field(name="🔂 Chế độ lặp", value="Bật" if player.loop_single else "Tắt", inline=True)
        await ctx.reply(embed=embed)

    # 7. LOOP
    @app_commands.command(name="loop", description="Bật/tắt chế độ lặp lại bài hát hiện tại.")
    async def slash_loop(self, interaction: discord.Interaction):
        player = self.get_player(interaction.guild_id)
        if not player.current:
            await interaction.response.send_message("❌ Cần có bài hát đang phát để bật/tắt lặp!", ephemeral=True)
            return

        player.loop_single = not player.loop_single
        status = "Bật 🔂" if player.loop_single else "Tắt ➡️"
        await interaction.response.send_message(f"Đã **{status}** chế độ lặp bài hát hiện tại.")

    @commands.command(name="loop")
    async def prefix_loop(self, ctx: commands.Context):
        player = self.get_player(ctx.guild.id)
        if not player.current:
            await ctx.reply("❌ Cần có bài hát đang phát để bật/tắt lặp!")
            return

        player.loop_single = not player.loop_single
        status = "Bật 🔂" if player.loop_single else "Tắt ➡️"
        await ctx.reply(f"Đã **{status}** chế độ lặp bài hát hiện tại.")

    # 8. VOLUME
    @app_commands.command(name="volume", description="Điều chỉnh âm lượng (1-100%).")
    @app_commands.describe(percent="Mức âm lượng từ 1 đến 100")
    async def slash_volume(self, interaction: discord.Interaction, percent: int):
        if not 1 <= percent <= 100:
            await interaction.response.send_message("❌ Mức âm lượng phải từ 1 đến 100!", ephemeral=True)
            return

        player = self.get_player(interaction.guild_id)
        player.volume = percent / 100.0
        if player.voice_client and player.voice_client.source:
            if hasattr(player.voice_client.source, "volume"):
                player.voice_client.source.volume = player.volume

        await interaction.response.send_message(f"🔊 Đã chỉnh âm lượng về **{percent}%**.")

    @commands.command(name="volume", aliases=["vol"])
    async def prefix_volume(self, ctx: commands.Context, percent: int):
        if not 1 <= percent <= 100:
            await ctx.reply("❌ Mức âm lượng phải từ 1 đến 100!")
            return

        player = self.get_player(ctx.guild.id)
        player.volume = percent / 100.0
        if player.voice_client and player.voice_client.source:
            if hasattr(player.voice_client.source, "volume"):
                player.voice_client.source.volume = player.volume

        await ctx.reply(f"🔊 Đã chỉnh âm lượng về **{percent}%**.")


async def setup(bot: commands.Bot):
    await bot.add_cog(MusicCog(bot))

