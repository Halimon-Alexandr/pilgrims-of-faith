import sys
import signal
import json
import os
import pytz
import pickle
import telebot
from telebot import types
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from decouple import config
from datetime import datetime, timedelta
from collections import defaultdict
import io
import schedule
from threading import Thread
import time
import logging

last_stats_message = ""
# Налаштування логування
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Встановлення часової зони Київ
kiev_timezone = pytz.timezone("Europe/Kiev")

# Встановлення часу публікації контента
publish_times = ["06:00", "07:00", "08:00", "10:00", "11:00", "12:00", "14:00", "15:00", "16:00", "18:00", "19:00", "20:00"]

bible = {
    "Буття": "01",
    "Вихід": "02",
    "Левіт": "03",
    "Числа": "04",
    "Второзаконня": "05",
    "Ісуса Навина": "06",
    "Суддів": "07",
    "Рути": "08",
    "1 Самуїла": "09",
    "2 Самуїла": "10",
    "1 Царів": "11",
    "2 Царів": "12",
    "1 Хронік": "13",
    "2 Хронік": "14",
    "Езри": "15",
    "Неємії": "16",
    "Естери": "17",
    "Іова": "18",
    "Псалмів": "19",
    "Приповідок": "20",
    "Проповідника": "21",
    "Пісні Пісень": "22",
    "Ісаї": "23",
    "Єремії": "24",
    "Плач Єремії": "25",
    "Єзекиїла": "26",
    "Даниїла": "27",
    "Осії": "28",
    "Йоіла": "29",
    "Амоса": "30",
    "Авдія": "31",
    "Йони": "32",
    "Міхея": "33",
    "Наума": "34",
    "Авакума": "35",
    "Софонії": "36",
    "Аггея": "37",
    "Захарії": "38",
    "Малахії": "39",
    "Євангеліє від Матея": "40",
    "Євангеліє від Марка": "41",
    "Євангеліє від Луки": "42",
    "Євангеліє від Йоана": "43",
    "Діяння апостолів": "44",
    "Послання Якова": "45",
    "1 Послання Петра": "46",
    "2 Послання Петра": "47",
    "1 Послання Йоана": "48",
    "2 Послання Йоана": "49",
    "3 Послання Йоана": "50",
    "Послання Юди": "51",
    "Послання до Римлян": "52",
    "1 Послання до Коринтян": "53",
    "2 Послання до Коринтян": "54",
    "Послання до Галатів": "55",
    "Послання до Ефесян": "56",
    "Послання до Филип'ян": "57",
    "Послання до Колосян": "58",
    "1 Послання до Солунян": "59",
    "2 Послання до Солунян": "60",
    "1 Послання до Тимотея": "61",
    "2 Послання до Тимотея": "62",
    "Послання до Тита": "63",
    "Послання до Филимона": "64",
    "Послання до Євреїв": "65",
    "Одкровення Йоана": "66"
}

# Налаштування адміністративних параметрів і токена бота
ADMIN = config("TG_CHAT_ADMIN")
GROUP_CHAT_ID = config("TG_GROUP_CHAT_ID")
READING_PLAN_THREAD_ID = config("TG_READING_PLAN_THREAD_ID")
GAME_THREAD_ID = config("TG_GAME_THREAD_ID", default=None)  # Використовуємо TG_Thread_ID
API_TOKEN = config('TG_BOT_TOKEN')

# Ініціалізація бота
bot = telebot.TeleBot(API_TOKEN)

# Шляхи до файлів даних
STATS_DATA_FILE = "stats_data.json"
QUIZ_DATA_FILE = "quiz_data.pickle"
DATA_FILE = "user_data.pickle"

# Функції для збереження, відновлення та очищення даних користувачів
def save_data():
    with open(DATA_FILE, 'wb') as file:
        pickle.dump(user_data, file)

def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'rb') as file:
                return pickle.load(file)
        except (EOFError, pickle.UnpicklingError):
            # Якщо файл пошкоджений або порожній, повертаємо порожній словник
            return {}
    else:
        # Якщо файл не існує, повертаємо порожній словник
        return {}

def reset_user_data():
    now = datetime.now(kiev_timezone)
    current_day = now.strftime('%A').lower()

    if current_day == "monday":
        user_data.clear()
        save_data()

