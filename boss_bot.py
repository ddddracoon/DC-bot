import discord
from discord.ext import commands, tasks
import json
import datetime
import os

# ========== ⚙️ 配置 ==========
BOT_TOKEN = os.getenv("BOT_TOKEN")  # 從 Render 設定讀取 Token

BOSS_CONFIG = {
    "雪毛怪人": {
        "respawn_minutes": 1,
        "input_channel_id": 1390168629609365584,   # 指令輸入頻道
        "notify_channel_id": 1390168629609365584   # 通知頻道
    },
    "黑輪王": {
        "respawn_minutes": 5,
        "input_channel_id": 1390168719677984808,
        "notify_channel_id": 1390168719677984808
    }
}
# =============================

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

try:
    with open("boss_kills.json", "r", encoding="utf-8") as f:
        boss_kills = json.load(f)
except FileNotFoundError:
    boss_kills = {}

def save_data():
    with open("boss_kills.json", "w", encoding="utf-8") as f:
        json.dump(boss_kills, f, ensure_ascii=False, indent=2)

@bot.event
async def on_ready():
    print(f"✅ Bot 已上線：{bot.user}")
    check_respawns.start()

@bot.command()
async def kill(ctx, boss: str, game_channel: str):
    boss = boss.lower()
    game_channel = game_channel.lower()

    if boss not in BOSS_CONFIG:
        return await ctx.send(f"❌ 無效王名稱 `{boss}`。可用：{', '.join(BOSS_CONFIG)}")

    config = BOSS_CONFIG[boss]
    if ctx.channel.id != config["input_channel_id"]:
        return await ctx.send("⚠️ 請在對應頻道使用此指令。")

    now_dt = datetime.datetime.now(datetime.timezone.utc)
    now = now_dt.isoformat()

    if boss not in boss_kills:
        boss_kills[boss] = {}

    boss_kills[boss][game_channel] = {
        "time": now,
        "notified": False
    }
    save_data()

    notify_channel = bot.get_channel(config["notify_channel_id"])
    if notify_channel:
        await notify_channel.send(
            f"📢 `{boss}` 擊殺紀錄\n"
            f"🕹️ 分流：`{game_channel}`\n"
            f"🕒 擊殺時間：`{now_dt.strftime('%Y-%m-%d %H:%M:%S')} UTC`"
        )

    await ctx.send(f"✅ `{boss}` 在 `{game_channel}` 擊殺已記錄。")

@bot.command()
async def next(ctx, boss: str, game_channel: str = None):
    boss = boss.lower()
    if boss not in BOSS_CONFIG:
        return await ctx.send(f"❌ 無效王名稱 `{boss}`。")

    if ctx.channel.id != BOSS_CONFIG[boss]["input_channel_id"]:
        return await ctx.send("⚠️ 請在對應頻道查詢。")

    if boss not in boss_kills:
        return await ctx.send(f"⚠️ 尚未記錄 `{boss}` 擊殺，請先使用 `!kill {boss} 分流`")

    respawn_minutes = BOSS_CONFIG[boss]["respawn_minutes"]

    if game_channel:
        data = boss_kills[boss].get(game_channel.lower())
        if not data:
            return await ctx.send(f"⚠️ `{boss}` 在 `{game_channel}` 尚無紀錄。")
        last_kill = datetime.datetime.fromisoformat(data["time"]).replace(tzinfo=datetime.timezone.utc)
        next_spawn = last_kill + datetime.timedelta(minutes=respawn_minutes)
        await ctx.send(
            f"🕒 `{boss}` `{game_channel}` 預估刷新：`{next_spawn.strftime('%Y-%m-%d %H:%M:%S')} UTC`"
        )
    else:
        msg = f"🕒 `{boss}` 預估刷新時間：\n"
        for ch, data in boss_kills[boss].items():
            last_kill = datetime.datetime.fromisoformat(data["time"]).replace(tzinfo=datetime.timezone.utc)
            next_spawn = last_kill + datetime.timedelta(minutes=respawn_minutes)
            msg += f"- `{ch}`：`{next_spawn.strftime('%Y-%m-%d %H:%M:%S')} UTC`\n"
        await ctx.send(msg)

@tasks.loop(seconds=60)
async def check_respawns():
    now = datetime.datetime.now(datetime.timezone.utc)
    for boss, config in BOSS_CONFIG.items():
        notify_channel = bot.get_channel(config["notify_channel_id"])
        if not notify_channel or boss not in boss_kills:
            continue

        respawn_minutes = config["respawn_minutes"]

        for game_channel, data in boss_kills[boss].items():
            if data.get("notified"):
                continue
            try:
                last_kill = datetime.datetime.fromisoformat(data["time"]).replace(tzinfo=datetime.timezone.utc)
                respawn_time = last_kill + datetime.timedelta(minutes=respawn_minutes)
                if now >= respawn_time:
                    await notify_channel.send(f"⚠️ `{boss}` 在 `{game_channel}` 分流已刷新！")
                    data["notified"] = True
                    save_data()
            except Exception as e:
                print(f"⚠️ 錯誤：{boss} {game_channel} - {e}")
                continue

bot.run(BOT_TOKEN)
