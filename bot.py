import discord
from discord import app_commands
from discord.ui import Button, View
import requests
import csv
import io
import asyncio
import json
import os
from datetime import datetime, date, timedelta
import re

TOKEN = os.getenv("DISCORD_TOKEN")


CSV_URL = "https://docs.google.com/spreadsheets/d/1XfG6cFcRLoxPxSRjUHflKxYAmnCx-OU6NlVSFUMQ7iw/export?format=csv"

NOTIFY_USERS = [1364992552616329349]

PREVIOUS_STATE_FILE = "previous_state.json"
HISTORY_FILE = "player_history.json"
STATS_FILE = "stats.json"
BLACKLIST_FILE = "blacklist.json"
SCHEDULES_FILE = "schedules.json"

intents = discord.Intents.default()
intents.message_content = True
bot = discord.Client(intents=intents)
tree = app_commands.CommandTree(bot)

moderation_channel = None
notification_channel = None
logs_channel = None
first_run = True

CHANNELS_CONFIG_FILE = "channels_config.json"

def load_channels_config():
    if not os.path.exists(CHANNELS_CONFIG_FILE):
        return {"moderation": None, "notification": None, "logs": None}
    try:
        with open(CHANNELS_CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return {"moderation": None, "notification": None, "logs": None}

def save_channels_config():
    global moderation_channel, notification_channel, logs_channel
    config = {
        "moderation": moderation_channel.id if moderation_channel else None,
        "notification": notification_channel.id if notification_channel else None,
        "logs": logs_channel.id if logs_channel else None
    }
    try:
        with open(CHANNELS_CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Ошибка сохранения: {e}")

def load_config_channels():
    global moderation_channel, notification_channel, logs_channel
    config = load_channels_config()
    
    if config.get("moderation"):
        moderation_channel = bot.get_channel(config["moderation"])
    if config.get("notification"):
        notification_channel = bot.get_channel(config["notification"])
    if config.get("logs"):
        logs_channel = bot.get_channel(config["logs"])

def load_blacklist():
    if not os.path.exists(BLACKLIST_FILE):
        return []
    try:
        with open(BLACKLIST_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return []

def save_blacklist(blacklist):
    try:
        with open(BLACKLIST_FILE, 'w', encoding='utf-8') as f:
            json.dump(blacklist, f, ensure_ascii=False, indent=2)
    except:
        pass

def is_blacklisted(user_id):
    return user_id in load_blacklist()

def load_player_history():
    if not os.path.exists(HISTORY_FILE):
        return {}
    try:
        with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return {}

def save_player_history(history):
    try:
        with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
    except:
        pass

def add_to_history(nick, action, details):
    history = load_player_history()
    if nick not in history:
        history[nick] = []
    history[nick].append({
        "action": action,
        "details": details,
        "timestamp": datetime.now().strftime("%d.%m.%Y %H:%M:%S")
    })
    if len(history[nick]) > 50:
        history[nick] = history[nick][-50:]
    save_player_history(history)

def load_stats():
    if not os.path.exists(STATS_FILE):
        return {"daily": {}, "weekly": {}, "monthly": {}, "total_added": 0, "total_removed": 0, "total_exited": 0}
    try:
        with open(STATS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return {"daily": {}, "weekly": {}, "monthly": {}, "total_added": 0, "total_removed": 0, "total_exited": 0}

def save_stats(stats):
    try:
        with open(STATS_FILE, 'w', encoding='utf-8') as f:
            json.dump(stats, f, ensure_ascii=False, indent=2)
    except:
        pass

def update_stats(action):
    stats = load_stats()
    today = date.today().strftime("%d.%m.%Y")
    week = date.today().strftime("%Y-%W")
    month = date.today().strftime("%Y-%m")
    
    if action == "added":
        stats["total_added"] += 1
        if today not in stats["daily"]:
            stats["daily"][today] = {"added": 0, "removed": 0, "exited": 0}
        stats["daily"][today]["added"] += 1
        if week not in stats["weekly"]:
            stats["weekly"][week] = {"added": 0, "removed": 0, "exited": 0}
        stats["weekly"][week]["added"] += 1
        if month not in stats["monthly"]:
            stats["monthly"][month] = {"added": 0, "removed": 0, "exited": 0}
        stats["monthly"][month]["added"] += 1
    elif action == "removed":
        stats["total_removed"] += 1
        if today not in stats["daily"]:
            stats["daily"][today] = {"added": 0, "removed": 0, "exited": 0}
        stats["daily"][today]["removed"] += 1
        if week not in stats["weekly"]:
            stats["weekly"][week] = {"added": 0, "removed": 0, "exited": 0}
        stats["weekly"][week]["removed"] += 1
        if month not in stats["monthly"]:
            stats["monthly"][month] = {"added": 0, "removed": 0, "exited": 0}
        stats["monthly"][month]["removed"] += 1
    elif action == "exited":
        stats["total_exited"] += 1
        if today not in stats["daily"]:
            stats["daily"][today] = {"added": 0, "removed": 0, "exited": 0}
        stats["daily"][today]["exited"] += 1
        if week not in stats["weekly"]:
            stats["weekly"][week] = {"added": 0, "removed": 0, "exited": 0}
        stats["weekly"][week]["exited"] += 1
        if month not in stats["monthly"]:
            stats["monthly"][month] = {"added": 0, "removed": 0, "exited": 0}
        stats["monthly"][month]["exited"] += 1
    
    save_stats(stats)

def load_schedules():
    if not os.path.exists(SCHEDULES_FILE):
        return []
    try:
        with open(SCHEDULES_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return []

def save_schedules(schedules):
    try:
        with open(SCHEDULES_FILE, 'w', encoding='utf-8') as f:
            json.dump(schedules, f, ensure_ascii=False, indent=2)
    except:
        pass

async def log_action(user, action, details):
    if logs_channel:
        embed = discord.Embed(
            title="📝 ЛОГ ДЕЙСТВИЯ",
            description=f"**{user.name}** выполнил команду",
            color=0x3498db,
            timestamp=datetime.now()
        )
        embed.add_field(name="🔧 Действие", value=f"```{action}```", inline=True)
        embed.add_field(name="📄 Детали", value=f"```{details[:100]}```", inline=True)
        await logs_channel.send(embed=embed)

@bot.event
async def on_ready():
    print(f"✅ Бот {bot.user} запущен!")
    await tree.sync()
    print("✅ Слэш-команды синхронизированы!")
    load_config_channels()
    
    bot.loop.create_task(check_changes_periodically())
    bot.loop.create_task(check_daily_notifications())
    bot.loop.create_task(check_tomorrow_exits())
    bot.loop.create_task(check_scheduled_reports())

async def check_changes_periodically():
    await bot.wait_until_ready()
    while not bot.is_closed():
        try:
            await check_all_changes()
            await asyncio.sleep(30)
        except Exception as e:
            print(f"Ошибка: {e}")
            await asyncio.sleep(30)

async def check_daily_notifications():
    await bot.wait_until_ready()
    while not bot.is_closed():
        try:
            now = datetime.now()
            if now.hour == 0 and now.minute == 0:
                await check_today_exits()
                await asyncio.sleep(60)
            await asyncio.sleep(30)
        except Exception as e:
            print(f"Ошибка в daily check: {e}")
            await asyncio.sleep(60)

async def check_tomorrow_exits():
    await bot.wait_until_ready()
    while not bot.is_closed():
        try:
            now = datetime.now()
            if now.hour == 20 and now.minute == 0:
                await send_tomorrow_notification()
                await asyncio.sleep(60)
            await asyncio.sleep(30)
        except Exception as e:
            print(f"Ошибка в tomorrow check: {e}")
            await asyncio.sleep(60)

async def check_scheduled_reports():
    await bot.wait_until_ready()
    while not bot.is_closed():
        try:
            now = datetime.now()
            schedules = load_schedules()
            current_time = now.strftime("%H:%M")
            for schedule in schedules:
                if schedule["time"] == current_time:
                    channel = bot.get_channel(schedule["channel_id"])
                    if channel:
                        await send_daily_report(channel)
            await asyncio.sleep(60)
        except Exception as e:
            print(f"Ошибка в scheduled reports: {e}")
            await asyncio.sleep(60)

async def send_tomorrow_notification():
    if not notification_channel:
        return
    try:
        response = requests.get(CSV_URL, timeout=10)
        response.encoding = 'utf-8'
        response.raise_for_status()
        
        csv_content = response.text
        reader = csv.DictReader(io.StringIO(csv_content))
        all_rows = list(reader)
        
        tomorrow = date.today() + timedelta(days=1)
        tomorrow_str = tomorrow.strftime("%d.%m.%Y")
        exiting_tomorrow = []
        
        for i, row in enumerate(all_rows, start=2):
            игровой_ник = row.get("Игровой ник", "").strip()
            if not игровой_ник:
                continue
            актуальность = row.get("Актуальность", "").strip()
            дата_снятия_str = row.get("Дата снятия", "").strip()
            if tomorrow_str not in дата_снятия_str:
                continue
            if актуальность.lower() == "в чс":
                exiting_tomorrow.append({
                    "ник": игровой_ник,
                    "строка": i,
                    "discord": row.get("Дискорд юз", "-"),
                    "причина": row.get("Причина", "-")[:50]
                })
        
        if exiting_tomorrow:
            embed = discord.Embed(
                title="⏰ УВЕДОМЛЕНИЕ ЗА 24 ЧАСА",
                description=f"**{len(exiting_tomorrow)}** игрок(ов) должны выйти из ЧС ЗАВТРА",
                color=0xff9900,
                timestamp=datetime.now()
            )
            for player in exiting_tomorrow[:10]:
                embed.add_field(
                    name=f"⚠️ {player['ник']}",
                    value=f"┌ **Строка:** #{player['строка']}\n├ **Discord:** {player['discord']}\n└ **Причина:** {player['причина']}",
                    inline=False
                )
            mentions = " ".join([f"<@{user_id}>" for user_id in NOTIFY_USERS])
            await notification_channel.send(content=mentions, embed=embed)
    except Exception as e:
        print(f"Ошибка tomorrow notification: {e}")

async def check_today_exits():
    if not notification_channel:
        return
    try:
        response = requests.get(CSV_URL, timeout=10)
        response.encoding = 'utf-8'
        response.raise_for_status()
        
        csv_content = response.text
        reader = csv.DictReader(io.StringIO(csv_content))
        all_rows = list(reader)
        
        today = date.today()
        today_str = today.strftime("%d.%m.%Y")
        exited_today = []
        
        for i, row in enumerate(all_rows, start=2):
            игровой_ник = row.get("Игровой ник", "").strip()
            if not игровой_ник:
                continue
            актуальность = row.get("Актуальность", "").strip()
            дата_снятия_str = row.get("Дата снятия", "").strip()
            if today_str not in дата_снятия_str:
                continue
            if "вынесен из чс" in актуальность.lower() or "амнистия" in актуальность.lower():
                exited_today.append({
                    "ник": игровой_ник,
                    "строка": i,
                    "discord": row.get("Дискорд юз", "-"),
                    "причина": row.get("Причина", "-")[:50]
                })
        
        if exited_today:
            embed = discord.Embed(
                title="🎉 ВЫХОД ИЗ ЧЕРНОГО СПИСКА",
                description=f"**{len(exited_today)}** игрок(ов) вышли из ЧС сегодня",
                color=0x00ff00,
                timestamp=datetime.now()
            )
            for player in exited_today[:10]:
                embed.add_field(
                    name=f"👤 {player['ник']}",
                    value=f"┌ **Строка:** #{player['строка']}\n├ **Discord:** {player['discord']}\n└ **Причина:** {player['причина']}",
                    inline=False
                )
            mentions = " ".join([f"<@{user_id}>" for user_id in NOTIFY_USERS])
            await notification_channel.send(content=mentions, embed=embed)
    except Exception as e:
        print(f"Ошибка daily check: {e}")

async def get_current_blacklist_with_details():
    try:
        response = requests.get(CSV_URL, timeout=10)
        response.encoding = 'utf-8'
        if response.status_code != 200:
            return []
        
        csv_content = response.text
        reader = csv.DictReader(io.StringIO(csv_content))
        current_rows = list(reader)
        current_players = []
        
        for i, row in enumerate(current_rows, start=2):
            игровой_ник = row.get("Игровой ник", "")
            if not игровой_ник:
                continue
            
            актуальность = row.get("Актуальность", "").lower()
            дата_снятия = row.get("Дата снятия", "").strip()
            is_in_blacklist = True
            
            if "навсегда" in актуальность:
                is_in_blacklist = False
            elif "вынесен из чс" in дата_снятия.lower() or "амнистия" in дата_снятия.lower():
                is_in_blacklist = False
            
            player_data = {
                "ник": игровой_ник,
                "дискорд": row.get("Дискорд юз", "-"),
                "причина": row.get("Причина", "-"),
                "дата_снятия": row.get("Дата снятия", "-"),
                "кто_выдал": row.get("Кто выдал", "-"),
                "актуальность": row.get("Актуальность", "-"),
                "организация": row.get("Организация", "-"),
                "строка": i,
                "is_in_blacklist": is_in_blacklist
            }
            current_players.append(player_data)
        return current_players
    except Exception as e:
        print(f"Ошибка загрузки: {e}")
        return []

async def check_all_changes():
    try:
        current_players = await get_current_blacklist_with_details()
        if not current_players:
            return
        
        previous_state = load_previous_state()
        if not previous_state:
            save_current_state(current_players)
            return
        
        prev_by_nick = {p["ник"].lower(): p for p in previous_state}
        curr_by_nick = {p["ник"].lower(): p for p in current_players}
        
        added = []
        removed = []
        changed = []
        exited = []
        
        for nick, curr in curr_by_nick.items():
            if nick not in prev_by_nick:
                added.append(curr)
                update_stats("added")
                add_to_history(nick, "added", f"Добавлен в ЧС. Причина: {curr['причина'][:100]}")
            else:
                prev = prev_by_nick[nick]
                if prev["is_in_blacklist"] and not curr["is_in_blacklist"]:
                    if notification_channel:
                        await send_instant_notification(curr)
                    exited.append(curr)
                    update_stats("exited")
                    add_to_history(nick, "exited", f"Вышел из ЧС. Дата снятия: {curr['дата_снятия']}")
                
                changes = []
                for field in ["причина", "дата_снятия", "кто_выдал", "актуальность", "организация", "дискорд"]:
                    if curr.get(field) != prev.get(field):
                        changes.append({
                            "поле": field,
                            "было": prev.get(field, "-"),
                            "стало": curr.get(field, "-")
                        })
                if changes:
                    changed.append({
                        "ник": curr['ник'],
                        "строка": curr['строка'],
                        "изменения": changes
                    })
                    add_to_history(nick, "changed", f"Изменены данные")
        
        for nick, prev in prev_by_nick.items():
            if nick not in curr_by_nick:
                removed.append(prev)
                update_stats("removed")
                add_to_history(nick, "removed", "Удален из таблицы")
        
        save_current_state(current_players)
        
        if moderation_channel and (added or removed or changed or exited):
            await send_all_changes_one_message(added, removed, changed, exited)
    except Exception as e:
        print(f"Ошибка: {e}")

async def send_instant_notification(player):
    if not notification_channel:
        return
    try:
        embed = discord.Embed(
            title="⚠️ СРОЧНОЕ УВЕДОМЛЕНИЕ",
            description=f"**{player['ник']}** вышел из черного списка!",
            color=0xff0000,
            timestamp=datetime.now()
        )
        embed.add_field(name="👤 Игрок", value=f"```{player['ник']}```", inline=True)
        embed.add_field(name="📍 Строка", value=f"```#{player['строка']}```", inline=True)
        embed.add_field(name="💬 Discord", value=f"```{player['дискорд'][:50]}```", inline=True)
        embed.add_field(name="📅 Дата снятия", value=f"```{player['дата_снятия']}```", inline=True)
        embed.add_field(name="📝 Причина", value=f"```{player['причина'][:100]}```", inline=False)
        mentions = " ".join([f"<@{user_id}>" for user_id in NOTIFY_USERS])
        await notification_channel.send(content=mentions, embed=embed)
    except Exception as e:
        print(f"Ошибка отправки уведомления: {e}")

def load_previous_state():
    if not os.path.exists(PREVIOUS_STATE_FILE):
        return []
    try:
        with open(PREVIOUS_STATE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return []

def save_current_state(players):
    try:
        with open(PREVIOUS_STATE_FILE, 'w', encoding='utf-8') as f:
            json.dump(players, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Ошибка сохранения: {e}")

async def send_all_changes_one_message(added, removed, changed, exited):
    if not moderation_channel:
        return
    try:
        embed = discord.Embed(
            title="📊 ИЗМЕНЕНИЯ В ТАБЛИЦЕ",
            color=0x3498db,
            timestamp=datetime.now()
        )
        stats_text = ""
        if added: stats_text += f"✅ **+{len(added)}** добавлено\n"
        if removed: stats_text += f"❌ **-{len(removed)}** удалено\n"
        if changed: stats_text += f"✏️ **{len(changed)}** изменено\n"
        if exited: stats_text += f"👤 **{len(exited)}** вышло из ЧС\n"
        embed.add_field(name="📈 Статистика", value=stats_text if stats_text else "Нет изменений", inline=False)
        
        for player in changed[:5]:
            changes_text = ""
            for change in player['изменения']:
                changes_text += f"└ {change['поле']}: {change['было'][:30]} → {change['стало'][:30]}\n"
            embed.add_field(
                name=f"✏️ {player['ник']} (стр.{player['строка']})",
                value=f"```{changes_text[:500]}```" if changes_text else "Изменения не указаны",
                inline=False
            )
        for player in added[:5]:
            embed.add_field(
                name=f"✅ {player['ник']} (стр.{player['строка']})",
                value=f"┌ **Discord:** {player['дискорд'][:50]}\n├ **Причина:** {player['причина'][:50]}\n└ **Выдал:** {player['кто_выдал'][:30]}",
                inline=False
            )
        for player in removed[:5]:
            embed.add_field(
                name=f"❌ {player['ник']} (стр.{player['строка']})",
                value="Запись была удалена из таблицы",
                inline=False
            )
        await moderation_channel.send(embed=embed)
    except Exception as e:
        print(f"Ошибка отправки: {e}")

class BlacklistView(View):
    def __init__(self, player_data):
        super().__init__()
        self.player_data = player_data
    
    @discord.ui.button(label="Подробнее", style=discord.ButtonStyle.primary, emoji="📋")
    async def details_button(self, interaction: discord.Interaction, button: Button):
        embed = discord.Embed(
            title=f"📊 ДЕТАЛЬНАЯ ИНФОРМАЦИЯ",
            description=f"**{self.player_data['ник']}**",
            color=0x3498db
        )
        for key, value in self.player_data.items():
            if key != "ник":
                embed.add_field(name=key, value=f"```{str(value)[:100]}```", inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @discord.ui.button(label="История", style=discord.ButtonStyle.secondary, emoji="📜")
    async def history_button(self, interaction: discord.Interaction, button: Button):
        history = load_player_history()
        player_history = history.get(self.player_data['ник'], [])
        if not player_history:
            await interaction.response.send_message(f"Нет истории для {self.player_data['ник']}", ephemeral=True)
            return
        embed = discord.Embed(
            title=f"📜 ИСТОРИЯ ИГРОКА",
            description=f"**{self.player_data['ник']}**",
            color=0x9b59b6
        )
        for event in player_history[-5:]:
            embed.add_field(
                name=f"🕐 {event['timestamp']}",
                value=f"┌ **Действие:** {event['action']}\n└ **Детали:** {event['details'][:100]}",
                inline=False
            )
        await interaction.response.send_message(embed=embed, ephemeral=True)

async def send_daily_report(channel):
    stats = load_stats()
    today = date.today().strftime("%d.%m.%Y")
    day_stats = stats["daily"].get(today, {"added": 0, "removed": 0, "exited": 0})
    embed = discord.Embed(
        title="📊 ЕЖЕДНЕВНЫЙ ОТЧЕТ",
        description=f"Отчет за {today}",
        color=0x3498db,
        timestamp=datetime.now()
    )
    embed.add_field(name="✅ Добавлено в ЧС", value=f"```{day_stats['added']}```", inline=True)
    embed.add_field(name="❌ Удалено из ЧС", value=f"```{day_stats['removed']}```", inline=True)
    embed.add_field(name="👤 Вышло из ЧС", value=f"```{day_stats['exited']}```", inline=True)
    await channel.send(embed=embed)

@tree.command(name="next", description="Показать игроков, которые должны выйти из ЧС сегодня")
async def slash_next(interaction: discord.Interaction):
    if is_blacklisted(interaction.user.id):
        await interaction.response.send_message("❌ Вы в черном списке бота", ephemeral=True)
        return
    await interaction.response.defer(thinking=True)
    await log_action(interaction.user, "/next", "Просмотр игроков на сегодня")
    
    try:
        response = requests.get(CSV_URL, timeout=10)
        response.encoding = 'utf-8'
        response.raise_for_status()
        csv_content = response.text
        reader = csv.DictReader(io.StringIO(csv_content))
        all_rows = list(reader)
        
        if not all_rows:
            embed = discord.Embed(title="❌ Ошибка", description="Таблица пуста", color=0xff0000)
            await interaction.followup.send(embed=embed)
            return
        
        today = date.today()
        today_str = today.strftime("%d.%m.%Y")
        exiting_today = []
        
        for i, row in enumerate(all_rows, start=2):
            игровой_ник = row.get("Игровой ник", "").strip()
            if not игровой_ник:
                continue
            актуальность = row.get("Актуальность", "").strip()
            if актуальность.lower() != "в чс":
                continue
            дата_снятия_str = row.get("Дата снятия", "").strip()
            if today_str not in дата_снятия_str:
                continue
            exiting_today.append({
                "ник": игровой_ник,
                "строка": i,
                "discord": row.get("Дискорд юз", "-").strip(),
                "причина": row.get("Причина", "-").strip()[:50]
            })
        
        embed = discord.Embed(title="📅 ДОЛЖНЫ ВЫЙТИ СЕГОДНЯ", color=0x00ff00, timestamp=datetime.now())
        embed.add_field(name="📆 Дата", value=f"```{today_str}```", inline=True)
        
        if exiting_today:
            exiting_today.sort(key=lambda x: x["ник"])
            embed.add_field(name="👥 Количество", value=f"```{len(exiting_today)} игроков```", inline=True)
            for player in exiting_today[:10]:
                embed.add_field(
                    name=f"⏳ {player['ник']}",
                    value=f"┌ **Строка:** #{player['строка']}\n├ **Discord:** {player['discord'][:50]}\n└ **Причина:** {player['причина']}",
                    inline=False
                )
            if len(exiting_today) > 10:
                embed.set_footer(text=f"Показаны первые 10 из {len(exiting_today)}")
            mentions = " ".join([f"<@{user_id}>" for user_id in NOTIFY_USERS])
            await interaction.followup.send(content=mentions, embed=embed)
        else:
            embed.add_field(name="ℹ️ Информация", value="Нет игроков, которые должны выйти из ЧС сегодня", inline=False)
            await interaction.followup.send(embed=embed)
    except Exception as e:
        embed = discord.Embed(title="❌ Ошибка", description=str(e), color=0xff0000)
        await interaction.followup.send(embed=embed)

@tree.command(name="overdue", description="Показать просроченные записи в черном списке")
async def slash_overdue(interaction: discord.Interaction):
    if is_blacklisted(interaction.user.id):
        await interaction.response.send_message("❌ Вы в черном списке бота", ephemeral=True)
        return
    await interaction.response.defer(thinking=True)
    
    try:
        response = requests.get(CSV_URL, timeout=10)
        response.encoding = 'utf-8'
        response.raise_for_status()
        csv_content = response.text
        reader = csv.DictReader(io.StringIO(csv_content))
        all_rows = list(reader)
        
        if not all_rows:
            embed = discord.Embed(title="❌ Ошибка", description="Таблица пуста", color=0xff0000)
            await interaction.followup.send(embed=embed)
            return
        
        today = date.today()
        просроченные_в_чс = []
        
        for i, row in enumerate(all_rows, start=2):
            игровой_ник = row.get("Игровой ник", "").strip()
            if not игровой_ник:
                continue
            дата_снятия_str = row.get("Дата снятия", "").strip()
            актуальность = row.get("Актуальность", "").strip().lower()
            
            if not дата_снятия_str or дата_снятия_str == "-":
                continue
            if "навсегда" in актуальность:
                continue
            if "вынесен из чс" in актуальность or "амнистия" in актуальность:
                continue
            if "в чс" not in актуальность:
                continue
            
            try:
                for fmt in ["%d.%m.%Y", "%d.%m.%y", "%Y-%m-%d"]:
                    try:
                        date_part = дата_снятия_str.split()[0]
                        дата_снятия = datetime.strptime(date_part, fmt).date()
                        break
                    except:
                        continue
                else:
                    continue
                if дата_снятия < today:
                    просроченные_в_чс.append({
                        "ник": игровой_ник,
                        "строка": i,
                        "дата": дата_снятия_str,
                        "статус": row.get("Актуальность", "-"),
                        "discord": row.get("Дискорд юз", "-").strip()[:50]
                    })
            except:
                continue
        
        embed = discord.Embed(title="⏰ ПРОСРОЧЕННЫЕ ЗАПИСИ", color=0xff9900, timestamp=datetime.now())
        embed.add_field(name="🔴 Найдено", value=f"```{len(просроченные_в_чс)} записей```", inline=True)
        
        if просроченные_в_чс:
            for player in просроченные_в_чс[:10]:
                embed.add_field(
                    name=f"⚠️ {player['ник']} (стр.{player['строка']})",
                    value=f"┌ **Дата снятия:** {player['дата']}\n├ **Статус:** {player['статус']}\n└ **Discord:** {player['discord']}",
                    inline=False
                )
        else:
            embed.add_field(name="✅ Отлично!", value="Нет просроченных записей", inline=False)
        await interaction.followup.send(embed=embed)
    except Exception as e:
        embed = discord.Embed(title="❌ Ошибка", description=str(e), color=0xff0000)
        await interaction.followup.send(embed=embed)

@tree.command(name="ds_overdue", description="Показать Discord'ы просроченных записей")
async def slash_ds_overdue(interaction: discord.Interaction):
    if is_blacklisted(interaction.user.id):
        await interaction.response.send_message("❌ Вы в черном списке бота", ephemeral=True)
        return
    await interaction.response.defer(thinking=True)
    
    try:
        response = requests.get(CSV_URL, timeout=10)
        response.encoding = 'utf-8'
        response.raise_for_status()
        csv_content = response.text
        reader = csv.DictReader(io.StringIO(csv_content))
        all_rows = list(reader)
        
        today = date.today()
        просроченные_дискорды = []
        
        for i, row in enumerate(all_rows, start=2):
            игровой_ник = row.get("Игровой ник", "")
            if not игровой_ник:
                continue
            дата_снятия_str = row.get("Дата снятия", "").strip()
            актуальность = row.get("Актуальность", "").strip().lower()
            
            if not дата_снятия_str or дата_снятия_str == "-":
                continue
            if "навсегда" in актуальность:
                continue
            if "вынесен из чс" in актуальность or "амнистия" in актуальность:
                continue
            
            try:
                for fmt in ["%d.%m.%Y", "%d.%m.%y", "%Y-%m-%d"]:
                    try:
                        дата_снятия = datetime.strptime(дата_снятия_str.split()[0], fmt).date()
                        break
                    except:
                        continue
                else:
                    continue
                if дата_снятия < today:
                    discord_value = row.get("Дискорд юз", "").strip()
                    if discord_value and discord_value != "-":
                        просроченные_дискорды.append(discord_value)
            except:
                continue
        
        embed = discord.Embed(title="📋 DISCORD'Ы ПРОСРОЧЕННЫХ ЗАПИСЕЙ", color=0x9b59b6, timestamp=datetime.now())
        
        if просроченные_дискорды:
            уникальные = list(set(просроченные_дискорды))
            уникальные.sort()
            embed.add_field(name="🔴 Найдено", value=f"```{len(уникальные)} Discord```", inline=True)
            discord_list = "\n".join([f"├ {d}" for d in уникальные[:25]])
            embed.add_field(name="📝 Список", value=f"```\n{discord_list}\n```", inline=False)
        else:
            embed.add_field(name="✅ Отлично!", value="Нет Discord'ов для отображения", inline=False)
        await interaction.followup.send(embed=embed)
    except Exception as e:
        embed = discord.Embed(title="❌ Ошибка", description=str(e), color=0xff0000)
        await interaction.followup.send(embed=embed)

@tree.command(name="info", description="Получить информацию об игроке (можно несколько через запятую, пробел или новой строкой)")
async def slash_info(interaction: discord.Interaction, ники: str):
    if is_blacklisted(interaction.user.id):
        await interaction.response.send_message("❌ Вы в черном списке бота", ephemeral=True)
        return
    await interaction.response.defer(thinking=True)
    
    try:
        if '\n' in ники:
            names_list = [n.strip() for n in ники.split('\n') if n.strip()]
        elif ',' in ники:
            names_list = [n.strip() for n in ники.split(',') if n.strip()]
        else:
            names_list = [n.strip() for n in ники.split() if n.strip()]
        
        if len(names_list) > 50:
            await interaction.followup.send("❌ Можно проверить не более 50 ников за раз")
            return
        
        response = requests.get(CSV_URL, timeout=10)
        response.encoding = 'utf-8'
        response.raise_for_status()
        csv_content = response.text
        reader = csv.DictReader(io.StringIO(csv_content))
        all_rows = list(reader)
        
        if not all_rows:
            embed = discord.Embed(title="❌ Ошибка", description="Таблица пуста", color=0xff0000)
            await interaction.followup.send(embed=embed)
            return
        
        found_players = []
        not_found = []
        
        for search_name in names_list:
            found = False
            search_lower = search_name.lower()
            
            for i, row in enumerate(all_rows, start=2):
                игровой_ник = row.get("Игровой ник", "")
                if игровой_ник and игровой_ник.lower() == search_lower:
                    актуальность = row.get("Актуальность", "-")
                    
                    player_data = {
                        "ник": игровой_ник,
                        "строка": i,
                        "discord": row.get("Дискорд юз", "-"),
                        "организация": row.get("Организация", "-"),
                        "причина": row.get("Причина", "-")[:80],
                        "дата_снятия": row.get("Дата снятия", "-"),
                        "кто_выдал": row.get("Кто выдал", "-"),
                        "актуальность": актуальность
                    }
                    found_players.append(player_data)
                    found = True
                    break
            
            if not found:
                not_found.append(search_name)
        
        if len(names_list) == 1 and found_players:
            player = found_players[0]
            актуальность = player["актуальность"]
            color = 0x00ff00 if "вынесен" in актуальность.lower() else (0xff0000 if "чс" in актуальность.lower() else 0x3498db)
            
            embed = discord.Embed(
                title=f"📊 ИНФОРМАЦИЯ ОБ ИГРОКЕ",
                description=f"**{player['ник']}**",
                color=color,
                timestamp=datetime.now()
            )
            embed.add_field(name="📍 Строка", value=f"```#{player['строка']}```", inline=True)
            embed.add_field(name="💬 Discord", value=f"```{player['discord'][:50]}```", inline=True)
            embed.add_field(name="🏢 Организация", value=f"```{player['организация'][:50]}```", inline=True)
            embed.add_field(name="📝 Причина", value=f"```{player['причина']}```", inline=False)
            embed.add_field(name="📅 Дата снятия", value=f"```{player['дата_снятия']}```", inline=True)
            embed.add_field(name="👮 Кто выдал", value=f"```{player['кто_выдал'][:50]}```", inline=True)
            embed.add_field(name="📌 Актуальность", value=f"```{player['актуальность']}```", inline=True)
            
            view = BlacklistView(player)
            await interaction.followup.send(embed=embed, view=view)
            
        elif len(found_players) > 0:
            embed = discord.Embed(
                title=f"📊 РЕЗУЛЬТАТЫ ПРОВЕРКИ",
                description=f"Найдено {len(found_players)} из {len(names_list)} игроков",
                color=0x00ff00,
                timestamp=datetime.now()
            )
            
            for player in found_players[:15]:
                status_emoji = "🔴" if "в чс" in player["актуальность"].lower() else ("🟢" if "вынесен" in player["актуальность"].lower() else "⚪")
                embed.add_field(
                    name=f"{status_emoji} {player['ник']}",
                    value=f"┌ **Строка:** #{player['строка']}\n├ **Discord:** {player['discord'][:40]}\n├ **Статус:** {player['актуальность']}\n└ **Причина:** {player['причина'][:60]}",
                    inline=False
                )
            
            if not_found:
                embed.add_field(
                    name="❌ Не найдены",
                    value="\n".join([f"├ {n}" for n in not_found[:10]]),
                    inline=False
                )
            
            if len(found_players) > 15:
                embed.set_footer(text=f"Показаны первые 15 из {len(found_players)}")
            
            await interaction.followup.send(embed=embed)
            
        elif not_found:
            matches = []
            search_lower = not_found[0].lower()
            for i, row in enumerate(all_rows, start=2):
                игровой_ник = row.get("Игровой ник", "")
                if игровой_ник and search_lower in игровой_ник.lower():
                    matches.append(игровой_ник)
            
            if matches:
                embed = discord.Embed(
                    title="🔍 НАЙДЕНЫ ПОХОЖИЕ ИГРОКИ",
                    description=f"По запросу **{not_found[0]}** найдено {len(matches)} совпадений",
                    color=0xff9900
                )
                embed.add_field(name="📝 Список", value="\n".join([f"├ {m}" for m in matches[:20]]), inline=False)
                await interaction.followup.send(embed=embed)
            else:
                embed = discord.Embed(
                    title="❌ ИГРОКИ НЕ НАЙДЕНЫ",
                    description=f"Не найдены: {', '.join(not_found[:5])}",
                    color=0xff0000
                )
                await interaction.followup.send(embed=embed)
        
    except Exception as e:
        embed = discord.Embed(title="❌ Ошибка", description=str(e), color=0xff0000)
        await interaction.followup.send(embed=embed)

@tree.command(name="help", description="Показать список всех команд")
async def slash_help(interaction: discord.Interaction):
    embed = discord.Embed(title="🤖 ПОМОЩЬ ПО КОМАНДАМ БОТА", description="Все доступные команды", color=0x00ff00, timestamp=datetime.now())
    embed.add_field(name="📅 /next", value="Показать игроков, которые должны выйти из ЧС сегодня", inline=False)
    embed.add_field(name="⏰ /overdue", value="Показать просроченные записи", inline=False)
    embed.add_field(name="📋 /ds_overdue", value="Показать Discord'ы просроченных записей", inline=False)
    embed.add_field(name="ℹ️ /info [ники]", value="Получить информацию об игроке (можно несколько через запятую, пробел или новой строкой)", inline=False)
    embed.add_field(name="📝 /log", value="Настроить канал для логов модерации", inline=False)
    embed.add_field(name="🚫 /unlog", value="Отключить логи модерации", inline=False)
    embed.add_field(name="🔔 /notification", value="Настроить канал для уведомлений", inline=False)
    embed.add_field(name="🔕 /unnotification", value="Отключить уведомления", inline=False)
    embed.add_field(name="📝 /logs", value="Настроить канал для логов действий", inline=False)
    embed.add_field(name="📊 /stats", value="Показать статистику", inline=False)
    embed.add_field(name="📜 /history [ник]", value="История изменений игрока", inline=False)
    embed.add_field(name="🔍 /search [часть]", value="Поиск по части ника", inline=False)
    embed.add_field(name="📎 /export", value="Экспорт данных в CSV", inline=False)
    embed.add_field(name="⏲️ /schedule_report [ЧЧ:ММ]", value="Настроить ежедневный отчет", inline=False)
    embed.add_field(name="🔧 /setrole [роль]", value="Установить роль для уведомлений", inline=False)
    embed.add_field(name="❓ /help", value="Показать это сообщение", inline=False)
    await interaction.response.send_message(embed=embed)

@tree.command(name="log", description="Настроить текущий канал для получения логов модерации")
async def slash_log(interaction: discord.Interaction):
    global moderation_channel
    moderation_channel = interaction.channel
    save_channels_config()
    embed = discord.Embed(title="✅ КАНАЛ НАСТРОЕН", description=f"Канал #{interaction.channel.name} будет получать логи модерации", color=0x00ff00)
    await interaction.response.send_message(embed=embed)

@tree.command(name="unlog", description="Отключить отправку логов модерации")
async def slash_unlog(interaction: discord.Interaction):
    global moderation_channel
    if moderation_channel and moderation_channel.id == interaction.channel.id:
        moderation_channel = None
        save_channels_config()
        embed = discord.Embed(title="❌ КАНАЛ ОТКЛЮЧЕН", description="Логи модерации больше не будут отправляться", color=0xff0000)
        await interaction.response.send_message(embed=embed)
    else:
        embed = discord.Embed(title="⚠️ ОШИБКА", description="Этот канал не настроен для логов", color=0xffaa00)
        await interaction.response.send_message(embed=embed, ephemeral=True)

@tree.command(name="notification", description="Настроить канал для уведомлений о выходе из ЧС")
async def slash_notification(interaction: discord.Interaction):
    global notification_channel
    notification_channel = interaction.channel
    save_channels_config()
    embed = discord.Embed(title="✅ КАНАЛ НАСТРОЕН", description=f"Канал #{interaction.channel.name} будет получать уведомления", color=0x00ff00)
    await interaction.response.send_message(embed=embed)

@tree.command(name="unnotification", description="Отключить уведомления о выходе из ЧС")
async def slash_unnotification(interaction: discord.Interaction):
    global notification_channel
    if notification_channel and notification_channel.id == interaction.channel.id:
        notification_channel = None
        save_channels_config()
        embed = discord.Embed(title="❌ КАНАЛ ОТКЛЮЧЕН", description="Уведомления больше не будут отправляться", color=0xff0000)
        await interaction.response.send_message(embed=embed)
    else:
        embed = discord.Embed(title="⚠️ ОШИБКА", description="Этот канал не настроен для уведомлений", color=0xffaa00)
        await interaction.response.send_message(embed=embed, ephemeral=True)

@tree.command(name="logs", description="Настроить канал для логов действий бота")
async def slash_logs(interaction: discord.Interaction):
    global logs_channel
    logs_channel = interaction.channel
    save_channels_config()
    embed = discord.Embed(title="✅ КАНАЛ ДЛЯ ЛОГОВ НАСТРОЕН", description=f"Логи действий будут отправляться в #{interaction.channel.name}", color=0x00ff00)
    await interaction.response.send_message(embed=embed)

@tree.command(name="stats", description="Показать статистику ЧС")
async def slash_stats(interaction: discord.Interaction):
    if is_blacklisted(interaction.user.id):
        await interaction.response.send_message("❌ Вы в черном списке бота", ephemeral=True)
        return
    stats = load_stats()
    embed = discord.Embed(title="📊 СТАТИСТИКА ЧС", color=0x3498db, timestamp=datetime.now())
    embed.add_field(name="✅ Всего добавлено", value=f"```{stats['total_added']}```", inline=True)
    embed.add_field(name="❌ Всего удалено", value=f"```{stats['total_removed']}```", inline=True)
    embed.add_field(name="👤 Всего вышло", value=f"```{stats['total_exited']}```", inline=True)
    await interaction.response.send_message(embed=embed)

@tree.command(name="history", description="История изменений игрока")
async def slash_history(interaction: discord.Interaction, ник: str):
    if is_blacklisted(interaction.user.id):
        await interaction.response.send_message("❌ Вы в черном списке бота", ephemeral=True)
        return
    history = load_player_history()
    player_history = history.get(ник, [])
    if not player_history:
        embed = discord.Embed(title="📜 ИСТОРИЯ ИГРОКА", description=f"Нет истории для **{ник}**", color=0xff9900)
        await interaction.response.send_message(embed=embed)
        return
    embed = discord.Embed(title=f"📜 ИСТОРИЯ ИГРОКА", description=f"**{ник}** - {len(player_history)} событий", color=0x9b59b6, timestamp=datetime.now())
    for event in player_history[-10:]:
        embed.add_field(name=f"🕐 {event['timestamp']}", value=f"┌ **Действие:** {event['action']}\n└ **Детали:** {event['details'][:100]}", inline=False)
    await interaction.response.send_message(embed=embed)

@tree.command(name="search", description="Поиск игроков по части ника")
async def slash_search(interaction: discord.Interaction, часть: str):
    if is_blacklisted(interaction.user.id):
        await interaction.response.send_message("❌ Вы в черном списке бота", ephemeral=True)
        return
    await interaction.response.defer(thinking=True)
    try:
        response = requests.get(CSV_URL, timeout=10)
        response.encoding = 'utf-8'
        response.raise_for_status()
        csv_content = response.text
        reader = csv.DictReader(io.StringIO(csv_content))
        all_rows = list(reader)
        matches = []
        search_lower = часть.lower()
        for i, row in enumerate(all_rows, start=2):
            игровой_ник = row.get("Игровой ник", "")
            if игровой_ник and search_lower in игровой_ник.lower():
                matches.append({"ник": игровой_ник, "строка": i, "статус": row.get("Актуальность", "-")})
        embed = discord.Embed(title="🔍 РЕЗУЛЬТАТЫ ПОИСКА", description=f"По запросу **{часть}** найдено {len(matches)} игроков", color=0x3498db, timestamp=datetime.now())
        for match in matches[:15]:
            embed.add_field(name=f"👤 {match['ник']}", value=f"┌ **Строка:** #{match['строка']}\n└ **Статус:** {match['статус']}", inline=False)
        await interaction.followup.send(embed=embed)
    except Exception as e:
        embed = discord.Embed(title="❌ Ошибка", description=str(e), color=0xff0000)
        await interaction.followup.send(embed=embed)

@tree.command(name="export", description="Экспортировать текущий ЧС в файл")
async def slash_export(interaction: discord.Interaction):
    if is_blacklisted(interaction.user.id):
        await interaction.response.send_message("❌ Вы в черном списке бота", ephemeral=True)
        return
    await interaction.response.defer(thinking=True)
    try:
        current_players = await get_current_blacklist_with_details()
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["Ник", "Discord", "Причина", "Дата снятия", "Кто выдал", "Актуальность", "Организация", "Строка"])
        for player in current_players:
            writer.writerow([player["ник"], player["дискорд"], player["причина"], player["дата_снятия"], player["кто_выдал"], player["актуальность"], player["организация"], player["строка"]])
        output.seek(0)
        file = discord.File(io.BytesIO(output.getvalue().encode('utf-8')), filename=f"blacklist_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
        await interaction.followup.send(content="📊 Экспорт данных ЧС:", file=file)
    except Exception as e:
        embed = discord.Embed(title="❌ Ошибка", description=str(e), color=0xff0000)
        await interaction.followup.send(embed=embed)

@tree.command(name="schedule_report", description="Настроить ежедневный отчет")
async def schedule_report(interaction: discord.Interaction, время: str):
    if interaction.user.id not in NOTIFY_USERS:
        await interaction.response.send_message("❌ У вас нет прав", ephemeral=True)
        return
    if not re.match(r'^\d{2}:\d{2}$', время):
        await interaction.response.send_message("❌ Неверный формат. Используйте ЧЧ:ММ", ephemeral=True)
        return
    schedules = load_schedules()
    schedules.append({"time": время, "channel_id": interaction.channel.id, "user_id": interaction.user.id})
    save_schedules(schedules)
    embed = discord.Embed(title="✅ РАСПИСАНИЕ НАСТРОЕНО", description=f"Отчет будет отправляться в {время}", color=0x00ff00)
    await interaction.response.send_message(embed=embed)

@tree.command(name="setrole", description="Установить роль для уведомлений")
async def set_role(interaction: discord.Interaction, роль: discord.Role):
    if interaction.user.id not in NOTIFY_USERS:
        await interaction.response.send_message("❌ У вас нет прав", ephemeral=True)
        return
    global NOTIFY_ROLE_ID
    NOTIFY_ROLE_ID = роль.id
    embed = discord.Embed(title="✅ РОЛЬ УСТАНОВЛЕНА", description=f"Роль {роль.mention} будет получать уведомления", color=0x00ff00)
    await interaction.response.send_message(embed=embed)

if __name__ == "__main__":
    print("🚀 Запуск бота...")
    bot.run(TOKEN)