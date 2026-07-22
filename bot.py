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

# ============= সাপোর্টেড কান্ট্রি লিস্ট =============
COUNTRIES = [
    {"serial": "1", "name": "Argentina", "cuy": "ar"},
    {"serial": "2", "name": "Australia", "cuy": "au"},
    {"serial": "3", "name": "Austria", "cuy": "at"},
    {"serial": "4", "name": "Bahrain", "cuy": "bh"},
    {"serial": "5", "name": "Brazil", "cuy": "br"},
    {"serial": "6", "name": "Chile", "cuy": "cl"},
    {"serial": "7", "name": "Colombia", "cuy": "co"},
    {"serial": "8", "name": "Czech Republic", "cuy": "cz"},
    {"serial": "9", "name": "Ecuador", "cuy": "eo"},
    {"serial": "10", "name": "Finland", "cuy": "fi"},
    {"serial": "11", "name": "France", "cuy": "fr"},
    {"serial": "12", "name": "Germany", "cuy": "de"},
    {"serial": "13", "name": "Ghana", "cuy": "gh"},
    {"serial": "14", "name": "Hungary", "cuy": "hu"},
    {"serial": "15", "name": "India", "cuy": "in"},
    {"serial": "16", "name": "Indonesia", "cuy": "id"},
    {"serial": "17", "name": "Ireland", "cuy": "ie"},
    {"serial": "18", "name": "Japan", "cuy": "jp"},
    {"serial": "19", "name": "Jordan", "cuy": "jo"},
    {"serial": "20", "name": "Kenya", "cuy": "ke"},
    {"serial": "21", "name": "Luxembourg", "cuy": "lu"},
    {"serial": "22", "name": "Malaysia", "cuy": "my"},
    {"serial": "23", "name": "Mexico", "cuy": "mx"},
    {"serial": "24", "name": "Netherlands", "cuy": "nl"},
    {"serial": "25", "name": "Nigeria", "cuy": "ng"},
    {"serial": "26", "name": "Norway", "cuy": "no"},
    {"serial": "27", "name": "Panama", "cuy": "pa"},
    {"serial": "28", "name": "Philippines", "cuy": "ph"},
    {"serial": "29", "name": "Poland", "cuy": "pl"},
    {"serial": "30", "name": "Portugal", "cuy": "pt"},
    {"serial": "31", "name": "Romania", "cuy": "ro"},
    {"serial": "32", "name": "Saudi Arabia", "cuy": "sa"},
    {"serial": "33", "name": "Singapore", "cuy": "sg"},
    {"serial": "34", "name": "Viet Nam", "cuy": "vn"},
    {"serial": "35", "name": "Slovenia", "cuy": "si"},
    {"serial": "36", "name": "South Africa", "cuy": "za"},
    {"serial": "37", "name": "Spain", "cuy": "es"},
    {"serial": "38", "name": "Switzerland", "cuy": "ch"},
    {"serial": "39", "name": "Thailand", "cuy": "th"},
    {"serial": "40", "name": "UAE", "cuy": "ae"},
    {"serial": "41", "name": "Macedonia", "cuy": "mk"},
    {"serial": "42", "name": "Egypt", "cuy": "eg"},
    {"serial": "43", "name": "United States", "cuy": "us"},
    {"serial": "44", "name": "Andorra", "cuy": "ad"},
    {"serial": "45", "name": "Afghanistan", "cuy": "af"},
    {"serial": "46", "name": "Antigua", "cuy": "ag"},
    {"serial": "47", "name": "Anguilla", "cuy": "ai"},
    {"serial": "48", "name": "Albania", "cuy": "al"},
    {"serial": "49", "name": "Armenia", "cuy": "am"},
    {"serial": "50", "name": "Angola", "cuy": "ao"},
    {"serial": "51", "name": "American Samoa", "cuy": "as"},
    {"serial": "52", "name": "Aruba", "cuy": "aw"},
    {"serial": "53", "name": "Azerbaijan", "cuy": "az"},
    {"serial": "54", "name": "Bosnia", "cuy": "bs"},
    {"serial": "55", "name": "Barbados", "cuy": "bb"},
    {"serial": "56", "name": "Bangladesh", "cuy": "bd"},
    {"serial": "57", "name": "Belgium", "cuy": "be"},
    {"serial": "58", "name": "Burkina Faso", "cuy": "bt"},
    {"serial": "59", "name": "Bulgaria", "cuy": "bg"},
]