# Функції для збереження, відновлення, та очищення даних вікторин
def save_quiz_data():
    with open(QUIZ_DATA_FILE, 'wb') as file:
        pickle.dump(quiz_data, file)

def load_quiz_data():
    if os.path.exists(QUIZ_DATA_FILE):
        try:
            with open(QUIZ_DATA_FILE, 'rb') as file:
                return pickle.load(file)
        except (EOFError, pickle.UnpicklingError):
            # Якщо файл пошкоджений або порожній, повертаємо порожній словник
            return {}
    else:
        # Якщо файл не існує, повертаємо порожній словник
        return {}

def reset_quiz_data():
    quiz_data.clear()
    save_quiz_data()

# Завантаження правильних відповідей з JSON файлу
def load_answers():
    with open('answers.json', 'r', encoding='utf-8') as file:
        return json.load(file)

# Функція для перезавантаження бота
def restart_bot():
    python = sys.executable
    os.execl(python, python, *sys.argv)

# Функція для зчитування плану читання з JSON файлу
def load_reading_plan():
    with open('bible_reading_plan.json', 'r', encoding='utf-8') as file:
        return json.load(file)

# Збереження та відоновлення повідомлення статистики
def save_stats_data():
    with open(STATS_DATA_FILE, 'w', encoding='utf-8') as file:
        json.dump({'stats_message_id': stats_message_id, 'last_stats_message': last_stats_message}, file, ensure_ascii=False, indent=4)

def load_stats_data():
    global stats_message_id, last_stats_message
    if os.path.exists(STATS_DATA_FILE):
        try:
            with open(STATS_DATA_FILE, 'r', encoding='utf-8') as file:
                data = json.load(file)
                stats_message_id = data.get('stats_message_id')
                last_stats_message = data.get('last_stats_message', "")
        except (EOFError, json.JSONDecodeError):
            stats_message_id = None
            last_stats_message = ""
    else:
        stats_message_id = None
        last_stats_message = ""

# Обробляємо повідомлення лише коли гра активна і з ігрової гілки
@bot.message_handler(func=lambda message: game_active and message.chat.id == int(GROUP_CHAT_ID)
                      and message.message_thread_id == int(GAME_THREAD_ID))
def check_message(message):
    user_id = message.from_user.id
    text = message.text.strip().lower()  # Змінюємо текст на нижній регістр

    # Перевірка на використане ім'я
    if text in (used_answer.lower() for used_answer in used_answers.keys()):  # Перевіряємо у використаних відповідях
        bot.send_message(GROUP_CHAT_ID, "✅ Це ім'я вже називалося!", message_thread_id=int(GAME_THREAD_ID), parse_mode='Markdown')
        return  # Завершуємо обробку, якщо ім'я вже було використано

    # Перевіряємо основний словник
    matched = False
    for answer in list(correct_answers):  # Створюємо копію списку ключів для ітерації
        answer_words = answer.split()

        # Якщо будь-яке слово з тексту користувача міститься в ключі
        if any(word.lower() == text for word in answer_words):  # Використовуємо нижній регістр для порівняння
            matched = True  # Відзначаємо, що знайдено збіг
            # Якщо відповідь правильна, оновлюємо статистику
            if user_id not in user_scores:
                user_scores[user_id] = 0
            user_scores[user_id] += 1

            # Формуємо повідомлення
            correct_answer_message = (
                f"✅ Так, вірно! Є таке ім'я: *{answer}*, воно згадується тут: \n*{correct_answers[answer]}*.\n"
                f"🎉 У тебе вже {user_scores[user_id]} правильних відповідей! 🎉"
            )

            # Відправляємо повідомлення в ту ж гілку
            bot.send_message(GROUP_CHAT_ID, correct_answer_message, message_thread_id=int(GAME_THREAD_ID), parse_mode='Markdown')

            # Переносимо правильну відповідь у використані та видаляємо з основного словника
            used_answers[answer] = correct_answers[answer]  # Додаємо до використаних
            del correct_answers[answer]  # Видаляємо з основного

            break  # Виходимо з циклу, бо вже знайшли відповідь

    # Якщо не знайдено правильну відповідь, надсилаємо повідомлення про помилку
    if not matched:
        error_message = "❌ Нажаль, я це ім'я не знаю."
        bot.send_message(GROUP_CHAT_ID, error_message, message_thread_id=int(GAME_THREAD_ID), parse_mode='Markdown')

