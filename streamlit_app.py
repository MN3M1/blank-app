import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import requests
import json
from pyrogram import Client, filters
from pyrogram.types import Message
import aiohttp
import os
import asyncio
from datetime import datetime
import uuid

# Telegram bot token
BOT_TOKEN = "8498331387:AAFcXV_yZSvfdxzYgchEBbjuJljt-yC5sAw"
# Pyrogram API credentials
API_ID = 20569963
API_HASH = "37f536fd550fa5dd70cdaaca39c2b1d7"
PYROGRAM_BOT_TOKEN = "8498331387:AAG8kflbjMHZChqvo3fkOfZmmSR1cvBJUJY"

# Initialize Telebot
bot = telebot.TeleBot(BOT_TOKEN)

# Initialize Pyrogram client
pyro_bot = Client(
    "streaming_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=PYROGRAM_BOT_TOKEN
)

API_BASE = 'https://api.x7m.site/akwam/'

data_map = {}
map_counter = 0

def get_key(value):
    global map_counter
    key = str(map_counter)
    data_map[key] = value
    map_counter += 1
    return key

# Function to create a constant dev button
def get_dev_button():
    return InlineKeyboardButton("👨‍💻 المطور @M_N_3_M", url="https://t.me/M_N_3_M")

# Function to search API
def search_api(query, page=1):
    url = f"{API_BASE}?q={query}&page={page}"
    try:
        response = requests.get(url)
        return response.json() if response.status_code == 200 else None
    except:
        return None

# Function to get item details
def get_item_details(link):
    url = f"{API_BASE}?link={link}"
    try:
        response = requests.get(url)
        return response.json() if response.status_code == 200 else None
    except:
        return None

# Function to get episode watch links
def get_episode_links(ep_link):
    url = f"{API_BASE}?ep={ep_link}"
    try:
        response = requests.get(url)
        return response.json() if response.status_code == 200 else None
    except:
        return None