print(f"✅ {len(COUNTRIES)}টি দেশ লোড হয়েছে")

# ============= বট =============
bot = telebot.TeleBot(BOT_TOKEN)
user_data = {}
monitoring_threads = {}
user_states = {}
user_country = {}

# ============= অটো PID ডিটেক্ট =============
def detect_working_pid(serial, cuy):
    """কোন PID কাজ করছে তা ডিটেক্ট করে"""
    pids_to_try = ["7403", "7402", "7401", "7393", "7392", "1", "123", "0"]
    working_pids = []
    
    for pid in pids_to_try:
        try:
            params = {
                'name': USERNAME,
                'ApiKey': API_KEY,
                'cuy': cuy,
                'pid': pid,
                'num': 1,
                'noblack': 0,
                'serial': serial,
                'secret_key': 'null',
                'vip': 'null'
            }
            url = f"{API_BASE_URL}/getMobile"
            if params:
                filtered_params = {k: v for k, v in params.items() if v}
                url += "?" + "&".join([f"{k}={v}" for k, v in filtered_params.items()])
            response = requests.get(url, timeout=10)
            data = response.json()
            
            if data.get('code') == 200:
                working_pids.append(pid)
                print(f"✅ PID {pid} কাজ করছে!")
            else:
                print(f"❌ PID {pid} কাজ করছে না: {data.get('msg')}")
        except:
            pass
        time.sleep(0.3)
    
    return working_pids

# ============= কী-বোর্ড =============
def get_main_keyboard():
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    btn1 = types.KeyboardButton('📱 Get Number')
    btn2 = types.KeyboardButton('💰 Balance')
    btn3 = types.KeyboardButton('📊 Status')
    btn4 = types.KeyboardButton('🗑️ Clear All')
    btn5 = types.KeyboardButton('ℹ️ Help')
    btn6 = types.KeyboardButton('🌍 Change Country')
    btn7 = types.KeyboardButton('📜 Active Numbers')
    markup.add(btn1, btn2, btn3, btn4, btn5, btn6, btn7)
    return markup

# ============= API কল =============
def call_api(endpoint, params=None):
    try:
        url = f"{API_BASE_URL}/{endpoint}"
        if params:
            filtered_params = {k: v for k, v in params.items() if v}
            url += "?" + "&".join([f"{k}={v}" for k, v in filtered_params.items()])
        response = requests.get(url, timeout=15)
        return response.json()
    except Exception as e:
        return {'code': 500, 'msg': str(e)}

# ============= কান্ট্রি সিলেক্ট =============
@bot.message_handler(func=lambda message: message.text == '🌍 Change Country')
def show_countries(message):
    chat_id = message.chat.id
    markup = types.InlineKeyboardMarkup(row_width=2)
    for country in COUNTRIES[:20]:
        btn = types.InlineKeyboardButton(f"🌍 {country['name']}", callback_data=f"country_{country['serial']}_{country['cuy']}")
        markup.add(btn)
    btn_more = types.InlineKeyboardButton("📋 আরও দেখুন", callback_data="more_countries")
    btn_cancel = types.InlineKeyboardButton("❌ বাতিল", callback_data="cancel")
    markup.add(btn_more, btn_cancel)
    bot.send_message(chat_id, "🌍 *কান্ট্রি সিলেক্ট করুন:*", parse_mode='Markdown', reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == 'more_countries')
