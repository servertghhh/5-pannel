import telebot
import requests
import json
import time
import threading
import re
from telebot import types
from datetime import datetime
import os

print("🚀 বট লোড হচ্ছে...")

# ============= আপনার ডেটা =============
BOT_TOKEN = "8807543327:AAFxZsJgSbi4wvl0pv1K_yWv6eu0MpkN500"
USERNAME = "Rabbi2780"
API_KEY = "L0J0SG9iVkl2SUxiQ0VEUlZ6SE5zUT09"
API_BASE_URL = "https://api.durianrcs.com/out/ext_api"

print("✅ কনফিগারেশন লোড হয়েছে")

# ============= সাপোর্টেড কান্ট্রি (আপনার স্ক্রিনশট থেকে) =============
COUNTRIES = [
    {"serial": "1", "name": "Argentina", "cuy": "ar", "short": ["arg", "argentina"]},
    {"serial": "2", "name": "Australia", "cuy": "au", "short": ["aus", "australia"]},
    {"serial": "3", "name": "Austria", "cuy": "at", "short": ["aut", "austria"]},
    {"serial": "4", "name": "Bahrain", "cuy": "bh", "short": ["bhr", "bahrain"]},
    {"serial": "5", "name": "Brazil", "cuy": "br", "short": ["bra", "brazil"]},
    {"serial": "6", "name": "Chile", "cuy": "cl", "short": ["chl", "chile"]},
    {"serial": "7", "name": "Colombia", "cuy": "co", "short": ["col", "colombia"]},
    {"serial": "8", "name": "Czech Republic", "cuy": "cz", "short": ["cze", "czech"]},
    {"serial": "9", "name": "Ecuador", "cuy": "eo", "short": ["ecu", "ecuador"]},
    {"serial": "10", "name": "Finland", "cuy": "fi", "short": ["fin", "finland"]},
    {"serial": "11", "name": "France", "cuy": "fr", "short": ["fre", "france"]},
    {"serial": "12", "name": "Germany", "cuy": "de", "short": ["deu", "germany"]},
    {"serial": "13", "name": "Ghana", "cuy": "gh", "short": ["gha", "ghana"]},
    {"serial": "14", "name": "Hungary", "cuy": "hu", "short": ["hun", "hungary"]},
    {"serial": "15", "name": "India", "cuy": "in", "short": ["ind", "india"]},
    {"serial": "16", "name": "Indonesia", "cuy": "id", "short": ["idn", "indonesia"]},
    {"serial": "17", "name": "Ireland", "cuy": "ie", "short": ["irl", "ireland"]},
    {"serial": "18", "name": "Japan", "cuy": "jp", "short": ["jpn", "japan"]},
    {"serial": "19", "name": "Jordan", "cuy": "jo", "short": ["jor", "jordan"]},
    {"serial": "20", "name": "Kenya", "cuy": "ke", "short": ["ken", "kenya"]},
    {"serial": "21", "name": "Luxembourg", "cuy": "lu", "short": ["lux", "luxembourg"]},
    {"serial": "22", "name": "Malaysia", "cuy": "my", "short": ["mys", "malaysia"]},
    {"serial": "23", "name": "Mexico", "cuy": "mx", "short": ["mex", "mexico"]},
    {"serial": "24", "name": "Netherlands", "cuy": "nl", "short": ["nld", "netherlands", "holland"]},
    {"serial": "25", "name": "Nigeria", "cuy": "ng", "short": ["nga", "nigeria"]},
    {"serial": "26", "name": "Norway", "cuy": "no", "short": ["nor", "norway"]},
    {"serial": "27", "name": "Panama", "cuy": "pa", "short": ["pan", "panama"]},
    {"serial": "28", "name": "Philippines", "cuy": "ph", "short": ["phl", "philippines"]},
    {"serial": "29", "name": "Poland", "cuy": "pl", "short": ["pol", "poland"]},
    {"serial": "30", "name": "Portugal", "cuy": "pt", "short": ["prt", "portugal"]},
    {"serial": "31", "name": "Romania", "cuy": "ro", "short": ["rou", "romania"]},
    {"serial": "32", "name": "Saudi Arabia", "cuy": "sa", "short": ["sau", "saudi"]},
    {"serial": "33", "name": "Singapore", "cuy": "sg", "short": ["sgp", "singapore"]},
    {"serial": "34", "name": "Viet Nam", "cuy": "vn", "short": ["vnm", "vietnam", "viet"]},
    {"serial": "35", "name": "Slovenia", "cuy": "si", "short": ["svn", "slovenia"]},
    {"serial": "36", "name": "South Africa", "cuy": "za", "short": ["zaf", "southafrica"]},
    {"serial": "37", "name": "Spain", "cuy": "es", "short": ["esp", "spain"]},
    {"serial": "38", "name": "Switzerland", "cuy": "ch", "short": ["che", "switzerland"]},
    {"serial": "39", "name": "Thailand", "cuy": "th", "short": ["tha", "thailand"]},
    {"serial": "40", "name": "UAE", "cuy": "ae", "short": ["are", "uae", "dubai"]},
    {"serial": "41", "name": "Macedonia", "cuy": "mk", "short": ["mkd", "macedonia"]},
    {"serial": "42", "name": "Egypt", "cuy": "eg", "short": ["egy", "egypt"]},
    {"serial": "43", "name": "United States", "cuy": "us", "short": ["usa", "us", "america", "unitedstates"]},
    {"serial": "44", "name": "Andorra", "cuy": "ad", "short": ["and", "andorra"]},
    {"serial": "45", "name": "Afghanistan", "cuy": "af", "short": ["afg", "afghanistan"]},
    {"serial": "46", "name": "Antigua", "cuy": "ag", "short": ["atg", "antigua"]},
    {"serial": "47", "name": "Anguilla", "cuy": "ai", "short": ["aia", "anguilla"]},
    {"serial": "48", "name": "Albania", "cuy": "al", "short": ["alb", "albania"]},
    {"serial": "49", "name": "Armenia", "cuy": "am", "short": ["arm", "armenia"]},
    {"serial": "50", "name": "Angola", "cuy": "ao", "short": ["ago", "angola"]},
    {"serial": "51", "name": "American Samoa", "cuy": "as", "short": ["asm", "americansamoa"]},
    {"serial": "52", "name": "Aruba", "cuy": "aw", "short": ["abw", "aruba"]},
    {"serial": "53", "name": "Azerbaijan", "cuy": "az", "short": ["aze", "azerbaijan"]},
    {"serial": "54", "name": "Bosnia", "cuy": "bs", "short": ["bih", "bosnia"]},
    {"serial": "55", "name": "Barbados", "cuy": "bb", "short": ["brb", "barbados"]},
    {"serial": "56", "name": "Bangladesh", "cuy": "bd", "short": ["bgd", "bangladesh", "bd"]},
    {"serial": "57", "name": "Belgium", "cuy": "be", "short": ["bel", "belgium"]},
    {"serial": "58", "name": "Burkina Faso", "cuy": "bt", "short": ["bfa", "burkina"]},
    {"serial": "59", "name": "Bulgaria", "cuy": "bg", "short": ["bgr", "bulgaria"]},
]

