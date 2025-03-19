import sqlite3
import random
import time
from telegram import Update, Message, InputFile, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, CallbackQueryHandler
from PIL import Image, ImageDraw, ImageFont
import logging
import requests
import io
import aiosqlite

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DATABASE = 'users.db'
PROFILE_DATABASE = 'profile_inf.db'

def create_user_tables():
    """Создает необходимые таблицы в базе данных."""
    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS allowed_users (
                id INTEGER PRIMARY KEY
            )
        ''')
        conn.commit()

    with sqlite3.connect(PROFILE_DATABASE) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS profile (
                user_id INTEGER PRIMARY KEY,
                username TEXT DEFAULT NONE,
                code INTEGER DEFAULT 0,
                coffe INTEGER DEFAULT 5,
                reputation INTEGER DEFAULT 0,
                theme TEXT DEFAULT 'black'
            )
        ''')
        conn.commit()
    with sqlite3.connect('coding.db') as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS coding (
                usid INTEGER PRIMARY KEY,
                last_time INTEGER DEFAULT 0,
                user_name TEXT DEFAULT NULL,
                chance INTEGER DEFAULT 5,
                count INTEGER DEFAULT 1,
                count2 INTEGER DEFAULT 5,
                chance_fail INTEGER DEFAULT 25
            )
        ''')
        conn.commit()

async def get_count(user_id):
    async with aiosqlite.connect('coding.db') as connection:
        async with connection.execute('SELECT count FROM coding WHERE usid = ?', (user_id,)) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0

async def get_count2(user_id):
    async with aiosqlite.connect('coding.db') as connection:
        async with connection.execute('SELECT count2 FROM coding WHERE usid = ?', (user_id,)) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0

async def get_last_time(user_id):
    async with aiosqlite.connect('coding.db') as connection:
        async with connection.execute('SELECT last_time FROM coding WHERE usid = ?', (user_id,)) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0  # Return None for no entry instead of 0

async def get_code(user_id):
    async with aiosqlite.connect('profile_inf.db') as connection:
        async with connection.execute('SELECT code FROM profile WHERE user_id = ?', (user_id,)) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0  # Return None for no entry instead of 0

async def get_chance_fail(user_id):
    async with aiosqlite.connect('coding.db') as connection:
        async with connection.execute('SELECT chance_fail FROM coding WHERE usid = ?', (user_id,)) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0
            
async def get_chance(user_id):
    async with aiosqlite.connect('coding.db') as connection:
        async with connection.execute('SELECT chance FROM coding WHERE usid = ?', (user_id,)) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0
            
async def get_rep(user_id):
    async with aiosqlite.connect('profile_inf.db') as connection:
        async with connection.execute('SELECT reputation FROM profile WHERE user_id = ?', (user_id,)) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0
          
async def get_coffe(user_id):
    async with aiosqlite.connect('profile_inf.db') as connection:
        async with connection.execute('SELECT coffe FROM profile WHERE user_id = ?', (user_id,)) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0

async def new_code(user_id, amount):
    async with aiosqlite.connect('profile_inf.db') as connection:
        async with connection.execute('''
            UPDATE profile
            SET code = code + ?
            WHERE user_id = ?
        ''', (amount, user_id)):
            await connection.commit()
            
async def new_codes(user_id, amount):
    async with aiosqlite.connect('profile_inf.db') as connection:
        async with connection.execute('''
            UPDATE profile
            SET code = code - ?
            WHERE user_id = ?
        ''', (amount, user_id)):
            await connection.commit()
            
async def drink_coffe(user_id):
    async with aiosqlite.connect('profile_inf.db') as connection:
        async with connection.execute('''
            UPDATE profile
            SET coffe = coffe - 1
            WHERE user_id = ?
        ''', (user_id,)):
            await connection.commit()
            
async def update_coffe(user_id, new_coffe):  # добавьте `amount` здесь
       async with aiosqlite.connect('profile_inf.db') as connection:
           async with connection.execute('''
               UPDATE profile
               SET coffe = ?
               WHERE user_id = ?
           ''', (new_coffe, user_id,)):
               await connection.commit()

async def update_last_time(user_id, last_time):
    async with aiosqlite.connect('coding.db') as connection:
        async with connection.execute('''
            UPDATE coding
            SET last_time = ?
            WHERE usid = ?
        ''', (last_time, user_id)):
            await connection.commit()
            
async def update_rep(user_id, new_rep):
    async with aiosqlite.connect('profile_inf.db') as connection:
        await connection.execute('''
            UPDATE profile
            SET reputation = ?
            WHERE user_id = ?
        ''', (new_rep, user_id))
        await connection.commit()

async def coding(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    fail_chance = await get_chance_fail(user_id)
    chance = await get_chance(user_id)
    count = await get_count(user_id)
    count2 = await get_count2(user_id)
    last_time = await get_last_time(user_id)
    coffe = await get_coffe(user_id)
    reputation = await get_rep(user_id)  # reputation не используется в коде
    
    current_time = int(time.time())
    
    if current_time - last_time > 300:  # 5 минут
        if coffe > 0:
            amount = random.randint(count, count2)  # инициализация amount

            # Определяем бонус
            bonus = random.choices(['chance', "nothing", "fail"], 
                                   weights=[chance, 100 - chance - fail_chance, fail_chance])[0]

            if bonus == "nothing":
                await new_code(user_id, amount)
                await drink_coffe(user_id)
                await update_last_time(user_id, current_time)  # Обновляем время последнего получения
                await update.message.reply_text(
                    f'Вы написали {amount} строк! Всего написано: {await get_code(user_id)} строк кода.'
                )
                
            elif bonus == "chance":
                amount *= 2  # Удваиваем amount для бонуса
                await new_code(user_id, amount)
                await drink_coffe(user_id)
                await update_last_time(user_id, current_time)  # Обновляем время последнего получения
                await update.message.reply_text(
                    f'Вы получили бонус x2 от {amount // 2} ({amount} строк) Всего строк написано: {await get_code(user_id)} строк.'
                )
            else:  # bonus == "fail"
                await drink_coffe(user_id)
                await update_last_time(user_id, current_time)
                await update.message.reply_text("Увы, у вас был неудачный день, и вы забыли сохраниться, ваш код пропал.")
                
        else:
            await update.message.reply_text("Недостаточно кофе.")
            
    else:
        remaining_time = 300 - (current_time - last_time)
        await update.message.reply_text(
            f'Вы можете получить деньги через {int(remaining_time / 60)} минут, {remaining_time % 60} секунд.'
        )
     
async def turn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if len(context.args) != 1:
        await update.message.reply_text("Использование: /turn <количество>")
        return

    try:
        amount = int(context.args[0])
    except ValueError:
        await update.message.reply_text("Пожалуйста, укажите корректное число для обмена.")
        return
    
    # Получаем текущее количество кода и репутации
    current_code = await get_code(user_id)
    current_rep = await get_rep(user_id)
    
    if amount <= 0:
        await update.message.reply_text("Количество для обмена должно быть положительным.")
        return
    
    if amount > current_code:
        await update.message.reply_text("Недостаточно кода для обмена.")
        return

    # Выполняем обмен: уменьшаем количество кода и увеличиваем репутацию
    new_rep = current_rep + (amount * 10)

    # Обновляем данные в базе
    await new_codes(user_id, amount)
    await update_rep(user_id, new_rep)  # Передаем новое значение репутации

    await update.message.reply_text(f"Вы обменяли {amount} код на {amount * 10} репутацию.")
    
async def shop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Открываем изображение магазина
    background = Image.open("shop.png")
    # Создаем байтовый поток для хранения изображения
    img_byte_arr = io.BytesIO()
    background.save(img_byte_arr, format='PNG')
    img_byte_arr.seek(0)  # Сбрасываем указатель в начало

    # Создаем кнопку
    keyboard = [
        [InlineKeyboardButton("купить 10 кофе за 100 монет", callback_data='spend_100_rep')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Отправляем изображение и кнопку пользователю
    await update.message.reply_photo(photo=InputFile(img_byte_arr, filename='shop.png'), reply_markup=reply_markup)

# Обработка нажатий на кнопки
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    amount = 10
    query = update.callback_query
    await query.answer()  # Отвечаем на запрос, чтобы убрать "крутилку"

    user_id = query.from_user.id
    current_rep = await get_rep(user_id)  # Получаем текущую репутацию
    current_coffe = await get_coffe(user_id)  # Получаем текущее количество кофе

    if query.data == 'spend_100_rep':
        if current_rep >= 100:
            new_rep = current_rep - 100
            new_coffe = current_coffe + amount
            await update_coffe(user_id, new_coffe)  # Обновляем количество кофе
            await update_rep(user_id, new_rep)  # Обновляем репутацию
            await query.edit_message_text(text="Вы успешно потратили 100 репутации!")
        else:
            await query.edit_message_text(text="Недостаточно репутации для траты!")
    
async def theme(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) != 1:
        await update.message.reply_text('Используйте: /theme black/white')
        return

    # Получаем аргумент темы и переводим его в нижний регистр
    new_theme = context.args[0].lower()

    if new_theme not in ["black", "white"]:
        await update.message.reply_text("Выберите существующую тему: 'black' или 'white'")
        return

    user_id = update.message.from_user.id  # Получаем ID пользователя

    # Обновляем тему пользователя в базе данных
    async with aiosqlite.connect(PROFILE_DATABASE) as db:
        cursor = await db.execute("UPDATE profile SET theme = ? WHERE user_id = ?", (new_theme, user_id))
        await db.commit()

        if cursor.rowcount > 0:
            await update.message.reply_text(f"Тема изменена на {new_theme}.")
        else:
            await update.message.reply_text("Не удалось изменить тему. Возможно, вы еще не создали профиль.")
        
async def get_profile_from_db(username):
    """Извлекает информацию о профиле пользователя из базы данных."""
    try:
        async with aiosqlite.connect(PROFILE_DATABASE) as conn:
            async with conn.execute("SELECT * FROM profile WHERE username = ?", (username,)) as cursor:
                profile_info = await cursor.fetchone()
                return profile_info
    except aiosqlite3.Error as e:
        logger.error(f"Ошибка при получении профиля из базы данных: {e}")
        return None


async def get_profile_pic(user_id, username, code, coffe, reputation, theme):
    """Генерация и возврат изображения профиля."""
    background = None
    img = None
    Font = None
    usfont = None
    avatar_response = None

    try:
        # Загрузка шрифтов и фоновых изображени
        try:
            Font = ImageFont.truetype("Loopiejuice-Regular.ttf", size=150)
            if len(username) < 10:
            	usfont = ImageFont.truetype("Loopiejuice-Regular.ttf", size=80)
            elif len(username) < 14:
            	usfont = ImageFont.truetype("Loopiejuice-Regular.ttf", size=58)
            elif len(username) < 18:
            	usfont = ImageFont.truetype("Loopiejuice-Regular.ttf", size=38)
            elif len(username) >= 18:
            	usfont = ImageFont.truetype("Loopiejuice-Regular.ttf", size=38)
        except FileNotFoundError:
        	logger.error("Шрифт Loopiejuice-Regular.ttf не найден.")
        	return None
    		
        try:
            if theme == 'black':
                background = Image.open('black.png')
            elif theme == 'white':
                background = Image.open('white.png')
            else:
                logger.warning("Указана неверная тема. Используется тема black по умолчанию.")
                background = Image.open('black.png')  # Fallback to black
        except FileNotFoundError:
            logger.error(f"Фоновое изображение для темы '{theme}' не найдено.")
            return None

        img = background.copy()
        avatar = None  # Здесь нужно добавить логику для создания аватара

        try:
            response = requests.get(
                f'https://api.telegram.org/bot7699458589:AAEcauqa4rAKBkPp3MIIRNmNfzXyqrZY7n4/getUserProfilePhotos?user_id={user_id}',
                timeout=5
            ).json()
            print("Ответ от getUserProfilePhotos:", response)  # Логируем ответ

            if response.get('result', {}).get('total_count', 0) > 0:
                photo_file_id = response['result']['photos'][0][-1]['file_id']
                print("file_id:", photo_file_id)  # Логируем file_id

                file_response = requests.get(
                    f'https://api.telegram.org/bot7699458589:AAEcauqa4rAKBkPp3MIIRNmNfzXyqrZY7n4/getFile?file_id={photo_file_id}',
                    timeout=5
                ).json()
                print("Ответ от getFile:", file_response)  # Логируем ответ

                if 'result' in file_response:
                    photo_url = f'https://api.telegram.org/file/bot7699458589:AAEcauqa4rAKBkPp3MIIRNmNfzXyqrZY7n4/{file_response["result"]["file_path"]}'
                    try:
                        avatar_response = requests.get(photo_url, stream=True, timeout=5)
                        avatar_response.raise_for_status()
                        avatar = Image.open(io.BytesIO(avatar_response.content)).convert("RGBA")
                        avatar = avatar.resize((400, 400))

                        # Создаем маску для закругления углов
                        mask = Image.new('L', avatar.size, 0)
                        draw = ImageDraw.Draw(mask)
                        draw.ellipse((0, 0, avatar.size[0], avatar.size[1]), fill=255)

                        # Применяем маску к аватару
                        avatar.putalpha(mask)
                        img.paste(avatar, (38, 20), avatar)
                        
                    except requests.exceptions.RequestException as e:
                    	print(f"Error fetching the photo: {e}")
                    except IOError as e:
                        print(f"Error processing the image: {e}")

                        	
                else:
                    logger.warning("Не удалось получить file_path из ответа.")
            else:
                logger.info("Нет доступных профилей для этого пользователя.")
        except requests.exceptions.RequestException as e:
            logger.error(f"Ошибка при запросе к Telegram API: {e}")
        except Exception as e:
            logger.error(f"Непредвиденная ошибка при получении аватара пользователя: {e}")

        # Обработка текста
        d = ImageDraw.Draw(img)
        if Font:
            d.text((240, 550), username, fill=(255, 255, 255), anchor="mm", font=usfont)
            d.text((710, 100), str(code), fill=(255, 255, 255), anchor="lm", font=Font)
            d.text((710, 331), str(reputation), fill=(255, 255, 255), anchor="lm", font=Font)
            d.text((715, 553), str(coffe), fill=(255, 255, 255), anchor="lm", font=Font) #Преобразуем code в строку

        # Сохранение изображения в byte stream
        output = io.BytesIO()
        img.save(output, format='PNG')
        output.seek(0)
        return output

    except Exception as e:
        logger.error(f"Произошла ошибка при создании изображения профиля: {e}")
        return None

    finally:
        if avatar_response:
            avatar_response.close()


async def get_profile_from_db(username):
    """Извлекает информацию о профиле пользователя из базы данных."""
    try:
        async with aiosqlite.connect(PROFILE_DATABASE) as conn:
            async with conn.execute("SELECT * FROM profile WHERE username = ?", (username,)) as cursor:
                profile_info = await cursor.fetchone()
                return profile_info
    except aiosqlite.Error as e:
        logger.error(f"Ошибка при получении профиля из базы данных: {e}")
        return None

async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получение профиля пользователя."""

    username = None
    user_id = None
    user_id = update.effective_user.id
    new_username = update.message.from_user.username

    if new_username:  # Проверяем, что новое имя пользователя не пустое
        try:
            async with aiosqlite.connect(PROFILE_DATABASE) as conn:
                await conn.execute('''
                    UPDATE profile SET username = ? WHERE user_id = ?
                ''', (new_username, user_id))
                await conn.commit()
                
        except aiosqlite.Error as e:
            logger.error(f"Ошибка при обновлении имени пользователя в базе данных: {e}")

    # Проверяем, указано ли имя пользователя через аргументы команды или в ответе на сообщение
    if len(context.args) == 1:
        username = context.args[0].lstrip('@')
    elif update.message.reply_to_message and update.message.reply_to_message.from_user:
        username = update.message.reply_to_message.from_user.username
    else:
        username = update.message.from_user.username  # Если пользователь не указал username, используем свой

    # Получаем user_id на основе введенного username
    if username:
        profile_info = await get_profile_from_db(username)
    else:
        user_id = update.effective_user.id  # Получаем ID пользователя, инициировавшего команду
        profile_info = await get_profile_from_db(user_id)

    # Если профиля нет, создаем его по умолчанию
    if profile_info is None:
        code = 0
        coffe = 5
        reputation = 0
        theme = 'black'
        user_added = await user_add(user_id, username, code, coffe, reputation, theme)
        if not user_added:
            await update.message.reply_text("Произошла ошибка при создании профиля. Пользователь уже существует.")
            return

        # Снова получаем профиль, чтобы использовать его данные
        profile_info = await get_profile_from_db(username)

        if profile_info is None:
            await print("Произошла ошибка при получении профиля после создания.")
            return

    user_id = profile_info[0]  # Получаем user_id из базы данных
    theme = profile_info[5]  # Получаем тему из базы данных
    code = profile_info[2]
    coffe = profile_info[3]
    reputation = profile_info[4]

    profile_image = await get_profile_pic(user_id, username, code, coffe, reputation, theme)

    if profile_image:
        try:
            await context.bot.send_photo(chat_id=update.effective_chat.id, photo=profile_image)
        except Exception as e:
            logger.error(f"Ошибка при отправке фото: {e}")
            await update.message.reply_text("Произошла ошибка при отправке изображения профиля.")
    else:
        await update.message.reply_text("Не удалось создать изображение профиля.")


async def get_user_reputation(user_id):
    """Получает репутацию пользователя из базы данных."""
    try:
        async with aiosqlite.connect(PROFILE_DATABASE) as conn:
            async with conn.execute("SELECT reputation FROM profile WHERE user_id = ?", (user_id,)) as cursor:
                result = await cursor.fetchone()
                if result:
                    return result[0]
                else:
                    return 0  # Репутация по умолчанию
    except aiosqlite.Error as e:
        logger.error(f"Ошибка при получении репутации из базы данных: {e}")
        return 0

async def user_add(user_id, username, code, coffe, reputation, theme):
    """Добавляет пользователя в базу данных."""
    try:
        async with aiosqlite.connect(PROFILE_DATABASE) as conn:
            async with conn.execute("SELECT user_id FROM profile WHERE user_id = ?", (user_id,)) as cursor:
                if await cursor.fetchone() is None:
                    await conn.execute('''
                    INSERT INTO profile (user_id, username, code, coffe, reputation, theme)
                    VALUES (?, ?, ?, ?, ?, ?)
                    ''', (user_id, username, 0, 5, 0, "black"))
                    await conn.commit()
                    logger.info(f"Пользователь {username} успешно добавлен в базу данных.")
                    return True
                else:
                    logger.warning(f"Пользователь с user_id {user_id} уже существует в базе данных.")
                    return False  # Пользователь уже существует
    except aiosqlite.Error as e:
        logger.error(f"Ошибка при добавлении пользователя в базу данных: {e}")
        return False

async def us_add(usid, last_time, user_name, chance, count, count2, chance_fail):
    """Добавляет пользователя в базу данных."""
    try:
        async with aiosqlite.connect('coding.db') as conn:
            async with conn.execute("SELECT usid FROM coding WHERE usid = ?", (usid,)) as cursor:
                if await cursor.fetchone() is None:
                    await conn.execute('''
                    INSERT INTO coding (usid, last_time, user_name, chance, count, count2, chance_fail)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', (usid, 0, user_name, 5, 1, 5, 25))
                    await conn.commit()
                    logger.info(f"Пользователь {user_name} успешно добавлен в базу данных.")
                    return True
                else:
                    logger.warning(f"Пользователь с user_id {usid} уже существует в базе данных.")
                    return False  # Пользователь уже существует
    except aiosqlite.Error as e:
        logger.error(f"Ошибка при добавлении пользователя в базу данных: {e}")
        return False