# Async function to stream and upload video using Pyrogram
async def stream_video(chat_id, file_url, file_name="video.mp4"):
    progress_msg = await bot.send_message(chat_id, "🔄 **جاري الاتصال بالخادم...**\n\n⏳ الرجاء الانتظار أثناء جلب الفيديو.")
    
    try:
        timeout = aiohttp.ClientTimeout(total=300)  # 5 minute timeout
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.head(file_url, ssl=False) as head_resp:
                if head_resp.status != 200:
                    await bot.edit_message_text(f"❌ فشل في الوصول إلى الملف. رمز الحالة: {head_resp.status}", chat_id, progress_msg.message_id)
                    return
                
                file_size = int(head_resp.headers.get('content-length', 0))
                size_mb = file_size / (1024 * 1024) if file_size > 0 else 0
                await bot.edit_message_text(
                    f"📥 **جاري التحميل: {file_name}**\n"
                    f"📊 الحجم: {size_mb:.1f} ميغابايت\n\n"
                    f"🔄 التقدم: 0% (جاري البدء...)\n"
                    f"⏱️ الحالة: جاري التحميل...",
                    chat_id, progress_msg.message_id
                )

            async with session.get(file_url, ssl=False) as resp:
                if resp.status == 200:
                    from io import BytesIO
                    video_content = BytesIO()
                    downloaded = 0
                    chunk_size = 8192  # 8KB chunks
                    last_update = datetime.now()
                    
                    async for chunk in resp.content.iter_chunked(chunk_size):
                        video_content.write(chunk)
                        downloaded += len(chunk)
                        
                        now = datetime.now()
                        if (now - last_update).total_seconds() >= 2:
                            if file_size > 0:
                                progress = (downloaded / file_size) * 100
                                progress_bar = "█" * int(progress // 5) + "░" * (20 - int(progress // 5))
                                await bot.edit_message_text(
                                    f"📥 **جاري التحميل: {file_name}**\n"
                                    f"📊 الحجم: {size_mb:.1f} ميغابايت\n\n"
                                    f"🔄 التقدم: {progress:.1f}%\n"
                                    f"[{progress_bar}]\n"
                                    f"⏱️ تم التحميل: {downloaded/(1024*1024):.1f} ميغابايت",
                                    chat_id, progress_msg.message_id
                                )
                            last_update = now
                    
                    await bot.edit_message_text(
                        f"📤 **جاري الرفع إلى تليجرام...**\n"
                        f"📊 الملف: {file_name}\n"
                        f"✅ اكتمل التحميل: {size_mb:.1f} ميغابايت\n\n"
                        f"🔄 الحالة: جاري الرفع إلى تليجرام...",
                        chat_id, progress_msg.message_id
                    )
                    
                    video_content.seek(0)
                    video_content.name = file_name
                    
                    async with pyro_bot:
                        await pyro_bot.send_video(
                            chat_id=chat_id,
                            video=video_content,
                            caption=f"🎬 **{file_name}**\n📊 الحجم: {size_mb:.1f} ميغابايت\n✅ تم الرفع بنجاح!",
                            file_name=file_name
                        )
                    
                    await bot.edit_message_text(
                        f"✅ **اكتمل الرفع!**\n"
                        f"📺 الملف: {file_name}\n"
                        f"📊 الحجم: {size_mb:.1f} ميغابايت\n"
                        f"🎉 تم بث الفيديو بنجاح!",
                        chat_id, progress_msg.message_id
                    )
                else:
                    await bot.edit_message_text(f"❌ فشل في تحميل الملف. رمز الحالة: {resp.status}", chat_id, progress_msg.message_id)
                    
    except asyncio.TimeoutError:
        await bot.edit_message_text("❌ **خطأ المهلة**\n\nاستغرق التحميل وقتًا طويلاً. حاول بملف أصغر أو تحقق من اتصالك بالإنترنت.", chat_id, progress_msg.message_id)
    except Exception as e:
        error_msg = str(e)
        if "SSL" in error_msg:
            await bot.edit_message_text("❌ **خطأ شهادة SSL**\n\nتعذر التحقق من شهادة الخادم. قد تكون هذه مشكلة أمان مع مضيف الفيديو.", chat_id, progress_msg.message_id)
        elif "DNS" in error_msg or "resolve" in error_msg:
            await bot.edit_message_text("❌ **خطأ الاتصال**\n\nتعذر الاتصال بالخادم. الرجاء التحقق من الرابط وحاول مرة أخرى.", chat_id, progress_msg.message_id)
        else:
            await bot.edit_message_text(f"❌ **حدث خطأ:**\n\n`{error_msg}`\n\nحاول مرة أخرى أو تواصل مع الدعم.", chat_id, progress_msg.message_id)

# Start command
@bot.message_handler(commands=['start'])
def start(message):
    markup = InlineKeyboardMarkup()
    markup.add(get_dev_button())
    bot.send_message(message.chat.id, "🎬 مرحباً! أرسل اسم فيلم أو مسلسل للبحث.", reply_markup=markup)

# Handle text search
@bot.message_handler(func=lambda message: True)
def handle_search(message):
    query = message.text.strip()
    query_key = get_key(query)
    results = search_api(query)
    if not results or not results.get('results'):
        markup = InlineKeyboardMarkup()
        markup.add(get_dev_button())
        bot.send_message(message.chat.id, "❌ لم يتم العثور على نتائج.", reply_markup=markup)
        return

    markup = InlineKeyboardMarkup(row_width=1)
    for result in results['results']:
        title = result['title']
        link = result['link']
        link_key = get_key(link)
        btn_text = f"{title} ({result['year']}, {result['quality']}, التقييم: {result['rating']})"
        callback_data = f"select:{link_key}:1:{query_key}"
        markup.add(InlineKeyboardButton(btn_text, callback_data=callback_data))

    if len(results['results']) == 10:
        markup.add(InlineKeyboardButton("➡️ الصفحة التالية", callback_data=f"next:2:{query_key}"))

    markup.add(get_dev_button())
    bot.send_message(message.chat.id, f"🔍 نتائج البحث عن '{query}':", reply_markup=markup)

# Handle callbacks
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    data = call.data.split(':')
    action = data[0]

    if action == 'select':
        link_key = data[1]
        page = data[2]
        query_key = data[3]
        link = data_map.get(link_key)
        query = data_map.get(query_key)
        if not link:
            bot.answer_callback_query(call.id, "خطأ: الرابط غير موجود.")
            return
        details = get_item_details(link)
        if not details:
            bot.answer_callback_query(call.id, "خطأ في جلب التفاصيل.")
            return

        caption = f"🎬 {details.get('title', '')}\n\n{details.get('story', '')}"
        photo_sent = False
        if 'image' in details:
            try:
                bot.send_photo(call.message.chat.id, details['image'], caption=caption[:1024])
                photo_sent = True
            except:
                pass

        info_items = []
        if 'badge' in details:
            info_items.append(f"🏷️ {details['badge']}")
        if 'rating' in details:
            info_items.append(f"⭐ التقييم: {details['rating']}")
        if 'language' in details:
            info_items.append(details['language'])
        if 'quality' in details:
            info_items.append(details['quality'])
        if 'production' in details:
            info_items.append(details['production'])
        if 'year' in details:
            info_items.append(details['year'])
        if 'duration' in details:
            info_items.append(details['duration'])
        if 'genre' in details:
            genres_text = ', '.join(details['genre'])
            info_items.append(f"🎭 النوع: {genres_text}")

        markup = InlineKeyboardMarkup(row_width=2)

        for i in range(0, len(info_items), 2):
            row = []
            for j in range(i, min(i+2, len(info_items))):
                row.append(InlineKeyboardButton(info_items[j], callback_data="noop"))
            markup.row(*row)

        if 'episodes' in details:
            for ep in details['episodes']:
                ep_title = ep['title']
                ep_link = ep['link']
                ep_key = get_key(ep_link)
                callback_data = f"epselect:{ep_key}"
                markup.add(InlineKeyboardButton(ep_title, callback_data=callback_data))
            
            if photo_sent:
                bot.send_message(call.message.chat.id, "📋 الحلقات المتاحة:", reply_markup=markup)
            else:
                bot.send_message(call.message.chat.id, f"📋 {details.get('title', 'الحلقات')}:", reply_markup=markup)
        else:
            if 'links' in details:
                for quality, links_list in details['links'].items():
                    for link_item in links_list:
                        size = link_item.get('size', '')
                        if 'video_direct' in link_item:
                            direct_url = link_item['video_direct']
                            file_name = f"{details.get('title', 'video')}_{quality}.mp4"
                            direct_key = get_key({'url': direct_url, 'file_name': file_name})
                            markup.add(InlineKeyboardButton(f"⬇️ تحميل مباشر {quality} ({size})", url=direct_url))
                            markup.add(InlineKeyboardButton(f"📤 إرسال إلى الدردشة {quality} ({size})", callback_data=f"stream:{direct_key}"))
                        if 'embed_link' in link_item:
                            embed_url = link_item['embed_link']
                            markup.add(InlineKeyboardButton(f"▶️ مشاهدة اونلاين {quality} ({size})", url=embed_url))
            
            bot.send_message(call.message.chat.id, "🎬 روابط الفيلم:", reply_markup=markup)

        back_markup = InlineKeyboardMarkup()
        back_markup.add(InlineKeyboardButton("🔙 العودة إلى البحث", callback_data=f"search:{page}:{query_key}"))
        back_markup.add(get_dev_button())
        bot.send_message(call.message.chat.id, "إجراءات:", reply_markup=back_markup)

    elif action == 'epselect':
        ep_key = data[1]
        ep_link = data_map.get(ep_key)
        if not ep_link:
            bot.answer_callback_query(call.id, "خطأ: رابط الحلقة غير موجود.")
            return
        ep_details = get_episode_links(ep_link)
        if not ep_details:
            bot.answer_callback_query(call.id, "خطأ في جلب الحلقة.")
            return

        caption = ep_details.get('title', '')
        photo_sent = False
        if 'image' in ep_details:
            try:
                bot.send_photo(call.message.chat.id, ep_details['image'], caption=caption)
                photo_sent = True
            except:
                pass

        info_items = []
        if 'rating' in ep_details:
            info_items.append(f"⭐ التقييم: {ep_details['rating']}")
        if 'language' in ep_details:
            info_items.append(ep_details['language'])
        if 'quality' in ep_details:
            info_items.append(ep_details['quality'])
        if 'production' in ep_details:
            info_items.append(ep_details['production'])
        if 'year' in ep_details:
            info_items.append(ep_details['year'])
        if 'duration' in ep_details:
            info_items.append(ep_details['duration'])
        if 'categories' in ep_details:
            info_items.append(f"🎭 النوع: {', '.join(ep_details['categories'])}")

        markup = InlineKeyboardMarkup(row_width=2)

        for i in range(0, len(info_items), 2):
            row = []
            for j in range(i, min(i+2, len(info_items))):
                row.append(InlineKeyboardButton(info_items[j], callback_data="noop"))
            markup.row(*row)

        if 'links' in ep_details:
            for quality, links_list in ep_details['links'].items():
                for link_item in links_list:
                    size = link_item.get('size', '')
                    if 'videos' in link_item:
                        for vid in link_item['videos']:
                            v_size = vid['size']
                            v_url = vid['url']
                            v_embed = vid['embed']
                            file_name = f"{ep_details.get('title', 'episode')}_{v_size}.mp4"
                            direct_key = get_key({'url': v_url, 'file_name': file_name})
                            markup.add(InlineKeyboardButton(f"⬇️ تحميل مباشر {v_size}p ({size})", url=v_url))
                            markup.add(InlineKeyboardButton(f"📤 إرسال إلى الدردشة {v_size}p ({size})", callback_data=f"stream:{direct_key}"))
                            markup.add(InlineKeyboardButton(f"▶️ مشاهدة اونلاين {v_size}p ({size})", url=v_embed))

        markup.add(get_dev_button())
        
        episode_title = ep_details.get('title', 'الحلقة')
        bot.send_message(call.message.chat.id, f"📺 {episode_title}", reply_markup=markup)

    elif action in ('next', 'prev'):
        page = int(data[1])
        query_key = data[2]
        query = data_map.get(query_key)
        if not query:
            bot.answer_callback_query(call.id, "خطأ: الاستعلام غير موجود.")
            return
        results = search_api(query, page)
        if not results or not results.get('results'):
            bot.answer_callback_query(call.id, "لا توجد نتائج إضافية.")
            return

        markup = InlineKeyboardMarkup(row_width=1)
        for result in results['results']:
            title = result['title']
            link = result['link']
            link_key = get_key(link)
            btn_text = f"{title} ({result['year']}, {result['quality']}, التقييم: {result['rating']})"
            callback_data = f"select:{link_key}:{page}:{query_key}"
            markup.add(InlineKeyboardButton(btn_text, callback_data=callback_data))

        row = []
        if page > 1:
            row.append(InlineKeyboardButton("⬅️ الصفحة السابقة", callback_data=f"prev:{page-1}:{query_key}"))
        if len(results['results']) == 10:
            row.append(InlineKeyboardButton("➡️ الصفحة التالية", callback_data=f"next:{page+1}:{query_key}"))
        if row:
            markup.row(*row)

        markup.add(get_dev_button())
        bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=markup)

    elif action == 'search':
        page = int(data[1])
        query_key = data[2]
        query = data_map.get(query_key)
        if not query:
            bot.answer_callback_query(call.id, "خطأ: الاستعلام غير موجود.")
            return
        results = search_api(query, page)
        if not results or not results.get('results'):
            bot.answer_callback_query(call.id, "لا توجد نتائج إضافية.")
            return

        markup = InlineKeyboardMarkup(row_width=1)
        for result in results['results']:
            title = result['title']
            link = result['link']
            link_key = get_key(link)
            btn_text = f"{title} ({result['year']}, {result['quality']}, التقييم: {result['rating']})"
            callback_data = f"select:{link_key}:{page}:{query_key}"
            markup.add(InlineKeyboardButton(btn_text, callback_data=callback_data))

        row = []
        if page > 1:
            row.append(InlineKeyboardButton("⬅️ الصفحة السابقة", callback_data=f"prev:{page-1}:{query_key}"))
        if len(results['results']) == 10:
            row.append(InlineKeyboardButton("➡️ الصفحة التالية", callback_data=f"next:{page+1}:{query_key}"))
        if row:
            markup.row(*row)

        markup.add(get_dev_button())
        bot.edit_message_text(f"🔍 نتائج البحث عن '{query}':", call.message.chat.id, call.message.message_id, reply_markup=markup)

    elif action == 'stream':
        direct_key = data[1]
        direct_data = data_map.get(direct_key)
        if not direct_data:
            bot.answer_callback_query(call.id, "خطأ: رابط الفيديو غير موجود.")
            return
        file_url = direct_data['url']
        file_name = direct_data['file_name']
        bot.answer_callback_query(call.id, "جاري بدء عملية البث...")
        asyncio.run_coroutine_threadsafe(stream_video(call.message.chat.id, file_url, file_name), loop)

    elif action == 'noop':
        pass

    bot.answer_callback_query(call.id)

# Run both bots
if __name__ == "__main__":
    print("🤖 Bot started...")
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(pyro_bot.start())
        bot.infinity_polling()
    finally:
        loop.run_until_complete(pyro_bot.stop())
        loop.close()