print(f"✅ {len(COUNTRIES)}টি দেশ লোড হয়েছে")

# ============= বট =============
bot = telebot.TeleBot(BOT_TOKEN)
user_data = {}
monitoring_threads = {}
user_states = {}
user_country = {}
user_search = {}  # সার্চ স্টেট ট্র্যাক করার জন্য

# ============= কী-বোর্ড =============
def get_main_keyboard():
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    btn1 = types.KeyboardButton('📱 Get Number')
    btn2 = types.KeyboardButton('💰 Balance')
    btn3 = types.KeyboardButton('📊 Status')
    btn4 = types.KeyboardButton('🗑️ Clear All')
    btn5 = types.KeyboardButton('ℹ️ Help')
    btn6 = types.KeyboardButton('🔍 Search Country')
    btn7 = types.KeyboardButton('📜 Active Numbers')
    markup.add(btn1, btn2, btn3, btn4, btn5, btn6, btn7)
    return markup

# ============= API কল =============
def call_api(endpoint, params=None):
    try:
        url = f"{API_BASE_URL}/{endpoint}"
        if params:
            filtered_params = {k: v for k, v in params.items() if v is not None and v != 'null'}
            url += "?" + "&".join([f"{k}={v}" for k, v in filtered_params.items()])
        print(f"📡 {url}")
        response = requests.get(url, timeout=15)
        return response.json()
    except Exception as e:
        print(f"❌ {e}")
        return {'code': 500, 'msg': str(e)}