def add_user(user_id):
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('INSERT INTO allowed_users (id) VALUES (?)', (user_id,))
    conn.commit()
    conn.close()

def remove_user(user_id):
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM allowed_users WHERE id = ?', (user_id,))
    conn.commit()
    conn.close()

def is_user_allowed(user_id):
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM allowed_users WHERE id = ?', (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result is not None

def extract_username(message: Message):
    if message.reply_to_message:
        return message.reply_to_message.from_user.username
    elif message.entities:
        for entity in message.entities:
            if entity.type == 'mention':
                return message.text[entity.offset + 1:entity.offset + entity.length]
    return None

async def joke(update: Update, context: ContextTypes.DEFAULT_TYPE):
	jokes = [
    ' Почему программисты путают Хэллоуин и Рождество? Потому что 31 OCT = 25 DEC.',

	' Два программиста обсуждают новый проект. Первый: "Давай напишем код так, чтобы он был понятен даже мне через полгода." Второй: "Ты что, собираешься увольняться?"',

	' Программист приходит к врачу: "Доктор, у меня болит голова!". Доктор: "Вы много работаете за компьютером?". Программист: "Нет, я пишу код!"',

	' Что общего у кота и хорошего программиста? Оба умеют спать по 16 часов, при этом выполнять свою работу отлично.',

	' Лучший способ объяснить рекурсию – это объяснить рекурсию.',

	' Дебаггинг – это процесс удаления ошибок из программы. Программирования – это процесс вставки ошибок.',

	' Программист – это человек, который решает проблемы, которых раньше не было.',

' Вопрос на собеседовании: "Что такое NULL?". Ответ программиста: "Это когда я наконец-то закончил работу в пятницу вечером."',

' Я не знаю, как прекратить программировать. Я пытался, но не получилось.',

' Программисты не умирают, они просто переходят в другое состояние.',

' Как программист называет свою собаку? Null Pointer.',

' Сколько программистов нужно, чтобы заменить лампочку? Ни одного. Это проблема оборудования.',

' Программист утонул. Ирония в том, что он знал Java, но не умел плавать.',

' Что делает программист в туалете? Он делает PUSH и POP.',

' В чем разница между программистом и богом? Бог не думает, что он – программист.',

' Программисты – это единственные люди, которые знают, что 1024 байт – это килобайт.',

' Почему программисты предпочитают пиво темному шоколаду? Потому что пиво быстрее дебажится.',

' Программист на вечеринке. Его спрашивают: "Что ты делаешь?". Он отвечает: "Я пытаюсь найти баг в системе." Гость: "Какой системе?". Программист: "В социальной."',

' Программист – это человек, который говорит: "Я всего лишь немного поменял код, и все сломалось".',

' Мой код работает идеально. Просто я его ещё не написал.',

' Что делает программист во время отпуска? Отлаживает свою личную жизнь.',

' В мире есть всего 10 типов людей: те, кто понимает двоичный код, и те, кто нет.',

' Программист – это человек, который может объяснить всё, кроме своего собственного кода.',

' Программист приходит домой и говорит жене: "У меня сегодня был очень тяжелый день. Мне пришлось дебажить целый день." Жена: "А завтра?" Программист: "Завтра выходной! Завтра у меня будет только 8 часов для отладки!"',

' У программиста спрашивают: "Сколько времени нужно, чтобы написать программу?". Он отвечает: "Полдня". А через полгода спрашивают: "Ну как?". Он отвечает: "Сейчас уже половина дня".',

' Программист и его собака гуляют. Собака находит кость. Программист смотрит на кость и говорит: "Неплохой сегмент памяти!".',

' Программист – это человек, который думает, что две бутылки пива – это модуль.',

' Программисты пишут программы, а программы пишут историю.',

' Что делает программист, когда его машина ломается? Он пишет новый код.',

' Почему программист купил холодильник? Чтобы избавиться от ошибок в коде (багов).',

' Программист: "О, у меня есть идея! Давай сделаем…". Все остальные: "Нет!"',

' Программист – это человек, который считает, что если это работает, то это можно улучшить.',

' Программист – это человек, который тратит 8 часов в день, чтобы создавать программы, которые никто не будет использовать.',

' Что такое оптимизация кода? Это когда он всё ещё работает, но выглядит ужасно.',

' Программист – это человек, который засыпает с клавиатурой в руках.',

' Лучший способ научиться программировать – это начать программировать.',

' Я провел целый день за компьютером и всё, что я получил – это новая ошибка.',

' Программирование – это как секс: один промах, и нужно девять месяцев, чтобы исправить последствия.',

' Если бы программисты могли строить здания, то каждое здание рухнуло бы.',

' Как называется группа программистов, которые дружат? Фреймворк.',

' Программисты и философы похожи: оба любят абстрактные идеи.',

' Программист – это тот, кто находит свои ошибки до того, как их найдёт юзер.',

' Программист: "Я закончил!" Менеджер: "А тесты?". Программист: "Они пройдут автоматически!".',

' Есть 10 видов людей: те, кто понимает двоичный код, и те, кто не понимает.',

' Программист не спит, он просто ищет баги в своем сне.',

' Хороший код объясняет себя сам. Плохой код требует комментариев.',

' Программист – это человек, который может решить проблему, которую никто не замечал.',

' Девушка спрашивает программиста: "Ты любишь меня?". Программист: "Да, правда-правда!".',

' Программист написал программу, которая может предсказывать будущее. Потому что он написал программу, которая предсказывала, что он напишет эту программу.',

' Программист – это человек, который решает проблемы с помощью технологий, которые создают новые проблемы.',

' Программист: "Не надо паниковать, всё ещё под контролем!". (Экран начинает мигать)',

' Программисты не используют копипаст, они используют рефакторинг.',

' Программист – это человек, который верит, что кофе – это волшебный эликсир.',

' Программирование – это искусство превращения кофе в код.',

' Почему программисты носят очки? Потому что они не видят разницы между 0 и 1.',

' Программист – это человек, который умеет говорить на нескольких языках: Python, Java, C++, и английском с сильным акцентом.',

' Программист – это тот, кто тратит 8 часов, чтобы написать программу, которая работает в течение 1 секунды.',

' Программисты – единственные, кто понимает, что «ошибка 404» – это не код ошибки, а отсутствие файла.',

' Что общего у женщины и компьютера? У обоих нужно сначала загрузить программу, прежде чем что-либо делать.',

' Программист – это человек, который думает, что код — это поэзия.',

' Программист – это человек, который тратит всю свою жизнь на разработку программ, которые никто не будет использовать.',

' Программисты любят работать на работе, потому что дома негде работать.',

' Программисты – это люди, которые живут в своем собственном мире.',

' Лучший способ объяснить что-то – это показать код.',

' Если бы программисты строили мосты, то мосты могли бы рухнуть.',

' Программисты – это единственные, кто думают, что «выходные» – это синтаксическая ошибка.',

' Почему программисты любят задержки? Потому что это как подарок к концу месяца.',

' Программисты думают, что они умные, пока не сталкиваются с реальным миром.',

' Программисты создают вирусы, а антивирусы создают программисты.',

' Программисты – это единственные, кто знают, что 2+2=5 (при определенных условиях).',

' Лучший способ найти баг – это написать новый код.',

' Программисты не засыпают, они просто отлаживают свои сны.',

' Как программист называет своего сына? Элемент.',

' Программист – это человек, который решает проблемы, которых не существовало.',

' Программисты – это единственные, кто знают, что 10^100 – это гугол.',

' Программист – это человек, который может написать код, который может написать другой код.',

' Программирование – это не работа, это образ жизни.',

' Программисты – это люди, которые знают, что мир движется благодаря коду.',

' Программист — это человек, который понимает, что бесконечный цикл — не всегда ошибка.',

' Почему программисты такие худые? Потому что они весь день едят только код.',

' Программисты не спят, они просто рекурсивно выполняют код.',

' Программисты не говорят, они компилируют.',

' Программисты — это творцы цифрового мира.',

' Программисты — это единственные, кто знает, что «undefined is not a function» — это не ошибка, а отсутствие функции.',

' Программист — это человек, который пишет код, чтобы автоматизировать свою работу, а затем проводит весь день, исправляя ошибки в этом коде.',

' Программисты — это люди, которые могут писать код на любом языке, кроме родного.',

' Что общего у программиста и пиццы? Они обоих лучше всего работают, когда их нарезают на кусочки.',

' Программисты – это те, кто знает, как сделать программу, которая сама себя пишет.',

' Программисты – это те, кто считает, что код – это лучшее искусство.',

' Программисты — это единственные, кто могут понять, что «null pointer exception» — это не просто ошибка, а отсутствие указателя.',

' Как программист украшает елку? Бинарным деревом.',

' Программисты не болеют, они просто подвержены ошибкам.',

' Программисты не задерживаются на работе, они просто отлаживают.',

' Программисты не пьют кофе, они запускают код.',

' Программисты не едят, они компилируют.',

' Программисты не ходят в туалет, они вызывают исключения.',

' Программисты не умирают, они просто переходят в состояние отладки.',

' Программисты не спят, они просто ищут ошибки в своей жизни.',

' Программисты не отдыхают, они просто перезагружаются.',

' Программисты не любят понедельники, они любят дедлайны.'
	]
	await update.message.reply_text(random.choice(jokes))

