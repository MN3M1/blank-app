import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import requests
import json
import aiohttp
from pyrogram.client import Client
from pyrogram import filters
from pyrogram.types import Message
import os
import asyncio
from datetime import datetime
from io import BytesIO
import threading

# Replace with your Telegram bot token
BOT_TOKEN = "6191519380:AAGk0Pg8CivZxe5uZeGWBtjnseeYHV2lnEc"

# Replace with your actual API credentials from my.telegram.org
API_ID = 20569963
API_HASH = "37f536fd550fa5dd70cdaaca39c2b1d7"

# Initialize TeleBot for main Akwam functionality
bot = telebot.TeleBot(BOT_TOKEN)

# Initialize Pyrogram client for streaming functionality
pyrogram_client = Client(
    "akwam_streaming_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

API_BASE = 'https://api.x7m.site/akwam/'

data_map = {}
map_counter = 0

# Track users waiting for download link
download_waiting_users = set()

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

# Async function to download and upload video using a fresh Pyrogram client
async def download_with_new_client(client, chat_id, file_url):
    """
    Downloads and uploads a video from a direct URL with progress monitoring.
    """
    # Start the client first
    await client.start()
    
    # Send initial status message
    progress_msg = await client.send_message(
        chat_id=chat_id,
        text="🔄 **جاري الاتصال بالخادم...**\n\n⏳ يرجى الانتظار أثناء جلب الفيديو."
    )

    try:
        # Use aiohttp for asynchronous streaming download
        timeout = aiohttp.ClientTimeout(total=300)  # 5 minute timeout
        async with aiohttp.ClientSession(timeout=timeout) as session:
            # Get file info first
            async with session.head(file_url, ssl=False) as head_resp:
                if head_resp.status != 200:
                    await progress_msg.edit_text(f"❌ فشل في الوصول للملف. رمز الحالة: {head_resp.status}")
                    return
                
                file_size = int(head_resp.headers.get('content-length', 0))
                file_name = os.path.basename(file_url) or "video.mp4"
                
                # Update progress with file info
                size_mb = file_size / (1024 * 1024) if file_size > 0 else 0
                await progress_msg.edit_text(
                    f"📥 **جاري التحميل: {file_name}**\n"
                    f"📊 الحجم: {size_mb:.1f} ميجابايت\n\n"
                    f"🔄 التقدم: 0% (بدء التحميل...)\n"
                    f"⏱️ الحالة: جاري التحميل..."
                )

            # Now download with progress
            async with session.get(file_url, ssl=False) as resp:
                if resp.status == 200:
                    video_content = BytesIO()
                    downloaded = 0
                    chunk_size = 8192  # 8KB chunks
                    last_update = datetime.now()
                    last_message_content = ""  # Track last message content
                    
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
                                
                                # Create progress message
                                progress_text = (
                                    f"📥 **جاري التحميل: {file_name}**\n"
                                    f"📊 الحجم: {size_mb:.1f} ميجابايت\n\n"
                                    f"🔄 التقدم: {progress:.1f}%\n"
                                    f"[{progress_bar}]\n"
                                    f"⏱️ تم تحميل: {downloaded/(1024*1024):.1f} ميجابايت"
                                )
                                
                                # Only update if content changed
                                if progress_text != last_message_content:
                                    try:
                                        await progress_msg.edit_text(progress_text)
                                        last_message_content = progress_text
                                        last_update = now
                                    except Exception as e:
                                        # Ignore message edit errors (like MESSAGE_NOT_MODIFIED)
                                        if "MESSAGE_NOT_MODIFIED" not in str(e):
                                            print(f"Progress update error: {e}")
                                        pass
                    
                    # Prepare for upload  
                    upload_text = (
                        f"📤 **جاري الرفع إلى تليجرام...**\n"
                        f"📊 الملف: {file_name}\n"
                        f"✅ اكتمل التحميل: {size_mb:.1f} ميجابايت\n\n"
                        f"🔄 الحالة: جاري الرفع إلى تليجرام..."
                    )
                    
                    try:
                        await progress_msg.edit_text(upload_text)
                    except Exception as e:
                        if "MESSAGE_NOT_MODIFIED" not in str(e):
                            print(f"Upload message error: {e}")
                    
                    # Prepare file for upload
                    video_content.seek(0)
                    video_content.name = file_name
                    
                    # Upload with progress callback
                    def progress_callback(current, total):
                        pass
                    
                    # Send the video
                    await client.send_video(
                        chat_id=chat_id,
                        video=video_content,
                        caption=f"🎬 **{file_name}**\n📊 الحجم: {size_mb:.1f} ميجابايت\n✅ تم الرفع بنجاح!",
                        file_name=file_name,
                        progress=progress_callback
                    )
                    
                    # Success message
                    success_text = (
                        f"✅ **اكتمل الرفع!**\n"
                        f"📺 الملف: {file_name}\n"
                        f"📊 الحجم: {size_mb:.1f} ميجابايت\n"
                        f"🎉 تم رفع الفيديو بنجاح!"
                    )
                    
                    try:
                        await progress_msg.edit_text(success_text)
                    except Exception as e:
                        if "MESSAGE_NOT_MODIFIED" not in str(e):
                            print(f"Success message error: {e}")
                    
                else:
                    error_text = f"❌ فشل في تحميل الملف. رمز الحالة: {resp.status}"
                    try:
                        await progress_msg.edit_text(error_text)
                    except Exception as e:
                        if "MESSAGE_NOT_MODIFIED" not in str(e):
                            print(f"Error message update failed: {e}")
                    
    except asyncio.TimeoutError:
        await progress_msg.edit_text("❌ **انتهت مهلة الاتصال**\n\nاستغرق التحميل وقتاً طويلاً جداً. يرجى المحاولة بملف أصغر أو فحص اتصال الإنترنت.")
    except Exception as e:
        error_msg = str(e)
        if "SSL" in error_msg:
            await progress_msg.edit_text("❌ **خطأ في شهادة الأمان**\n\nلا يمكن التحقق من شهادة الخادم. قد تكون هناك مشكلة أمنية مع مضيف الفيديو.")
        elif "DNS" in error_msg or "resolve" in error_msg:
            await progress_msg.edit_text("❌ **خطأ في الاتصال**\n\nلا يمكن الاتصال بالخادم. يرجى فحص الرابط والمحاولة مرة أخرى.")
        else:
            await progress_msg.edit_text(f"❌ **حدث خطأ:**\n\n`{error_msg}`\n\nيرجى المحاولة مرة أخرى أو التواصل مع الدعم الفني.")

# Start command for TeleBot
@bot.message_handler(commands=['start'])
def start(message):
    markup = InlineKeyboardMarkup()
    markup.add(get_dev_button())
    bot.send_message(message.chat.id, "🎬 مرحباً! أرسل اسم فيلم أو مسلسل للبحث.\n\n💡 يمكنك أيضاً استخدام الأمر /download لتحميل الفيديو.", reply_markup=markup)

# Download command for TeleBot
@bot.message_handler(commands=['download'])
def download_command(message):
    user_id = message.from_user.id
    download_waiting_users.add(user_id)
    markup = InlineKeyboardMarkup()
    markup.add(get_dev_button())
    bot.send_message(message.chat.id, "🔗 أرسل الرابط المباشر للفيديو الذي تريد تحميله:", reply_markup=markup)

# Handle text messages (search or download link)
@bot.message_handler(func=lambda message: not message.text.startswith('/'))
def handle_text(message):
    user_id = message.from_user.id
    text = message.text.strip()
    
    # Check if user is waiting for download link
    if user_id in download_waiting_users:
        # Remove user from waiting list
        download_waiting_users.discard(user_id)
        
        # Validate URL
        if not text.startswith(("http://", "https://")):
            markup = InlineKeyboardMarkup()
            markup.add(get_dev_button())
            bot.send_message(message.chat.id, "❌ الرابط المدرج غير صحيح. يرجى إدراج رابط كامل يبدأ بـ http أو https", reply_markup=markup)
            return
        
        # Start download process
        bot.send_message(message.chat.id, "🔄 جاري بدء عملية التحميل...")
        
        # Use a simple approach - run pyrogram download in new loop
        def start_download():
            try:
                # Create a new event loop for this download
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                # Create a new Pyrogram client with unique session name
                import time
                import random
                unique_id = f"download_{message.chat.id}_{int(time.time())}_{random.randint(1000,9999)}"
                download_client = Client(
                    unique_id,
                    api_id=API_ID,
                    api_hash=API_HASH,
                    bot_token=BOT_TOKEN
                )
                
                # Run the download
                loop.run_until_complete(download_with_new_client(download_client, message.chat.id, text))
                
                # Clean up
                try:
                    loop.run_until_complete(download_client.stop())
                except:
                    pass
                loop.close()
                
            except Exception as e:
                print(f"Error in download: {e}")
                bot.send_message(message.chat.id, f"❌ خطأ في التحميل: {str(e)}")
        
        download_thread = threading.Thread(target=start_download)
        download_thread.start()
        return
    
    # Regular search functionality
    query = text
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

    elif action == 'noop':
        pass  # Do nothing

    bot.answer_callback_query(call.id)

# Function to run both bots
async def start_pyrogram():
    await pyrogram_client.start()

def run_both_bots():
    print("🤖 بدء تشغيل البوت...")
    
    # Start Pyrogram client in a separate thread
    def start_pyrogram_client():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(start_pyrogram())
        loop.run_forever()
    
    pyrogram_thread = threading.Thread(target=start_pyrogram_client)
    pyrogram_thread.daemon = True
    pyrogram_thread.start()
    
    print("✅ تم تشغيل عميل Pyrogram")
    print("✅ بدء تشغيل TeleBot...")
    
    # Start telebot polling
    bot.infinity_polling()

# Run the bot
if __name__ == "__main__":
    run_both_bots()
