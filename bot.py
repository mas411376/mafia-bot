import sqlite3
import math
import io
import os
import logging
import random
import html
from datetime import datetime
import matplotlib.pyplot as plt
from telegram import (
    Update,
    BotCommand,
    BotCommandScopeDefault,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

TOKEN = "8842154275:AAFW0Pi9C6TDbCYMtgRJexpel3ut2BIS_M4"
ADMIN_ID = 61730708
ADMIN_ID_2 = 5525697104  # ادمین دوم با دسترسی محدود به ثبت و مدیریت بازی‌ها

TUTORIAL_CHANNEL_URL = "https://t.me/MASamoozesh"
GROUP_INVITE_URL = "https://t.me/+cvkbTFtXhqhkZGI0"
WEBSITE_URL = "https://roundgangs.com"
BANNER_PATH = "banner.jpg"

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

SCENARIO_LIST = [
    "بازپرس",
    "تفنگدار (تکاور)",
    "مذاکره",
    "کاپو",
    "نماینده",
    "شاهنامه",
    "رنک",
    "نقابدار",
    "ارتش سری",
    "هانیبال",
    "دربار",
    "الکلاسیکو (تسلا)",
    "نیمروز مهم (دورو)",
    "تارگت",
    "کاور",
    "پرطرفدار",
    "زودیاک",
    "اختاپوس مخوف (سندیکا)",
    "جایزه سر رئیس",
    "میتیک",
]


def init_db():
  with sqlite3.connect("mafia_league.db") as conn:
    c = conn.cursor()
    c.execute("""
            CREATE TABLE IF NOT EXISTS league_settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)
    c.execute(
        "INSERT OR IGNORE INTO league_settings (key, value) VALUES"
        " ('current_season', '1')"
    )

    c.execute("""
            CREATE TABLE IF NOT EXISTS players (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                name TEXT UNIQUE,
                raw_score INTEGER DEFAULT 0,
                total_games INTEGER DEFAULT 0,
                wins INTEGER DEFAULT 0,
                losses INTEGER DEFAULT 0,
                mvp_count INTEGER DEFAULT 0,
                axe_count INTEGER DEFAULT 0,
                unfair_count INTEGER DEFAULT 0,
                artin_count INTEGER DEFAULT 0,
                citizen_games INTEGER DEFAULT 0,
                citizen_wins INTEGER DEFAULT 0,
                mafia_games INTEGER DEFAULT 0,
                mafia_wins INTEGER DEFAULT 0,
                independent_games INTEGER DEFAULT 0,
                independent_wins INTEGER DEFAULT 0,
                current_streak INTEGER DEFAULT 0,
                best_streak INTEGER DEFAULT 0,
                night1_shots INTEGER DEFAULT 0,
                night1_outs INTEGER DEFAULT 0,
                chaos_count INTEGER DEFAULT 0,
                chaos_selected_count INTEGER DEFAULT 0,
                chaos_win_impact_count INTEGER DEFAULT 0,
                advanced_skill_score REAL DEFAULT 1000.0
            )
        """)
    c.execute("""
            CREATE TABLE IF NOT EXISTS match_history (
                match_id INTEGER PRIMARY KEY AUTOINCREMENT,
                season INTEGER DEFAULT 1,
                scenario_name TEXT DEFAULT 'کلاسیک',
                winning_side TEXT,
                end_mode TEXT DEFAULT 'روند عادی',
                chaos_players TEXT,
                chaos_selected TEXT,
                chaos_win_impact TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    c.execute("""
            CREATE TABLE IF NOT EXISTS match_participants (
                match_id INTEGER,
                player_name TEXT,
                side TEXT,
                won INTEGER,
                is_mvp INTEGER,
                is_axe INTEGER DEFAULT 0,
                is_unfair INTEGER DEFAULT 0,
                is_artin INTEGER DEFAULT 0,
                rating_after REAL,
                night1_shot INTEGER DEFAULT 0,
                night1_out INTEGER DEFAULT 0,
                FOREIGN KEY (match_id) REFERENCES match_history(match_id)
            )
        """)
    c.execute("""
            CREATE TABLE IF NOT EXISTS season_archives (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                season INTEGER,
                player_name TEXT,
                final_rank INTEGER,
                final_rating REAL,
                raw_score INTEGER,
                total_games INTEGER,
                wins INTEGER,
                losses INTEGER,
                mvp_count INTEGER,
                axe_count INTEGER DEFAULT 0,
                unfair_count INTEGER DEFAULT 0,
                artin_count INTEGER DEFAULT 0,
                advanced_skill_score REAL DEFAULT 1000.0,
                archived_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    c.execute("""
            CREATE TABLE IF NOT EXISTS bot_analytics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                feature_name TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

    c.execute("PRAGMA table_info(players)")
    pl_cols = [col[1] for col in c.fetchall()]
    if "axe_count" not in pl_cols:
      c.execute("ALTER TABLE players ADD COLUMN axe_count INTEGER DEFAULT 0")
    if "unfair_count" not in pl_cols:
      c.execute("ALTER TABLE players ADD COLUMN unfair_count INTEGER DEFAULT 0")
    if "artin_count" not in pl_cols:
      c.execute("ALTER TABLE players ADD COLUMN artin_count INTEGER DEFAULT 0")

    c.execute("PRAGMA table_info(match_participants)")
    p_cols = [col[1] for col in c.fetchall()]
    if "is_axe" not in p_cols:
      c.execute("ALTER TABLE match_participants ADD COLUMN is_axe INTEGER DEFAULT 0")
    if "is_unfair" not in p_cols:
      c.execute("ALTER TABLE match_participants ADD COLUMN is_unfair INTEGER DEFAULT 0")
    if "is_artin" not in p_cols:
      c.execute("ALTER TABLE match_participants ADD COLUMN is_artin INTEGER DEFAULT 0")

    c.execute("PRAGMA table_info(season_archives)")
    sa_cols = [col[1] for col in c.fetchall()]
    if "axe_count" not in sa_cols:
      c.execute("ALTER TABLE season_archives ADD COLUMN axe_count INTEGER DEFAULT 0")
    if "unfair_count" not in sa_cols:
      c.execute("ALTER TABLE season_archives ADD COLUMN unfair_count INTEGER DEFAULT 0")
    if "artin_count" not in sa_cols:
      c.execute("ALTER TABLE season_archives ADD COLUMN artin_count INTEGER DEFAULT 0")

    conn.commit()


init_db()


def log_feature_click(user_id: int, feature_name: str):
  try:
    with sqlite3.connect("mafia_league.db") as conn:
      c = conn.cursor()
      c.execute(
          "INSERT INTO bot_analytics (user_id, feature_name) VALUES (?, ?)",
          (user_id, feature_name),
      )
      conn.commit()
  except Exception as e:
    logging.error(f"Error logging analytics: {e}")


def get_current_season():
  with sqlite3.connect("mafia_league.db") as conn:
    c = conn.cursor()
    c.execute("SELECT value FROM league_settings WHERE key = 'current_season'")
    row = c.fetchone()
    return int(row[0]) if row else 1


def set_current_season(season_num: int):
  with sqlite3.connect("mafia_league.db") as conn:
    c = conn.cursor()
    c.execute(
        "UPDATE league_settings SET value = ? WHERE key = 'current_season'",
        (str(season_num),),
    )
    conn.commit()


def get_available_seasons():
  cur = get_current_season()
  with sqlite3.connect("mafia_league.db") as conn:
    c = conn.cursor()
    c.execute(
        "SELECT DISTINCT season FROM match_history WHERE season IS NOT NULL"
        " ORDER BY season ASC"
    )
    db_seasons = [r[0] for r in c.fetchall()]
  all_s = sorted(list(set(db_seasons + [cur, 1])))
  return all_s


def calculate_rating(raw_score, total_games):
  if total_games == 0:
    return 0.0
  base = (raw_score + 18) / (total_games + 3)
  bonus = 2 * math.sqrt(total_games)
  return round(base + bonus, 2)


def recalculate_all_players():
  cur_season = get_current_season()
  with sqlite3.connect("mafia_league.db") as conn:
    c = conn.cursor()
    c.execute("SELECT name FROM players")
    players = [r[0] for r in c.fetchall()]

    player_adv_scores = {p_name: 1000.0 for p_name in players}

    c.execute("""
        SELECT m.match_id
        FROM match_history m
        WHERE m.season = ?
        ORDER BY m.match_id ASC
    """, (cur_season,))
    season_matches = [r[0] for r in c.fetchall()]

    for m_id in season_matches:
      c.execute("SELECT player_name, won, is_mvp, is_axe, is_unfair, is_artin FROM match_participants WHERE match_id = ?", (m_id,))
      parts = c.fetchall()
      
      winners = [p[0] for p in parts if p[1] == 1]
      losers = [p[0] for p in parts if p[1] == 0]

      if not winners or not losers:
        continue

      avg_winner_skill = sum(player_adv_scores.get(w, 1000.0) for w in winners) / len(winners)
      avg_loser_skill = sum(player_adv_scores.get(l, 1000.0) for l in losers) / len(losers)

      skill_diff = avg_loser_skill - avg_winner_skill
      dynamic_factor = max(-4.0, min(4.0, skill_diff / 50.0))

      for p_name, won, mvp, axe, unfair, artin in parts:
        if p_name not in player_adv_scores:
          player_adv_scores[p_name] = 1000.0

        if won == 1:
          base_delta = 10.0 + dynamic_factor
        else:
          base_delta = -8.0 + dynamic_factor

        bonus_mvp = (4.0 if mvp else 0.0)
        penalty_axe = (-3.0 if axe else 0.0)
        penalty_unfair = (-6.0 if unfair else 0.0)
        penalty_artin = (-8.0 if artin else 0.0)
        player_adv_scores[p_name] += (base_delta + bonus_mvp + penalty_axe + penalty_unfair + penalty_artin)

    for p_name in players:
      c.execute(
          """
                SELECT p.side, p.won, p.is_mvp, p.is_axe, p.is_unfair, p.is_artin, p.night1_shot, p.night1_out, p.match_id
                FROM match_participants p
                JOIN match_history m ON p.match_id = m.match_id
                WHERE p.player_name = ? AND m.season = ?
                ORDER BY p.match_id ASC
            """,
          (p_name, cur_season),
      )
      matches = c.fetchall()

      total_g = len(matches)
      wins = sum(1 for m in matches if m[1] == 1)
      losses = total_g - wins
      mvps = sum(1 for m in matches if m[2] == 1)
      axes = sum(1 for m in matches if m[3] == 1)
      unfairs = sum(1 for m in matches if m[4] == 1)
      artins = sum(1 for m in matches if m[5] == 1)
      n1_shots = sum(1 for m in matches if m[6] == 1)
      n1_outs = sum(1 for m in matches if m[7] == 1)

      adv_score = player_adv_scores.get(p_name, 1000.0)

      c.execute(
          """
                SELECT m.chaos_players, m.chaos_selected, m.chaos_win_impact 
                FROM match_history m
                JOIN match_participants p ON m.match_id = p.match_id
                WHERE p.player_name = ? AND m.season = ? AND m.end_mode = 'کی آس'
            """,
          (p_name, cur_season),
      )
      chaos_matches = c.fetchall()
      
      c_count = 0
      c_sel_count = 0
      c_impact_count = 0

      for ch_players, ch_selected, ch_impact in chaos_matches:
        if ch_players and p_name in ch_players.split(","):
          c_count += 1
        if ch_selected == p_name:
          c_sel_count += 1
          if ch_impact == "بله":
            c_impact_count += 1

      raw = 0
      cur_streak = 0
      best_streak = 0

      for m in matches:
        won = m[1]
        mvp = m[2]
        axe = m[3]
        unfair = m[4]
        artin = m[5]
        
        game_pts = (10 if won else 0) + (4 if mvp else 0) + (-3 if axe else 0) + (-6 if unfair else 0) + (-8 if artin else 0)
        if won:
          cur_streak += 1
          if cur_streak >= 3:
            game_pts += 2
          best_streak = max(best_streak, cur_streak)
        else:
          cur_streak = 0

        raw += game_pts

      c_games = sum(1 for m in matches if m[0] == "شهروند")
      c_wins = sum(1 for m in matches if m[0] == "شهروند" and m[1] == 1)
      m_games = sum(1 for m in matches if m[0] == "مافیا")
      m_wins = sum(1 for m in matches if m[0] == "مافیا" and m[1] == 1)
      i_games = sum(1 for m in matches if m[0] == "مستقل")
      i_wins = sum(1 for m in matches if m[0] == "مستقل" and m[1] == 1)

      c.execute(
          """
                UPDATE players SET
                    raw_score = ?, total_games = ?, wins = ?, losses = ?,
                    mvp_count = ?, axe_count = ?, unfair_count = ?, artin_count = ?,
                    citizen_games = ?, citizen_wins = ?,
                    mafia_games = ?, mafia_wins = ?,
                    independent_games = ?, independent_wins = ?,
                    current_streak = ?, best_streak = ?,
                    night1_shots = ?, night1_outs = ?,
                    chaos_count = ?, chaos_selected_count = ?, chaos_win_impact_count = ?,
                    advanced_skill_score = ?
                WHERE name = ?
            """,
          (
              raw,
              total_g,
              wins,
              losses,
              mvps,
              axes,
              unfairs,
              artins,
              c_games,
              c_wins,
              m_games,
              m_wins,
              i_games,
              i_wins,
              cur_streak,
              best_streak,
              n1_shots,
              n1_outs,
              c_count,
              c_sel_count,
              c_impact_count,
              round(adv_score, 2),
              p_name,
          ),
      )
    conn.commit()


recalculate_all_players()


async def check_channel_membership(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
  user_id = update.effective_user.id
  if user_id in [ADMIN_ID, ADMIN_ID_2]:
    return True
    
  channel_username = TUTORIAL_CHANNEL_URL.rstrip("/").split("/")[-1]
  if not channel_username:
    return True

  try:
    member = await context.bot.get_chat_member(chat_id=f"@{channel_username}", user_id=user_id)
    if member.status in ["member", "administrator", "creator"]:
      return True
  except Exception as e:
    logging.error(f"Error checking channel membership: {e}")
    return False
    
  return False


async def enforce_channel_lock(update: Update, context: ContextTypes.DEFAULT_TYPE, check_lock: bool = True) -> bool:
  if not check_lock:
    return True

  is_member = await check_channel_membership(update, context)
  if not is_member:
    keyboard = [[InlineKeyboardButton("📚 عضویت در کانال آموزش‌ها", url=TUTORIAL_CHANNEL_URL)]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    text = "⛔️ برای استفاده از بخش آمار و رده‌بندی، ابتدا باید در کانال آموزش‌ها عضو شوید!"
    
    if update.callback_query:
      try:
        await update.callback_query.answer("⛔️ ابتدا در کانال عضو شوید!", show_alert=True)
        await update.callback_query.message.reply_text(text, reply_markup=reply_markup, parse_mode="Markdown")
      except Exception:
        pass
    elif update.message:
      try:
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode="Markdown")
      except Exception:
        pass
    return False
  return True


async def post_init(application):
  commands = [
      BotCommand("takamol", "نمایش منوی ربات تکامل 🎩"),
      BotCommand("join", "عضویت در جدول لیگ"),
      BotCommand("links", "ورود به سایت، گروه و کانال 🌐"),
      BotCommand("history", "سوابق و آرشیو مسابقات 📜"),
      BotCommand("table", "جدول لیگ و رده‌بندی 🏆"),
      BotCommand("advanced_table", "رده‌بندی پیشرفته (ارزش برد) ⭐"),
      BotCommand("stats", "آمار و پروفایل بازیکنان 👤"),
      BotCommand("bests", "برترین بست پلیرهای بازی 🌟"),
      BotCommand("axes", "جدول تبر طلایی 🪓"),
      BotCommand("unfair", "جدول نامرد طلایی (آنفیر) 🐍"),
      BotCommand("artin", "جدول آرتین طلایی (آرتین بازی) 👑"),
      BotCommand("teammates", "رده‌‌بندی بهترین هم‌تیمی‌ها 👥"),
      BotCommand("streaks", "رده‌بندی بهترین استریک‌ها 🔥"),
      BotCommand("shots_top", "برترین سوءقصدشده‌های شب اول 🎯"),
      BotCommand("vs", "تقابل دوئل و رودررو ⚔️"),
      BotCommand("chart", "نمودار پیشرفت بازیکنان 📈"),
      BotCommand("scoring", "راهنمای امتیازدهی لیگ 📜"),
      BotCommand("admin", "پنل مدیریت ادمین ⚙️️"),
      BotCommand("matches", "حذف و مدیریت بازی‌ها (ادمین) 🛠"),
      BotCommand("submit_game", "ثبت مسابقه با دکمه (ادمین)"),
      BotCommand("add_player", "افزودن دستی بازیکن (ادمین) ➕"),
      BotCommand("remove_player", "حذف بازیکن از لیگ (ادمین) 🗑"),
      BotCommand("merge_player", "ادغام آمار دو بازیکن (ادمین) 🔄"),
      BotCommand("rename", "تغییر نام بازیکن ✏️"),
      BotCommand("players", "فهرست بازیکنان (ادمین)"),
      BotCommand("scenarios", "آمار سناریوها 🎬"),
      BotCommand("sides", "آمار سایدها"),
  ]
  await application.bot.set_my_commands(commands, scope=BotCommandScopeDefault())


def get_all_player_names():
  with sqlite3.connect("mafia_league.db") as conn:
    c = conn.cursor()
    c.execute("SELECT name FROM players ORDER BY name ASC")
    return [r[0] for r in c.fetchall()]


async def scoring_guide(update: Update, context: ContextTypes.DEFAULT_TYPE):
  if not await enforce_channel_lock(update, context, check_lock=True):
    return
  log_feature_click(update.effective_user.id, "راهنمای امتیازدهی")
  text = (
      "📜 **راهنمای سیستم امتیازدهی و ریتینگ لیگ:**\n\n"
      "🎖 **امتیازات هر مسابقه:**\n"
      "▫️ پیروزی در مسابقه: `+۱۰` امتیاز\n"
      "▫️ شکست در مسابقه: `۰` امتیاز\n"
      "▫️ بست پلیر بازی (MVP): `+۴` امتیاز پاداش\n"
      "▫️ پلیر تبر بازی (برگزیده تبر): `-۳` امتیاز جریمه\n"
      "▫️ پلیر آنفیر (نامرد بازی): `-۶` امتیاز جریمه\n"
      "▫️ پلیر آرتین (یارفروش): `-۸` امتیاز جریمه\n\n"
      "👑 **القاب اختصاصی نفرات اول هر جدول در هر فصل:**\n"
      "▫️ نفر اول جدول رده‌بندی لیگ: 🏛 **امپراطور لیگ**\n"
      "▫️ نفر اول رده‌بندی پیشرفته (ارزش برد): 🧠 **مغز متفکر**\n"
      "▫️ نفر اول تالار بست‌پلیرها: ⚡ **ترس واقعی**\n"
      "▫️ نفر اول جدول تبر طلایی: 🐻 **خاله خرسه**\n"
      "▫️ نفر اول جدول نامرد طلایی (آنفیر): 🐍 **پیتون اعظم**\n"
      "▫️ نفر اول جدول آرتین طلایی: 🐺 **کفتار تنها**\n"
      "▫️ نفر اول رده‌بندی بهترین هم‌تیمی‌ها: 🤝 **اتحاد آهنین**\n"
      "▫️ نفر اول رده‌بندی بهترین استریک‌ها: ⚔️ **ماشین کشتار**\n"
      "▫️ نفر اول برترین شات‌شده‌های شب اول: 🎯 **کابوس مافیا**\n\n"
      "⚖️ **نحوه تعیین عناوین (MVP، تبر، آنفیر و آرتین):**\n"
      "▫️ انتخاب بازیکنان برتر، تبر، آنفیر و آرتین **بر عهده مدیر بازی** و در صورت نداشتن مدیر، **بر عهده گرداننده (گاد)** داخل بازی است.\n\n"
      "📌 **قوانین و شرایط خاص یارفروشی و خودزنی:**\n"
      "▫️ اگر تصمیم یارفروشی یا خودزنی، **تصمیم کل تیم** باشد، جریمه برای همه اعضای تیم لحاظ می‌شود؛ در این حالت تیم با توجه به امتیاز برد و جریمه کسر شده، پاداش بسیار کمی از آن برد نصیبش خواهد شد.\n"
      "▫️ اما اگر یارفروشی یا خودزنی **تصمیم فردی** باشد، جریمه صرفاً شامل حال همان فرد خواهد شد.\n"
      "▫️ در نتیجه، یارفروشی اصلاً توصیه نمی‌شود، اما بازیکن می‌تواند با انجام این کار امتیاز برد را دریافت کند و حتی اگر روی نوار استریک برد باشد، با حفظ آن نوار امتیاز بیشتری کسب کند.\n\n"
      "🔥 **پاداش ویژه کمبو (StreaK Bonus):**\n"
      "▫️ کسب بردهای پیاپی (۳ برد و بیشتر): پاداش ویژه `+۲` امتیاز اضافی به ازای هر برد متوالی از برد سوم به بعد!\n\n"
      "⭐ **رده‌بندی پیشرفته (پویا و مهارت‌محور):**\n"
      "در این بخش امتیازات بر اساس میانگین مهارت تیم‌ها محاسبه می‌شود؛ برد در برابر تیم‌های قوی‌تر پاداش بیشتری دارد و باخت در برابر تیم‌های ضعیف‌تر جریمه سنگین‌تری به همراه خواهد داشت.\n\n"
      "⚖️ **نحوه محاسبه ریتینگ در جدول رده‌بندی:**\n"
      "رتبه نهایی بازیکنان بر اساس «ریتینگ هوشمند» محاسبه می‌شود که علاوه بر مجموع امتیازات، تعداد بازی‌ها و کیفیت عملکرد را در نظر می‌گیرد."
  )
  keyboard = [[InlineKeyboardButton("🔙 بازگشت به منوی آمار", callback_data="open_stats_hub")]]
  if update.message:
    await update.message.reply_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown",
    )
  elif update.callback_query:
    try:
      await update.callback_query.message.reply_text(
          text,
          reply_markup=InlineKeyboardMarkup(keyboard),
          parse_mode="Markdown",
      )
    except Exception:
      pass


async def show_links_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
  if not await enforce_channel_lock(update, context, check_lock=False):
    return
  log_feature_click(update.effective_user.id, "لینک‌های پلتفرم و شبکه‌ها")
  text = (
      "🌐 **لینک‌های رسمی پلتفرم مافیا گنگز:**\n\n"
      "از دکمه‌های زیر برای ورود به پلتفرم سایت و سوپرگروه هماهنگی بازی‌ها استفاده کنید:"
  )
  keyboard = [
      [
          InlineKeyboardButton(
              "🔗 ورود به سایت و شروع بازی (roundgangs.com)", url=WEBSITE_URL
          )
      ],
      [
          InlineKeyboardButton(
              "🤖 وصل کردن تلگرام به سایت", url="https://t.me/roundgangs_bot"
          )
      ],
      [
          InlineKeyboardButton(
              "👥 ورود به سوپرگروه هماهنگی بازی‌ها", url=GROUP_INVITE_URL
          )
      ],
      [
          InlineKeyboardButton(
              "🔙 بازگشت به منوی اصلی", callback_data="back_to_start"
          )
      ],
  ]
  if update.message:
    await update.message.reply_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown",
    )
  elif update.callback_query:
    try:
      await update.callback_query.message.reply_text(
          text,
          reply_markup=InlineKeyboardMarkup(keyboard),
          parse_mode="Markdown",
      )
    except Exception:
      pass


async def show_rules_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
  if not await enforce_channel_lock(update, context, check_lock=False):
    return
  log_feature_click(update.effective_user.id, "قوانین بازی‌های گروه")
  text = (
      "📜 **قوانین بازی‌های گروه مافیا تکامل** 📜\n\n"
      "لطفاً برای مطالعه هر بخش، روی سرفصل مورد نظر خود در زیر کلیک کنید:"
  )
  keyboard = [
      [InlineKeyboardButton("۱. مدیریت، اقتدار گرداننده و ارتباطات", callback_data="rule_sec:1")],
      [InlineKeyboardButton("۲. اخلاق، احترام و مسائل شخصی", callback_data="rule_sec:2")],
      [InlineKeyboardButton("۳. نظم نوبت‌ها، مکالمات و فاز شب", callback_data="rule_sec:3")],
      [InlineKeyboardButton("۴. افشای نقش و سلامت بازی", callback_data="rule_sec:4")],
      [InlineKeyboardButton("۵. اصول تارگت، کاور، سفید/سیاه کردن و دفاعیه", callback_data="rule_sec:5")],
      [InlineKeyboardButton("۶. حضور، پایان بازی، خداحافظی و نظرسنجی‌ها", callback_data="rule_sec:6")],
      [InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="back_to_start")]
  ]
  reply_markup = InlineKeyboardMarkup(keyboard)
  if update.callback_query:
    try:
      await update.callback_query.message.reply_text(text, reply_markup=reply_markup, parse_mode="Markdown")
      await update.callback_query.answer()
    except Exception:
      pass
  elif update.message:
    await update.message.reply_text(text, reply_markup=reply_markup, parse_mode="Markdown")


async def show_rule_detail(update: Update, sec_num: str):
  query = update.callback_query
  try:
    await query.answer()
  except Exception:
    pass

  rules_dict = {
      "1": (
          "۱. **مدیریت، اقتدار گرداننده و ارتباطات**\n\n"
          "🔹 **مرجعیت گرداننده (گاد):** تصمیمات گرداننده در جریان بازی در هر شرایطی درست و قطعی تلقی می‌شود و هرگونه دخالت در کار او ممنوع است.\n\n"
          "🔹 **نحوه اعتراض و تذکر:** اعتراض یا بیان نکات صرفاً از طریق پیام خصوصی (پی‌وی) به گاد/ادمین‌ها یا بخش «صحبت با خدا» در سایت انجام می‌شود. هرگونه اعتراض داخل بازی موجب اخراج خواهد شد.\n\n"
          "🔹 **ارتباط در پی‌‌وی:** هرگونه پیام خصوصی میان بازیکنان در حین بازی (چه هم‌تیمی و چه رقیب) تقلب محسوب شده و منجر به محرومیت و در صورت تکرار، اخراج دائمی می‌شود."
      ),
      "2": (
          "۲. **اخلاق، احترام و مسائل شخصی**\n\n"
          "🔹 **ادب و احترام:** استفاده از الفاظ رکیک، توهین‌آمیز و شوخی‌های نامناسب (حتی خطاب به دوستان صمیمی) اکیداً ممنوع است و تشخیص آن بر عهده گاد خواهد بود.\n\n"
          "🔹 **سلسله‌مراتب جرایم انضباطی بی‌احترامی:**\n"
          "   ▫️ بار اول: قطع نوبت صحبت\n"
          "   ▫️ بار دوم: سلب حق رأی\n"
          "   ▫️ بار سوم: اخراج مستقیم از بازی و گروه\n\n"
          "🔹 **کدورت و عقاید شخصی:** ورود عقاید شخصی به بازی ممنوع است. در صورت داشتن خصومت قبلی با بازیکنی در یک دک، نباید در آن دک ثبت‌نام کنید؛ ایجاد درگیری شخصی به اخراج قطعی از گروه ختم می‌شود.\n\n"
          "🔹 **محدودیت چت گروه:** هرگونه بحث، کل‌کل و گفت‌وگوی خارج از موضوع مافیا در این گروه ممنوع است (۲۴ ساعت سلب دسترسی و در صورت تکرار، اخراج)."
      ),
      "3": (
          "۳. **نظم نوبت‌ها، مکالمات و فاز شب**\n\n"
          "🔹 **نوبت صحبت (ترن):** صحبت کردن صرفاً در نوبت مجاز است. باز کردن میکروفون خارج از نوبت با اخطار و در صورت تکرار با کیک همراه است.\n\n"
          "🔹 **فاز شب:** تصویر و میکروفون در فاز شب باید کاملاً خاموش باشد؛ هرگونه فعالیت (اکت) در این فاز منجر به کیک مستقیم می‌شود.\n\n"
          "🔹 **قانون چالش دستی:** چالش دادن پس از آغاز نوبت صحبت به صورت دستی ممنوع است؛ در صورت فراموشی، چالش سوخت می‌شود."
      ),
      "4": (
          "۴. **افشای نقش و سلامت بازی**\n\n"
          "🔹 **افشای نقش (Look/Reveal):** فاش کردن نقش خود یا دیگران (حتی با اشاره)، تهدید به افشا یا خروج بی‌دلیل از بازی ممنوع است:\n"
          "   ▫️ بار اول: کیک و ۴۸ ساعت محرومیت\n"
          "   ▫️ بار دوم: ۷۲ ساعت محرومیت\n\n"
          "🔹 **نقش چسباندن:** نسبت دادن نقش به دیگران (به‌جز سناریوهای مجاز) ممنوع است:\n"
          "   ▫️ بار اول: اخطار | بار دوم: سلب حق رای | بار سوم: کیک\n\n"
          "🔹 **کشف نقش غیرمجاز:** هر تلاشی برای کشف نقش‌ها در خارج از روند بازی باعث حذف فوری خواهد شد.\n\n"
          "🔹 **نقش شهروندی:** هرگونه نزدیک شدن به نقش شهروندی چه مستقیم چه غیر مستقیم، چه به خود فرد و چه به کس دیگری (به‌جز سناریوی مجاز که قبل بازی توسط گرداننده گفته می‌شود) ممنوع و منجر به خروج انضباطی خواهد شد."
      ),
      "5": (
          "۵. **اصول تارگت، کاور، سفید/سیاه کردن و دفاعیه**\n\n"
          "🔹 **سفید و سیاه کردن افراد در طول بازی:**\n"
          "   ▫️ تارگت و کاور کردن (یا همان سفید و سیاه کردن) افراد در طول روز بازی بدون ارائه فکت و استدلال معتبر ممنوع است و جریمه آن به ترتیب زیر است:\n"
          "      - بار اول: دریافت یک اخطار\n"
          "      - بار دوم: سلب حق رأی\n"
          "      - بار سوم: خروج انضباطی\n"
          "   ▫️ محتوای صحبت در زمان تارگت یا کاور باید دقیقاً در جهت فرد هدف باشد (تارگت برای رأی جمع کردن علیه فرد / کاور در جهت دفاع از فرد)؛ در غیر این صورت فاقد اعتبار است و می‌سوزد.\n\n"
          "🔹 **شهروندنمایی (ممنوع و دارای کیک مستقیم):** هرگونه فریب نامتعارف برای اثبات بی‌گناهی، از جمله:\n"
          "   ▫️ تظاهر به بی‌خبری از کشته‌های شب، دیالوگ یا تارگت زدن به فرد خارج‌شده.\n"
          "   ▫️ اعلام بی‌تفاوتی به بازی، عدم مشارکت در چالش و رأی‌گیری به قصد اثبات شهروندی.\n"
          "   ▫️️ اشاره به نقش‌های سناریوهای دیگر در جریان بازی جاری.\n\n"
          "🔹 **اکت در دفاعیه:** هرگونه اکت دادن در فاز دفاعیه ممنوع بوده و موجب سلب حق رأی می‌شود (مگر در سناریوهایی با قانون اکت آزاد یا میتیک که کیک مستقیم دارد)."
      ),
      "6": (
          "۶. **حضور، پایان بازی، خداحافظی و نحوه نظرسنجی‌ها**\n\n"
          "🔹 **تأخیر و غیبت:** بیش از ۱۵ دقیقه تأخیر منجر به حذف یا جایگزینی خواهد شد و فرد خاطی در صورت تکرار، یک هفته از بازی‌های گروه محروم می‌شود.\n\n"
          "🔹 **پایان بازی:** حضور در جلسه تا انتهای بازی الزامی است مگر با هماهنگی قبلی.\n\n"
          "🔹 **خداحافظی و لغو تحلیلیه:**\n"
          "   ▫️ بازی‌ها فاز «تحلیلیه» ندارند.\n"
          "   ▫️ بعد از هر بازی، هر فرد ۱۵ الی ۲۰ ثانیه وقت برای خداحافظی در اختیار دارد و پس از آن حق صحبت و تصویر از همه افراد گرفته می‌شود.\n"
          "   ▫️️ در صورت تمایل به تحلیلیه، اعضا می‌توانند با ایجاد لینک جداگانه در میت یا زوم، یا به صورت پیام متنی در گروه به تحلیل بپردازند.\n\n"
          "🔹 **نظرسنجی‌ها (قانون جدید):** از این به بعد دیگر نظرسنجی عادی تلگرام در گروه نخواهیم داشت و تمامی نظرسنجی‌ها صرفاً با بات خود نرم‌افزار انجام می‌شود."
      )
  }

  text = rules_dict.get(sec_num, "محتوای قوانین یافت نشد.")
  keyboard = [
      [InlineKeyboardButton("🔙 بازگشت به لیست سرفصل‌ها", callback_data="open_rules_menu")],
      [InlineKeyboardButton("🏠 منوی اصلی", callback_data="back_to_start")]
  ]
  reply_markup = InlineKeyboardMarkup(keyboard)
  try:
    await query.message.edit_text(text, reply_markup=reply_markup, parse_mode="Markdown")
  except Exception:
    pass


async def show_stats_hub(update: Update, context: ContextTypes.DEFAULT_TYPE):
  if not await enforce_channel_lock(update, context, check_lock=True):
    return

  log_feature_click(update.effective_user.id, "منوی اصلی آمار و رده‌بندی")
  text = (
      "📊 **بخش آمار، اطلاعات و رده‌بندی لیگ مافیا تکامل** 📊\n\n"
      "لطفاً بخش مورد نظر خود را از دکمه‌های زیر انتخاب کنید:"
  )
  keyboard = [
      [InlineKeyboardButton("👤 آمار بازیکنان", callback_data="open_stats_picker")],
      [InlineKeyboardButton("🏆 جدول رده‌بندی لیگ", callback_data="ask_table_season")],
      [InlineKeyboardButton("⭐ رده‌بندی پیشرفته (ارزش برد)", callback_data="ask_advanced_season")],
      [InlineKeyboardButton("🌟 برترین بست پلیرهای بازی", callback_data="ask_bests_season")],
      [InlineKeyboardButton("🪓 جدول تبر طلایی (پلیر تبر)", callback_data="ask_axes_season")],
      [InlineKeyboardButton("🐍 جدول نامرد طلایی (پلیر آنفیر)", callback_data="ask_unfair_season")],
      [InlineKeyboardButton("👑 جدول آرتین طلایی (آرتین بازی)", callback_data="ask_artin_season")],
      [InlineKeyboardButton("👥 رده‌بندی بهترین هم‌تیمی‌ها", callback_data="ask_teammates_season")],
      [InlineKeyboardButton("🔥 رده‌بندی بهترین استریک‌ها", callback_data="ask_streaks_season")],
      [InlineKeyboardButton("🎯 برترین شات‌شده‌های شب اول", callback_data="show_shots_lb")],
      [InlineKeyboardButton("⚔️ دوئل و تقابل رودررو", callback_data="ask_vs_season")],
      [InlineKeyboardButton("📈 نمودار پیشرفت بازیکنان", callback_data="open_chart_picker")],
      [InlineKeyboardButton("📜 راهنمای امتیازدهی", callback_data="show_scoring_info")],
      [InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="back_to_start")]
  ]
  reply_markup = InlineKeyboardMarkup(keyboard)
  
  if update.callback_query:
    try:
      await update.callback_query.message.reply_text(text, reply_markup=reply_markup, parse_mode="Markdown")
    except Exception:
      pass
  elif update.message:
    try:
      await update.message.reply_text(text, reply_markup=reply_markup, parse_mode="Markdown")
    except Exception:
      pass


async def ask_axes_season_choice(update: Update):
  seasons = get_available_seasons()
  keyboard = [[
      InlineKeyboardButton(
          "🌐 تبرهای کل تاریخچه (All-Time)", callback_data="axes_page:all:1"
      )
  ]]
  row = []
  for s_num in seasons:
    row.append(
        InlineKeyboardButton(
            f"🪓 فصل {s_num}", callback_data=f"axes_page:{s_num}:1"
        )
    )
    if len(row) == 2:
      keyboard.append(row)
      row = []
  if row:
    keyboard.append(row)

  keyboard.append([InlineKeyboardButton("🔙 بازگشت به منوی آمار", callback_data="open_stats_hub")])
  text = (
      "🪓 **جدول تبر طلایی (بیشترین تبر بازی):**\n\nمایلید آمار تبرهای کدام بازه را مشاهده کنید؟"
  )

  if update.callback_query:
    try:
      await update.callback_query.message.reply_text(
          text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown"
      )
    except Exception:
      pass


async def render_axes_page_filtered(update: Update, season_filter: str, page: int):
  log_feature_click(update.effective_user.id, f"جدول تبر طلایی ({season_filter})")
  with sqlite3.connect("mafia_league.db") as conn:
    c = conn.cursor()
    if season_filter == "all":
      season_title = "کل تاریخچه (All-Time)"
      c.execute("""
                SELECT player_name, 
                       SUM(is_axe) as axes, 
                       COUNT(*) as total_games
                FROM match_participants
                GROUP BY player_name
                HAVING SUM(is_axe) > 0
                ORDER BY axes DESC, total_games ASC
            """)
      rows = c.fetchall()
    else:
      s_int = int(season_filter)
      season_title = f"فصل {s_int}"
      cur_season = get_current_season()
      if s_int == cur_season:
        c.execute("""
                    SELECT name, axe_count, total_games
                    FROM players
                    WHERE axe_count > 0
                    ORDER BY axe_count DESC, total_games ASC
                """)
        rows = c.fetchall()
      else:
        c.execute(
            """
                    SELECT player_name, axe_count, total_games
                    FROM season_archives
                    WHERE season = ? AND axe_count > 0
                    ORDER BY axe_count DESC, total_games ASC
                """,
            (s_int,),
        )
        rows = c.fetchall()

  if not rows:
    text = f"🪓 هنوز هیچ تبری در {season_title} ثبت نشده است."
    keyboard = [
        [InlineKeyboardButton("🔄 انتخاب فصلی دیگر", callback_data="ask_axes_season")],
        [InlineKeyboardButton("🔙 بازگشت به منوی آمار", callback_data="open_stats_hub")],
    ]
    if update.callback_query:
      try:
        await update.callback_query.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
      except Exception:
        pass
    return

  total_items = len(rows)
  total_pages = max(1, math.ceil(total_items / PAGE_SIZE))
  page = max(1, min(page, total_pages))

  start_idx = (page - 1) * PAGE_SIZE
  end_idx = min(start_idx + PAGE_SIZE, total_items)
  page_rows = rows[start_idx:end_idx]

  text = (
      f"🪓 **جدول تبر طلایی لیگ ({season_title})** 🪓\n"
      f"صفحه {page} از {total_pages}\n"
      f"➖➖➖➖➖➖➖➖➖➖\n\n"
  )

  for rank, r in enumerate(page_rows, start=start_idx + 1):
    medal = "🥇" if rank == 1 else ("🥈" if rank == 2 else ("🥉" if rank == 3 else f"`#{rank:02d}`"))
    title_badge = " ⟨ 🐻 **خاله خرسه** ⟩" if rank == 1 else ""
    axe_bar = "🪓" * min(r[1], 8)
    text += (
        f"{medal} **{r[0]}**{title_badge}\n"
        f"   🪵 نشان‌ها: {axe_bar}\n"
        f"   ▫️ دفعات تبر بازی: `{r[1]}` بار (در {r[2]} مسابقه)\n"
        f"────────────────────\n"
    )

  nav_row = []
  if page > 1:
    nav_row.append(InlineKeyboardButton("⬅️ صفحه قبل", callback_data=f"axes_page:{season_filter}:{page - 1}"))
  if page < total_pages:
    nav_row.append(InlineKeyboardButton("صفحه بعد ➡️", callback_data=f"axes_page:{season_filter}:{page + 1}"))

  keyboard = []
  if nav_row:
    keyboard.append(nav_row)
  keyboard.append([InlineKeyboardButton("🔄 تغییر فصل / بازه تبر", callback_data="ask_axes_season")])
  keyboard.append([InlineKeyboardButton("🔙 بازگشت به منوی آمار", callback_data="open_stats_hub")])

  reply_markup = InlineKeyboardMarkup(keyboard)
  if update.callback_query:
    try:
      await update.callback_query.message.reply_text(text, reply_markup=reply_markup, parse_mode="Markdown")
    except Exception:
      pass


async def ask_unfair_season_choice(update: Update):
  seasons = get_available_seasons()
  keyboard = [[
      InlineKeyboardButton(
          "🌐 آنفیرهای کل تاریخچه (All-Time)", callback_data="unfair_page:all:1"
      )
  ]]
  row = []
  for s_num in seasons:
    row.append(
        InlineKeyboardButton(
            f"🐍 فصل {s_num}", callback_data=f"unfair_page:{s_num}:1"
        )
    )
    if len(row) == 2:
      keyboard.append(row)
      row = []
  if row:
    keyboard.append(row)

  keyboard.append([InlineKeyboardButton("🔙 بازگشت به منوی آمار", callback_data="open_stats_hub")])
  text = (
      "🐍 **جدول نامرد طلایی (پلیر آنفیر):**\n\nمایلید آمار آنفیرهای کدام بازه را مشاهده کنید؟"
  )

  if update.callback_query:
    try:
      await update.callback_query.message.reply_text(
          text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown"
      )
    except Exception:
      pass


async def render_unfair_page_filtered(update: Update, season_filter: str, page: int):
  log_feature_click(update.effective_user.id, f"جدول نامرد طلایی ({season_filter})")
  with sqlite3.connect("mafia_league.db") as conn:
    c = conn.cursor()
    if season_filter == "all":
      season_title = "کل تاریخچه (All-Time)"
      c.execute("""
                SELECT player_name, 
                       SUM(is_unfair) as unfairs, 
                       COUNT(*) as total_games
                FROM match_participants
                GROUP BY player_name
                HAVING SUM(is_unfair) > 0
                ORDER BY unfairs DESC, total_games ASC
            """)
      rows = c.fetchall()
    else:
      s_int = int(season_filter)
      season_title = f"فصل {s_int}"
      cur_season = get_current_season()
      if s_int == cur_season:
        c.execute("""
                    SELECT name, unfair_count, total_games
                    FROM players
                    WHERE unfair_count > 0
                    ORDER BY unfair_count DESC, total_games ASC
                """)
        rows = c.fetchall()
      else:
        c.execute(
            """
                    SELECT player_name, unfair_count, total_games
                    FROM season_archives
                    WHERE season = ? AND unfair_count > 0
                    ORDER BY unfair_count DESC, total_games ASC
                """,
            (s_int,),
        )
        rows = c.fetchall()

  if not rows:
    text = f"🐍 هنوز هیچ آمار آنفیری در {season_title} ثبت نشده است."
    keyboard = [
        [InlineKeyboardButton("🔄 انتخاب فصلی دیگر", callback_data="ask_unfair_season")],
        [InlineKeyboardButton("🔙 بازگشت به منوی آمار", callback_data="open_stats_hub")],
    ]
    if update.callback_query:
      try:
        await update.callback_query.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
      except Exception:
        pass
    return

  total_items = len(rows)
  total_pages = max(1, math.ceil(total_items / PAGE_SIZE))
  page = max(1, min(page, total_pages))

  start_idx = (page - 1) * PAGE_SIZE
  end_idx = min(start_idx + PAGE_SIZE, total_items)
  page_rows = rows[start_idx:end_idx]

  text = (
      f"🐍 **جدول نامرد طلایی لیگ ({season_title})** 🐍\n"
      f"صفحه {page} از {total_pages}\n"
      f"➖➖➖➖➖➖➖➖➖➖\n\n"
  )

  for rank, r in enumerate(page_rows, start=start_idx + 1):
    medal = "🥇" if rank == 1 else ("🥈" if rank == 2 else ("🥉" if rank == 3 else f"`#{rank:02d}`"))
    title_badge = " ⟨ 🐍 **پیتون اعظم** ⟩" if rank == 1 else ""
    unfair_bar = "🐍" * min(r[1], 8)
    text += (
        f"{medal} **{r[0]}**{title_badge}\n"
        f"   🪵 نشان‌ها: {unfair_bar}\n"
        f"   ▫️ دفعات آنفیر بازی: `{r[1]}` بار (در {r[2]} مسابقه)\n"
        f"────────────────────\n"
    )

  nav_row = []
  if page > 1:
    nav_row.append(InlineKeyboardButton("⬅️ صفحه قبل", callback_data=f"unfair_page:{season_filter}:{page - 1}"))
  if page < total_pages:
    nav_row.append(InlineKeyboardButton("صفحه بعد ➡️", callback_data=f"unfair_page:{season_filter}:{page + 1}"))

  keyboard = []
  if nav_row:
    keyboard.append(nav_row)
  keyboard.append([InlineKeyboardButton("🔄 تغییر فصل / بازه نامرد", callback_data="ask_unfair_season")])
  keyboard.append([InlineKeyboardButton("🔙 بازگشت به منوی آمار", callback_data="open_stats_hub")])

  reply_markup = InlineKeyboardMarkup(keyboard)
  if update.callback_query:
    try:
      await update.callback_query.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    except Exception:
      pass


async def ask_artin_season_choice(update: Update):
  seasons = get_available_seasons()
  keyboard = [[
      InlineKeyboardButton(
          "🌐 آرتین‌های کل تاریخچه (All-Time)", callback_data="artin_page:all:1"
      )
  ]]
  row = []
  for s_num in seasons:
    row.append(
        InlineKeyboardButton(
            f"👑 فصل {s_num}", callback_data=f"artin_page:{s_num}:1"
        )
    )
    if len(row) == 2:
      keyboard.append(row)
      row = []
  if row:
    keyboard.append(row)

  keyboard.append([InlineKeyboardButton("🔙 بازگشت به منوی آمار", callback_data="open_stats_hub")])
  text = (
      "👑 **جدول آرتین طلایی (آرتین بازی):**\n\nمایلید آمار آرتین بازی‌های کدام بازه را مشاهده کنید؟"
  )

  if update.callback_query:
    try:
      await update.callback_query.message.reply_text(
          text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown"
      )
    except Exception:
      pass


async def render_artin_page_filtered(update: Update, season_filter: str, page: int):
  log_feature_click(update.effective_user.id, f"جدول آرتین طلایی ({season_filter})")
  with sqlite3.connect("mafia_league.db") as conn:
    c = conn.cursor()
    if season_filter == "all":
      season_title = "کل تاریخچه (All-Time)"
      c.execute("""
                SELECT player_name, 
                       SUM(is_artin) as artins, 
                       COUNT(*) as total_games
                FROM match_participants
                GROUP BY player_name
                HAVING SUM(is_artin) > 0
                ORDER BY artins DESC, total_games ASC
            """)
      rows = c.fetchall()
    else:
      s_int = int(season_filter)
      season_title = f"فصل {s_int}"
      cur_season = get_current_season()
      if s_int == cur_season:
        c.execute("""
                    SELECT name, artin_count, total_games
                    FROM players
                    WHERE artin_count > 0
                    ORDER BY artin_count DESC, total_games ASC
                """)
        rows = c.fetchall()
      else:
        c.execute(
            """
                    SELECT player_name, artin_count, total_games
                    FROM season_archives
                    WHERE season = ? AND artin_count > 0
                    ORDER BY artin_count DESC, total_games ASC
                """,
            (s_int,),
        )
        rows = c.fetchall()

  if not rows:
    text = f"👑 هنوز هیچ آمار آرتین بازی در {season_title} ثبت نشده است."
    keyboard = [
        [InlineKeyboardButton("🔄 انتخاب فصلی دیگر", callback_data="ask_artin_season")],
        [InlineKeyboardButton("🔙 بازگشت به منوی آمار", callback_data="open_stats_hub")],
    ]
    if update.callback_query:
      try:
        await update.callback_query.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
      except Exception:
        pass
    return

  total_items = len(rows)
  total_pages = max(1, math.ceil(total_items / PAGE_SIZE))
  page = max(1, min(page, total_pages))

  start_idx = (page - 1) * PAGE_SIZE
  end_idx = min(start_idx + PAGE_SIZE, total_items)
  page_rows = rows[start_idx:end_idx]

  text = (
      f"👑 **جدول آرتین طلایی لیگ ({season_title})** 👑\n"
      f"صفحه {page} از {total_pages}\n"
      f"➖➖➖➖➖➖➖➖➖➖\n\n"
  )

  for rank, r in enumerate(page_rows, start=start_idx + 1):
    medal = "🥇" if rank == 1 else ("🥈" if rank == 2 else ("🥉" if rank == 3 else f"`#{rank:02d}`"))
    title_badge = " ⟨ 🐺 **کفتار تنها** ⟩" if rank == 1 else ""
    artin_bar = "👑" * min(r[1], 8)
    text += (
        f"{medal} **{r[0]}**{title_badge}\n"
        f"   🪵 نشان‌ها: {artin_bar}\n"
        f"   ▫️ دفعات آرتین بازی: `{r[1]}` بار (در {r[2]} مسابقه)\n"
        f"────────────────────\n"
    )

  nav_row = []
  if page > 1:
    nav_row.append(InlineKeyboardButton("⬅️ صفحه قبل", callback_data=f"artin_page:{season_filter}:{page - 1}"))
  if page < total_pages:
    nav_row.append(InlineKeyboardButton("صفحه بعد ➡️", callback_data=f"artin_page:{season_filter}:{page + 1}"))

  keyboard = []
  if nav_row:
    keyboard.append(nav_row)
  keyboard.append([InlineKeyboardButton("🔄 تغییر فصل / بازه آرتین", callback_data="ask_artin_season")])
  keyboard.append([InlineKeyboardButton("🔙 بازگشت به منوی آمار", callback_data="open_stats_hub")])

  reply_markup = InlineKeyboardMarkup(keyboard)
  if update.callback_query:
    try:
      await update.callback_query.message.reply_text(text, reply_markup=reply_markup, parse_mode="Markdown")
    except Exception:
      pass


async def ask_teammates_season_choice(update: Update):
  seasons = get_available_seasons()
  keyboard = [[
      InlineKeyboardButton(
          "🌐 بهترین هم‌تیمی‌های کل تاریخچه (All-Time)", callback_data="teammates_page:all:1"
      )
  ]]
  row = []
  for s_num in seasons:
    row.append(
        InlineKeyboardButton(
            f"👥 فصل {s_num}", callback_data=f"teammates_page:{s_num}:1"
        )
    )
    if len(row) == 2:
      keyboard.append(row)
      row = []
  if row:
    keyboard.append(row)

  keyboard.append([InlineKeyboardButton("🔙 بازگشت به منوی آمار", callback_data="open_stats_hub")])
  text = "👥 **رده‌بندی بهترین هم‌تیمی‌ها (بیشترین برد مشترک):**\n\nلطفاً بازه مورد نظر را انتخاب فرمایید:"

  if update.callback_query:
    try:
      await update.callback_query.message.reply_text(
          text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown"
      )
    except Exception:
      pass


async def render_teammates_leaderboard_filtered(update: Update, season_filter: str, page: int):
  log_feature_click(update.effective_user.id, f"بهترین هم‌تیمی‌ها ({season_filter})")

  with sqlite3.connect("mafia_league.db") as conn:
    c = conn.cursor()
    if season_filter == "all":
      season_title = "کل تاریخچه (All-Time)"
      c.execute("""
            SELECT p1.player_name, p2.player_name, COUNT(*), SUM(p1.won)
            FROM match_participants p1
            JOIN match_participants p2 ON p1.match_id = p2.match_id AND p1.side = p2.side
            WHERE p1.player_name < p2.player_name AND p1.won = 1 AND p2.won = 1
            GROUP BY p1.player_name, p2.player_name
            ORDER BY COUNT(*) DESC
        """)
      rows = c.fetchall()
    else:
      s_int = int(season_filter)
      season_title = f"فصل {s_int}"
      c.execute("""
            SELECT p1.player_name, p2.player_name, COUNT(*), SUM(p1.won)
            FROM match_participants p1
            JOIN match_participants p2 ON p1.match_id = p2.match_id AND p1.side = p2.side
            JOIN match_history m ON p1.match_id = m.match_id
            WHERE p1.player_name < p2.player_name AND p1.won = 1 AND p2.won = 1 AND m.season = ?
            GROUP BY p1.player_name, p2.player_name
            ORDER BY COUNT(*) DESC
        """, (s_int,))
      rows = c.fetchall()

  if not rows:
    text = f"هنوز داده‌ای در رده‌بندی هم‌تیمی‌های {season_title} ثبت نشده است."
    keyboard = [
        [InlineKeyboardButton("🔄 انتخاب فصلی دیگر", callback_data="ask_teammates_season")],
        [InlineKeyboardButton("🔙 بازگشت به منوی آمار", callback_data="open_stats_hub")],
    ]
    if update.callback_query:
      try:
        await update.callback_query.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
      except Exception:
        pass
    return

  total_items = len(rows)
  total_pages = max(1, math.ceil(total_items / PAGE_SIZE))
  page = max(1, min(page, total_pages))

  start_idx = (page - 1) * PAGE_SIZE
  end_idx = min(start_idx + PAGE_SIZE, total_items)
  page_rows = rows[start_idx:end_idx]

  text = (
      f"👥 **رده‌بندی بهترین جفت‌های هم‌تیمی ({season_title})**\n"
      f"صفحه {page} از {total_pages}\n"
      f"➖➖➖➖➖➖➖➖➖➖\n\n"
  )

  for i, r in enumerate(page_rows, start=start_idx + 1):
    medal = "🥇" if i == 1 else ("🥈" if i == 2 else ("🥉" if i == 3 else f"`#{i:02d}`"))
    title_badge = " ⟨ 🤝 **اتحاد آهنین** ⟩" if i == 1 else ""
    text += (
        f"{medal} **{r[0]}** 🤝 **{r[1]}**{title_badge}\n"
        f"   ▫️ بردهای مشترک: `{r[2]}` پیروزی\n"
        f"────────────────────\n"
    )

  nav_row = []
  if page > 1:
    nav_row.append(InlineKeyboardButton("⬅️ صفحه قبل", callback_data=f"teammates_page:{season_filter}:{page - 1}"))
  if page < total_pages:
    nav_row.append(InlineKeyboardButton("صفحه بعد ➡️", callback_data=f"teammates_page:{season_filter}:{page + 1}"))

  keyboard = []
  if nav_row:
    keyboard.append(nav_row)
  keyboard.append([InlineKeyboardButton("🔄 تغییر فصل / بازه", callback_data="ask_teammates_season")])
  keyboard.append([InlineKeyboardButton("🔙 بازگشت به منوی آمار", callback_data="open_stats_hub")])

  reply_markup = InlineKeyboardMarkup(keyboard)
  if update.callback_query:
    try:
      await update.callback_query.message.reply_text(text, reply_markup=reply_markup, parse_mode="Markdown")
    except Exception:
      pass


async def ask_streaks_season_choice(update: Update):
  seasons = get_available_seasons()
  keyboard = [[
      InlineKeyboardButton(
          "🌐 استریک‌های کل تاریخچه (All-Time)", callback_data="streaks_page:all:1"
      )
  ]]
  row = []
  for s_num in seasons:
    row.append(
        InlineKeyboardButton(
            f"🔥 فصل {s_num}", callback_data=f"streaks_page:{s_num}:1"
        )
    )
    if len(row) == 2:
      keyboard.append(row)
      row = []
  if row:
    keyboard.append(row)

  keyboard.append([InlineKeyboardButton("🔙 بازگشت به منوی آمار", callback_data="open_stats_hub")])
  text = "🔥 **رده‌بندی بهترین استریک‌ها (بیشترین بردهای پیاپی):**\n\nلطفاً بازه مورد نظر را انتخاب فرمایید:"

  if update.callback_query:
    try:
      await update.callback_query.message.reply_text(
          text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown"
      )
    except Exception:
      pass


async def render_streaks_leaderboard_filtered(update: Update, season_filter: str, page: int):
  log_feature_click(update.effective_user.id, f"بهترین استریک‌ها ({season_filter})")

  with sqlite3.connect("mafia_league.db") as conn:
    c = conn.cursor()
    if season_filter == "all":
      season_title = "کل تاریخچه (All-Time)"
      c.execute("""
            SELECT p.player_name, p.won, m.created_at
            FROM match_participants p
            JOIN match_history m ON p.match_id = m.match_id
            ORDER BY p.player_name ASC, m.created_at ASC, p.match_id ASC
        """)
      all_records = c.fetchall()
      
      player_streaks = {}
      for p_name, won, _ in all_records:
        if p_name not in player_streaks:
          player_streaks[p_name] = {"best": 0, "current": 0, "total": 0, "wins": 0}
        
        player_streaks[p_name]["total"] += 1
        if won == 1:
          player_streaks[p_name]["wins"] += 1
          player_streaks[p_name]["current"] += 1
          if player_streaks[p_name]["current"] > player_streaks[p_name]["best"]:
            player_streaks[p_name]["best"] = player_streaks[p_name]["current"]
        else:
          player_streaks[p_name]["current"] = 0

      rows = [
          (p_name, data["best"], data["total"], data["wins"])
          for p_name, data in player_streaks.items()
          if data["best"] > 0
      ]
      rows.sort(key=lambda x: (x[1], x[3]), reverse=True)

    else:
      s_int = int(season_filter)
      season_title = f"فصل {s_int}"
      cur_season = get_current_season()
      if s_int == cur_season:
        c.execute("""
            SELECT name, best_streak, total_games, wins 
            FROM players 
            WHERE best_streak > 0 
            ORDER BY best_streak DESC, wins DESC
        """)
        rows = c.fetchall()
      else:
        c.execute("""
            SELECT p.player_name, p.won, m.created_at
            FROM match_participants p
            JOIN match_history m ON p.match_id = m.match_id
            WHERE m.season = ?
            ORDER BY p.player_name ASC, m.created_at ASC, p.match_id ASC
        """, (s_int,))
        season_records = c.fetchall()
        
        season_player_streaks = {}
        for p_name, won, _ in season_records:
          if p_name not in season_player_streaks:
            season_player_streaks[p_name] = {"best": 0, "current": 0, "total": 0, "wins": 0}
          
          season_player_streaks[p_name]["total"] += 1
          if won == 1:
            season_player_streaks[p_name]["wins"] += 1
            season_player_streaks[p_name]["current"] += 1
            if season_player_streaks[p_name]["current"] > season_player_streaks[p_name]["best"]:
              season_player_streaks[p_name]["best"] = season_player_streaks[p_name]["current"]
          else:
            season_player_streaks[p_name]["current"] = 0

        rows = [
            (p_name, data["best"], data["total"], data["wins"])
            for p_name, data in season_player_streaks.items()
            if data["best"] > 0
        ]
        rows.sort(key=lambda x: (x[1], x[3]), reverse=True)

  if not rows:
    text = f"هنوز داده‌ای در رده‌بندی استریک‌های {season_title} ثبت نشده است."
    keyboard = [
        [InlineKeyboardButton("🔄 انتخاب فصلی دیگر", callback_data="ask_streaks_season")],
        [InlineKeyboardButton("🔙 بازگشت به منوی آمار", callback_data="open_stats_hub")],
    ]
    if update.callback_query:
      try:
        await update.callback_query.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
      except Exception:
        pass
    return

  total_items = len(rows)
  total_pages = max(1, math.ceil(total_items / PAGE_SIZE))
  page = max(1, min(page, total_pages))

  start_idx = (page - 1) * PAGE_SIZE
  end_idx = min(start_idx + PAGE_SIZE, total_items)
  page_rows = rows[start_idx:end_idx]

  text = (
      f"🔥 **رده‌بندی بهترین استریک‌های پیروزی ({season_title})**\n"
      f"صفحه {page} از {total_pages}\n"
      f"➖➖➖➖➖➖➖➖➖➖\n\n"
  )

  for i, r in enumerate(page_rows, start=start_idx + 1):
    medal = "🥇" if i == 1 else ("🥈" if i == 2 else ("🥉" if i == 3 else f"`#{i:02d}`"))
    title_badge = " ⟨ ⚔️ **ماشین کشتار** ⟩" if i == 1 else ""
    text += (
        f"{medal} **{r[0]}**{title_badge}\n"
        f"   ▫️ رکورد استریک پیاپی: `🔥 {r[1]}` برد متوالی\n"
        f"   ▫️ بازی: `{r[2]}` (برد: `{r[3]}`)\n"
        f"────────────────────\n"
    )

  nav_row = []
  if page > 1:
    nav_row.append(InlineKeyboardButton("⬅️ صفحه قبل", callback_data=f"streaks_page:{season_filter}:{page - 1}"))
  if page < total_pages:
    nav_row.append(InlineKeyboardButton("صفحه بعد ➡️", callback_data=f"streaks_page:{season_filter}:{page + 1}"))

  keyboard = []
  if nav_row:
    keyboard.append(nav_row)
  keyboard.append([InlineKeyboardButton("🔄 تغییر فصل / بازه", callback_data="ask_streaks_season")])
  keyboard.append([InlineKeyboardButton("🔙 بازگشت به منوی آمار", callback_data="open_stats_hub")])

  reply_markup = InlineKeyboardMarkup(keyboard)
  if update.callback_query:
    try:
      await update.callback_query.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    except Exception:
      pass


async def ask_advanced_season_choice(update: Update):
  seasons = get_available_seasons()
  keyboard = [[
      InlineKeyboardButton(
          "🌐 رده‌بندی پیشرفته کل تاریخچه (All-Time)", callback_data="adv_table_page:all:1"
      )
  ]]
  row = []
  for s_num in seasons:
    if s_num == 1:
      continue
    row.append(
        InlineKeyboardButton(
            f"⭐ فصل {s_num}", callback_data=f"adv_table_page:{s_num}:1"
        )
    )
    if len(row) == 2:
      keyboard.append(row)
      row = []
  if row:
    keyboard.append(row)

  keyboard.append([InlineKeyboardButton("🔙 بازگشت به منوی آمار", callback_data="open_stats_hub")])
  text = (
      "⭐ **رده‌بندی پیشرفته (ارزش برد و عملکرد تیمی):**\n\nلطفاً بازه مورد نظر را انتخاب فرمایید:"
  )

  if update.callback_query:
    try:
      await update.callback_query.message.reply_text(
          text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown"
      )
    except Exception:
      pass


async def render_advanced_table_page(update: Update, season_filter: str, page: int):
  log_feature_click(update.effective_user.id, f"رده‌‌بندی پیشرفته ({season_filter})")

  with sqlite3.connect("mafia_league.db") as conn:
    c = conn.cursor()
    if season_filter == "all":
      season_title = "کل تاریخچه (All-Time)"
      c.execute("SELECT name, advanced_skill_score, total_games, wins, losses FROM players WHERE total_games > 0 ORDER BY advanced_skill_score DESC")
      rows = c.fetchall()
    else:
      s_int = int(season_filter)
      season_title = f"فصل {s_int}"
      cur_season = get_current_season()
      if s_int == cur_season:
        c.execute("SELECT name, advanced_skill_score, total_games, wins, losses FROM players WHERE total_games > 0 ORDER BY advanced_skill_score DESC")
        rows = c.fetchall()
      else:
        c.execute("""
            SELECT player_name, advanced_skill_score, total_games, wins, losses 
            FROM season_archives 
            WHERE season = ? AND total_games > 0
            ORDER BY advanced_skill_score DESC
        """, (s_int,))
        rows = c.fetchall()

  if not rows:
    text = f"هنوز داده‌ای در رده‌بندی پیشرفته {season_title} ثبت نشده است."
    keyboard = [
        [InlineKeyboardButton("🔄 انتخاب فصلی دیگر", callback_data="ask_advanced_season")],
        [InlineKeyboardButton("🔙 بازگشت به منوی آمار", callback_data="open_stats_hub")],
    ]
    if update.callback_query:
      try:
        await update.callback_query.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
      except Exception:
        pass
    return

  total_players = len(rows)
  total_pages = max(1, math.ceil(total_players / PAGE_SIZE))
  page = max(1, min(page, total_pages))

  start_idx = (page - 1) * PAGE_SIZE
  end_idx = min(start_idx + PAGE_SIZE, total_players)
  page_players = rows[start_idx:end_idx]

  text = (
      f"⭐ **رده‌بندی پیشرفته و مهارت ({season_title})** ⭐\n"
      f"صفحه {page} از {total_pages}\n"
      f"➖➖➖➖➖➖➖➖➖➖\n\n"
  )

  for i, p in enumerate(page_players, start=start_idx + 1):
    medal = "🥇" if i == 1 else ("🥈" if i == 2 else ("🥉" if i == 3 else f"`#{i:02d}`"))
    title_badge = " ⟨ 🧠 **مغز متفکر** ⟩" if i == 1 else ""
    win_rate = round((p[3] / p[2] * 100), 1) if p[2] > 0 else 0
    text += (
        f"{medal} **{p[0]}**{title_badge}\n"
        f"   ▫️ امتیاز پیشرفته (Skill): `{p[1]}`\n"
        f"   ▫️ بازی: `{p[2]}` (برد: `{p[3]}` / باخت: `{p[4]}`) | WR: `{win_rate}%`\n"
        f"────────────────────\n"
    )

  nav_row = []
  if page > 1:
    nav_row.append(InlineKeyboardButton("⬅️ صفحه قبل", callback_data=f"adv_table_page:{season_filter}:{page - 1}"))
  if page < total_pages:
    nav_row.append(InlineKeyboardButton("صفحه بعد ➡️", callback_data=f"adv_table_page:{season_filter}:{page + 1}"))

  keyboard = []
  if nav_row:
    keyboard.append(nav_row)
  keyboard.append([InlineKeyboardButton("🔄 تغییر فصل / بازه", callback_data="ask_advanced_season")])
  keyboard.append([InlineKeyboardButton("🔙 بازگشت به منوی آمار", callback_data="open_stats_hub")])

  reply_markup = InlineKeyboardMarkup(keyboard)
  if update.callback_query:
    try:
      await update.callback_query.message.reply_text(text, reply_markup=reply_markup, parse_mode="Markdown")
    except Exception:
      pass


async def ask_shots_season_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
  seasons = get_available_seasons()
  keyboard = [[
      InlineKeyboardButton(
          "🌐 کل تاریخچه شات‌ها (All-Time)", callback_data="shots_page:all"
      )
  ]]
  row = []
  for s_num in seasons:
    row.append(
        InlineKeyboardButton(
            f"🎯 فصل {s_num}", callback_data=f"shots_page:{s_num}"
        )
    )
    if len(row) == 2:
      keyboard.append(row)
      row = []
  if row:
    keyboard.append(row)

  keyboard.append([InlineKeyboardButton("🔙 بازگشت به منوی آمار", callback_data="open_stats_hub")])
  text = (
      "🎯 **برترین سوءقصدشده‌های شب اول:**\n\nمایلید آمار شات‌های شب اول را برای کدام بازه مشاهده کنید؟"
  )

  if update.callback_query:
    try:
      await update.callback_query.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    except Exception:
      pass
  elif update.message:
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")


async def render_shots_leaderboard_filtered(update: Update, season_filter: str):
  log_feature_click(update.effective_user.id, f"برترین شات‌شده‌ها ({season_filter})")
  
  with sqlite3.connect("mafia_league.db") as conn:
    c = conn.cursor()
    if season_filter == "all":
      season_title = "کل تاریخچه (All-Time)"
      c.execute("""
          SELECT p.player_name, SUM(p.night1_shot) as total_shots
          FROM match_participants p
          GROUP BY p.player_name
          HAVING SUM(p.night1_shot) > 0
          ORDER BY total_shots DESC
          LIMIT 15
      """)
      rows = c.fetchall()
    else:
      s_int = int(season_filter)
      season_title = f"فصل {s_int}"
      c.execute("""
          SELECT p.player_name, SUM(p.night1_shot) as total_shots
          FROM match_participants p
          JOIN match_history m ON p.match_id = m.match_id
          WHERE m.season = ?
          GROUP BY p.player_name
          HAVING SUM(p.night1_shot) > 0
          ORDER BY total_shots DESC
          LIMIT 15
      """, (s_int,))
      rows = c.fetchall()

  if not rows:
    text = f"🎯 هنوز هیچ آماری از شات‌های شب اول در {season_title} ثبت نشده است."
  else:
    text = f"🎯 **برترین سوءقصدشده‌های شب اول ({season_title})**:\n\n"
    for idx, (p_name, shots) in enumerate(rows, start=1):
      medal = "🥇" if idx == 1 else ("🥈" if idx == 2 else ("🥉" if idx == 3 else f"`#{idx:02d}`"))
      title_badge = " ⟨ 🎯 **کابوس مافیا** ⟩" if idx == 1 else ""
      text += f"{medal} **{p_name}**{title_badge} ──> `{shots}` بار هدف شات شب اول\n"

  keyboard = [
      [InlineKeyboardButton("🔄 انتخاب فصلی دیگر", callback_data="show_shots_lb")],
      [InlineKeyboardButton("🔙 بازگشت به منوی آمار", callback_data="open_stats_hub")]
  ]
  reply_markup = InlineKeyboardMarkup(keyboard)

  if update.callback_query:
    try:
      await update.callback_query.message.reply_text(text, reply_markup=reply_markup, parse_mode="Markdown")
    except Exception:
      pass


async def send_takamol_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
  user_id = update.effective_user.id
  keyboard = [
      [InlineKeyboardButton("🤖 عضویت در ربات", callback_data="btn_join_league")],
      [
          InlineKeyboardButton(
              "🌐 ورود به سایت و گروه بازی‌ها",
              callback_data="open_community_links",
          )
      ],
      [
          InlineKeyboardButton("📚 آموزش سناریوها", url=TUTORIAL_CHANNEL_URL)
      ],
      [
          InlineKeyboardButton("📜 قوانین بازی‌های گروه", callback_data="open_rules_menu")
      ],
      [
          InlineKeyboardButton("📊 آمار و رده‌بندی", callback_data="open_stats_hub"),
          InlineKeyboardButton("📜 آرشیو مسابقات", callback_data="pub_history_page:1"),
      ],
  ]

  if user_id in [ADMIN_ID, ADMIN_ID_2]:
    keyboard.append([
        InlineKeyboardButton(
            "⚙️ پنل مدیریت ادمین (ثبت، فصل، آمار، مسابقات)",
            callback_data="open_admin_panel",
        )
    ])

  reply_markup = InlineKeyboardMarkup(keyboard)

  caption_text = (
      "🔥 **به ربات بهترین پلتفرم مافیای خودکار و بدون گرداننده خوش آمدید❗️**"
      " 🔥\n\n"
      "🧠 **هوشمند بازی کن، حرفه‌ای ببر** 🏆"
  )

  if update.callback_query:
    try:
      if os.path.exists(BANNER_PATH):
        with open(BANNER_PATH, "rb") as photo_file:
          await update.callback_query.message.reply_photo(
              photo=photo_file,
              caption=caption_text,
              reply_markup=reply_markup,
              parse_mode="Markdown",
          )
      else:
        await update.callback_query.message.reply_text(
            caption_text, reply_markup=reply_markup, parse_mode="Markdown"
        )
    except Exception:
      pass
  elif update.message:
    if os.path.exists(BANNER_PATH):
      with open(BANNER_PATH, "rb") as photo_file:
        await update.message.reply_photo(
            photo=photo_file,
            caption=caption_text,
            reply_markup=reply_markup,
            parse_mode="Markdown",
        )
    else:
      await update.message.reply_text(
          caption_text, reply_markup=reply_markup, parse_mode="Markdown"
      )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
  await send_takamol_menu(update, context)


async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
  user_id = update.effective_user.id
  if user_id not in [ADMIN_ID, ADMIN_ID_2]:
    if update.message:
      await update.message.reply_text("⛔ این بخش فقط برای ادمین لیگ در دسترس است.")
    elif update.callback_query:
      try:
        await update.callback_query.answer(
            "⛔️ دسترسی فقط برای ادمین مجاز است.", show_alert=True
        )
      except Exception:
        pass
    return

  cur_season = get_current_season()
  next_season = cur_season + 1

  if user_id == ADMIN_ID:
    text = (
        f"⚙️ **پنل مدیریت ادمین (فصل فعال: {cur_season}):**\n\n"
        "برای انجام هر عملیات، روی دکمه مربوطه در زیر کلیک کنید:"
    )
    keyboard = [
        [
            InlineKeyboardButton(
                "📊 آمار و تحلیل محبوبیت بخش‌ها (Analytics)",
                callback_data="show_admin_analytics",
            )
        ],
        [
            InlineKeyboardButton(
                f"🎮 ثبت مسابقه جدید (فصل {cur_season})",
                callback_data="admin_btn_submit",
            )
        ],
        [
            InlineKeyboardButton(
                "🗑 حذف و مدیریت بازی‌ها",
                callback_data="open_matches_list",
            )
        ],
        [
            InlineKeyboardButton(
                f"🏁 بستن فصل {cur_season} و شروع رسمی فصل {next_season}",
                callback_data="confirm_finish_season_prompt",
            )
        ],
        [
            InlineKeyboardButton(
                "➕ افزودن دستی بازیکن قدیمی", callback_data="admin_btn_add"
            )
        ],
        [
            InlineKeyboardButton(
                "🔄 ادغام بازیکن قدیم و جدید", callback_data="open_merge_picker_old"
            )
        ],
        [
            InlineKeyboardButton(
                "🗑 حذف بازیکن از لیگ", callback_data="admin_btn_remove_list"
            )
        ],
        [
            InlineKeyboardButton(
                "📋 فهرست بازیکنان لیگ", callback_data="show_players_info"
            )
        ],
        [
            InlineKeyboardButton(
                "🔙 بازگشت به منوی اصلی", callback_data="back_to_start"
            )
        ],
    ]
  else:
    text = (
        f"⚙️ **پنل مدیریت ادمین دوم (فصل فعال: {cur_season}):**\n\n"
        "شما به قابلیت‌های ثبت و مدیریت مسابقات دسترسی دارید:"
    )
    keyboard = [
        [
            InlineKeyboardButton(
                f"🎮 ثبت مسابقه جدید (فصل {cur_season})",
                callback_data="admin_btn_submit",
            )
        ],
        [
            InlineKeyboardButton(
                "🗑 حذف و مدیریت بازی‌ها",
                callback_data="open_matches_list",
            )
        ],
        [
            InlineKeyboardButton(
                "📋 فهرست بازیکنان لیگ",
                callback_data="show_players_info",
            )
        ],
        [
            InlineKeyboardButton(
                "🔙 بازگشت به منوی اصلی",
                callback_data="back_to_start",
            )
        ],
    ]

  reply_markup = InlineKeyboardMarkup(keyboard)
  if update.message:
    await update.message.reply_text(
        text, reply_markup=reply_markup, parse_mode="Markdown"
    )
  elif update.callback_query:
    try:
      await update.callback_query.message.reply_text(
          text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown"
      )
    except Exception:
      pass


async def show_analytics_report(update: Update):
  with sqlite3.connect("mafia_league.db") as conn:
    c = conn.cursor()

    c.execute("""
            SELECT feature_name, COUNT(*) 
            FROM bot_analytics 
            WHERE DATE(created_at) = DATE('now')
            GROUP BY feature_name 
            ORDER BY COUNT(*) DESC
        """)
    today_stats = c.fetchall()
    today_total = sum(row[1] for row in today_stats)

    c.execute("""
            SELECT feature_name, COUNT(*) 
            FROM bot_analytics 
            GROUP BY feature_name 
            ORDER BY COUNT(*) DESC
        """)
    all_time_stats = c.fetchall()
    all_time_total = sum(row[1] for row in all_time_stats)

    c.execute("SELECT COUNT(DISTINCT user_id) FROM bot_analytics")
    unique_users = c.fetchone()[0]

  text = (
      "📊 **گزارش آماری و تحلیل استفاده کاربران از بخش‌های مختلف:**\n"
      "➖➖➖➖➖➖➖➖➖➖\n\n"
      f"👥 **کاربران فعال ثبت‌شده:** `{unique_users}` کاربر یکتا\n\n"
  )

  text += f"📅 **آمار امروز (کلیک‌های امروز: `{today_total}` بار):**\n"
  if not today_stats:
    text += "▫️ امروز هنوز فعالیتی ثبت نشده است.\n"
  else:
    for f_name, count in today_stats:
      pct = round((count / today_total * 100), 1) if today_total > 0 else 0
      text += f"▫️ {f_name}: `{count}` بار ({pct}%)\n"

  text += "\n────────────────────\n\n"

  text += f"🏆 **آمار کل تاریخچه (مجموع کلیک‌ها: `{all_time_total}` بار):**\n"
  if not all_time_stats:
    text += "▫️ هنوز دیتایی ثبت نشده است.\n"
  else:
    for idx, (f_name, count) in enumerate(all_time_stats, start=1):
      pct = round((count / all_time_total * 100), 1) if all_time_total > 0 else 0
      bar_len = int(round(pct / 10))
      bar = "🟩" * bar_len + "▫️️" * (10 - bar_len)
      medal = (
          "🥇"
          if idx == 1
          else "🥈" if idx == 2 else "🥉" if idx == 3 else f"`#{idx:02d}`"
      )
      text += f"{medal} **{f_name}**\n   [{bar}] `{count}` کلیک ({pct}%)\n"

  keyboard = [
      [
          InlineKeyboardButton(
              "🔄 به‌روزرسانی گزارش", callback_data="show_admin_analytics"
          )
      ],
      [
          InlineKeyboardButton(
              "🔙 بازگشت به پنل مدیریت", callback_data="open_admin_panel"
          )
      ],
  ]
  try:
    await update.callback_query.message.reply_text(
        text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown"
    )
  except Exception:
    pass


async def prompt_finish_season(update: Update):
  cur_season = get_current_season()
  next_season = cur_season + 1
  text = (
      f"⚠️ **آیا مطمئن هستید که می‌خواهید پرونده فصل {cur_season} را ببندید؟**\n\n"
      f"با این اقدام:\n"
      f"۱. تمام رتبه‌ها، امتیازات و ریتینگ‌های فعلی به عنوان **آرشیو جاودانه فصل"
      f" {cur_season}** ثبت و ذخیره می‌شوند.\n"
      f"۲. اکانت همه بازیکنان حفظ شده اما آمار جدول برای **فصل {next_season}**"
      f" صفر می‌شود تا مسابقات از ابتدا آغاز گردند.\n"
      f"۳. تمام مسابقات گذشته با برچسب فصل {cur_season} در آرشیو باقی می‌مانند."
  )
  keyboard = [
      [
          InlineKeyboardButton(
              f"✅ بله، فصل {cur_season} را ببند و فصل {next_season} را شروع کن",
              callback_data="do_finish_season_action",
          )
      ],
      [
          InlineKeyboardButton(
              "❌ خیر، انصراف", callback_data="open_admin_panel"
          )
      ],
  ]
  try:
    await update.callback_query.message.reply_text(
        text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown"
    )
  except Exception:
    pass


async def execute_finish_season(
    update: Update, context: ContextTypes.DEFAULT_TYPE
):
  cur_season = get_current_season()
  next_season = cur_season + 1

  with sqlite3.connect("mafia_league.db") as conn:
    c = conn.cursor()
    c.execute(
        "SELECT name, raw_score, total_games, wins, losses, mvp_count, axe_count, unfair_count, artin_count,"
        " advanced_skill_score FROM players"
    )
    players = c.fetchall()

    ranking = []
    for p in players:
      ranking.append((p[0], p[9], p[1], p[2], p[3], p[4], p[5], p[6], p[7], p[8]))

    ranking.sort(key=lambda x: (x[1], x[2], x[4]), reverse=True)

    for rank, p in enumerate(ranking, start=1):
      c.execute(
          """
                INSERT INTO season_archives (season, player_name, final_rank, final_rating, raw_score, total_games, wins, losses, mvp_count, axe_count, unfair_count, artin_count, advanced_skill_score)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
          (
              cur_season,
              p[0],
              rank,
              calculate_rating(p[2], p[3]),
              p[2],
              p[3],
              p[4],
              p[5],
              p[6],
              p[7],
              p[8],
              p[9],
              p[1],
          ),
      )

    c.execute("""
            UPDATE players SET
                raw_score = 0, total_games = 0, wins = 0, losses = 0,
                mvp_count = 0, axe_count = 0, unfair_count = 0, artin_count = 0, citizen_games = 0, citizen_wins = 0,
                mafia_games = 0, mafia_wins = 0, independent_games = 0, independent_wins = 0,
                current_streak = 0, best_streak = 0, night1_shots = 0, night1_outs = 0,
                chaos_count = 0, chaos_selected_count = 0, chaos_win_impact_count = 0,
                advanced_skill_score = 1000.0
        """)
    conn.commit()

  set_current_season(next_season)

  msg = (
      f"🏆 **پرونده فصل {cur_season} با موفقیت بسته شد و به آرشیو منتقل"
      f" گردید!**\n\n"
      f"🚀 **فصل {next_season} رسماً آغاز شد!**\n"
      f"▫️ جدول بازیکنان برای فصل جدید صفر شد.\n"
      f"▫️ اعضای لیگ بدون نیاز به عضویت مجدد در سیستم باقی مانده‌اند."
  )
  keyboard = [[InlineKeyboardButton("🔙 بازگشت به پنل مدیریت", callback_data="open_admin_panel")]]
  try:
    await update.callback_query.message.reply_text(
        msg, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown"
    )
  except Exception:
    pass


async def process_join_user(
    user, context: ContextTypes.DEFAULT_TYPE, reply_func=None, alert_func=None
):
  user_id = user.id
  display_name = (
      user.full_name.strip()
      if user.full_name
      else (user.username or f"Player_{user_id}")
  )
  username = user.username or ""

  try:
    with sqlite3.connect("mafia_league.db") as conn:
      c = conn.cursor()
      c.execute(
          "INSERT INTO players (user_id, username, name) VALUES (?, ?, ?)",
          (user_id, username, display_name),
      )
      conn.commit()

    log_feature_click(user_id, "عضویت در لیگ")
    msg = (
        f"✅ شما با نام «**{display_name}**» در لیگ ثبت شدید!\nدر صورت نیاز"
        " می‌توانید با دستور `/rename` نام خود را تغییر دهید."
    )
    if alert_func:
      await alert_func(f"✅ با نام «{display_name}» عضو لیگ شدید!", show_alert=True)
    elif reply_func:
      await reply_func(msg, parse_mode="Markdown")

    try:
      user_tag = f"@{username}" if username else "ندارد"
      admin_msg = (
          "🔔 **عضو جدید به لیگ ملحق شد!**\n\n"
          f"👤 نام: **{display_name}**\n"
          f"🆔 آیدی عددی: `{user_id}`\n"
          f"🏷 نام کاربری: {user_tag}"
      )
      await context.bot.send_message(
          chat_id=ADMIN_ID, text=admin_msg, parse_mode="Markdown"
      )
    except Exception as e:
      logging.error(f"Error notifying admin: {e}")

  except sqlite3.IntegrityError:
    msg = (
        "ℹ️ شما قبلاً در لیگ عضو شده‌اید. برای تغییر نام از دستور `/rename`"
        " استفاده کنید."
    )
    if alert_func:
      await alert_func(msg, show_alert=True)
    elif reply_func:
      await reply_func(msg)


async def join(update: Update, context: ContextTypes.DEFAULT_TYPE):
  if not await enforce_channel_lock(update, context, check_lock=False):
    return
  await process_join_user(
      update.effective_user, context, reply_func=update.message.reply_text
  )


HISTORY_PAGE_SIZE = 8


async def render_public_history_page(update: Update, page: int):
  log_feature_click(update.effective_user.id, "آرشیو مسابقات")
  with sqlite3.connect("mafia_league.db") as conn:
    c = conn.cursor()
    c.execute(
        "SELECT match_id, scenario_name, winning_side, created_at, season FROM"
        " match_history ORDER BY match_id DESC"
    )
    all_matches = c.fetchall()

  if not all_matches:
    text = "📜 هنوز هیچ مسابقه‌ای در تاریخچه لیگ ثبت نشده است."
    keyboard = [[InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="back_to_start")]]
    if update.callback_query:
      try:
        await update.callback_query.message.reply_text(
            text, reply_markup=InlineKeyboardMarkup(keyboard)
        )
      except Exception:
        pass
    elif update.message:
      await update.message.reply_text(
          text, reply_markup=InlineKeyboardMarkup(keyboard)
      )
    return

  total_matches = len(all_matches)
  total_pages = max(1, math.ceil(total_matches / HISTORY_PAGE_SIZE))
  page = max(1, min(page, total_pages))

  start_idx = (page - 1) * HISTORY_PAGE_SIZE
  end_idx = min(start_idx + HISTORY_PAGE_SIZE, total_matches)
  page_matches = all_matches[start_idx:end_idx]

  text = (
      f"📜 **آرشیو و سوابق مسابقات لیگ** (صفحه {page} از {total_pages})\n"
      f"➖➖➖➖➖➖➖➖➖➖\n"
      f"برای مشاهده شناسنامه کامل هر بازی، روی دکمه مربوط به آن کلیک کنید:\n\n"
  )

  keyboard = []
  for m_id, scen, win_side, dt, s_num in page_matches:
    time_clean = dt.split()[0] if dt else ""
    icon = (
        "🏙" if win_side == "شهروند" else ("🔪" if win_side == "مافیا" else "🃏")
    )
    btn_label = (
        f"🎮 بازی #{m_id} [فصل {s_num}] | {scen} | {icon} {win_side}"
        f" ({time_clean})"
    )
    keyboard.append([
        InlineKeyboardButton(
            btn_label, callback_data=f"pub_match_view:{m_id}:{page}"
        )
    ])

  nav_row = []
  if page > 1:
    nav_row.append(
        InlineKeyboardButton(
            "⬅️ صفحه قبل", callback_data=f"pub_history_page:{page - 1}"
        )
    )
  if page < total_pages:
    nav_row.append(
        InlineKeyboardButton(
            "صفحه بعد ➡️", callback_data=f"pub_history_page:{page + 1}"
        )
    )

  if nav_row:
    keyboard.append(nav_row)
  keyboard.append([InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="back_to_start")])

  reply_markup = InlineKeyboardMarkup(keyboard)
  if update.callback_query:
    try:
      await update.callback_query.message.reply_text(
          text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown"
      )
    except Exception:
      pass
  elif update.message:
    await update.message.reply_text(
        text, reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def public_history_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
  if not await enforce_channel_lock(update, context, check_lock=False):
    return
  await render_public_history_page(update, 1)


async def show_public_match_details(
    update: Update, match_id: int, back_page: int
):
  log_feature_click(update.effective_user.id, "شناسنامه بازی")
  with sqlite3.connect("mafia_league.db") as conn:
    c = conn.cursor()
    c.execute(
        "SELECT match_id, scenario_name, winning_side, created_at, season, end_mode, chaos_players, chaos_selected, chaos_win_impact FROM"
        " match_history WHERE match_id = ?",
        (match_id,),
    )
    match = c.fetchone()
    if not match:
      try:
        await update.callback_query.message.reply_text("مسابقه مورد نظر پیدا نشد.")
      except Exception:
        pass
      return

    c.execute(
        "SELECT player_name, side, won, is_mvp, is_axe, is_unfair, is_artin, night1_shot, night1_out FROM match_participants"
        " WHERE match_id = ?",
        (match_id,),
    )
    participants = c.fetchall()

  cits = [p[0] for p in participants if p[1] == "شهروند"]
  mafs = [p[0] for p in participants if p[1] == "مافیا"]
  inds = [p[0] for p in participants if p[1] == "مستقل"]
  mvps = [p[0] for p in participants if p[3] == 1]
  axes = [p[0] for p in participants if p[4] == 1]
  unfairs = [p[0] for p in participants if p[5] == 1]
  artins = [p[0] for p in participants if p[6] == 1]
  
  n1_shot_player = next((p[0] for p in participants if p[7] == 1), None)
  n1_out_player = next((p[0] for p in participants if p[8] == 1), None)

  icon = "🏙" if match[2] == "شهروند" else ("🔪" if match[2] == "مافیا" else "🃏")

  text = (
      f"🎮 **شناسنامه مسابقه شماره #{match[0]} (فصل {match[4]})**\n"
      f"➖➖➖➖➖➖➖➖➖➖\n\n"
      f"🎬 سناریو اجرا شده: **{match[1]}**\n"
      f"🏆 ساید پیروز مسابقه: **{icon} {match[2]}**\n"
      f"🏁 نحوه پایان بازی: **{match[5]}**\n"
  )

  if match[5] == "کی آس" and match[6]:
    c_players = match[6].split(",")
    selected = match[7] or "ثبت نشده"
    impact = match[8] or "ثبت نشده"
    text += (
        f"🌪 بازیکنان کِی‌آس: `{', '.join(c_players)}`\n"
        f"🎯 فرد منتخب کِی‌آس: **{selected}**\n"
        f"💡 باعث برد سایدش شد؟ **{impact}**\n"
    )

  text += (
      f"\n🏙 **ساید شهروند:**\n▫️ {', '.join(cits) if cits else 'ثبت نشده'}\n\n"
      f"🔪 **ساید مافیا:**\n▫️ {', '.join(mafs) if mafs else 'ثبت نشده'}\n"
  )
  if inds:
    text += f"\n🃏 **ساید مستقل:**\n▫️ {', '.join(inds)}\n"

  text += (
      f"\n🎯 **شات شب اول توسط مافیا:**\n▫️ {n1_shot_player if n1_shot_player else 'ندارد'}\n"
      f"🚪 **وضعیت شات شب اول:** "
      f"{'خارج شد ❌' if n1_out_player else ('ماند ✅' if n1_shot_player else 'ثبت نشده')}\n\n"
      f"🌟 **بست پلیر بازی (MVP):**\n▫️"
      f" {', '.join(mvps) if mvps else 'ندارد'}\n"
      f"🪓 **پلیر تبر (Axe):**\n▫️"
      f" {', '.join(axes) if axes else 'ندارد'}\n"
      f"🐍 **پلیر آنفیر (Unfair):**\n▫️"
      f" {', '.join(unfairs) if unfairs else 'ندارد'}\n"
      f"👑 **پلیر آرتین (Artin):**\n▫️"
      f" {', '.join(artins) if artins else 'ندارد'}\n\n"
      f"⏱ زمان ثبت بازی: `{match[3]}`"
  )

  keyboard = [
      [
          InlineKeyboardButton(
              "🔙 بازگشت به لیست سوابق",
              callback_data=f"pub_history_page:{back_page}",
          )
      ],
      [InlineKeyboardButton("🏠 منوی اصلی", callback_data="back_to_start")],
  ]
  try:
    await update.callback_query.message.reply_text(
        text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown"
    )
  except Exception:
    pass


async def show_merge_picker_old(update: Update, context: ContextTypes.DEFAULT_TYPE):
  if update.effective_user.id != ADMIN_ID:
    return

  with sqlite3.connect("mafia_league.db") as conn:
    c = conn.cursor()
    c.execute("SELECT user_id, name FROM players ORDER BY name ASC")
    rows = c.fetchall()

  if len(rows) < 2:
    msg = "❌ حداقل باید ۲ بازیکن در سیستم باشد تا بتوانید ادغام انجام دهید."
    if update.callback_query:
      try:
        await update.callback_query.answer(msg, show_alert=True)
      except Exception:
        pass
    else:
      await update.message.reply_text(msg)
    return

  keyboard = []
  row = []
  for u_id, p_name in rows:
    label = p_name[:18] + ("..." if len(p_name) > 18 else "")
    row.append(
        InlineKeyboardButton(f"📜 {label}", callback_data=f"sel_mrg_old:{u_id}")
    )
    if len(row) == 2:
      keyboard.append(row)
      row = []
  if row:
    keyboard.append(row)

  keyboard.append([InlineKeyboardButton("🔙 بازگشت به پنل ادمین", callback_data="open_admin_panel")])
  text = (
      "🔄 **مرحله ۱ ادغام (حذف شونده):**\n\n"
      "لطفاً **نام قدیمی / ثبت دستی** که می‌خواهید تمام سوابقش منتقل و خودش"
      " **حذف** شود را انتخاب کنید:"
  )
  if update.callback_query:
    try:
      await update.callback_query.message.reply_text(
          text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown"
      )
    except Exception:
      pass
  else:
    await update.message.reply_text(
        text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown"
    )


async def show_merge_picker_new(
    update: Update, context: ContextTypes.DEFAULT_TYPE, old_uid: int
):
  with sqlite3.connect("mafia_league.db") as conn:
    c = conn.cursor()
    c.execute("SELECT name FROM players WHERE user_id = ?", (old_uid,))
    old_row = c.fetchone()
    old_name = old_row[0] if old_row else "بازیکن قدیمی"

    c.execute(
        "SELECT user_id, name FROM players WHERE user_id != ? ORDER BY name ASC",
        (old_uid,),
    )
    rows = c.fetchall()

  keyboard = []
  row = []
  for u_id, p_name in rows:
    label = p_name[:18] + ("..." if len(p_name) > 18 else "")
    row.append(
        InlineKeyboardButton(
            f"👤 {label}", callback_data=f"do_merge_final:{old_uid}:{u_id}"
        )
    )
    if len(row) == 2:
      keyboard.append(row)
      row = []
  if row:
    keyboard.append(row)

  keyboard.append([
      InlineKeyboardButton(
          "🔙 انتخاب مجدد نام قدیمی", callback_data="open_merge_picker_old"
      )
  ])
  text = (
      f"🗑 بازیکن قدیمی برای حذف: **{old_name}**\n\n"
      f"حالا **اکانت اصلی و دائمی تلگرام** بازیکن را انتخاب کنید که می‌خواهید"
      f" سوابق به او منتقل شود و در لیگ بماند:"
  )
  try:
    await update.callback_query.message.reply_text(
        text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown"
    )
  except Exception:
    pass


async def execute_final_merge(update: Update, old_uid: int, new_uid: int):
  with sqlite3.connect("mafia_league.db") as conn:
    c = conn.cursor()
    c.execute("SELECT name FROM players WHERE user_id = ?", (old_uid,))
    old_row = c.fetchone()
    c.execute("SELECT name, username FROM players WHERE user_id = ?", (new_uid,))
    new_row = c.fetchone()

    if not old_row or not new_row:
      try:
        await update.callback_query.message.reply_text("❌ یکی از بازیکنان یافت نشد.")
      except Exception:
        pass
      return

    old_manual_name = old_row[0]
    new_player_name = new_row[0]

    c.execute(
        "UPDATE match_participants SET player_name = ? WHERE player_name = ?",
        (new_player_name, old_manual_name),
    )
    c.execute("DELETE FROM players WHERE user_id = ?", (old_uid,))
    conn.commit()

  recalculate_all_players()

  text = (
      f"🎉 **ادغام با موفقیت انجام شد!**\n\n"
      f"✅ تمام سوابق و امتیازات «{old_manual_name}» به اکانت اصلی"
      f" «**{new_player_name}**» منتقل شد.\n"
      f"🗑 پروفایل قدیمی «{old_manual_name}» با موفقیت حذف گردید و اکانت"
      f" تلگرامی در لیگ باقی ماند."
  )
  keyboard = [[InlineKeyboardButton("🔙 بازگشت به پنل ادمین", callback_data="open_admin_panel")]]
  try:
    await update.callback_query.message.reply_text(
        text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown"
    )
  except Exception:
    pass


async def show_matches_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
  if update.effective_user.id not in [ADMIN_ID, ADMIN_ID_2]:
    return

  cur_season = get_current_season()
  with sqlite3.connect("mafia_league.db") as conn:
    c = conn.cursor()
    c.execute(
        "SELECT match_id, scenario_name, winning_side, created_at, season FROM"
        " match_history WHERE season = ? ORDER BY match_id ASC",
        (cur_season,),
    )
    rows = c.fetchall()

  if not rows:
    msg = f"هنوز هیچ مسابقه‌ای در فصل {cur_season} ثبت نشده است."
    if update.message:
      await update.message.reply_text(msg)
    elif update.callback_query:
      try:
        await update.callback_query.message.reply_text(msg)
      except Exception:
        pass
    return

  keyboard = []
  for idx, (m_id, scen, win_side, dt, s_num) in enumerate(rows, start=1):
    btn_text = f"🎮 بازی شماره {idx} | {scen} | برد: {win_side}"
    keyboard.append([
        InlineKeyboardButton(btn_text, callback_data=f"detail_match:{m_id}")
    ])

  keyboard.append([InlineKeyboardButton("🔙 بازگشت به پنل ادمین", callback_data="open_admin_panel")])
  text = (
      f"🗑 **فهرست مسابقات برای حذف در فصل {cur_season} (پنل ادمین):**\n"
      "شماره بازی‌ها به صورت مرتب نمایش داده شده‌اند. روی بازی مورد نظر برای حذف کلیک کنید:"
  )

  if update.message:
    await update.message.reply_text(
        text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown"
    )
  elif update.callback_query:
    try:
      await update.callback_query.message.reply_text(
          text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown"
      )
    except Exception:
      pass


async def show_match_details(update: Update, match_id: int):
  with sqlite3.connect("mafia_league.db") as conn:
    c = conn.cursor()
    c.execute(
        "SELECT match_id, scenario_name, winning_side, created_at, season, end_mode, chaos_players, chaos_selected, chaos_win_impact FROM"
        " match_history WHERE match_id = ?",
        (match_id,),
    )
    match = c.fetchone()
    if not match:
      try:
        await update.callback_query.message.reply_text("مسابقه مورد نظر پیدا نشد.")
      except Exception:
        pass
      return

    c.execute(
        "SELECT player_name, side, won, is_mvp, is_axe, is_unfair, is_artin, night1_shot, night1_out FROM match_participants"
        " WHERE match_id = ?",
        (match_id,),
    )
    participants = c.fetchall()

  cits = [p[0] for p in participants if p[1] == "شهروند"]
  mafs = [p[0] for p in participants if p[1] == "مافیا"]
  inds = [p[0] for p in participants if p[1] == "مستقل"]
  mvps = [p[0] for p in participants if p[3] == 1]
  axes = [p[0] for p in participants if p[4] == 1]
  unfairs = [p[0] for p in participants if p[5] == 1]
  artins = [p[0] for p in participants if p[6] == 1]
  n1_shot_player = next((p[0] for p in participants if p[7] == 1), None)
  n1_out_player = next((p[0] for p in participants if p[8] == 1), None)

  text = (
      f"🎮 **اطلاعات مسابقه شماره #{match[0]} (فصل {match[4]})**\n\n"
      f"🎬 سناریو: **{match[1]}**\n"
      f"🏆 ساید برنده: **{match[2]}**\n"
      f"🏁 نحوه پایان: **{match[5]}**\n"
  )
  if match[5] == "کی آس" and match[6]:
    c_players = match[6].split(",")
    text += (
        f"🌪 بازیکنان کِی‌آس: `{', '.join(c_players)}`\n"
        f"🎯 فرد منتخب: **{match[7]}**\n"
        f"💡 باعث برد سایدش شد؟ **{match[8]}**\n"
    )

  text += (
      f"🏙 شهروندان: {', '.join(cits) if cits else 'ندارد'}\n"
      f"🔪 مافیاها: {', '.join(mafs) if mafs else 'ندارد'}\n"
  )
  if inds:
    text += f"🃏 مستقل: {', '.join(inds)}\n"
  text += (
      f"🎯 شات شب اول: {n1_shot_player if n1_shot_player else 'ندارد'}\n"
      f"🚪 وضعیت شات شب اول: {'خارج شد' if n1_out_player else ('ماند' if n1_shot_player else 'ندارد')}\n\n"
      f"🌟 بست پلیر بازی (MVP): {', '.join(mvps) if mvps else 'ندارد'}\n"
      f"🪓 پلیر تبر (Axe): {', '.join(axes) if axes else 'ندارد'}\n"
      f"🐍 پلیر آنفیر (Unfair): {', '.join(unfairs) if unfairs else 'ندارد'}\n"
      f"👑 پلیر آرتین (Artin): {', '.join(artins) if artins else 'ندارد'}\n"
      f"⏱ تاریخ ثبت: `{match[3]}`\n\n"
      f"عملیات مورد نظر را انتخاب کنید:"
  )

  keyboard = [
      [
          InlineKeyboardButton(
              "🗑 حذف کامل این بازی و بازگشت امتیازات",
              callback_data=f"del_match_confirm:{match_id}",
          )
      ],
      [
          InlineKeyboardButton(
              "🔙 بازگشت به لیست مسابقات", callback_data="open_matches_list"
          )
      ],
  ]
  try:
    await update.callback_query.message.reply_text(
        text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown"
    )
  except Exception:
    pass


async def delete_match_by_id(update: Update, match_id: int):
  with sqlite3.connect("mafia_league.db") as conn:
    c = conn.cursor()
    c.execute(
        "DELETE FROM match_participants WHERE match_id = ?", (match_id,)
    )
    c.execute("DELETE FROM match_history WHERE match_id = ?", (match_id,))
    conn.commit()

  recalculate_all_players()

  msg = (
      f"🗑 **مسابقه با موفقیت حذف شد!**\nتمام امتیازات و ریتینگ‌های"
      " بازیکنان مجدداً بازسازی و اصلاح گردید."
  )
  keyboard = [[InlineKeyboardButton("🔙 بازگشت به لیست مسابقات", callback_data="open_matches_list")]]

  if update.callback_query:
    try:
      await update.callback_query.message.reply_text(
          msg, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown"
      )
    except Exception:
      pass
  elif update.message:
    await update.message.reply_text(
        msg, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown"
    )


async def delete_match_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
  if update.effective_user.id not in [ADMIN_ID, ADMIN_ID_2]:
    await update.message.reply_text("⛔️ فقط ادمین لیگ اجازه دسترسی دارد.")
    return

  if not context.args:
    await update.message.reply_text(
        "فرمت صحیح: `/delete_match [شناسه مسابقه]`\nمثال: `/delete_match 3`"
    )
    return

  try:
    m_id = int(context.args[0])
    await delete_match_by_id(update, m_id)
  except ValueError:
    await update.message.reply_text("شناسه مسابقه باید یک عدد باشد.")


async def add_player_manual(update: Update, context: ContextTypes.DEFAULT_TYPE):
  if update.effective_user.id != ADMIN_ID:
    await update.message.reply_text("⛔️ این دستور فقط مخصوص ادمین لیگ است.")
    return

  if not context.args:
    context.user_data["waiting_for_manual_add"] = True
    await update.message.reply_text(
        "➕ لطفاً **نام بازیکن قدیمی** را ارسال کنید تا بدون نیاز به اکانت ثبت"
        " شود:",
        parse_mode="Markdown",
    )
    return

  player_name = " ".join(context.args).strip()
  await apply_add_player(update, player_name)


async def apply_add_player(update, player_name):
  temp_user_id = -random.randint(100000, 999999)
  try:
    with sqlite3.connect("mafia_league.db") as conn:
      c = conn.cursor()
      c.execute(
          "INSERT INTO players (user_id, username, name) VALUES (?, '', ?)",
          (temp_user_id, player_name),
      )
      conn.commit()
    await update.message.reply_text(
        f"✅ بازیکن «**{player_name}**» به صورت دستی اضافه شد و اکنون در لیست"
        " ثبت مسابقات در دسترس است.",
        parse_mode="Markdown",
    )
  except sqlite3.IntegrityError:
    await update.message.reply_text(
        "❌ بازیکنی با این نام از قبل در سیستم وجود دارد."
    )


async def remove_player_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
  if update.effective_user.id != ADMIN_ID:
    await update.message.reply_text("⛔️ این دستور فقط مخصوص ادمین لیگ است.")
    return

  if not context.args:
    await show_remove_player_buttons(update, context)
    return

  player_name = " ".join(context.args).strip()
  await apply_remove_player_by_name(update, player_name)


async def show_remove_player_buttons(
    update: Update, context: ContextTypes.DEFAULT_TYPE
):
  with sqlite3.connect("mafia_league.db") as conn:
    c = conn.cursor()
    c.execute("SELECT user_id, name FROM players ORDER BY name ASC")
    rows = c.fetchall()

  if not rows:
    msg = "هنوز هیچ بازیکنی در سیستم ثبت نشده است."
    if update.message:
      await update.message.reply_text(msg)
    elif update.callback_query:
      try:
        await update.callback_query.message.reply_text(msg)
      except Exception:
        pass
    return

  keyboard = []
  row = []
  for u_id, p_name in rows:
    label = p_name[:18] + ("..." if len(p_name) > 18 else "")
    row.append(
        InlineKeyboardButton(f"🗑 {label}", callback_data=f"del_id:{u_id}")
    )
    if len(row) == 2:
      keyboard.append(row)
      row = []
  if row:
    keyboard.append(row)

  keyboard.append([InlineKeyboardButton("🔙 بازگشت به پنل ادمین", callback_data="open_admin_panel")])

  text = "🗑 **روی نام بازیکنی که می‌خواهید از لیگ حذف شود کلیک کنید:**"
  if update.message:
    await update.message.reply_text(
        text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown"
    )
  elif update.callback_query:
    try:
      await update.callback_query.message.reply_text(
          text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown"
      )
    except Exception:
      pass


async def apply_remove_player_by_id(update, user_id):
  with sqlite3.connect("mafia_league.db") as conn:
    c = conn.cursor()
    c.execute("SELECT name FROM players WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    if not row:
      msg = "❌ بازیکن پیدا نشد."
      try:
        await update.callback_query.message.reply_text(msg)
      except Exception:
        pass
      return

    player_name = row[0]
    c.execute("DELETE FROM players WHERE user_id = ?", (user_id,))
    c.execute(
        "DELETE FROM match_participants WHERE player_name = ?", (player_name,)
    )
    conn.commit()

  recalculate_all_players()
  msg = (
      f"🗑 بازیکن «**{player_name}**» با موفقیت از لیگ و تمامی سوابق حذف شد."
  )
  keyboard = [[InlineKeyboardButton("🔙 بازگشت به پنل ادمین", callback_data="open_admin_panel")]]
  try:
    await update.callback_query.message.reply_text(
        msg, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown"
    )
  except Exception:
    pass


async def apply_remove_player_by_name(update, player_name):
  with sqlite3.connect("mafia_league.db") as conn:
    c = conn.cursor()
    c.execute("SELECT name FROM players WHERE name = ?", (player_name,))
    if not c.fetchone():
      await update.message.reply_text(
          f"❌ بازیکنی با نام «{player_name}» در لیگ پیدا نشد."
      )
      return

    c.execute("DELETE FROM players WHERE name = ?", (player_name,))
    c.execute(
        "DELETE FROM match_participants WHERE player_name = ?", (player_name,)
    )
    conn.commit()

  recalculate_all_players()
  await update.message.reply_text(
      f"🗑 بازیکن «**{player_name}**» با موفقیت از لیگ و تمامی سوابق حذف شد.",
      parse_mode="Markdown",
  )


async def merge_players_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
  if update.effective_user.id != ADMIN_ID:
    await update.message.reply_text("⛔️ این دستور فقط مخصوص ادمین لیگ است.")
    return

  await show_merge_picker_old(update, context)


async def rename(update: Update, context: ContextTypes.DEFAULT_TYPE):
  if not await enforce_channel_lock(update, context, check_lock=False):
    return

  user_id = update.effective_user.id
  with sqlite3.connect("mafia_league.db") as conn:
    c = conn.cursor()
    c.execute("SELECT name FROM players WHERE user_id = ?", (user_id,))
    row = c.fetchone()

  if not row:
    await update.message.reply_text(
        "❌ شما هنوز در لیگ عضو نشده‌اید! ابتدا دستور `/join` را ارسال فرمایید."
    )
    return

  if context.args:
    new_name = " ".join(context.args).strip()
    await apply_rename(update, context, user_id, row[0], new_name)
  else:
    context.user_data["waiting_for_new_name"] = True
    await update.message.reply_text(
        f"نام فعلی شما «**{row[0]}**» است.\nلطفاً **نام جدید** خود را تایپ و ارسال"
        " کنید:",
        parse_mode="Markdown",
    )


async def handle_text_messages(
    update: Update, context: ContextTypes.DEFAULT_TYPE
):
  user_id = update.effective_user.id
  raw_text = (
      update.message.text.strip()
      if update.message and update.message.text
      else ""
  )

  if raw_text == "تکامل":
    await send_takamol_menu(update, context)
    return

  if context.user_data.get("waiting_for_new_name"):
    new_name = raw_text
    context.user_data.pop("waiting_for_new_name", None)

    with sqlite3.connect("mafia_league.db") as conn:
      c = conn.cursor()
      c.execute("SELECT name FROM players WHERE user_id = ?", (user_id,))
      row = c.fetchone()
      if not row:
        return
      old_name = row[0]

    await apply_rename(update, context, user_id, old_name, new_name)
    return

  if user_id == ADMIN_ID and context.user_data.get("waiting_for_manual_add"):
    p_name = raw_text
    context.user_data.pop("waiting_for_manual_add", None)
    await apply_add_player(update, p_name)
    return


async def apply_rename(update, context, user_id, old_name, new_name):
  if not new_name or len(new_name) < 2:
    await update.message.reply_text(
        "❌ نام انتخابی بسیار کوتاه است. لطفاً نام معتبری وارد کنید."
    )
    return

  try:
    with sqlite3.connect("mafia_league.db") as conn:
      c = conn.cursor()
      c.execute(
          "UPDATE players SET name = ? WHERE user_id = ?", (new_name, user_id)
      )
      c.execute(
          "UPDATE match_participants SET player_name = ? WHERE player_name = ?",
          (new_name, old_name),
      )
      conn.commit()

    await update.message.reply_text(
        f"✅ نام شما با موفقیت به «**{new_name}**» تغییر یافت.",
        parse_mode="Markdown",
    )
  except sqlite3.IntegrityError:
    await update.message.reply_text(
        "❌ این نام قبلاً توسط بازیکن دیگری در لیگ انتخاب شده است."
    )


PLAYERS_PAGE_SIZE = 15


async def render_players_list_page(
    update: Update, context: ContextTypes.DEFAULT_TYPE, page: int
):
  log_feature_click(update.effective_user.id, "فهرست بازیکنان")
  req_user_id = update.effective_user.id
  is_admin = req_user_id in [ADMIN_ID, ADMIN_ID_2]

  with sqlite3.connect("mafia_league.db") as conn:
    c = conn.cursor()
    c.execute("SELECT name, username FROM players ORDER BY name ASC")
    rows = c.fetchall()

  if not rows:
    text = "هنوز بازیکنی در سیستم ثبت نشده است."
    keyboard = [[InlineKeyboardButton("🔙 بازگشت به پنل ادمین", callback_data="open_admin_panel")]]
    if update.callback_query:
      try:
        await update.callback_query.message.reply_text(
            text, reply_markup=InlineKeyboardMarkup(keyboard)
        )
      except Exception:
        pass
    elif update.message:
      await update.message.reply_text(
          text, reply_markup=InlineKeyboardMarkup(keyboard)
      )
    return

  total_count = len(rows)
  total_pages = max(1, math.ceil(total_count / PLAYERS_PAGE_SIZE))
  page = max(1, min(page, total_pages))

  start_idx = (page - 1) * PLAYERS_PAGE_SIZE
  end_idx = min(start_idx + PLAYERS_PAGE_SIZE, total_count)
  page_rows = rows[start_idx:end_idx]

  text = f"📋 <b>فهرست بازیکنان لیگ</b> (صفحه {page} از {total_pages})\n"
  text += f"👥 کل اعضا: <code>{total_count}</code> نفر\n"
  text += "➖➖➖➖➖➖➖➖➖➖\n\n"

  for idx, r in enumerate(page_rows, start=start_idx + 1):
    safe_name = html.escape(r[0])
    if is_admin:
      if r[1]:
        safe_user = html.escape(r[1])
        tag = f" (@{safe_user})"
      else:
        tag = " (دستی/بدون آیدی)"
    else:
      tag = ""
    text += f"<code>{idx:02d}.</code> <b>{safe_name}</b>{tag}\n"

  nav_row = []
  if page > 1:
    nav_row.append(
        InlineKeyboardButton(
            "⬅️ صفحه قبل", callback_data=f"players_page:{page - 1}"
        )
    )
  if page < total_pages:
    nav_row.append(
        InlineKeyboardButton(
            "صفحه بعد ➡️", callback_data=f"players_page:{page + 1}"
        )
    )

  keyboard = []
  if nav_row:
    keyboard.append(nav_row)
  keyboard.append([InlineKeyboardButton("🔙 بازگشت به پنل ادمین", callback_data="open_admin_panel")])

  reply_markup = InlineKeyboardMarkup(keyboard)

  if update.callback_query:
    try:
      await update.callback_query.message.reply_text(
          text, reply_markup=reply_markup, parse_mode="HTML"
      )
    except Exception:
      pass
  elif update.message:
    await update.message.reply_text(
        text, reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def players_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
  await render_players_list_page(update, context, 1)


async def ask_table_season_choice(update: Update):
  seasons = get_available_seasons()
  keyboard = [[
      InlineKeyboardButton(
          "🌐 جدول کل تاریخچه (All-Time)", callback_data="table_page:all:1"
      )
  ]]
  row = []
  for s_num in seasons:
    row.append(
        InlineKeyboardButton(
            f"🏆 فصل {s_num}", callback_data=f"table_page:{s_num}:1"
        )
    )
    if len(row) == 2:
      keyboard.append(row)
      row = []
  if row:
    keyboard.append(row)

  keyboard.append([InlineKeyboardButton("🔙 بازگشت به منوی آمار", callback_data="open_stats_hub")])
  text = (
      "🏆 **جدول رده‌بندی لیگ:**\n\nلطفاً بازه مورد نظر را برای مشاهده رده‌‌بندی"
      " انتخاب فرمایید:"
  )

  if update.callback_query:
    try:
      await update.callback_query.message.reply_text(
          text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown"
      )
    except Exception:
      pass


PAGE_SIZE = 10


async def render_table_page_filtered(
    update: Update, season_filter: str, page: int
):
  log_feature_click(update.effective_user.id, f"جدول لیگ ({season_filter})")

  with sqlite3.connect("mafia_league.db") as conn:
    c = conn.cursor()
    if season_filter == "all":
      season_title = "کل تاریخچه (All-Time)"
      c.execute("SELECT DISTINCT player_name FROM match_participants")
      active_players = [r[0] for r in c.fetchall()]

      c.execute("SELECT name FROM players")
      all_db_players = [r[0] for r in c.fetchall()]
      players_pool = sorted(list(set(active_players + all_db_players)))

      ranking = []
      for p_name in players_pool:
        c.execute(
            """
                    SELECT won, is_mvp, is_axe, is_unfair, is_artin 
                    FROM match_participants 
                    WHERE player_name = ?
                    ORDER BY match_id ASC
                """,
            (p_name,),
        )
        matches = c.fetchall()
        total_g = len(matches)
        wins = sum(1 for m in matches if m[0] == 1)
        losses = total_g - wins
        mvps = sum(1 for m in matches if m[1] == 1)
        axes = sum(1 for m in matches if m[2] == 1)
        unfairs = sum(1 for m in matches if m[3] == 1)
        artins = sum(1 for m in matches if m[4] == 1)

        raw = 0
        cur_streak = 0
        for m in matches:
          game_pts = (
              (10 if m[0] == 1 else 0)
              + (4 if m[1] == 1 else 0)
              + (-3 if m[2] == 1 else 0)
              + (-6 if m[3] == 1 else 0)
              + (-8 if m[4] == 1 else 0)
          )
          if m[0] == 1:
            cur_streak += 1
            if cur_streak >= 3:
              game_pts += 2
          else:
            cur_streak = 0
          raw += game_pts

        rate = calculate_rating(raw, total_g)
        win_rate = round((wins / total_g * 100), 1) if total_g > 0 else 0
        ranking.append({
            "name": p_name,
            "rating": rate,
            "raw_score": raw,
            "total_games": total_g,
            "wins": wins,
            "losses": losses,
            "mvp": mvps,
            "axe": axes,
            "unfair": unfairs,
            "artin": artins,
            "streak": cur_streak,
            "win_rate": win_rate,
        })
    else:
      s_int = int(season_filter)
      season_title = f"فصل {s_int}"
      cur_season = get_current_season()

      if s_int == cur_season:
        c.execute(
            "SELECT name, raw_score, total_games, wins, losses, mvp_count,"
            " axe_count, unfair_count, artin_count, current_streak FROM players"
        )
        rows = c.fetchall()
        ranking = []
        for r in rows:
          rate = calculate_rating(r[1], r[2])
          win_rate = round((r[3] / r[2] * 100), 1) if r[2] > 0 else 0
          ranking.append({
              "name": r[0],
              "rating": rate,
              "raw_score": r[1],
              "total_games": r[2],
              "wins": r[3],
              "losses": r[4],
              "mvp": r[5],
              "axe": r[6],
              "unfair": r[7],
              "artin": r[8],
              "streak": r[9],
              "win_rate": win_rate,
          })
      else:
        c.execute(
            """
                    SELECT player_name, final_rating, raw_score, total_games, wins, losses, mvp_count, axe_count, unfair_count, artin_count 
                    FROM season_archives 
                    WHERE season = ? 
                    ORDER BY final_rank ASC
                """,
            (s_int,),
        )
        rows = c.fetchall()
        ranking = []
        for r in rows:
          win_rate = round((r[4] / r[3] * 100), 1) if r[3] > 0 else 0
          ranking.append({
              "name": r[0],
              "rating": r[1],
              "raw_score": r[2],
              "total_games": r[3],
              "wins": r[4],
              "losses": r[5],
              "mvp": r[6],
              "axe": r[7],
              "unfair": r[8],
              "artin": r[9],
              "streak": 0,
              "win_rate": win_rate,
          })

  if not ranking:
    text = f"هنوز داده‌ای در جدول {season_title} ثبت نشده است."
    keyboard = [
        [
            InlineKeyboardButton(
                "🔄 انتخاب فصلی دیگر", callback_data="ask_table_season"
            )
        ],
        [InlineKeyboardButton("🔙 بازگشت به منوی آمار", callback_data="open_stats_hub")],
    ]
    if update.callback_query:
      try:
        await update.callback_query.message.reply_text(
            text, reply_markup=InlineKeyboardMarkup(keyboard)
        )
      except Exception:
        pass
    elif update.message:
      await update.message.reply_text(
          text, reply_markup=InlineKeyboardMarkup(keyboard)
      )
    return

  ranking.sort(key=lambda x: (x["rating"], x["raw_score"], x["wins"]), reverse=True)

  total_players = len(ranking)
  total_pages = max(1, math.ceil(total_players / PAGE_SIZE))
  page = max(1, min(page, total_pages))

  start_idx = (page - 1) * PAGE_SIZE
  end_idx = min(start_idx + PAGE_SIZE, total_players)
  page_players = ranking[start_idx:end_idx]

  text = (
      f"🏆 **جدول رده‌بندی لیگ تکامل ({season_title})** 🏆\n"
      f"صفحه {page} از {total_pages}\n"
      f"➖➖➖➖➖➖➖➖➖➖\n\n"
  )

  for i, p in enumerate(page_players, start=start_idx + 1):
    medal = (
        "🥇"
        if i == 1
        else "🥈" if i == 2 else "🥉" if i == 3 else f"`#{i:02d}`"
    )
    crown = " 👑" if i == 1 else ""
    streak_badge = f" 🔥`{p['streak']}`" if p["streak"] > 1 else ""
    title_badge = " ⟨ 🏛 **امپراطور لیگ** ⟩" if i == 1 else ""

    text += (
        f"{medal} **{p['name']}**{crown}{title_badge}{streak_badge}\n"
        f"   ▫️ ریتینگ: `{p['rating']}` | امتیاز: `{p['raw_score']}`\n"
        f"   ▫️ بازی: `{p['total_games']}` (برد: `{p['wins']}` / باخت:"
        f" `{p['losses']}`) | WR: `{p['win_rate']}%`\n"
        f"   ▫️ بست‌ها: 🌟`{p['mvp']}` | تبرها: 🪓`{p['axe']}` | نامردها: 🐍`{p['unfair']}` | آرتین‌ها: 👑`{p['artin']}`\n"
        f"────────────────────\n"
    )

  text += f"👥 کل شرکت‌کنندگان این بازه: `{total_players}` نفر"

  nav_row = []
  if page > 1:
    nav_row.append(
        InlineKeyboardButton(
            "⬅️ صفحه قبل", callback_data=f"table_page:{season_filter}:{page - 1}"
        )
    )
  if page < total_pages:
    nav_row.append(
        InlineKeyboardButton(
            "صفحه بعد ➡️", callback_data=f"table_page:{season_filter}:{page + 1}"
        )
    )

  keyboard = []
  if nav_row:
    keyboard.append(nav_row)
  keyboard.append([
      InlineKeyboardButton(
          "🔄 تغییر فصل / بازه جدول", callback_data="ask_table_season"
      )
  ])
  keyboard.append([InlineKeyboardButton("🔙 بازگشت به منوی آمار", callback_data="open_stats_hub")])

  reply_markup = InlineKeyboardMarkup(keyboard)

  if update.callback_query:
    try:
      await update.callback_query.message.reply_text(
          text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown"
      )
    except Exception:
      pass
  elif update.message:
    await update.message.reply_text(
        text, reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def table(update: Update, context: ContextTypes.DEFAULT_TYPE):
  if not await enforce_channel_lock(update, context, check_lock=True):
    return
  cur_season = get_current_season()
  await render_table_page_filtered(update, str(cur_season), 1)


async def ask_bests_season_choice(update: Update):
  seasons = get_available_seasons()
  keyboard = [[
      InlineKeyboardButton(
          "🌐 تالار کل تاریخچه (All-Time)", callback_data="bests_page:all:1"
      )
  ]]
  row = []
  for s_num in seasons:
    row.append(
        InlineKeyboardButton(
            f"🌟 فصل {s_num}", callback_data=f"bests_page:{s_num}:1"
        )
    )
    if len(row) == 2:
      keyboard.append(row)
      row = []
  if row:
    keyboard.append(row)

  keyboard.append([InlineKeyboardButton("🔙 بازگشت به منوی آمار", callback_data="open_stats_hub")])
  text = (
      "🌟 **تالار افتخارات بست‌پلیرهای بازی:**\n\nمایلید بست‌های کدام بازه را مشاهده"
      " کنید؟"
  )

  if update.callback_query:
    try:
      await update.callback_query.message.reply_text(
          text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown"
      )
    except Exception:
      pass


async def render_bests_page_filtered(
    update: Update, season_filter: str, page: int
):
  log_feature_click(update.effective_user.id, f"بست‌پلیرها ({season_filter})")
  with sqlite3.connect("mafia_league.db") as conn:
    c = conn.cursor()
    if season_filter == "all":
      season_title = "کل تاریخچه (All-Time)"
      c.execute("""
                SELECT player_name, 
                       SUM(is_mvp) as mvps, 
                       SUM(is_mvp) as total_bests,
                       COUNT(*) as total_games
                FROM match_participants
                GROUP BY player_name
                HAVING SUM(is_mvp) > 0
                ORDER BY mvps DESC, total_games ASC
            """)
      rows = c.fetchall()
    else:
      s_int = int(season_filter)
      season_title = f"فصل {s_int}"
      cur_season = get_current_season()
      if s_int == cur_season:
        c.execute("""
                    SELECT name, mvp_count, mvp_count as total_bests, total_games
                    FROM players
                    WHERE mvp_count > 0
                    ORDER BY mvp_count DESC, total_games ASC
                """)
        rows = c.fetchall()
      else:
        c.execute(
            """
                    SELECT player_name, mvp_count, mvp_count as total_bests, total_games
                    FROM season_archives
                    WHERE season = ? AND mvp_count > 0
                    ORDER BY mvp_count DESC, total_games ASC
                """,
            (s_int,),
        )
        rows = c.fetchall()

  if not rows:
    text = f"🌟 هنوز هیچ بست پلیری در {season_title} ثبت نشده است."
    keyboard = [
        [
            InlineKeyboardButton(
                "🔄 انتخاب فصلی دیگر", callback_data="ask_bests_season"
            )
        ],
        [InlineKeyboardButton("🔙 بازگشت به منوی آمار", callback_data="open_stats_hub")],
    ]
    if update.callback_query:
      try:
        await update.callback_query.message.reply_text(
            text, reply_markup=InlineKeyboardMarkup(keyboard)
        )
      except Exception:
        pass
    elif update.message:
      await update.message.reply_text(
          text, reply_markup=InlineKeyboardMarkup(keyboard)
      )
    return

  total_bests_count = len(rows)
  total_pages = max(1, math.ceil(total_bests_count / PAGE_SIZE))
  page = max(1, min(page, total_pages))

  start_idx = (page - 1) * PAGE_SIZE
  end_idx = min(start_idx + PAGE_SIZE, total_bests_count)
  page_rows = rows[start_idx:end_idx]

  text = (
      f"🌟 **تالار افتخارات برترین بست پلیرهای بازی ({season_title})**\n"
      f"صفحه {page} از {total_pages}\n"
      f"➖➖➖➖➖➖➖➖➖➖\n\n"
  )

  for rank, r in enumerate(page_rows, start=start_idx + 1):
    medal = (
        "🥇"
        if rank == 1
        else "🥈" if rank == 2 else "🥉" if rank == 3 else f"`#{rank:02d}`"
    )
    crown = " 👑" if rank == 1 else ""
    title_badge = " ⟨ ⚡ **ترس واقعی** ⟩" if rank == 1 else ""

    mvp_bar = "🌟" * min(r[1], 8)
    stars_line = f"{mvp_bar}"

    text += (
        f"{medal} **{r[0]}**{crown}{title_badge}\n"
        f"   ✨ نشان‌ها: {stars_line}\n"
        f"   ▫️ بست پلیر بازی (MVP): `{r[1]}` بار\n"
        f"   ▫️ مجموع کل بست‌ها: `{r[2]}` عدد (در {r[3]} مسابقه)\n"
        f"────────────────────\n"
    )

  text += f"🎖 کل بازیکنان دارای نشان بست: `{total_bests_count}` نفر"

  nav_row = []
  if page > 1:
    nav_row.append(
        InlineKeyboardButton(
            "⬅️ صفحه قبل", callback_data=f"bests_page:{season_filter}:{page - 1}"
        )
    )
  if page < total_pages:
    nav_row.append(
        InlineKeyboardButton(
            "صفحه بعد ➡️", callback_data=f"bests_page:{season_filter}:{page + 1}"
        )
    )

  keyboard = []
  if nav_row:
    keyboard.append(nav_row)
  keyboard.append([
      InlineKeyboardButton(
          "🔄 تغییر فصل / بازه تالار", callback_data="ask_bests_season"
      )
  ])
  keyboard.append([InlineKeyboardButton("🔙 بازگشت به منوی آمار", callback_data="open_stats_hub")])

  reply_markup = InlineKeyboardMarkup(keyboard)

  if update.callback_query:
    try:
      await update.callback_query.message.reply_text(
          text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown"
      )
    except Exception:
      pass
  elif update.message:
    await update.message.reply_text(
        text, reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def best_players_leaderboard(
    update: Update, context: ContextTypes.DEFAULT_TYPE
):
  if not await enforce_channel_lock(update, context, check_lock=True):
    return
  cur_season = get_current_season()
  await render_bests_page_filtered(update, str(cur_season), 1)


async def axes_leaderboard(
    update: Update, context: ContextTypes.DEFAULT_TYPE
):
  if not await enforce_channel_lock(update, context, check_lock=True):
    return
  cur_season = get_current_season()
  await render_axes_page_filtered(update, str(cur_season), 1)


async def unfair_leaderboard(
    update: Update, context: ContextTypes.DEFAULT_TYPE
):
  if not await enforce_channel_lock(update, context, check_lock=True):
    return
  cur_season = get_current_season()
  await render_unfair_page_filtered(update, str(cur_season), 1)


async def artin_leaderboard(
    update: Update, context: ContextTypes.DEFAULT_TYPE
):
  if not await enforce_channel_lock(update, context, check_lock=True):
    return
  cur_season = get_current_season()
  await render_artin_page_filtered(update, str(cur_season), 1)


async def ask_vs_season_choice(update: Update):
  seasons = get_available_seasons()
  keyboard = [[
      InlineKeyboardButton(
          "🌐 تقابل در کل تاریخچه (All-Time)",
          callback_data="open_vs_picker_1:all",
      )
  ]]
  row = []
  for s_num in seasons:
    row.append(
        InlineKeyboardButton(
            f"⚔️ تقابل در فصل {s_num}", callback_data=f"open_vs_picker_1:{s_num}"
        )
    )
    if len(row) == 2:
      keyboard.append(row)
      row = []
  if row:
    keyboard.append(row)

  keyboard.append([InlineKeyboardButton("🔙 بازگشت به منوی آمار", callback_data="open_stats_hub")])
  text = (
      "⚔️ **دوئل و تقابل دو نفره:**\n\nمایلید آمار رودرروی دو بازیکن در چه"
      " بازه‌ای مقایسه شود؟"
  )

  if update.callback_query:
    try:
      await update.callback_query.message.reply_text(
          text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown"
      )
    except Exception:
      pass


async def show_vs_picker_first(
    update: Update, context: ContextTypes.DEFAULT_TYPE, season_filter: str
):
  log_feature_click(update.effective_user.id, "دوئل و تقابل رودررو")
  with sqlite3.connect("mafia_league.db") as conn:
    c = conn.cursor()
    c.execute("SELECT user_id, name FROM players ORDER BY name ASC")
    rows = c.fetchall()

  if len(rows) < 2:
    msg = "❌ برای تقابل، حداقل باید ۲ بازیکن در لیگ ثبت شده باشند."
    if update.message:
      await update.message.reply_text(msg)
    elif update.callback_query:
      try:
        await update.callback_query.message.reply_text(msg)
      except Exception:
        pass
    return

  keyboard = []
  row = []
  for u_id, p_name in rows:
    label = p_name[:18] + ("..." if len(p_name) > 18 else "")
    row.append(
        InlineKeyboardButton(
            f"⚔️ {label}", callback_data=f"vs_p1:{season_filter}:{u_id}"
        )
    )
    if len(row) == 2:
      keyboard.append(row)
      row = []
  if row:
    keyboard.append(row)

  keyboard.append([
      InlineKeyboardButton(
          "🔄 تغییر فصل دوئل", callback_data="ask_vs_season"
      )
  ])
  keyboard.append([InlineKeyboardButton("🔙 بازگشت به منوی آمار", callback_data="open_stats_hub")])

  b_title = "کل تاریخچه" if season_filter == "all" else f"فصل {season_filter}"
  text = (
      f"⚔️ **دوئل و تقابل دو نفره ({b_title}):**\n\nمبارز **اول** را انتخاب"
      " فرمایید:"
  )

  if update.message:
    await update.message.reply_text(
        text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown"
    )
  elif update.callback_query:
    try:
      await update.callback_query.message.reply_text(
          text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown"
      )
    except Exception:
      pass


async def show_vs_picker_second(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    season_filter: str,
    first_uid: int,
):
  with sqlite3.connect("mafia_league.db") as conn:
    c = conn.cursor()
    c.execute("SELECT name FROM players WHERE user_id = ?", (first_uid,))
    first_row = c.fetchone()
    first_name = first_row[0] if first_row else "مبارز اول"

    c.execute(
        "SELECT user_id, name FROM players WHERE user_id != ? ORDER BY name ASC",
        (first_uid,),
    )
    rows = c.fetchall()

  keyboard = []
  row = []
  for u_id, p_name in rows:
    label = p_name[:18] + ("..." if len(p_name) > 18 else "")
    row.append(
        InlineKeyboardButton(
            f"⚔️ {label}",
            callback_data=f"vs_p2:{season_filter}:{first_uid}:{u_id}",
        )
    )
    if len(row) == 2:
      keyboard.append(row)
      row = []
  if row:
    keyboard.append(row)

  keyboard.append([
      InlineKeyboardButton(
          "🔙 تغییر مبارز اول",
          callback_data=f"open_vs_picker_1:{season_filter}",
      )
  ])
  text = (
      f"⚔️ مبارز اول: **{first_name}**\n\nحریف و مبارز **دوم** را انتخاب کنید:"
  )

  try:
    await update.callback_query.message.reply_text(
        text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown"
    )
  except Exception:
    pass


async def render_vs_comparison_filtered(
    update: Update, season_filter: str, uid1: int, uid2: int
):
  with sqlite3.connect("mafia_league.db") as conn:
    c = conn.cursor()
    c.execute("SELECT * FROM players WHERE user_id = ?", (uid1,))
    p1 = c.fetchone()
    c.execute("SELECT * FROM players WHERE user_id = ?", (uid2,))
    p2 = c.fetchone()

    if not p1 or not p2:
      try:
        await update.callback_query.message.reply_text("بازیکنان پیدا نشدند.")
      except Exception:
        pass
      return

    name1, name2 = p1[2], p2[2]

    if season_filter == "all":
      season_label = "کل تاریخچه (All-Time)"
      season_cond = ""
      params_rival = (name1, name2)
      params_coop = (name1, name2)
      p1_match_query = (
          "SELECT won, is_mvp FROM match_participants WHERE player_name"
          " = ?"
      )
      p2_match_query = (
          "SELECT won, is_mvp FROM match_participants WHERE player_name"
          " = ?"
      )
      p1_params = (name1,)
      p2_params = (name2,)
    else:
      s_int = int(season_filter)
      season_label = f"فصل {s_int}"
      season_cond = "AND m.season = ?"
      params_rival = (name1, name2, s_int)
      params_coop = (name1, name2, s_int)
      p1_match_query = (
          "SELECT p.won, p.is_mvp FROM match_participants p JOIN"
          " match_history m ON p.match_id = m.match_id WHERE p.player_name = ?"
          " AND m.season = ?"
      )
      p2_match_query = (
          "SELECT p.won, p.is_mvp FROM match_participants p JOIN"
          " match_history m ON p.match_id = m.match_id WHERE p.player_name = ?"
          " AND m.season = ?"
      )
      p1_params = (name1, s_int)
      p2_params = (name2, s_int)

    c.execute(
        f"""
            SELECT p1.won, p2.won
            FROM match_participants p1
            JOIN match_participants p2 ON p1.match_id = p2.match_id
            JOIN match_history m ON p1.match_id = m.match_id
            WHERE p1.player_name = ? AND p2.player_name = ? AND p1.side != p2.side {season_cond}
        """,
        params_rival,
    )
    rival_matches = c.fetchall()
    p1_direct_wins = sum(1 for m in rival_matches if m[0] == 1)
    p2_direct_wins = sum(1 for m in rival_matches if m[1] == 1)
    total_rival_games = len(rival_matches)

    c.execute(
        f"""
            SELECT p1.won
            FROM match_participants p1
            JOIN match_participants p2 ON p1.match_id = p2.match_id
            JOIN match_history m ON p1.match_id = m.match_id
            WHERE p1.player_name = ? AND p2.player_name = ? AND p1.side = p2.side {season_cond}
        """,
        params_coop,
    )
    coop_matches = c.fetchall()
    coop_wins = sum(1 for m in coop_matches if m[0] == 1)
    total_coop = len(coop_matches)

    c.execute(p1_match_query, p1_params)
    p1_matches = c.fetchall()
    p1_g = len(p1_matches)
    p1_w = sum(1 for m in p1_matches if m[0] == 1)
    p1_mvp = sum(1 for m in p1_matches if m[1] == 1)
    p1_raw = sum(
        (10 if m[0] == 1 else 0) + (4 if m[1] == 1 else 0)
        for m in p1_matches
    )
    r1 = calculate_rating(p1_raw, p1_g)

    c.execute(p2_match_query, p2_params)
    p2_matches = c.fetchall()
    p2_g = len(p2_matches)
    p2_w = sum(1 for m in p2_matches if m[0] == 1)
    p2_mvp = sum(1 for m in p2_matches if m[1] == 1)
    p2_raw = sum(
        (10 if m[0] == 1 else 0) + (4 if m[1] == 1 else 0)
        for m in p2_matches
    )
    r2 = calculate_rating(p2_raw, p2_g)

  win_rate1 = round((p1_w / p1_g * 100), 1) if p1_g > 0 else 0
  win_rate2 = round((p2_w / p2_g * 100), 1) if p2_g > 0 else 0

  total_rate = (r1 + r2) if (r1 + r2) > 0 else 1
  p1_bar_len = int(round((r1 / total_rate) * 10))
  p2_bar_len = 10 - p1_bar_len
  power_bar = ("🟩" * p1_bar_len) + ("🟥" * p2_bar_len)

  r1_crown = "👑 " if r1 > r2 else ""
  r2_crown = "👑 " if r2 > r1 else ""

  text = (
      f"⚔️ **دوئل نفس‌گیر و تقابل رودررو:**\n"
      f"🟩 **{name1}** VS 🟥 **{name2}**\n"
      f"🗓 **بازه مقایسه:** `{season_label}`\n\n"
      f"📊 **شاخص برتری قدرت:**\n"
      f"[{power_bar}]\n"
      f"▫️ 🟩 {name1}: `{r1}` ریتینگ {r1_crown}\n"
      f"▫️ 🟥 {name2}: `{r2}` ریتینگ {r2_crown}\n\n"
      f"🥊 **تاریخچه رویارویی مستقیم (ساید مخالف):**\n"
      f"▫️ کل مسابقات روبه‌‌رو: `{total_rival_games}` دست\n"
      f"▫️ بردهای 🟩 {name1}: `{p1_direct_wins}` پیروزی\n"
      f"▫️ بردهای 🟥 {name2}: `{p2_direct_wins}` پیروزی\n\n"
      f"🤝 **همکاری در یک تیم (ساید مشترک):**\n"
      f"▫️ بازی‌های هم‌تیمی: `{total_coop}` دست (`{coop_wins}` برد مشترک)\n\n"
      f"📋 **مقایسه فاکتورهای کلیدی در این بازه:**\n"
      f"▫️ **نرخ برد:** 🟩 `{win_rate1}%` | 🟥 `{win_rate2}%`\n"
      f"▫️ **تعداد کل بردها:** 🟩 `{p1_w}` برد | 🟥 `{p2_w}` برد\n"
      f"▫️ **کل بازی‌های انجام داده:** 🟩 `{p1_g}` دست | 🟥 `{p2_g}` دست\n"
      f"▫️ **بست پلیر بازی (MVP):** 🟩 `{p1_mvp}` بار | 🟥 `{p2_mvp}` بار\n"
  )

  keyboard = [
      [
          InlineKeyboardButton(
              "⚔️ انتخاب تقابل دونفره دیگر",
              callback_data=f"open_vs_picker_1:{season_filter}",
          )
      ],
      [
          InlineKeyboardButton(
              "🔄 تغییر فصل / بازه دوئل", callback_data="ask_vs_season"
          )
      ],
      [InlineKeyboardButton("🔙 بازگشت به منوی آمار", callback_data="open_stats_hub")],
  ]
  try:
    await update.callback_query.message.reply_text(
        text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown"
    )
  except Exception:
    pass


async def vs(update: Update, context: ContextTypes.DEFAULT_TYPE):
  if not await enforce_channel_lock(update, context, check_lock=True):
    return
  await ask_vs_season_choice(update)


async def show_stats_picker(update: Update, context: ContextTypes.DEFAULT_TYPE):
  log_feature_click(update.effective_user.id, "آمار بازیکنان")
  with sqlite3.connect("mafia_league.db") as conn:
    c = conn.cursor()
    c.execute("SELECT user_id, name FROM players ORDER BY name ASC")
    rows = c.fetchall()

  if not rows:
    msg = "هنوز بازیکنی ثبت نشده است."
    if update.message:
      await update.message.reply_text(msg)
    elif update.callback_query:
      try:
        await update.callback_query.message.reply_text(msg)
      except Exception:
        pass
    return

  keyboard = []
  row = []
  for u_id, p_name in rows:
    label = p_name[:18] + ("..." if len(p_name) > 18 else "")
    row.append(
        InlineKeyboardButton(
            f"👤 {label}", callback_data=f"ask_stat_season:{u_id}"
        )
    )
    if len(row) == 2:
      keyboard.append(row)
      row = []
  if row:
    keyboard.append(row)

  keyboard.append([InlineKeyboardButton("🔙 بازگشت به منوی آمار", callback_data="open_stats_hub")])
  text = "👤 **روی نام بازیکن مورد نظر کلیک کنید تا آمار او را بررسی کنید:**"

  if update.message:
    await update.message.reply_text(
        text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown"
    )
  elif update.callback_query:
    try:
      await update.callback_query.message.reply_text(
          text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown"
      )
    except Exception:
      pass


async def ask_stat_season_choice(update: Update, user_id: int):
  with sqlite3.connect("mafia_league.db") as conn:
    c = conn.cursor()
    c.execute("SELECT name FROM players WHERE user_id = ?", (user_id,))
    p = c.fetchone()
    if not p:
      try:
        await update.callback_query.message.reply_text("بازیکن پیدا نشد.")
      except Exception:
        pass
      return
    name = p[0]

  seasons = get_available_seasons()
  keyboard = [[
      InlineKeyboardButton(
          "🌐 آمار کل تاریخچه (All-Time)",
          callback_data=f"view_stat_target:{user_id}:all",
      )
  ]]
  row = []
  for s_num in seasons:
    row.append(
        InlineKeyboardButton(
            f"🏆 فصل {s_num}", callback_data=f"view_stat_target:{user_id}:{s_num}"
        )
    )
    if len(row) == 2:
      keyboard.append(row)
      row = []
  if row:
    keyboard.append(row)

  keyboard.append([
      InlineKeyboardButton(
          "🔙 بازگشت به انتخاب بازیکن", callback_data="open_stats_picker"
      )
  ])

  text = (
      f"👤 بازیکن انتخابی: **{name}**\n\nلطفاً مشخص کنید مایل به مشاهده آمار"
      f" **کل تاریخچه** هستید یا یک **فصل خاص**؟"
  )
  try:
    await update.callback_query.message.reply_text(
        text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown"
    )
  except Exception:
    pass


async def show_chart_picker(update: Update, context: ContextTypes.DEFAULT_TYPE):
  log_feature_click(update.effective_user.id, "نمودار پیشرفت")
  with sqlite3.connect("mafia_league.db") as conn:
    c = conn.cursor()
    c.execute("SELECT user_id, name FROM players ORDER BY name ASC")
    rows = c.fetchall()

  if not rows:
    msg = "هنوز بازیکنی ثبت نشده است."
    if update.message:
      await update.message.reply_text(msg)
    elif update.callback_query:
      try:
        await update.callback_query.message.reply_text(msg)
      except Exception:
        pass
    return

  keyboard = []
  row = []
  for u_id, p_name in rows:
    label = p_name[:18] + ("..." if len(p_name) > 18 else "")
    row.append(
        InlineKeyboardButton(
            f"📈 {label}", callback_data=f"ask_chart_season:{u_id}"
        )
    )
    if len(row) == 2:
      keyboard.append(row)
      row = []
  if row:
    keyboard.append(row)

  keyboard.append([InlineKeyboardButton("🔙 بازگشت به منوی آمار", callback_data="open_stats_hub")])
  text = (
      "📈 **روی نام بازیکن مورد نظر کلیک کنید تا نوع نمودار او انتخاب شود:**"
  )

  if update.message:
    await update.message.reply_text(
        text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown"
    )
  elif update.callback_query:
    try:
      await update.callback_query.message.reply_text(
          text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown"
      )
    except Exception:
      pass


async def ask_chart_season_choice(update: Update, user_id: int):
  with sqlite3.connect("mafia_league.db") as conn:
    c = conn.cursor()
    c.execute("SELECT name FROM players WHERE user_id = ?", (user_id,))
    p = c.fetchone()
    if not p:
      try:
        await update.callback_query.message.reply_text("بازیکن پیدا نشد.")
      except Exception:
        pass
      return
    name = p[0]

  seasons = get_available_seasons()
  keyboard = [
      [
          InlineKeyboardButton(
              "🔵 نمودار ریتینگ هوشمند (All-Time)",
              callback_data=f"view_chart_target:{user_id}:all:rating",
          ),
          InlineKeyboardButton(
              "⭐ نمودار پیشرفته/ارزش برد (All-Time)",
              callback_data=f"view_chart_target:{user_id}:all:adv",
          )
      ]
  ]
  row_rate = []
  row_adv = []
  for s_num in seasons:
    row_rate.append(
        InlineKeyboardButton(
            f"📊 ریتینگ فصل {s_num}", callback_data=f"view_chart_target:{user_id}:{s_num}:rating"
        )
    )
    row_adv.append(
        InlineKeyboardButton(
            f"⭐ پیشرفته فصل {s_num}", callback_data=f"view_chart_target:{user_id}:{s_num}:adv"
        )
    )
    if len(row_rate) == 2:
      keyboard.append(row_rate)
      row_rate = []
    if len(row_adv) == 2:
      keyboard.append(row_adv)
      row_adv = []
  if row_rate:
    keyboard.append(row_rate)
  if row_adv:
    keyboard.append(row_adv)

  keyboard.append([
      InlineKeyboardButton(
          "🔙 بازگشت به انتخاب بازیکن", callback_data="open_chart_picker"
      )
  ])

  text = (
      f"📈 بازیکن انتخابی: **{name}**\n\nمایلید چه نوع نموداری و برای چه بازه‌ای رسم شود؟"
  )
  try:
    await update.callback_query.message.reply_text(
        text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown"
    )
  except Exception:
    pass


async def render_player_stats(update: Update, user_id: int, season_filter: str):
  with sqlite3.connect("mafia_league.db") as conn:
    c = conn.cursor()
    c.execute(
        "SELECT user_id, username, name FROM players WHERE user_id = ?",
        (user_id,),
    )
    p = c.fetchone()
    if not p:
      try:
        await update.callback_query.message.reply_text("بازیکن پیدا نشد.")
      except Exception:
        pass
      return

    name = p[2]

    if season_filter == "all":
      query = """
                SELECT p.side, p.won, p.is_mvp, p.is_axe, p.is_unfair, p.is_artin, p.match_id, p.night1_shot, p.night1_out
                FROM match_participants p
                JOIN match_history m ON p.match_id = m.match_id
                WHERE p.player_name = ?
                ORDER BY p.match_id ASC
            """
      params = (name,)
      title_suffix = "کل تاریخچه لیگ (All-Time)"
      team_condition = ""
      team_params = (name, name)
      nem_condition = ""
      nem_params = (name,)
    else:
      s_int = int(season_filter)
      query = """
                SELECT p.side, p.won, p.is_mvp, p.is_axe, p.is_unfair, p.is_artin, p.match_id, p.night1_shot, p.night1_out
                FROM match_participants p
                JOIN match_history m ON p.match_id = m.match_id
                WHERE p.player_name = ? AND m.season = ?
                ORDER BY p.match_id ASC
            """
      params = (name, s_int)
      title_suffix = f"فصل {s_int}"
      team_condition = "AND m.season = ?"
      team_params = (name, name, s_int)
      nem_condition = "AND m.season = ?"
      nem_params = (name, s_int)

    c.execute(query, params)
    matches = c.fetchall()

    total_g = len(matches)
    wins = sum(1 for m in matches if m[1] == 1)
    losses = total_g - wins
    mvps = sum(1 for m in matches if m[2] == 1)
    axes = sum(1 for m in matches if m[3] == 1)
    unfairs = sum(1 for m in matches if m[4] == 1)
    artins = sum(1 for m in matches if m[5] == 1)
    n1_shots_cnt = sum(1 for m in matches if m[7] == 1)
    n1_outs_cnt = sum(1 for m in matches if m[8] == 1)

    if season_filter == "all":
      c.execute("""
            SELECT chaos_players, chaos_selected, chaos_win_impact 
            FROM match_history 
            WHERE end_mode = 'کی آس'
        """)
    else:
      c.execute("""
            SELECT chaos_players, chaos_selected, chaos_win_impact 
            FROM match_history 
            WHERE end_mode = 'کی آس' AND season = ?
        """, (int(season_filter),))
    
    ch_rows = c.fetchall()
    ch_count = 0
    ch_sel_count = 0
    ch_impact_count = 0

    for ch_p, ch_s, ch_i in ch_rows:
      if ch_p and name in ch_p.split(","):
        ch_count += 1
      if ch_s == name:
        ch_sel_count += 1
        if ch_i == "بله":
          ch_impact_count += 1

    raw = 0
    cur_streak = 0
    best_streak = 0

    for m in matches:
      won = m[1]
      mvp = m[2]
      axe = m[3]
      unfair = m[4]
      artin = m[5]
      
      game_pts = (10 if won else 0) + (4 if mvp else 0) + (-3 if axe else 0) + (-6 if unfair else 0) + (-8 if artin else 0)
      if won:
        cur_streak += 1
        if cur_streak >= 3:
          game_pts += 2
        best_streak = max(best_streak, cur_streak)
      else:
        cur_streak = 0
      raw += game_pts

    cit_games = sum(1 for m in matches if m[0] == "شهروند")
    cit_wins = sum(1 for m in matches if m[0] == "شهروند" and m[1] == 1)
    maf_games = sum(1 for m in matches if m[0] == "مافیا")
    maf_wins = sum(1 for m in matches if m[0] == "مافیا" and m[1] == 1)
    ind_games = sum(1 for m in matches if m[0] == "مستقل")
    ind_wins = sum(1 for m in matches if m[0] == "مستقل" and m[1] == 1)

    c.execute(
        f"""
            SELECT p2.player_name, COUNT(*), SUM(p2.won)
            FROM match_participants p1
            JOIN match_participants p2 ON p1.match_id = p2.match_id AND p1.side = p2.side
            JOIN match_history m ON p1.match_id = m.match_id
            WHERE p1.player_name = ? AND p2.player_name != ? {team_condition}
            GROUP BY p2.player_name
            ORDER BY SUM(p2.won) DESC LIMIT 1
        """,
        team_params,
    )
    best_teammate = c.fetchone()

    c.execute(
        f"""
            SELECT p2.player_name, COUNT(*)
            FROM match_participants p1
            JOIN match_participants p2 ON p1.match_id = p2.match_id AND p1.side != p2.side
            JOIN match_history m ON p1.match_id = m.match_id
            WHERE p1.player_name = ? AND p1.won = 0 {nem_condition}
            GROUP BY p2.player_name
            ORDER BY COUNT(*) DESC LIMIT 1
        """,
        nem_params,
    )
    nemesis = c.fetchone()

    earned_titles = []

    if season_filter == "all":
      c.execute("SELECT DISTINCT player_name FROM match_participants")
      all_p_names = [r[0] for r in c.fetchall()]
      ranking_data = []
      for p_n in all_p_names:
        c.execute("SELECT won, is_mvp, is_axe, is_unfair, is_artin FROM match_participants WHERE player_name = ?", (p_n,))
        p_matches = c.fetchall()
        p_g = len(p_matches)
        p_raw = sum((10 if m[0] == 1 else 0) + (4 if m[1] == 1 else 0) + (-3 if m[2] == 1 else 0) + (-6 if m[3] == 1 else 0) + (-8 if m[4] == 1 else 0) for m in p_matches)
        p_rate = calculate_rating(p_raw, p_g)
        p_wins = sum(1 for m in p_matches if m[0] == 1)
        ranking_data.append((p_n, p_rate, p_raw, p_wins))
      
      if ranking_data:
        ranking_data.sort(key=lambda x: (x[1], x[2], x[3]), reverse=True)
        if ranking_data[0][0] == name:
          earned_titles.append("🏛 **امپراطور لیگ**")

      c.execute("SELECT name FROM players WHERE total_games > 0 ORDER BY advanced_skill_score DESC LIMIT 1")
      top_adv = c.fetchone()
      if top_adv and top_adv[0] == name:
        earned_titles.append("🧠 **مغز متفکر**")

    else:
      s_int = int(season_filter)
      cur_season = get_current_season()
      if s_int == cur_season:
        c.execute("SELECT name, raw_score, total_games, wins FROM players WHERE total_games > 0")
        p_rows = c.fetchall()
        r_list = []
        for r in p_rows:
          rt = calculate_rating(r[1], r[2])
          r_list.append((r[0], rt, r[1], r[3]))
        if r_list:
          r_list.sort(key=lambda x: (x[1], x[2], x[3]), reverse=True)
          if r_list[0][0] == name:
            earned_titles.append("🏛 **امپراطور لیگ**")

        c.execute("SELECT name FROM players WHERE total_games > 0 ORDER BY advanced_skill_score DESC LIMIT 1")
        top_adv = c.fetchone()
        if top_adv and top_adv[0] == name:
          earned_titles.append("🧠 **مغز متفکر**")
      else:
        c.execute("SELECT player_name FROM season_archives WHERE season = ? ORDER BY final_rank ASC LIMIT 1", (s_int,))
        top_arch = c.fetchone()
        if top_arch and top_arch[0] == name:
          earned_titles.append("🏛 **امپراطور لیگ**")

        c.execute("SELECT player_name FROM season_archives WHERE season = ? AND total_games > 0 ORDER BY advanced_skill_score DESC LIMIT 1", (s_int,))
        top_adv_arch = c.fetchone()
        if top_adv_arch and top_adv_arch[0] == name:
          earned_titles.append("🧠 **مغز متفکر**")

    if season_filter == "all":
      c.execute("SELECT player_name FROM match_participants GROUP BY player_name ORDER BY SUM(is_mvp) DESC, COUNT(*) ASC LIMIT 1")
    else:
      c.execute("SELECT player_name FROM match_participants p JOIN match_history m ON p.match_id = m.match_id WHERE m.season = ? GROUP BY player_name ORDER BY SUM(is_mvp) DESC, COUNT(*) ASC LIMIT 1", (int(season_filter),))
    top_mvp = c.fetchone()
    if top_mvp and top_mvp[0] == name and mvps > 0:
      earned_titles.append("⚡ **ترس واقعی**")

    if season_filter == "all":
      c.execute("SELECT player_name FROM match_participants GROUP BY player_name ORDER BY SUM(is_axe) DESC, COUNT(*) ASC LIMIT 1")
    else:
      c.execute("SELECT player_name FROM match_participants p JOIN match_history m ON p.match_id = m.match_id WHERE m.season = ? GROUP BY player_name ORDER BY SUM(is_axe) DESC, COUNT(*) ASC LIMIT 1", (int(season_filter),))
    top_axe = c.fetchone()
    if top_axe and top_axe[0] == name and axes > 0:
      earned_titles.append("🐻 **خاله خرسه**")

    if season_filter == "all":
      c.execute("SELECT player_name FROM match_participants GROUP BY player_name ORDER BY SUM(is_unfair) DESC, COUNT(*) ASC LIMIT 1")
    else:
      c.execute("SELECT player_name FROM match_participants p JOIN match_history m ON p.match_id = m.match_id WHERE m.season = ? GROUP BY player_name ORDER BY SUM(is_unfair) DESC, COUNT(*) ASC LIMIT 1", (int(season_filter),))
    top_unfair = c.fetchone()
    if top_unfair and top_unfair[0] == name and unfairs > 0:
      earned_titles.append("🐍 **پیتون اعظم**")

    if season_filter == "all":
      c.execute("SELECT player_name FROM match_participants GROUP BY player_name ORDER BY SUM(is_artin) DESC, COUNT(*) ASC LIMIT 1")
    else:
      c.execute("SELECT player_name FROM match_participants p JOIN match_history m ON p.match_id = m.match_id WHERE m.season = ? GROUP BY player_name ORDER BY SUM(is_artin) DESC, COUNT(*) ASC LIMIT 1", (int(season_filter),))
    top_artin = c.fetchone()
    if top_artin and top_artin[0] == name and artins > 0:
      earned_titles.append("🐺 **کفتار تنها**")

    if season_filter == "all":
      c.execute("""
            SELECT p1.player_name, p2.player_name 
            FROM match_participants p1
            JOIN match_participants p2 ON p1.match_id = p2.match_id AND p1.side = p2.side
            WHERE p1.player_name < p2.player_name AND p1.won = 1 AND p2.won = 1
            GROUP BY p1.player_name, p2.player_name
            ORDER BY COUNT(*) DESC LIMIT 1
      """)
    else:
      c.execute("""
            SELECT p1.player_name, p2.player_name 
            FROM match_participants p1
            JOIN match_participants p2 ON p1.match_id = p2.match_id AND p1.side = p2.side
            JOIN match_history m ON p1.match_id = m.match_id
            WHERE p1.player_name < p2.player_name AND p1.won = 1 AND p2.won = 1 AND m.season = ?
            GROUP BY p1.player_name, p2.player_name
            ORDER BY COUNT(*) DESC LIMIT 1
      """, (int(season_filter),))
    top_pair = c.fetchone()
    if top_pair and name in top_pair:
      earned_titles.append("🤝 **اتحاد آهنین**")

    if season_filter == "all":
      c.execute("SELECT p.player_name, p.won, m.created_at FROM match_participants p JOIN match_history m ON p.match_id = m.match_id ORDER BY p.player_name ASC, m.created_at ASC, p.match_id ASC")
      all_recs = c.fetchall()
      p_streaks = {}
      for p_n, w_val, _ in all_recs:
        if p_n not in p_streaks:
          p_streaks[p_n] = {"best": 0, "curr": 0, "wins": 0}
        p_streaks[p_n]["wins"] += (1 if w_val == 1 else 0)
        if w_val == 1:
          p_streaks[p_n]["curr"] += 1
          if p_streaks[p_n]["curr"] > p_streaks[p_n]["best"]:
            p_streaks[p_n]["best"] = p_streaks[p_n]["curr"]
        else:
          p_streaks[p_n]["curr"] = 0
      sorted_str = sorted(p_streaks.items(), key=lambda x: (x[1]["best"], x[1]["wins"]), reverse=True)
      if sorted_str and sorted_str[0][0] == name and sorted_str[0][1]["best"] > 0:
        earned_titles.append("⚔️ **ماشین کشتار**")
    else:
      s_int = int(season_filter)
      cur_season = get_current_season()
      if s_int == cur_season:
        c.execute("SELECT name FROM players WHERE best_streak > 0 ORDER BY best_streak DESC, wins DESC LIMIT 1")
        top_strk = c.fetchone()
        if top_strk and top_strk[0] == name and best_streak > 0:
          earned_titles.append("⚔️ **ماشین کشتار**")
      else:
        c.execute("SELECT p.player_name, p.won, m.created_at FROM match_participants p JOIN match_history m ON p.match_id = m.match_id WHERE m.season = ? ORDER BY p.player_name ASC, m.created_at ASC, p.match_id ASC", (s_int,))
        s_recs = c.fetchall()
        s_streaks = {}
        for p_n, w_val, _ in s_recs:
          if p_n not in s_streaks:
            s_streaks[p_n] = {"best": 0, "curr": 0, "wins": 0}
          s_streaks[p_n]["wins"] += (1 if w_val == 1 else 0)
          if w_val == 1:
            s_streaks[p_n]["curr"] += 1
            if s_streaks[p_n]["curr"] > s_streaks[p_n]["best"]:
              s_streaks[p_n]["best"] = s_streaks[p_n]["curr"]
          else:
            s_streaks[p_n]["curr"] = 0
        sorted_s = sorted(s_streaks.items(), key=lambda x: (x[1]["best"], x[1]["wins"]), reverse=True)
        if sorted_s and sorted_s[0][0] == name and sorted_s[0][1]["best"] > 0:
          earned_titles.append("⚔️ **ماشین کشتار**")

    if season_filter == "all":
      c.execute("SELECT player_name FROM match_participants GROUP BY player_name ORDER BY SUM(night1_shot) DESC LIMIT 1")
    else:
      c.execute("SELECT player_name FROM match_participants p JOIN match_history m ON p.match_id = m.match_id WHERE m.season = ? GROUP BY player_name ORDER BY SUM(night1_shot) DESC LIMIT 1", (int(season_filter),))
    top_shot = c.fetchone()
    if top_shot and top_shot[0] == name and n1_shots_cnt > 0:
      earned_titles.append("🎯 **کابوس مافیا**")

  rating = calculate_rating(raw, total_g)
  win_rate = round((wins / total_g * 100), 1) if total_g > 0 else 0
  cit_rate = round((cit_wins / cit_games * 100), 1) if cit_games > 0 else 0
  maf_rate = round((maf_wins / maf_games * 100), 1) if maf_games > 0 else 0
  ind_rate = round((ind_wins / ind_games * 100), 1) if ind_games > 0 else 0

  tm_text = (
      f"{best_teammate[0]} ({best_teammate[2]} برد مشترک)"
      if best_teammate
      else "ثبت نشده"
  )
  nem_text = f"{nemesis[0]} ({nemesis[1]} باخت مقابلش)" if nemesis else "ثبت نشده"

  titles_str = "\n".join([f"▫️ {t}" for t in earned_titles]) if earned_titles else "▫️ فعلاً عنوانی در این بازه ثبت نشده است."

  text = (
      f"👤 **پروفایل عملکرد: {name}**\n"
      f"📅 **بازه گزارش:** `{title_suffix}`\n"
      f"────────────────────────\n"
      f"⭐ **ریتینگ عملکرد:** `{rating}`\n"
      f"📊 **مجموع امتیاز خام:** `{raw}`\n"
      f"🎮 **بازی‌ها:** `{total_g}` (برد: `{wins}` | باخت: `{losses}` | نرخ برد: `{win_rate}%`)\n"
      f"────────────────────────\n"
      f"👑 **القاب و عناوین کسب‌شده در این بازه:**\n"
      f"{titles_str}\n"
      f"────────────────────────\n"
      f"🌟 **بست‌پلیر (MVP):** `{mvps}` بار\n"
      f"🪓 **تبر:** `{axes}` بار\n"
      f"🐍 **آنفیر:** `{unfairs}` بار\n"
      f"👑 **آرتین:** `{artins}` بار\n"
      f"🌪 **حضور در کِی‌آس:** `{ch_count}` بار\n"
      f"🎯 **فرد منتخب کِی‌آس:** `{ch_sel_count}` بار\n"
      f"💡 **تاثیر در برد کِی‌آس:** `{ch_impact_count}` بار\n"
      f"🎯 **شات شب اول:** `{n1_shots_cnt}` بار\n"
      f"🚪 **خروج شب اول:** `{n1_outs_cnt}` بار\n"
      f"🔥 **استریک:** فعلی: `{cur_streak}` | رکورد: `{best_streak}`\n"
      f"────────────────────────\n"
      f"🎭 **تخصص سایدها:**\n"
      f"▫️ شهروند: `{cit_games}` بازی (برد: `{cit_rate}%`)\n"
      f"▫️ مافیا: `{maf_games}` بازی (برد: `{maf_rate}%`)\n"
      f"▫️ مستقل: `{ind_games}` بازی (برد: `{ind_rate}%`)\n"
      f"────────────────────────\n"
      f"🤝 **بهترین هم‌تیمی:** {tm_text}\n"
      f"⚔️ **بدترین رقیب:** {nem_text}"
  )

  keyboard = [
      [
          InlineKeyboardButton(
              "📈 رسم نمودار همین بازه",
              callback_data=f"view_chart_target:{user_id}:{season_filter}:rating",
          )
      ],
      [
          InlineKeyboardButton(
              "🔄 تغییر فصل / بازه",
              callback_data=f"ask_stat_season:{user_id}",
          )
      ],
      [
          InlineKeyboardButton(
              "🔙 بازگشت به منوی آمار", callback_data="open_stats_hub"
          )
      ],
  ]
  try:
    await update.callback_query.message.reply_text(
        text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown"
    )
  except Exception:
    pass


async def render_and_send_chart_filtered(
    update: Update, user_id: int, season_filter: str, chart_type: str = "rating"
):
  with sqlite3.connect("mafia_league.db") as conn:
    c = conn.cursor()
    c.execute("SELECT name FROM players WHERE user_id = ?", (user_id,))
    p = c.fetchone()
    if not p:
      try:
        await update.callback_query.answer("بازیکن یافت نشد.", show_alert=True)
      except Exception:
        pass
      return
    name = p[0]

    if season_filter == "all":
      query = """
                SELECT p.match_id, p.won, p.is_mvp, p.is_axe, p.is_unfair, p.is_artin, m.season 
                FROM match_participants p
                JOIN match_history m ON p.match_id = m.match_id
                WHERE p.player_name = ?
                ORDER BY p.match_id ASC
            """
      params = (name,)
      range_desc = "کل تاریخچه بازی‌ها"
    else:
      s_int = int(season_filter)
      query = """
                SELECT p.match_id, p.won, p.is_mvp, p.is_axe, p.is_unfair, p.is_artin, m.season 
                FROM match_participants p
                JOIN match_history m ON p.match_id = m.match_id
                WHERE p.player_name = ? AND m.season = ?
                ORDER BY p.match_id ASC
            """
      params = (name, s_int)
      range_desc = f"فصل {s_int}"

    c.execute(query, params)
    rows = c.fetchall()

  if not rows or len(rows) < 2:
    msg = (
        f"برای رسم نمودار «{name}» در {range_desc}، باید حداقل ۲ بازی ثبت شده"
        " باشد."
    )
    try:
      await update.callback_query.answer(msg, show_alert=True)
    except Exception:
      pass
    return

  values_list = []
  
  if chart_type == "adv":
    title_label = f"{name} (Advanced Skill - {range_desc})"
    y_label = "Advanced Skill Score"
    line_color = "#2ca02c"
    line_label = "Skill Score"
    
    current_adv = 1000.0
    for r in rows:
      m_id = r[0]
      won = r[1]
      mvp = r[2]
      axe = r[3]
      unfair = r[4]
      artin = r[5]
      m_season = r[6]
      
      with sqlite3.connect("mafia_league.db") as conn2:
        c2 = conn2.cursor()
        c2.execute("SELECT player_name, won, is_mvp, is_axe, is_unfair, is_artin FROM match_participants WHERE match_id = ?", (m_id,))
        parts = c2.fetchall()
        winners = [pt[0] for pt in parts if pt[1] == 1]
        losers = [pt[0] for pt in parts if pt[0] == 0]
        
        # تخمین دینامیک فاکتور مهارت حریفان
        if winners and losers:
          base_d = (10.0 if won == 1 else -8.0)
          b_mvp = (4.0 if mvp else 0.0)
          p_axe = (-3.0 if axe else 0.0)
          p_unf = (-6.0 if unfair else 0.0)
          p_art = (-8.0 if artin else 0.0)
          current_adv += (base_d + b_mvp + p_axe + p_unf + p_art)
      values_list.append(round(current_adv, 2))
  else:
    title_label = f"{name} (Smart Rating - {range_desc})"
    y_label = "Rating"
    line_color = "#1f77b4"
    line_label = "Rating"
    
    running_raw = 0
    running_games = 0
    temp_streak = 0
    for r in rows:
      won = r[1]
      mvp = r[2]
      axe = r[3]
      unfair = r[4]
      artin = r[5]
      
      game_pts = (10 if won else 0) + (4 if mvp else 0) + (-3 if axe else 0) + (-6 if unfair else 0) + (-8 if artin else 0)
      if won:
        temp_streak += 1
        if temp_streak >= 3:
          game_pts += 2
      else:
        temp_streak = 0

      running_raw += game_pts
      running_games += 1
      
      cur_rating = calculate_rating(running_raw, running_games)
      values_list.append(cur_rating)

  matches_count = list(range(1, len(values_list) + 1))

  fig, ax1 = plt.subplots(figsize=(8.5, 4.5), dpi=120)

  ax1.set_xlabel("Matches Played", fontsize=11, fontweight="bold")
  ax1.set_ylabel(y_label, color=line_color, fontsize=11, fontweight="bold")
  ax1.plot(
      matches_count,
      values_list,
      color=line_color,
      marker="o",
      linewidth=2.5,
      label=line_label,
  )
  ax1.tick_params(axis="y", labelcolor=line_color)
  ax1.grid(True, linestyle="--", alpha=0.4)

  ax1.legend(loc="upper left", framealpha=0.85)

  plt.title(
      f"Performance Trend: {title_label}",
      fontsize=12,
      fontweight="bold",
      pad=12,
  )

  buf = io.BytesIO()
  plt.savefig(buf, format="png", bbox_inches="tight")
  buf.seek(0)
  plt.close()

  desc_line = "🔵 **خط آبی:** روند نوسان ریتینگ هوشمند" if chart_type == "rating" else "🟢 **خط سبز:** روند امتیاز مهارت و ارزش برد پیشرفته"
  caption = (
      f"📈 **نمودار پیشرفت و رشد {name}**\n"
      f"🗓 **بازه:** `{range_desc}`\n\n"
      f"{desc_line}"
  )
  keyboard = [
      [
          InlineKeyboardButton(
              "🔄 تغییر نوع یا فصل نمودار", callback_data=f"ask_chart_season:{user_id}"
          )
      ],
      [
          InlineKeyboardButton(
              "🔙 بازگشت به منوی آمار", callback_data="open_stats_hub"
          )
      ],
  ]
  reply_markup = InlineKeyboardMarkup(keyboard)

  try:
    await update.callback_query.message.reply_photo(
        photo=buf,
        caption=caption,
        reply_markup=reply_markup,
        parse_mode="Markdown",
    )
  except Exception:
    pass


async def chart(update: Update, context: ContextTypes.DEFAULT_TYPE):
  if not await enforce_channel_lock(update, context, check_lock=True):
    return
  await show_chart_picker(update, context)


async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
  if not await enforce_channel_lock(update, context, check_lock=True):
    return
  await show_stats_picker(update, context)


async def sides(update: Update, context: ContextTypes.DEFAULT_TYPE):
  if not await enforce_channel_lock(update, context, check_lock=False):
    return
  cur_season = get_current_season()
  with sqlite3.connect("mafia_league.db") as conn:
    c = conn.cursor()
    c.execute(
        "SELECT winning_side, COUNT(*) FROM match_history WHERE season = ?"
        " GROUP BY winning_side",
        (cur_season,),
    )
    rows = c.fetchall()

  if not rows:
    await update.message.reply_text(
        f"هنوز هیچ مسابقه‌ای در فصل {cur_season} ثبت نشده است."
    )
    return

  total = sum(r[1] for r in rows)
  text = f"⚖️ **آمار پیروزی سایدها در فصل {cur_season}** (کل بازی‌ها: {total})\n\n"
  for side, count in rows:
    pct = round((count / total) * 100, 1)
    text += f"▫️ {side}: `{count}` برد ({pct}%)\n"

  await update.message.reply_text(text, parse_mode="Markdown")


async def scenarios_stat(update: Update, context: ContextTypes.DEFAULT_TYPE):
  if not await enforce_channel_lock(update, context, check_lock=False):
    return
  cur_season = get_current_season()
  try:
    with sqlite3.connect("mafia_league.db") as conn:
      c = conn.cursor()
      c.execute(
          "SELECT scenario_name, COUNT(*) FROM match_history WHERE"
          " scenario_name IS NOT NULL AND season = ? GROUP BY scenario_name"
          " ORDER BY COUNT(*) DESC",
          (cur_season,),
      )
      rows = c.fetchall()

    if not rows:
      await update.message.reply_text(
          f"🎬 هنوز مسابقه‌ای با سناریوها در فصل {cur_season} ثبت نشده است."
      )
      return

    total = sum(r[1] for r in rows)
    text = (
        f"🎬 **آمار تعداد دفعات اجرای سناریوها در فصل {cur_season}** (کل بازی‌ها:"
        f" {total})\n\n"
    )
    for scen, count in rows:
      pct = round((count / total) * 100, 1)
      text += f"▫️ سناریو **{scen}**: `{count}` بار ({pct}%)\n"

    await update.message.reply_text(text, parse_mode="Markdown")
  except Exception:
    await update.message.reply_text(
        "🎬 هنوز بازی‌ای برای نمایش آمار سناریوها وجود ندارد."
    )


async def submit_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
  if update.effective_user.id not in [ADMIN_ID, ADMIN_ID_2]:
    if update.message:
      await update.message.reply_text(
          "⛔️ فقط ادمین لیگ اجازه ثبت مسابقات را دارد."
      )
    elif update.callback_query:
      try:
        await update.callback_query.answer("⛔️ فقط ادمین اجازه دارد.", show_alert=True)
      except Exception:
        pass
    return

  all_players = get_all_player_names()
  if len(all_players) < 4:
    msg = "❌ برای ثبت مسابقه، حداقل باید ۴ بازیکن عضو لیگ شده باشند."
    if update.message:
      await update.message.reply_text(msg)
    elif update.callback_query:
      try:
        await update.callback_query.message.reply_text(msg)
      except Exception:
        pass
    return

  context.user_data["game_flow"] = {
      "scenario": None,
      "has_independent": False,
      "winner_side": None,
      "end_mode": None,
      "chaos_players": [],
      "chaos_selected": None,
      "chaos_win_impact": None,
      "citizens": [],
      "mafias": [],
      "independents": [],
      "night1_shot": None,
      "night1_out": False,
      "mvps": [],
      "axes": [],
      "unfairs": [],
      "artins": [],
  }

  keyboard = []
  row = []
  for s_name in SCENARIO_LIST:
    row.append(
        InlineKeyboardButton(f"🎬 {s_name}", callback_data=f"scen_pick:{s_name}")
    )
    if len(row) == 2:
      keyboard.append(row)
      row = []
  if row:
    keyboard.append(row)

  cur_season = get_current_season()
  prompt = f"🎬 **مرحله ۱:** سناریوی بازی را انتخاب کنید (فصل {cur_season}):"
  if update.message:
    await update.message.reply_text(
        prompt, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown"
    )
  elif update.callback_query:
    try:
      await update.callback_query.message.reply_text(
          prompt, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown"
      )
    except Exception:
      pass


async def game_flow_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
  query = update.callback_query
  try:
    await query.answer()
  except Exception:
    pass

  data = query.data

  if data == "open_community_links":
    if not await enforce_channel_lock(update, context, check_lock=False):
      return
    await show_links_menu(update, context)
    return

  if data == "open_rules_menu":
    if not await enforce_channel_lock(update, context, check_lock=False):
      return
    await show_rules_menu(update, context)
    return

  if data.startswith("rule_sec:"):
    sec_n = data.split(":", 1)[1]
    await show_rule_detail(update, sec_n)
    return

  if data == "open_stats_hub":
    if not await enforce_channel_lock(update, context, check_lock=True):
      return
    await show_stats_hub(update, context)
    return

  if data == "ask_advanced_season":
    if not await enforce_channel_lock(update, context, check_lock=True):
      return
    await ask_advanced_season_choice(update)
    return

  if data.startswith("adv_table_page:"):
    if not await enforce_channel_lock(update, context, check_lock=True):
      return
    parts = data.split(":")
    s_filt = parts[1]
    p_num = int(parts[2])
    await render_advanced_table_page(update, s_filt, p_num)
    return

  if data == "ask_teammates_season":
    if not await enforce_channel_lock(update, context, check_lock=True):
      return
    await ask_teammates_season_choice(update)
    return

  if data.startswith("teammates_page:"):
    if not await enforce_channel_lock(update, context, check_lock=True):
      return
    parts = data.split(":")
    s_filt = parts[1]
    p_num = int(parts[2])
    await render_teammates_leaderboard_filtered(update, s_filt, p_num)
    return

  if data == "ask_streaks_season":
    if not await enforce_channel_lock(update, context, check_lock=True):
      return
    await ask_streaks_season_choice(update)
    return

  if data.startswith("streaks_page:"):
    if not await enforce_channel_lock(update, context, check_lock=True):
      return
    parts = data.split(":")
    s_filt = parts[1]
    p_num = int(parts[2])
    await render_streaks_leaderboard_filtered(update, s_filt, p_num)
    return

  if data == "show_shots_lb":
    if not await enforce_channel_lock(update, context, check_lock=True):
      return
    await ask_shots_season_choice(update, context)
    return

  if data.startswith("shots_page:"):
    if not await enforce_channel_lock(update, context, check_lock=True):
      return
    s_filt = data.split(":", 1)[1]
    await render_shots_leaderboard_filtered(update, s_filt)
    return

  if data == "show_admin_analytics":
    await show_analytics_report(update)
    return

  if data == "show_scoring_info":
    if not await enforce_channel_lock(update, context, check_lock=True):
      return
    await scoring_guide(update, context)
    return

  if data == "ask_table_season":
    if not await enforce_channel_lock(update, context, check_lock=True):
      return
    await ask_table_season_choice(update)
    return
  if data.startswith("table_page:"):
    if not await enforce_channel_lock(update, context, check_lock=True):
      return
    parts = data.split(":")
    s_filt = parts[1]
    p_num = int(parts[2])
    await render_table_page_filtered(update, s_filt, p_num)
    return

  if data == "ask_bests_season":
    if not await enforce_channel_lock(update, context, check_lock=True):
      return
    await ask_bests_season_choice(update)
    return
  if data.startswith("bests_page:"):
    if not await enforce_channel_lock(update, context, check_lock=True):
      return
    parts = data.split(":")
    s_filt = parts[1]
    p_num = int(parts[2])
    await render_bests_page_filtered(update, s_filt, p_num)
    return

  if data == "ask_axes_season":
    if not await enforce_channel_lock(update, context, check_lock=True):
      return
    await ask_axes_season_choice(update)
    return
  if data.startswith("axes_page:"):
    if not await enforce_channel_lock(update, context, check_lock=True):
      return
    parts = data.split(":")
    s_filt = parts[1]
    p_num = int(parts[2])
    await render_axes_page_filtered(update, s_filt, p_num)
    return

  if data == "ask_unfair_season":
    if not await enforce_channel_lock(update, context, check_lock=True):
      return
    await ask_unfair_season_choice(update)
    return
  if data.startswith("unfair_page:"):
    if not await enforce_channel_lock(update, context, check_lock=True):
      return
    parts = data.split(":")
    s_filt = parts[1]
    p_num = int(parts[2])
    await render_unfair_page_filtered(update, s_filt, p_num)
    return

  if data == "ask_artin_season":
    if not await enforce_channel_lock(update, context, check_lock=True):
      return
    await ask_artin_season_choice(update)
    return
  if data.startswith("artin_page:"):
    if not await enforce_channel_lock(update, context, check_lock=True):
      return
    parts = data.split(":")
    s_filt = parts[1]
    p_num = int(parts[2])
    await render_artin_page_filtered(update, s_filt, p_num)
    return

  if data == "ask_vs_season":
    if not await enforce_channel_lock(update, context, check_lock=True):
      return
    await ask_vs_season_choice(update)
    return
  if data.startswith("open_vs_picker_1:"):
    if not await enforce_channel_lock(update, context, check_lock=True):
      return
    s_filt = data.split(":", 1)[1]
    await show_vs_picker_first(update, context, s_filt)
    return
  if data.startswith("vs_p1:"):
    if not await enforce_channel_lock(update, context, check_lock=True):
      return
    _, s_filt, uid1 = data.split(":")
    await show_vs_picker_second(update, context, s_filt, int(uid1))
    return
  if data.startswith("vs_p2:"):
    if not await enforce_channel_lock(update, context, check_lock=True):
      return
    _, s_filt, uid1, uid2 = data.split(":")
    await render_vs_comparison_filtered(update, s_filt, int(uid1), int(uid2))
    return

  if data == "confirm_finish_season_prompt":
    await prompt_finish_season(update)
    return
  if data == "do_finish_season_action":
    await execute_finish_season(update, context)
    return

  if data.startswith("pub_history_page:"):
    if not await enforce_channel_lock(update, context, check_lock=False):
      return
    p_num = int(data.split(":", 1)[1])
    await render_public_history_page(update, p_num)
    return
  if data.startswith("pub_match_view:"):
    if not await enforce_channel_lock(update, context, check_lock=False):
      return
    parts = data.split(":")
    m_id = int(parts[1])
    b_page = int(parts[2]) if len(parts) > 2 else 1
    await show_public_match_details(update, m_id, b_page)
    return

  if data == "show_players_info":
    await render_players_list_page(update, context, 1)
    return
  if data.startswith("players_page:"):
    p_num = int(data.split(":", 1)[1])
    await render_players_list_page(update, context, p_num)
    return

  if data == "open_stats_picker":
    if not await enforce_channel_lock(update, context, check_lock=True):
      return
    await show_stats_picker(update, context)
    return

  if data.startswith("ask_stat_season:"):
    if not await enforce_channel_lock(update, context, check_lock=True):
      return
    u_id = int(data.split(":", 1)[1])
    await ask_stat_season_choice(update, u_id)
    return
  if data.startswith("view_stat_target:"):
    if not await enforce_channel_lock(update, context, check_lock=True):
      return
    _, u_id, s_filt = data.split(":")
    await render_player_stats(update, int(u_id), s_filt)
    return

  if data == "open_chart_picker":
    if not await enforce_channel_lock(update, context, check_lock=True):
      return
    await show_chart_picker(update, context)
    return
  if data.startswith("ask_chart_season:"):
    if not await enforce_channel_lock(update, context, check_lock=True):
      return
    u_id = int(data.split(":", 1)[1])
    await ask_chart_season_choice(update, u_id)
    return
  if data.startswith("view_chart_target:"):
    if not await enforce_channel_lock(update, context, check_lock=True):
      return
    parts = data.split(":")
    u_id = int(parts[1])
    s_filt = parts[2]
    c_type = parts[3] if len(parts) > 3 else "rating"
    await render_and_send_chart_filtered(update, u_id, s_filt, c_type)
    return

  if data == "open_admin_panel":
    await admin_panel(update, context)
    return
  if data == "open_matches_list":
    await show_matches_list(update, context)
    return
  if data.startswith("detail_match:"):
    m_id = int(data.split(":", 1)[1])
    await show_match_details(update, m_id)
    return
  if data.startswith("del_match_confirm:"):
    m_id = int(data.split(":", 1)[1])
    await delete_match_by_id(update, m_id)
    return

  if data == "open_merge_picker_old":
    await show_merge_picker_old(update, context)
    return
  if data.startswith("sel_mrg_old:"):
    old_uid = int(data.split(":", 1)[1])
    await show_merge_picker_new(update, context, old_uid)
    return
  if data.startswith("do_merge_final:"):
    _, old_uid, new_uid = data.split(":")
    await execute_final_merge(update, int(old_uid), int(new_uid))
    return

  if data == "admin_btn_add":
    context.user_data["waiting_for_manual_add"] = True
    try:
      await query.message.reply_text(
          "➕ لطفاً **نام بازیکن قدیمی** را ارسال کنید تا دستی به لیگ اضافه شود:"
      )
    except Exception:
      pass
    return
  if data == "admin_btn_remove_list":
    await show_remove_player_buttons(update, context)
    return
  if data.startswith("del_id:"):
    u_id = int(data.split(":", 1)[1])
    await apply_remove_player_by_id(update, u_id)
    return
  if data == "admin_btn_submit":
    await submit_game(update, context)
    return
  if data == "back_to_start":
    await send_takamol_menu(update, context)
    return

  if data == "btn_join_league":
    if not await enforce_channel_lock(update, context, check_lock=False):
      return
    await process_join_user(query.from_user, context, alert_func=query.answer)
    return

  flow = context.user_data.get("game_flow")
  if flow is not None:
    if data.startswith("scen_pick:"):
      scen = data.split(":", 1)[1]
      flow["scenario"] = scen
      
      keyboard = [
          [
              InlineKeyboardButton("✅ بله، ساید مستقل دارد", callback_data="indep_yes"),
              InlineKeyboardButton("❌ خیر، ندارد", callback_data="indep_no")
          ]
      ]
      try:
        await query.edit_message_text(
            f"🎬 سناریو: **{scen}**\n\n🃏 **مرحله ۲:** آیا این بازی ساید مستقل دارد؟",
            reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown"
        )
      except Exception:
        pass
      return

    elif data in ["indep_yes", "indep_no"]:
      flow["has_independent"] = (data == "indep_yes")
      
      sides_list = [
          [InlineKeyboardButton("🏙 شهروند", callback_data="win_side:شهروند")],
          [InlineKeyboardButton("🔪 مافیا", callback_data="win_side:مافیا")]
      ]
      if flow["has_independent"]:
        sides_list.append([InlineKeyboardButton("🃏 مستقل", callback_data="win_side:مستقل")])
      
      try:
        await query.edit_message_text(
            "🏆 **مرحله ۳:** ساید برنده مسابقه را انتخاب کنید:",
            reply_markup=InlineKeyboardMarkup(sides_list), parse_mode="Markdown"
        )
      except Exception:
        pass
      return

    elif data.startswith("win_side:"):
      w_side = data.split(":", 1)[1]
      flow["winner_side"] = w_side
      
      end_modes = [
          [InlineKeyboardButton("🛡 کلین شیت", callback_data="end_mode:کلین شیت")],
          [InlineKeyboardButton("📈 روند عادی", callback_data="end_mode:روند عادی")],
          [InlineKeyboardButton("🌪 کِی‌آس (Chaos)", callback_data="end_mode:کی آس")]
      ]
      try:
        await query.edit_message_text(
            f"🏆 ساید برنده: **{w_side}**\n\n🏁 **مرحله ۴:** بازی در چه حالتی به پایان یافت؟",
            reply_markup=InlineKeyboardMarkup(end_modes), parse_mode="Markdown"
        )
      except Exception:
        pass
      return

    elif data.startswith("end_mode:"):
      e_mode = data.split(":", 1)[1]
      flow["end_mode"] = e_mode

      if e_mode == "کی آس":
        await prompt_chaos_player_selection(query, flow)
      else:
        await prompt_multiselect_citizens(query, flow)
      return

    elif data.startswith("chaos_pick:"):
      p_name = data.split(":", 1)[1]
      if p_name not in flow["chaos_players"]:
        flow["chaos_players"].append(p_name)
      
      if len(flow["chaos_players"]) < 3:
        await prompt_chaos_player_selection(query, flow)
      else:
        await prompt_chaos_selected_player(query, flow)
      return

    elif data.startswith("chaos_select_one:"):
      selected_p = data.split(":", 1)[1]
      flow["chaos_selected"] = selected_p

      keyboard = [
          [
              InlineKeyboardButton("✅ بله", callback_data="chaos_impact:بله"),
              InlineKeyboardButton("❌ خیر", callback_data="chaos_impact:خیر")
          ]
      ]
      try:
        await query.edit_message_text(
            f"🎯 فرد منتخب بین ۳ نفر: **{selected_p}**\n\n"
            f"💡 آیا عملکرد این فرد باعث برد سایدش شد؟",
            reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown"
        )
      except Exception:
        pass
      return

    elif data.startswith("chaos_impact:"):
      impact = data.split(":", 1)[1]
      flow["chaos_win_impact"] = impact

      await prompt_multiselect_citizens(query, flow)
      return

    elif data.startswith("m_cit_toggle:"):
      p_name = data.split(":", 1)[1]
      if "temp_citizens" not in flow:
        flow["temp_citizens"] = []
      if p_name in flow["temp_citizens"]:
        flow["temp_citizens"].remove(p_name)
      else:
        flow["temp_citizens"].append(p_name)
      await refresh_multiselect_citizens(query, flow)
      return

    elif data == "m_cit_done":
      selected = flow.get("temp_citizens", [])
      if not selected:
        try:
          await query.answer("❌ حداقل یک شهروند باید انتخاب شود.", show_alert=True)
        except Exception:
          pass
        return
      flow["citizens"] = selected
      flow.pop("temp_citizens", None)
      await prompt_multiselect_mafias(query, flow)
      return

    elif data.startswith("m_maf_toggle:"):
      p_name = data.split(":", 1)[1]
      if "temp_mafias" not in flow:
        flow["temp_mafias"] = []
      if p_name in flow["temp_mafias"]:
        flow["temp_mafias"].remove(p_name)
      else:
        flow["temp_mafias"].append(p_name)
      await refresh_multiselect_mafias(query, flow)
      return

    elif data == "m_maf_done":
      selected = flow.get("temp_mafias", [])
      if not selected:
        try:
          await query.answer("❌ حداقل یک مافیا باید انتخاب شود.", show_alert=True)
        except Exception:
          pass
        return
      flow["mafias"] = selected
      flow.pop("temp_mafias", None)

      if flow["has_independent"]:
        await prompt_multiselect_independents(query, flow)
      else:
        await prompt_night1_shot(query, flow)
      return

    elif data.startswith("m_ind_toggle:"):
      p_name = data.split(":", 1)[1]
      if "temp_independents" not in flow:
        flow["temp_independents"] = []
      if p_name in flow["temp_independents"]:
        flow["temp_independents"].remove(p_name)
      else:
        flow["temp_independents"].append(p_name)
      await refresh_multiselect_independents(query, flow)
      return

    elif data == "m_ind_done":
      selected = flow.get("temp_independents", [])
      flow["independents"] = selected
      flow.pop("temp_independents", None)
      await prompt_night1_shot(query, flow)
      return

    elif data.startswith("n1_shot_pick:"):
      shot_target = data.split(":", 1)[1]
      flow["night1_shot"] = shot_target
      
      if shot_target == "none":
        flow["night1_out"] = False
        await prompt_mvp_selection(query, flow)
      else:
        keyboard = [
            [
                InlineKeyboardButton("✅ بله، خارج شد", callback_data="n1_out:yes"),
                InlineKeyboardButton("❌ خیر، نرفت/ماند", callback_data="n1_out:no")
            ]
        ]
        try:
          await query.edit_message_text(
              f"🎯 شات شب اول مافیا روی: **{shot_target}** ثبت شد.\n\n"
              f"🚪 آیا این فرد در شب اول خارج شد؟",
              reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown"
          )
        except Exception:
          pass
      return

    elif data.startswith("n1_out:"):
      out_status = data.split(":", 1)[1]
      flow["night1_out"] = (out_status == "yes")
      await prompt_mvp_selection(query, flow)
      return

    elif data.startswith("mvp_pick:"):
      p_name = data.split(":", 1)[1]
      if p_name in flow["mvps"]:
        flow["mvps"].remove(p_name)
      else:
        flow["mvps"].append(p_name)
      
      await refresh_mvp_keyboard(query, flow)
      return

    elif data == "done_mvps":
      await prompt_axe_selection(query, flow)
      return

    elif data.startswith("axe_pick:"):
      p_name = data.split(":", 1)[1]
      if p_name in flow["axes"]:
        flow["axes"].remove(p_name)
      else:
        flow["axes"].append(p_name)
      
      await refresh_axe_keyboard(query, flow)
      return

    elif data == "done_axes":
      await prompt_unfair_selection(query, flow)
      return

    elif data.startswith("unfair_pick:"):
      p_name = data.split(":", 1)[1]
      if p_name in flow["unfairs"]:
        flow["unfairs"].remove(p_name)
      else:
        flow["unfairs"].append(p_name)
      
      await refresh_unfair_keyboard(query, flow)
      return

    elif data == "done_unfairs":
      await prompt_artin_selection(query, flow)
      return

    elif data.startswith("artin_pick:"):
      p_name = data.split(":", 1)[1]
      if p_name in flow["artins"]:
        flow["artins"].remove(p_name)
      else:
        flow["artins"].append(p_name)
      
      await refresh_artin_keyboard(query, flow)
      return

    elif data == "done_artins":
      await finalize_and_save_game(query, flow, context)
      return


async def prompt_multiselect_citizens(query, flow):
  all_p = get_all_player_names()
  if "temp_citizens" not in flow:
    flow["temp_citizens"] = []
  
  keyboard = []
  row = []
  for p in all_p:
    is_selected = p in flow["temp_citizens"]
    mark = "✅ " if is_selected else ""
    row.append(InlineKeyboardButton(f"{mark}{p}", callback_data=f"m_cit_toggle:{p}"))
    if len(row) == 2:
      keyboard.append(row)
      row = []
  if row:
    keyboard.append(row)
  
  keyboard.append([InlineKeyboardButton("✅ اتمام انتخاب شهروندان", callback_data="m_cit_done")])

  try:
    await query.edit_message_text(
        "🏙 **انتخاب ساید شهروند:**\nروی نام هر بازیکن کلیک کنید تا تیک بخورد، سپس دکمه اتمام را بزنید:",
        reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown"
    )
  except Exception:
    pass


async def refresh_multiselect_citizens(query, flow):
  all_p = get_all_player_names()
  selected = flow.get("temp_citizens", [])
  
  keyboard = []
  row = []
  for p in all_p:
    is_selected = p in selected
    mark = "✅ " if is_selected else ""
    row.append(InlineKeyboardButton(f"{mark}{p}", callback_data=f"m_cit_toggle:{p}"))
    if len(row) == 2:
      keyboard.append(row)
      row = []
  if row:
    keyboard.append(row)
  
  keyboard.append([InlineKeyboardButton("✅ اتمام انتخاب شهروندان", callback_data="m_cit_done")])

  selected_str = ", ".join(selected) if selected else "هیچ‌کس انتخاب نشده"
  try:
    await query.edit_message_text(
        f"🏙 شهروندان تیک‌خورده: `{selected_str}`\n\nبرای تغییر انتخاب‌ها دکمه‌ها را لمس کنید:",
        reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown"
    )
  except Exception:
    pass


async def prompt_multiselect_mafias(query, flow):
  all_p = get_all_player_names()
  already_chosen = flow.get("citizens", [])
  if "temp_mafias" not in flow:
    flow["temp_mafias"] = []
  
  keyboard = []
  row = []
  for p in all_p:
    if p in already_chosen:
      continue
    is_selected = p in flow["temp_mafias"]
    mark = "✅ " if is_selected else ""
    row.append(InlineKeyboardButton(f"{mark}{p}", callback_data=f"m_maf_toggle:{p}"))
    if len(row) == 2:
      keyboard.append(row)
      row = []
  if row:
    keyboard.append(row)
  
  keyboard.append([InlineKeyboardButton("✅ اتمام انتخاب مافیاها", callback_data="m_maf_done")])

  try:
    await query.edit_message_text(
        "🔪 **انتخاب ساید مافیا:**\nروی نام بازیکنان مافیا کلیک کنید تا تیک بخورند:",
        reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown"
    )
  except Exception:
    pass


async def refresh_multiselect_mafias(query, flow):
  all_p = get_all_player_names()
  already_chosen = flow.get("citizens", [])
  selected = flow.get("temp_mafias", [])
  
  keyboard = []
  row = []
  for p in all_p:
    if p in already_chosen:
      continue
    is_selected = p in selected
    mark = "✅ " if is_selected else ""
    row.append(InlineKeyboardButton(f"{mark}{p}", callback_data=f"m_maf_toggle:{p}"))
    if len(row) == 2:
      keyboard.append(row)
      row = []
  if row:
    keyboard.append(row)
  
  keyboard.append([InlineKeyboardButton("✅ اتمام انتخاب مافیاها", callback_data="m_maf_done")])

  selected_str = ", ".join(selected) if selected else "هیچ‌کس انتخاب نشده"
  try:
    await query.edit_message_text(
        f"🔪 مافیاهای تیک‌خورده: `{selected_str}`\n\nبرای تغییر انتخاب‌ها دکمه‌ها را لمس کنید:",
        reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown"
    )
  except Exception:
    pass


async def prompt_multiselect_independents(query, flow):
  all_p = get_all_player_names()
  already_chosen = flow.get("citizens", []) + flow.get("mafias", [])
  if "temp_independents" not in flow:
    flow["temp_independents"] = []
  
  keyboard = []
  row = []
  for p in all_p:
    if p in already_chosen:
      continue
    is_selected = p in flow["temp_independents"]
    mark = "✅ " if is_selected else ""
    row.append(InlineKeyboardButton(f"{mark}{p}", callback_data=f"m_ind_toggle:{p}"))
    if len(row) == 2:
      keyboard.append(row)
      row = []
  if row:
    keyboard.append(row)
  
  keyboard.append([InlineKeyboardButton("✅ اتمام انتخاب مستقل‌ها", callback_data="m_ind_done")])

  try:
    await query.edit_message_text(
        "🃏 **انتخاب ساید مستقل:**\nروی نام بازیکنان مستقل کلیک کنید تا تیک بخورند:",
        reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown"
    )
  except Exception:
    pass


async def refresh_multiselect_independents(query, flow):
  all_p = get_all_player_names()
  already_chosen = flow.get("citizens", []) + flow.get("mafias", [])
  selected = flow.get("temp_independents", [])
  
  keyboard = []
  row = []
  for p in all_p:
    if p in already_chosen:
      continue
    is_selected = p in selected
    mark = "✅ " if is_selected else ""
    row.append(InlineKeyboardButton(f"{mark}{p}", callback_data=f"m_ind_toggle:{p}"))
    if len(row) == 2:
      keyboard.append(row)
      row = []
  if row:
    keyboard.append(row)
  
  keyboard.append([InlineKeyboardButton("✅ اتمام انتخاب مستقل‌ها", callback_data="m_ind_done")])

  selected_str = ", ".join(selected) if selected else "هیچ‌کس انتخاب نشده"
  try:
    await query.edit_message_text(
        f"🃏 مستقل‌های تیک‌خورده: `{selected_str}`\n\nبرای تغییر انتخاب‌ها دکمه‌ها را لمس کنید:",
        reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown"
    )
  except Exception:
    pass


async def prompt_chaos_player_selection(query, flow):
  all_players = get_all_player_names()
  keyboard = []
  row = []
  for p in all_players:
    if p not in flow["chaos_players"]:
      row.append(InlineKeyboardButton(p, callback_data=f"chaos_pick:{p}"))
      if len(row) == 2:
        keyboard.append(row)
        row = []
  if row:
    keyboard.append(row)

  current_count = len(flow["chaos_players"]) + 1
  selected_str = ", ".join(flow["chaos_players"]) if flow["chaos_players"] else "هنوز انتخابی نشده"
  
  try:
    await query.edit_message_text(
        f"🌪 بازیکنان منتخب کِی‌آس تا اینجا: `{selected_str}`\n\n"
        f"لطفاً بازیکن شماره **{current_count}** از ۳ نفر کِی‌آس را انتخاب کنید:",
        reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown"
    )
  except Exception:
    pass


async def prompt_chaos_selected_player(query, flow):
  keyboard = []
  row = []
  for p in flow["chaos_players"]:
    row.append(InlineKeyboardButton(p, callback_data=f"chaos_select_one:{p}"))
    if len(row) == 2:
      keyboard.append(row)
      row = []
  if row:
    keyboard.append(row)

  try:
    await query.edit_message_text(
        f"🌪 ۳ بازیکن کِی‌آس: `{', '.join(flow['chaos_players'])}`\n\n"
        f"🎯 لطفاً **فرد منتخب** را از بین این سه نفر مشخص کنید:",
        reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown"
    )
  except Exception:
    pass


async def prompt_night1_shot(query, flow):
  all_players_in_game = flow["citizens"] + flow["mafias"] + flow["independents"]
  keyboard = []
  row = []
  for p in all_players_in_game:
    row.append(InlineKeyboardButton(p, callback_data=f"n1_shot_pick:{p}"))
    if len(row) == 2:
      keyboard.append(row)
      row = []
  if row:
    keyboard.append(row)
  keyboard.append([InlineKeyboardButton("🚫 شات شب اول نداشت / ثبت نشد", callback_data="n1_shot_pick:none")])

  try:
    await query.edit_message_text(
        "🎯 شات شب اول توسط مافیا روی چه کسی بوده است؟",
        reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown"
    )
  except Exception:
    pass


async def prompt_mvp_selection(query, flow):
  all_players_in_game = flow["citizens"] + flow["mafias"] + flow["independents"]
  keyboard = []
  row = []
  for p in all_players_in_game:
    mark = "🌟 " if p in flow["mvps"] else ""
    row.append(InlineKeyboardButton(f"{mark}{p}", callback_data=f"mvp_pick:{p}"))
    if len(row) == 2:
      keyboard.append(row)
      row = []
  if row:
    keyboard.append(row)
  keyboard.append([InlineKeyboardButton("✅ اتمام انتخاب بست پلیر بازی (MVP)", callback_data="done_mvps")])

  try:
    await query.edit_message_text(
        "🌟 بست پلیر(های) بازی (MVP) را از میان تمام بازیکنان انتخاب کنید (می‌توانید چند نفر را لمس کنید):",
        reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown"
    )
  except Exception:
    pass


async def refresh_mvp_keyboard(query, flow):
  all_players_in_game = flow["citizens"] + flow["mafias"] + flow["independents"]
  keyboard = []
  row = []
  for p in all_players_in_game:
    mark = "🌟 " if p in flow["mvps"] else ""
    row.append(InlineKeyboardButton(f"{mark}{p}", callback_data=f"mvp_pick:{p}"))
    if len(row) == 2:
      keyboard.append(row)
      row = []
  if row:
    keyboard.append(row)
  keyboard.append([InlineKeyboardButton("✅ اتمام انتخاب بست پلیر بازی (MVP)", callback_data="done_mvps")])

  mvp_str = ", ".join(flow["mvps"]) if flow["mvps"] else "هنوز انتخاب نشده"
  try:
    await query.edit_message_text(
        f"🌟 افراد انتخاب شده به عنوان بست پلیر بازی: {mvp_str}\n\nبرای تغییر یا اتمام دکمه‌ها را لمس کنید:",
        reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown"
    )
  except Exception:
    pass


async def prompt_axe_selection(query, flow):
  all_players_in_game = flow["citizens"] + flow["mafias"] + flow["independents"]
  keyboard = []
  row = []
  for p in all_players_in_game:
    mark = "🪓 " if p in flow["axes"] else ""
    row.append(InlineKeyboardButton(f"{mark}{p}", callback_data=f"axe_pick:{p}"))
    if len(row) == 2:
      keyboard.append(row)
      row = []
  if row:
    keyboard.append(row)
  keyboard.append([InlineKeyboardButton("✅ اتمام انتخاب تبر", callback_data="done_axes")])

  try:
    await query.edit_message_text(
        "🪓 پلیر(های) تبر بازی را انتخاب کنید (اختیاری - دارای امتیاز منفی):",
        reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown"
    )
  except Exception:
    pass


async def refresh_axe_keyboard(query, flow):
  all_players_in_game = flow["citizens"] + flow["mafias"] + flow["independents"]
  keyboard = []
  row = []
  for p in all_players_in_game:
    mark = "🪓 " if p in flow["axes"] else ""
    row.append(InlineKeyboardButton(f"{mark}{p}", callback_data=f"axe_pick:{p}"))
    if len(row) == 2:
      keyboard.append(row)
      row = []
  if row:
    keyboard.append(row)
  keyboard.append([InlineKeyboardButton("✅ اتمام انتخاب تبر", callback_data="done_axes")])

  axe_str = ", ".join(flow["axes"]) if flow["axes"] else "بدون تبر"
  try:
    await query.edit_message_text(
        f"🪓 افراد انتخاب شده به عنوان تبر: {axe_str}\n\nبرای تغییر یا اتمام دکمه‌ها را لمس کنید:",
        reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown"
    )
  except Exception:
    pass


async def prompt_unfair_selection(query, flow):
  all_players_in_game = flow["citizens"] + flow["mafias"] + flow["independents"]
  keyboard = []
  row = []
  for p in all_players_in_game:
    mark = "🐍 " if p in flow["unfairs"] else ""
    row.append(InlineKeyboardButton(f"{mark}{p}", callback_data=f"unfair_pick:{p}"))
    if len(row) == 2:
      keyboard.append(row)
      row = []
  if row:
    keyboard.append(row)
  keyboard.append([InlineKeyboardButton("✅ اتمام انتخاب آنفیر", callback_data="done_unfairs")])

  try:
    await query.edit_message_text(
        "🐍 پلیر(های) آنفیر (نامرد) بازی را انتخاب کنید (اختیاری - دارای امتیاز منفی):",
        reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown"
    )
  except Exception:
    pass


async def refresh_unfair_keyboard(query, flow):
  all_players_in_game = flow["citizens"] + flow["mafias"] + flow["independents"]
  keyboard = []
  row = []
  for p in all_players_in_game:
    mark = "🐍 " if p in flow["unfairs"] else ""
    row.append(InlineKeyboardButton(f"{mark}{p}", callback_data=f"unfair_pick:{p}"))
    if len(row) == 2:
      keyboard.append(row)
      row = []
  if row:
    keyboard.append(row)
  keyboard.append([InlineKeyboardButton("✅ اتمام انتخاب آنفیر", callback_data="done_unfairs")])

  unfair_str = ", ".join(flow["unfairs"]) if flow["unfairs"] else "بدون آنفیر"
  try:
    await query.edit_message_text(
        f"🐍 افراد انتخاب شده به عنوان آنفیر: {unfair_str}\n\nبرای تغییر یا اتمام دکمه‌ها را لمس کنید:",
        reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown"
    )
  except Exception:
    pass


async def prompt_artin_selection(query, flow):
  all_players_in_game = flow["citizens"] + flow["mafias"] + flow["independents"]
  keyboard = []
  row = []
  for p in all_players_in_game:
    mark = "👑 " if p in flow["artins"] else ""
    row.append(InlineKeyboardButton(f"{mark}{p}", callback_data=f"artin_pick:{p}"))
    if len(row) == 2:
      keyboard.append(row)
      row = []
  if row:
    keyboard.append(row)
  keyboard.append([InlineKeyboardButton("✅ اتمام و ذخیره نهایی بازی", callback_data="done_artins")])

  try:
    await query.edit_message_text(
        "👑 پلیر(های) آرتین (یارفروش) بازی را انتخاب کنید (اختیاری - دارای امتیاز منفی سنگین):",
        reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown"
    )
  except Exception:
    pass


async def refresh_artin_keyboard(query, flow):
  all_players_in_game = flow["citizens"] + flow["mafias"] + flow["independents"]
  keyboard = []
  row = []
  for p in all_players_in_game:
    mark = "👑 " if p in flow["artins"] else ""
    row.append(InlineKeyboardButton(f"{mark}{p}", callback_data=f"artin_pick:{p}"))
    if len(row) == 2:
      keyboard.append(row)
      row = []
  if row:
    keyboard.append(row)
  keyboard.append([InlineKeyboardButton("✅ اتمام و ذخیره نهایی بازی", callback_data="done_artins")])

  artin_str = ", ".join(flow["artins"]) if flow["artins"] else "بدون آرتین"
  try:
    await query.edit_message_text(
        f"👑 افراد انتخاب شده به عنوان آرتین: {artin_str}\n\nبرای تغییر یا اتمام دکمه‌ها را لمس کنید:",
        reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown"
    )
  except Exception:
    pass


async def finalize_and_save_game(query, flow, context):
  cur_season = get_current_season()
  scen = flow["scenario"]
  winner = flow["winner_side"]
  end_mode = flow["end_mode"]
  chaos_players_str = ",".join(flow["chaos_players"]) if flow["chaos_players"] else None
  chaos_selected = flow["chaos_selected"]
  chaos_win_impact = flow["chaos_win_impact"]

  citizens = flow["citizens"]
  mafias = flow["mafias"]
  independents = flow["independents"]
  n1_shot = flow["night1_shot"]
  n1_out = flow["night1_out"]
  mvps = flow["mvps"]
  axes = flow["axes"]
  unfairs = flow["unfairs"]
  artins = flow["artins"]

  with sqlite3.connect("mafia_league.db") as conn:
    c = conn.cursor()
    c.execute(
        "INSERT INTO match_history (season, scenario_name, winning_side, end_mode, chaos_players, chaos_selected, chaos_win_impact) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (cur_season, scen, winner, end_mode, chaos_players_str, chaos_selected, chaos_win_impact)
    )
    match_id = c.lastrowid

    for p in citizens:
      won = 1 if winner == "شهروند" else 0
      is_mvp = 1 if p in mvps else 0
      is_axe = 1 if p in axes else 0
      is_unfair = 1 if p in unfairs else 0
      is_artin = 1 if p in artins else 0
      n1_s = 1 if (n1_shot == p) else 0
      n1_o = 1 if (n1_shot == p and n1_out) else 0
      c.execute(
          "INSERT INTO match_participants (match_id, player_name, side, won, is_mvp, is_axe, is_unfair, is_artin, night1_shot, night1_out) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
          (match_id, p, "شهروند", won, is_mvp, is_axe, is_unfair, is_artin, n1_s, n1_o)
      )

    for p in mafias:
      won = 1 if winner == "مافیا" else 0
      is_mvp = 1 if p in mvps else 0
      is_axe = 1 if p in axes else 0
      is_unfair = 1 if p in unfairs else 0
      is_artin = 1 if p in artins else 0
      n1_s = 1 if (n1_shot == p) else 0
      n1_o = 1 if (n1_shot == p and n1_out) else 0
      c.execute(
          "INSERT INTO match_participants (match_id, player_name, side, won, is_mvp, is_axe, is_unfair, is_artin, night1_shot, night1_out) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
          (match_id, p, "مافیا", won, is_mvp, is_axe, is_unfair, is_artin, n1_s, n1_o)
      )

    for p in independents:
      won = 1 if winner == "مستقل" else 0
      is_mvp = 1 if p in mvps else 0
      is_axe = 1 if p in axes else 0
      is_unfair = 1 if p in unfairs else 0
      is_artin = 1 if p in artins else 0
      n1_s = 1 if (n1_shot == p) else 0
      n1_o = 1 if (n1_shot == p and n1_out) else 0
      c.execute(
          "INSERT INTO match_participants (match_id, player_name, side, won, is_mvp, is_axe, is_unfair, is_artin, night1_shot, night1_out) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
          (match_id, p, "مستقل", won, is_mvp, is_axe, is_unfair, is_artin, n1_s, n1_o)
      )

    conn.commit()

  recalculate_all_players()

  success_text = (
      f"🎉 **مسابقه جدید با موفقیت ثبت و ذخیره شد!**\n\n"
      f"🎬 سناریو: **{scen}**\n"
      f"🏆 برنده: **{winner}**\n"
      f"🏁 نحوه پایان: **{end_mode}**\n"
  )
  if end_mode == "کی آس":
    success_text += (
        f"🌪 بازیکنان کِی‌آس: `{chaos_players_str}`\n"
        f"🎯 فرد منتخب: **{chaos_selected}**\n"
        f"💡 باعث برد سایدش شد؟ **{chaos_win_impact}**\n"
    )

  success_text += (
      f"🎯 شات شب اول: **{n1_shot if n1_shot != 'none' else 'ندارد'}** "
      f"({'خارج شد ❌' if n1_out else ('ماند ✅' if n1_shot != 'none' else '')})\n\n"
      "تمامی امتیازات، ریتینگ‌ها و آمار تبرها، آنفیرها و آرتین‌های بازیکنان بروزرسانی گردید."
  )
  keyboard = [[InlineKeyboardButton("🔙 بازگشت به پنل مدیریت", callback_data="open_admin_panel")]]
  try:
    await query.edit_message_text(success_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
  except Exception:
    pass


def main():
  builder = ApplicationBuilder().token(TOKEN).post_init(post_init)

  builder.connect_timeout(30.0).read_timeout(30.0).write_timeout(30.0)

  app = builder.build()

  app.add_handler(CommandHandler("start", start))
  app.add_handler(CommandHandler("takamol", send_takamol_menu))
  app.add_handler(CommandHandler("help", start))
  app.add_handler(CommandHandler("join", join))
  app.add_handler(CommandHandler("links", show_links_menu))
  app.add_handler(CommandHandler("history", public_history_cmd))
  app.add_handler(CommandHandler("rename", rename))
  app.add_handler(CommandHandler("scoring", scoring_guide))
  app.add_handler(CommandHandler("admin", admin_panel))
  app.add_handler(CommandHandler("matches", show_matches_list))
  app.add_handler(CommandHandler("delete_match", delete_match_cmd))
  app.add_handler(CommandHandler("add_player", add_player_manual))
  app.add_handler(CommandHandler("remove_player", remove_player_cmd))
  app.add_handler(CommandHandler("merge_player", merge_players_cmd))
  app.add_handler(CommandHandler("rename", rename))
  app.add_handler(CommandHandler("players", players_list))
  app.add_handler(CommandHandler("table", table))
  app.add_handler(CommandHandler("advanced_table", ask_advanced_season_choice))
  app.add_handler(CommandHandler("bests", best_players_leaderboard))
  app.add_handler(CommandHandler("axes", axes_leaderboard))
  app.add_handler(CommandHandler("unfair", unfair_leaderboard))
  app.add_handler(CommandHandler("artin", artin_leaderboard))
  app.add_handler(CommandHandler("teammates", ask_teammates_season_choice))
  app.add_handler(CommandHandler("streaks", ask_streaks_season_choice))
  app.add_handler(CommandHandler("shots_top", ask_shots_season_choice))
  app.add_handler(CommandHandler("stats", stats))
  app.add_handler(CommandHandler("vs", vs))
  app.add_handler(CommandHandler("chart", chart))
  app.add_handler(CommandHandler("sides", sides))
  app.add_handler(CommandHandler("scenarios", scenarios_stat))
  app.add_handler(CommandHandler("submit_game", submit_game))
  app.add_handler(CallbackQueryHandler(game_flow_handler))
  app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_messages))

  print("ربات لیگ با موفقیت فعال شد...")
  app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
  main()