async def quote(update: Update, context: ContextTypes.DEFAULT_TYPE):
	# Простой список цитат
	quotes = [
	"Не позволяйте вчерашнему дню занимать слишком много из сегодняшнего.",
	"Только тот, кто рискует зайти слишком далеко, может узнать, как далеко можно зайти.",
	"Сложности - это то, что делает жизнь интересной. Преодоление их - это то, что делает жизнь значимой.",
	"Лучшая месть - это огромный успех."
	]
	await update.message.reply_text(random.choice(quotes))

async def report(update: Update, context: ContextTypes.DEFAULT_TYPE):
	if len(context.args) < 1:
		await update.message.reply_text('Пожалуйста, укажите пользователя, которого хотите зарепортить, используя @username или ответив на его сообщение.')
		return
		
		username = extract_username(update.message)
		if username is None:
			await update.message.reply_text("Укажите пользователя, используя @username или ответьте на его сообщение.")
			return
			
			# Здесь можно добавить функциональность для отправки репорта (например, администратору или в лог)
			await update.message.reply_text(f'Пользователь @{username} был зарепорчен.')

# Команды
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Добро пожаловать в бота от Фрики! введите/help для просмотрасписка комманд.")

async def add_user_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_user_allowed(update.effective_user.id):
        await update.message.reply_text("У вас нет прав для использования этой команды.")
        return

    username = extract_username(update.message)
    if username is None:
        await update.message.reply_text("Укажите пользователя, используя @username или ответьте на его сообщение.")
        return

    user_id = update.message.reply_to_message.from_user.id if update.message.reply_to_message else None
    if user_id is not None:
        add_user(user_id)
        await update.message.reply_text(f'Пользователь @{username} добавлен.')
    else:
        await update.message.reply_text('Не удалось добавить пользователя. Убедитесь, что вы указали корректного пользователя.')

