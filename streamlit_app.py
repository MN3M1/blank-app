import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import requests
import json
import aiohttp
import asyncio
from io import BytesIO
from datetime import datetime
import os

# Replace with your Telegram bot token
BOT_TOKEN = "8498331387:AAG8kflbjMHZChqvo3fkOfZmmSR1cvBJUJY"
bot = telebot.TeleBot(BOT_TOKEN)

API_BASE = 'https://api.x7m.site/akwam/'

data_map = {}
map_counter = 0

def get_key(value):
    global map_counter
    key = str(map_counter)
    data_map[key] = value
    map_counter += 1
    return key

async def stream_video_to_chat(chat_id, video_url, file_name="video.mp4"):
    """
    Downloads and streams a video directly to the chat without saving to disk
    """
    try:
        # Send initial status message
        progress_msg = bot.send_message(
            chat_id=chat_id,
            text="🔄 **جاري التحميل...**\n\n⏳ يرجى الانتظار بينما نجلب الفيديو."
        )

        # Use aiohttp for asynchronous streaming download
        timeout = aiohttp.ClientTimeout(total=300)  # 5 minute timeout
        async with aiohttp.ClientSession(timeout=timeout) as session:
            # Get file info first
            async with session.head(video_url, ssl=False) as head_resp:
                if head_resp.status != 200:
                    bot.edit_message_text(
                        f"❌ فشل في الوصول للملف. رمز الحالة: {head_resp.status}",
                        chat_id, progress_msg.message_id
                    )
                    return
                
                file_size = int(head_resp.headers.get('content-length', 0))
                
                # Update progress with file info
                size_mb = file_size / (1024 * 1024) if file_size > 0 else 0
                bot.edit_message_text(
                    f"📥 **جاري التحميل: {file_name}**\n"
                    f"📊 الحجم: {size_mb:.1f} ميجابايت\n\n"
                    f"🔄 التقدم: 0% (بدء التحميل...)\n"
                    f"⏱️ الحالة: جاري التحميل...",
                    chat_id, progress_msg.message_id
                )

            # Now download with progress
            async with session.get(video_url, ssl=False) as resp:
                if resp.status == 200:
                    video_content = BytesIO()
                    downloaded = 0
                    chunk_size = 8192  # 8KB chunks
                    last_update = datetime.now()
                    
                    # Download in chunks with progress updates
                    async for chunk in resp.content.iter_chunked(chunk_size):
                        video_content.write(chunk)
                        downloaded += len(chunk)
                        
                        # Update progress every 3 seconds
                        now = datetime.now()
                        if (now - last_update).total_seconds() >= 3:
                            if file_size > 0:
                                progress = (downloaded / file_size) * 100
                                progress_bar = "█" * int(progress // 5) + "░" * (20 - int(progress // 5))
                                bot.edit_message_text(
                                    f"📥 **جاري التحميل: {file_name}**\n"
                                    f"📊 الحجم: {size_mb:.1f} ميجابايت\n\n"
                                    f"🔄 التقدم: {progress:.1f}%\n"
                                    f"[{progress_bar}]\n"
                                    f"⏱️ تم تحميل: {downloaded/(1024*1024):.1f} ميجابايت",
                                    chat_id, progress_msg.message_id
                                )
                            last_update = now
                    
                    # Prepare for upload
                    bot.edit_message_text(
                        f"📤 **جاري الرفع إلى تليجرام...**\n"
                        f"📊 الملف: {file_name}\n"
                        f"✅ اكتمل التحميل: {size_mb:.1f} ميجابايت\n\n"
                        f"🔄 الحالة: جاري الرفع إلى تليجرام...",
                        chat_id, progress_msg.message_id
                    )
                    
                    # Prepare file for upload
                    video_content.seek(0)
                    video_content.name = file_name
                    
                    # Send the video
                    bot.send_video(
                        chat_id=chat_id,
                        video=video_content,
                        caption=f"🎬 **{file_name}**\n📊 الحجم: {size_mb:.1f} ميجابايت\n✅ تم الإرسال بنجاح!"
                    )
                    
                    # Success message
                    bot.edit_message_text(
                        f"✅ **اكتمل الرفع!**\n"
                        f"📺 الملف: {file_name}\n"
                        f"📊 الحجم: {size_mb:.1f} ميجابايت\n"
                        f"🎉 تم إرسال الفيديو بنجاح!",
                        chat_id, progress_msg.message_id
                    )
                    
                else:
                    bot.edit_message_text(
                        f"❌ فشل في تحميل الملف. رمز الحالة: {resp.status}",
                        chat_id, progress_msg.message_id
                    )
                    
    except asyncio.TimeoutError:
        bot.send_message(chat_id, "❌ **خطأ في المهلة الزمنية**\n\nاستغرق التحميل وقتاً طويلاً. يرجى المحاولة مع ملف أصغر.")
    except Exception as e:
        error_msg = str(e)
        if "SSL" in error_msg:
            bot.send_message(chat_id, "❌ **خطأ في شهادة SSL**\n\nلا يمكن التحقق من شهادة الخادم.")
        elif "DNS" in error_msg or "resolve" in error_msg:
            bot.send_message(chat_id, "❌ **خطأ في الاتصال**\n\nلا يمكن الاتصال بالخادم. يرجى التحقق من الرابط والمحاولة مرة أخرى.")
        else:
            bot.send_message(chat_id, f"❌ **حدث خطأ:**\n\n`{error_msg}`\n\nيرجى المحاولة مرة أخرى.")

def get_dev_button():
    return InlineKeyboardButton("👨‍💻 المطور @M_N_3_M", url="https://t.me/M_N_3_M")

def search_api(query, page=1):
    url = f"{API_BASE}?q={query}&page={page}"
    try:
        response = requests.get(url)
        return response.json() if response.status_code == 200 else None
    except:
        return None

def get_item_details(link):
    url = f"{API_BASE}?link={link}"
    try:
        response = requests.get(url)
        return response.json() if response.status_code == 200 else None
    except:
        return None

def get_episode_links(ep_link):
    url = f"{API_BASE}?ep={ep_link}"
    try:
        response = requests.get(url)
        return response.json() if response.status_code == 200 else None
    except:
        return None

@bot.message_handler(commands=['start'])
def start(message):
    markup = InlineKeyboardMarkup()
    markup.add(get_dev_button())
    bot.send_message(message.chat.id, "🎬 مرحباً! أرسل اسم فيلم أو مسلسل للبحث.", reply_markup=markup)

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

    # Pagination if more pages
    if len(results['results']) == 10:  # Assuming 10 per page
        markup.add(InlineKeyboardButton("➡️ الصفحة التالية", callback_data=f"next:2:{query_key}"))

    markup.add(get_dev_button())
    bot.send_message(message.chat.id, f"🔍 نتائج البحث عن '{query}':", reply_markup=markup)

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

        # Send photo with story as caption if possible
        caption = f"🎬 {details.get('title', '')}\n\n{details.get('story', '')}"
        photo_sent = False
        if 'image' in details:
            try:
                bot.send_photo(call.message.chat.id, details['image'], caption=caption[:1024])  # Truncate if too long
                photo_sent = True
            except:
                # If photo fails, continue without it
                pass

        # Prepare info buttons
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

        # Add info buttons
        for i in range(0, len(info_items), 2):
            row = []
            for j in range(i, min(i+2, len(info_items))):
                row.append(InlineKeyboardButton(info_items[j], callback_data="noop"))
            markup.row(*row)

        if 'episodes' in details:  # It's a series season
            for ep in details['episodes']:
                ep_title = ep['title']
                ep_link = ep['link']
                ep_key = get_key(ep_link)
                callback_data = f"epselect:{ep_key}"
                markup.add(InlineKeyboardButton(ep_title, callback_data=callback_data))
            
            if photo_sent:
                # If photo was sent, send episodes list with proper text
                bot.send_message(call.message.chat.id, "📋 الحلقات المتاحة:", reply_markup=markup)
            else:
                # If no photo, send title with episodes
                bot.send_message(call.message.chat.id, f"📋 {details.get('title', 'الحلقات')}:", reply_markup=markup)
        else:  # It's a movie
            if 'links' in details:
                for quality, links_list in details['links'].items():
                    for link_item in links_list:
                        size = link_item.get('size', '')
                        # Add direct video if available
                        if 'video_direct' in link_item:
                            direct_url = link_item['video_direct']
                            markup.add(InlineKeyboardButton(f"⬇️ تحميل مباشر {quality} ({size})", url=direct_url))
                            direct_key = get_key(direct_url)
                            markup.add(InlineKeyboardButton(f"📤 إرسال في الدردشة {quality} ({size})", callback_data=f"stream:{direct_key}:{quality}:{size}"))
                        # Add embed if available
                        if 'embed_link' in link_item:
                            embed_url = link_item['embed_link']
                            markup.add(InlineKeyboardButton(f"▶️ مشاهدة اونلاين {quality} ({size})", url=embed_url))
            
            bot.send_message(call.message.chat.id, "🎬 روابط الفيلم:", reply_markup=markup)

        # Add back to search results if needed
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

        # Send photo for episode
        caption = ep_details.get('title', '')
        photo_sent = False
        if 'image' in ep_details:
            try:
                bot.send_photo(call.message.chat.id, ep_details['image'], caption=caption)
                photo_sent = True
            except:
                # If photo fails, continue without it
                pass

        # Prepare info buttons for episode
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

        # Add info buttons
        for i in range(0, len(info_items), 2):
            row = []
            for j in range(i, min(i+2, len(info_items))):
                row.append(InlineKeyboardButton(info_items[j], callback_data="noop"))
            markup.row(*row)

        if 'links' in ep_details:
            for quality, links_list in ep_details['links'].items():
                for link_item in links_list:
                    size = link_item.get('size', '')
                    # For episodes, check videos
                    if 'videos' in link_item:
                        for vid in link_item['videos']:
                            v_size = vid['size']
                            v_url = vid['url']
                            v_embed = vid['embed']
                            markup.add(InlineKeyboardButton(f"⬇️ تحميل مباشر {v_size}p ({size})", url=v_url))
                            vid_key = get_key(v_url)
                            markup.add(InlineKeyboardButton(f"📤 إرسال في الدردشة {v_size}p ({size})", callback_data=f"stream:{vid_key}:{v_size}p:{size}"))
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

        # Pagination buttons
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

        # Pagination buttons
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
        url_key = data[1]
        quality = data[2]
        size = data[3]
        video_url = data_map.get(url_key)
        
        if not video_url:
            bot.answer_callback_query(call.id, "خطأ: الرابط غير موجود.")
            return
            
        bot.answer_callback_query(call.id, "🔄 بدء تحميل الفيديو...")
        
        # Create a filename based on quality and size
        file_name = f"video_{quality}_{size}.mp4"
        
        # Run the streaming function in a separate thread to avoid blocking
        import threading
        def run_stream():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(stream_video_to_chat(call.message.chat.id, video_url, file_name))
            loop.close()
        
        thread = threading.Thread(target=run_stream)
        thread.start()

    elif action == 'noop':
        pass  # Do nothing

    bot.answer_callback_query(call.id)

if __name__ == "__main__":
    print("🤖 Bot started...")
    bot.infinity_polling()