# Функція для надсилання плану читання
def publish_reading(entry, index, total):
    book = entry['book']
    chapter = entry['chapter']

    # Отримуємо відповідну директорію книги за допомогою словника
    book_dir = bible.get(book)

    # Створюємо інлайн клавіатуру з чотирьма кнопками
    keyboard = InlineKeyboardMarkup()
    button_khomenko = InlineKeyboardButton(
        text="Хоменка",
        url=f"http://mog-pod.pp.ua/bible/UBIH/book{book_dir}/{chapter}/"
    )
    button_modern = InlineKeyboardButton(
        text="Сучасний",
        url=f"http://mog-pod.pp.ua/bible/CUV/book{book_dir}/{chapter}/"
    )
    button_turkonyak = InlineKeyboardButton(
        text="Турконяка",
        url=f"http://mog-pod.pp.ua/bible/УТТ/book{book_dir}/{chapter}/"
    )
    button_ogiyenko = InlineKeyboardButton(
        text="Огієнка",
        url=f"http://mog-pod.pp.ua/bible/UBIO/book{book_dir}/{chapter}/"

)
    keyboard.add(button_ogiyenko, button_khomenko, button_modern, button_turkonyak)

    if book_dir:
        file_name = f"{int(chapter):03d}.ogg"  # Форматування номера розділу у вигляді 001, 002 і т.д.
        file_path = os.path.join("bible", book_dir, file_name)

        if os.path.exists(file_path):
            try:
                with open(file_path, 'rb') as ogg_file:
                    ogg_data = io.BytesIO(ogg_file.read())

                message = f"📖 План читання {index} із {total}:\nКнига {book}, Розділ {chapter} ✨"
                # Відправляємо голосове повідомлення з клавіатурою
                bot.send_voice(GROUP_CHAT_ID, ogg_data, caption=message, reply_markup=keyboard, message_thread_id=READING_PLAN_THREAD_ID)
            except Exception as e:
                bot.send_message(ADMIN, f"Сталася помилка при відправці аудіофайлу: {e}")
        else:
            message = f"📖 План читання {index} із {total}:\nКнига {book}, Розділ {chapter} ✨"
            bot.send_message(GROUP_CHAT_ID, message, reply_markup=keyboard, message_thread_id=READING_PLAN_THREAD_ID)
    else:
        message = f"📖 План читання {index} із {total}:\nКнига {book}, Розділ {chapter} ✨"
        bot.send_message(GROUP_CHAT_ID, message, reply_markup=keyboard, message_thread_id=READING_PLAN_THREAD_ID)

    entry['published'] = True

# Функція для публікації вікторини
def publish_quiz(quiz):
    question = quiz['question']
    options = quiz['answers']
    correct_option_id = quiz.get('correct_option_id')
    explanation = quiz.get('comment', 'Правильна відповідь не надана.')  # Додаємо пояснення

    if not isinstance(correct_option_id, int) or correct_option_id < 0 or correct_option_id >= len(options):
        return

    message = bot.send_poll(
        GROUP_CHAT_ID,
        question,
        options,
        is_anonymous=False,
        type='quiz',
        correct_option_id=correct_option_id,
        explanation=explanation,
        message_thread_id=READING_PLAN_THREAD_ID
    )
    quiz_data[message.poll.id] = {"correct_option_id": correct_option_id}
    save_quiz_data()
    quiz['published'] = True

# Функція для ручної публікації плану читання та вікторин
def manual_publish_reading_and_quizzes():
    today = datetime.now(kiev_timezone).strftime('%m-%d')

    if today in reading_plan:
        daily_plan = reading_plan[today]

        for idx, entry in enumerate(daily_plan):
            if not entry.get('published', False):
                total_readings = len(daily_plan)
                publish_reading(entry, idx + 1, total_readings)
                entry['published'] = True

                with open('bible_reading_plan.json', 'w', encoding='utf-8') as file:
                    json.dump(reading_plan, file, ensure_ascii=False, indent=4)

                return

            if 'quizzes' in entry:
                for quiz in entry['quizzes']:
                    if not quiz.get('published', False):
                        publish_quiz(quiz)
                        quiz['published'] = True

                        with open('bible_reading_plan.json', 'w', encoding='utf-8') as file:
                            json.dump(reading_plan, file, ensure_ascii=False, indent=4)

                        return