async def remove_user_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_user_allowed(update.effective_user.id):
        await update.message.reply_text("У вас нет прав для использования этой команды.")
        return

    username = extract_username(update.message)
    if username is None:
        await update.message.reply_text("Укажите пользователя, используя @username или ответьте на его сообщение.")
        return

    user_id = update.message.reply_to_message.from_user.id if update.message.reply_to_message else None
    if user_id is not None:
        remove_user(user_id)
        await update.message.reply_text(f'Пользователь @{username} удален.')
    else:
        await update.message.reply_text('Не удалось удалить пользователя. Убедитесь, что вы указали корректного пользователя.')

async def list_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_user_allowed(update.effective_user.id):
        await update.message.reply_text("У вас нет прав для использования этой команды.")
        return

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('SELECT id FROM allowed_users')
    users = cursor.fetchall()
    conn.close()

    if users:
        user_list = "\n".join(str(user[0]) for user in users)
        await update.message.reply_text(f"Разрешённые пользователи:\n{user_list}")
    else:
        await update.message.reply_text("Нет разрешённых пользователей.")

async def ban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_user_allowed(update.effective_user.id):
        await update.message.reply_text("У вас нет прав для использования этой команды.")
        return

    if len(context.args) < 1:
        await update.message.reply_text('Укажите пользователя, используя @username или ответьте на его сообщение.')
        return

    username = extract_username(update.message)
    if not username:
        await update.message.reply_text("Укажите пользователя, используя @username или ответьте на его сообщение.")
        return

    user_id = update.message.reply_to_message.from_user.id if update.message.reply_to_message else None

    if user_id is not None:
        duration = context.args[0] if context.args else None
        if duration and duration.lower() == 'навсегда':
            banned_users[username] = 'forever'
            await update.message.reply_text(f'Пользователь @{username} забанен навсегда.')
        else:
            try:
                time = int(duration)  # предполагаем, что время передается в минутах
                banned_users[username] = timedelta(minutes=time)
                await update.message.reply_text(f'Пользователь @{username} забанен на {time} минут.')
            except ValueError:
                await update.message.reply_text('Неправильный формат времени. Используйте целое число или "навсегда".')
    else:
        await update.message.reply_text('Не удалось забанить пользователя. Убедитесь, что вы указали корректного пользователя.')