# ============= কান্ট্রি সার্চ ফাংশন =============
def search_country(query):
    """কান্ট্রি নাম বা শর্টকাট দিয়ে সার্চ করুন"""
    query = query.lower().strip()
    results = []
    
    for country in COUNTRIES:
        # নামের সাথে মিল
        if query in country['name'].lower():
            results.append(country)
        # শর্টকাটের সাথে মিল
        elif any(query in short.lower() for short in country['short']):
            results.append(country)
        # কান্ট্রি কোডের সাথে মিল
        elif query == country['cuy'].lower():
            results.append(country)
        # সিরিয়াল নম্বরের সাথে মিল
        elif query == country['serial']:
            results.append(country)
    
    return results

# ============= কান্ট্রি সিলেক্ট =============
@bot.message_handler(func=lambda message: message.text == '🔍 Search Country')
def search_country_prompt(message):
    chat_id = message.chat.id
    user_search[str(chat_id)] = True
    bot.send_message(chat_id, 
        "🔍 *কান্ট্রি খুঁজুন:*\n\n"
        "কান্ট্রির নাম, শর্টকাট বা কোড লিখুন।\n"
        "যেমন: `bd`, `bangladesh`, `us`, `usa`, `india`\n\n"
        "📌 *টিপস:*\n"
        "• `bd` → বাংলাদেশ\n"
        "• `us` → যুক্তরাষ্ট্র\n"
        "• `uk` → যুক্তরাজ্য\n"
        "• `in` → ভারত",
        parse_mode='Markdown'
    )

# ============= টেক্সট হ্যান্ডলার (সার্চ) =============
@bot.message_handler(func=lambda message: True)
def handle_text_messages(message):
    chat_id = message.chat.id
    text = message.text
    
    # ===== সার্চ মোড =====
    if str(chat_id) in user_search and user_search[str(chat_id)]:
        # সার্চ করুন
        results = search_country(text)
        
        if results:
            # রেজাল্ট দেখান
            markup = types.InlineKeyboardMarkup(row_width=2)
            for country in results[:20]:  # সর্বোচ্চ ২০টা দেখান
                btn = types.InlineKeyboardButton(
                    f"🌍 {country['name']} ({country['cuy'].upper()})", 
                    callback_data=f"country_{country['serial']}_{country['cuy']}"
                )
                markup.add(btn)
            
            btn_cancel = types.InlineKeyboardButton("❌ বাতিল", callback_data="cancel")
            markup.add(btn_cancel)
            
            user_search[str(chat_id)] = False
            bot.send_message(chat_id, 
                f"🔍 *'{text}' এর জন্য {len(results)}টি ফলাফল পাওয়া গেছে:*", 
                parse_mode='Markdown',
                reply_markup=markup
            )
        else:
            bot.send_message(chat_id, 
                f"❌ '{text}' এর জন্য কোনো কান্ট্রি পাওয়া যায়নি!\n\n"
                f"💡 আবার চেষ্টা করুন অথবা বাটন ব্যবহার করুন।",
                reply_markup=get_main_keyboard()
            )
            user_search[str(chat_id)] = False
        return
    
    # ===== অন্যান্য বাটন =====
    if text == '📱 Get Number' or text == '/getnumber':
        if str(chat_id) not in user_country:
            bot.send_message(chat_id, "❌ আগে 🔍 Search Country দিয়ে দেশ সিলেক্ট করুন!")
            return
        markup = types.InlineKeyboardMarkup(row_width=3)
        for i in range(1, 6):
            markup.add(types.InlineKeyboardButton(f"{i}", callback_data=f"count_{i}"))
        for i in range(6, 11):
            markup.add(types.InlineKeyboardButton(f"{i}", callback_data=f"count_{i}"))
        markup.add(types.InlineKeyboardButton("❌ বাতিল", callback_data="cancel"))
        country = user_country[str(chat_id)]
        bot.send_message(chat_id, 
            f"📱 *কয়টি নাম্বার নিতে চান?*\n\n🌍 দেশ: {country['name']}", 
            parse_mode='Markdown', 
            reply_markup=markup
        )
        user_states[str(chat_id)] = 'waiting_count'
    
    elif text == '💰 Balance' or text == '/balance':
        check_balance(message)
    
    elif text == '📊 Status' or text == '/status':
        show_status(message)
    
    elif text == '🗑️ Clear All' or text == '/clear':
        clear_all(message)
    
    elif text == 'ℹ️ Help' or text == '/help':
        show_help(message)
    
    elif text == '📜 Active Numbers':
        show_active_numbers(message)
    
    elif text == '🔍 Search Country':
        # ইতিমধ্যে হ্যান্ডল করা হয়েছে
        pass
    
    else:
        bot.send_message(chat_id, "❓ বাটন ব্যবহার করুন:", reply_markup=get_main_keyboard())