# Функція публікації щоденної статистики вікторин
def publish_daily_quiz_statistics():
    global stats_message_id, last_stats_message
    now = datetime.now(kiev_timezone)
    today_weekday = now.strftime("%A").lower()

    # Переклад днів тижня
    days_translation = {
        "monday": "Понеділок",
        "tuesday": "Вівторок",
        "wednesday": "Середа",
        "thursday": "Четвер",
        "friday": "П'ятниця",
        "saturday": "Субота",
        "sunday": "Неділя"
    }
    day_of_week_ua = days_translation.get(today_weekday, today_weekday)

    # Переклад місяців
    months_translation = {
        "january": "січня",
        "february": "лютого",
        "march": "березня",
        "april": "квітня",
        "may": "травня",
        "june": "червня",
        "july": "липня",
        "august": "серпня",
        "september": "вересня",
        "october": "жовтня",
        "november": "листопада",
        "december": "грудня"
    }
    month_ua = months_translation.get(now.strftime("%B").lower(), now.strftime("%B").lower())

    day_number = now.weekday() + 1

    stats_message = f"{day_of_week_ua} {now.day} {month_ua}\n"
    total_quizzes_today = 0
    stats = defaultdict(lambda: {'today': 0})

    # Count the total number of quizzes for today
    for entry in reading_plan.get(now.strftime('%m-%d'), []):
        if 'quizzes' in entry:
            total_quizzes_today += len(entry['quizzes'])

    # Collect today's statistics
    for user_id, data in user_data.items():
        name = data["name"]
        today_correct = data["correct_answers"].get(today_weekday, 0)
        if today_correct > 0:
            stats[user_id]['today'] = today_correct

    # Sort users by today's correct answers
    sorted_stats = sorted(stats.items(), key=lambda x: x[1]['today'], reverse=True)

    if not sorted_stats:
        stats_message += "На сьогодні результатів покищо немає.\n"
    else:
        stats_message += f"Кількість вікторин: {total_quizzes_today}\n"
        stats_message += "Найкращі результати:\n"
        for user_id, stat in sorted_stats:
            user_name = user_data[user_id]['name']
            today_correct = stat['today']
            stats_message += f"{user_name}: {today_correct}.\n"

    # Check if the content of the message has changed
    if stats_message == last_stats_message:
        return

    if stats_message_id:
        bot.edit_message_text(stats_message, GROUP_CHAT_ID, stats_message_id)
    else:
        message = bot.send_message(GROUP_CHAT_ID, stats_message, message_thread_id=READING_PLAN_THREAD_ID)
        stats_message_id = message.message_id
        bot.pin_chat_message(GROUP_CHAT_ID, stats_message_id)

    # Save the last stats message and message ID
    last_stats_message = stats_message
    save_stats_data()