async def unban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_user_allowed(update.effective_user.id):
        await update.message.reply_text("У вас нет прав для использования этой команды.")
        return

    username = extract_username(update.message)
    if username is None:
        await update.message.reply_text("Укажите пользователя, используя @username или ответьте на его сообщение.")
        return

    user_id = update.message.reply_to_message.from_user.id if update.message.reply_to_message else None

    if user_id:
        if username in banned_users:
            del banned_users[username]
            await update.message.reply_text(f'Пользователь @{username} разблокирован.')
        else:
            await update.message.reply_text(f'Пользователь @{username} не забанен.')
    else:
        await update.message.reply_text('Не удалось разблокировать пользователя. Убедитесь, что вы указали корректного пользователя.')

async def mute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_user_allowed(update.effective_user.id):
        await update.message.reply_text("У вас нет прав для использования этой команды.")
        return

    if len(context.args) < 1:
        await update.message.reply_text('Укажите пользователя, используя @username или ответьте на его сообщение.')
        return

    username = extract_username(update.message)
    if username is None:
        await update.message.reply_text("Укажите пользователя, используя @username или ответьте на его сообщение.")
        return

    user_id = update.message.reply_to_message.from_user.id if update.message.reply_to_message else None

    if user_id is not None:
        duration = context.args[0] if context.args else None
        if duration and duration.lower() == 'навсегда':
            muted_users[username] = 'forever'
            await update.message.reply_text(f'Пользователь @{username} отключен навсегда.')
        else:
            try:
                time = int(duration)  # предполагаем, что время передается в минутах
                muted_users[username] = timedelta(minutes=time)
                await update.message.reply_text(f'Пользователь @{username} отключен на {time} минут.')
            except ValueError:
                await update.message.reply_text('Неправильный формат времени. Используйте целое число или "навсегда".')
    else:
        await update.message.reply_text('Не удалось отключить пользователя. Убедитесь, что вы указали корректного пользователя.')