# ============= কলব্যাক =============
@bot.callback_query_handler(func=lambda call: True)
def handle_inline_callback(call):
    chat_id = call.message.chat.id
    
    if call.data.startswith('country_'):
        parts = call.data.split('_')
        serial = parts[1]
        cuy = parts[2]
        country_name = "Unknown"
        for c in COUNTRIES:
            if c['serial'] == serial:
                country_name = c['name']
                break
        user_country[str(chat_id)] = {'serial': serial, 'cuy': cuy, 'name': country_name}
        bot.answer_callback_query(call.id, f"✅ {country_name} সিলেক্ট করা হয়েছে!")
        try:
            bot.delete_message(chat_id, call.message.message_id)
        except:
            pass
        bot.send_message(chat_id, 
            f"✅ *কান্ট্রি সিলেক্ট করা হয়েছে!*\n\n"
            f"🌍 {country_name}\n"
            f"📌 Serial: {serial}\n"
            f"📌 Code: {cuy.upper()}", 
            parse_mode='Markdown',
            reply_markup=get_main_keyboard()
        )
    
    elif call.data.startswith('count_'):
        count = int(call.data.split('_')[1])
        bot.answer_callback_query(call.id, f"{count}টি নাম্বার নেওয়া হচ্ছে...")
        try:
            bot.delete_message(chat_id, call.message.message_id)
        except:
            pass
        get_multiple_numbers(chat_id, count)
    
    elif call.data == 'cancel':
        bot.answer_callback_query(call.id, "বাতিল!")
        try:
            bot.delete_message(chat_id, call.message.message_id)
        except:
            pass
        user_states[str(chat_id)] = None
        user_search[str(chat_id)] = False
        bot.send_message(chat_id, "✅ বাতিল!", reply_markup=get_main_keyboard())
    
    elif call.data.startswith('check_'):
        phone = call.data.replace('check_', '')
        show_number_details(chat_id, phone)
    
    elif call.data == 'all_status':
        show_all_status(chat_id)
    
    elif call.data == 'clear_all':
        if str(chat_id) in user_data:
            for num_data in user_data[str(chat_id)]['numbers']:
                thread_key = f"{chat_id}_{num_data['phone']}"
                if thread_key in monitoring_threads:
                    del monitoring_threads[thread_key]
            del user_data[str(chat_id)]
        bot.answer_callback_query(call.id, "ক্লিয়ার!")
        try:
            bot.delete_message(chat_id, call.message.message_id)
        except:
            pass
        bot.send_message(chat_id, "✅ ক্লিয়ার!", reply_markup=get_main_keyboard())

# ============= স্টার্ট =============
@bot.message_handler(commands=['start'])
def send_welcome(message):
    chat_id = message.chat.id
    if str(chat_id) not in user_country:
        user_country[str(chat_id)] = {'serial': '56', 'cuy': 'bd', 'name': 'Bangladesh'}
    
    # ব্যালেন্স দেখান
    try:
        params = {'name': USERNAME, 'ApiKey': API_KEY}
        data = call_api('getUserInfo', params)
        balance = data.get('data', {}).get('score', 'N/A')
    except:
        balance = 'N/A'
    
    bot.send_message(chat_id, 
        f"🌟 *ডুরিয়ান আরসিএস বটে স্বাগতম!*\n\n"
        f"✅ *একাউন্ট:* {USERNAME}\n"
        f"💰 *ব্যালেন্স:* {balance}\n"
        f"🌍 *বর্তমান দেশ:* {user_country[str(chat_id)]['name']}\n\n"
        f"👇 *নিচের বাটন ব্যবহার করুন*\n"
        f"🔍 *Search Country* → নাম/শর্টকাট দিয়ে দেশ খুঁজুন", 
        parse_mode='Markdown', 
        reply_markup=get_main_keyboard()
    )

