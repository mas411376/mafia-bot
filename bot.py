import sqlite3
import math
import os
import logging
import random
import html
from datetime import datetime
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
ADMIN_ID_2 = 5525697104

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

SPECIAL_SCENARIOS = [
    "شاهنامه",
    "رنک",
    "هانیبال",
    "اختاپوس مخوف (سندیکا)",
    "جایزه سر رئیس",
    "میتیک",
    "ارتش سری",
    "نقابدار",
    "دربار",
    "پرطرفدار",
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
                raw_score REAL DEFAULT 0.0,
                total_games INTEGER DEFAULT 0,
                wins INTEGER DEFAULT 0,
                losses INTEGER DEFAULT 0,
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
                advanced_skill_score REAL DEFAULT 1000.0,
                is_restricted INTEGER DEFAULT 0
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
                raw_score REAL,
                total_games INTEGER,
                wins INTEGER,
                losses INTEGER,
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
    if "unfair_count" not in pl_cols:
      c.execute("ALTER TABLE players ADD COLUMN unfair_count INTEGER DEFAULT 0")
    if "artin_count" not in pl_cols:
      c.execute("ALTER TABLE players ADD COLUMN artin_count INTEGER DEFAULT 0")
    if "is_restricted" not in pl_cols:
      c.execute("ALTER TABLE players ADD COLUMN is_restricted INTEGER DEFAULT 0")

    c.execute("PRAGMA table_info(match_participants)")
    p_cols = [col[1] for col in c.fetchall()]
    if "is_unfair" not in p_cols:
      c.execute("ALTER TABLE match_participants ADD COLUMN is_unfair INTEGER DEFAULT 0")
    if "is_artin" not in p_cols:
      c.execute("ALTER TABLE match_participants ADD COLUMN is_artin INTEGER DEFAULT 0")

    c.execute("PRAGMA table_info(season_archives)")
    sa_cols = [col[1] for col in c.fetchall()]
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


def get_opponent_strength_multiplier(conn, match_id, player_name, player_side):
  c = conn.cursor()
  c.execute("SELECT player_name, side, won FROM match_participants WHERE match_id = ?", (match_id,))
  parts = c.fetchall()
  
  opp_ratings = []
  for p_name, side, won in parts:
    if side != player_side:
      c.execute("SELECT advanced_skill_score FROM players WHERE name = ?", (p_name,))
      r_row = c.fetchone()
      opp_ratings.append(r_row[0] if r_row else 1000.0)
      
  c.execute("SELECT advanced_skill_score FROM players WHERE name = ?", (player_name,))
  p_row = c.fetchone()
  p_rating = p_row[0] if p_row else 1000.0
  
  if not opp_ratings:
    return 1.0
    
  avg_opp_rating = sum(opp_ratings) / len(opp_ratings)
  diff = avg_opp_rating - p_rating
  
  if diff > 30.0:
    return 1.3
  elif diff < -30.0:
    return 0.8
  else:
    return 1.0


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
      c.execute("SELECT player_name, won, is_unfair, is_artin FROM match_participants WHERE match_id = ?", (m_id,))
      parts = c.fetchall()
      
      winners = [p[0] for p in parts if p[1] == 1]
      losers = [p[0] for p in parts if p[1] == 0]

      if not winners or not losers:
        continue

      avg_winner_skill = sum(player_adv_scores.get(w, 1000.0) for w in winners) / len(winners)
      avg_loser_skill = sum(player_adv_scores.get(l, 1000.0) for l in losers) / len(losers)

      skill_diff = avg_loser_skill - avg_winner_skill
      dynamic_factor = max(-4.0, min(4.0, skill_diff / 50.0))

      for p_name, won, unfair, artin in parts:
        if p_name not in player_adv_scores:
          player_adv_scores[p_name] = 1000.0

        if won == 1:
          base_delta = 10.0 + dynamic_factor
        else:
          base_delta = -8.0 + dynamic_factor

        penalty_unfair = (-6.0 if unfair else 0.0)
        penalty_artin = (-8.0 if artin else 0.0)
        player_adv_scores[p_name] += (base_delta + penalty_unfair + penalty_artin)

    for p_name in players:
      c.execute(
          """
                SELECT p.side, p.won, p.is_unfair, p.is_artin, p.night1_shot, p.night1_out, p.match_id, m.scenario_name, m.end_mode
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
      unfairs = sum(1 for m in matches if m[2] == 1)
      artins = sum(1 for m in matches if m[3] == 1)
      n1_shots = sum(1 for m in matches if m[4] == 1)
      n1_outs = sum(1 for m in matches if m[5] == 1)

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

      raw = 0.0
      cur_streak = 0
      best_streak = 0

      for m in matches:
        won = m[1]
        unfair = m[2]
        artin = m[3]
        m_id = m[6]
        scen_name = m[7]
        end_mode = m[8]
        side = m[0]

        if won == 1:
          cur_streak += 1
          best_streak = max(best_streak, cur_streak)
          
          if cur_streak == 3:
            streak_bonus = 2.0
          elif cur_streak == 4:
            streak_bonus = 4.0
          elif cur_streak >= 5:
            streak_bonus = 6.0
          else:
            streak_bonus = 0.0

          opp_mult = get_opponent_strength_multiplier(conn, m_id, p_name, side)

          if end_mode == "کلین شیت":
            if side == "شهروند":
              win_type_mult = 2.0
            elif side == "مافیا":
              win_type_mult = 1.4
            else:
              win_type_mult = 1.0
          elif end_mode == "کی آس":
            win_type_mult = 0.7
          else:
            win_type_mult = 1.0

          scen_mult = 1.3 if scen_name in SPECIAL_SCENARIOS else 1.0

          game_pts = ((10.0 * opp_mult * win_type_mult) + streak_bonus) * scen_mult
        else:
          cur_streak = 0
          game_pts = 0.0

        if unfair:
          game_pts -= 6.0
        if artin:
          game_pts -= 8.0

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
                    unfair_count = ?, artin_count = ?,
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
              round(raw, 2),
              total_g,
              wins,
              losses,
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


def get_all_player_names():
  with sqlite3.connect("mafia_league.db") as conn:
    c = conn.cursor()
    c.execute("SELECT name FROM players WHERE is_restricted = 0 ORDER BY name ASC")
    return [r[0] for r in c.fetchall()]


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
      BotCommand("unfair", "جدول نامرد طلایی (آنفیر) 🐍"),
      BotCommand("artin", "جدول آرتین طلایی (آرتین بازی) 👑"),
      BotCommand("teammates", "رده‌بندی بهترین هم‌تیمی‌ها 👥"),
      BotCommand("streaks", "رده‌بندی بهترین استریک‌ها 🔥"),
      BotCommand("shots_top", "برترین سوءقصدشده‌های شب اول 🎯"),
      BotCommand("vs", "تقابل دوئل و رودررو ⚔️"),
      BotCommand("scoring", "راهنمای امتیازدهی لیگ 📜"),
      BotCommand("admin", "پنل مدیریت ادمین ⚙"),
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


async def scoring_guide(update: Update, context: ContextTypes.DEFAULT_TYPE):
  if not await enforce_channel_lock(update, context, check_lock=True):
    return
  log_feature_click(update.effective_user.id, "راهنمای امتیازدهی")
  text = (
      "📜 **راهنمای سیستم امتیازدهی و ریتینگ لیگ:**\n\n"
      "🎖 **مدل جامع امتیازدهی و ضرایب لیگ تکامل:**\n"
      "▫️ امتیاز پایه هر برد: `۱۰` امتیاز (قابل تعدیل بر اساس ضریب قدرت حریف، نوع پیروزی و سناریو)\n"
      "▫️ شکست در مسابقه: `۰` امتیاز\n"
      "▫️ پلیر آنفیر (نامرد بازی): `-۶` امتیاز جریمه\n"
      "▫️ پلیر آرتین (یارفروش): `-۸` امتیاز جریمه\n\n"
      "🔥 **۱. پاداش استریک‌های پیاپی (پلکانی و تصاعدی):**\n"
      "▫️ برد ۱ و ۲: بدون پاداش استریک (ضریب پایه)\n"
      "▫️ برد ۳ متوالی: `+۲` امتیاز اضافه\n"
      "▫️ برد ۴ متوالی: `+۴` امتیاز اضافه\n"
      "▫️ برد ۵ و بالاتر: `+۶` امتیاز اضافه به ازای هر برد متوالی\n\n"
      "⚖️ **۲. ضریب قدرت حریف (توازن مهارت تیم‌ها):**\n"
      "▫️ برد در برابر تیم قوی‌تر: ضریب `1.3` (پاداش ویژه به خاطر تسخیر حریف قدرتمند)\n"
      "▫️ برد در برابر تیم هم‌سطح: ضریب `1.0` (امتیاز استاندارد)\n"
      "▫️ برد در برابر تیم ضعیف‌تر: ضریب `0.8` (پاداش کمتر برای بردهای قابل پیش‌بینی)\n\n"
      "🏁 **۳. پاداش نوع پیروزی (کلین‌شیت و کی‌آس):**\n"
      "▫️ کلین‌شیت شهروندی (برد قاطع بدون تلفات): ضریب `2.0` (دو برابر امتیاز برد عادی)\n"
      "▫️ کلین‌شیت مافیایی (برد قاطع مافیا): ضریب `1.4` (پاداش بیشتر نسبت به برد معمولی)\n"
      "▫️ پیروزی در حالت کی‌آس (Chaos): ضریب `0.7` (چون بازی از حالت استاندارد خارج شده و شانس هم دخیل بوده، پاداش کمتری برای تعادل لحاظ می‌شود)\n\n"
      "🎬 **۴. ضریب سختی و جذابیت سناریوها:**\n"
      "▫️ سناریوهای ویژه (ضریب `1.3`): شاهنامه، رنک، هانیبال، اختاپوس مخوف (سندیکا)، جایزه سر رئیس، میتیک، ارتش سری، نقابدار، دربار، پرطرفدار\n"
      "▫️ سایر سناریوهای استاندارد: ضریب `1.0`\n\n"
      "👑 **القاب اختصاصی نفرات اول هر جدول در هر فصل:**\n"
      "▫️ نفر اول جدول رده‌بندی لیگ: 🏛 **امپراطور لیگ**\n"
      "▫️ نفر اول رده‌بندی پیشرفته (ارزش برد): 🧠 **مغز متفکر**\n"
      "▫️ نفر اول جدول نامرد طلایی (آنفیر): 🐍 **پیتون اعظم**\n"
      "▫️ نفر اول جدول آرتین طلایی: 🐺 **کفتار تنها**\n"
      "▫️ نفر اول رده‌بندی بهترین هم‌تیمی‌ها: 🤝 **اتحاد آهنین**\n"
      "▫️ نفر اول رده‌بندی بهترین استریک‌ها: ⚔️ **ماشین کشتار**\n"
      "▫️ نفر اول برترین شات‌شده‌های شب اول: 🎯 **کابوس مافیا**\n\n"
      "⚖️ **نحوه تعیین عناوین (آنفیر و آرتین):**\n"
      "▫️ انتخاب بازیکنان آنفیر و آرتین بر عهده مدیر بازی و در صورت نداشتن مدیر، بر عهده گرداننده (گاد) داخل بازی است.\n\n"
      "📌 **قوانین و شرایط خاص یارفروشی و خودزنی:**\n"
      "▫️ اگر تصمیم یارفروشی یا خودزنی، تصمیم کل تیم باشد، جریمه برای همه اعضای تیم لحاظ می‌شود؛ در این حالت تیم با توجه به امتیاز برد و جریمه کسر شده، پاداش بسیار کمی از آن برد نصیبش خواهد شد.\n"
      "▫️ اما اگر یارفروشی یا خودزنی تصمیم فردی باشد، جریمه صرفاً شامل حال همان فرد خواهد شد.\n"
      "▫️ در نتیجه، یارفروشی اصلاً توصیه نمی‌شود، اما بازیکن می‌تواند با انجام این کار امتیاز برد را دریافت کند و حتی اگر روی نوار استریک برد باشد، با حفظ آن نوار امتیاز بیشتری کسب کند.\n\n"
      "⭐ **رده‌بندی پیشرفته (پویا و مهارت‌محور):**\n"
      "در این بخش امتیازات بر اساس میانگین مهارت تیم‌ها محاسبه می‌شود؛ برد در برابر تیم‌های قوی‌تر پاداش بیشتری دارد و باخت در برابر تیم‌های ضعیف‌تر جریمه سنگین‌تری به همراه خواهد داشت.\n\n"
      "⚖️ **نحوه محاسبه ریتینگ در جدول رده‌بندی:**\n"
      "رتبه نهایی بازیکنان بر اساس «ریتینگ هوشمند» محاسبه می‌شود که علاوه بر مجموع امتیازات خام اصلاح‌شده، تعداد بازی‌ها و کیفیت عملکرد را در نظر می‌گیرد."
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
          "🔹 **ارتباط در پی‌وی:** هرگونه پیام خصوصی میان بازیکنان در حین بازی (چه هم‌تیمی و چه رقیب) تقلب محسوب شده و منجر به محرومیت و در صورت تکرار، اخراج دائمی می‌شود."
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
          "   ▫️ اشاره به نقش‌های سناریوهای دیگر در جریان بازی جاری.\n\n"
          "🔹 **اکت در دفاعیه:** هرگونه اکت دادن در فاز دفاعیه ممنوع بوده و موجب سلب حق رأی می‌شود (مگر در سناریوهایی با قانون اکت آزاد یا میتیک که کیک مستقیم دارد)."
      ),
      "6": (
          "۶. **حضور، پایان بازی، خداحافظی و نحوه نظرسنجی‌ها**\n\n"
          "🔹 **تأخیر و غیبت:** بیش از ۱۵ دقیقه تأخیر منجر به حذف یا جایگزینی خواهد شد و فرد خاطی در صورت تکرار، یک هفته از بازی‌های گروه محروم می‌شود.\n\n"
          "🔹 **پایان بازی:** حضور در جلسه تا انتهای بازی الزامی است مگر با هماهنگی قبلی.\n\n"
          "🔹 **خداحافظی و لغو تحلیلیه:**\n"
          "   ▫️ بازی‌ها فاز «تحلیلیه» ندارند.\n"
          "   ▫️ بعد از هر بازی، هر فرد ۱۵ الی ۲۰ ثانیه وقت برای خداحافظی در اختیار دارد و پس از آن حق صحبت و تصویر از همه افراد گرفته می‌شود.\n"
          "   ▫️ در صورت تمایل به تحلیلیه، اعضا می‌توانند با ایجاد لینک جداگانه در میت یا زوم، یا به صورت پیام متنی در گروه به تحلیل بپردازند.\n\n"
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
      [InlineKeyboardButton("🐍 جدول نامرد طلایی (پلیر آنفیر)", callback_data="ask_unfair_season")],
      [InlineKeyboardButton("👑 جدول آرتین طلایی (آرتین بازی)", callback_data="ask_artin_season")],
      [InlineKeyboardButton("👥 رده‌بندی بهترین هم‌تیمی‌ها", callback_data="ask_teammates_season")],
      [InlineKeyboardButton("🔥 رده‌بندی بهترین استریک‌ها", callback_data="ask_streaks_season")],
      [InlineKeyboardButton("🎯 برترین شات‌شده‌های شب اول", callback_data="show_shots_lb")],
      [InlineKeyboardButton("⚔️ دوئل و تقابل رودررو", callback_data="ask_vs_season")],
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


async def ask_unfair_season_choice(update: Update, context: ContextTypes.DEFAULT_TYPE = None):
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
  elif update.message:
    await update.message.reply_text(
        text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown"
    )


async def unfair_leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
  if not await enforce_channel_lock(update, context, check_lock=True):
    return
  await ask_unfair_season_choice(update, context)


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


async def ask_artin_season_choice(update: Update, context: ContextTypes.DEFAULT_TYPE = None):
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
  elif update.message:
    await update.message.reply_text(
        text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown"
    )


async def artin_leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
  if not await enforce_channel_lock(update, context, check_lock=True):
    return
  await ask_artin_season_choice(update, context)


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
      await update.callback_query.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    except Exception:
      pass


async def ask_teammates_season_choice(update: Update, context: ContextTypes.DEFAULT_TYPE = None):
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
  elif update.message:
    await update.message.reply_text(
        text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown"
    )


async def teammates_leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
  if not await enforce_channel_lock(update, context, check_lock=True):
    return
  await ask_teammates_season_choice(update, context)


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
      await update.callback_query.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    except Exception:
      pass


async def ask_streaks_season_choice(update: Update, context: ContextTypes.DEFAULT_TYPE = None):
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
  elif update.message:
    await update.message.reply_text(
        text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown"
    )


async def streaks_leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
  if not await enforce_channel_lock(update, context, check_lock=True):
    return
  await ask_streaks_season_choice(update, context)


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


async def ask_advanced_season_choice(update: Update, context: ContextTypes.DEFAULT_TYPE = None):
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
  elif update.message:
    await update.message.reply_text(
        text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown"
    )


async def advanced_table_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
  if not await enforce_channel_lock(update, context, check_lock=True):
    return
  await ask_advanced_season_choice(update, context)


async def render_advanced_table_page(update: Update, season_filter: str, page: int):
  log_feature_click(update.effective_user.id, f"رده‌بندی پیشرفته ({season_filter})")

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
  elif update.message:
    await update.message.reply_text(text, reply_markup=reply_markup, parse_mode="Markdown")


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
                "➕ افزودن بازیکن به مسابقه ثبت‌شده",
                callback_data="open_add_to_match_list",
            )
        ],
        [
            InlineKeyboardButton(
                "🚫 مدیریت محدودیت بازیکنان",
                callback_data="open_restrict_picker",
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
                "➕ افزودن بازیکن به مسابقه ثبت‌شده",
                callback_data="open_add_to_match_list",
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


async def show_add_to_match_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
  if update.effective_user.id not in [ADMIN_ID, ADMIN_ID_2]:
    return

  cur_season = get_current_season()
  with sqlite3.connect("mafia_league.db") as conn:
    c = conn.cursor()
    c.execute(
        "SELECT match_id, scenario_name, winning_side, created_at FROM match_history WHERE season = ? ORDER BY match_id DESC",
        (cur_season,),
    )
    rows = c.fetchall()

  if not rows:
    msg = f"هنوز مسابقه‌ای در فصل {cur_season} ثبت نشده است."
    if update.callback_query:
      await update.callback_query.answer(msg, show_alert=True)
    return

  keyboard = []
  for m_id, scen, win_side, dt in rows:
    time_clean = dt.split()[0] if dt else ""
    btn_text = f"🎮 بازی #{m_id} | {scen} | برنده: {win_side} ({time_clean})"
    keyboard.append([InlineKeyboardButton(btn_text, callback_data=f"add_to_match_sel:{m_id}")])

  keyboard.append([InlineKeyboardButton("🔙 بازگشت به پنل ادمین", callback_data="open_admin_panel")])
  text = "➕ **انتخاب مسابقه:**\n\nمسابقه‌ای که می‌خواهید به آن بازیکن اضافه کنید را انتخاب کنید:"
  
  if update.callback_query:
    try:
      await update.callback_query.message.reply_text(
          text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown"
      )
    except Exception:
      pass


async def show_add_player_side_picker(update: Update, context: ContextTypes.DEFAULT_TYPE, match_id: int):
  context.user_data["add_to_match_id"] = match_id
  
  with sqlite3.connect("mafia_league.db") as conn:
    c = conn.cursor()
    c.execute("SELECT winning_side FROM match_history WHERE match_id = ?", (match_id,))
    m = c.fetchone()
    winning_side = m[0] if m else "شهروند"

  keyboard = [
      [InlineKeyboardButton("🏙 شهروند", callback_data="atm_side:شهروند")],
      [InlineKeyboardButton("🔪 مافیا", callback_data="atm_side:مافیا")],
      [InlineKeyboardButton("🃏 مستقل", callback_data="atm_side:مستقل")],
      [InlineKeyboardButton("🔙 بازگشت به لیست مسابقات", callback_data="open_add_to_match_list")]
  ]
  text = (
      f"🎮 **مسابقه شماره #{match_id}**\n\n"
      f"انتخاب کنید بازیکن جدید به کدام **ساید** اضافه شود؟\n"
      f"(توجه: اگر ساید انتخاب‌شده با ساید برنده مسابقه مطابقت داشته باشد، امتیاز برد به این بازیکن هم تعلق خواهد گرفت)"
  )
  if update.callback_query:
    try:
      await update.callback_query.message.reply_text(
          text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown"
      )
    except Exception:
      pass


async def show_add_player_player_picker(update: Update, context: ContextTypes.DEFAULT_TYPE, side: str):
  context.user_data["add_to_match_side"] = side
  match_id = context.user_data.get("add_to_match_id")

  with sqlite3.connect("mafia_league.db") as conn:
    c = conn.cursor()
    c.execute("SELECT player_name FROM match_participants WHERE match_id = ?", (match_id,))
    existing = [r[0] for r in c.fetchall()]

    c.execute("SELECT name FROM players WHERE is_restricted = 0 ORDER BY name ASC")
    all_players = [r[0] for r in c.fetchall()]

  available_players = [p for p in all_players if p not in existing]

  if not available_players:
    keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data=f"add_to_match_sel:{match_id}")]]
    if update.callback_query:
      await update.callback_query.message.reply_text("❌ تمامی بازیکنان آزاد فعال هم‌اکنون در این مسابقه حضور دارند.", reply_markup=InlineKeyboardMarkup(keyboard))
    return

  keyboard = []
  row = []
  for p_name in available_players:
    label = p_name[:18] + ("..." if len(p_name) > 18 else "")
    row.append(InlineKeyboardButton(f"👤 {label}", callback_data=f"atm_player:{p_name}"))
    if len(row) == 2:
      keyboard.append(row)
      row = []
  if row:
    keyboard.append(row)

  keyboard.append([InlineKeyboardButton("🔙 بازگشت به انتخاب ساید", callback_data=f"add_to_match_sel:{match_id}")])
  text = f"➕ **افزودن به ساید [{side}]**\n\nبازیکن مورد نظر را انتخاب کنید:"

  if update.callback_query:
    try:
      await update.callback_query.message.reply_text(
          text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown"
      )
    except Exception:
      pass


async def execute_add_player_to_match(update: Update, context: ContextTypes.DEFAULT_TYPE, player_name: str):
  match_id = context.user_data.get("add_to_match_id")
  side = context.user_data.get("add_to_match_side")

  with sqlite3.connect("mafia_league.db") as conn:
    c = conn.cursor()
    c.execute("SELECT winning_side FROM match_history WHERE match_id = ?", (match_id,))
    row = c.fetchone()
    if not row:
      if update.callback_query:
        await update.callback_query.answer("❌ مسابقه یافت نشد.", show_alert=True)
      return
    winning_side = row[0]
    won = 1 if side == winning_side else 0

    c.execute(
        "INSERT INTO match_participants (match_id, player_name, side, won, is_unfair, is_artin, night1_shot, night1_out) VALUES (?, ?, ?, ?, 0, 0, 0, 0)",
        (match_id, player_name, side, won)
    )
    conn.commit()

  recalculate_all_players()

  msg = (
      f"🎉 **بازیکن با موفقیت به مسابقه اضافه شد!**\n\n"
      f"👤 نام بازیکن: **{player_name}**\n"
      f"🎭 ساید: **{side}**\n"
      f"🏆 وضعیت برد در این مسابقه: **{'پیروز ✅' if won == 1 else 'شکست ❌'}**\n\n"
      f"امتیازات و ریتینگ‌های لیگ مجدداً محاسبه و به‌روزرسانی شدند."
  )
  keyboard = [
      [InlineKeyboardButton("➕ افزودن بازیکن دیگر به این مسابقه", callback_data=f"add_to_match_sel:{match_id}")],
      [InlineKeyboardButton("🔙 بازگشت به پنل مدیریت", callback_data="open_admin_panel")]
  ]
  if update.callback_query:
    try:
      await update.callback_query.message.reply_text(
          msg, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown"
      )
    except Exception:
      pass


async def show_restrict_picker(update: Update, context: ContextTypes.DEFAULT_TYPE):
  if update.effective_user.id != ADMIN_ID:
    return

  with sqlite3.connect("mafia_league.db") as conn:
    c = conn.cursor()
    c.execute("SELECT user_id, name, is_restricted FROM players ORDER BY name ASC")
    rows = c.fetchall()

  if not rows:
    msg = "هنوز بازیکنی در سیستم ثبت نشده است."
    if update.callback_query:
      await update.callback_query.message.reply_text(msg)
    return

  keyboard = []
  row = []
  for u_id, p_name, restricted in rows:
    status_icon = "🔴 [محدود]" if restricted == 1 else "🟢 [آزاد]"
    label = f"{p_name[:14]} {status_icon}"
    row.append(
        InlineKeyboardButton(label, callback_data=f"toggle_restrict:{u_id}")
    )
    if len(row) == 2:
      keyboard.append(row)
      row = []
  if row:
    keyboard.append(row)

  keyboard.append([InlineKeyboardButton("🔙 بازگشت به پنل ادمین", callback_data="open_admin_panel")])
  text = (
      "🚫 **مدیریت محدودیت بازیکنان:**\n\n"
      "روی نام هر بازیکن کلیک کنید تا وضعیت محدودیت او تغییر کند (تغییر از آزاد به محدود و بالعکس).\n"
      "بازیکنان محدودشده در ثبت مسابقه و بخش آمار نمایش داده نخواهند شد."
  )
  if update.callback_query:
    try:
      await update.callback_query.message.reply_text(
          text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown"
      )
    except Exception:
      pass


async def toggle_player_restriction(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
  if update.effective_user.id != ADMIN_ID:
    return

  with sqlite3.connect("mafia_league.db") as conn:
    c = conn.cursor()
    c.execute("SELECT name, is_restricted FROM players WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    if not row:
      return
    name, current_status = row
    new_status = 0 if current_status == 1 else 1
    
    c.execute("UPDATE players SET is_restricted = ? WHERE user_id = ?", (new_status, user_id))
    conn.commit()

  status_text = "محدود شد 🔴" if new_status == 1 else "از محدودیت خارج شد 🟢"
  try:
    await update.callback_query.answer(f"بازیکن «{name}» {status_text}", show_alert=True)
  except Exception:
    pass

  await show_restrict_picker(update, context)


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
      bar = "🟩" * bar_len + "▫️" * (10 - bar_len)
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
        "SELECT name, raw_score, total_games, wins, losses, unfair_count, artin_count,"
        " advanced_skill_score FROM players"
    )
    players = c.fetchall()

    ranking = []
    for p in players:
      ranking.append((p[0], p[7], p[1], p[2], p[3], p[4], p[5], p[6]))

    ranking.sort(key=lambda x: (x[1], x[2], x[4]), reverse=True)

    for rank, p in enumerate(ranking, start=1):
      c.execute(
          """
                INSERT INTO season_archives (season, player_name, final_rank, final_rating, raw_score, total_games, wins, losses, unfair_count, artin_count, advanced_skill_score)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
              p[1],
          ),
      )

    c.execute("""
            UPDATE players SET
                raw_score = 0.0, total_games = 0, wins = 0, losses = 0,
                unfair_count = 0, artin_count = 0, citizen_games = 0, citizen_wins = 0,
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
  base_name = (
      user.full_name.strip()
      if user.full_name
      else (user.username or f"Player_{user_id}")
  )
  username = user.username or ""

  display_name = base_name
  success = False

  for attempt in range(5):
    try:
      with sqlite3.connect("mafia_league.db") as conn:
        c = conn.cursor()
        c.execute(
            "INSERT INTO players (user_id, username, name) VALUES (?, ?, ?)",
            (user_id, username, display_name),
        )
        conn.commit()
      success = True
      break
    except sqlite3.IntegrityError:
      random_suffix = random.randint(10, 99)
      display_name = f"{base_name}_{random_suffix}"

  if success:
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
  else:
    msg = (
        "ℹ️ ثبت‌نام با خطا مواجه شد. لطفاً دوباره تلاش کنید یا نام خود را با دستور `/rename` تغییر دهید."
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
            "صفحه بعد ➡", callback_data=f"pub_history_page:{page + 1}"
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
        "SELECT player_name, side, won, is_unfair, is_artin, night1_shot, night1_out FROM match_participants"
        " WHERE match_id = ?",
        (match_id,),
    )
    participants = c.fetchall()

  cits = [p[0] for p in participants if p[1] == "شهروند"]
  mafs = [p[0] for p in participants if p[1] == "مافیا"]
  inds = [p[0] for p in participants if p[1] == "مستقل"]
  unfairs = [p[0] for p in participants if p[3] == 1]
  artins = [p[0] for p in participants if p[4] == 1]
  
  n1_shot_player = next((p[0] for p in participants if p[5] == 1), None)
  n1_out_player = next((p[0] for p in participants if p[6] == 1), None)

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
        "SELECT player_name, side, won, is_unfair, is_artin, night1_shot, night1_out FROM match_participants"
        " WHERE match_id = ?",
        (match_id,),
    )
    participants = c.fetchall()

  cits = [p[0] for p in participants if p[1] == "شهروند"]
  mafs = [p[0] for p in participants if p[1] == "مافیا"]
  inds = [p[0] for p in participants if p[1] == "مستقل"]
  unfairs = [p[0] for p in participants if p[3] == 1]
  artins = [p[0] for p in participants if p[4] == 1]
  n1_shot_player = next((p[0] for p in participants if p[5] == 1), None)
  n1_out_player = next((p[0] for p in participants if p[6] == 1), None)

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
  app.add_handler(CommandHandler("players", players_list))
  app.add_handler(CommandHandler("table", table))
  app.add_handler(CommandHandler("advanced_table", advanced_table_cmd))
  app.add_handler(CommandHandler("unfair", unfair_leaderboard))
  app.add_handler(CommandHandler("artin", artin_leaderboard))
  app.add_handler(CommandHandler("teammates", teammates_leaderboard))
  app.add_handler(CommandHandler("streaks", streaks_leaderboard))
  app.add_handler(CommandHandler("shots_top", ask_shots_season_choice))
  app.add_handler(CommandHandler("stats", stats))
  app.add_handler(CommandHandler("vs", vs))
  app.add_handler(CommandHandler("sides", sides))
  app.add_handler(CommandHandler("scenarios", scenarios_stat))
  app.add_handler(CommandHandler("submit_game", submit_game))
  app.add_handler(CallbackQueryHandler(game_flow_handler))
  app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_messages))

  print("ربات لیگ با موفقیت فعال شد...")
  app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
  main()
