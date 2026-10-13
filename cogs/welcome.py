import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime, timezone
import config


class WelcomeCog(commands.Cog, name="Welcome & Leave"):
    """Quản lý thông báo thành viên tham gia và rời khỏi server."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    def _get_channel(self, guild: discord.Guild, setting_key: str, env_default: str) -> discord.TextChannel | None:
        """Tìm kênh thông báo dựa trên cài đặt của server, file .env hoặc kênh hệ thống mặc định."""
        # 1. Kiểm tra cấu hình riêng của guild
        channel_id = config.get_guild_setting(guild.id, setting_key)
        if channel_id:
            channel = guild.get_channel(int(channel_id))
            if channel:
                return channel

        # 2. Kiểm tra cấu hình trong .env
        if env_default and env_default.isdigit():
            channel = guild.get_channel(int(env_default))
            if channel:
                return channel

        # 3. Kênh hệ thống của Discord (system_channel)
        if guild.system_channel:
            return guild.system_channel

        # 4. Fallback: Kênh text đầu tiên bot có quyền gửi tin
        for ch in guild.text_channels:
            if ch.permissions_for(guild.me).send_messages:
                return ch
        return None

    def create_welcome_embed(self, member: discord.Member) -> discord.Embed:
        """Tạo embed chào mừng thành viên mới."""
        embed = discord.Embed(
            title="🎉 CHÀO MỪNG THÀNH VIÊN MỚI!",
            description=(
                f"Chào mừng {member.mention} đã tham gia đại gia đình **{member.guild.name}**! 🚀\n"
                f"Hãy đọc các kênh nội quy và chúc bạn có khoảng thời gian thật tuyệt vời cùng CLB!"
            ),
            color=discord.Color.from_rgb(0, 204, 255),
            timestamp=datetime.now(timezone.utc),
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="👤 Tên người dùng", value=f"`{member.name}`", inline=True)
        embed.add_field(
            name="📅 Ngày tạo tài khoản",
            value=f"<t:{int(member.created_at.timestamp())}:D>",
            inline=True,
        )
        embed.add_field(
            name="👥 Thành viên thứ",
            value=f"**#{member.guild.member_count}**",
            inline=True,
        )
        embed.set_footer(
            text="HYCSC Autobot • Chào mừng bạn gia nhập!",
            icon_url=self.bot.user.display_avatar.url if self.bot.user else None,
        )
        return embed

    def create_leave_embed(self, member: discord.Member) -> discord.Embed:
        """Tạo embed thông báo khi thành viên rời server."""
        embed = discord.Embed(
            title="👋 THÀNH VIÊN ĐÃ RỜI ĐI",
            description=f"**{member.name}** ({member.mention}) vừa rời khỏi server.",
            color=discord.Color.from_rgb(255, 107, 107),
            timestamp=datetime.now(timezone.utc),
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(
            name="👥 Số thành viên còn lại",
            value=f"**{member.guild.member_count}**",
            inline=True,
        )
        embed.set_footer(
            text="HYCSC Autobot • Tạm biệt và hẹn gặp lại!",
            icon_url=self.bot.user.display_avatar.url if self.bot.user else None,
        )
        return embed

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        """Sự kiện kích hoạt khi có người tham gia server."""
        channel = self._get_channel(member.guild, "welcome_channel_id", config.DEFAULT_WELCOME_CHANNEL_ID)
        if channel and channel.permissions_for(member.guild.me).send_messages:
            embed = self.create_welcome_embed(member)
            await channel.send(content=f"Chào mừng {member.mention}! 👋", embed=embed)

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        """Sự kiện kích hoạt khi có người rời khỏi server."""
        channel = self._get_channel(member.guild, "leave_channel_id", config.DEFAULT_LEAVE_CHANNEL_ID)
        if not channel:
            channel = self._get_channel(member.guild, "welcome_channel_id", config.DEFAULT_WELCOME_CHANNEL_ID)

        if channel and channel.permissions_for(member.guild.me).send_messages:
            embed = self.create_leave_embed(member)
            await channel.send(embed=embed)

    # ================= LỆNH CẤU HÌNH (SLASH COMMANDS & PREFIX) =================

    @app_commands.command(name="setwelcome", description="Đặt kênh gửi thông báo chào mừng thành viên mới.")
    @app_commands.describe(channel="Kênh text dùng để gửi thông báo")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def slash_set_welcome(self, interaction: discord.Interaction, channel: discord.TextChannel):
        config.set_guild_setting(interaction.guild_id, "welcome_channel_id", channel.id)
        await interaction.response.send_message(
            f"✅ Đã đặt kênh chào mừng thành công: {channel.mention}", ephemeral=True
        )

    @commands.command(name="setwelcome")
    @commands.has_permissions(manage_guild=True)
    async def prefix_set_welcome(self, ctx: commands.Context, channel: discord.TextChannel):
        """Lệnh prefix: !setwelcome #channel"""
        config.set_guild_setting(ctx.guild.id, "welcome_channel_id", channel.id)
        await ctx.reply(f"✅ Đã đặt kênh chào mừng thành công: {channel.mention}")

    @app_commands.command(name="setleave", description="Đặt kênh gửi thông báo khi có người rời server.")
    @app_commands.describe(channel="Kênh text dùng để gửi thông báo")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def slash_set_leave(self, interaction: discord.Interaction, channel: discord.TextChannel):
        config.set_guild_setting(interaction.guild_id, "leave_channel_id", channel.id)
        await interaction.response.send_message(
            f"✅ Đã đặt kênh tạm biệt thành công: {channel.mention}", ephemeral=True
        )

    @commands.command(name="setleave")
    @commands.has_permissions(manage_guild=True)
    async def prefix_set_leave(self, ctx: commands.Context, channel: discord.TextChannel):
        """Lệnh prefix: !setleave #channel"""
        config.set_guild_setting(ctx.guild.id, "leave_channel_id", channel.id)
        await ctx.reply(f"✅ Đã đặt kênh tạm biệt thành công: {channel.mention}")

    @app_commands.command(name="testwelcome", description="Gửi thử một thông báo chào mừng mẫu để kiểm tra.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def slash_test_welcome(self, interaction: discord.Interaction):
        embed = self.create_welcome_embed(interaction.user)
        await interaction.response.send_message(
            content=f"*(Bản xem trước thông báo chào mừng)* Chào mừng {interaction.user.mention}! 👋",
            embed=embed,
        )

    @commands.command(name="testwelcome")
    @commands.has_permissions(manage_guild=True)
    async def prefix_test_welcome(self, ctx: commands.Context):
        embed = self.create_welcome_embed(ctx.author)
        await ctx.reply(
            content=f"*(Bản xem trước thông báo chào mừng)* Chào mừng {ctx.author.mention}! 👋",
            embed=embed,
        )

    @app_commands.command(name="testleave", description="Gửi thử một thông báo tạm biệt mẫu để kiểm tra.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def slash_test_leave(self, interaction: discord.Interaction):
        embed = self.create_leave_embed(interaction.user)
        await interaction.response.send_message(
            content="*(Bản xem trước thông báo tạm biệt)*",
            embed=embed,
        )

    @commands.command(name="testleave")
    @commands.has_permissions(manage_guild=True)
    async def prefix_test_leave(self, ctx: commands.Context):
        embed = self.create_leave_embed(ctx.author)
        await ctx.reply(
            content="*(Bản xem trước thông báo tạm biệt)*",
            embed=embed,
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(WelcomeCog(bot))