# ============= নাম্বার নেওয়া =============
def get_multiple_numbers(chat_id, count):
    try:
        country = user_country.get(str(chat_id), {'serial': '56', 'cuy': 'bd', 'name': 'Bangladesh'})
        
        bot.send_message(chat_id, f"⏳ {count}টি নাম্বার সংগ্রহ করা হচ্ছে...\n🌍 {country['name']}")
        
        numbers = []
        success_count = 0
        
        # আপনার PID গুলো (Project ID)
        pids_to_try = ["7403", "7402", "7401", "7393", "7392"]
        
        for i in range(count):
            try:
                found = False
                for pid in pids_to_try:
                    params = {
                        'name': USERNAME,
                        'ApiKey': API_KEY,
                        'cuy': country['cuy'],
                        'pid': pid,
                        'num': 1,
                        'noblack': 0,
                        'serial': 2,
                        'secret_key': 'null',
                        'vip': 'null'
                    }
                    data = call_api('getMobile', params)
                    print(f"📊 PID {pid}: {data}")
                    
                    if data.get('code') == 200:
                        phone_number = data.get('data')
                        if phone_number and isinstance(phone_number, str):
                            numbers.append(phone_number)
                            success_count += 1
                            found = True
                            
                            chat_id_str = str(chat_id)
                            if chat_id_str not in user_data:
                                user_data[chat_id_str] = {'numbers': []}
                            
                            user_data[chat_id_str]['numbers'].append({
                                'phone': phone_number,
                                'timestamp': time.time(),
                                'pid': pid,
                                'serial': country['serial'],
                                'cuy': country['cuy'],
                                'country': country['name'],
                                'otp_received': False,
                                'otp_code': None,
                                'full_message': None
                            })
                            
                            start_monitoring(chat_id, phone_number)
                            break
                    else:
                        error_msg = data.get('msg', 'Unknown error')
                        print(f"❌ PID {pid} ব্যর্থ: {error_msg}")
                        
                        if data.get('code') == 403:
                            bot.send_message(chat_id, "⚠️ ব্যালেন্স কম! রিচার্জ করুন।")
                            return
                        elif data.get('code') == 904:
                            bot.send_message(chat_id, f"⚠️ PID {pid} সঠিক নয়!")
                        elif data.get('code') == 400906:
                            bot.send_message(chat_id, f"⚠️ Serial প্যারামিটার ভুল!")
                
                if not found:
                    bot.send_message(chat_id, f"⚠️ নাম্বার {i+1} পেতে ব্যর্থ")
                
                time.sleep(0.5)
                
            except Exception as e:
                bot.send_message(chat_id, f"❌ {str(e)}")
        
        if success_count > 0:
            numbers_text = "\n".join([f"📱 `{num}`" for num in numbers])
            bot.send_message(chat_id, 
                f"✅ *{success_count}টি নাম্বার পেলাম!*\n\n{numbers_text}\n\n"
                f"🌍 দেশ: {country['name']}\n"
                f"⏰ ৫ মিনিট ভ্যালিড\n"
                f"🤖 অটো OTP সক্রিয়\n"
                f"💡 ৫ সেকেন্ড অপেক্ষা করে OTP পাঠান", 
                parse_mode='Markdown'
            )
            
            markup = types.InlineKeyboardMarkup(row_width=2)
            for num in numbers[:10]:
                markup.add(types.InlineKeyboardButton(f"📱 {num[-4:]}", callback_data=f"check_{num}"))
            markup.add(types.InlineKeyboardButton("📊 সব স্ট্যাটাস", callback_data="all_status"))
            markup.add(types.InlineKeyboardButton("🗑️ ক্লিয়ার", callback_data="clear_all"))
            bot.send_message(chat_id, "👇 ডিটেইলস:", reply_markup=markup)
        else:
            bot.send_message(chat_id, 
                f"❌ কোনো নাম্বার পাইনি!\n\n"
                f"💡 *টিপস:*\n"
                f"• অন্য দেশ ট্রাই করুন\n"
                f"• ব্যালেন্স চেক করুন (/balance)\n"
                f"• PID সঠিক কিনা চেক করুন"
            )
            
    except Exception as e:
        bot.send_message(chat_id, f"❌ {str(e)}")

