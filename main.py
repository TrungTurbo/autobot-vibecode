import asyncio
import os
import sys
import discord
from discord.ext import commands

import config

# Cấu hình Intents
# Bắt buộc bật Server Members Intent và Message Content Intent trên Discord Developer Portal!
intents = discord.Intents.default()
intents.members = True          # Bắt buộc để nhận sự kiện người vào/ra server
intents.message_content = True  # Bắt buộc để đọc nội dung lệnh prefix (!play,...)

bot = commands.Bot(
    command_prefix=config.COMMAND_PREFIX,
    intents=intents,
    help_command=None,  # Tùy biến hoặc tắt default help command
)


@bot.event
async def on_ready():
    print("=" * 55)
    print(f"🤖 Bot Name    : {bot.user.name}#{bot.user.discriminator} (ID: {bot.user.id})")
    print(f"📡 Discord.py  : {discord.__version__}")
    print(f"🌐 Server Count: {len(bot.guilds)} server(s)")
    print(f"⚡ Prefix      : {config.COMMAND_PREFIX}")
    print("=" * 55)

    # Đặt trạng thái hoạt động hiển thị trên Discord
    activity = discord.Activity(
        type=discord.ActivityType.listening,
        name=f"{config.COMMAND_PREFIX}play | /play • HYCSC Autobot",
    )
    await bot.change_presence(status=discord.Status.online, activity=activity)
    print("✅ HYCSC Autobot đã sẵn sàng hoạt động!")


@bot.event
async def on_command_error(ctx: commands.Context, error: commands.CommandError):
    """Xử lý lỗi các lệnh prefix."""
    if isinstance(error, commands.CommandNotFound):
        return  # Bỏ qua nếu lệnh không tồn tại

    if isinstance(error, commands.MissingPermissions):
        await ctx.reply("❌ Bạn không có quyền thực hiện lệnh này!")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.reply(f"❌ Thiếu tham số bắt buộc! Hãy kiểm tra cú pháp lệnh.")
    else:
        print(f"[Command Error] {error}")


class HelpCog(commands.Cog, name="Trợ giúp"):
    """Lệnh hướng dẫn danh sách lệnh."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @discord.app_commands.command(name="help", description="Xem danh sách tất cả các lệnh của bot.")
    async def slash_help(self, interaction: discord.Interaction):
        embed = self._build_help_embed()
        await interaction.response.send_message(embed=embed)

    @commands.command(name="help")
    async def prefix_help(self, ctx: commands.Context):
        embed = self._build_help_embed()
        await ctx.reply(embed=embed)

    def _build_help_embed(self) -> discord.Embed:
        embed = discord.Embed(
            title="📖 BẢNG LỆNH HYCSC AUTOBOT",
            description="Bot phục vụ server CLB HYCSC với 2 tính năng chính: **Chào mừng/Tạm biệt** & **Phát nhạc đa nền tảng**.",
            color=discord.Color.blue(),
        )
        embed.add_field(
            name="🎵 Lệnh Âm Nhạc",
            value=(
                "• `/play <tên hoặc link>` hoặc `!play`: Phát nhạc từ YouTube / Spotify\n"
                "• `/skip` hoặc `!skip`: Bỏ qua bài hát hiện tại\n"
                "• `/pause` / `/resume`: Tạm dừng / Tiếp tục phát nhạc\n"
                "• `/stop` hoặc `!stop`: Dừng phát và rời voice channel\n"
                "• `/queue` hoặc `!queue`: Xem danh sách bài hát chờ\n"
                "• `/nowplaying` hoặc `!np`: Xem thông tin bài hát đang phát\n"
                "• `/loop` hoặc `!loop`: Bật/tắt lặp lại bài hát hiện tại\n"
                "• `/volume <1-100>` hoặc `!vol`: Điều chỉnh âm lượng"
            ),
            inline=False,
        )
        embed.add_field(
            name="📢 Lệnh Quản Lý Server (Admin/Manage Server)",
            value=(
                "• `/setwelcome #kênh`: Đặt kênh thông báo thành viên mới vào server\n"
                "• `/setleave #kênh`: Đặt kênh thông báo khi có người rời server\n"
                "• `/testwelcome`: Xem thử thông báo chào mừng mẫu\n"
                "• `/testleave`: Xem thử thông báo tạm biệt mẫu"
            ),
            inline=False,
        )
        embed.set_footer(text="HYCSC Autobot • Được thiết kế cho CLB")
        return embed



# Lệnh hỗ trợ cập nhật / reload cho Developer
@bot.command(name="reload")
@commands.is_owner()
async def reload_cog(ctx: commands.Context, cog_name: str):
    """Reload một cog cụ thể mà không cần tắt bot (VD: !reload music hoặc !reload welcome)."""
    full_name = f"cogs.{cog_name}" if not cog_name.startswith("cogs.") else cog_name
    try:
        await bot.reload_extension(full_name)
        await ctx.reply(f"🔄 Đã nạp lại thành công module `{full_name}`!")
    except Exception as e:
        await ctx.reply(f"❌ Lỗi khi nạp lại `{full_name}`: {e}")


@bot.command(name="sync")
@commands.is_owner()
async def sync_commands(ctx: commands.Context):
    """Đồng bộ lại Slash Commands lên Discord ngay lập tức."""
    try:
        synced = await bot.tree.sync()
        await ctx.reply(f"✨ Đã đồng bộ lại {len(synced)} lệnh Slash thành công!")
    except Exception as e:
        await ctx.reply(f"❌ Lỗi khi đồng bộ: {e}")


async def load_all_cogs():
    """Tự động quét và nạp toàn bộ các file cog trong thư mục cogs/."""
    cogs_dir = config.BASE_DIR / "cogs"
    if not cogs_dir.exists():
        return
    for file in cogs_dir.glob("*.py"):
        if file.name.startswith("__"):
            continue
        cog_path = f"cogs.{file.stem}"
        try:
            await bot.load_extension(cog_path)
            print(f"📦 Đã nạp module: {cog_path}")
        except Exception as e:
            print(f"⚠️ Không thể nạp module {cog_path}: {e}")


async def main():
    async with bot:
        # Nạp cog trợ giúp
        await bot.add_cog(HelpCog(bot))

        # Tự động nạp toàn bộ cogs
        await load_all_cogs()

        # Đồng bộ Slash Commands với Discord API
        try:
            synced = await bot.tree.sync()
            print(f"✨ Đã đồng bộ thành công {len(synced)} Slash Commands.")
        except Exception as e:
            print(f"⚠️ Không thể đồng bộ Slash Commands: {e}")

        # Kiểm tra token
        token = config.DISCORD_TOKEN.strip()
        if not token or token == "your_bot_token_here":
            print("\n" + "!" * 65)
            print("❌ LỖI: Bạn chưa điền DISCORD_TOKEN vào file .env!")
            print("👉 Vui lòng tạo file .env (sao chép từ .env.example) và dán token của bạn vào.")
            print("!" * 65 + "\n")
            sys.exit(1)

        await bot.start(token)



if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Bot đã tắt an toàn.")