async def unmute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_user_allowed(update.effective_user.id):
        await update.message.reply_text("У вас нет прав для использования этой команды.")
        return

    username = extract_username(update.message)
    if username is None:
        await update.message.reply_text("Укажите пользователя, используя @username или ответьте на его сообщение.")
        return

    user_id = update.message.reply_to_message.from_user.id if update.message.reply_to_message else None

    if user_id:
        if username in muted_users:
            del muted_users[username]
            await update.message.reply_text(f'Пользователь @{username} снова включен.')
        else:
            await update.message.reply_text(f'Пользователь @{username} не отключен.')
    else:
        await update.message.reply_text('Не удалось включить пользователя. Убедитесь, что вы указали корректного пользователя.')

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    banned_count = len(banned_users)
    muted_count = len(muted_users)
    await update.message.reply_text(f'Забанено пользователей: {banned_count}\n'
                                     f'Отключено пользователей: {muted_count}')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "Доступные команды:\n"
        "/start - Запуск бота\n"
        "/add_user @username - Добавить пользователя в администраторы (только для администраторов)\n"
        "/remove_user @username - Удалить пользователя из администраторов (только для администраторов)\n"
        "/list_users - Показать список администраторов (только для администраторов)\n"
        "/ban @username <время/навсегда> - Забанить пользователя (только для администраторов)\n"
        "/unban @username - Разбанить пользователя (только для администраторов)\n"
        "/mute @username <время/навсегда> - Отключить пользователя (только для администраторов)\n"
        "/unmute @username - Включить пользователя (только для администраторов)\n"
        "/stats - Показать статистику наказанийn"
        "/help - Показать это сообщение\n"
        "/ping - Проверить работоспособность бота\n"
        "/echo <сообщение> - Повторить ваше сообщение\n"
        "/clear_bans - Очистить список забаненных пользователей (только для администраторов)\n"
        "/clear_mutes - Очистить список замученных пользователей (только для администраторов)\n"
        "/joke - рандомная шутка про програмистов\n"
        "/quote - рандомная цитата\n"
        "/report - жалоба"
    )
    await update.message.reply_text(help_text)