# ============= OTP মনিটরিং =============
def start_monitoring(chat_id, phone_number):
    thread_key = f"{chat_id}_{phone_number}"
    if thread_key in monitoring_threads and monitoring_threads[thread_key].is_alive():
        return
    thread = threading.Thread(target=monitor_otp, args=(chat_id, phone_number), daemon=True)
    monitoring_threads[thread_key] = thread
    thread.start()

def monitor_otp(chat_id, phone_number):
    start_time = time.time()
    last_msg_count = 0
    
    pid = "7403"
    serial = "56"
    chat_id_str = str(chat_id)
    if chat_id_str in user_data:
        for num_data in user_data[chat_id_str]['numbers']:
            if num_data['phone'] == phone_number:
                pid = num_data.get('pid', '7403')
                serial = num_data.get('serial', '56')
                break
    
    while time.time() - start_time < 300:
        try:
            params = {
                'name': USERNAME,
                'ApiKey': API_KEY,
                'pn': phone_number,
                'pid': pid,
                'serial': 2
            }
            data = call_api('getMsg', params)
            
            if data.get('code') == 200:
                otp_code = data.get('data')
                if otp_code:
                    if chat_id_str in user_data:
                        for num_data in user_data[chat_id_str]['numbers']:
                            if num_data['phone'] == phone_number:
                                num_data['otp_received'] = True
                                num_data['otp_code'] = otp_code
                                num_data['full_message'] = otp_code
                                break
                    
                    bot.send_message(chat_id, 
                        f"🔔 *OTP পাওয়া গেছে!*\n\n"
                        f"📱 নাম্বার: `{phone_number}`\n"
                        f"🔑 কোড: `{otp_code}`\n"
                        f"⏰ {datetime.now().strftime('%I:%M %p')}", 
                        parse_mode='Markdown'
                    )
                    break
            
            elif data.get('code') == 908:
                pass
            elif data.get('code') == 405:
                bot.send_message(chat_id, f"⚠️ {phone_number} এর জন্য SMS পাওয়া যায়নি")
                break
            
            time.sleep(15)
            
        except Exception as e:
            print(f"⚠️ {e}")
            time.sleep(15)
    
    thread_key = f"{chat_id}_{phone_number}"
    if thread_key in monitoring_threads:
        del monitoring_threads[thread_key]

# ============= হেল্পার =============
def show_number_details(chat_id, phone):
    chat_id_str = str(chat_id)
    if chat_id_str in user_data:
        for num_data in user_data[chat_id_str]['numbers']:
            if num_data['phone'] == phone:
                status = "✅" if num_data['otp_received'] else "⏳"
                otp = num_data['otp_code'] if num_data['otp_code'] else "N/A"
                remaining = int(300 - (time.time() - num_data['timestamp']))
                bot.send_message(chat_id, 
                    f"📱 `{phone}`\n"
                    f"স্ট্যাটাস: {status}\n"
                    f"OTP: `{otp}`\n"
                    f"ভ্যালিডিটি: {remaining}s", 
                    parse_mode='Markdown'
                )
                break

def show_all_status(chat_id):
    chat_id_str = str(chat_id)
    if chat_id_str in user_data:
        text = "📊 *স্ট্যাটাস:*\n\n"
        for num_data in user_data[chat_id_str]['numbers']:
            status = "✅" if num_data['otp_received'] else "⏳"
            otp = num_data['otp_code'] if num_data['otp_code'] else "..."
            remaining = int(300 - (time.time() - num_data['timestamp']))
            text += f"{status} `{num_data['phone']}` → `{otp}` ({remaining}s)\n"
        bot.send_message(chat_id, text, parse_mode='Markdown')