def show_more_countries(call):
    chat_id = call.message.chat.id
    markup = types.InlineKeyboardMarkup(row_width=2)
    for country in COUNTRIES[20:50]:
        btn = types.InlineKeyboardButton(f"🌍 {country['name']}", callback_data=f"country_{country['serial']}_{country['cuy']}")
        markup.add(btn)
    btn_back = types.InlineKeyboardButton("🔙 আগের পেজ", callback_data="back_countries")
    btn_cancel = types.InlineKeyboardButton("❌ বাতিল", callback_data="cancel")
    markup.add(btn_back, btn_cancel)
    bot.answer_callback_query(call.id)
    bot.edit_message_text("🌍 *কান্ট্রি সিলেক্ট করুন (২১-৫০):*", chat_id, call.message.message_id, parse_mode='Markdown', reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == 'back_countries')
def back_countries(call):
    chat_id = call.message.chat.id
    markup = types.InlineKeyboardMarkup(row_width=2)
    for country in COUNTRIES[:20]:
        btn = types.InlineKeyboardButton(f"🌍 {country['name']}", callback_data=f"country_{country['serial']}_{country['cuy']}")
        markup.add(btn)
    btn_more = types.InlineKeyboardButton("📋 আরও দেখুন", callback_data="more_countries")
    btn_cancel = types.InlineKeyboardButton("❌ বাতিল", callback_data="cancel")
    markup.add(btn_more, btn_cancel)
    bot.answer_callback_query(call.id)
    bot.edit_message_text("🌍 *কান্ট্রি সিলেক্ট করুন:*", chat_id, call.message.message_id, parse_mode='Markdown', reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('country_'))
def select_country(call):
    chat_id = call.message.chat.id
    parts = call.data.split('_')
    serial = parts[1]
    cuy = parts[2]
    country_name = "Unknown"
    for c in COUNTRIES:
        if c['serial'] == serial:
            country_name = c['name']
            break
    
    # PID ডিটেক্ট করুন
    bot.send_message(chat_id, f"🔍 PID ডিটেক্ট করা হচ্ছে... ({country_name})")
    working_pids = detect_working_pid(serial, cuy)
    
    if working_pids:
        user_country[str(chat_id)] = {
            'serial': serial,
            'cuy': cuy,
            'name': country_name,
            'pids': working_pids
        }
        bot.answer_callback_query(call.id, f"✅ {country_name} সিলেক্ট করা হয়েছে! ({len(working_pids)}টি PID পাওয়া গেছে)")
        try:
            bot.delete_message(chat_id, call.message.message_id)
        except:
            pass
        bot.send_message(chat_id, f"✅ *কান্ট্রি সিলেক্ট করা হয়েছে!*\n\n🌍 {country_name}\n📌 Serial: {serial}\n📌 পাওয়া PID: {', '.join(working_pids)}", parse_mode='Markdown')
    else:
        bot.answer_callback_query(call.id, f"❌ {country_name} এ কোনো PID কাজ করছে না!")
        bot.send_message(chat_id, f"❌ {country_name} এ কোনো PID কাজ করছে না! অন্য দেশ ট্রাই করুন।")

# ============= স্টার্ট =============
@bot.message_handler(commands=['start'])
def send_welcome(message):
    chat_id = message.chat.id
    if str(chat_id) not in user_country:
        user_country[str(chat_id)] = {'serial': '56', 'cuy': 'bd', 'name': 'Bangladesh', 'pids': ['7403', '7402', '7401']}
    bot.send_message(chat_id, f"🌟 *ডুরিয়ান আরসিএস বটে স্বাগতম!*\n\n✅ *একাউন্ট:* {USERNAME}\n🌍 *বর্তমান দেশ:* {user_country[str(chat_id)]['name']}\n\n👇 *নিচের বাটন ব্যবহার করুন*", parse_mode='Markdown', reply_markup=get_main_keyboard())