async def ping(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Pong!")

async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.args:
        username = update.effective_user.username
        message = ' '.join(context.args)
        response_message = f'@{username} попросил меня сказать "{message}"'
        await update.message.reply_text(response_message)
    else:
        await update.message.reply_text('Введите сообщение для повтора. Используйте /echo <ваше сообщение>.')

async def clear_bans(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_user_allowed(update.effective_user.id):
        await update.message.reply_text("У вас нет прав для использования этой команды.")
        return

    banned_users.clear()
    await update.message.reply_text('Список забаненных пользователей очищен.')

async def clear_mutes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_user_allowed(update.effective_user.id):
        await update.message.reply_text("У вас нет прав для использования этой команды.")
        return

    muted_users.clear()
    await update.message.reply_text('Список замученных пользователей очищен.')

def main():
    # Создаем таблицу пользователей
    create_user_tables()

    # Замените 'YOUR_TOKEN' на токен вашего бота
    application = ApplicationBuilder().token("7699458589:AAEcauqa4rAKBkPp3MIIRNmNfzXyqrZY7n4").build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("add_user", add_user_command))
    application.add_handler(CommandHandler("remove_user", remove_user_command))
    application.add_handler(CommandHandler("list_users", list_users))
    application.add_handler(CommandHandler("ban", ban))
    application.add_handler(CommandHandler("unban", unban))
    application.add_handler(CommandHandler("mute", mute))
    application.add_handler(CommandHandler("unmute", unmute))
    application.add_handler(CommandHandler("stats", stats))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("ping", ping))
    application.add_handler(CommandHandler("echo", echo))
    application.add_handler(CommandHandler("clear_bans", clear_bans))
    application.add_handler(CommandHandler("clear_mutes", clear_mutes))
    application.add_handler(CommandHandler("report", report))
    application.add_handler(CommandHandler("quote", quote))
    application.add_handler(CommandHandler("joke", joke))
    application.add_handler(CommandHandler("profile", profile))
    application.add_handler(CommandHandler("theme", theme))
    application.add_handler(CommandHandler("coding", coding))
    application.add_handler(CommandHandler("turn", turn))
    application.add_handler(CommandHandler("shop", shop))
    application.add_handler(CallbackQueryHandler(button_callback))


    application.run_polling()

if __name__ == '__main__':
    main()