# Функція публікації статистики вікторин
def publish_quiz_statistics():
    now = datetime.now(kiev_timezone)
    today_str = now.strftime('%m-%d')
    today_weekday = now.strftime("%A").lower()
    days_translation = {
        "Monday": "Понеділок",
        "Tuesday": "Вівторок",
        "Wednesday": "Середа",
        "Thursday": "Четвер",
        "Friday": "П'ятниця",
        "Saturday": "Субота",
        "Sunday": "Неділя"
    }
    day_of_week = now.strftime("%A")
    day_of_week_ua = days_translation.get(day_of_week, day_of_week)
    day_number = now.weekday() + 1
    if day_number == 1:
        stats_message = f"Сьогодні {day_of_week_ua}, перший день марафону. 🎉 🏃"
    elif day_number == 7:
        stats_message = f"Сьогодні {day_of_week_ua}, останній і заключний день марафону. 🎆 🏁"
    else:
        stats_message = f"Сьогодні {day_of_week_ua}, {day_number}-й день марафону. 🏃"
    total_quizzes_week = 0
    start_date = (now - timedelta(days=now.weekday())).strftime('%m-%d')
    for date, entries in reading_plan.items():
        if start_date <= date <= today_str:
            total_quizzes_week += sum(len(entry.get('quizzes', [])) for entry in entries)
    total_correct_week = 0
    stats = defaultdict(lambda: {'weekly': 0, 'today': 0})
    fully_correct_users = 0
    week_days = [(now - timedelta(days=i)).strftime('%A').lower() for i in range(now.weekday() + 1)]
    for user_id, data in user_data.items():
        name = data["name"]
        weekly_correct = 0
        today_correct = 0
        for day_str, count in data["correct_answers"].items():
            if day_str in week_days:
                weekly_correct += count
                total_correct_week += count
                if day_str == today_weekday:
                    today_correct += count
        stats[user_id]['weekly'] = weekly_correct
        stats[user_id]['today'] = today_correct
        if weekly_correct >= total_quizzes_week and total_quizzes_week > 0:
            fully_correct_users += 1
    total_participants_week = len(user_data)
    sorted_stats = sorted(stats.items(), key=lambda x: x[1]['weekly'], reverse=True)
    stats_message += f"\nКількість вікторин: {total_quizzes_week}\nКількість користувачів: {total_participants_week}\n"
    stats_message += f"🏆 На сьогодні топ-10 виглядає так:\n"
    stats_message += f"Користувач | За тиждень | Сьогодні.\n"
    for i, (user_id, stat) in enumerate(sorted_stats[:10], start=1):
        user_name = user_data[user_id]['name']
        weekly_correct = stat['weekly']
        today_correct = stat['today']
        stats_message += f"{user_name} | {weekly_correct} | {today_correct}.\n"

    # Відправка повідомлення
    bot.send_message(GROUP_CHAT_ID, stats_message, message_thread_id=251)
    



# Статистика по публікаціям
def check_unpublished_content():
    now = datetime.now(kiev_timezone)
    today_str = now.strftime('%m-%d')

    total_readings = 0
    published_readings = 0
    unpublished_readings = 0

    total_quizzes = 0
    published_quizzes = 0
    unpublished_quizzes = 0

    if today_str in reading_plan:
        daily_plan = reading_plan[today_str]

        # Підрахунок планів читання
        total_readings = len(daily_plan)
        for entry in daily_plan:
            if entry.get('published', False):
                published_readings += 1
            else:
                unpublished_readings += 1

            # Підрахунок вікторин
            if 'quizzes' in entry:
                total_quizzes += len(entry['quizzes'])
                for quiz in entry['quizzes']:
                    if quiz.get('published', False):
                        published_quizzes += 1
                    else:
                        unpublished_quizzes += 1

    # Формування повідомлення
    message = (
        f"Кількість місць писання: {total_readings}, з них неопубліковано: {unpublished_readings}.\n"
        f"\nКількість вікторин: {total_quizzes}, не опубліковано: {unpublished_quizzes}.\n"
    )

    # Відправка повідомлення адміністратору
    bot.send_message(ADMIN, message)

# Обробник голосувань по вікторинам
@bot.poll_answer_handler()
def handle_poll_answer(poll_answer):
    user_id = poll_answer.user.id
    selected_option = poll_answer.option_ids[0]
    poll_id = poll_answer.poll_id

    # Перевірка правильності відповіді
    if poll_id in quiz_data:
        correct_option_id = quiz_data[poll_id]['correct_option_id']
        day_of_week = datetime.now(kiev_timezone).strftime("%A").lower()

        if selected_option == correct_option_id:
            # Перевірка, чи користувач вже зареєстрований
            if user_id not in user_data:
                # Отримуємо повне ім'я користувача
                first_name = poll_answer.user.first_name if poll_answer.user.first_name else ""
                last_name = poll_answer.user.last_name if poll_answer.user.last_name else ""
                full_name = f"{first_name} {last_name}" if first_name and last_name else first_name or "без імені"

                user_data[user_id] = {
                    "name": full_name,
                    "correct_answers": {}
                }

            # Оновлюємо статистику правильних відповідей
            if day_of_week not in user_data[user_id]["correct_answers"]:
                user_data[user_id]["correct_answers"][day_of_week] = 0
            user_data[user_id]["correct_answers"][day_of_week] += 1

    # Оновлюємо дані користувачів
    save_data()
    publish_daily_quiz_statistics()