def show_active_numbers(message):
    chat_id = message.chat.id
    chat_id_str = str(chat_id)
    
    if chat_id_str in user_data and user_data[chat_id_str]['numbers']:
        text = "📱 *আপনার অ্যাক্টিভ নাম্বার:*\n\n"
        for i, num_data in enumerate(user_data[chat_id_str]['numbers'], 1):
            remaining = int(300 - (time.time() - num_data['timestamp']))
            if remaining > 0:
                status = "✅ OTP পেয়েছে" if num_data['otp_received'] else "⏳ অপেক্ষমান"
                text += f"{i}. `{num_data['phone']}`\n   → {status}\n   → {remaining}সেকেন্ড বাকি\n\n"
            else:
                text += f"{i}. `{num_data['phone']}` ⏰ এক্সপায়ার্ড\n\n"
        
        if len(text) > 4000:
            text = text[:4000] + "\n...(বাকি অংশ কাটা হয়েছে)"
        bot.send_message(chat_id, text, parse_mode='Markdown')
    else:
        bot.send_message(chat_id, "📭 কোনো অ্যাক্টিভ নাম্বার নেই!")

def show_status(message):
    chat_id = message.chat.id
    chat_id_str = str(chat_id)
    if chat_id_str in user_data and user_data[chat_id_str]['numbers']:
        total = len(user_data[chat_id_str]['numbers'])
        received = sum(1 for n in user_data[chat_id_str]['numbers'] if n['otp_received'])
        bot.send_message(chat_id, f"📊 মোট: {total}, OTP প্রাপ্ত: {received}")
    else:
        bot.send_message(chat_id, "📭 কোনো নাম্বার নেই!")

def clear_all(message):
    chat_id = message.chat.id
    chat_id_str = str(chat_id)
    if chat_id_str in user_data:
        for num_data in user_data[chat_id_str]['numbers']:
            thread_key = f"{chat_id}_{num_data['phone']}"
            if thread_key in monitoring_threads:
                del monitoring_threads[thread_key]
        del user_data[chat_id_str]
        bot.send_message(chat_id, "✅ ক্লিয়ার!", reply_markup=get_main_keyboard())

def check_balance(message):
    chat_id = message.chat.id
    try:
        params = {'name': USERNAME, 'ApiKey': API_KEY}
        data = call_api('getUserInfo', params)
        print(f"📊 {data}")
        
        if data.get('code') == 200:
            balance = data.get('data', {}).get('score', 'N/A')
            bot.send_message(chat_id, 
                f"💰 *ব্যালেন্স: {balance}*\n\n"
                f"👤 *একাউন্ট:* {USERNAME}\n"
                f"📅 *জয়েন:* {data.get('data', {}).get('create_date', 'N/A')}", 
                parse_mode='Markdown'
            )
        else:
            bot.send_message(chat_id, f"❌ {data.get('msg', 'Error')}")
    except Exception as e:
        bot.send_message(chat_id, f"❌ {str(e)}")

def show_help(message):
    bot.send_message(message.chat.id, """
📚 *হেল্প:*

🔍 **Search Country** - নাম/শর্টকাট দিয়ে দেশ খুঁজুন
   যেমন: `bd`, `bangladesh`, `us`, `india`

📱 **Get Number** - নাম্বার নিন (৫ মিনিট ভ্যালিড)
💰 **Balance** - ব্যালেন্স চেক
📊 **Status** - স্ট্যাটাস দেখুন
📜 **Active Numbers** - অ্যাক্টিভ নাম্বার দেখুন
🗑️ **Clear All** - সব ক্লিয়ার
ℹ️ **Help** - এই মেসেজ

✨ *অটো ফিচার:*
• OTP আসলেই অটো নোটিফিকেশন
• ১৫ সেকেন্ড পর পর OTP চেক

📌 *টিপস:*
• নাম্বার পেয়ে ৫ সেকেন্ড পর OTP পাঠান
• ৫ মিনিট ভ্যালিড
• SMS না এলে ১৫ সেকেন্ড পর আবার চেক করুন
    """, parse_mode='Markdown')

# ============= চালান =============
if __name__ == "__main__":
    print("=" * 50)
    print("🤖 ডুরিয়ান আরসিএস বট চালু হচ্ছে...")
    print(f"👤 ইউজারনাম: {USERNAME}")
    print(f"🔑 API কী: {API_KEY[:10]}...")
    print(f"🌍 সাপোর্টেড দেশ: {len(COUNTRIES)}টি")
    print("=" * 50)
    print("✅ বট প্রস্তুত! টেলিগ্রামে /start দিন")
    print("=" * 50)
    
    while True:
        try:
            bot.polling(none_stop=True, interval=1)
        except Exception as e:
            print(f"❌ {e}")
            time.sleep(5)