# ============= টেক্সট হ্যান্ডলার =============
@bot.message_handler(func=lambda message: True)
def handle_text_messages(message):
    chat_id = message.chat.id
    text = message.text
    if text == '📱 Get Number' or text == '/getnumber':
        if str(chat_id) not in user_country:
            bot.send_message(chat_id, "❌ আগে 🌍 Change Country দিয়ে দেশ সিলেক্ট করুন!")
            return
        markup = types.InlineKeyboardMarkup(row_width=3)
        for i in range(1, 6):
            markup.add(types.InlineKeyboardButton(f"{i}", callback_data=f"count_{i}"))
        for i in range(6, 11):
            markup.add(types.InlineKeyboardButton(f"{i}", callback_data=f"count_{i}"))
        markup.add(types.InlineKeyboardButton("❌ বাতিল", callback_data="cancel"))
        country = user_country[str(chat_id)]
        bot.send_message(chat_id, f"📱 *কয়টি নাম্বার নিতে চান?*\n\n🌍 দেশ: {country['name']}", parse_mode='Markdown', reply_markup=markup)
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
    else:
        bot.send_message(chat_id, "❓ বাটন ব্যবহার করুন:", reply_markup=get_main_keyboard())

# ============= কলব্যাক =============
@bot.callback_query_handler(func=lambda call: True)
def handle_inline_callback(call):
    chat_id = call.message.chat.id
    if call.data.startswith('count_'):
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

# ============= নাম্বার নেওয়া =============
def get_multiple_numbers(chat_id, count):
    try:
        country = user_country.get(str(chat_id), {'serial': '56', 'cuy': 'bd', 'name': 'Bangladesh', 'pids': ['7403']})
        pids = country.get('pids', ['7403', '7402', '7401'])
        
        bot.send_message(chat_id, f"⏳ {count}টি নাম্বার সংগ্রহ করা হচ্ছে...\n🌍 {country['name']}")
        numbers = []
        success_count = 0
        
        for i in range(count):
            try:
                found = False
                for pid in pids:
                    params = {
                        'name': USERNAME,
                        'ApiKey': API_KEY,
                        'cuy': country['cuy'],
                        'pid': pid,
                        'num': 5,
                        'noblack': 0,
                        'serial': country['serial'],
                        'secret_key': 'null',
                        'vip': 'null'
                    }
                    data = call_api('getMobile', params)
                    if data.get('code') == 200:
                        phone_number = data.get('data', {}).get('mobile')
                        if phone_number:
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
                if not found:
                    bot.send_message(chat_id, f"⚠️ নাম্বার {i+1} পেতে ব্যর্থ")
                time.sleep(0.5)
            except Exception as e:
                bot.send_message(chat_id, f"❌ {str(e)}")
        
        if success_count > 0:
            numbers_text = "\n".join([f"📱 `{num}`" for num in numbers])
            bot.send_message(chat_id, f"✅ *{success_count}টি নাম্বার পেলাম!*\n\n{numbers_text}\n\n🌍 দেশ: {country['name']}\n⏰ ১০ মিনিট ভ্যালিড\n🤖 অটো OTP সক্রিয়", parse_mode='Markdown')
            markup = types.InlineKeyboardMarkup(row_width=2)
            for num in numbers[:10]:
                markup.add(types.InlineKeyboardButton(f"📱 {num[-4:]}", callback_data=f"check_{num}"))
            markup.add(types.InlineKeyboardButton("📊 সব স্ট্যাটাস", callback_data="all_status"))
            markup.add(types.InlineKeyboardButton("🗑️ ক্লিয়ার", callback_data="clear_all"))
            bot.send_message(chat_id, "👇 ডিটেইলস:", reply_markup=markup)
        else:
            bot.send_message(chat_id, "❌ কোনো নাম্বার পাইনি!\n\n💡 টিপস:\n• অন্য দেশ ট্রাই করুন\n• ব্যালেন্স চেক করুন\n• API Key চেক করুন")
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
    while time.time() - start_time < 600:
        try:
            params = {
                'name': USERNAME,
                'ApiKey': API_KEY,
                'pn': phone_number,
                'pid': pid,
                'serial': serial
            }
            data = call_api('getMsg', params)
            if data.get('code') == 200:
                messages = data.get('data', {}).get('messages', [])
                if messages and len(messages) > last_msg_count:
                    new_messages = messages[last_msg_count:]
                    last_msg_count = len(messages)
                    for msg in new_messages:
                        msg_text = msg.get('content', '')
                        otp_matches = re.findall(r'\b\d{4,6}\b', msg_text)
                        otp_code = otp_matches[0] if otp_matches else None
                        if chat_id_str in user_data:
                            for num_data in user_data[chat_id_str]['numbers']:
                                if num_data['phone'] == phone_number:
                                    num_data['otp_received'] = True
                                    num_data['otp_code'] = otp_code
                                    num_data['full_message'] = msg_text
                                    break
                        bot.send_message(chat_id, f"🔔 *OTP পাওয়া গেছে!*\n\n📱 নাম্বার: `{phone_number}`\n🔑 কোড: `{otp_code if otp_code else 'পাইনি'}`\n📩 মেসেজ: {msg_text}\n⏰ {datetime.now().strftime('%I:%M %p')}", parse_mode='Markdown')
            time.sleep(5)
        except Exception as e:
            time.sleep(10)
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
                remaining = int(600 - (time.time() - num_data['timestamp']))
                bot.send_message(chat_id, f"📱 `{phone}`\nস্ট্যাটাস: {status}\nOTP: `{otp}`\nভ্যালিডিটি: {remaining}s", parse_mode='Markdown')
                break