# Обробка документів, отриманих через бот
@bot.message_handler(content_types=['document'])
def handle_document_message(message):
    document_id = message.document.file_id
    file_info = bot.get_file(document_id)
    file_path = file_info.file_path

    download_path = os.path.join(os.getcwd(), message.document.file_name)

    try:
        with open(download_path, 'wb') as file:
            file.write(bot.download_file(file_path))
        reading_plan = load_reading_plan()
        bot.send_message(message.chat.id, f"Файл '{message.document.file_name}' успішно збережено у директорії бота.")
    except Exception as e:
        bot.send_message(message.chat.id, f"Сталася помилка при збереженні файлу: {e}")

# Функція для старту гри
def start_game(message):
    global game_active, correct_answers

    if str(message.from_user.id) != ADMIN:
        bot.reply_to(message, "Тільки адміністратор може запустити гру.")
        return

    game_active = True
    correct_answers = load_answers()  # Оновлюємо список відповідей
    used_answers.clear()  # Очищаємо словник використаних відповідей

    game_start_message = (
        """**Друзі!** 🌟

Я нещодавно досліджував книги Нового Завіту і з великим інтересом помітив, що там згадується безліч жіночих імен. 💖

Якщо ви напишете імена, які я там знайшов, то за кожне правильне ім'я ви отримаєте бал. 🎉

**Кращих учасників я відзначу в статистиці!** 🏆

Гра розпочалася! Можете писати! 📜"""
    )

    if GAME_THREAD_ID:  # Використовуємо THREAD_ID, якщо воно визначене
        bot.send_message(GROUP_CHAT_ID, game_start_message, message_thread_id=int(GAME_THREAD_ID), parse_mode='Markdown')
    else:
        bot.send_message(GROUP_CHAT_ID, game_start_message, parse_mode='Markdown')

# Команда для зупинки гри
def stop_game(message):
    global game_active

    if str(message.from_user.id) != ADMIN:
        bot.reply_to(message, "Тільки адміністратор може зупинити гру.")
        return

    game_active = False
    if GAME_THREAD_ID:
        bot.send_message(GROUP_CHAT_ID, "Гру зупинено! Ось статистика правильних відповідей:", message_thread_id=int(GAME_THREAD_ID))
    else:
        bot.send_message(GROUP_CHAT_ID, "Гру зупинено! Ось статистика правильних відповідей:")

    # Виводимо статистику
    if user_scores:
        stats = "\n".join([f"{bot.get_chat_member(GROUP_CHAT_ID, user_id).user.first_name}: {score}" for user_id, score in user_scores.items()])
        if GAME_THREAD_ID:
            bot.send_message(GROUP_CHAT_ID, stats, message_thread_id=int(GAME_THREAD_ID))
        else:
            bot.send_message(GROUP_CHAT_ID, stats)
    else:
        if GAME_THREAD_ID:
            bot.send_message(GROUP_CHAT_ID, "Ніхто не дав правильних відповідей.", message_thread_id=int(GAME_THREAD_ID))
        else:
            bot.send_message(GROUP_CHAT_ID, "Ніхто не дав правильних відповідей.")

    # Очищаємо статистику та відповіді для нової гри
    user_scores.clear()

