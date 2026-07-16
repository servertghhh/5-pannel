#!/usr/bin/env python3
"""
🤖 StexSMS Bot Unified Runner
----------------------------------
A highly robust Python combination of the panel monitoring/forwarding system
and the interactive Telegram Bot Controller.

This single file handles:
1. Multi-threaded background panel monitoring (CDRs & Active GetNum/Info numbers) for StexSMS.
2. Dynamic solving of mathematical captchas for logins.
3. Fully functional interactive Telegram Bot matching server.ts exactly.
4. Professional copy and exploration commands: /start, /getnum, /search, and /traffic.
5. Absolute error safety by sanitizing Telegram button schemas to prevent Status 400 errors.

Usage:
    python bot.py
"""

import os
import re
import sys
import time
import json
import random
import logging
import threading
from datetime import datetime
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
import firebase_admin
from firebase_admin import credentials, firestore

# Load env variables
load_dotenv()

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("StexSMSBot")

# Config Files
PANELS_FILE = "panels.json"
SERVICES_FILE = "services.json"
ADMIN_DB_FILE = "admin_db.json"
OWNER_ID = "1849126202" # Change this ID to your main Admin ID
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "8779046135:AAE_1iEJNQJtYulpETM8L9c2jbPWq6brM7c")

# Admin DB Logic (Tracks Users and Today's Numbers)
def load_admin_db():
    default_db = {"users": [], "today_date": datetime.now().strftime("%Y-%m-%d"), "today_numbers_count": 0, "admins": [OWNER_ID], "force_join_status": False, "force_join_channels": [], "otp_group_link": "", "forward_groups": [], "dxa_config": {"withdraw_group": "", "otp_reward": 0.0, "min_withdraw": 20.0, "methods": [], "max_concurrent": 3, "cooldown": 0}, "user_stats": {}, "active_numbers": {}}
    if os.path.exists(ADMIN_DB_FILE):
        try:
            with open(ADMIN_DB_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if "admins" not in data: data["admins"] = [OWNER_ID]
                if "force_join_status" not in data: data["force_join_status"] = False
                if "force_join_channels" not in data: data["force_join_channels"] = []
                if "otp_group_link" not in data: data["otp_group_link"] = ""
                if "forward_groups" not in data: data["forward_groups"] = []
                if "dxa_config" not in data: data["dxa_config"] = {"withdraw_group": "", "otp_reward": 0.0, "min_withdraw": 20.0, "methods": [], "max_concurrent": 3, "cooldown": 0}
                else:
                    data["dxa_config"].setdefault("max_concurrent", 3)
                    data["dxa_config"].setdefault("cooldown", 0)
                if "user_stats" not in data: data["user_stats"] = {}
                if "active_numbers" not in data: data["active_numbers"] = {}
                return data
        except: pass
    return default_db

def check_user_limits(chat_id, update_cooldown=True):
    cfg = admin_db.get("dxa_config", {})
    max_c = int(cfg.get("max_concurrent", 1))
    if max_c < 1: max_c = 1
    
    if str(chat_id) in admin_db.get("admins", [OWNER_ID]):
        return True, "", max_c
        
    cd = int(cfg.get("cooldown", 0))

    stats = admin_db.setdefault("user_stats", {}).setdefault(str(chat_id), {})
    stats.setdefault("otp_count", 0)
    stats.setdefault("balance", 0.0)
    stats.setdefault("last_req", 0)

    now = int(time.time())
    last_req = stats.get("last_req", 0)
    
    if cd > 0 and (now - last_req) < cd:
        rem = cd - (now - last_req)
        return False, f"⏳ Cooldown Active!\nPlease wait {rem} seconds before getting another number.", max_c

    if update_cooldown:
        stats["last_req"] = now
        save_admin_db()
        
    return True, "", max_c

def save_admin_db():
    try:
        with open(ADMIN_DB_FILE, "w", encoding="utf-8") as f:
            json.dump(admin_db, f, indent=2)
    except: pass

admin_db = load_admin_db()

# ----------------------------------------------------
# Firebase Cloud Firestore Setup (Direct File Emission - 100% Fix)
# ----------------------------------------------------
import json

db_firestore = None

def initialize_firebase():
    global db_firestore
    try:
        # ১. নতুন ওএম ফাইল (zihani-bot) ডেটা থেকে সরাসরি নিখুঁত ডিকশনারি অবজেক্ট তৈরি
        cred_json_data = {
          "type": "service_account",
          "project_id": "zihani-bot",
          "private_key_id": "284d9b7a6f662620833b5d4d2557d899bd488fba",
          "private_key": "-----BEGIN PRIVATE KEY-----\nMIIEvAIBADANBgkqhkiG9w0BAQEFAASCBKYwggSiAgEAAoIBAQCv++zFBoW7hJHS\n18jaI5rYzxPrUyrspfbs+P7FZygeqN5SJjVpxaMEvHAxO+8jM5tzwopukYZ4PlyF\n8U7GmG1U6D5dPbmnrn2QGvf/4hWsdmoBVRQU2uL/G2HcSYUh0grYGYdkmxAwE2Gw\nzUGogYD1L2RjPMr2Kq9zrbf0lPDbY2BZZNMRbuKepa2YXYaY3/Sq9Y+WMYXvaBzd\nQEbHW6Bce0mgOyM6Th25djfG/wBduyD4PId0HhJPkDt61ZqP103/jT/HwfS7rEIU\n5YnkGDlEfwhGzA7qJF0y/Sfh1I5wdOk0LoOZBlwBgKzgX15q68/RTlIGPXgzA6Bx\nBswoky1/AgMBAAECggEAUeiYiA+EGQYX9SF4G4es37JqHAJmnSSV7C/sLKbZtoN0\njpm4DJXvTRoDwfaaVDEF7ngihFn5U2f7GmB5ANgbMwSxWiaLja8aRAM5YICzA8VN\ni3c01IwYURJGlwglDdu8Ll6bdMjzXNz4gBjYsXwtMHExcTrvYGn3pYi6cP0NqZ4u\nDPp4sAO7HQ3WG/wG11iQwGnXvUQWh8j8eJSlDtwJTjEttlap0GHK25ICEUt6+So7\nYbjQxqIbSdl6bVIXWfSDzn9rdSx9b2EtMvM1a8E89xYbIgE7wz9ZWCaJDL0VyPCv\nVwQs3r3RjXq6a6mEPPyN8gGruN26sZs3IhATMNFjOQKBgQDmiuPZpXgBeLDP39Kf\n9Ch2lsN5BT511nHOy4NJjJN0pUxsJNDZZMJAmZmueD4ggPJsLYwXraVGwDaQH3vV\n8Vel6k8aIk9+L9+2EwNknBESBlqo6FQ8+yv2wFbP2dmRO5gUqpipeVfLN9sKRa0P\njCTDnvb+rrZPYrvY25KwaLxskwKBgQDDar6psBNJlFQHUxdrhUZM6kUA+r+M+xAz\n0iEu6watdqgUngPJwQnAQlszZfRTzRAbI94Uc5IQ5EkXdJdfYxJYQJa298VPVBeS\ncYS/3YL/QfF+oW3+hx5/aWTLvOYhCMwksqVnjo0NJ8a4Pt1ybO70ggpmrrCdP/yk\niK2hF5h65QKBgDT1rPffghzca8mlAg6KmQz8/zR61ulc9NHrgGJR78G5A0BIiM2X\nzuPmJR6mMqdm18mwAOGjmzcQirg680inY1oS5E79mMNFHiAGaB4hl+5LFWJ91HQZ\nwvSxJIAk7Eznor0En4M3A8sELsZCUUokCIIDr3u8CNdduAdOEXmC5d4PAoGAchO0\nbfadq8xtKUF2YIwSt//ifGnkvHYrxTSbrnoBEe48vJxp9bM88AFMoDqaYPlKt60+\njY3R7Q53JLwpScPaB67czL7jbiXXBORD7IVxXXWvdo7iWT2jrhlmgBEr/ojWM24e\nZM+ww8c+mHwKZiv1asMnMz4zV/jskVhAk9PkbYkCgYBZfHWc9SfxZf5GWcgJgI7R\nhfl1pG4N9UZZugDTeSOBc5V2xaNsunAoskbuFrC8V47fJA7xL0PnaLwDa9bLBN6K\n39lvfuKRU9fZA2Y2H2B5Rv4skrvUmDtgaAybdG8LZoFnVyUI5PYM7h5EVmDpGmHs\nuwiiOl/jTkjY8+epLjZF+g==\n-----END PRIVATE KEY-----\n",
          "client_email": "firebase-adminsdk-fbsvc@zihani-bot.iam.gserviceaccount.com",
          "client_id": "103881953882674833116",
          "auth_uri": "https://accounts.google.com/o/oauth2/auth",
          "token_uri": "https://oauth2.googleapis.com/token",
          "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
          "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/firebase-adminsdk-fbsvc%40zihani-bot.iam.gserviceaccount.com",
          "universe_domain": "googleapis.com"
        }

        # ২. কন্টেইনারে সরাসরি ফাইল রাইট করা হচ্ছে
        temp_cred_path = "firebase_cred.json"
        with open(temp_cred_path, "w", encoding="utf-8") as temp_file:
            json.dump(cred_json_data, temp_file, ensure_ascii=False, indent=2)

        # ৩. ফাইল পাথ থেকে নতুন সার্টিফিকেট লোড করা হচ্ছে
        if not firebase_admin._apps:
            cred = credentials.Certificate(temp_cred_path)
            firebase_admin.initialize_app(cred)
        else:
            try:
                firebase_admin.get_app()
            except ValueError:
                cred = credentials.Certificate(temp_cred_path)
                firebase_admin.initialize_app(cred)
                
        db_firestore = firestore.client()
        logger.info("🔥 Firebase Firestore (zihani-bot) initialized successfully via Direct File Emission!")
        return True, "Firebase connected successfully!"
    except Exception as e:
        db_firestore = None
        logger.error(f"❌ Firebase initialization failed: {e}")
        return False, str(e)

# প্রথমে রান করুন
initialize_firebase()

def restore_from_firestore():
    global admin_db
    if not db_firestore: return
    try:
        # ১. অ্যাডমিন কনফিগ রি-স্টোর
        cfg_doc = db_firestore.collection("DXA_System").document("Bot_Config").get()
        if cfg_doc.exists:
            data = cfg_doc.to_dict()
            if "dxa_config" in data: admin_db["dxa_config"] = data["dxa_config"]
            if "search_cfg" in data: admin_db["search_cfg"] = data["search_cfg"]
            if "admins" in data: admin_db["admins"] = data["admins"]
            if "otp_group_link" in data: admin_db["otp_group_link"] = data["otp_group_link"]
            if "forward_groups" in data: admin_db["forward_groups"] = data["forward_groups"]
            if "force_join_status" in data: admin_db["force_join_status"] = data["force_join_status"]
            if "force_join_channels" in data: admin_db["force_join_channels"] = data["force_join_channels"]
            if "banned_users" in data: admin_db["banned_users"] = data["banned_users"]
        
        # ২. ইউজার ব্যালেন্স ও OTP 리-স্টোর
        users_doc = db_firestore.collection("DXA_System").document("Users_Data").get()
        if users_doc.exists:
            data = users_doc.to_dict()
            if "active_users" in data:
                for uid, udata in data["active_users"].items():
                    stats = admin_db.setdefault("user_stats", {}).setdefault(uid, {})
                    stats["balance"] = udata.get("balance", 0.0)
                    stats["otp_count"] = udata.get("otp_count", 0)
                    if uid not in admin_db.setdefault("users", []): admin_db["users"].append(uid)
        save_admin_db()
        logger.info("Successfully restored essential data from Firestore on boot!")
    except Exception as e:
        logger.error(f"Failed to restore from Firestore: {e}")

# বট স্টার্ট হলেই ডেটা রিস্টোর হবে
restore_from_firestore()

def sync_essential_data_to_firestore():
    """Syncs only essential data: User Balances, Panels, Services, and Config to Firestore"""
    if not db_firestore: 
        return False, "Firebase is not initialized."
    try:
        # 1. User Balances & Stats
        stats = admin_db.get("user_stats", {})
        clean_stats = {}
        for uid, data in stats.items():
            if data.get("balance", 0.0) > 0 or data.get("otp_count", 0) > 0:
                clean_stats[uid] = {
                    "balance": data.get("balance", 0.0),
                    "otp_count": data.get("otp_count", 0)
                }
        
        db_firestore.collection("DXA_System").document("Users_Data").set({
            "total_users": len(admin_db.get("users", [])),
            "active_users": clean_stats,
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
        
        # 2. Panels Config (Cleaned without junk session cookies)
        clean_panels = []
        for p in panels:
            clean_panels.append({
                "id": p.get("id"),
                "name": p.get("name"),
                "status": p.get("status"),
                "url": p.get("url"),
                "getNumberUrl": p.get("getNumberUrl", ""),
                "getMessageUrl": p.get("getMessageUrl", "")
            })
            
        db_firestore.collection("DXA_System").document("Panels_Data").set({
            "panels": clean_panels,
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
        
        # 3. Services & Countries
        services_dict = load_services()
        db_firestore.collection("DXA_System").document("Services_Data").set({
            "services": services_dict,
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
        
        # 4. Admin Config
        db_firestore.collection("DXA_System").document("Bot_Config").set({
            "dxa_config": admin_db.get("dxa_config", {}),
            "search_cfg": admin_db.get("search_cfg", {}),
            "admins": admin_db.get("admins", []),
            "otp_group_link": admin_db.get("otp_group_link", ""),
            "forward_groups": admin_db.get("forward_groups", []),
            "force_join_status": admin_db.get("force_join_status", False),
            "force_join_channels": admin_db.get("force_join_channels", []),
            "banned_users": admin_db.get("banned_users", []),
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
        
        return True, "Successfully synced Balances, Panels, Services & Config to Firestore!"
    except Exception as e:
        return False, f"Firestore Sync Error: {e}"

# Telegram Secrets moved to the top

# Global variables/caches
user_conversations = {}
user_prompts = {}
sessions = {}
panel_backoff_until = {}  # Dynamic rate limit tracking
local_traffic_stats = {}  # 🚀 Fast Traffic Local Database
local_raw_logs_cache = {} # 🚀 Cumulative logs to prevent data loss

# Mapped country metadata
shortCountryCodes = {
    'CI': {'name': "Côte d'Ivoire (Ivory Coast)", 'flag': '🇨🇮'},
    'CM': {'name': 'Cameroon', 'flag': '🇨🇲'},
    'TG': {'name': 'Togo', 'flag': '🇹🇬'},
    'MG': {'name': 'Madagascar', 'flag': '🇲🇬'},
    'BJ': {'name': 'Benin', 'flag': '🇧🇯'},
    'GN': {'name': 'Guinea', 'flag': '🇬🇳'},
    'GA': {'name': 'Gabon', 'flag': '🇬🇦'},
    'CF': {'name': 'Central African Republic', 'flag': '🇨🇫'},
    'CG': {'name': 'Congo', 'flag': '🇨🇬'},
    'CD': {'name': 'DR Congo', 'flag': '🇨🇩'},
    'SN': {'name': 'Senegal', 'flag': '🇸🇳'},
    'ML': {'name': 'Mali', 'flag': '🇲🇱'},
    'TJ': {'name': 'Tajikistan', 'flag': '🇹🇯'},
    'BF': {'name': 'Burkina Faso', 'flag': '🇧🇫'},
    'NE': {'name': 'Niger', 'flag': '🇳🇪'},
    'TD': {'name': 'Chad', 'flag': '🇹🇩'},
}

prefixCountryMap = {
    '237': 'Cameroon 🇨🇲',
    '225': 'Ivory Coast 🇨🇮',
    '228': 'Togo 🇹🇬',
    '261': 'Madagascar 🇲🇬',
    '229': 'Benin 🇧🇯',
    '224': 'Guinea 🇬🇳',
    '241': 'Gabon 🇬🇦',
    '236': 'Central African Republic 🇨🇫',
    '242': 'Congo 🇨🇬',
    '243': 'DR Congo 🇨🇩',
    '221': 'Senegal 🇸🇳',
    '223': 'Mali 🇲🇱',
    '992': 'Tajikistan 🇹🇯',
    '7992': 'Tajikistan 🇹🇯',
    '226': 'Burkina Faso 🇧🇫',
    '227': 'Niger 🇳🇪',
    '235': 'Chad 🇹🇩',
}

# ----------------------------------------------------
# Utilities
# ----------------------------------------------------

# ----------------------------------------------------
# Premium Emoji Database
# ----------------------------------------------------
PREMIUM_EMOJIS = {
    "dxa": "<tg-emoji emoji-id='5334763399299506604'>😒</tg-emoji>",
    "time": "<tg-emoji emoji-id='5336983442125001376'>🕓</tg-emoji>",
    "otp": "<tg-emoji emoji-id='5337255927735163754'>🔐</tg-emoji>",
    "fire": "<tg-emoji emoji-id='5337267511261960341'>🔥</tg-emoji>",
    "king": "<tg-emoji emoji-id='5353032893096567467'>👑</tg-emoji>",
    "dashboard": "<tg-emoji emoji-id='5352877703043258544'>📊</tg-emoji>",
    "user": "<tg-emoji emoji-id='5352861489541714456'>👤</tg-emoji>",
    "rocket": "<tg-emoji emoji-id='5352597830089347330'>🚀</tg-emoji>",
    "gem": "<tg-emoji emoji-id='5352838545826420397'>💎</tg-emoji>",
    "done": "<tg-emoji emoji-id='5352694861990501856'>✅</tg-emoji>",
    "error": "<tg-emoji emoji-id='5420130255174145507'>❌</tg-emoji>",
    "search": "<tg-emoji emoji-id='5463352748751753567'>🔍</tg-emoji>",
    "number": "<tg-emoji emoji-id='5337132498965010628'>🍏</tg-emoji>",
    "phone": "<tg-emoji emoji-id='5355208818017999139'>📱</tg-emoji>",
    "warn": "<tg-emoji emoji-id='5336944168944047463'>⚠️</tg-emoji>",
    "wait": "<tg-emoji emoji-id='5337172996211648018'>⏳</tg-emoji>",
    "note": "<tg-emoji emoji-id='5395444784611480792'>📝</tg-emoji>",
    "world": "<tg-emoji emoji-id='5336972142066047577'>🌐</tg-emoji>",
    "gear": "<tg-emoji emoji-id='5420155432272438703'>⚙️</tg-emoji>",
    "back": "<tg-emoji emoji-id='5267490665117275176'>⬅️</tg-emoji>"
}

RAW_APP_EMOJIS = {
    "facebook": "5334807341109908955", "whatsapp": "5334759662677957452",
    "telegram": "5337010556253543833", "imo": "5337155807752524558",
    "instagram": "5334868205091459431", "apple": "5334637951894722661",
    "google": "5335010201005231986", "microsoft": "5334880948259427772",
    "tiktok": "5339213256001102461", "amazon": "4995019580536524226",
    "twitter": "5215726959056662534", "snapchat": "5359441366554255082",
    "netflix": "6255738712664050133", "linkedin": "6224222994265279792",
    "discord": "5116246243646898866", "viber": "5463060437572528782",
    "wechat": "5782757599560602950", "line": "5399818044866327279",
    "paypal": "5776103539872896061", "uber": "5298715455316303708",
    "bkash": "5348469219761626211", "rocket": "5352597830089347330",
    "binance": "5348212415077064131", "bybit": "5348372939479751825",
    "gmail": "5348494358205207761", "messenger": "5348486915026884464",
    "chrome": "5346311574221000149", "chatgpt": "5296516998996445955",
    "github": "5417836094098007862", "canva": "5111661409008092227"
}

def get_pemoji(key, fallback=""):
    return PREMIUM_EMOJIS.get(key.lower(), fallback)

def load_premium_apps():
    if os.path.exists("premium_apps.json"):
        try:
            with open("premium_apps.json", "r", encoding="utf-8") as f: return json.load(f)
        except: pass
    return {}

def load_premium_flags():
    if os.path.exists("premium_flags.json"):
        try:
            with open("premium_flags.json", "r", encoding="utf-8") as f: return json.load(f)
        except: pass
    return {}

def process_premium_txt(text_content):
    apps_data = load_premium_apps()
    flags_data = load_premium_flags()
    count_apps = 0
    count_flags = 0
    
    for line in text_content.strip().split('\n'):
        line = line.strip()
        if not line or "{" not in line: continue
        try:
            json_start = line.rfind("{")
            info = json.loads(line[json_start:])
            prefix = line[:json_start].strip()
            
            # Country/Flag Text Regex Parser
            match = re.search(r'\((\d+)\)\(([A-Z0-9]+)\)(.*)', prefix)
            if match:
                phone_code = match.group(1)
                short_code = match.group(2)
                raw_name = match.group(3).strip()
                first_space = raw_name.find(" ")
                
                flags_data[short_code] = {
                    "phone_code": phone_code,
                    "flag": raw_name[:first_space] if first_space != -1 else "🏳️",
                    "name": raw_name[first_space:].strip() if first_space != -1 else raw_name,
                    "id": info.get("id", "5336972142066047577")
                }
                count_flags += 1
            else:
                # Apps/Service Parser
                app_name = re.sub(r'^[^\w\s]+', '', prefix).strip().lower()
                if app_name:
                    apps_data[app_name] = info.get("id", "5336879280578138635")
                    count_apps += 1
        except: pass
        
    with open("premium_apps.json", "w", encoding="utf-8") as f: json.dump(apps_data, f, indent=2)
    with open("premium_flags.json", "w", encoding="utf-8") as f: json.dump(flags_data, f, indent=2)
    return count_apps, count_flags

def get_country_info(short_code):
    dyn_flags = load_premium_flags()
    
    # 🚀 Handle if the admin inputted a dialing code (e.g. 225, 880) instead of short code
    if str(short_code).isdigit() or str(short_code).startswith("+"):
        clean_phone = str(short_code).replace("+", "").strip()
        for code, info in dyn_flags.items():
            if info.get("phone_code") == clean_phone:
                return info
        
        resolved_code = get_country_code(clean_phone)
        if resolved_code != 'Unknown':
            short_code = resolved_code

    if short_code in dyn_flags:
        return dyn_flags[short_code]
    return shortCountryCodes.get(short_code, {"name": short_code, "flag": "🏳️", "id": "5336972142066047577"})

def get_app_raw_id(app_name):
    dyn_apps = load_premium_apps()
    name_lower = app_name.lower()
    
    for key, val in dyn_apps.items():
        if key in name_lower: return val
            
    for key, val in RAW_APP_EMOJIS.items():
        if key in name_lower: return val
    return "5336879280578138635" # Default 🖥 Other Service

def get_app_pemoji(app_name):
    raw_id = get_app_raw_id(app_name)
    return f"<tg-emoji emoji-id='{raw_id}'>🖥</tg-emoji>"

def escape_html(text):
    if not text:
        return ""
    return str(text).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

def mask_number(num):
    if not num:
        return ""
    num_str = str(num).replace("+", "").strip()
    if len(num_str) <= 6:
        return num_str
    first_3 = num_str[:3]
    last_3 = num_str[-3:]
    # এখানে ❖ যোগ করা হলো
    return f"{first_3}❖DXA❖{last_3}"

def extract_otp(text):
    if not text:
        return "No OTP Found"
    
    # ১. হাইফেন বা স্পেস ছাড়া সরাসরি ৪-৮ ডিজিট (যেমন: 123456)
    match = re.search(r'\b\d{4,8}\b', text)
    if match: return match.group(0)
    
    # ২. হাইফেন যুক্ত ওটিপি (যেমন: 123-456)
    match = re.search(r'\b\d{3}-\d{3}\b', text)
    if match: return match.group(0).replace("-", "")

    # ৩. স্পেস যুক্ত ওটিপি যা Instagram এ থাকে (যেমন: 123 456)
    match = re.search(r'\b\d{3}\s\d{3}\b', text)
    if match: return match.group(0).replace(" ", "")

    # ৪. টেক্সটের ভেতরে থাকা ওটিপি খোঁজা
    matches = re.findall(r'(\b\d{3,4}-\d{3,4}\b)|(\b\d{4,8}\b)', text)
    if matches:
        first_match = next((item for item in matches[0] if item), "")
        return first_match.replace("-", "").replace(" ", "")

    return "No OTP Found"

def normalize_base_url(input_url):
    url = input_url.strip()
    if not re.match(r'^https?://', url, re.IGNORECASE):
        url = 'https://' + url
        
    if '/#/' in url:
        url = url.split('/#/')[0]
    elif '/#' in url:
        url = url.split('/#')[0]
        
    while url.endswith('/'):
        url = url[:-1]
        
    changed = True
    while changed:
        changed = False
        lower = url.lower()
        if lower.endswith('/mauth/login'):
            url = url[:-12]
            changed = True
        elif lower.endswith('/mauth'):
            url = url[:-6]
            changed = True
        elif lower.endswith('/auth/login'):
            url = url[:-11]
            changed = True
        elif lower.endswith('/auth'):
            url = url[:-5]
            changed = True
        elif lower.endswith('/login.php'):
            url = url[:-10]
            changed = True
        elif lower.endswith('/login'):
            url = url[:-6]
            changed = True
        elif lower.endswith('/signin'):
            url = url[:-7]
            changed = True
        elif lower.endswith('/client/smscdrstats'):
            url = url[:-19]
            changed = True
        elif lower.endswith('/cdrs'):
            url = url[:-5]
            changed = True
        elif lower.endswith('/app'):
            url = url[:-4]
            changed = True
        elif lower.endswith('/dashboard'):
            url = url[:-10]
            changed = True
            
        while url.endswith('/'):
            url = url[:-1]
            changed = True
            
    return url

# Time Helpers Matching JS CEST timezone logic
def parse_time_to_seconds(time_str):
    if not time_str:
        return 0
    parts = time_str.strip().split(':')
    h = int(parts[0]) if parts[0].isdigit() else 0
    m = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 0
    s = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else 0
    return h * 3600 + m * 60 + s

def get_seconds_difference(time1, time2):
    t1 = parse_time_to_seconds(time1)
    t2 = parse_time_to_seconds(time2)
    diff = abs(t1 - t2)
    if diff > 43200:
        diff = 86400 - diff
    return diff

def get_current_cest_time():
    # Fetch UTC timezone then add CEST (+2)
    now_utc = datetime.utcnow()
    # Simple hours addition for CEST
    hour = (now_utc.hour + 2) % 24
    return f"{hour:02d}:{now_utc.minute:02d}:{now_utc.second:02d}"

# ----------------------------------------------------
# DB Load and Save
# ----------------------------------------------------

def load_services():
    default_services = {}
    if os.path.exists(SERVICES_FILE):
        try:
            with open(SERVICES_FILE, "r", encoding="utf-8") as f:
                content = json.load(f)
                if isinstance(content, dict):
                    return content
                elif isinstance(content, list): # Purgatory Migration
                    return {"stexsms": content}
        except Exception as e:
            logger.error(f"Error reading services.json: {e}")
            
    try:
        with open(SERVICES_FILE, "w", encoding="utf-8") as f:
            json.dump(default_services, f, indent=2, ensure_ascii=False)
        return default_services
    except Exception as e:
        logger.error(f"Error saving default services: {e}")
    return default_services

def save_services(services_dict):
    try:
        with open(SERVICES_FILE, "w", encoding="utf-8") as f:
            json.dump(services_dict, f, indent=2, ensure_ascii=False)
        # 🚀 সার্ভিস সেভ হওয়ার সাথে সাথেই ফায়ারবেসে সিঙ্ক করার ব্যাকগ্রাউন্ড থ্রেড
        threading.Thread(target=sync_essential_data_to_firestore, daemon=True).start()
    except Exception as e:
        logger.error(f"Error saving services.json: {e}")

def load_panels():
    default_panels = [
        {
            "id": "voltx_api", "name": "Voltx API", "url": "https://2oo9.cloud/api/MXS47FLFX0U/project/tetragonexvoltxsms/@public/api", 
            "username": "API", "password": "MKJGS2MSZYB", 
            "getNumberUrl": "https://2oo9.cloud/api/MXS47FLFX0U/project/tetragonexvoltxsms/@public/api/getnum", 
            "getMessageUrl": "https://2oo9.cloud/api/MXS47FLFX0U/project/tetragonexvoltxsms/@public/api/success-otp", 
            "trafficUrl": "https://2oo9.cloud/api/MXS47FLFX0U/project/tetragonexvoltxsms/@public/api/console", 
            "sessionCookie": "MKJGS2MSZYB", "lastSeenCDRId": None, "status": "Initializing...", "lastSeenGetnumIds": []
        },
        {
            "id": "stexsms", "name": "Stex SMS", "url": "https://stexsms.com/mauth/login", 
            "username": "asikisbackagain@gmail.com", "password": "@@Admin@@00", 
            "getNumberUrl": "https://stexsms.com/mapi/v1/mdashboard/getnum/number", 
            "getMessageUrl": "https://stexsms.com/mapi/v1/mdashboard/getnum/info", 
            "trafficUrl": "https://stexsms.com/mapi/v1/mdashboard/console/info", 
            "sessionCookie": "", "lastSeenCDRId": None, "status": "Initializing...", "lastSeenGetnumIds": []
        },
        {
            "id": "xmint", "name": "X mint", "url": "https://x.mnitnetwork.com/mauth/login", 
            "username": "pcmastersami@gmail.com", "password": "alihasan#", 
            "getNumberUrl": "https://x.mnitnetwork.com/mapi/v1/mdashboard/getnum/number", 
            "getMessageUrl": "https://x.mnitnetwork.com/mapi/v1/mdashboard/getnum/info", 
            "trafficUrl": "https://x.mnitnetwork.com/mapi/v1/mdashboard/console/info", 
            "sessionCookie": "", "lastSeenCDRId": None, "status": "Initializing...", "lastSeenGetnumIds": []
        },
        {
            "id": "nexa", "name": "Nexa Panel", "url": "http://63.141.255.227/app/login", 
            "username": "asikisbackagain@gmail.com", "password": "@@Asik@@2.0", 
            "getNumberUrl": "http://63.141.255.227/api/user/request-number", 
            "getMessageUrl": "http://63.141.255.227/api/user/numbers?page=1", 
            "trafficUrl": "http://63.141.255.227/api/user/console-log", 
            "sessionCookie": "", "lastSeenCDRId": None, "status": "Initializing...", "lastSeenGetnumIds": []
        },
        {
            "id": "mk", "name": "Mk", "url": "https://mknetworkbd.com/login.php", 
            "username": "01995743604", "password": "Rakib9090", 
            "getNumberUrl": "https://mknetworkbd.com/API/api_handler_test.php", 
            "getMessageUrl": "https://mknetworkbd.com/API/api_handler_test.php?action=get_history&page=1&limit=20", 
            "trafficUrl": "https://mknetworkbd.com/console.php?ajax=1", 
            "sessionCookie": "", "lastSeenCDRId": None, "status": "Initializing...", "lastSeenGetnumIds": []
        }
    ]
    if not os.path.exists(PANELS_FILE):
        save_panels_to_file(default_panels)
        return default_panels
    try:
        with open(PANELS_FILE, "r", encoding="utf-8") as f:
            list_panels = json.load(f)
            if not list_panels:
                list_panels = default_panels
            else:
                existing_ids = [p.get("id", "") for p in list_panels]
                for dp in default_panels:
                    if dp["id"] not in existing_ids:
                        list_panels.append(dp)
            for p in list_panels:
                p.setdefault("id", p.get("name", "panel").lower().replace(" ", "-"))
                p.setdefault("sessionCookie", "")
                p.setdefault("lastSeenCDRId", None)
                p.setdefault("lastSeenGetnumIds", [])
                p.setdefault("status", "Initializing...")
            return list_panels
    except Exception as e:
        logger.error(f"Failed to read panels.json: {e}")
        return default_panels

def save_panels_to_file(panels_list):
    try:
        with open(PANELS_FILE, "w", encoding="utf-8") as f:
            json.dump(panels_list, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Failed to save panels.json: {e}")

# Global Active Config List
panels = load_panels()

def get_session(panel_id):
    if panel_id not in sessions:
        try:
            import cloudscraper
            s = cloudscraper.create_scraper(browser={'browser': 'chrome', 'platform': 'windows', 'desktop': True})
        except ImportError:
            s = requests.Session()
        s.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        })
        sessions[panel_id] = s
    return sessions[panel_id]

# ----------------------------------------------------
# Telegram API - Sanitized for zero Bad Request 400
# ----------------------------------------------------

def clean_keyboard(reply_markup):
    return reply_markup

def call_telegram(method, payload):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/{method}"
    try:
        if "reply_markup" in payload:
            payload["reply_markup"] = clean_keyboard(payload["reply_markup"])
        res = requests.post(url, json=payload, timeout=15)
        return res.json()
    except Exception as e:
        logger.error(f"Telegram {method} raw execution exception: {e}")
        return None

def send_bot_message(chat_id, text, reply_markup=None):
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }
    if reply_markup:
        payload["reply_markup"] = reply_markup
    return call_telegram("sendMessage", payload)

def edit_bot_message(chat_id, message_id, text, reply_markup=None):
    payload = {
        "chat_id": chat_id,
        "message_id": message_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }
    if reply_markup:
        payload["reply_markup"] = reply_markup
    return call_telegram("editMessageText", payload)

def answer_callback(callback_query_id, text=None, show_alert=False):
    payload = {"callback_query_id": callback_query_id}
    if text:
        payload["text"] = text
        if show_alert:
            payload["show_alert"] = True
    call_telegram("answerCallbackQuery", payload)

def get_otp_group_btn():
    link = admin_db.get("otp_group_link", "").strip()
    if link and link.startswith("http"):
        return {"text": " Otp Group", "url": link, "style": "primary", "icon_custom_emoji_id": "5420145051336485498"}
    return {"text": " Otp Group", "callback_data": "usr_otp_grp", "style": "primary", "icon_custom_emoji_id": "5420145051336485498"}

def get_service_short_code(name, sms_body=""):
    text = (str(name) + " " + str(sms_body)).lower()
    if 'whatsapp' in text or 'wa' in text: return 'WS'
    if 'facebook' in text or 'fb' in text: return 'FB'
    if 'telegram' in text or 'tg' in text: return 'TG'
    if 'instagram' in text or 'ig' in text: return 'IG'
    if 'tiktok' in text or 'tt' in text: return 'TT'
    if 'google' in text: return 'GG'
    if 'microsoft' in text: return 'MS'
    if 'imo' in text: return 'IMO'
    if 'viber' in text: return 'VI'
    if 'snapchat' in text: return 'SC'
    if 'wechat' in text: return 'WC'
    if 'line' in text: return 'LN'
    if 'twitter' in text or ' x ' in text: return 'TW'
    if 'paypal' in text: return 'PP'
    if 'discord' in text: return 'DC'
    if 'amazon' in text: return 'AMZ'
    return 'OTP'

def send_to_telegram(message, otp=None, quick_range=None, full_sms_body=None, svc_em_id=None, buyer_chat_id=None, unmasked_number=None, svc_short=None, flag=None):
    fwd_groups = admin_db.get("forward_groups", [])
        
    base_keyboard = []
    
    # ওটিপি বাটন লজিক: ওটিপি না থাকলে "Copy SMS" আসবে
    if full_sms_body:
        has_otp = otp and otp != "No OTP Found"
        btn_label = f" {otp}" if has_otp else " Copy SMS"
        copy_val = otp if has_otp else full_sms_body
        
        otp_btn = {
            "text": btn_label,
            "copy_text": {"text": copy_val},
            "style": "success",
            "icon_custom_emoji_id": svc_em_id if svc_em_id else "5337255927735163754"
        }
        base_keyboard.append([otp_btn])

    if full_sms_body:
        base_keyboard.append([{
            "text": " Full Message",
            "copy_text": {"text": full_sms_body},
            "style": "primary",
            "icon_custom_emoji_id": "5337302974806922068"
        }])

    # --- Send to Inbox (Buyer) ---
    if buyer_chat_id and unmasked_number and svc_short and flag:
        # কান্ট্রি কোড থেকে প্রিমিয়াম ফ্ল্যাগ আইডি বের করা
        c_code_for_inbox = get_country_code(unmasked_number)
        c_info_inbox = get_country_info(c_code_for_inbox)
        f_id_inbox = c_info_inbox.get('id', '5336972142066047577')
        p_flag_inbox = f"<tg-emoji emoji-id='{f_id_inbox}'>{flag}</tg-emoji>"

        inbox_msg = (
            f"╔═════════════╗\n"
            f"║ <tg-emoji emoji-id='{svc_em_id if svc_em_id else '5336879280578138635'}'>💬</tg-emoji> #{svc_short} {p_flag_inbox} <code>{unmasked_number}</code>\n"
            f"╚═════════════╝"
        )
        
        inbox_payload = {
            "chat_id": buyer_chat_id,
            "text": inbox_msg,
            "parse_mode": "HTML",
            "disable_web_page_preview": True
        }
        if base_keyboard:
            inbox_payload["reply_markup"] = {"inline_keyboard": base_keyboard}
        call_telegram("sendMessage", inbox_payload)

    # --- Send to Groups ---
    for grp in fwd_groups:
        chat_id = grp.get("id")
        custom_btns = grp.get("buttons", [])
        
        payload = {
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "HTML",
            "disable_web_page_preview": True
        }
        
        group_keyboard = [row for row in base_keyboard]
        
        if custom_btns:
            btn_row = []
            for btn in custom_btns:
                btn_text = btn.get("text", "")
                btn_url = btn.get("url", "")
                
                btn_obj = {"text": btn_text, "url": btn_url}
                
                # 🚀 Priority 1: Use extracted premium emoji ID from DB
                if btn.get("emoji_id"):
                    btn_obj["icon_custom_emoji_id"] = btn.get("emoji_id")
                    btn_obj["style"] = "primary"
                else:
                    # 🚀 Fallback logic for old buttons or normal text
                    match = re.search(r'^([^\w\s]+)\s*(.*)', btn_text)
                    if match:
                        app_em_id = get_app_raw_id(match.group(2).strip())
                        if app_em_id and app_em_id != "5336879280578138635":
                            btn_obj["icon_custom_emoji_id"] = app_em_id
                            btn_obj["style"] = "primary"
                            btn_obj["text"] = f" {match.group(2).strip()}"
                
                btn_row.append(btn_obj)
                if len(btn_row) == 2:
                    group_keyboard.append(btn_row)
                    btn_row = []
            if btn_row:
                group_keyboard.append(btn_row)
                
        if group_keyboard:
            payload["reply_markup"] = {"inline_keyboard": group_keyboard}

        call_telegram("sendMessage", payload)

def process_and_send_sms(panel_name, raw_number, app_name, msg_body):
    otp = extract_otp(msg_body)
    masked_number = mask_number(raw_number)
    clean_num = str(raw_number).replace("+", "").strip()
    c_code = get_country_code(clean_num)
    c_info = get_country_info(c_code)
    flag = c_info.get('flag', '🏳️')
    
    svc_short = get_service_short_code(app_name, msg_body)
    
    # Smart Service Emoji Finder
    actual_app_name = str(app_name).strip() if app_name else ""
    if not actual_app_name:
        mb_lower = msg_body.lower()
        if "facebook" in mb_lower or "fb" in mb_lower: actual_app_name = "facebook"
        elif "whatsapp" in mb_lower or "wa" in mb_lower: actual_app_name = "whatsapp"
        elif "telegram" in mb_lower: actual_app_name = "telegram"
        elif "instagram" in mb_lower: actual_app_name = "instagram"
        elif "tiktok" in mb_lower: actual_app_name = "tiktok"
        elif "google" in mb_lower: actual_app_name = "google"
        elif "microsoft" in mb_lower: actual_app_name = "microsoft"
        else: actual_app_name = svc_short
        
    svc_em_id = get_app_raw_id(actual_app_name)
    
    # গ্রুপ মেসেজের জন্য প্রিমিয়াম ফ্ল্যাগ তৈরি
    f_id_grp = c_info.get('id', '5336972142066047577')
    premium_flag_grp = f"<tg-emoji emoji-id='{f_id_grp}'>{flag}</tg-emoji>"

    # নতুন মাস্কিং স্টাইল অনুযায়ী স্প্লিট করা হচ্ছে
    parts = masked_number.split("❖DXA❖")
    if len(parts) == 2:
        linked_number = f"<code>{parts[0]}</code>❖<a href='tg://user?id=8570538705'>DXA</a>❖<code>{parts[1]}</code>"
    else:
        linked_number = f"<code>{masked_number}</code>"
    
    group_message = (
        f"╔═════════════╗\n"
        f"║ <tg-emoji emoji-id='{svc_em_id}'>💬</tg-emoji> #{svc_short} {premium_flag_grp} {linked_number}\n"
        f"╚═════════════╝"
    )
    
    buyer_chat_id = admin_db.get("active_numbers", {}).get(clean_num)
    if otp and otp != "No OTP Found" and buyer_chat_id:
        stats = admin_db.setdefault("user_stats", {}).setdefault(str(buyer_chat_id), {})
        stats.setdefault("otp_count", 0)
        stats.setdefault("balance", 0.0)
        cfg = admin_db.get("dxa_config", {})
        stats["otp_count"] += 1
        stats["balance"] += float(cfg.get("otp_reward", 0.0))
        if stats.get("active_reqs"): stats["active_reqs"].pop(0)
        save_admin_db()
        
    quick_range = get_range_from_number(clean_num)
    send_to_telegram(group_message, otp, quick_range, msg_body, svc_em_id, buyer_chat_id, clean_num, svc_short, flag)

# ----------------------------------------------------
# Math Captcha & Authentication Solvers
# ----------------------------------------------------

def is_php_panel(panel):
    if not panel or not panel.get("url"): return False
    url_lower = panel["url"].lower()
    name_lower = panel.get("name", "").lower()
    return (".php" in url_lower) or ("mknetwork" in url_lower) or ("mk" in name_lower) or ("php" in name_lower)

def is_nexa_otp(panel):
    if not panel or not panel.get("url"): return False
    url_lower = panel["url"].lower()
    name_lower = panel.get("name", "").lower()
    return ("nexa" in name_lower) or ("63.141.255.227" in url_lower) or ("nexaotp" in url_lower)

def is_tetragon(panel):
    if not panel or not panel.get("url"): return False
    url_lower = panel["url"].lower()
    name_lower = panel.get("name", "").lower()
    return ("voltxsms" in url_lower) or ("2oo9.cloud" in url_lower) or ("voltex" in url_lower) or ("vortex" in url_lower) or ("voltx" in url_lower)

def is_voltx_api(panel):
    if not panel or not panel.get("url"): return False
    url_lower = panel["url"].lower()
    id_lower = panel.get("id", "").lower()
    return "@public/api" in url_lower or "voltx_api" in id_lower or "voltx api" in id_lower

def is_nextjs_panel(panel):
    if not panel or not panel.get("url"): return False
    if is_nexa_otp(panel) or is_tetragon(panel) or is_php_panel(panel) or is_voltx_api(panel): return False
    return True

def get_tetragon_sid(panel):
    if not panel or not panel.get("sessionCookie"): return "M0000000001"
    try:
        parts = panel["sessionCookie"].split('.')
        if len(parts) > 1:
            import base64
            payload_b64 = parts[1]
            payload_b64 += "=" * ((4 - len(payload_b64) % 4) % 4)
            payload_json = base64.b64decode(payload_b64).decode('utf-8', errors='ignore')
            payload_obj = json.loads(payload_json)
            if payload_obj and payload_obj.get("sid"): return payload_obj["sid"]
    except: pass
    return "M0000000001"

def run_node_codec(action, data_str, key=""):
    import subprocess, os, urllib.request
    possible_paths = ["/app/applet/codec_bg.js", os.path.join(os.getcwd(), "codec_bg.js"), "codec_bg.js"]
    codec_path = None
    for p in possible_paths:
        if os.path.exists(p):
            codec_path = os.path.abspath(p)
            break

    if not codec_path:
        local_target_path = os.path.join(os.getcwd(), "codec_bg.js")
        try:
            mirrors = ["https://raw.githubusercontent.com/VortexSMS/Mirror/main/codec_bg.js", "https://2oo9.cloud/api/MXS47FLFX0U/project/tetragonexvoltxsms/codec_bg.js"]
            for url in mirrors:
                try:
                    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                    with urllib.request.urlopen(req, timeout=15) as response:
                        with open(local_target_path, 'wb') as out_file: out_file.write(response.read())
                    codec_path = os.path.abspath(local_target_path)
                    break
                except: pass
        except: pass
    if not codec_path: codec_path = "/app/applet/codec_bg.js"
    codec_path = codec_path.replace("\\", "\\\\")
    js_code = f"""
    let path = '{codec_path}'.replace(/\\\\/g, '/');
    if (!path.startsWith('/')) path = '/' + path;
    import('file://' + path).then(codec => {{
        const binary = codec.t();
        codec.n({{ module_or_path: binary }}).then(() => {{
            const payloadStr = process.argv[2];
            const keyVal = process.argv[3] || '';
            if ('{action}' === 'encode') {{ console.log(codec.i(payloadStr, keyVal)); }}
            else {{ console.log(codec.r(payloadStr, keyVal)); }}
            process.exit(0);
        }}).catch(err => process.exit(1));
    }}).catch(err => process.exit(1));
    """
    try:
        res = subprocess.run(["node", "-e", js_code, data_str, key], capture_output=True, text=True, timeout=15)
        if res.returncode == 0: return res.stdout.strip()
        return None
    except: return None

def get_clean_base_url(panel, base_url):
    if panel.get("resolvedBaseUrl"): return panel["resolvedBaseUrl"].rstrip('/')
    return base_url.split('#')[0].rstrip('/')

def login_to_panel(panel, force=False):
    panel_id = panel["id"]
    now = time.time()
    if not force and panel_id in panel_backoff_until and now < panel_backoff_until[panel_id]:
        logger.info(f"[{panel['name']}] Login requested skipped due to backoff.")
        return False

    session = get_session(panel_id)
    baseUrl = normalize_base_url(panel["url"])

    # 0. Voltx API
    if is_voltx_api(panel):
        panel["status"] = "Running (API)"
        panel["sessionCookie"] = panel.get("password", "MKJGS2MSZYB")
        save_panels_to_file(panels)
        return True

    # 1. Tetragon / Voltex Panel
    if is_tetragon(panel):
        logger.info(f"[{panel['name']}] Initiating dedicated Tetragon login sequence...")
        try:
            payload = {"email": panel["username"], "password": panel["password"], "remember": False}
            encoded_body = run_node_codec("encode", json.dumps(payload), "M0000000001")
            if not encoded_body: raise Exception("Failed to encode payload using Node codec")
            
            post_url = "https://2oo9.cloud/api/MXS47FLFX0U/project/tetragonexvoltxsms/@auth/login"
            headers = {"Content-Type": "text/plain; charset=utf-8", "User-Agent": "Mozilla/5.0", "Referer": "https://voltxsms.com/m29/", "Origin": "https://voltxsms.com"}
            res = requests.post(post_url, data=encoded_body, headers=headers, timeout=20)
            
            if res.status_code == 200 and res.text:
                decoded_text = run_node_codec("decode", res.text.strip(), "M0000000001")
                if decoded_text:
                    decoded_obj = json.loads(decoded_text)
                    if decoded_obj and decoded_obj.get("meta", {}).get("code") == 200 and decoded_obj.get("data", {}).get("session_token"):
                        logger.info(f"[{panel['name']}] Tetragon Login successful!")
                        panel["sessionCookie"] = decoded_obj["data"]["session_token"]
                        panel["status"] = "Running (LoggedIn)"
                        save_panels_to_file(panels)
                        return True
            raise Exception(f"Invalid login response: status {res.status_code}")
        except Exception as err:
            logger.error(f"[{panel['name']}] Tetragon Login failed: {err}")
            panel["status"] = "Error (Login Failed)"
            save_panels_to_file(panels)
            return False

    # 2. PHP / MK Panel
    elif is_php_panel(panel):
        logger.info(f"[{panel['name']}] Initiating dedicated PHP/MK login sequence...")
        clean_base = get_clean_base_url(panel, baseUrl)
        login_url = panel["url"] if panel["url"].endswith('.php') else f"{clean_base}/login.php"
        try:
            post_res = requests.post(login_url, data={"login_id": panel["username"], "password": panel["password"]}, headers={"Content-Type": "application/x-www-form-urlencoded", "User-Agent": "Mozilla/5.0"}, allow_redirects=False, timeout=20)
            cookies = post_res.cookies
            if cookies:
                cookie_str = "; ".join([f"{k}={v}" for k, v in cookies.items()])
                is_redirect = post_res.status_code == 302
                location = post_res.headers.get("location", "")
                has_location = any(kw in location for kw in ["index.php", "dashboard.php", "main.php"])
                has_cookies = "PHPSESSID" in cookie_str or "mk_remember" in cookie_str

                if (is_redirect or has_location or post_res.status_code == 200) and has_cookies:
                    logger.info(f"[{panel['name']}] PHP/MK Login successful! Cookies acquired.")
                    panel["sessionCookie"] = cookie_str
                    panel["status"] = "Running (LoggedIn)"
                    save_panels_to_file(panels)
                    return True
            logger.error(f"[{panel['name']}] PHP/MK Login failed: status {post_res.status_code}")
        except Exception as err:
            logger.error(f"[{panel['name']}] PHP/MK Login error: {err}")
        panel["status"] = "Error (Login Failed)"
        save_panels_to_file(panels)
        return False

    # 3. NexaOTP Panel
    elif is_nexa_otp(panel):
        logger.info(f"[{panel['name']}] Initiating dedicated NexaOTP login sequence...")
        clean_base = get_clean_base_url(panel, baseUrl)
        post_url = f"{clean_base}/api/auth/login"
        try:
            res = requests.post(post_url, json={"email": panel["username"], "password": panel["password"]}, headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"}, timeout=20)
            if res.status_code == 200:
                data = res.json()
                token = data.get("token") or data.get("data", {}).get("token")
                if token:
                    logger.info(f"[{panel['name']}] NexaOTP Login successful!")
                    panel["sessionCookie"] = token
                    panel["status"] = "Running (LoggedIn)"
                    save_panels_to_file(panels)
                    return True
            logger.error(f"[{panel['name']}] NexaOTP Login failed: status {res.status_code}")
        except Exception as err:
            logger.error(f"[{panel['name']}] NexaOTP Login error: {err}")
        panel["status"] = "Error (Login Failed)"
        save_panels_to_file(panels)
        return False

    # 4. NextJS (StexSMS / XMint)
    elif is_nextjs_panel(panel):
        try:
            logger.info(f"[{panel['name']}] Initiating NextJS authentication bypass sequence...")
            clean_base = get_clean_base_url(panel, baseUrl)
            post_url = f"{clean_base}/mapi/v1/mauth/login"
            
            referer_url = f"{clean_base}/mauth/login"
            url_lower = panel["url"].lower()
            if "/auth" in url_lower:
                if "/#/auth" in url_lower:
                    referer_url = f"{clean_base}/#/auth"
                else:
                    referer_url = f"{clean_base}/auth"
                    
            from urllib.parse import urlparse
            try:
                u = urlparse(clean_base)
                origin_url = f"{u.scheme}://{u.netloc}"
            except Exception:
                origin_url = "https://stexsms.com"

            headers = {
                "Content-Type": "application/json",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                "Referer": referer_url,
                "Origin": origin_url
            }
            
            # Advanced Cloudflare Bypass using globally cached session
            res = session.post(post_url, json={
                "email": panel["username"],
                "password": panel["password"]
            }, headers=headers, timeout=20)

            # Advanced Fallback logic if X mint uses /auth instead of /mauth
            if res.status_code == 404:
                logger.info(f"[{panel['name']}] /mauth/login returned 404. Trying /auth/login fallback...")
                fallback_url = f"{clean_base}/mapi/v1/auth/login"
                fallback_res = session.post(fallback_url, json={"email": panel["username"], "password": panel["password"]}, headers=headers, timeout=15)
                if fallback_res.status_code == 200:
                    res = fallback_res
                else:
                    try:
                        u = urlparse(clean_base)
                        root_base = f"{u.scheme}://{u.netloc}"
                        if root_base != clean_base:
                            logger.info(f"[{panel['name']}] Retrying login at domain root: {root_base}...")
                            root_res = session.post(f"{root_base}/mapi/v1/mauth/login", json={"email": panel["username"], "password": panel["password"]}, headers=headers, timeout=15)
                            if root_res.status_code == 200:
                                res = root_res
                                panel["resolvedBaseUrl"] = root_base
                            else:
                                root_res_auth = session.post(f"{root_base}/mapi/v1/auth/login", json={"email": panel["username"], "password": panel["password"]}, headers=headers, timeout=15)
                                if root_res_auth.status_code == 200:
                                    res = root_res_auth
                                    panel["resolvedBaseUrl"] = root_base
                    except: pass

            if res.status_code == 200:
                data = res.json()
                # Dynamic Token Extraction (Handles both StexSMS and X mint formats)
                token = data.get("token") or data.get("data", {}).get("token")
                if token:
                    logger.info(f"[{panel['name']}] NEXTJS login success token preserved!")
                    panel["sessionCookie"] = token
                    panel["status"] = "Running (LoggedIn)"
                    save_panels_to_file(panels)
                    return True
            
            logger.error(f"[{panel['name']}] NextJS credentials rejected or rate limited ({res.status_code}). Details: {res.text[:100]}")
            panel["status"] = "Error (Login Failed)"
            save_panels_to_file(panels)
            return False
        except Exception as e:
            logger.error(f"[{panel['name']}] Connection authentication exception: {e}")
            panel["status"] = "Error (Connection)"
            save_panels_to_file(panels)
            return False

# ----------------------------------------------------
# Live SMS Real Purchasing
# ----------------------------------------------------

def buy_number(range_val, target_panel_id=None):
    panel = None
    if target_panel_id:
        panel = next((p for p in panels if p.get("id") == target_panel_id), None)
    else:
        services_data = load_services()
        supported_panels = []
        for p_id, s_list in services_data.items():
            for s in s_list:
                for c in s.get("countries", []):
                    clean_target = range_val.replace("X", "").replace("*", "")
                    if any(clean_target in r for r in c.get("ranges", [])):
                        supported_panels.append(p_id)
        if supported_panels:
            chosen_p_id = random.choice(supported_panels)
            panel = next((p for p in panels if p.get("id") == chosen_p_id), None)
            logger.info(f"Randomly selected panel {chosen_p_id} for range {range_val}")
        else:
            panel = panels[0] if panels else None
            
    if not panel:
        return {"success": False, "message": "No suitable panel configuration found."}

    if not panel.get("sessionCookie"):
        login_to_panel(panel, force=True)
        if not panel.get("sessionCookie"):
            return {"success": False, "message": "Stex SMS authentication failed. Credentials check required."}

    try:
        # A. PHP / MK Panel
        if is_php_panel(panel):
            baseUrl = normalize_base_url(panel["url"])
            clean_base = get_clean_base_url(panel, baseUrl)
            num_url = panel.get("getNumberUrl") or f"{clean_base}/API/api_handler_test.php"
            
            headers = {
                "Content-Type": "application/x-www-form-urlencoded",
                "Cookie": panel["sessionCookie"],
                "User-Agent": "Mozilla/5.0"
            }
            res = requests.post(num_url, data={
                "action": "get_number",
                "range": range_val.strip()
            }, headers=headers, timeout=45)
            
            if res.status_code == 200:
                data = res.json()
                if data.get("status") == "success":
                    today = datetime.now().strftime("%Y-%m-%d")
                    if admin_db.get("today_date") != today:
                        admin_db["today_date"] = today
                        admin_db["today_numbers_count"] = 0
                    admin_db["today_numbers_count"] = admin_db.get("today_numbers_count", 0) + 1
                    save_admin_db()
                    
                    return {
                        "success": True,
                        "message": data.get("message", "Number allocated successfully"),
                        "number": data.get("number") or "",
                        "operator": data.get("operator", "Unknown"),
                        "country": data.get("country", "Unknown")
                    }
                return {"success": False, "message": data.get("message") or "Failed to request number from MK panel."}
            return {"success": False, "message": f"MK panel responded with error code {res.status_code}"}

        # B. NexaOTP Panel
        elif is_nexa_otp(panel):
            baseUrl = normalize_base_url(panel["url"])
            clean_base = get_clean_base_url(panel, baseUrl)
            num_url = panel.get("getNumberUrl") or f"{clean_base}/api/user/request-number"
            
            headers = {
                "Content-Type": "application/json",
                "X-Session-Token": panel["sessionCookie"],
                "User-Agent": "Mozilla/5.0"
            }
            res = requests.post(num_url, json={
                "range": range_val.strip(),
                "format": "standard"
            }, headers=headers, timeout=45)
            
            if res.status_code == 200:
                data = res.json()
                if data.get("success") is True:
                    today = datetime.now().strftime("%Y-%m-%d")
                    if admin_db.get("today_date") != today:
                        admin_db["today_date"] = today
                        admin_db["today_numbers_count"] = 0
                    admin_db["today_numbers_count"] = admin_db.get("today_numbers_count", 0) + 1
                    save_admin_db()

                    return {
                        "success": True,
                        "message": data.get("message", "Number allocated successfully"),
                        "number": data.get("number") or "",
                        "operator": data.get("operator", "Unknown"),
                        "country": data.get("country", "Unknown")
                    }
                return {"success": False, "message": data.get("error") or data.get("message") or "Failed to request number from NexaOTP."}
            return {"success": False, "message": f"NexaOTP panel responded with error code {res.status_code}"}

        # B.5 Voltx API Panel
        elif is_voltx_api(panel):
            clean_base = get_clean_base_url(panel, panel["url"])
            num_url = panel.get("getNumberUrl") or f"{clean_base}/getnum"
            headers = {
                "Content-Type": "application/json",
                "mauthapi": panel.get("sessionCookie", "MKJGS2MSZYB")
            }
            rid = range_val.replace("X", "").replace("*", "").strip()
            
            res = requests.post(num_url, json={"rid": rid}, headers=headers, timeout=20)
            
            if res.status_code == 200:
                data = res.json()
                if data.get("meta", {}).get("code") == 200 and data.get("data"):
                    num_data = data["data"]
                    today = datetime.now().strftime("%Y-%m-%d")
                    if admin_db.get("today_date") != today:
                        admin_db["today_date"] = today
                        admin_db["today_numbers_count"] = 0
                    admin_db["today_numbers_count"] = admin_db.get("today_numbers_count", 0) + 1
                    save_admin_db()

                    return {
                        "success": True,
                        "message": data.get("message", "Number allocated successfully"),
                        "number": num_data.get("full_number") or num_data.get("no_plus_number") or "",
                        "operator": num_data.get("operator", "Unknown"),
                        "country": num_data.get("country", "Unknown")
                    }
                return {"success": False, "message": data.get("message", "Failed to get number from API.")}
            return {"success": False, "message": f"API Error: {res.status_code}"}

        # C. NextJS (StexSMS / X Mint) Panel
        else:
            baseUrl = normalize_base_url(panel["url"])
            clean_base = get_clean_base_url(panel, baseUrl)
            num_url = panel.get("getNumberUrl") or f"{clean_base}/mapi/v1/mdashboard/getnum/number"
            headers = {
                "Content-Type": "application/json",
                "mauthtoken": panel["sessionCookie"],
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }
            payload = {
                "range": range_val.strip(),
                "is_national": False,
                "remove_plus": False
            }
            
            # Cloudflare Bypass using Cloudscraper for API requests
            try:
                import cloudscraper
                scraper = cloudscraper.create_scraper(
                    browser={
                        'browser': 'chrome',
                        'platform': 'windows',
                        'desktop': True
                    }
                )
            except ImportError:
                logger.error("cloudscraper module not found! Fallback to standard requests.")
                scraper = requests
                
            res = scraper.post(num_url, json=payload, headers=headers, timeout=20)
            
            if res.status_code == 200:
                res_data = res.json()
                meta_status = res_data.get("meta", {}).get("status")
                success_status = res_data.get("success") == True or res_data.get("status") == "success"
                
                inner_data = res_data.get("data", res_data)
                has_num = inner_data.get("number") or inner_data.get("copy") or inner_data.get("full_number")
                
                if meta_status == "success" or success_status or has_num:
                    today = datetime.now().strftime("%Y-%m-%d")
                    if admin_db.get("today_date") != today:
                        admin_db["today_date"] = today
                        admin_db["today_numbers_count"] = 0
                    admin_db["today_numbers_count"] = admin_db.get("today_numbers_count", 0) + 1
                    save_admin_db()

                    return {
                        "success": True,
                        "message": res_data.get("message", "Number allocated successfully"),
                        "number": inner_data.get("number") or inner_data.get("copy") or inner_data.get("full_number") or res_data.get("number", ""),
                        "operator": inner_data.get("operator", "Unknown"),
                        "country": inner_data.get("country", "Unknown")
                    }
                return {"success": False, "message": res_data.get("message", "Failed to retrieve allocated number.")}
            else:
                return {"success": False, "message": f"Server responded with error status code: {res.status_code}"}
    except Exception as e:
        logger.error(f"Error buying number for range: {e}")
        return {"success": False, "message": str(e)}

# ----------------------------------------------------
# Active Traffic Aggregation Compiler
# ----------------------------------------------------

def compile_traffic_stats():
    # 🚀 Returns instant cached data from local database
    global local_traffic_stats
    return local_traffic_stats, get_current_cest_time(), False

def get_country_code(num):
    clean = str(num).replace('+', '').strip()
    if clean.startswith('225'): return 'CI'
    if clean.startswith('237'): return 'CM'
    if clean.startswith('228'): return 'TG'
    if clean.startswith('261'): return 'MG'
    if clean.startswith('229'): return 'BJ'
    if clean.startswith('224'): return 'GN'
    if clean.startswith('241'): return 'GA'
    if clean.startswith('236'): return 'CF'
    if clean.startswith('242'): return 'CG'
    if clean.startswith('243'): return 'CD'
    if clean.startswith('221'): return 'SN'
    if clean.startswith('223'): return 'ML'
    if clean.startswith('992') or clean.startswith('7992'): return 'TJ'
    if clean.startswith('226'): return 'BF'
    if clean.startswith('227'): return 'NE'
    if clean.startswith('235'): return 'TD'
    return 'Unknown'

def get_range_from_number(num):
    clean = str(num).replace('+', '').strip()
    first_x = re.search(r'[Xx*\-]', clean)
    if first_x:
        clean = clean[:first_x.start()]
    if clean.startswith('225') and len(clean) > 7:
        return clean[:7]
    if len(clean) > 8:
        return clean[:8]
    return clean

def get_service_short_code(name, sms_body=""):
    text = (str(name) + " " + str(sms_body)).lower()
    if 'whatsapp' in text or 'wa' in text: return 'WS'
    if 'facebook' in text or 'fb' in text: return 'FB'
    if 'telegram' in text or 'tg' in text: return 'TG'
    if 'instagram' in text or 'ig' in text: return 'IG'
    if 'tiktok' in text or 'tt' in text: return 'TT'
    if 'google' in text: return 'GG'
    if 'microsoft' in text: return 'MS'
    if 'imo' in text: return 'IMO'
    if 'viber' in text: return 'VI'
    if 'snapchat' in text: return 'SC'
    if 'wechat' in text: return 'WC'
    if 'line' in text: return 'LN'
    if 'twitter' in text or ' x ' in text: return 'TW'
    if 'paypal' in text: return 'PP'
    if 'discord' in text: return 'DC'
    if 'amazon' in text: return 'AMZ'
    return 'OTP'

def get_service_display_name(name):
    lower = str(name).strip().lower()
    if 'facebook' in lower or lower == 'fb': return 'Facebook'
    if 'whatsapp' in lower or lower == 'wa': return 'WhatsApp'
    if 'telegram' in lower or lower == 'tg': return 'Telegram'
    if 'instagram' in lower or lower == 'ig': return 'Instagram'
    if 'microsoft' in lower or lower == 'ms': return 'Microsoft'
    if 'google' in lower or lower == 'gg': return 'Google'
    if 'imo' in lower: return 'IMO'
    if 'tiktok' in lower or lower == 'tt': return 'TikTok'
    if 'snapchat' in lower: return 'Snapchat'
    if 'viber' in lower: return 'Viber'
    if 'line' in lower: return 'LINE'
    if 'wechat' in lower: return 'WeChat'
    if 'twitter' in lower or lower == 'x': return 'Twitter'
    if 'postpaid' in lower: return 'PostPaid'
    if 'failed' in lower: return 'Failed Calls'
    return str(name).strip().capitalize()

def find_service_by_slug(stats, slug):
    # একদম হুবহু বা প্রথম ৫০ ক্যারেক্টার ম্যাচ করানো হচ্ছে যাতে কনফ্লিক্ট না হয়
    for service in stats.keys():
        if service[:50] == slug:
            return service
    for service in stats.keys():
        if slug.lower() in service.lower():
            return service
    return None

# ----------------------------------------------------
# Traffic Visualizers Layout
# ----------------------------------------------------

def render_traffic_home(chat_id, message_id=None):
    try:
        stats, ref_time, is_fallback = compile_traffic_stats()
        
        message_text = "╔═══════════════╗\n" \
                       f"║ <tg-emoji emoji-id='5352877703043258544'>📈</tg-emoji> <b>NETWORK TRAFFIC</b>\n" \
                       "╚═══════════════╝\n"

        services_with_counts = []
        for svc, ctrs in stats.items():
            total = sum(ctr_data["success"] for ctr_data in ctrs.values())
            services_with_counts.append((svc, total))

        services_with_counts.sort(key=lambda x: x[1], reverse=True)

        if not services_with_counts:
            message_text += "<i>No active traffic recorded in the last 10 minutes on DXA.</i>"
        else:
            is_first = True
            # ডাইনামিক ইনলাইন বাটনের ইমোজি আইডি
            raw_ids = {
                "Facebook": "5334807341109908955", "WhatsApp": "5334759662677957452",
                "Telegram": "5337010556253543833", "Instagram": "5334868205091459431",
                "Microsoft": "5334880948259427772", "Google": "5463352748751753567",
                "TikTok": "5339213256001102461"
            }
            
            for svc, total in services_with_counts:
                if not is_first:
                    message_text += "\n"
                is_first = False
                p_emoji = get_app_pemoji(svc)
                message_text += f"» {p_emoji} {svc}\n" \
                               f"➥ {total} OTP\n"

        inline_buttons = []
        for svc, total in services_with_counts:
            safe_slug = svc[:50]
            btn_emoji_id = get_app_raw_id(svc)
            inline_buttons.append([{
                "text": f" Explore {svc} Range",
                "callback_data": f"tr_svc:{safe_slug}",
                "style": "primary",
                "icon_custom_emoji_id": btn_emoji_id
            }])

        inline_buttons.append([
            {"text": " Refresh", "callback_data": "tr_refresh", "style": "success", "icon_custom_emoji_id": "5465368548702446780"},
            {"text": " Close", "callback_data": "tr_close", "style": "danger", "icon_custom_emoji_id": "5420130255174145507"}
        ])

        keyboard = {"inline_keyboard": inline_buttons}
        if message_id:
            edit_bot_message(chat_id, message_id, message_text, keyboard)
        else:
            send_bot_message(chat_id, message_text, keyboard)

    except Exception as e:
        error_msg = f"❌ Error fetching traffic stats: <code>{escape_html(str(e))}</code>"
        if message_id:
            edit_bot_message(chat_id, message_id, error_msg, {
                "inline_keyboard": [[{"text": "🔙 Back to Traffic Menu", "callback_data": "tr_refresh", "style": "danger"}]]
            })
        else:
            send_bot_message(chat_id, error_msg, {
                "inline_keyboard": [[{"text": "🔙 Back to Traffic Menu", "callback_data": "tr_refresh", "style": "danger"}]]
            })

def render_explore_service(chat_id, message_id, service_slug):
    try:
        stats, _, _ = compile_traffic_stats()
        service_name = find_service_by_slug(stats, service_slug)

        if not service_name or service_name not in stats:
            edit_bot_message(chat_id, message_id, f"❌ Service <code>{escape_html(service_slug)}</code> has no active traffic or has expired.", {
                "inline_keyboard": [[{"text": "🔙 Back to Traffic Menu", "callback_data": "tr_refresh", "style": "danger"}]]
            })
            return

        text = f"{get_pemoji('king', '👑')} <b>Explore Service:</b> {service_name}\n\nSelect a country to view available ranges:"
        country_buttons = []
        sorted_codes = sorted(stats[service_name].keys(), key=lambda code: stats[service_name][code]["success"], reverse=True)
        
        for idx, code in enumerate(sorted_codes, start=1):
            c_info = get_country_info(code)
            name = c_info.get("name", "Unknown")
            em_id = c_info.get("id", "5336972142066047577") # Default World ID
            success_count = stats[service_name][code]["success"]
            
            country_buttons.append([{
                "text": f"{idx}. {name} ({code}) - {success_count} OTP",
                "callback_data": f"tr_ctr:{service_slug}:{code}",
                "style": "primary",
                "icon_custom_emoji_id": em_id
            }])

        country_buttons.append([{"text": " Back", "callback_data": "tr_refresh", "style": "danger", "icon_custom_emoji_id": "5267490665117275176"}])
        edit_bot_message(chat_id, message_id, text, {"inline_keyboard": country_buttons})

    except Exception as e:
        edit_bot_message(chat_id, message_id, f"❌ Error: <code>{escape_html(str(e))}</code>", {
            "inline_keyboard": [[{"text": "🔙 Back to Traffic Menu", "callback_data": "tr_refresh", "style": "danger"}]]
        })

def render_explore_ranges(chat_id, message_id, service_slug, country_code):
    try:
        stats, _, _ = compile_traffic_stats()
        service_name = find_service_by_slug(stats, service_slug)

        if not service_name or service_name not in stats or country_code not in stats[service_name]:
            edit_bot_message(chat_id, message_id, "❌ No active ranges found for this service and country.", {
                "inline_keyboard": [[{"text": "🔙 Back", "callback_data": f"tr_svc:{service_slug}", "style": "danger"}]]
            })
            return

        c_info = get_country_info(country_code)
        flag_pemoji = f"<tg-emoji emoji-id='{c_info.get('id', '5336972142066047577')}'>{c_info.get('flag', '🏳️')}</tg-emoji>"
        
        text = f"{get_pemoji('king', '👑')} <b>Ranges for</b> {service_name} - {flag_pemoji} {country_code}\n\n" \
               "Click on any range below to get an instant tap-to-copy message!"

        range_buttons = []
        ranges_data = stats[service_name][country_code]["ranges"]
        sorted_ranges = sorted(ranges_data.items(), key=lambda x: x[1], reverse=True)

        for range_val, count in sorted_ranges:
            range_buttons.append([{
                "text": f" {range_val} ({count})",
                "copy_text": {"text": range_val},
                "style": "success",
                "icon_custom_emoji_id": "5192739271886282680" # Notepad/Clipboard emoji
            }])

        range_buttons.append([{"text": " Back", "callback_data": f"tr_svc:{service_slug}", "style": "danger", "icon_custom_emoji_id": "5267490665117275176"}])
        edit_bot_message(chat_id, message_id, text, {"inline_keyboard": range_buttons})
        
    except Exception as e:
        edit_bot_message(chat_id, message_id, f"❌ Error: <code>{escape_html(str(e))}</code>", {
            "inline_keyboard": [[{"text": "🔙 Back", "callback_data": f"tr_svc:{service_slug}", "style": "danger"}]]
        })

# ----------------------------------------------------
# Search Engine and allocation routers
# ----------------------------------------------------

def search_number_otp(chat_id, query):
    passed, err_msg, _ = check_user_limits(chat_id, update_cooldown=False)
    if not passed:
        kb = {"inline_keyboard": [[{"text": " Back", "callback_data": "usr_search_home", "style": "danger", "icon_custom_emoji_id": "5267490665117275176"}]]}
        send_bot_message(chat_id, err_msg, kb)
        return

    clean_num = str(query).replace("+", "").strip()
    search_cfg = admin_db.get("search_cfg", {})
    valid_panels = []
    
    for p in panels:
        p_id = p["id"]
        cfg = search_cfg.get(p_id, {})
        if not cfg.get("is_active", True): continue
        prefixes = cfg.get("prefixes", [])
        if not prefixes: continue
        for pfx in prefixes:
            if clean_num.startswith(pfx):
                valid_panels.append(p)
                break
                
    if not valid_panels:
        send_bot_message(chat_id, f"{get_pemoji('error', '❌')} <b>Search Restricted!</b>\n\nNo active panels support searching for the country code of <code>{clean_num}</code>.\n<i>Please ensure the country code is supported or ask the admin to add it.</i>")
        return
        
    panel = random.choice(valid_panels)
    if not panel.get("sessionCookie"): login_to_panel(panel, force=True)

    send_bot_message(chat_id, f"{get_pemoji('search', '🔍')} <i>Searching messages on <b>{panel['name']}</b> for <b>{escape_html(clean_num)}</b>...</i>")

    try:
        baseUrl = normalize_base_url(panel["url"])
        domain_match = re.match(r'^(https?://[^/]+)', baseUrl)
        domain = domain_match.group(1) if domain_match else baseUrl
        today_date_str = datetime.now().strftime("%Y-%m-%d")
        session = get_session(panel["id"])

        if is_voltx_api(panel):
            get_url = panel.get("getMessageUrl") or f"{get_clean_base_url(panel, panel['url'])}/success-otp"
            headers = {"mauthapi": panel.get("sessionCookie", "MKJGS2MSZYB")}
            res = session.get(get_url, headers=headers, timeout=20)
            
            if res.status_code == 200:
                data = res.json()
                otps = data.get("data", {}).get("otps", [])
                numbers = [{"number": i.get("number"), "message": i.get("message"), "app_name": "OTP"} for i in otps]
            else:
                send_bot_message(chat_id, f"❌ Voltx API search error: {res.status_code}")
                return
        else:
            get_url = panel.get("getMessageUrl") or f"{domain}/mapi/v1/mdashboard/getnum/info"
            headers = {
                "Content-Type": "application/json",
                "mauthtoken": panel.get("sessionCookie", ""),
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }
            params = {"date": today_date_str, "page": 1, "search": clean_num, "status": ""}
            res = session.get(get_url, headers=headers, params=params, timeout=20)
            if res.status_code != 200:
                send_bot_message(chat_id, f"❌ API search responded with error code: {res.status_code}")
                return
            res_data = res.json()
            numbers = res_data.get("data", {}).get("numbers", [])

        if isinstance(numbers, list):
            matched = [num for num in numbers if clean_num in str(num.get("number", ""))]
            if matched:
                send_bot_message(chat_id, f"🔍 Found <b>{len(matched)}</b> match(es) for <code>{clean_num}</code>:")
                for num in matched:
                    raw_msg = num.get("message") or num.get("otp") or num.get("sms") or num.get("smsBody") or num.get("sms_text") or num.get("sms_body") or ""
                    msg = str(raw_msg).strip()
                    number_val = num.get("number", "")
                    
                    c_code = get_country_code(number_val)
                    c_info = get_country_info(c_code)
                    flag_em_id = c_info.get("id", "5336972142066047577")
                    
                    svc_name = num.get("app_name", "OTP")
                    svc_short = get_service_short_code(svc_name, msg)
                    svc_em_id = get_app_raw_id(svc_name)
                    
                    box_design = (
                        f"╔═════════════╗\n"
                        f"║ <tg-emoji emoji-id='{svc_em_id}'>💬</tg-emoji> #{svc_short} <tg-emoji emoji-id='{flag_em_id}'>🚩</tg-emoji> <code>{number_val}</code>\n"
                        f"╚═════════════╝"
                    )

                    inline_keyboard = []
                    if msg:
                        otp_val = extract_otp(msg)
                        has_otp = otp_val != "No OTP Found"
                        inline_keyboard.append([{
                            "text": f" {otp_val}" if has_otp else " Copy SMS",
                            "copy_text": {"text": otp_val if has_otp else msg},
                            "style": "success",
                            "icon_custom_emoji_id": svc_em_id
                        }])
                        inline_keyboard.append([{
                            "text": " Full Message",
                            "copy_text": {"text": msg},
                            "style": "primary",
                            "icon_custom_emoji_id": "5337302974806922068"
                        }])
                    else:
                        inline_keyboard.append([{
                            "text": " Pending (No SMS yet)",
                            "callback_data": "none",
                            "style": "danger",
                            "icon_custom_emoji_id": "5337172996211648018"
                        }])

                    search_range_val = get_range_from_number(number_val)
                    inline_keyboard.extend([
                        [
                            {"text": " Change Number", "callback_data": f"buy_{search_range_val}", "style": "danger", "icon_custom_emoji_id": "5420155432272438703"},
                            get_otp_group_btn()
                        ],
                        [{"text": " Back", "callback_data": "usr_search_home", "style": "danger", "icon_custom_emoji_id": "5267490665117275176"}]
                    ])
                    send_bot_message(chat_id, box_design, {"inline_keyboard": inline_keyboard})
            else:
                send_bot_message(chat_id, f"❌ No active numbers found matching <code>{clean_num}</code> on {panel['name']} today.")
        else:
            send_bot_message(chat_id, "❌ Failed to retrieve valid numbers format from API.")
    except Exception as e:
        send_bot_message(chat_id, f"❌ Error searching database: <code>{escape_html(str(e))}</code>")

def trigger_buy_number(chat_id, range_val, target_panel_id=None, message_id=None, callback_id=None):
    try:
        passed, err_msg, batch_size = check_user_limits(chat_id)
        if not passed:
            if callback_id:
                answer_callback(callback_id, err_msg, show_alert=True)
            else:
                kb = {"inline_keyboard": [[{"text": " Back", "callback_data": "usr_menu_home", "style": "danger", "icon_custom_emoji_id": "5267490665117275176"}]]}
                if message_id: edit_bot_message(chat_id, message_id, f"⚠️ {err_msg}", kb)
                else: send_bot_message(chat_id, f"⚠️ {err_msg}", kb)
            return

        if callback_id:
            answer_callback(callback_id, f"Requesting {range_val}...")

        initial_text = f"{get_pemoji('wait', '⏳')} <i>Allocating {batch_size} number(s) for range <b>{escape_html(range_val)}</b>... Please wait.</i>"
        
        if message_id:
            edit_bot_message(chat_id, message_id, initial_text)
        else:
            res = send_bot_message(chat_id, initial_text)
            message_id = res.get("result", {}).get("message_id") if res else None

        numbers_fetched = []
        last_err = "Unknown error"
        if "active_numbers" not in admin_db: admin_db["active_numbers"] = {}
        
        for _ in range(batch_size):
            result = buy_number(range_val, target_panel_id)
            if result.get("success"):
                numbers_fetched.append(result)
                number_val = result.get("number") or ""
                clean_num = str(number_val).replace("+", "").strip()
                admin_db["active_numbers"][clean_num] = str(chat_id)
            else:
                last_err = result.get("message", "Failed.")
                break
                
        if numbers_fetched:
            save_admin_db()
            c_code = get_country_code(numbers_fetched[0].get("number", ""))
            c_info = get_country_info(c_code)
            flag_em_id = c_info.get("id", "5336972142066047577")
            
            blank_text = "ㅤ"
            keyboard = {"inline_keyboard": []}
            
            for res in numbers_fetched:
                num = res.get("number", "")
                keyboard["inline_keyboard"].append([{
                    "text": f" +{num.replace('+', '')}",
                    "copy_text": {"text": f"{num}"},
                    "style": "primary",
                    "icon_custom_emoji_id": flag_em_id
                }])
                
            keyboard["inline_keyboard"].extend([
                [
                    {"text": " Change Number", "callback_data": f"buy_{range_val}", "style": "danger", "icon_custom_emoji_id": "5420155432272438703"},
                    get_otp_group_btn()
                ],
                [{"text": " Back", "callback_data": "usr_search_home", "style": "danger", "icon_custom_emoji_id": "5267490665117275176"}]
            ])
            if message_id:
                edit_bot_message(chat_id, message_id, blank_text, keyboard)
            else:
                send_bot_message(chat_id, blank_text, keyboard)
        else:
            failure_text = f"❌ <b>Get Number Failed!</b>\n\n" \
                           f"<b>Range:</b> <code>{escape_html(range_val)}</code>\n" \
                           f"<b>Error:</b> <code>{escape_html(last_err)}</code>\n\n" \
                           f"<i>Please try again, or confirm you have enough balance.</i>"

            keyboard = {
                "inline_keyboard": [
                    [{"text": "🔁 Retry getting range", "callback_data": f"buy_{range_val}", "style": "danger"}]
                ]
            }
            if message_id:
                edit_bot_message(chat_id, message_id, failure_text, keyboard)
            else:
                send_bot_message(chat_id, failure_text, keyboard)
    except Exception as e:
        logger.error(f"Error buying range: {e}")
        send_bot_message(chat_id, f"❌ <code>Error requesting number: {escape_html(str(e))}</code>")

def render_admin_panel(chat_id, message_id=None):
    if str(chat_id) not in admin_db.get("admins", [OWNER_ID]):
        send_bot_message(chat_id, "❌ You are not authorized to view the Admin Panel.")
        return

    # Check and reset daily count if needed
    today = datetime.now().strftime("%Y-%m-%d")
    if admin_db.get("today_date") != today:
        admin_db["today_date"] = today
        admin_db["today_numbers_count"] = 0
        save_admin_db()

    users_count = len(admin_db.get("users", []))
    numbers_count = admin_db.get("today_numbers_count", 0)

    text = (
        f"{get_pemoji('dashboard', '📊')} <b>ADMIN CONTROL PANEL</b> {get_pemoji('dashboard', '📊')}\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        f"{get_pemoji('dashboard', '📊')} <b>DATABASE OVERVIEW</b>\n"
        "— — — — — — — — — —\n"
        f"{get_pemoji('user', '👤')} <b>Users</b>      » {users_count}\n"
        f"{get_pemoji('number', '🔢')} <b>Numbers</b>    » {numbers_count} (Today)\n"
    )

    inline_keyboard = [
        [
            {"text": " Broadcast", "callback_data": "adm_broadcast", "style": "primary", "icon_custom_emoji_id": "5789428375261023681"},
            {"text": " Force Join", "callback_data": "adm_fj_menu", "style": "primary", "icon_custom_emoji_id": "5190447043545438788"}
        ],
        [{"text": " User Management", "callback_data": "adm_user_mgmt_menu", "style": "success", "icon_custom_emoji_id": "5352861489541714456"}],
        [{"text": " Admin Management", "callback_data": "adm_admin_menu", "style": "danger", "icon_custom_emoji_id": "5353032893096567467"}],
        [
            {"text": " System", "callback_data": "adm_system_menu", "style": "primary", "icon_custom_emoji_id": "5420155432272438703"},
            {"text": " Manage Dxa", "callback_data": "adm_dxa_menu", "style": "success", "icon_custom_emoji_id": "5352838545826420397"}
        ],
        [{"text": " Developer Info", "callback_data": "adm_developer", "style": "primary", "icon_custom_emoji_id": "5353032893096567467"}],
        [{"text": " Back to Home", "callback_data": "usr_menu_home", "style": "danger", "icon_custom_emoji_id": "5267490665117275176"}]
    ]
    
    keyboard = {"inline_keyboard": inline_keyboard}
    if message_id:
        edit_bot_message(chat_id, message_id, text, keyboard)
    else:
        send_bot_message(chat_id, text, keyboard)

def render_admin_developer(chat_id, message_id):
    text = (
        "╔═══════════╗\n"
        f"      {get_pemoji('dxa', '😒')} <b>DEVELOPER</b> {get_pemoji('dxa', '😒')}\n"
        "╚═══════════╝\n"
        f"{get_pemoji('user', '👤')} ➤ 𝐍𝐚𝐦𝐞 : <a href='tg://user?id=8570538705'>𝗔𝗟𝗜𝗙 𝗦𝗛𝗘𝗜𝗞𝗛</a> {get_pemoji('done', '✅')}\n\n"
        f"{get_pemoji('user', '👤')} ➤ 𝐍𝐢𝐜𝐤𝐍𝐚𝐦𝐞 : Asik\n\n"
        "📍 ➤ 𝐂𝐨𝐮𝐧𝐭𝐫𝐲 : Bangladesh\n\n"
        f"{get_pemoji('world', '🌐')} ➤ 𝐑𝐞𝐥𝐢𝐠𝐢𝐨𝐧 : Islam\n\n"
        "🔹 ➤ 𝐋𝐚𝐧𝐠𝐮𝐚𝐠𝐞 : বাংলা | English | Hindi\n\n"
        f"{get_pemoji('gem', '💎')} ➤ 𝐒𝐤𝐢𝐥𝐥 : Technology • Coding\n\n"
        f"{get_pemoji('fire', '🔥')} ➤ 𝐇𝐨𝐛𝐛𝐢𝐞𝐬 : Music • Anime"
    )
    
    inline_keyboard = [
        [{"text": " Back to Admin", "callback_data": "adm_main_menu", "style": "danger", "icon_custom_emoji_id": "5267490665117275176"}]
    ]
    
    edit_bot_message(chat_id, message_id, text, {"inline_keyboard": inline_keyboard})

def check_force_join(chat_id, message_id=None):
    if str(chat_id) in admin_db.get("admins", [OWNER_ID]) or not admin_db.get("force_join_status", False):
        return True
        
    channels = admin_db.get("force_join_channels", [])
    if not channels:
        return True
        
    not_joined = []
    for ch in channels:
        check_id = ch
        if "t.me/" in ch:
            check_id = "@" + ch.split("t.me/")[1].split("/")[0]
            
        res = call_telegram("getChatMember", {"chat_id": check_id, "user_id": chat_id})
        if res and res.get("ok"):
            status = res.get("result", {}).get("status")
            if status in ["left", "kicked", "restricted"]:
                not_joined.append(ch)
        else:
            not_joined.append(ch)
            
    if not_joined:
        inline_keyboard = []
        for ch in not_joined:
            url = ch if ch.startswith("http") else f"https://t.me/{ch.replace('@', '')}"
            # Join channel buttons with premium 📢 icon
            inline_keyboard.append([{"text": f" Join {ch}", "url": url, "style": "primary", "icon_custom_emoji_id": "5789428375261023681"}])
        
        # Check again button with premium 🔄 icon
        inline_keyboard.append([{"text": " Check Again", "callback_data": "check_fj", "style": "success", "icon_custom_emoji_id": "5465368548702446780"}])
        
        text = (
            "╔═══════════════╗\n"
            "   <tg-emoji emoji-id='5190447043545438788'>🛡</tg-emoji> <b>ACCESS RESTRICTED</b>\n"
            "╚═══════════════╝\n\n"
            "Hello! To use our bot services, you must join our official channels listed below.\n\n"
            "<i>After joining, click the 'Check Again' button to verify.</i>"
        )
        
        if message_id:
            edit_bot_message(chat_id, message_id, text, {"inline_keyboard": inline_keyboard})
        else:
            send_bot_message(chat_id, text, {"inline_keyboard": inline_keyboard})
        return False
    return True

def render_force_join_menu(chat_id, message_id):
    status = admin_db.get("force_join_status", False)
    # Status label and style
    status_label = " ACTIVE: ON" if status else " ACTIVE: OFF"
    status_style = "success" if status else "danger"
    # ✅ if ON, ❌ if OFF
    status_emoji_id = "5352694861990501856" if status else "5420130255174145507"
    
    inline_keyboard = [
        [{"text": status_label, "callback_data": "adm_fj_toggle", "style": status_style, "icon_custom_emoji_id": status_emoji_id}]
    ]
    
    channels = admin_db.get("force_join_channels", [])
    if channels:
        for idx, ch in enumerate(channels):
            # Channel list with 🗑 icon and Danger style
            inline_keyboard.append([{"text": f" Remove: {ch}", "callback_data": f"adm_fj_del:{idx}", "style": "danger", "icon_custom_emoji_id": "5422557736330106570"}])
    
    # Add Channel button with ➕ icon
    inline_keyboard.append([{"text": " Add New Channel", "callback_data": "adm_fj_add", "style": "primary", "icon_custom_emoji_id": "5420323438508155202"}])
    # Back button with ⬅️ icon
    inline_keyboard.append([{"text": " Back to Admin", "callback_data": "adm_main_menu", "style": "danger", "icon_custom_emoji_id": "5267490665117275176"}])
    
    text = (
        f"<tg-emoji emoji-id='5420517437885943844'>🔗</tg-emoji> <b>FORCE JOIN MANAGEMENT</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "Configure the channels users must join before using the bot.\n"
        "<i>Click the toggle to enable/disable the system.</i>"
    )
    edit_bot_message(chat_id, message_id, text, {"inline_keyboard": inline_keyboard})

def render_admin_user_mgmt_menu(chat_id, message_id):
    text = (
        f"<tg-emoji emoji-id='5352861489541714456'>👤</tg-emoji> <b>USER MANAGEMENT</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "Search for users to view profiles, manage their balances, or restrict their access."
    )
    inline_keyboard = [
        [{"text": " User Profile", "callback_data": "adm_um_prof", "style": "primary", "icon_custom_emoji_id": "5463352748751753567"}],
        [
            {"text": " Manage Balance", "callback_data": "adm_um_bal", "style": "success", "icon_custom_emoji_id": "5352838545826420397"},
            {"text": " Ban / Unban", "callback_data": "adm_um_ban", "style": "danger", "icon_custom_emoji_id": "5422557736330106570"}
        ],
        [{"text": " Back to Admin", "callback_data": "adm_main_menu", "style": "danger", "icon_custom_emoji_id": "5267490665117275176"}]
    ]
    edit_bot_message(chat_id, message_id, text, {"inline_keyboard": inline_keyboard})

def render_um_profile(chat_id, message_id, target_uid):
    stats = admin_db.get("user_stats", {}).get(str(target_uid), {"otp_count": 0, "balance": 0.0})
    is_banned = str(target_uid) in admin_db.get("banned_users", [])
    status_text = "Banned 🚫" if is_banned else "Active ✅"
    
    text = (
        f"╔═══════════════╗\n"
        f"║ <tg-emoji emoji-id='5352861489541714456'>👤</tg-emoji> <b>USER PROFILE</b>\n"
        f"╚═══════════════╝\n\n"
        f"<b>User ID:</b> <code>{target_uid}</code>\n"
        f"<b>Status:</b> <b>{status_text}</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"<tg-emoji emoji-id='5352838545826420397'>💎</tg-emoji> <b>Balance:</b> <code>{stats.get('balance', 0.0)} ৳</code>\n"
        f"<tg-emoji emoji-id='5352694861990501856'>✅</tg-emoji> <b>Total OTPs:</b> <code>{stats.get('otp_count', 0)}</code>\n"
    )
    inline_keyboard = [
        [{"text": " Manage Balance", "callback_data": f"adm_um_view_bal:{target_uid}", "style": "success", "icon_custom_emoji_id": "5352838545826420397"}],
        [{"text": " Ban / Unban", "callback_data": f"adm_um_view_ban:{target_uid}", "style": "danger", "icon_custom_emoji_id": "5422557736330106570"}],
        [{"text": " Back to Menu", "callback_data": "adm_user_mgmt_menu", "style": "danger", "icon_custom_emoji_id": "5267490665117275176"}]
    ]
    if message_id: edit_bot_message(chat_id, message_id, text, {"inline_keyboard": inline_keyboard})
    else: send_bot_message(chat_id, text, {"inline_keyboard": inline_keyboard})

def render_um_balance(chat_id, message_id, target_uid):
    stats = admin_db.get("user_stats", {}).get(str(target_uid), {"otp_count": 0, "balance": 0.0})
    text = (
        f"<tg-emoji emoji-id='5352838545826420397'>💎</tg-emoji> <b>MANAGE BALANCE</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n\n"
        f"<b>User ID:</b> <code>{target_uid}</code>\n"
        f"<b>Current Balance:</b> <code>{stats.get('balance', 0.0)} ৳</code>\n\n"
        f"<i>Choose an action below to add or deduct balance.</i>"
    )
    inline_keyboard = [
        [
            {"text": " Add Balance", "callback_data": f"adm_bal_add:{target_uid}", "style": "success", "icon_custom_emoji_id": "5420323438508155202"},
            {"text": " Deduct Balance", "callback_data": f"adm_bal_sub:{target_uid}", "style": "danger", "icon_custom_emoji_id": "5422557736330106570"}
        ],
        [{"text": " Back to Profile", "callback_data": f"adm_um_view_prof:{target_uid}", "style": "primary", "icon_custom_emoji_id": "5267490665117275176"}]
    ]
    if message_id: edit_bot_message(chat_id, message_id, text, {"inline_keyboard": inline_keyboard})
    else: send_bot_message(chat_id, text, {"inline_keyboard": inline_keyboard})

def render_um_ban(chat_id, message_id, target_uid):
    is_banned = str(target_uid) in admin_db.get("banned_users", [])
    status_text = f"BANNED {get_pemoji('error', '🚫')}" if is_banned else f"ACTIVE {get_pemoji('done', '✅')}"
    
    text = (
        f"<tg-emoji emoji-id='5422557736330106570'>🚫</tg-emoji> <b>BAN / UNBAN USER</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n\n"
        f"<b>User ID:</b> <code>{target_uid}</code>\n"
        f"<b>Current Status:</b> <b>{status_text}</b>\n\n"
        f"<i>Banned users cannot use any bot commands or features.</i>"
    )
    
    btn_text = " Unban User" if is_banned else " Ban User"
    btn_icon = "5352694861990501856" if is_banned else "5420130255174145507"
    btn_style = "success" if is_banned else "danger"
    
    inline_keyboard = [
        [{"text": btn_text, "callback_data": f"adm_ban_tog:{target_uid}", "style": btn_style, "icon_custom_emoji_id": btn_icon}],
        [{"text": " Back to Profile", "callback_data": f"adm_um_view_prof:{target_uid}", "style": "primary", "icon_custom_emoji_id": "5267490665117275176"}]
    ]
    if message_id: edit_bot_message(chat_id, message_id, text, {"inline_keyboard": inline_keyboard})
    else: send_bot_message(chat_id, text, {"inline_keyboard": inline_keyboard})

def render_admin_management_menu(chat_id, message_id):
    admins = admin_db.get("admins", [OWNER_ID])
    inline_keyboard = []
    
    for adm in admins:
        if adm == OWNER_ID:
            inline_keyboard.append([{"text": f" Owner: {adm}", "callback_data": "none", "style": "primary", "icon_custom_emoji_id": "5353032893096567467"}])
        else:
            inline_keyboard.append([{"text": f" Delete: {adm}", "callback_data": f"adm_admin_del:{adm}", "style": "danger", "icon_custom_emoji_id": "5422557736330106570"}])
    
    inline_keyboard.append([{"text": " Add Admin", "callback_data": "adm_admin_add", "style": "success", "icon_custom_emoji_id": "5420323438508155202"}])
    inline_keyboard.append([{"text": " Back", "callback_data": "adm_main_menu", "style": "danger", "icon_custom_emoji_id": "5267490665117275176"}])
    
    text = f"{get_pemoji('user', '👤')} <b>ADMIN MANAGEMENT</b>\n━━━━━━━━━━━━━━━━━━\nManage your bot admins below:"
    if message_id:
        edit_bot_message(chat_id, message_id, text, {"inline_keyboard": inline_keyboard})
    else:
        send_bot_message(chat_id, text, {"inline_keyboard": inline_keyboard})

def render_admin_system_menu(chat_id, message_id):
    text = (
        f"<tg-emoji emoji-id='5420155432272438703'>⚙️</tg-emoji> <b>SYSTEM CONTROL PANEL</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "Select an option to manage the core systems:"
    )
    inline_keyboard = [
        [
            {"text": " Panel Management", "callback_data": "adm_panel_mgmt_menu", "style": "primary", "icon_custom_emoji_id": "5420155432272438703"}
        ],
        [
            {"text": " Upload Flag", "callback_data": "adm_prem_flag", "style": "success", "icon_custom_emoji_id": "5352838545826420397"},
            {"text": " Upload App", "callback_data": "adm_prem_app", "style": "success", "icon_custom_emoji_id": "5348494358205207761"}
        ],
        [{"text": " Manage Otp Group", "callback_data": "adm_otp_grp_menu", "style": "primary", "icon_custom_emoji_id": "5420145051336485498"}],
        [{"text": " Back to Admin", "callback_data": "adm_main_menu", "style": "danger", "icon_custom_emoji_id": "5267490665117275176"}]
    ]
    edit_bot_message(chat_id, message_id, text, {"inline_keyboard": inline_keyboard})

def render_admin_otp_grp_menu(chat_id, message_id):
    link = admin_db.get("otp_group_link", "")
    fwd_groups = admin_db.get("forward_groups", [])
    
    text = f"{get_pemoji('gear', '⚙️')} <b>OTP GROUP MANAGEMENT</b>\n━━━━━━━━━━━━━━━━━━\n\n"
    text += f"<b>User Button Link:</b>\n<code>{escape_html(link) if link else 'Not Set'}</code>\n\n"
    text += f"<b>Forward Groups ({len(fwd_groups)}):</b>\n"
    
    inline_keyboard = [
        [{"text": " Edit User Button Link", "callback_data": "adm_otp_edit_link", "style": "primary", "icon_custom_emoji_id": "5395444784611480792"}]
    ]
    
    for idx, grp in enumerate(fwd_groups):
        g_id = grp.get("id")
        btns = len(grp.get("buttons", []))
        inline_keyboard.append([{"text": f" FWD: {g_id} ({btns} Btns)", "callback_data": f"adm_fwd_view:{idx}", "style": "success", "icon_custom_emoji_id": "5789428375261023681"}])
        
    inline_keyboard.append([{"text": " Add Forward Group", "callback_data": "adm_fwd_add", "style": "success", "icon_custom_emoji_id": "5420323438508155202"}])
    inline_keyboard.append([{"text": " Back to System", "callback_data": "adm_system_menu", "style": "danger", "icon_custom_emoji_id": "5267490665117275176"}])
    
    edit_bot_message(chat_id, message_id, text, {"inline_keyboard": inline_keyboard})

def render_admin_fwd_view(chat_id, message_id, idx):
    fwd_groups = admin_db.get("forward_groups", [])
    if idx >= len(fwd_groups): return
    grp = fwd_groups[idx]
    g_id = grp.get("id")
    btns = grp.get("buttons", [])
    
    text = f"{get_pemoji('gear', '⚙️')} <b>FORWARD GROUP: {g_id}</b>\n━━━━━━━━━━━━━━━━━━\nManage inline buttons for this forward group:\n"
    
    inline_keyboard = []
    for b_idx, btn in enumerate(btns):
        inline_keyboard.append([{"text": f"❌ {btn['text']} - {btn['url'][:15]}...", "callback_data": f"adm_fwd_btn_del:{idx}:{b_idx}", "style": "danger", "icon_custom_emoji_id": "5422557736330106570"}])
        
    inline_keyboard.append([{"text": " Add Inline Button", "callback_data": f"adm_fwd_btn_add:{idx}", "style": "success", "icon_custom_emoji_id": "5420323438508155202"}])
    inline_keyboard.append([{"text": " Remove Forward Group", "callback_data": f"adm_fwd_del:{idx}", "style": "danger", "icon_custom_emoji_id": "5422557736330106570"}])
    inline_keyboard.append([{"text": " Back", "callback_data": "adm_otp_grp_menu", "style": "danger", "icon_custom_emoji_id": "5267490665117275176"}])
    
    edit_bot_message(chat_id, message_id, text, {"inline_keyboard": inline_keyboard})

def render_admin_firebase_menu(chat_id, message_id):
    status = "✅ Connected" if db_firestore else "❌ Not Connected"
    
    text = (
        f"<tg-emoji emoji-id='5337267511261960341'>🔥</tg-emoji> <b>FIREBASE CONTROL PANEL</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        f"<b>Status:</b> {status}\n"
        f"<b>Auto-Sync:</b> Every 5 Minutes 🔄\n\n"
        "<i>Syncs: User Balances, Panels, Services & Config.</i>"
    )
    inline_keyboard = [
        [
            {"text": " Force Sync Database", "callback_data": "adm_fb_sync_users", "style": "success", "icon_custom_emoji_id": "5465368548702446780"}
        ],
        [{"text": " Back to System", "callback_data": "adm_system_menu", "style": "danger", "icon_custom_emoji_id": "5267490665117275176"}]
    ]
    edit_bot_message(chat_id, message_id, text, {"inline_keyboard": inline_keyboard})

def render_admin_panel_mgmt_menu(chat_id, message_id):
    text = (
        f"{get_pemoji('gear', '⚙️')} <b>PANEL MANAGEMENT</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "Configure your API panels and traffic filters:"
    )
    inline_keyboard = [
        [
            {"text": " Manage Panel", "callback_data": "adm_pnl_home", "style": "primary", "icon_custom_emoji_id": "5366231924597604153"},
            {"text": " Manage Traffic", "callback_data": "adm_trf_home", "style": "success", "icon_custom_emoji_id": "5352877703043258544"}
        ],
        [
            {"text": " Manage Service", "callback_data": "adm_svc_home", "style": "success", "icon_custom_emoji_id": "5366231924597604153"},
            {"text": " Search Country", "callback_data": "adm_srch_home", "style": "primary", "icon_custom_emoji_id": "5463352748751753567"}
        ],
        [{"text": " Back to System", "callback_data": "adm_system_menu", "style": "danger", "icon_custom_emoji_id": "5267490665117275176"}]
    ]
    edit_bot_message(chat_id, message_id, text, {"inline_keyboard": inline_keyboard})

def render_admin_trf_home(chat_id, message_id):
    text = f"{get_pemoji('dashboard', '📊')} <b>TRAFFIC MANAGEMENT</b>\n━━━━━━━━━━━━━━━━━━\nSelect a panel to manage its traffic logging:"
    inline_keyboard = []
    
    for p in panels:
        inline_keyboard.append([{"text": f" {p['name']}", "callback_data": f"adm_trf_pnl:{p['id']}", "style": "primary", "icon_custom_emoji_id": "5352877703043258544"}])
        
    inline_keyboard.append([{"text": " Back", "callback_data": "adm_panel_mgmt_menu", "style": "danger", "icon_custom_emoji_id": "5267490665117275176"}])
    edit_bot_message(chat_id, message_id, text, {"inline_keyboard": inline_keyboard})

def render_admin_trf_pnl_view(chat_id, message_id, panel_id):
    panel = next((p for p in panels if p["id"] == panel_id), None)
    if not panel: return
    p_name = panel["name"]
    is_active = panel.get("is_traffic_active", True)
    
    status_text = " Traffic Logging: ON" if is_active else " Traffic Logging: OFF"
    status_style = "success" if is_active else "danger"
    status_icon = "5352694861990501856" if is_active else "5420130255174145507"
    
    text = f"{get_pemoji('dashboard', '📊')} <b>TRAFFIC: {p_name}</b>\n━━━━━━━━━━━━━━━━━━\nEnable or disable traffic monitoring for this panel.\n\n<i>If OFF, this panel's logs will not appear in the /traffic menu.</i>"
    inline_keyboard = [
        [{"text": status_text, "callback_data": f"adm_trf_tog_pnl:{panel_id}", "style": status_style, "icon_custom_emoji_id": status_icon}],
        [{"text": " Back to Panels", "callback_data": "adm_trf_home", "style": "danger", "icon_custom_emoji_id": "5267490665117275176"}]
    ]
    edit_bot_message(chat_id, message_id, text, {"inline_keyboard": inline_keyboard})

def render_admin_srch_home(chat_id, message_id):
    text = f"{get_pemoji('search', '🔍')} <b>SEARCH MANAGEMENT</b>\n━━━━━━━━━━━━━━━━━━\nSelect a panel to manage its search routing and allowed country codes:"
    inline_keyboard = []
    for p in panels:
        inline_keyboard.append([{"text": f" {p['name']}", "callback_data": f"adm_srch_pnl:{p['id']}", "style": "primary", "icon_custom_emoji_id": "5463352748751753567"}])
    inline_keyboard.append([{"text": " Back", "callback_data": "adm_panel_mgmt_menu", "style": "danger", "icon_custom_emoji_id": "5267490665117275176"}])
    edit_bot_message(chat_id, message_id, text, {"inline_keyboard": inline_keyboard})

def render_admin_srch_pnl_view(chat_id, message_id, panel_id):
    panel = next((p for p in panels if p["id"] == panel_id), None)
    if not panel: return
    p_name = panel["name"]
    
    search_cfg = admin_db.setdefault("search_cfg", {})
    p_cfg = search_cfg.setdefault(panel_id, {"is_active": True, "prefixes": []})
    is_active = p_cfg.get("is_active", True)
    prefixes = p_cfg.get("prefixes", [])
    
    status_text = " Search Status: ON" if is_active else " Search Status: OFF"
    status_style = "success" if is_active else "danger"
    status_icon = "5352694861990501856" if is_active else "5420130255174145507"
    
    text = f"{get_pemoji('search', '🔍')} <b>SEARCH ROUTES: {p_name}</b>\n━━━━━━━━━━━━━━━━━━\nManage allowed country codes for this panel. If a user searches for a number outside these codes, it will be blocked.\n"
    inline_keyboard = [
        [{"text": status_text, "callback_data": f"adm_srch_tog:{panel_id}", "style": status_style, "icon_custom_emoji_id": status_icon}]
    ]
    
    for pfx in prefixes:
        inline_keyboard.append([{"text": f"❌ Prefix: +{pfx}", "callback_data": f"adm_srch_del:{panel_id}:{pfx}", "style": "danger", "icon_custom_emoji_id": "5422557736330106570"}])
        
    inline_keyboard.append([{"text": " Add Country Code", "callback_data": f"adm_srch_add:{panel_id}", "style": "success", "icon_custom_emoji_id": "5420323438508155202"}])
    inline_keyboard.append([{"text": " Back to Panels", "callback_data": "adm_srch_home", "style": "danger", "icon_custom_emoji_id": "5267490665117275176"}])
    edit_bot_message(chat_id, message_id, text, {"inline_keyboard": inline_keyboard})

def render_admin_svc_home(chat_id, message_id):
    text = f"{get_pemoji('gear', '⚙️')} <b>SELECT PANEL</b>\n━━━━━━━━━━━━━━━━━━\nSelect a panel to manage its services:"
    inline_keyboard = []
    
    for p in panels:
        inline_keyboard.append([{"text": f" {p['name']}", "callback_data": f"adm_svc_pnl:{p['id']}", "style": "primary", "icon_custom_emoji_id": "5366231924597604153"}])
        
    inline_keyboard.append([{"text": " Back", "callback_data": "adm_panel_mgmt_menu", "style": "danger", "icon_custom_emoji_id": "5267490665117275176"}])
    edit_bot_message(chat_id, message_id, text, {"inline_keyboard": inline_keyboard})

def render_admin_svc_pnl_view(chat_id, message_id, panel_id):
    services_dict = load_services()
    p_services = services_dict.get(panel_id, [])
    
    panel = next((p for p in panels if p["id"] == panel_id), None)
    if not panel: return
    p_name = panel["name"]
    is_active = panel.get("is_active", True)
    
    status_text = " Panel Status: ON" if is_active else " Panel Status: OFF"
    status_style = "success" if is_active else "danger"
    status_icon = "5352694861990501856" if is_active else "5420130255174145507"
    
    text = f"{get_pemoji('gear', '⚙️')} <b>SERVICES: {p_name}</b>\n━━━━━━━━━━━━━━━━━━\nManage services for this panel:"
    inline_keyboard = [
        [{"text": status_text, "callback_data": f"adm_svc_tog_pnl:{panel_id}", "style": status_style, "icon_custom_emoji_id": status_icon}]
    ]
    
    for s in p_services:
        em_id = get_app_raw_id(s['name'])
        inline_keyboard.append([{"text": f" {s['name']} ({len(s.get('countries', []))} Countries)", "callback_data": f"adm_svc_view:{panel_id}:{s['id']}", "style": "primary", "icon_custom_emoji_id": em_id}])
        
    inline_keyboard.append([{"text": " Add New Service", "callback_data": f"adm_svc_add:{panel_id}", "style": "success", "icon_custom_emoji_id": "5420323438508155202"}])
    inline_keyboard.append([{"text": " Back to Panels", "callback_data": "adm_svc_home", "style": "danger", "icon_custom_emoji_id": "5267490665117275176"}])
    edit_bot_message(chat_id, message_id, text, {"inline_keyboard": inline_keyboard})

def render_admin_svc_view(chat_id, message_id, panel_id, service_id):
    services_dict = load_services()
    p_services = services_dict.get(panel_id, [])
    service = next((s for s in p_services if s["id"] == service_id), None)
    if not service: return
    
    text = f"{get_pemoji('gear', '⚙️')} <b>SERVICE: {service['name'].upper()}</b>\n━━━━━━━━━━━━━━━━━━\nSelect a country to manage ranges:"
    inline_keyboard = []
    
    for c in service.get("countries", []):
        c_info = get_country_info(c['code'])
        name = c.get("name") or c_info["name"]
        em_id = c_info.get("id", "5336972142066047577")
        inline_keyboard.append([{"text": f" {name} ({c['code']}) - {len(c.get('ranges', []))} Ranges", "callback_data": f"adm_svc_ctr:{panel_id}:{service_id}:{c['code']}", "style": "primary", "icon_custom_emoji_id": em_id}])
        
    inline_keyboard.append([{"text": " Add Country", "callback_data": f"adm_svc_add_ctr:{panel_id}:{service_id}", "style": "success", "icon_custom_emoji_id": "5420323438508155202"}])
    inline_keyboard.append([{"text": " Delete Service", "callback_data": f"adm_svc_del:{panel_id}:{service_id}", "style": "danger", "icon_custom_emoji_id": "5422557736330106570"}])
    inline_keyboard.append([{"text": " Back", "callback_data": f"adm_svc_pnl:{panel_id}", "style": "danger", "icon_custom_emoji_id": "5267490665117275176"}])
    edit_bot_message(chat_id, message_id, text, {"inline_keyboard": inline_keyboard})

def render_admin_svc_ctr_view(chat_id, message_id, panel_id, service_id, country_code):
    services_dict = load_services()
    p_services = services_dict.get(panel_id, [])
    service = next((s for s in p_services if s["id"] == service_id), None)
    if not service: return
    country = next((c for c in service.get("countries", []) if c["code"] == country_code), None)
    if not country: return
    
    c_info = get_country_info(country_code)
    text = f"{get_pemoji('gear', '⚙️')} <b>RANGES: {c_info.get('name', country_code)} ({service['name']})</b>\n━━━━━━━━━━━━━━━━━━\n"
    
    ranges = country.get("ranges", [])
    if not ranges: text += "<i>No ranges added yet.</i>\n"
    for idx, r in enumerate(ranges):
        text += f"{idx+1}. <code>{r}</code>\n"
        
    inline_keyboard = [
        [{"text": " Add Range", "callback_data": f"adm_svc_add_rg:{panel_id}:{service_id}:{country_code}", "style": "success", "icon_custom_emoji_id": "5420323438508155202"}],
        [{"text": " Clear All Ranges", "callback_data": f"adm_svc_clr_rg:{panel_id}:{service_id}:{country_code}", "style": "danger", "icon_custom_emoji_id": "5422557736330106570"}],
        [{"text": " Remove Country", "callback_data": f"adm_svc_del_ctr:{panel_id}:{service_id}:{country_code}", "style": "danger", "icon_custom_emoji_id": "5422557736330106570"}],
        [{"text": " Back", "callback_data": f"adm_svc_view:{panel_id}:{service_id}", "style": "danger", "icon_custom_emoji_id": "5267490665117275176"}]
    ]
    edit_bot_message(chat_id, message_id, text, {"inline_keyboard": inline_keyboard})

def render_panel_list(chat_id, message_id):
    text = (
        f"{get_pemoji('gear', '⚙️')} <b>PANEL SELECTION</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "Select a panel to configure its API/Login settings:"
    )
    
    # আলাদা আলাদা প্যানেলের জন্য আলাদা আলাদা প্রিমিয়াম ইমোজি আইডি
    panel_emojis = {
        "stexsms": "5336972142066047577", # Chrome
        "xmint": "5336879280578138635",   # Gem
        "mk": "5352552689983067014",      # Proton VPN
        "nexa": "5352838545826420397"     # Express VPN
    }
    
    inline_keyboard = []
    row = []
    for idx, p in enumerate(panels):
        btn_text = f" {p['name']}"
        emoji_id = panel_emojis.get(p.get('id', 'stexsms'), "5366231924597604153") # Default
        
        row.append({"text": btn_text, "callback_data": f"adm_pnl_view:{idx}", "style": "primary", "icon_custom_emoji_id": emoji_id})
        if len(row) == 2:
            inline_keyboard.append(row)
            row = []
    if row:
        inline_keyboard.append(row)
        
    inline_keyboard.append([{"text": " Back", "callback_data": "adm_panel_mgmt_menu", "style": "danger", "icon_custom_emoji_id": "5267490665117275176"}])
    edit_bot_message(chat_id, message_id, text, {"inline_keyboard": inline_keyboard})

def render_panel_details(chat_id, message_id, p_idx):
    if p_idx >= len(panels):
        edit_bot_message(chat_id, message_id, f"{get_pemoji('error', '❌')} Panel not found.", {"inline_keyboard": [[{"text": " Back", "callback_data": "adm_pnl_home", "style": "danger", "icon_custom_emoji_id": "5267490665117275176"}]]})
        return
    panel = panels[p_idx]
    
    status = panel.get('status', 'Unknown')
    status_icon = get_pemoji("done", "✅") if "LoggedIn" in status or "API" in status else get_pemoji("error", "❌")
    
    baseUrl = normalize_base_url(panel.get("url", ""))
    clean_base = baseUrl.split('#')[0].rstrip('/')
    
    gn_url = panel.get('getNumberUrl') or f"{clean_base}/mapi/v1/mdashboard/getnum/number"
    gm_url = panel.get('getMessageUrl') or f"{clean_base}/mapi/v1/mdashboard/getnum/info"
    tr_url = panel.get('trafficUrl') or f"{clean_base}/mapi/v1/mdashboard/console/info"

    if is_voltx_api(panel):
        api_key = panel.get('password', 'MKJGS2MSZYB')
        text = (
            f"<tg-emoji emoji-id='5420155432272438703'>⚙️</tg-emoji> <b>API CONFIGURATION</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"<tg-emoji emoji-id='5353032893096567467'>👑</tg-emoji> <b>Name:</b> {panel['name']}\n"
            f"<tg-emoji emoji-id='5337267511261960341'>🔥</tg-emoji> <b>Status:</b> <code>{status}</code> {status_icon}\n\n"
            f"<tg-emoji emoji-id='5336972142066047577'>🌐</tg-emoji> <b>1. Base API URL:</b>\n<code>{panel.get('url', '')}</code>\n\n"
            f"<tg-emoji emoji-id='5337255927735163754'>🔐</tg-emoji> <b>2. API Key (Token):</b>\n<code>{api_key}</code>\n\n"
            f"<tg-emoji emoji-id='5352862640592949843'>🔢</tg-emoji> <b>3. Get Number API:</b>\n<code>{gn_url}</code>\n\n"
            f"<tg-emoji emoji-id='5337302974806922068'>💬</tg-emoji> <b>4. Get Message API:</b>\n<code>{gm_url}</code>\n\n"
            f"<tg-emoji emoji-id='5352877703043258544'>📊</tg-emoji> <b>5. Traffic API:</b>\n<code>{tr_url}</code>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"<tg-emoji emoji-id='5192739271886282680'>📝</tg-emoji> <i>Edit system configuration:</i>"
        )
        inline_keyboard = [
            [
                {"text": " Edit Base URL", "callback_data": f"adm_pnl_edit:{p_idx}:url", "style": "primary", "icon_custom_emoji_id": "5336972142066047577"},
                {"text": " Edit API Key", "callback_data": f"adm_pnl_edit:{p_idx}:pass", "style": "success", "icon_custom_emoji_id": "5337255927735163754"}
            ],
            [
                {"text": " Edit GetNum URL", "callback_data": f"adm_pnl_edit:{p_idx}:getnum", "style": "primary", "icon_custom_emoji_id": "5337132498965010628"},
                {"text": " Edit GetMsg URL", "callback_data": f"adm_pnl_edit:{p_idx}:getmsg", "style": "primary", "icon_custom_emoji_id": "5395444784611480792"}
            ],
            [
                {"text": " Edit Traffic URL", "callback_data": f"adm_pnl_edit:{p_idx}:traffic", "style": "primary", "icon_custom_emoji_id": "5352877703043258544"}
            ],
            [{"text": " Back", "callback_data": "adm_pnl_home", "style": "danger", "icon_custom_emoji_id": "5267490665117275176"}]
        ]
    else:
        raw_user = panel.get('username', 'N/A')
        masked_user = raw_user
        if "@" in raw_user:
            u_parts = raw_user.split("@")
            masked_user = f"{u_parts[0][0]}*****@{u_parts[1]}"
        masked_pass = "********" if panel.get('password') else "N/A"
        text = (
            f"<tg-emoji emoji-id='5420155432272438703'>⚙️</tg-emoji> <b>PANEL CONFIGURATION</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"<tg-emoji emoji-id='5353032893096567467'>👑</tg-emoji> <b>Name:</b> {panel['name']}\n"
            f"<tg-emoji emoji-id='5337267511261960341'>🔥</tg-emoji> <b>Status:</b> <code>{status}</code> {status_icon}\n\n"
            f"<tg-emoji emoji-id='5336972142066047577'>🌐</tg-emoji> <b>1. Login Link:</b>\n<code>{panel.get('url', 'https://stexsms.com/mauth/login')}</code>\n\n"
            f"<tg-emoji emoji-id='5348494358205207761'>🐁</tg-emoji> <b>2. Login Gmail:</b>\n<code>{masked_user}</code>\n\n"
            f"<tg-emoji emoji-id='5337255927735163754'>🔐</tg-emoji> <b>3. Login Pass:</b>\n<code>Password {masked_pass}</code>\n\n"
            f"<tg-emoji emoji-id='5352862640592949843'>🔢</tg-emoji> <b>4. Get Number API:</b>\n<code>{gn_url}</code>\n\n"
            f"<tg-emoji emoji-id='5337302974806922068'>💬</tg-emoji> <b>5. Get Message API:</b>\n<code>{gm_url}</code>\n\n"
            f"<tg-emoji emoji-id='5352877703043258544'>📊</tg-emoji> <b>6. Traffic API:</b>\n<code>{tr_url}</code>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"<tg-emoji emoji-id='5192739271886282680'>📝</tg-emoji> <i>Edit system configuration:</i>"
        )
        
        inline_keyboard = [
            [
                {"text": " Edit Login URL", "callback_data": f"adm_pnl_edit:{p_idx}:url", "style": "primary", "icon_custom_emoji_id": "5336972142066047577"},
                {"text": " Edit Gmail", "callback_data": f"adm_pnl_edit:{p_idx}:user", "style": "primary", "icon_custom_emoji_id": "5352861489541714456"}
            ],
            [
                {"text": " Edit Password", "callback_data": f"adm_pnl_edit:{p_idx}:pass", "style": "primary", "icon_custom_emoji_id": "5337255927735163754"},
                {"text": " Edit GetNum", "callback_data": f"adm_pnl_edit:{p_idx}:getnum", "style": "primary", "icon_custom_emoji_id": "5337132498965010628"}
            ],
            [
                {"text": " Edit GetMsg", "callback_data": f"adm_pnl_edit:{p_idx}:getmsg", "style": "primary", "icon_custom_emoji_id": "5395444784611480792"},
                {"text": " Edit Traffic", "callback_data": f"adm_pnl_edit:{p_idx}:traffic", "style": "primary", "icon_custom_emoji_id": "5352877703043258544"}
            ],
            [{"text": " Back", "callback_data": "adm_pnl_home", "style": "danger", "icon_custom_emoji_id": "5267490665117275176"}]
        ]
    edit_bot_message(chat_id, message_id, text, {"inline_keyboard": inline_keyboard})

def render_admin_dxa_menu(chat_id, message_id):
    cfg = admin_db.get("dxa_config", {})
    w_grp = cfg.get("withdraw_group", "")
    rew = cfg.get("otp_reward", 0.0)
    m_wd = cfg.get("min_withdraw", 20.0)
    mth = cfg.get("methods", [])
    max_c = cfg.get("max_concurrent", 3)
    cd = cfg.get("cooldown", 0)
    
    text = f"{get_pemoji('gem', '💎')} <b>MANAGE DXA (Withdrawal System)</b>\n━━━━━━━━━━━━━━━━━━\n"
    text += f"{get_pemoji('dashboard', '📊')} <b>Withdraw Group:</b> <code>{escape_html(w_grp) if w_grp else 'Not Set'}</code>\n"
    text += f"{get_pemoji('fire', '🔥')} <b>OTP Reward:</b> <code>{rew} ৳</code>\n"
    text += f"{get_pemoji('otp', '🔐')} <b>Min Withdraw:</b> <code>{m_wd} ৳</code>\n"
    text += f"{get_pemoji('user', '👤')} <b>Max Numbers/User:</b> <code>{max_c}</code>\n"
    text += f"{get_pemoji('time', '🕓')} <b>Cooldown:</b> <code>{cd} sec</code>\n"
    text += f"{get_pemoji('note', '📝')} <b>Methods ({len(mth)}):</b> {', '.join(mth) if mth else 'None'}\n"
    
    inline_keyboard = [
        [{"text": " Set Withdraw Group", "callback_data": "adm_dxa_grp", "style": "primary", "icon_custom_emoji_id": "5395444784611480792"}],
        [
            {"text": " OTP Reward", "callback_data": "adm_dxa_rew", "style": "primary", "icon_custom_emoji_id": "5352838545826420397"},
            {"text": " Min Withdraw", "callback_data": "adm_dxa_min", "style": "primary", "icon_custom_emoji_id": "5352862640592949843"}
        ],
        [
            {"text": " Max Numbers", "callback_data": "adm_dxa_maxc", "style": "primary", "icon_custom_emoji_id": "5352861489541714456"},
            {"text": " Cooldown", "callback_data": "adm_dxa_cd", "style": "primary", "icon_custom_emoji_id": "5336983442125001376"}
        ],
        [
            {"text": " Add Method", "callback_data": "adm_dxa_mth_add", "style": "success", "icon_custom_emoji_id": "5420323438508155202"},
            {"text": " Clear Methods", "callback_data": "adm_dxa_mth_clr", "style": "danger", "icon_custom_emoji_id": "5422557736330106570"}
        ],
        [{"text": " Back to Admin", "callback_data": "adm_main_menu", "style": "danger", "icon_custom_emoji_id": "5267490665117275176"}]
    ]
    edit_bot_message(chat_id, message_id, text, {"inline_keyboard": inline_keyboard})

def render_user_balance(chat_id, message_id=None):
    stats = admin_db.get("user_stats", {}).get(str(chat_id), {"otp_count": 0, "balance": 0.0})
    cfg = admin_db.get("dxa_config", {})
    min_wd = cfg.get("min_withdraw", 20.0)
    methods = cfg.get("methods", [])
    
    text = f"━━━━━━━━━━━━\n"
    text += f"《 {get_pemoji('dxa', '😒')} <b>Profile</b> 》\n"
    text += f"━━━━━━━━━━━━\n"
    text += f"{get_pemoji('done', '👋')} <b>Total Otp:</b> {stats.get('otp_count', 0)}\n"
    text += f"━━━━━━━━━━━━\n"
    text += f"{get_pemoji('user', '👤')} <b>User Id:</b> <code>{chat_id}</code>\n"
    text += f"━━━━━━━━━━━━\n"
    text += f"{get_pemoji('gem', '📅')} <b>BALANCE:</b> {stats.get('balance', 0.0)} ৳\n"
    text += f"━━━━━━━━━━━━\n"
    text += f"{get_pemoji('otp', '🔐')} <b>MINIMUM:</b> {min_wd} ৳\n"
    text += f"━━━━━━━━━━━━\n"
    text += f"<b>SELECT METHOD:</b>"
    
    inline_keyboard = []
    row = []
    for m in methods:
        row.append({"text": f" {m}", "callback_data": f"usr_wd_{m}", "style": "success", "icon_custom_emoji_id": "5352585194295564660"})
        if len(row) == 2:
            inline_keyboard.append(row)
            row = []
    if row:
        inline_keyboard.append(row)
        
    if message_id:
        edit_bot_message(chat_id, message_id, text, {"inline_keyboard": inline_keyboard} if inline_keyboard else None)
    else:
        send_bot_message(chat_id, text, {"inline_keyboard": inline_keyboard} if inline_keyboard else None)

def get_bot_menu_keyboard(chat_id):
    keyboard = [
        [
            {"text": "GET NUMBER", "style": "primary", "icon_custom_emoji_id": "5337132498965010628"}, 
            {"text": "SEARCH NUMBER", "style": "success", "icon_custom_emoji_id": "5463352748751753567"}
        ],
        [
            {"text": "TRAFFIC", "style": "primary", "icon_custom_emoji_id": "5352877703043258544"},
            {"text": "BALANCE", "style": "success", "icon_custom_emoji_id": "5352838545826420397"}
        ]
    ]
    
    if str(chat_id) in admin_db.get("admins", [OWNER_ID]):
        keyboard.append([{"text": "ADMIN PANEL", "style": "danger", "icon_custom_emoji_id": "5420155432272438703"}])
        
    return {"keyboard": keyboard, "resize_keyboard": True}

# ----------------------------------------------------
# Service selections UI layouts
# ----------------------------------------------------

def render_services_list(chat_id, message_id=None):
    services_dict = load_services()
    merged_services = {}
    
    active_panel_ids = [p["id"] for p in panels if p.get("is_active", True)]
    
    for p_id, s_list in services_dict.items():
        if p_id not in active_panel_ids: continue
        for s in s_list:
            if s["id"] not in merged_services:
                merged_services[s["id"]] = {"id": s["id"], "name": s["name"]}
                
    text = f"{get_pemoji('phone', '📱')} <b>Select a service:</b>"
    
    inline_keyboard = []
    if not merged_services:
        inline_keyboard.append([{"text": " No Services Available", "callback_data": "none", "style": "danger", "icon_custom_emoji_id": "5336944168944047463"}])
    else:
        for s_id, s_data in merged_services.items():
            em_id = get_app_raw_id(s_data['name'])
            inline_keyboard.append([{"text": f" {s_data['name']}", "callback_data": f"usr_srv_sel:{s_id}", "style": "primary", "icon_custom_emoji_id": em_id}])

    keyboard = {"inline_keyboard": inline_keyboard}
    if message_id:
        edit_bot_message(chat_id, message_id, text, keyboard)
    else:
        send_bot_message(chat_id, text, keyboard)

def render_countries_list(chat_id, message_id, service_id):
    services_dict = load_services()
    merged_countries = {}
    service_name = "Unknown"
    
    active_panel_ids = [p["id"] for p in panels if p.get("is_active", True)]
    
    for p_id, s_list in services_dict.items():
        if p_id not in active_panel_ids: continue
        for s in s_list:
            if s["id"] == service_id:
                service_name = s["name"]
                for c in s.get("countries", []):
                    if len(c.get("ranges", [])) > 0:
                        merged_countries[c["code"]] = c

    if not merged_countries:
        edit_bot_message(chat_id, message_id, f"{get_pemoji('error', '❌')} No countries are currently configured for <b>{escape_html(service_name)}</b>.", {
            "inline_keyboard": [[{"text": " Back", "callback_data": "usr_menu_home", "style": "danger", "icon_custom_emoji_id": "5267490665117275176"}]]
        })
        return

    text = f"{get_pemoji('phone', '📱')} <b>Select a country for {service_name.upper()}:</b>"
    inline_keyboard = []
    
    for code, c in merged_countries.items():
        c_info = get_country_info(code)
        name = c.get("name") or c_info["name"]
        em_id = c_info.get("id", "5336972142066047577")
        inline_keyboard.append([
            {"text": f" {name} ({code})", "callback_data": f"usr_ctr_sel:{service_id}:{code}", "style": "primary", "icon_custom_emoji_id": em_id}
        ])
        
    inline_keyboard.append([{"text": " Back", "callback_data": "usr_menu_home", "style": "danger", "icon_custom_emoji_id": "5267490665117275176"}])
    edit_bot_message(chat_id, message_id, text, {"inline_keyboard": inline_keyboard})

def allocate_and_show_number_py(chat_id, message_id, service_id, country_code, callback_id=None):
    passed, err_msg, batch_size = check_user_limits(chat_id)
    if not passed:
        if callback_id:
            answer_callback(callback_id, err_msg, show_alert=True)
        else:
            kb = {"inline_keyboard": [[{"text": " Back", "callback_data": f"usr_srv_sel:{service_id}", "style": "danger", "icon_custom_emoji_id": "5267490665117275176"}]]}
            edit_bot_message(chat_id, message_id, f"⚠️ {err_msg}", kb)
        return

    if callback_id:
        answer_callback(callback_id, "Allocating number...")

    services_dict = load_services()
    available_panels = []
    service_name = "Unknown"
    
    active_panel_ids = [p["id"] for p in panels if p.get("is_active", True)]
    
    for p_id, s_list in services_dict.items():
        if p_id not in active_panel_ids: continue
        for s in s_list:
            if s["id"] == service_id:
                service_name = s["name"]
                for c in s.get("countries", []):
                    if c["code"] == country_code and len(c.get("ranges", [])) > 0:
                        available_panels.append({"panel_id": p_id, "ranges": c["ranges"]})
                        
    if not available_panels:
        edit_bot_message(chat_id, message_id, f"{get_pemoji('error', '❌')} No ranges configured for this selection.", {
            "inline_keyboard": [[{"text": " Back", "callback_data": f"usr_srv_sel:{service_id}", "style": "danger", "icon_custom_emoji_id": "5267490665117275176"}]]
        })
        return

    chosen_setup = random.choice(available_panels)
    panel_id = chosen_setup["panel_id"]
    range_val = random.choice(chosen_setup["ranges"]).strip().upper()
    
    if not any(c in range_val for c in ("X", "x", "*")) and range_val.isdigit():
        range_val += "XXX"
        
    wait_emoji = get_pemoji("wait", "⏳")
    edit_bot_message(chat_id, message_id, f"{wait_emoji} <i>Allocating {batch_size} number(s) for <b>{escape_html(service_name)}</b>... Please wait.</i>")
    
    numbers_fetched = []
    last_err = "Unknown error"
    if "active_numbers" not in admin_db: admin_db["active_numbers"] = {}
    
    for _ in range(batch_size):
        result = buy_number(range_val, panel_id)
        if result.get("success"):
            numbers_fetched.append(result)
            number_val = result.get("number") or ""
            clean_num = str(number_val).replace("+", "").strip()
            admin_db["active_numbers"][clean_num] = str(chat_id)
        else:
            last_err = result.get("message", "Failed to retrieve.")
            break
            
    if numbers_fetched:
        save_admin_db()
        blank_text = "ㅤ"
        svc_em_id = get_app_raw_id(service_name)
        
        inline_keyboard = [
            [{"text": f" {service_name}", "callback_data": "none", "style": "success", "icon_custom_emoji_id": svc_em_id}]
        ]
        
        for res in numbers_fetched:
            num = res.get("number", "")
            actual_c_code = get_country_code(num)
            c_info_actual = get_country_info(actual_c_code)
            actual_flag_em_id = c_info_actual.get("id", "5336972142066047577")
            
            inline_keyboard.append([{
                "text": f" +{num.replace('+', '')}",
                "copy_text": {"text": f"{num}"},
                "style": "primary",
                "icon_custom_emoji_id": actual_flag_em_id
            }])
            
        inline_keyboard.extend([
            [
                {"text": " Change Number", "callback_data": f"usr_change_num:{service_id}:{country_code}", "style": "danger", "icon_custom_emoji_id": "5420155432272438703"},
                get_otp_group_btn()
            ],
            [{"text": " Back", "callback_data": f"usr_srv_sel:{service_id}", "style": "danger", "icon_custom_emoji_id": "5267490665117275176"}]
        ])
        edit_bot_message(chat_id, message_id, blank_text, {"inline_keyboard": inline_keyboard})
    else:
        failure_text = f"{get_pemoji('error', '❌')} <b>Get Number Failed!</b>\n\n" \
                       f"<b>Service:</b> {escape_html(service_name)}\n" \
                       f"<b>Country:</b> {escape_html(country_code)}\n" \
                       f"<b>Range tried:</b> <code>{escape_html(range_val)}</code>\n" \
                       f"<b>Error:</b> <code>{escape_html(last_err)}</code>\n\n" \
                       f"<i>Please try again.</i>"
        
        inline_keyboard = [
            [
                {"text": " Retry Allocating", "callback_data": f"usr_change_num:{service_id}:{country_code}", "style": "success", "icon_custom_emoji_id": "5465368548702446780"},
                {"text": " Back to Countries", "callback_data": f"usr_srv_sel:{service_id}", "style": "danger", "icon_custom_emoji_id": "5267490665117275176"}
            ]
        ]
        edit_bot_message(chat_id, message_id, failure_text, {"inline_keyboard": inline_keyboard})

# ----------------------------------------------------
# Telegram Bot Inbound Controllers
# ----------------------------------------------------

def handle_callback_query(callback_query):
    callback_id = callback_query.get("id")
    chat_id = callback_query.get("message", {}).get("chat", {}).get("id")
    message_id = callback_query.get("message", {}).get("message_id")
    data = callback_query.get("data", "")
    
    if not chat_id or not message_id:
        answer_callback(callback_id)
        return

    # 🚫 Check Ban Status
    if str(chat_id) in admin_db.get("banned_users", []):
        answer_callback(callback_id, "🚫 You are banned from using this bot.", show_alert=True)
        return

    # 🔄 গ্লোবাল স্টেট রিসেট: যেকোনো ব্যাক বা হোম বাটনে ক্লিক করলে আগের পেন্ডিং ইনপুট মুছে যাবে
    if data in ["usr_menu_home", "adm_main_menu", "adm_admin_menu", "adm_fj_menu", "adm_system_menu", "adm_firebase_menu", "adm_svc_home", "adm_panel_mgmt_menu", "adm_trf_home", "adm_srch_home"]:
        user_conversations.pop(chat_id, None)
        
    if data.startswith("adm_svc_view:") or data.startswith("adm_svc_ctr:"):
        user_conversations.pop(chat_id, None)

    logger.info(f"Bot Callback Triggered: data='{data}'")

    if data == "usr_menu_home":
        answer_callback(callback_id)
        render_services_list(chat_id, message_id)
        
    elif data == "usr_search_home":
        user_conversations.pop(chat_id, None) # আগের স্টেট ক্লিয়ার
        answer_callback(callback_id, "Opening Search Menu...")
        user_conversations[chat_id] = "waiting_for_search"
        text_help = (
            "╔═══════════╗\n"
            f"     {get_pemoji('search', '🔍')} <b>SEARCH NUMBER</b>\n"
            "╚═══════════╝\n"
            f"{get_pemoji('done', '📌')} Enter 3 to 9 digits  \n"
            "to search for a number.\n"
            "━━━━━━━━━━━━━\n"
            f"<tg-emoji emoji-id='5395444784611480792'>📝</tg-emoji> Example:\n"
            "➥ 880\n"
            "➥ 9227373\n"
            "━━━━━━━━━━━━━\n"
            f"{get_pemoji('search', '🔍')} Fast Number Lookup System"
        )
        edit_bot_message(chat_id, message_id, text_help, {"inline_keyboard": [[{"text": " Back", "callback_data": "usr_menu_home", "style": "danger", "icon_custom_emoji_id": "5267490665117275176"}]]})
        
    elif data.startswith("usr_srv_sel:"):
        service_id = data.split(":")[1]
        answer_callback(callback_id, "Loading countries...")
        render_countries_list(chat_id, message_id, service_id)
        
    elif data.startswith("usr_ctr_sel:"):
        parts = data.split(":")
        service_id = parts[1]
        country_code = parts[2]
        allocate_and_show_number_py(chat_id, message_id, service_id, country_code, callback_id)
        
    elif data.startswith("usr_change_num:"):
        parts = data.split(":")
        service_id = parts[1]
        country_code = parts[2]
        allocate_and_show_number_py(chat_id, message_id, service_id, country_code, callback_id)
        
    elif data.startswith("buy_"):
        range_val = data.split("_")[1]
        trigger_buy_number(chat_id, range_val, message_id=message_id, callback_id=callback_id)

    elif data == "usr_otp_grp":
        # চ্যাটে মেসেজ পাঠানোর অংশটি ডিলিট করা হয়েছে। এখন লিংক না থাকলে শুধু ছোট্ট পপ-আপ দেখাবে।
        answer_callback(callback_id, "OTP Group link is not set by admin yet!", show_alert=True)

    elif data == "tr_refresh":
         answer_callback(callback_id, "Refreshing traffic dashboard...")
         render_traffic_home(chat_id, message_id)

    elif data == "tr_close":
         answer_callback(callback_id, "Closed")
         call_telegram("deleteMessage", {"chat_id": chat_id, "message_id": message_id})

    elif data == "adm_coming_soon":
         answer_callback(callback_id, "🚧 This feature is coming soon!")

    elif data == "adm_user_mgmt_menu":
         user_conversations.pop(chat_id, None)
         answer_callback(callback_id, "Opening User Management...")
         render_admin_user_mgmt_menu(chat_id, message_id)

    elif data in ["adm_um_prof", "adm_um_bal", "adm_um_ban"]:
         action_map = {"adm_um_prof": "Profile", "adm_um_bal": "Balance", "adm_um_ban": "Ban/Unban"}
         action_type = data.split("_")[2]
         answer_callback(callback_id, "Send User ID...")
         user_conversations[chat_id] = f"um_wait_id_{action_type}"
         user_prompts[chat_id] = message_id
         text = f"<tg-emoji emoji-id='5463352748751753567'>🔍</tg-emoji> <b>Search User for {action_map[data]}</b>\n\nPlease send the Telegram User ID (e.g., <code>123456789</code>)."
         edit_bot_message(chat_id, message_id, text, {"inline_keyboard": [[{"text": " Back", "callback_data": "adm_user_mgmt_menu", "style": "danger", "icon_custom_emoji_id": "5267490665117275176"}]]})

    elif data.startswith("adm_um_view_prof:"):
         target_uid = data.split(":")[1]
         answer_callback(callback_id)
         render_um_profile(chat_id, message_id, target_uid)

    elif data.startswith("adm_um_view_bal:"):
         target_uid = data.split(":")[1]
         answer_callback(callback_id)
         render_um_balance(chat_id, message_id, target_uid)

    elif data.startswith("adm_um_view_ban:"):
         target_uid = data.split(":")[1]
         answer_callback(callback_id)
         render_um_ban(chat_id, message_id, target_uid)

    elif data.startswith("adm_bal_add:"):
         target_uid = data.split(":")[1]
         answer_callback(callback_id, "Send Amount...")
         user_conversations[chat_id] = f"um_wait_amt_add_{target_uid}"
         user_prompts[chat_id] = message_id
         text = f"<tg-emoji emoji-id='5420323438508155202'>➕</tg-emoji> <b>Add Balance</b>\n\nUser ID: <code>{target_uid}</code>\nSend the amount to add (e.g., <code>50</code>):"
         edit_bot_message(chat_id, message_id, text, {"inline_keyboard": [[{"text": " Back", "callback_data": f"adm_um_view_bal:{target_uid}", "style": "danger", "icon_custom_emoji_id": "5267490665117275176"}]]})

    elif data.startswith("adm_bal_sub:"):
         target_uid = data.split(":")[1]
         answer_callback(callback_id, "Send Amount...")
         user_conversations[chat_id] = f"um_wait_amt_sub_{target_uid}"
         user_prompts[chat_id] = message_id
         text = f"<tg-emoji emoji-id='5422557736330106570'>➖</tg-emoji> <b>Deduct Balance</b>\n\nUser ID: <code>{target_uid}</code>\nSend the amount to deduct (e.g., <code>50</code>):"
         edit_bot_message(chat_id, message_id, text, {"inline_keyboard": [[{"text": " Back", "callback_data": f"adm_um_view_bal:{target_uid}", "style": "danger", "icon_custom_emoji_id": "5267490665117275176"}]]})

    elif data.startswith("adm_ban_tog:"):
         target_uid = data.split(":")[1]
         banned_list = admin_db.setdefault("banned_users", [])
         if target_uid in banned_list:
             banned_list.remove(target_uid)
             answer_callback(callback_id, "User Unbanned!")
         else:
             banned_list.append(target_uid)
             answer_callback(callback_id, "User Banned!")
         save_admin_db()
         render_um_ban(chat_id, message_id, target_uid)

    elif data == "check_fj":
         answer_callback(callback_id, "Checking Force Join...")
         if check_force_join(chat_id, message_id):
             call_telegram("deleteMessage", {"chat_id": chat_id, "message_id": message_id})
             send_bot_message(chat_id, "✅ <b>Verification Successful!</b>\nWelcome to DXA Bot.", get_bot_menu_keyboard(chat_id))

    elif data == "adm_fj_menu":
         user_conversations.pop(chat_id, None) # 🛠️ চ্যানেল লিংক দেওয়ার স্টেট ক্লিয়ার করা হলো
         answer_callback(callback_id, "Opening Force Join Menu...")
         render_force_join_menu(chat_id, message_id)

    elif data == "adm_fj_toggle":
         answer_callback(callback_id, "Toggling status...")
         admin_db["force_join_status"] = not admin_db.get("force_join_status", False)
         save_admin_db()
         render_force_join_menu(chat_id, message_id)

    elif data.startswith("adm_fj_del:"):
         idx = int(data.split(":")[1])
         answer_callback(callback_id, "Deleting channel...")
         channels = admin_db.get("force_join_channels", [])
         if 0 <= idx < len(channels):
             channels.pop(idx)
             save_admin_db()
         render_force_join_menu(chat_id, message_id)

    elif data == "adm_fj_add":
         answer_callback(callback_id, "Send Channel Link...")
         user_conversations[chat_id] = "waiting_fj_channel"
         text = "🔗 <b>Add Force Join Channel</b>\n\nPlease send the channel username (e.g., <code>@dxa_admin</code>) or an invite link."
         edit_bot_message(chat_id, message_id, text, {"inline_keyboard": [[{"text": " Back", "callback_data": "adm_fj_menu", "style": "danger", "icon_custom_emoji_id": "5267490665117275176"}]]})

    elif data == "adm_admin_menu":
         user_conversations.pop(chat_id, None) # 🛠️ আইডি দেওয়ার স্টেট ক্লিয়ার করা হলো
         answer_callback(callback_id, "Opening Admin Management...")
         render_admin_management_menu(chat_id, message_id)

    elif data.startswith("adm_admin_del:"):
         adm_id = data.split(":")[1]
         answer_callback(callback_id, "Deleting admin...")
         admins = admin_db.get("admins", [OWNER_ID])
         if adm_id in admins and adm_id != OWNER_ID:
             admins.remove(adm_id)
             save_admin_db()
         render_admin_management_menu(chat_id, message_id)

    elif data == "adm_admin_add":
         answer_callback(callback_id, "Send Admin ID...")
         user_conversations[chat_id] = "waiting_admin_id"
         text = "👤 <b>Add New Admin</b>\n\nPlease send the Telegram User ID of the new admin (e.g., <code>123456789</code>)."
         edit_bot_message(chat_id, message_id, text, {"inline_keyboard": [[{"text": " Back", "callback_data": "adm_admin_menu", "style": "danger", "icon_custom_emoji_id": "5267490665117275176"}]]})

    elif data == "adm_broadcast":
         answer_callback(callback_id, "Ready for broadcast")
         user_conversations[chat_id] = "waiting_for_broadcast"
         text = f"<tg-emoji emoji-id='5789428375261023681'>📢</tg-emoji> <b>BROADCAST SYSTEM</b>\n\nPlease send the message (Text, Photo, Video, Audio, Document, etc.) you want to broadcast to all users."
         edit_bot_message(chat_id, message_id, text, {"inline_keyboard": [[{"text": " Back", "callback_data": "adm_main_menu", "style": "danger", "icon_custom_emoji_id": "5267490665117275176"}]]})

    elif data == "adm_main_menu":
         answer_callback(callback_id, "Returning to Admin Panel...")
         render_admin_panel(chat_id, message_id)

    elif data == "adm_developer":
         user_conversations.pop(chat_id, None)
         answer_callback(callback_id, "Loading Developer Info...")
         render_admin_developer(chat_id, message_id)

    elif data == "adm_system_menu":
         answer_callback(callback_id, "Opening System Menu...")
         render_admin_system_menu(chat_id, message_id)

    elif data == "adm_panel_mgmt_menu":
         answer_callback(callback_id, "Opening Panel Management...")
         render_admin_panel_mgmt_menu(chat_id, message_id)

    elif data == "adm_trf_home":
         answer_callback(callback_id, "Opening Traffic Management...")
         render_admin_trf_home(chat_id, message_id)

    elif data.startswith("adm_trf_pnl:"):
         pnl_id = data.split(":")[1]
         answer_callback(callback_id)
         render_admin_trf_pnl_view(chat_id, message_id, pnl_id)

    elif data.startswith("adm_trf_tog_pnl:"):
         pnl_id = data.split(":")[1]
         for p in panels:
             if p["id"] == pnl_id:
                 p["is_traffic_active"] = not p.get("is_traffic_active", True)
                 save_panels_to_file(panels)
                 break
         answer_callback(callback_id, "Toggled Traffic Status!")
         render_admin_trf_pnl_view(chat_id, message_id, pnl_id)

    elif data == "adm_srch_home":
         answer_callback(callback_id)
         render_admin_srch_home(chat_id, message_id)

    elif data.startswith("adm_srch_pnl:"):
         pnl_id = data.split(":")[1]
         answer_callback(callback_id)
         render_admin_srch_pnl_view(chat_id, message_id, pnl_id)

    elif data.startswith("adm_srch_tog:"):
         pnl_id = data.split(":")[1]
         search_cfg = admin_db.setdefault("search_cfg", {})
         p_cfg = search_cfg.setdefault(pnl_id, {"is_active": True, "prefixes": []})
         p_cfg["is_active"] = not p_cfg.get("is_active", True)
         save_admin_db()
         answer_callback(callback_id, "Toggled Search Status!")
         render_admin_srch_pnl_view(chat_id, message_id, pnl_id)

    elif data.startswith("adm_srch_add:"):
         pnl_id = data.split(":")[1]
         answer_callback(callback_id, "Send Country Code...")
         user_conversations[chat_id] = f"add_srch_pfx:{pnl_id}"
         user_prompts[chat_id] = message_id
         text = f"{get_pemoji('world', '🌐')} <b>Add Country Code</b>\n\nSend the calling code (e.g., <code>880</code>, <code>92</code>) to allow searching for this panel."
         edit_bot_message(chat_id, message_id, text, {"inline_keyboard": [[{"text": " Back", "callback_data": f"adm_srch_pnl:{pnl_id}", "style": "danger", "icon_custom_emoji_id": "5267490665117275176"}]]})

    elif data.startswith("adm_srch_del:"):
         parts = data.split(":")
         pnl_id = parts[1]
         pfx = parts[2]
         search_cfg = admin_db.setdefault("search_cfg", {})
         if pnl_id in search_cfg and pfx in search_cfg[pnl_id].get("prefixes", []):
             search_cfg[pnl_id]["prefixes"].remove(pfx)
             save_admin_db()
         answer_callback(callback_id, "Deleted Prefix!")
         render_admin_srch_pnl_view(chat_id, message_id, pnl_id)

    elif data in ["adm_wd_app", "adm_wd_rej"]:
         user_id = callback_query.get("from", {}).get("id")
         
         # 🔒 সিকিউরিটি: শুধুমাত্র অ্যাডমিন ক্লিক করতে পারবে
         if str(user_id) not in admin_db.get("admins", [OWNER_ID]):
             answer_callback(callback_id, "❌ Only Admins can process withdrawals!", show_alert=True)
             return
             
         msg_text = callback_query.get("message", {}).get("text", "")
         
         u_match = re.search(r"User:\s*(\d+)", msg_text)
         m_match = re.search(r"Method:\s*(.+)", msg_text)
         a_match = re.search(r"Account:\s*([\d\+\w]+)", msg_text)
         amt_match = re.search(r"Amount:\s*([\d\.]+)", msg_text)
         
         if not (u_match and a_match and amt_match):
             answer_callback(callback_id, "❌ Error parsing request data!", show_alert=True)
             return
             
         u_id = u_match.group(1)
         meth = m_match.group(1).strip() if m_match else "Unknown"
         acc_num = a_match.group(1)
         amt = amt_match.group(1)
         
         masked_acc = mask_number(acc_num)
         
         if data == "adm_wd_app":
             status_text = f"APPROVED {get_pemoji('done', '✅')}"
             new_msg = (
                 f"╔═══════════════╗\n"
                 f"║ {get_pemoji('gem', '💎')} <b>WITHDRAWAL {status_text}</b>\n"
                 f"╚═══════════════╝\n\n"
                 f"{get_pemoji('user', '👤')} <b>User:</b> <code>{u_id}</code>\n"
                 f"{get_pemoji('dashboard', '💳')} <b>Method:</b> {meth}\n"
                 f"{get_pemoji('phone', '📱')} <b>Account:</b> <code>{masked_acc}</code>\n"
                 f"{get_pemoji('fire', '💰')} <b>Amount:</b> <b>{amt} ৳</b>\n"
                 f"━━━━━━━━━━━━"
             )
             edit_bot_message(chat_id, message_id, new_msg)
             send_bot_message(u_id, f"{get_pemoji('done', '✅')} <b>Withdrawal Approved!</b>\nYour request for {amt} ৳ via {meth} has been processed.")
             answer_callback(callback_id, "Approved!")
         else:
             status_text = f"REJECTED {get_pemoji('error', '❌')}"
             new_msg = (
                 f"╔═══════════════╗\n"
                 f"║ {get_pemoji('gem', '💎')} <b>WITHDRAWAL {status_text}</b>\n"
                 f"╚═══════════════╝\n\n"
                 f"{get_pemoji('user', '👤')} <b>User:</b> <code>{u_id}</code>\n"
                 f"{get_pemoji('dashboard', '💳')} <b>Method:</b> {meth}\n"
                 f"{get_pemoji('phone', '📱')} <b>Account:</b> <code>{masked_acc}</code>\n"
                 f"{get_pemoji('fire', '💰')} <b>Amount:</b> <b>{amt} ৳</b>\n"
                 f"━━━━━━━━━━━━"
             )
             edit_bot_message(chat_id, message_id, new_msg)
             
             stats = admin_db.setdefault("user_stats", {}).setdefault(u_id, {})
             stats["balance"] = stats.get("balance", 0.0) + float(amt)
             save_admin_db()
             
             send_bot_message(u_id, f"❌ <b>Withdrawal Rejected!</b>\nYour request for {amt} ৳ was declined. The amount has been refunded to your balance.")
             answer_callback(callback_id, "Rejected & Refunded!")

    elif data == "adm_pnl_home":
         user_conversations.pop(chat_id, None)
         answer_callback(callback_id, "Loading Panels...")
         render_panel_list(chat_id, message_id)

    elif data.startswith("adm_pnl_view:"):
         user_conversations.pop(chat_id, None)
         p_idx = int(data.split(":")[1])
         answer_callback(callback_id, "Loading Details...")
         render_panel_details(chat_id, message_id, p_idx)

    elif data == "adm_panel_mgmt_menu":
         user_conversations.pop(chat_id, None)
         answer_callback(callback_id)
         render_admin_panel_mgmt_menu(chat_id, message_id)

    elif data == "adm_svc_home":
         answer_callback(callback_id)
         render_admin_svc_home(chat_id, message_id)

    elif data.startswith("adm_svc_pnl:"):
         pnl_id = data.split(":")[1]
         answer_callback(callback_id)
         render_admin_svc_pnl_view(chat_id, message_id, pnl_id)

    elif data.startswith("adm_svc_tog_pnl:"):
         pnl_id = data.split(":")[1]
         for p in panels:
             if p["id"] == pnl_id:
                 p["is_active"] = not p.get("is_active", True)
                 save_panels_to_file(panels)
                 break
         answer_callback(callback_id, "Toggled Panel Status!")
         render_admin_svc_pnl_view(chat_id, message_id, pnl_id)

    elif data.startswith("adm_svc_view:"):
         parts = data.split(":")
         answer_callback(callback_id)
         render_admin_svc_view(chat_id, message_id, parts[1], parts[2])

    elif data.startswith("adm_svc_ctr:"):
         parts = data.split(":")
         answer_callback(callback_id)
         render_admin_svc_ctr_view(chat_id, message_id, parts[1], parts[2], parts[3])

    elif data.startswith("adm_svc_add:"):
         pnl_id = data.split(":")[1]
         answer_callback(callback_id, "Send service name...")
         user_conversations[chat_id] = f"add_svc_name:{pnl_id}"
         user_prompts[chat_id] = message_id
         text = f"{get_pemoji('note', '📝')} <b>Add New Service</b>\n\nSend the exact Name of the service (e.g., <code>Facebook</code>, <code>Netflix</code>)."
         edit_bot_message(chat_id, message_id, text, {"inline_keyboard": [[{"text": " Back", "callback_data": f"adm_svc_pnl:{pnl_id}", "style": "danger", "icon_custom_emoji_id": "5267490665117275176"}]]})

    elif data.startswith("adm_svc_add_ctr:"):
         parts = data.split(":")
         pnl_id = parts[1]
         s_id = parts[2]
         answer_callback(callback_id, "Send country code...")
         user_conversations[chat_id] = f"add_svc_ctr:{pnl_id}:{s_id}"
         user_prompts[chat_id] = message_id
         text = f"{get_pemoji('world', '🌐')} <b>Add Country</b>\n\nSend the short Country Code (e.g., <code>CI</code>, <code>CM</code>, <code>SN</code>)."
         edit_bot_message(chat_id, message_id, text, {"inline_keyboard": [[{"text": " Back", "callback_data": f"adm_svc_view:{pnl_id}:{s_id}", "style": "danger", "icon_custom_emoji_id": "5267490665117275176"}]]})

    elif data.startswith("adm_svc_add_rg:"):
         parts = data.split(":")
         pnl_id = parts[1]
         s_id = parts[2]
         c_code = parts[3]
         answer_callback(callback_id, "Send range...")
         user_conversations[chat_id] = f"add_svc_rg:{pnl_id}:{s_id}:{c_code}"
         user_prompts[chat_id] = message_id
         text = f"{get_pemoji('number', '🔢')} <b>Add Range</b>\n\nSend the number range (e.g., <code>225070</code> or <code>225070XXX</code>).\n<i>(If you forget 'XXX', the bot will add it automatically!)</i>"
         edit_bot_message(chat_id, message_id, text, {"inline_keyboard": [[{"text": " Back", "callback_data": f"adm_svc_ctr:{pnl_id}:{s_id}:{c_code}", "style": "danger", "icon_custom_emoji_id": "5267490665117275176"}]]})

    elif data.startswith("adm_svc_del_rg:"): # Added for completion if needed
         pass

    elif data.startswith("adm_svc_del:"):
         parts = data.split(":")
         pnl_id = parts[1]
         s_id = parts[2]
         answer_callback(callback_id, "Deleted Service")
         services_dict = load_services()
         services_dict[pnl_id] = [s for s in services_dict.get(pnl_id, []) if s['id'] != s_id]
         save_services(services_dict)
         render_admin_svc_pnl_view(chat_id, message_id, pnl_id)

    elif data.startswith("adm_svc_del_ctr:"):
         parts = data.split(":")
         pnl_id = parts[1]
         s_id = parts[2]
         c_code = parts[3]
         answer_callback(callback_id, "Deleted Country")
         services_dict = load_services()
         p_services = services_dict.get(pnl_id, [])
         for s in p_services:
             if s['id'] == s_id:
                 s['countries'] = [c for c in s.get('countries', []) if c['code'] != c_code]
                 break
         save_services(services_dict)
         render_admin_svc_view(chat_id, message_id, pnl_id, s_id)

    elif data.startswith("adm_svc_clr_rg:"):
         parts = data.split(":")
         pnl_id = parts[1]
         s_id = parts[2]
         c_code = parts[3]
         answer_callback(callback_id, "Cleared Ranges")
         services_dict = load_services()
         p_services = services_dict.get(pnl_id, [])
         for s in p_services:
             if s['id'] == s_id:
                 for c in s.get('countries', []):
                     if c['code'] == c_code:
                         c['ranges'] = []
                         break
                 break
         save_services(services_dict)
         render_admin_svc_ctr_view(chat_id, message_id, pnl_id, s_id, c_code)

    elif data.startswith("adm_pnl_edit:"):
        parts = data.split(":")
        p_idx = int(parts[1])
        field = parts[2]
        answer_callback(callback_id, f"Editing {field}...")
        user_conversations[chat_id] = f"edit_pnl_{p_idx}_{field}"
        user_prompts[chat_id] = message_id
        
        panel = panels[p_idx] if p_idx < len(panels) else {}
        
        if is_voltx_api(panel) and field == "pass":
            field_name = "API Key (Token)"
        elif is_voltx_api(panel) and field == "url":
            field_name = "Base API URL"
        else:
            names = {"url":"Login Link","user":"Gmail","pass":"Password","getnum":"GetNum URL","getmsg":"GetMsg URL","traffic":"Traffic URL"}
            field_name = names.get(field, field)
        
        panel_name = panel.get("name", "Panel")
        text = f"{get_pemoji('note', '📝')} <b>Editing {field_name} for {panel_name}</b>\n\n" \
               f"Please send the new value/URL to update the system."
        
        edit_bot_message(chat_id, message_id, text, {
            "inline_keyboard": [[{"text": " Back", "callback_data": f"adm_pnl_view:{p_idx}", "style": "danger", "icon_custom_emoji_id": "5267490665117275176"}]]
        })

    elif data == "adm_firebase_menu":
         answer_callback(callback_id, "Opening Firebase Control...")
         render_admin_firebase_menu(chat_id, message_id)

    elif data in ["adm_fb_upload", "adm_fb_view", "adm_fb_delete"]:
         answer_callback(callback_id, "Feature disabled. Creds are now fixed in code.")

    elif data == "adm_fb_sync_users":
         answer_callback(callback_id, "Syncing entire database to Firestore...")
         success, msg_text = sync_essential_data_to_firestore()
         status_emoji = "✅" if success else "❌"
         text = f"{status_emoji} <b>FIREBASE SYNC STATUS</b>\n\n{msg_text}"
         edit_bot_message(chat_id, message_id, text, {"inline_keyboard": [[{"text": " Back", "callback_data": "adm_firebase_menu", "style": "primary", "icon_custom_emoji_id": "5267490665117275176"}]]})

    elif data == "adm_prem_flag":
         answer_callback(callback_id, "Upload Premium Flag...")
         user_conversations[chat_id] = "upload_prem_flag"
         text = f"<tg-emoji emoji-id='5353001161878182134'>📤</tg-emoji> <b>Upload Premium Flag</b>\n\nPlease send me the <code>.txt</code> file containing your country flags."
         edit_bot_message(chat_id, message_id, text, {"inline_keyboard": [[{"text": " Back", "callback_data": "adm_system_menu", "style": "danger", "icon_custom_emoji_id": "5267490665117275176"}]]})

    elif data == "adm_prem_app":
         answer_callback(callback_id, "Upload Premium App...")
         user_conversations[chat_id] = "upload_prem_app"
         text = f"<tg-emoji emoji-id='5353001161878182134'>📤</tg-emoji> <b>Upload Premium App</b>\n\nPlease send me the <code>.txt</code> file containing your service/app emojis."
         edit_bot_message(chat_id, message_id, text, {"inline_keyboard": [[{"text": " Back", "callback_data": "adm_system_menu", "style": "danger", "icon_custom_emoji_id": "5267490665117275176"}]]})

    elif data == "adm_otp_grp_menu":
         user_conversations.pop(chat_id, None)
         answer_callback(callback_id)
         render_admin_otp_grp_menu(chat_id, message_id)

    elif data == "adm_otp_edit_link":
         answer_callback(callback_id)
         user_conversations[chat_id] = "edit_otp_link"
         user_prompts[chat_id] = message_id
         text = f"{get_pemoji('note', '📝')} <b>Edit OTP Group Link</b>\n\nSend the new URL (e.g., https://t.me/...) for the user 'Otp Group' button."
         edit_bot_message(chat_id, message_id, text, {"inline_keyboard": [[{"text": " Back", "callback_data": "adm_otp_grp_menu", "style": "danger", "icon_custom_emoji_id": "5267490665117275176"}]]})

    elif data == "adm_fwd_add":
         answer_callback(callback_id)
         user_conversations[chat_id] = "add_fwd_grp"
         user_prompts[chat_id] = message_id
         text = f"{get_pemoji('note', '📝')} <b>Add Forward Group</b>\n\nSend the Chat ID (e.g., <code>-100123456789</code>) where OTPs should be forwarded."
         edit_bot_message(chat_id, message_id, text, {"inline_keyboard": [[{"text": " Back", "callback_data": "adm_otp_grp_menu", "style": "danger", "icon_custom_emoji_id": "5267490665117275176"}]]})

    elif data.startswith("adm_fwd_view:"):
         idx = int(data.split(":")[1])
         answer_callback(callback_id)
         render_admin_fwd_view(chat_id, message_id, idx)

    elif data.startswith("adm_fwd_del:"):
         idx = int(data.split(":")[1])
         answer_callback(callback_id, "Deleted Group")
         fwd_groups = admin_db.get("forward_groups", [])
         if 0 <= idx < len(fwd_groups):
             fwd_groups.pop(idx)
             save_admin_db()
         render_admin_otp_grp_menu(chat_id, message_id)

    elif data.startswith("adm_fwd_btn_add:"):
         idx = int(data.split(":")[1])
         answer_callback(callback_id)
         user_conversations[chat_id] = f"add_fwd_btn:{idx}"
         user_prompts[chat_id] = message_id
         text = f"{get_pemoji('note', '📝')} <b>Add Custom Button</b>\n\nSend the button Text and URL separated by a pipe (`|`).\nExample:\n<code>Support|https://t.me/admin</code>"
         edit_bot_message(chat_id, message_id, text, {"inline_keyboard": [[{"text": " Back", "callback_data": f"adm_fwd_view:{idx}", "style": "danger", "icon_custom_emoji_id": "5267490665117275176"}]]})

    elif data.startswith("adm_fwd_btn_del:"):
         parts = data.split(":")
         idx = int(parts[1])
         b_idx = int(parts[2])
         answer_callback(callback_id, "Deleted Button")
         fwd_groups = admin_db.get("forward_groups", [])
         if 0 <= idx < len(fwd_groups):
             btns = fwd_groups[idx].get("buttons", [])
             if 0 <= b_idx < len(btns):
                 btns.pop(b_idx)
                 save_admin_db()
         render_admin_fwd_view(chat_id, message_id, idx)

    elif data == "adm_dxa_menu":
         user_conversations.pop(chat_id, None)
         answer_callback(callback_id)
         render_admin_dxa_menu(chat_id, message_id)

    elif data == "adm_dxa_grp":
         answer_callback(callback_id, "Send group ID")
         user_conversations[chat_id] = "set_dxa_grp"
         user_prompts[chat_id] = message_id
         edit_bot_message(chat_id, message_id, f"{get_pemoji('note', '📝')} Send the Group ID for Withdrawal Posts (e.g., <code>-100...</code>):", {"inline_keyboard": [[{"text": " Back", "callback_data": "adm_dxa_menu", "style": "danger", "icon_custom_emoji_id": "5267490665117275176"}]]})

    elif data == "adm_dxa_rew":
         answer_callback(callback_id, "Send OTP reward")
         user_conversations[chat_id] = "set_dxa_rew"
         user_prompts[chat_id] = message_id
         edit_bot_message(chat_id, message_id, f"{get_pemoji('fire', '💰')} Send the amount user earns per successful OTP (e.g., <code>0.5</code>):", {"inline_keyboard": [[{"text": " Back", "callback_data": "adm_dxa_menu", "style": "danger", "icon_custom_emoji_id": "5267490665117275176"}]]})

    elif data == "adm_dxa_min":
         answer_callback(callback_id, "Send Min Withdraw")
         user_conversations[chat_id] = "set_dxa_min"
         user_prompts[chat_id] = message_id
         edit_bot_message(chat_id, message_id, f"{get_pemoji('otp', '🔐')} Send Minimum Withdraw Amount (e.g., <code>20</code>):", {"inline_keyboard": [[{"text": " Back", "callback_data": "adm_dxa_menu", "style": "danger", "icon_custom_emoji_id": "5267490665117275176"}]]})

    elif data == "adm_dxa_mth_add":
         answer_callback(callback_id, "Send Method Name")
         user_conversations[chat_id] = "add_dxa_mth"
         user_prompts[chat_id] = message_id
         edit_bot_message(chat_id, message_id, f"{get_pemoji('dashboard', '🏦')} Send New Withdrawal Method Name (e.g., <code>bKash</code>):", {"inline_keyboard": [[{"text": " Back", "callback_data": "adm_dxa_menu", "style": "danger", "icon_custom_emoji_id": "5267490665117275176"}]]})

    elif data == "adm_dxa_mth_clr":
         answer_callback(callback_id, "Cleared Methods!")
         if "dxa_config" in admin_db:
             admin_db["dxa_config"]["methods"] = []
             save_admin_db()
         render_admin_dxa_menu(chat_id, message_id)

    elif data == "adm_dxa_maxc":
         answer_callback(callback_id, "Send max numbers per user...")
         user_conversations[chat_id] = "set_dxa_maxc"
         user_prompts[chat_id] = message_id
         edit_bot_message(chat_id, message_id, f"{get_pemoji('number', '🔢')} Send Max Numbers a user can request at a time (e.g., <code>3</code>):", {"inline_keyboard": [[{"text": " Back", "callback_data": "adm_dxa_menu", "style": "danger", "icon_custom_emoji_id": "5267490665117275176"}]]})

    elif data == "adm_dxa_cd":
         answer_callback(callback_id, "Send cooldown in seconds...")
         user_conversations[chat_id] = "set_dxa_cd"
         user_prompts[chat_id] = message_id
         edit_bot_message(chat_id, message_id, f"{get_pemoji('wait', '⏳')} Send Cooldown Time in seconds (e.g., <code>30</code>):", {"inline_keyboard": [[{"text": " Back", "callback_data": "adm_dxa_menu", "style": "danger", "icon_custom_emoji_id": "5267490665117275176"}]]})

    elif data.startswith("usr_wd_"):
         method = data.replace("usr_wd_", "")
         stats = admin_db.get("user_stats", {}).get(str(chat_id), {"otp_count": 0, "balance": 0.0})
         cfg = admin_db.get("dxa_config", {})
         if stats.get("balance", 0.0) < float(cfg.get("min_withdraw", 20.0)):
             answer_callback(callback_id, f"❌ Minimum withdraw is {cfg.get('min_withdraw', 20.0)} ৳", show_alert=True)
         else:
             answer_callback(callback_id)
             user_conversations[chat_id] = f"wd_wait_amt_{method}"
             user_prompts[chat_id] = message_id
             text = (
                 f"{get_pemoji('gem', '💎')} <b>Withdraw via {method}</b>\n"
                 f"━━━━━━━━━━━━\n\n"
                 f"{get_pemoji('note', '📝')} Please send the <b>Amount</b> you want to withdraw:\n"
                 f"<i>(Available Balance: {stats.get('balance', 0.0)} ৳)</i>"
             )
             edit_bot_message(chat_id, message_id, text, {"inline_keyboard": [[{"text": " Cancel", "callback_data": "usr_menu_home", "style": "danger", "icon_custom_emoji_id": "5267490665117275176"}]]})
         
    elif data == "adm_main_menu":
         answer_callback(callback_id, "Returning to Admin Panel...")
         render_admin_panel(chat_id, message_id)

    elif data == "adm_developer":
         user_conversations.pop(chat_id, None)
         answer_callback(callback_id, "Loading Developer Info...")
         render_admin_developer(chat_id, message_id)

    elif data.startswith("tr_svc:"):
         service_slug = data.split(":")[1]
         answer_callback(callback_id, f"Loading {service_slug} stats...")
         render_explore_service(chat_id, message_id, service_slug)

    elif data.startswith("tr_ctr:"):
         parts = data.split(":")
         service_slug = parts[1]
         c_code = parts[2]
         answer_callback(callback_id, f"Loading {c_code} ranges...")
         render_explore_ranges(chat_id, message_id, service_slug, c_code)

    else:
        answer_callback(callback_id)

def handle_message(msg):
    chat_id = msg["chat"]["id"]
    chat_type = msg["chat"].get("type", "private")
    
    # 🚫 গ্রুপে কোনো মেসেজ বা কমান্ডের উত্তর দেবে না (শুধু বাটন কাজ করবে)
    if chat_type in ["group", "supergroup"]:
        return

    # 🚫 Check Ban Status
    if str(chat_id) in admin_db.get("banned_users", []):
        return

    # Allow text or captions for media support
    text = msg.get("text", "").strip() or msg.get("caption", "").strip()

    # --- BROADCAST HANDLER (Supports All Media Types: Photo, Video, Audio, etc.) ---
    if user_conversations.get(chat_id) == "waiting_for_broadcast":
        user_conversations.pop(chat_id, None)
        users = admin_db.get("users", [])
        if not users:
            send_bot_message(chat_id, "❌ No users found in database to broadcast.", {"inline_keyboard": [[{"text": " Back to Admin", "callback_data": "adm_main_menu", "style": "primary", "icon_custom_emoji_id": "5267490665117275176"}]]})
            return
            
        send_bot_message(chat_id, f"⏳ Broadcasting to {len(users)} users. Please wait...")
        success_count = 0
        
        for u in users:
            try:
                # Telegram copyMessage API দিয়ে অরিজিনাল মেসেজ ফরওয়ার্ড (Without forwarded tag)
                payload = {
                    "chat_id": u,
                    "from_chat_id": chat_id,
                    "message_id": msg["message_id"]
                }
                res = requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/copyMessage", json=payload).json()
                if res.get("ok"):
                    success_count += 1
            except Exception:
                pass
                
        send_bot_message(chat_id, f"{get_pemoji('done', '✅')} <b>Broadcast Completed!</b>\n\nSuccessfully sent to {success_count}/{len(users)} users.", {"inline_keyboard": [[{"text": " Back to Admin", "callback_data": "adm_main_menu", "style": "primary", "icon_custom_emoji_id": "5267490665117275176"}]]})
        return

    if user_conversations.get(chat_id) == "waiting_fj_channel":
        channel = text.strip()
        if channel:
            if "force_join_channels" not in admin_db:
                admin_db["force_join_channels"] = []
            if channel not in admin_db["force_join_channels"]:
                admin_db["force_join_channels"].append(channel)
                save_admin_db()
            user_conversations.pop(chat_id, None)
            send_bot_message(chat_id, f"{get_pemoji('done', '✅')} <b>Channel added successfully!</b>", {"inline_keyboard": [[{"text": " Back", "callback_data": "adm_fj_menu", "style": "primary", "icon_custom_emoji_id": "5267490665117275176"}]]})
        return

    if user_conversations.get(chat_id) == "waiting_admin_id":
        adm_id = text.strip()
        if adm_id.isdigit():
            if "admins" not in admin_db:
                admin_db["admins"] = [OWNER_ID]
            if adm_id not in admin_db["admins"]:
                admin_db["admins"].append(adm_id)
                save_admin_db()
            user_conversations.pop(chat_id, None)
            send_bot_message(chat_id, f"{get_pemoji('done', '✅')} <b>Admin added successfully!</b>", {"inline_keyboard": [[{"text": " Back", "callback_data": "adm_admin_menu", "style": "primary", "icon_custom_emoji_id": "5267490665117275176"}]]})
        else:
            send_bot_message(chat_id, f"{get_pemoji('error', '❌')} Please enter a valid numeric User ID.", {"inline_keyboard": [[{"text": " Back", "callback_data": "adm_admin_menu", "style": "danger", "icon_custom_emoji_id": "5267490665117275176"}]]})
        return

    # --- NEW: File Upload Handler for Admin ---
    state = user_conversations.get(chat_id)
    if state in ["upload_prem_flag", "upload_prem_app"]:
        if "document" in msg:
            file_id = msg["document"]["file_id"]
            file_name = msg["document"]["file_name"]
            if file_name.endswith(".txt"):
                send_bot_message(chat_id, f"<tg-emoji emoji-id='5337172996211648018'>⏳</tg-emoji> Processing file...")
                res = call_telegram("getFile", {"file_id": file_id})
                if res and res.get("ok"):
                    file_path = res["result"]["file_path"]
                    download_url = f"https://api.telegram.org/file/bot{TELEGRAM_TOKEN}/{file_path}"
                    r = requests.get(download_url)
                    if r.status_code == 200:
                        # 🚀 Save raw file to disk dynamically based on state
                        target_file = "Premium Flag.txt" if state == "upload_prem_flag" else "Premium App.txt"
                        with open(target_file, "w", encoding="utf-8") as f:
                            f.write(r.text)
                            
                        apps, flags = process_premium_txt(r.text)
                        user_conversations.pop(chat_id, None)
                        
                        send_bot_message(chat_id, f"<tg-emoji emoji-id='5352694861990501856'>✅</tg-emoji> <b>Database Updated!</b>\n\nFile saved as: <code>{target_file}</code>\nAdded/Updated:\n» {apps} Apps\n» {flags} Countries", {"inline_keyboard": [[{"text": " Back to System", "callback_data": "adm_system_menu", "style": "primary", "icon_custom_emoji_id": "5267490665117275176"}]]})
                        return
        send_bot_message(chat_id, "<tg-emoji emoji-id='5420130255174145507'>❌</tg-emoji> Please upload a valid `.txt` file.", {"inline_keyboard": [[{"text": " Back", "callback_data": "adm_system_menu", "style": "danger", "icon_custom_emoji_id": "5267490665117275176"}]]})
        return  

    # --- MANAGE OTP & FORWARD GROUPS ---
    state = user_conversations.get(chat_id, "")

    if state == "set_dxa_grp":
        user_conversations.pop(chat_id, None)
        prompt_id = user_prompts.pop(chat_id, None)
        admin_db.setdefault("dxa_config", {})["withdraw_group"] = text.strip()
        save_admin_db()
        kb = {"inline_keyboard": [[{"text": " Back", "callback_data": "adm_dxa_menu", "style": "primary", "icon_custom_emoji_id": "5267490665117275176"}]]}
        call_telegram("deleteMessage", {"chat_id": chat_id, "message_id": msg["message_id"]})
        res_text = f"{get_pemoji('done', '✅')} Withdraw Group Updated!"
        if prompt_id: edit_bot_message(chat_id, prompt_id, res_text, kb)
        else: send_bot_message(chat_id, res_text, kb)
        return

    if state == "set_dxa_rew":
        user_conversations.pop(chat_id, None)
        prompt_id = user_prompts.pop(chat_id, None)
        try:
            admin_db.setdefault("dxa_config", {})["otp_reward"] = float(text.strip())
            save_admin_db()
            res_text = f"{get_pemoji('done', '✅')} OTP Reward Updated!"
        except: res_text = f"{get_pemoji('error', '❌')} Invalid Amount!"
        kb = {"inline_keyboard": [[{"text": " Back", "callback_data": "adm_dxa_menu", "style": "primary", "icon_custom_emoji_id": "5267490665117275176"}]]}
        call_telegram("deleteMessage", {"chat_id": chat_id, "message_id": msg["message_id"]})
        if prompt_id: edit_bot_message(chat_id, prompt_id, res_text, kb)
        else: send_bot_message(chat_id, res_text, kb)
        return

    if state == "set_dxa_min":
        user_conversations.pop(chat_id, None)
        prompt_id = user_prompts.pop(chat_id, None)
        try:
            admin_db.setdefault("dxa_config", {})["min_withdraw"] = float(text.strip())
            save_admin_db()
            res_text = f"{get_pemoji('done', '✅')} Min Withdraw Updated!"
        except: res_text = f"{get_pemoji('error', '❌')} Invalid Amount!"
        kb = {"inline_keyboard": [[{"text": " Back", "callback_data": "adm_dxa_menu", "style": "primary", "icon_custom_emoji_id": "5267490665117275176"}]]}
        call_telegram("deleteMessage", {"chat_id": chat_id, "message_id": msg["message_id"]})
        if prompt_id: edit_bot_message(chat_id, prompt_id, res_text, kb)
        else: send_bot_message(chat_id, res_text, kb)
        return

    if state == "set_dxa_maxc":
        user_conversations.pop(chat_id, None)
        prompt_id = user_prompts.pop(chat_id, None)
        try:
            admin_db.setdefault("dxa_config", {})["max_concurrent"] = int(text.strip())
            save_admin_db()
            res_text = f"{get_pemoji('done', '✅')} Max Concurrent Numbers Updated!"
        except: res_text = f"{get_pemoji('error', '❌')} Invalid Number!"
        kb = {"inline_keyboard": [[{"text": " Back", "callback_data": "adm_dxa_menu", "style": "primary", "icon_custom_emoji_id": "5267490665117275176"}]]}
        call_telegram("deleteMessage", {"chat_id": chat_id, "message_id": msg["message_id"]})
        if prompt_id: edit_bot_message(chat_id, prompt_id, res_text, kb)
        else: send_bot_message(chat_id, res_text, kb)
        return

    if state == "set_dxa_cd":
        user_conversations.pop(chat_id, None)
        prompt_id = user_prompts.pop(chat_id, None)
        try:
            admin_db.setdefault("dxa_config", {})["cooldown"] = int(text.strip())
            save_admin_db()
            res_text = f"{get_pemoji('done', '✅')} Cooldown Time Updated!"
        except: res_text = f"{get_pemoji('error', '❌')} Invalid Number!"
        kb = {"inline_keyboard": [[{"text": " Back", "callback_data": "adm_dxa_menu", "style": "primary", "icon_custom_emoji_id": "5267490665117275176"}]]}
        call_telegram("deleteMessage", {"chat_id": chat_id, "message_id": msg["message_id"]})
        if prompt_id: edit_bot_message(chat_id, prompt_id, res_text, kb)
        else: send_bot_message(chat_id, res_text, kb)
        return

    if state == "add_dxa_mth":
        user_conversations.pop(chat_id, None)
        prompt_id = user_prompts.pop(chat_id, None)
        admin_db.setdefault("dxa_config", {}).setdefault("methods", []).append(text.strip())
        save_admin_db()
        kb = {"inline_keyboard": [[{"text": " Back", "callback_data": "adm_dxa_menu", "style": "primary", "icon_custom_emoji_id": "5267490665117275176"}]]}
        call_telegram("deleteMessage", {"chat_id": chat_id, "message_id": msg["message_id"]})
        res_text = f"{get_pemoji('done', '✅')} Method {text.strip()} Added!"
        if prompt_id: edit_bot_message(chat_id, prompt_id, res_text, kb)
        else: send_bot_message(chat_id, res_text, kb)
        return

    if state.startswith("wd_wait_amt_"):
        user_conversations.pop(chat_id, None)
        prompt_id = user_prompts.pop(chat_id, None)
        method = state.replace("wd_wait_amt_", "")
        
        call_telegram("deleteMessage", {"chat_id": chat_id, "message_id": msg["message_id"]})
        kb = {"inline_keyboard": [[{"text": " Cancel", "callback_data": "usr_menu_home", "style": "danger", "icon_custom_emoji_id": "5267490665117275176"}]]}
        
        try:
            amount = float(text.strip())
            stats = admin_db.get("user_stats", {}).get(str(chat_id), {"otp_count": 0, "balance": 0.0})
            cfg = admin_db.get("dxa_config", {})
            
            if amount < float(cfg.get("min_withdraw", 20.0)):
                res_text = f"{get_pemoji('error', '❌')} <b>Failed:</b> Minimum withdraw is {cfg.get('min_withdraw', 20.0)} ৳"
                if prompt_id: edit_bot_message(chat_id, prompt_id, res_text, kb)
                else: send_bot_message(chat_id, res_text, kb)
            elif amount > stats.get("balance", 0.0):
                res_text = f"{get_pemoji('error', '❌')} <b>Failed:</b> Insufficient balance!"
                if prompt_id: edit_bot_message(chat_id, prompt_id, res_text, kb)
                else: send_bot_message(chat_id, res_text, kb)
            else:
                user_conversations[chat_id] = f"wd_wait_num_{method}_{amount}"
                user_prompts[chat_id] = prompt_id 
                res_text = (
                    f"{get_pemoji('gem', '💎')} <b>Withdraw via {method}</b>\n"
                    f"━━━━━━━━━━━━\n"
                    f"{get_pemoji('done', '✅')} <b>Amount:</b> {amount} ৳\n\n"
                    f"{get_pemoji('phone', '📱')} Now, please send your <b>Account Number</b>:"
                )
                if prompt_id: edit_bot_message(chat_id, prompt_id, res_text, kb)
                else: 
                    new_msg = send_bot_message(chat_id, res_text, kb)
                    if new_msg: user_prompts[chat_id] = new_msg.get("result", {}).get("message_id")
        except ValueError:
            res_text = f"{get_pemoji('error', '❌')} Invalid amount format. Please send numbers only."
            if prompt_id: edit_bot_message(chat_id, prompt_id, res_text, kb)
            else: send_bot_message(chat_id, res_text, kb)
        return

    if state.startswith("wd_wait_num_"):
        user_conversations.pop(chat_id, None)
        prompt_id = user_prompts.pop(chat_id, None)
        
        # Method এবং Amount এক্সট্র্যাক্ট করা
        remainder = state.replace("wd_wait_num_", "")
        last_underscore = remainder.rfind("_")
        method = remainder[:last_underscore]
        amount = float(remainder[last_underscore+1:])
        number = text.strip()
        
        call_telegram("deleteMessage", {"chat_id": chat_id, "message_id": msg["message_id"]})
        kb = {"inline_keyboard": [[{"text": " Back to Home", "callback_data": "usr_menu_home", "style": "primary", "icon_custom_emoji_id": "5267490665117275176"}]]}
        
        stats = admin_db.get("user_stats", {}).get(str(chat_id), {"otp_count": 0, "balance": 0.0})
        if stats["balance"] >= amount:
            admin_db["user_stats"][str(chat_id)]["balance"] -= amount
            save_admin_db()
            
            res_text = (
                f"{get_pemoji('done', '✅')} <b>Withdrawal requested successfully!</b>\n"
                f"━━━━━━━━━━━━\n"
                f"{get_pemoji('gem', '💎')} <b>Amount:</b> {amount} ৳\n"
                f"{get_pemoji('phone', '📱')} <b>Number:</b> <code>{number}</code>\n"
                f"<i>It will be processed soon by the DXA admins.</i>"
            )
            
            cfg = admin_db.get("dxa_config", {})
            w_grp = cfg.get("withdraw_group")
            if w_grp:
                w_msg = (
                    f"╔═══════════════╗\n"
                    f"║ {get_pemoji('gem', '💎')} <b>NEW WITHDRAWAL REQUEST</b>\n"
                    f"╚═══════════════╝\n\n"
                    f"{get_pemoji('user', '👤')} <b>User:</b> <code>{chat_id}</code>\n"
                    f"{get_pemoji('dashboard', '💳')} <b>Method:</b> {method}\n"
                    f"{get_pemoji('phone', '📱')} <b>Account:</b> <code>{number}</code>\n"
                    f"{get_pemoji('fire', '💰')} <b>Amount:</b> <b>{amount} ৳</b>\n"
                    f"━━━━━━━━━━━━"
                )
                wd_kb = {
                    "inline_keyboard": [
                        [
                            {"text": " Approve", "callback_data": "adm_wd_app", "style": "success", "icon_custom_emoji_id": "5352694861990501856"},
                            {"text": " Reject", "callback_data": "adm_wd_rej", "style": "danger", "icon_custom_emoji_id": "5420130255174145507"}
                        ]
                    ]
                }
                call_telegram("sendMessage", {"chat_id": w_grp, "text": w_msg, "parse_mode": "HTML", "reply_markup": wd_kb})
        else:
            res_text = f"{get_pemoji('error', '❌')} Something went wrong with your balance verification!"

        if prompt_id: edit_bot_message(chat_id, prompt_id, res_text, kb)
        else: send_bot_message(chat_id, res_text, kb)
        return
    
    if state.startswith("um_wait_id_"):
        user_conversations.pop(chat_id, None)
        prompt_id = user_prompts.pop(chat_id, None)
        action_type = state.split("_")[3]
        target_uid = text.strip()
        
        call_telegram("deleteMessage", {"chat_id": chat_id, "message_id": msg["message_id"]})
        
        if not target_uid.isdigit():
            err_txt = "❌ Invalid User ID. Must be numeric."
            kb = {"inline_keyboard": [[{"text": " Back", "callback_data": "adm_user_mgmt_menu", "style": "danger", "icon_custom_emoji_id": "5267490665117275176"}]]}
            if prompt_id: edit_bot_message(chat_id, prompt_id, err_txt, kb)
            else: send_bot_message(chat_id, err_txt, kb)
            return

        if action_type == "prof":
            render_um_profile(chat_id, prompt_id, target_uid)
        elif action_type == "bal":
            render_um_balance(chat_id, prompt_id, target_uid)
        elif action_type == "ban":
            render_um_ban(chat_id, prompt_id, target_uid)
        return

    if state.startswith("um_wait_amt_"):
        user_conversations.pop(chat_id, None)
        prompt_id = user_prompts.pop(chat_id, None)
        parts = state.split("_")
        action = parts[3] # "add" or "sub"
        target_uid = parts[4]
        
        call_telegram("deleteMessage", {"chat_id": chat_id, "message_id": msg["message_id"]})
        kb = {"inline_keyboard": [[{"text": " Back to Balance", "callback_data": f"adm_um_view_bal:{target_uid}", "style": "primary", "icon_custom_emoji_id": "5267490665117275176"}]]}
        
        try:
            amount = float(text.strip())
            stats = admin_db.setdefault("user_stats", {}).setdefault(target_uid, {"otp_count": 0, "balance": 0.0})
            
            if action == "add":
                stats["balance"] += amount
                res_txt = f"<tg-emoji emoji-id='5352694861990501856'>✅</tg-emoji> Added {amount} ৳ to <code>{target_uid}</code>'s balance."
            else:
                stats["balance"] = max(0.0, stats["balance"] - amount)
                res_txt = f"<tg-emoji emoji-id='5352694861990501856'>✅</tg-emoji> Deducted {amount} ৳ from <code>{target_uid}</code>'s balance."
                
            save_admin_db()
        except ValueError:
            res_txt = "<tg-emoji emoji-id='5420130255174145507'>❌</tg-emoji> Invalid amount! Please send a valid number."
            
        if prompt_id: edit_bot_message(chat_id, prompt_id, res_txt, kb)
        else: send_bot_message(chat_id, res_txt, kb)
        return

    if state == "edit_otp_link":
        user_conversations.pop(chat_id, None)
        prompt_id = user_prompts.pop(chat_id, None)
        link = text.strip()
        admin_db["otp_group_link"] = link
        save_admin_db()
        res_text = f"{get_pemoji('done', '✅')} User OTP Group Link updated successfully!"
        kb = {"inline_keyboard": [[{"text": " Back", "callback_data": "adm_otp_grp_menu", "style": "primary", "icon_custom_emoji_id": "5267490665117275176"}]]}
        call_telegram("deleteMessage", {"chat_id": chat_id, "message_id": msg["message_id"]})
        if prompt_id: edit_bot_message(chat_id, prompt_id, res_text, kb)
        else: send_bot_message(chat_id, res_text, kb)
        return

    if state == "add_fwd_grp":
        user_conversations.pop(chat_id, None)
        prompt_id = user_prompts.pop(chat_id, None)
        g_id = text.strip()
        fwd_groups = admin_db.setdefault("forward_groups", [])
        if not any(g["id"] == g_id for g in fwd_groups):
            fwd_groups.append({"id": g_id, "buttons": []})
            save_admin_db()
            res_text = f"{get_pemoji('done', '✅')} Forward Group added!"
        else:
            res_text = f"{get_pemoji('error', '❌')} Group already exists!"
        kb = {"inline_keyboard": [[{"text": " Back", "callback_data": "adm_otp_grp_menu", "style": "primary", "icon_custom_emoji_id": "5267490665117275176"}]]}
        call_telegram("deleteMessage", {"chat_id": chat_id, "message_id": msg["message_id"]})
        if prompt_id: edit_bot_message(chat_id, prompt_id, res_text, kb)
        else: send_bot_message(chat_id, res_text, kb)
        return

    if state.startswith("add_fwd_btn:"):
        user_conversations.pop(chat_id, None)
        prompt_id = user_prompts.pop(chat_id, None)
        idx = int(state.split(":")[1])
        
        res_text = f"{get_pemoji('error', '❌')} Invalid format. Use Text|URL"
        if "|" in text:
            b_text, b_url = text.split("|", 1)
            
            # 🚀 Extract Premium Emoji ID directly from the message entities
            em_id = None
            if "entities" in msg:
                for ent in msg["entities"]:
                    if ent.get("type") == "custom_emoji":
                        em_id = ent.get("custom_emoji_id")
                        break
            
            # Remove the fallback emoji character from the text to avoid double emojis
            clean_text = b_text.strip()
            match = re.search(r'^([^\w\s]+)\s*(.*)', clean_text, re.UNICODE)
            if match:
                clean_text = match.group(2).strip()
            
            btn_data = {"text": f" {clean_text}", "url": b_url.strip()}
            if em_id:
                btn_data["emoji_id"] = em_id
            
            fwd_groups = admin_db.get("forward_groups", [])
            if 0 <= idx < len(fwd_groups):
                fwd_groups[idx].setdefault("buttons", []).append(btn_data)
                save_admin_db()
                res_text = f"{get_pemoji('done', '✅')} Button added successfully!"
                
        kb = {"inline_keyboard": [[{"text": " Back", "callback_data": f"adm_fwd_view:{idx}", "style": "primary", "icon_custom_emoji_id": "5267490665117275176"}]]}
        call_telegram("deleteMessage", {"chat_id": chat_id, "message_id": msg["message_id"]})
        if prompt_id: edit_bot_message(chat_id, prompt_id, res_text, kb)
        else: send_bot_message(chat_id, res_text, kb)
        return

    if state.startswith("add_srch_pfx:"):
        user_conversations.pop(chat_id, None)
        prompt_id = user_prompts.pop(chat_id, None)
        pnl_id = state.split(":")[1]
        pfx = text.strip().replace("+", "")
        
        res_text = f"{get_pemoji('error', '❌')} Invalid format. Only numbers are allowed."
        kb = {"inline_keyboard": [[{"text": " Back", "callback_data": f"adm_srch_pnl:{pnl_id}", "style": "primary", "icon_custom_emoji_id": "5267490665117275176"}]]}
        
        if pfx.isdigit():
            search_cfg = admin_db.setdefault("search_cfg", {})
            p_cfg = search_cfg.setdefault(pnl_id, {"is_active": True, "prefixes": []})
            if pfx not in p_cfg["prefixes"]:
                p_cfg["prefixes"].append(pfx)
                save_admin_db()
                res_text = f"{get_pemoji('done', '✅')} Country code <b>+{pfx}</b> added for search!"
            else:
                res_text = f"{get_pemoji('error', '❌')} Country code already exists!"
                
        call_telegram("deleteMessage", {"chat_id": chat_id, "message_id": msg["message_id"]})
        if prompt_id: edit_bot_message(chat_id, prompt_id, res_text, kb)
        else: send_bot_message(chat_id, res_text, kb)
        return
    
    if state.startswith("add_svc_name:"):
        user_conversations.pop(chat_id, None)
        prompt_id = user_prompts.pop(chat_id, None)
        pnl_id = state.split(":")[1]
        svc_name = text.strip()
        svc_id = svc_name.lower().replace(" ", "_")
        services_dict = load_services()
        if pnl_id not in services_dict:
            services_dict[pnl_id] = []
            
        p_services = services_dict[pnl_id]
        kb = {"inline_keyboard": [[{"text": " Back to Services", "callback_data": f"adm_svc_pnl:{pnl_id}", "style": "primary", "icon_custom_emoji_id": "5267490665117275176"}]]}
        if not any(s['id'] == svc_id for s in p_services):
            p_services.append({"id": svc_id, "name": svc_name, "countries": []})
            save_services(services_dict)
            res_text = f"{get_pemoji('done', '✅')} Service <b>{svc_name}</b> added to panel!"
        else:
            res_text = f"{get_pemoji('error', '❌')} Service already exists!"
        
        if prompt_id:
            edit_bot_message(chat_id, prompt_id, res_text, kb)
        else:
            send_bot_message(chat_id, res_text, kb)
        return

    if state.startswith("add_svc_ctr:"):
        user_conversations.pop(chat_id, None)
        prompt_id = user_prompts.pop(chat_id, None)
        parts = state.split(":")
        pnl_id = parts[1]
        s_id = parts[2]
        c_code = text.strip().upper()
        services_dict = load_services()
        p_services = services_dict.get(pnl_id, [])
        
        kb = {"inline_keyboard": [[{"text": " Back to Service", "callback_data": f"adm_svc_view:{pnl_id}:{s_id}", "style": "primary", "icon_custom_emoji_id": "5267490665117275176"}]]}
        res_text = f"{get_pemoji('error', '❌')} Error processing country."
        
        for s in p_services:
            if s['id'] == s_id:
                if not any(c['code'] == c_code for c in s.get('countries', [])):
                    s.setdefault('countries', []).append({"code": c_code, "ranges": []})
                    save_services(services_dict)
                    res_text = f"{get_pemoji('done', '✅')} Country <b>{c_code}</b> added to {s['name']}!"
                else:
                    res_text = f"{get_pemoji('error', '❌')} Country already added!"
                break
                
        if prompt_id:
            edit_bot_message(chat_id, prompt_id, res_text, kb)
        else:
            send_bot_message(chat_id, res_text, kb)
        return

    if state.startswith("add_svc_rg:"):
        user_conversations.pop(chat_id, None)
        prompt_id = user_prompts.pop(chat_id, None)
        parts = state.split(":")
        pnl_id = parts[1]
        s_id = parts[2]
        c_code = parts[3]
        
        new_range = text.strip().upper()
        if not any(x in new_range for x in ("X", "*")) and new_range.isdigit():
            new_range += "XXX"
            
        services_dict = load_services()
        p_services = services_dict.get(pnl_id, [])
        kb = {"inline_keyboard": [[{"text": " Back to Ranges", "callback_data": f"adm_svc_ctr:{pnl_id}:{s_id}:{c_code}", "style": "primary", "icon_custom_emoji_id": "5267490665117275176"}]]}
        res_text = f"{get_pemoji('error', '❌')} Error processing range."
        
        for s in p_services:
            if s['id'] == s_id:
                for c in s.get('countries', []):
                    if c['code'] == c_code:
                        if new_range not in c.get('ranges', []):
                            c.setdefault('ranges', []).append(new_range)
                            save_services(services_dict)
                            res_text = f"{get_pemoji('done', '✅')} Range <code>{new_range}</code> added!"
                        else:
                            res_text = f"{get_pemoji('error', '❌')} Range already exists!"
                        break
                break
                
        if prompt_id:
            edit_bot_message(chat_id, prompt_id, res_text, kb)
        else:
            send_bot_message(chat_id, res_text, kb)
        return

    if state.startswith("edit_pnl_"):
        parts = state.split("_")
        if len(parts) >= 4:
            p_idx = int(parts[2])
            field_key = parts[3]
            
            if p_idx < len(panels):
                p = panels[p_idx]
                
                mapping = {
                    "url": "url", 
                    "user": "username", 
                    "pass": "password", 
                    "getnum": "getNumberUrl", 
                    "getmsg": "getMessageUrl", 
                    "traffic": "trafficUrl"
                }
                actual_key = mapping.get(field_key, field_key)
                p[actual_key] = text
                
                if field_key in ["url", "user", "pass"]:
                    p["sessionCookie"] = "" # Reset session for auth changes
                    
                save_panels_to_file(panels)
                user_conversations.pop(chat_id, None)
                
                # ইউজারের ইনপুট মেসেজ ডিলিট করে দেওয়া হচ্ছে
                call_telegram("deleteMessage", {"chat_id": chat_id, "message_id": msg["message_id"]})
                prompt_id = user_prompts.pop(chat_id, None)
                
                if field_key in ["url", "user", "pass"]:
                    wait_text = f"{get_pemoji('wait', '⏳')} <b>Configuration Saved!</b>\nChecking authentication status for {p['name']}..."
                    if prompt_id:
                        edit_bot_message(chat_id, prompt_id, wait_text)
                    else:
                        wait_msg = send_bot_message(chat_id, wait_text)
                        prompt_id = wait_msg.get("result", {}).get("message_id")
                        
                    login_result = login_to_panel(p, force=True)
                    
                    if login_result:
                        final_text = f"{get_pemoji('done', '✅')} <b>Success!</b> Login verified with new settings."
                        style = "success"
                    else:
                        final_text = f"{get_pemoji('error', '❌')} <b>Login Failed!</b> Please check your URL/Credentials."
                        style = "danger"
                        
                    edit_bot_message(chat_id, prompt_id, final_text, {
                        "inline_keyboard": [[{"text": " Back to Panel details", "callback_data": f"adm_pnl_view:{p_idx}", "style": style, "icon_custom_emoji_id": "5267490665117275176"}]]
                    })
                else:
                    res_text_edit = f"{get_pemoji('done', '✅')} <b>Configuration Saved!</b>\n\nAPI link updated successfully."
                    kb_edit = {"inline_keyboard": [[{"text": " Back to Panel details", "callback_data": f"adm_pnl_view:{p_idx}", "style": "primary", "icon_custom_emoji_id": "5267490665117275176"}]]}
                    if prompt_id:
                        edit_bot_message(chat_id, prompt_id, res_text_edit, kb_edit)
                    else:
                        send_bot_message(chat_id, res_text_edit, kb_edit)
                return
            
    if not text:
        return

    # 🚀 Track Unique Users for Admin DB
    if chat_id not in admin_db.get("users", []):
        if "users" not in admin_db:
            admin_db["users"] = []
        admin_db["users"].append(chat_id)
        save_admin_db()
        # Background Auto-Sync to Firebase
        threading.Thread(target=sync_essential_data_to_firestore, daemon=True).start()
        
    lower = text.lower()
    logger.info(f"Inbound chat message [ID={chat_id}]: '{text}'")

    # 🛡️ Force Join Check Middleware
    if not check_force_join(chat_id):
        return

    # Handle Admin Panel Option
    if "admin panel" in lower or lower == "/admin":
        render_admin_panel(chat_id)
        return

    # Handle Start/Menu commands ONLY
    if lower in ["/start", "/help", "/menu"]:
        text_start = (
            "╔═══════════╗\n"
            f"       {get_pemoji('dashboard', '📊')} <b>NUMBER BOT</b>\n"
            "╚═══════════╝\n"
            f"{get_pemoji('rocket', '🚀')} Welcome to Number & OTP Service\n"
            "━━━━━━━━━━━━\n"
            f"{get_pemoji('done', '✅')} Choose an option below\n"
            "to continue using the bot.\n"
            "━━━━━━━━━━━━\n"
            f"{get_pemoji('gem', '💎')} Premium OTP Service"
        )
        # শুধু ওয়েলকাম মেসেজ এবং নিচের কীবোর্ড দেবে
        send_bot_message(chat_id, text_start, get_bot_menu_keyboard(chat_id))
        return

    # Handle Get Number command ONLY
    if "get number" in lower:
        # শুধু Get Number এ চাপ দিলে সার্ভিস লিস্ট দেবে
        render_services_list(chat_id)
        return

    # Handle Master Menu Commands
    if "search number" in lower or lower == "/search":
        user_conversations[chat_id] = "waiting_for_search"
        text_help = (
            "╔═══════════╗\n"
            f"     {get_pemoji('search', '🔍')} <b>SEARCH NUMBER</b>\n"
            "╚═══════════╝\n"
            f"{get_pemoji('done', '📌')} Enter 3 to 9 digits  \n"
            "to search for a number.\n"
            "━━━━━━━━━━━━━\n"
            f"<tg-emoji emoji-id='5395444784611480792'>📝</tg-emoji> Example:\n"
            "➥ 880\n"
            "➥ 9227373\n"
            "━━━━━━━━━━━━━\n"
            f"{get_pemoji('search', '🔍')} Fast Number Lookup System"
        )
        send_bot_message(chat_id, text_help, {"inline_keyboard": [[{"text": " Back", "callback_data": "usr_menu_home", "style": "danger", "icon_custom_emoji_id": "5267490665117275176"}]]})
        return

    if lower.startswith("/search "):
        query = text[8:].strip()
        if query:
            q_sanit = query.replace("+", "").strip()
            
            # --- Check Search Restriction & Find Valid Panels ---
            search_cfg = admin_db.get("search_cfg", {})
            valid_panels = []
            for p in panels:
                cfg = search_cfg.get(p["id"], {})
                if not cfg.get("is_active", True): continue
                for pfx in cfg.get("prefixes", []):
                    if q_sanit.startswith(pfx):
                        valid_panels.append(p)
                        break
                        
            if not valid_panels:
                send_bot_message(chat_id, f"{get_pemoji('error', '❌')} <b>Search Restricted!</b>\n\nThe country code for <code>{q_sanit}</code> is not configured or allowed by the admin.")
                return
                
            chosen_panel_id = random.choice(valid_panels)["id"]
            # --------------------------------------------------
            
            if 'x' in q_sanit.lower():
                trigger_buy_number(chat_id, q_sanit.upper(), chosen_panel_id)
            elif q_sanit.isdigit() and len(q_sanit) <= 9:
                trigger_buy_number(chat_id, q_sanit + "XXX", chosen_panel_id)
            else:
                search_number_otp(chat_id, q_sanit)
        else:
            send_bot_message(chat_id, "❌ Please specify a number to search. Usage: <code>/search 237620610123</code>")
        return

    if "traffic" in lower or lower == "/traffic":
        render_traffic_home(chat_id)
        return

    if "balance" in lower or lower == "/balance":
        render_user_balance(chat_id)
        return

    # Direct allocation hooks format buy/get/getnum
    if lower.startswith(("/getnum ", "/buy ", "/get ")):
        parts = text.split()
        if len(parts) > 1:
            q_rang = parts[-1].replace("+", "").strip()
            if 'x' in q_rang.lower():
                trigger_buy_number(chat_id, q_rang.upper())
            elif q_rang.isdigit() and len(q_rang) <= 9:
                trigger_buy_number(chat_id, q_rang + "XXX")
            else:
                trigger_buy_number(chat_id, q_rang)
        else:
            send_bot_message(chat_id, "❌ Please specify a range. Usage: <code>/getnum 237620610XXX</code>")
        return

    # Process raw numerical values ONLY IF in search state
    if user_conversations.get(chat_id) == "waiting_for_search":
        user_conversations.pop(chat_id, None)  # ইনপুট নেওয়ার পর state ক্লিয়ার করে দেবে
        clean_text = text.replace("+", "").strip()
        has_x = 'x' in clean_text.lower()
        is_numbers = clean_text.isdigit()

        # --- Check Search Restriction & Find Valid Panels ---
        search_cfg = admin_db.get("search_cfg", {})
        valid_panels = []
        for p in panels:
            cfg = search_cfg.get(p["id"], {})
            if not cfg.get("is_active", True): continue
            for pfx in cfg.get("prefixes", []):
                if clean_text.startswith(pfx):
                    valid_panels.append(p)
                    break
                    
        if not valid_panels:
            send_bot_message(chat_id, f"{get_pemoji('error', '❌')} <b>Search Restricted!</b>\n\nThe country code for <code>{clean_text}</code> is not configured or allowed by the admin.")
            return
            
        chosen_panel_id = random.choice(valid_panels)["id"]
        # --------------------------------------------------

        if has_x:
            trigger_buy_number(chat_id, clean_text.upper(), chosen_panel_id)
            return
        elif is_numbers:
            if len(clean_text) <= 9:
                trigger_buy_number(chat_id, clean_text + "XXX", chosen_panel_id)
            else:
                search_number_otp(chat_id, clean_text)
            return
        else:
            send_bot_message(chat_id, "❌ Invalid format. Please enter a valid number or range.")
            return

    # General unknown prompt Fallback (Disabled)
    pass

# ----------------------------------------------------
# Background Panel Periodic SMS Forwarder Checks Thread
# ----------------------------------------------------

def check_cdrs_for_panel(panel):
    global local_traffic_stats, local_raw_logs_cache
    session = get_session(panel["id"])
    baseUrl = normalize_base_url(panel["url"])

    # --- START PHP/MK PANEL LOGIC ---
    if is_php_panel(panel):
        try:
            clean_base = get_clean_base_url(panel, baseUrl)
            console_url = panel.get("trafficUrl") or f"{clean_base}/console.php?ajax=1"
            
            # 🚀 Added Advanced AJAX Headers for MK PHP Panels to avoid 403 & empty data
            headers = {
                "Cookie": panel.get("sessionCookie", ""),
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "application/json, text/javascript, */*; q=0.01",
                "X-Requested-With": "XMLHttpRequest",
                "Referer": f"{clean_base}/dashboard.php"
            }
            
            # Using Cloudscraper session to bypass Cloudflare
            res = session.get(console_url, headers=headers, timeout=20)

            if res.status_code != 200 or "login_id" in res.text or "<title>Just a moment...</title>" in res.text:
                if "<title>Just a moment...</title>" in res.text:
                    logger.warning(f"[{panel['name']}] Cloudflare blocked MK Panel traffic request (403).")
                else:
                    logger.info(f"[{panel['name']}] PHP Session expired or invalid, re-logging in...")
                    panel["sessionCookie"] = ""
                    login_to_panel(panel)
                return

            try:
                feed = res.json().get("feed", [])
            except:
                feed = []

            standard_logs = []
            today_date_str = datetime.now().strftime("%Y-%m-%d")
            current_t = get_current_cest_time()
            for log in feed:
                raw_time = log.get("time", "")
                time_txt = str(raw_time.get("text", "") if isinstance(raw_time, dict) else raw_time).strip()
                
                # 🚀 MK Panel returns relative times like "Just Now" or "3 m ago"
                # If it doesn't have ':', we override non-standard times with current time to show it in live traffic!
                if not time_txt or ":" not in time_txt:
                    time_txt = current_t

                raw_msg = log.get("msg", "") or log.get("sms", "") or log.get("message", "") or ""
                raw_msg = re.sub(r'<[^>]*>', '', raw_msg).replace("&lt;", "<").replace("&gt;", ">")
                
                # 🚀 Smartly extract App Name for different MK panel versions
                app_name = log.get("service_name", "") or log.get("service", "") or log.get("app", "") or ""
                if not app_name:
                    app_name = get_service_short_code("", raw_msg)
                
                number_val = log.get("range", "") or log.get("phone", "") or log.get("number", "") or ""
                
                msg_id = f"{time_txt}_{number_val}_{raw_msg[:10]}"
                
                standard_logs.append({
                    "id": msg_id,
                    "time": time_txt,
                    "number": number_val,
                    "app_name": app_name,
                    "sms": raw_msg,
                    "range": number_val
                })

            # --- START LOCAL TRAFFIC DB CACHE ---
            ref_time = get_current_cest_time()
            if panel.get("is_traffic_active", True):
                for log in standard_logs:
                    if log["id"]: local_raw_logs_cache[log["id"]] = log
            
            new_stats = {}
            keys_to_delete = []
            for log_id, log_data in local_raw_logs_cache.items():
                if get_seconds_difference(log_data.get("time", ""), ref_time) <= 600:
                    raw_service = log_data.get("app_name") or "Unknown"
                    display_service = get_service_display_name(raw_service)
                    num = log_data.get("number") or ""
                    c_code = get_country_code(num)
                    range_val = log_data.get("range") or get_range_from_number(num)

                    new_stats.setdefault(display_service, {}).setdefault(c_code, {"success": 0, "ranges": {}})
                    new_stats[display_service][c_code]["success"] += 1
                    new_stats[display_service][c_code]["ranges"][range_val] = new_stats[display_service][c_code]["ranges"].get(range_val, 0) + 1
                else:
                    keys_to_delete.append(log_id)
            for k in keys_to_delete: del local_raw_logs_cache[k]
            local_traffic_stats = new_stats
            # --- END LOCAL TRAFFIC DB CACHE ---

            if standard_logs:
                standard_logs.sort(key=lambda x: x["id"], reverse=True)

                if not panel.get("lastSeenCDRId"):
                    panel["lastSeenCDRId"] = standard_logs[0]["id"]
                    save_panels_to_file(panels)
                else:
                    new_entries = []
                    for cdr in standard_logs:
                        if cdr["id"] == panel.get("lastSeenCDRId"): break
                        new_entries.append(cdr)
                    if new_entries:
                        logger.info(f"[{panel['name']}] Found {len(new_entries)} new incoming traffic logs.")
                        panel["lastSeenCDRId"] = standard_logs[0]["id"]
                        save_panels_to_file(panels)

            # PHP GetNum Check
            try:
                getnum_url = panel.get("getMessageUrl") or f"{clean_base}/API/api_handler_test.php?action=get_history&page=1&limit=20"
                
                # Using Cloudscraper session to bypass Cloudflare
                num_res = session.get(getnum_url, headers=headers, timeout=20)
                if num_res.status_code == 200:
                    num_data = num_res.json()
                    numbers = num_data.get("data", [])
                    
                    if num_data.get("status") == "success" and isinstance(numbers, list):
                        updated = False
                        if "lastSeenGetnumIds" not in panel or not isinstance(panel["lastSeenGetnumIds"], list):
                            panel["lastSeenGetnumIds"] = []
                        
                        is_initial = len(panel["lastSeenGetnumIds"]) == 0

                        for num in numbers:
                            otps_str = num.get("otps", "")
                            sms_list_str = num.get("full_sms_list", "")
                            otps = otps_str.split("|||") if otps_str else []
                            full_sms_list = sms_list_str.split("|||") if sms_list_str else []
                            
                            # 🚀 Advanced OTP extractor for various MK PHP versions
                            if not otps:
                                fallback_msg = num.get("otp") or num.get("sms") or num.get("message") or num.get("msg")
                                if fallback_msg: otps = [fallback_msg]

                            for i in range(len(otps)):
                                otp_val = str(otps[i]).strip()
                                full_msg = str(full_sms_list[i] if i < len(full_sms_list) else otp_val).strip()

                                if full_msg:
                                    phone_num = num.get("phone_number") or num.get("number") or ""
                                    num_id = num.get("id") or phone_num
                                    unique_key = f"{num_id}_{i}_{full_msg}"
                                    
                                    if unique_key not in panel["lastSeenGetnumIds"]:
                                        if is_initial:
                                            panel["lastSeenGetnumIds"].append(unique_key)
                                            updated = True
                                        else:
                                            svc_name = num.get("service_name") or num.get("service") or "OTP"
                                            logger.info(f"[{panel['name']}] Forwarding PHP GetNum SMS: {phone_num}")
                                            process_and_send_sms(panel['name'], phone_num, svc_name, full_msg)
                                            panel["lastSeenGetnumIds"].append(unique_key)
                                            updated = True

                        if len(panel["lastSeenGetnumIds"]) > 200: panel["lastSeenGetnumIds"] = panel["lastSeenGetnumIds"][-200:]
                        if updated: save_panels_to_file(panels)
            except Exception as e_php_num:
                logger.error(f"[{panel['name']}] PHP GetNum history check failed: {e_php_num}")

        except Exception as e:
            logger.error(f"[{panel['name']}] Error polling PHP updates: {e}")

    # --- START NEXA OTP LOGIC ---
    elif is_nexa_otp(panel):
        try:
            clean_base = get_clean_base_url(panel, baseUrl)
            logs_url = panel.get("trafficUrl") or f"{clean_base}/api/user/console-log"
            headers = {
                "Content-Type": "application/json",
                "X-Session-Token": panel.get("sessionCookie", ""),
                "User-Agent": "Mozilla/5.0"
            }
            res = requests.get(logs_url, headers=headers, timeout=15)
            
            if res.status_code != 200:
                logger.info(f"[{panel['name']}] Nexa Session expired, re-logging in...")
                panel["sessionCookie"] = ""
                login_to_panel(panel)
                return

            data = res.json()
            logs = data.get("data", {}).get("logs", [])
            standard_logs = []
            
            for log in logs:
                delivered_at = log.get("delivered_at", "")
                time_only = delivered_at.split("T")[1][:8] if "T" in delivered_at else log.get("time", "")
                msg_body = log.get("message", "")
                msg_id = f"{delivered_at}_{log.get('number', '')}_{msg_body[:10]}"
                
                standard_logs.append({
                    "id": msg_id,
                    "time": time_only,
                    "number": log.get("number", ""),
                    "app_name": log.get("app_name", ""),
                    "sms": msg_body,
                    "range": log.get("number", "")
                })

            # --- START LOCAL TRAFFIC DB CACHE ---
            ref_time = get_current_cest_time()
            if panel.get("is_traffic_active", True):
                for log in standard_logs:
                    if log["id"]: local_raw_logs_cache[log["id"]] = log
            
            new_stats = {}
            keys_to_delete = []
            for log_id, log_data in local_raw_logs_cache.items():
                if get_seconds_difference(log_data.get("time", ""), ref_time) <= 600:
                    raw_service = log_data.get("app_name") or "Unknown"
                    display_service = get_service_display_name(raw_service)
                    num = log_data.get("number") or ""
                    c_code = get_country_code(num)
                    range_val = log_data.get("range") or get_range_from_number(num)

                    new_stats.setdefault(display_service, {}).setdefault(c_code, {"success": 0, "ranges": {}})
                    new_stats[display_service][c_code]["success"] += 1
                    new_stats[display_service][c_code]["ranges"][range_val] = new_stats[display_service][c_code]["ranges"].get(range_val, 0) + 1
                else:
                    keys_to_delete.append(log_id)
            for k in keys_to_delete: del local_raw_logs_cache[k]
            local_traffic_stats = new_stats
            # --- END LOCAL TRAFFIC DB CACHE ---

            if standard_logs:
                standard_logs.sort(key=lambda x: x["id"], reverse=True)
                if not panel.get("lastSeenCDRId"):
                    panel["lastSeenCDRId"] = standard_logs[0]["id"]
                    save_panels_to_file(panels)
                else:
                    new_entries = []
                    for cdr in standard_logs:
                        if cdr["id"] == panel.get("lastSeenCDRId"): break
                        new_entries.append(cdr)
                    if new_entries:
                        logger.info(f"[{panel['name']}] Found {len(new_entries)} new incoming traffic logs.")
                        panel["lastSeenCDRId"] = standard_logs[0]["id"]
                        save_panels_to_file(panels)

            # Nexa GetNum Check
            try:
                getnum_url = panel.get("getMessageUrl") or f"{clean_base}/api/user/numbers?page=1"
                num_res = requests.get(getnum_url, headers=headers, timeout=15)
                if num_res.status_code == 200:
                    num_data = num_res.json()
                    if num_data.get("success") is True and num_data.get("data"):
                        numbers_obj = num_data["data"]
                        numbers = numbers_obj if isinstance(numbers_obj, list) else list(numbers_obj.values())
                        updated = False
                        if "lastSeenGetnumIds" not in panel or not isinstance(panel["lastSeenGetnumIds"], list):
                            panel["lastSeenGetnumIds"] = []

                        is_initial = len(panel["lastSeenGetnumIds"]) == 0

                        for num in numbers:
                            raw_msg = num.get("message") or num.get("otp") or num.get("sms") or ""
                            msg = str(raw_msg).strip()
                            if msg:
                                unique_key = f"{num.get('internal_id') or num.get('number')}_{msg}"
                                if unique_key not in panel["lastSeenGetnumIds"]:
                                    if is_initial:
                                        panel["lastSeenGetnumIds"].append(unique_key)
                                        updated = True
                                    else:
                                        logger.info(f"[{panel['name']}] Forwarding NexaOTP GetNum SMS: {num.get('number')}")
                                        process_and_send_sms(panel['name'], num.get("number", ""), num.get("app_name", "OTP"), msg)
                                        panel["lastSeenGetnumIds"].append(unique_key)
                                        updated = True

                        if len(panel["lastSeenGetnumIds"]) > 200: panel["lastSeenGetnumIds"] = panel["lastSeenGetnumIds"][-200:]
                        if updated: save_panels_to_file(panels)
            except Exception as num_err:
                logger.error(f"[{panel['name']}] Error polling Nexa GetNum: {num_err}")

        except Exception as e:
            logger.error(f"[{panel['name']}] Error polling Nexa updates: {e}")

    # --- START VOLTX API LOGIC ---
    elif is_voltx_api(panel):
        try:
            clean_base = get_clean_base_url(panel, baseUrl)
            logs_url = panel.get("trafficUrl") or f"{clean_base}/console"
            otp_url = panel.get("getMessageUrl") or f"{clean_base}/success-otp"
            headers = {"Content-Type": "application/json", "mauthapi": panel.get("sessionCookie", "MKJGS2MSZYB")}
            
            # 1. Traffic Fetch
            res = session.get(logs_url, headers=headers, timeout=20)
            if res.status_code == 200:
                data = res.json()
                hits = data.get("data", {}).get("hits", [])
                if isinstance(hits, list):
                    ref_time = get_current_cest_time()
                    if panel.get("is_traffic_active", True):
                        for log in hits:
                            log_id = f"{log.get('time')}_{log.get('range')}_{str(log.get('message', ''))[:5]}"
                            if log_id: local_raw_logs_cache[log_id] = {
                                "time": get_current_cest_time(),
                                "app_name": log.get("sid", "OTP"),
                                "number": log.get("range", ""),
                                "range": log.get("range", "")
                            }
                        
                    new_stats = {}
                    keys_to_delete = []
                    for log_id, log_data in local_raw_logs_cache.items():
                        if get_seconds_difference(log_data.get("time", ""), ref_time) <= 600:
                            display_service = get_service_display_name(log_data.get("app_name") or "Unknown")
                            num = log_data.get("number") or ""
                            c_code = get_country_code(num)
                            range_val = log_data.get("range") or get_range_from_number(num)

                            new_stats.setdefault(display_service, {}).setdefault(c_code, {"success": 0, "ranges": {}})
                            new_stats[display_service][c_code]["success"] += 1
                            new_stats[display_service][c_code]["ranges"][range_val] = new_stats[display_service][c_code]["ranges"].get(range_val, 0) + 1
                        else:
                            keys_to_delete.append(log_id)
                    for k in keys_to_delete: del local_raw_logs_cache[k]
                    local_traffic_stats = new_stats
            
            # 2. OTP Fetch
            otp_res = session.get(otp_url, headers=headers, timeout=20)
            if otp_res.status_code == 200:
                otp_data = otp_res.json()
                otps = otp_data.get("data", {}).get("otps", [])
                if isinstance(otps, list):
                    updated = False
                    if "lastSeenGetnumIds" not in panel or not isinstance(panel["lastSeenGetnumIds"], list):
                        panel["lastSeenGetnumIds"] = []
                    
                    is_initial = len(panel["lastSeenGetnumIds"]) == 0

                    for item in otps:
                        unique_key = str(item.get("otp_id", ""))
                        msg = str(item.get("message", "")).strip()
                        num = str(item.get("number", ""))
                        
                        if unique_key and msg and unique_key not in panel["lastSeenGetnumIds"]:
                            if is_initial:
                                panel["lastSeenGetnumIds"].append(unique_key)
                                updated = True
                            else:
                                logger.info(f"[{panel['name']}] Forwarding Voltx API SMS: {num}")
                                process_and_send_sms(panel['name'], f"+{num}", "OTP", msg)
                                panel["lastSeenGetnumIds"].append(unique_key)
                                updated = True

                    if len(panel["lastSeenGetnumIds"]) > 200: panel["lastSeenGetnumIds"] = panel["lastSeenGetnumIds"][-200:]
                    if updated: save_panels_to_file(panels)

        except Exception as e:
            logger.error(f"[{panel['name']}] Error polling Voltx API: {e}")

    # --- START NEXTJS / X MINT / STEXSMS LOGIC ---
    elif is_nextjs_panel(panel):
        try:
            clean_base = get_clean_base_url(panel, baseUrl)
            logs_url = panel.get("trafficUrl") or f"{clean_base}/mapi/v1/mdashboard/console/info"

            headers = {
                "Content-Type": "application/json",
                "mauthtoken": panel.get("sessionCookie", ""),
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }
            
            # 1. Traffic Data Fetch (Using globally cached session to prevent memory leak)
            res = session.get(logs_url, headers=headers, timeout=20)
            today_date_str = datetime.now().strftime("%Y-%m-%d")
            
            if res.status_code == 401 or res.status_code == 404:
                logger.info(f"[{panel['name']}] Native session token expired ({res.status_code}), reloading session cookies...")
                panel["sessionCookie"] = ""
                login_to_panel(panel)
                return
            elif res.status_code == 403:
                logger.warning(f"[{panel['name']}] Cloudflare 403 on Traffic API. Skipping traffic logs but proceeding to OTP check.")
            elif res.status_code == 200:
                data = res.json()
                logs = data.get("data", {}).get("logs", [])
                if isinstance(logs, list):
                    # --- START LOCAL TRAFFIC DB CACHE ---
                    ref_time = get_current_cest_time()
                    if panel.get("is_traffic_active", True):
                        for log in logs:
                            log_id = str(log.get("id", ""))
                            if log_id: local_raw_logs_cache[log_id] = log
                    
                    new_stats = {}
                    keys_to_delete = []
                    for log_id, log_data in local_raw_logs_cache.items():
                        if get_seconds_difference(log_data.get("time", ""), ref_time) <= 600:
                            raw_service = log_data.get("app_name") or "Unknown"
                            
                            # 🚀 Smart extraction ONLY for StexSMS / X Mint
                            msg_body = str(log_data.get("sms") or log_data.get("smsBody") or log_data.get("message") or "").lower()
                            smart_svc = None
                            
                            if "instagram" in msg_body or "ig code" in msg_body: smart_svc = "Instagram"
                            elif "facebook" in msg_body or "meta" in msg_body or "fb code" in msg_body: smart_svc = "Facebook"
                            elif "whatsapp" in msg_body or "wa code" in msg_body: smart_svc = "WhatsApp"
                            elif "telegram" in msg_body or "tg code" in msg_body: smart_svc = "Telegram"
                            elif "tiktok" in msg_body: smart_svc = "TikTok"
                            elif "google" in msg_body or "g-" in msg_body: smart_svc = "Google"
                            elif "microsoft" in msg_body: smart_svc = "Microsoft"
                            elif "amazon" in msg_body: smart_svc = "Amazon"
                            elif "paypal" in msg_body: smart_svc = "PayPal"
                            elif "viber" in msg_body: smart_svc = "Viber"
                            
                            # If message contains app name, use it. Otherwise, use panel's default name.
                            display_service = smart_svc if smart_svc else get_service_display_name(raw_service)
                            
                            num = log_data.get("number") or ""
                            c_code = get_country_code(num)
                            range_val = log_data.get("range") or get_range_from_number(num)

                            new_stats.setdefault(display_service, {}).setdefault(c_code, {"success": 0, "ranges": {}})
                            new_stats[display_service][c_code]["success"] += 1
                            new_stats[display_service][c_code]["ranges"][range_val] = new_stats[display_service][c_code]["ranges"].get(range_val, 0) + 1
                        else:
                            keys_to_delete.append(log_id)
                    for k in keys_to_delete: del local_raw_logs_cache[k]
                    local_traffic_stats = new_stats
                    # --- END LOCAL TRAFFIC DB CACHE ---

                    cdrs = []
                    for log in logs:
                        cdrs.append({
                            "date": f"{today_date_str} {log.get('time', '')}".strip(),
                            "number": log.get("number", ""),
                            "cli": log.get("app_name", ""),
                            "messageId": str(log.get("id", "")),
                            "smsBody": log.get("sms", "")
                        })

                    if cdrs:
                        cdrs.sort(key=lambda x: x["messageId"], reverse=True)
                        if not panel.get("lastSeenCDRId"):
                            panel["lastSeenCDRId"] = cdrs[0]["messageId"]
                            save_panels_to_file(panels)
                        else:
                            new_entries = []
                            for cdr in cdrs:
                                if cdr["messageId"] == panel.get("lastSeenCDRId"): break
                                new_entries.append(cdr)
                            if new_entries:
                                logger.info(f"[{panel['name']}] Found {len(new_entries)} new incoming traffic logs.")
                                panel["lastSeenCDRId"] = cdrs[0]["messageId"]
                                save_panels_to_file(panels)

            # 2. NextJS GetNum Check (OTP Fetching)
            try:
                clean_base = get_clean_base_url(panel, baseUrl)
                getnum_url = panel.get("getMessageUrl") or f"{clean_base}/mapi/v1/mdashboard/getnum/info"
                # Removed "date" parameter to prevent Timezone/Date mismatch issues causing hidden OTPs
                num_params = {"page": 1, "search": "", "status": ""}
                
                # OTP/Messages GET Request using cached session
                num_res = session.get(getnum_url, headers=headers, params=num_params, timeout=20)
                if num_res.status_code == 200:
                    num_data = num_res.json()
                    numbers = num_data.get("data", {}).get("numbers", [])
                    if isinstance(numbers, list):
                        updated = False
                        if "lastSeenGetnumIds" not in panel or not isinstance(panel["lastSeenGetnumIds"], list):
                            panel["lastSeenGetnumIds"] = []
                        
                        is_initial = len(panel["lastSeenGetnumIds"]) == 0

                        for num in numbers:
                            raw_msg = num.get("message") or num.get("otp") or num.get("sms") or num.get("smsBody") or ""
                            msg = str(raw_msg).strip()
                            if msg:
                                unique_key = f"{num.get('nid') or num.get('number')}_{msg}"
                                if unique_key not in panel["lastSeenGetnumIds"]:
                                    if is_initial:
                                        panel["lastSeenGetnumIds"].append(unique_key)
                                        updated = True
                                    else:
                                        logger.info(f"[{panel['name']}] Parsing active GetNum SMS: {num.get('number')}")
                                        process_and_send_sms(panel['name'], num.get('number', ''), num.get('app_name', ''), msg)
                                        panel["lastSeenGetnumIds"].append(unique_key)
                                        updated = True

                        if len(panel["lastSeenGetnumIds"]) > 200: panel["lastSeenGetnumIds"] = panel["lastSeenGetnumIds"][-200:]
                        if updated: save_panels_to_file(panels)
            except Exception as num_err:
                logger.error(f"[{panel['name']}] Error polling GetNum numbers: {num_err}")

        except Exception as e:
            logger.error(f"[{panel['name']}] Error polling updates: {e}")

def monitor_loop():
    logger.info("Background Panel Monitoring Loop Thread started successfully.")
    sync_counter = 0
    while True:
        try:
            for panel in panels:
                check_cdrs_for_panel(panel)
            
            # 🚀 Auto Sync to Firebase every ~5 minutes (30 loops * 10s)
            sync_counter += 1
            if sync_counter >= 30:
                threading.Thread(target=sync_essential_data_to_firestore, daemon=True).start()
                sync_counter = 0
                
        except Exception as e:
            logger.error(f"Global panel check monitor loop exception: {e}")
        time.sleep(10)

# ----------------------------------------------------
# Main Program Entry Point
# ----------------------------------------------------

def main():
    logger.info("Initializing StexSMS Unified Bot...")
    
    # Run immediate validation of panel logins
    for panel in panels:
        threading.Thread(target=login_to_panel, args=(panel,), daemon=True).start()

    # Start automated background checker thread
    threading.Thread(target=monitor_loop, daemon=True).start()

    # Empty old commands in getUpdates queue to prevent old triggers
    call_telegram("getUpdates", {"offset": -1, "timeout": 0})
    logger.info("StexSMS Telegram Long-Polling Engine online and watching.")

    offset = None
    while True:
        try:
            payload = {"timeout": 30}
            if offset:
                payload["offset"] = offset

            updates = call_telegram("getUpdates", payload)
            if updates and updates.get("ok"):
                for update in updates.get("result", []):
                    offset = update["update_id"] + 1

                    # Core processing routers (Multi-threading added for 0 lag)
                    if "message" in update:
                        threading.Thread(target=handle_message, args=(update["message"],)).start()
                    elif "callback_query" in update:
                        threading.Thread(target=handle_callback_query, args=(update["callback_query"],)).start()

            time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Shutting down bot. Enjoy your day!")
            break
        except Exception as e:
            logger.error(f"Long poll loop iteration error: {e}")
            time.sleep(5)

if __name__ == "__main__":
    main()