def show_all_status(chat_id):
    chat_id_str = str(chat_id)
    if chat_id_str in user_data:
        text = "📊 *স্ট্যাটাস:*\n\n"
        for num_data in user_data[chat_id_str]['numbers']:
            status = "✅" if num_data['otp_received'] else "⏳"
            otp = num_data['otp_code'] if num_data['otp_code'] else "..."
            remaining = int(600 - (time.time() - num_data['timestamp']))
            text += f"{status} `{num_data['phone']}` → `{otp}` ({remaining}s)\n"
        bot.send_message(chat_id, text, parse_mode='Markdown')

def show_active_numbers(message):
    chat_id = message.chat.id
    chat_id_str = str(chat_id)
    if chat_id_str in user_data and user_data[chat_id_str]['numbers']:
        text = "📱 *আপনার অ্যাক্টিভ নাম্বার:*\n\n"
        for i, num_data in enumerate(user_data[chat_id_str]['numbers'], 1):
            remaining = int(600 - (time.time() - num_data['timestamp']))
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
        print(f"📊 ব্যালেন্স রেসপন্স: {data}")
        
        if data.get('code') == 200:
            balance = data.get('data', {}).get('balance', 'N/A')
            bot.send_message(chat_id, f"💰 *ব্যালেন্স: {balance}*\n\n👤 *একাউন্ট:* {USERNAME}", parse_mode='Markdown')
        else:
            bot.send_message(chat_id, f"❌ {data.get('msg', 'Error')}")
    except Exception as e:
        bot.send_message(chat_id, f"❌ {str(e)}")

def show_help(message):
    bot.send_message(message.chat.id, """
📚 *হেল্প:*

📱 Get Number - নাম্বার নিন
🌍 Change Country - দেশ পরিবর্তন
💰 Balance - ব্যালেন্স চেক
📊 Status - স্ট্যাটাস দেখুন
📜 Active Numbers - অ্যাক্টিভ নাম্বার দেখুন
🗑️ Clear All - সব ক্লিয়ার
ℹ️ Help - এই মেসেজ

✨ *অটো ফিচার:*
• OTP আসলেই অটো নোটিফিকেশন
• ব্যাকগ্রাউন্ড মনিটরিং
• ইনলাইন বাটন কন্ট্রোল
    """, parse_mode='Markdown')

# ============= চালান =============
if __name__ == "__main__":
    print("=" * 50)
    print("🤖 ডুরিয়ান আরসিএস বট চালু হচ্ছে...")
    print(f"👤 ইউজারনাম: {USERNAME}")
    print(f"🌍 সাপোর্টেড দেশ: {len(COUNTRIES)}টি")
    print("=" * 50)
    print("✅ বট প্রস্তুত! টেলিগ্রামে /start দিন")
    print("=" * 50)
    while True:
        try:
            bot.polling(none_stop=True, interval=1)
        except Exception as e:
            print(f"❌ পোলিং এরর: {e}")
            time.sleep(5)