@bot.message_handler(commands=['start'])
def handle_start(message):
    user_id = message.from_user.id
    first_name = message.from_user.first_name or "Без імені"
    last_name = message.from_user.last_name or ""

    full_name = f"{first_name} {last_name}".strip()

    welcome_text = (
        f"Привіт, {full_name}! 😊\n\n"
        "Я бот, створений для тих, хто прагне поглибити свої знання Біблії. 📖 Моє завдання — допомогти вам скласти план читання Святого Письма "
        "та організувати цікаві вікторини, які зроблять цей процес ще більш захопливим! 📝🤓\n\n"
        "❗️Щоб спробувати план читання та взяти участь у вікторинах, перейдіть за цим посиланням: [t.me/PilgrimsOfFaith](https://t.me/PilgrimsOfFaith) 🔗\n\n"
        "Або натисніть кнопку: 'Долучитися до групи'\n\n"
        "Бажаю вам натхнення та приємного часу з Біблією! 🙏✨"
    )

    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)

    # Додавання кнопок для адміністратора
    if str(user_id) == ADMIN:
        start_game_button = types.KeyboardButton("Запустити гру")
        stop_game_button = types.KeyboardButton("Зупинити гру")
        publish_stats_button = types.KeyboardButton("Опублікувати статистику")
        publish_content_button = types.KeyboardButton("Опублікувати контент")
        get_stats_button = types.KeyboardButton("Отримати статистику публікацій")
        restart_bot_button = types.KeyboardButton("Перезавантажити бота")

        keyboard.add(start_game_button, stop_game_button)
        keyboard.add(publish_stats_button, publish_content_button)
        keyboard.add(get_stats_button)
        keyboard.add(restart_bot_button)
    else:
        join_group_button = types.KeyboardButton("Долучитися до групи")
        keyboard.add(join_group_button)

    # Відправка повідомлення з кнопкою
    bot.send_message(message.chat.id, welcome_text, reply_markup=keyboard)

# Обробник текстових повідомлень, що працює тільки в особистому чаті з ботом
@bot.message_handler(func=lambda message: message.chat.type == 'private')
def handle_private_message(message):
    global game_active, correct_answers

    user_id = message.from_user.id

    if message.text.strip() == "Запустити гру" and str(user_id) == ADMIN:
        start_game(message)

    elif message.text.strip() == "Зупинити гру" and str(user_id) == ADMIN:
        stop_game(message)

    elif message.text.strip() == "Опублікувати статистику" and str(user_id) == ADMIN:
        publish_quiz_statistics()

    elif message.text.strip() == "Опублікувати контент" and str(user_id) == ADMIN:
        manual_publish_reading_and_quizzes()

    elif message.text.strip() == "Отримати статистику публікацій" and str(user_id) == ADMIN:
        check_unpublished_content()

    elif message.text.strip() == "Перезавантажити бота" and str(user_id) == ADMIN:
        bot.send_message(message.chat.id, "Бот перезавантажується...")
        time.sleep(10)  # Додаємо затримку на 10 секунд
        restart_bot()

    elif message.text.strip() == "Долучитися до групи":
        bot.send_message(message.chat.id, "Перейдіть за цим посиланням, щоб долучитися до групи: [t.me/PilgrimsOfFaith](https://t.me/PilgrimsOfFaith)")

# Функція для перевірки часу і публікації контенту
def check_and_publish():
    now = datetime.now(kiev_timezone)
    current_time = now.strftime('%H:%M')

    # Публікація контенту
    if current_time in publish_times:
        manual_publish_reading_and_quizzes()

    # Публікація статистики
    if current_time == "23:00":
        publish_quiz_statistics()

    # Очищення даних вікторин
    if current_time == "00:00":
        reset_quiz_data()
        reset_user_data()
        publish_daily_quiz_statistics()
    publish_daily_quiz_statistics()

# Планувальник, який запускає перевірку кожну годину
def run_schedulers():
    while True:
        check_and_publish()

        # Отримуємо поточний час
        now = datetime.now(kiev_timezone)

        # Обчислюємо кількість секунд до наступної години
        next_hour = (now + timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)
        time_to_next_hour = (next_hour - now).total_seconds()

        # Очікуємо до наступної години
        time.sleep(time_to_next_hour)

# Функція для запуску бота з моніторингом помилок та перезавантаження
def run_bot():
    while True:
        try:
            bot.polling()
        except Exception as e:
            logger.error(f"Помилка при роботі бота: {e}")
            logger.info("Перезавантаження бота...")
            time.sleep(10)  # Додаємо затримку на 10 секунд
            restart_bot()

# Запуск бота, планувальника та Ініціалізація даних
# Для гри
correct_answers = load_answers()
used_answers = {}
user_scores = {}
game_active = False

#  Для плану читання та вікторин
load_stats_data()
user_data = load_data()
quiz_data = load_quiz_data()
reading_plan = load_reading_plan()
scheduler_thread = Thread(target=run_schedulers)
scheduler_thread.start()
check_unpublished_content()

# Запуск бота з моніторингом помилок та перезавантаження
run_bot()
