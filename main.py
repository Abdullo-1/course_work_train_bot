import random
import telebot
from telebot import types
import requests
import os
from dotenv import load_dotenv
from telebot.types import ReplyKeyboardMarkup, ReplyKeyboardRemove

load_dotenv()
token = os.getenv('TOKEN')
exercise = os.getenv('API_KEY')
spoon = os.getenv('API_SPOON')

bot = telebot.TeleBot(token)

profiles = {}
history = {}

HEADERS = {
    "X-RapidAPI-Key": exercise,
    "X-RapidAPI-Host": "exercisedb.p.rapidapi.com"
}

MUSCLES = {
    "Грудь":"chest",
    "Спина":"back",
    "Ноги":"upper legs",
    "Руки":"upper arms",
    "Плечи":"shoulders",
    "Пресс":"waist"
}

def get_exercises_api(body_part, num=3):
    url = f"https://exercisedb.p.rapidapi.com/exercises/bodyPart/{body_part}?limit=150"
    res = requests.get(url, headers=HEADERS).json()
    if not isinstance(res, list):
        return []
    return random.sample(res, min(num, len(res)))


def generate_workout_week_api(chat_id):
    profile = profiles[chat_id]
    program = profile["program"]
    goal = profile["goal"]

    days = ["Понедельник","Вторник","Среда","Четверг","Пятница"]
    week_plan = {}

    for day in days:
        exercises = []
        if program == "Full Body":
            for muscle in MUSCLES.values():
                exercises.extend(get_exercises_api(muscle, num=1))
        else:
            if day in ["Понедельник","Среда","Пятница"]:
                muscles_today = random.sample(list(MUSCLES.values()), 3)
                for m in muscles_today:
                    exercises.extend(get_exercises_api(m, num=2))
            else:
                continue


        week_plan[day] = exercises


    text = f"Твоя программа ({goal}/{program}):\n\n"
    for day, ex_list in week_plan.items():
        text += f"{day}:\n"
        for ex in ex_list:
            text += f" - {ex['name']}\n"
        text += "\n"

    bot.send_message(chat_id, text)

@bot.message_handler(commands=['start'])
def start_bot(message):
    user = profiles.get(message.chat.id)
    if not user:
        profiles[message.chat.id] = {}
        bot.send_message(message.chat.id, "Привет! Давай создадим твой профиль.\nВведите свой возраст:")
        bot.register_next_step_handler(message, profile_age)
        return

    bot.send_message(message.chat.id,
                     f"С возвращением! Твой профиль уже сохранён.\n"
                     f"Возраст: {user.get('age')}\n"
                     f"Вес: {user.get('weight')} кг\n"
                     f"Рост: {user.get('height')} см\n"
                     f"Цель: {user.get('goal')}\n"
                     f"Программа: {user.get('program')}\n\n"
                     f"Список команд: /help")


def profile_age(message):

    try:
        age = int(message.text)
        profiles[message.chat.id] = {"age": age}
        bot.send_message(message.chat.id, "Теперь введи свой вес (кг):")
        bot.register_next_step_handler(message, profile_weight)
    except:
        bot.send_message(message.chat.id, "Введи возраст числом!")
        bot.register_next_step_handler(message, profile_age)


def profile_weight(message):
    try:
        weight = float(message.text)
        profiles[message.chat.id]["weight"] = weight
        bot.send_message(message.chat.id, "Теперь введи свой рост (см):")
        bot.register_next_step_handler(message, profile_height)
    except:
        bot.send_message(message.chat.id, "Введи вес числом!")
        bot.register_next_step_handler(message, profile_weight)


def profile_height(message):
    try:
        height = float(message.text)
        profiles[message.chat.id]["height"] = height
        bot.send_message(message.chat.id, "Отлично! Теперь выбери цель.")
        choose_goal(message)
    except:
        bot.send_message(message.chat.id, "Введи рост числом!")
        bot.register_next_step_handler(message, profile_height)


def choose_goal(message):
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add("Похудение", "Набор массы", "Поддержание")
    bot.send_message(message.chat.id, "Выбери цель:", reply_markup=keyboard)
    bot.register_next_step_handler(message, save_goal)


def save_goal(message):
    profiles[message.chat.id]["goal"] = message.text

    choose_program_type(message)


def choose_program_type(message):
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add("Full Body", "Split")
    bot.send_message(message.chat.id, "Выбери программу:", reply_markup=keyboard)
    bot.register_next_step_handler(message, save_program)


def save_program(message):
    profiles[message.chat.id]["program"] = message.text
    bot.send_message(message.chat.id, "Генерирую твою тренировочную неделю...",reply_markup=ReplyKeyboardRemove())
    generate_workout_week_api(message.chat.id)

    bot.register_next_step_handler(message, lambda msg: generate_workout_week_api(msg.chat.id))

@bot.message_handler(commands=['help'])
def com_help(message):
    bot.send_message(message.chat.id,"/start - Запустить фитнес тренера\n"
                                     "/random - Случайная тренировка\n"
                                     "/muscle - Выбрать мышцу\n"
                                     "/full - Тренировка на все тело\n"
                                     "/history - История тренировок\n"
                                     "/advice - Совет дня\n"
                                     "/gif - ГИФ для упражнений\n"
                                     "/bmi - Расчет ИМТ\n"
                                     "/mealplan - План питания"
                                     "/profile - Профиль")

@bot.message_handler(commands=['gif'])
def request_exercises_gif(message):
    bot.send_message(message.chat.id, "Напиши названия упражнений через запятую (до 6):")
    bot.register_next_step_handler(message, send_exercises_gifs)

def send_exercises_gifs(message):
    exercises_list = [ex.strip() for ex in message.text.split(',') if ex.strip()]

    if not exercises_list:
        bot.send_message(message.chat.id, "Не введено ни одного упражнения!")
        return

    exercises_list = exercises_list[:6]

    for ex_name in exercises_list:
        get_and_send_gif(message.chat.id, ex_name)

def get_and_send_gif(chat_id, ex_name):
    ex_name_clean = ex_name.strip().lower()
    url = f"https://exercisedb.p.rapidapi.com/exercises/name/{ex_name_clean}"

    try:
        res = requests.get(url, headers=HEADERS).json()
    except Exception as e:
        bot.send_message(chat_id, f"Ошибка запроса API: {e}")
        return

    if not isinstance(res, list) or not res:
        bot.send_message(chat_id, f"Упражнение '{ex_name}' не найдено")
        return


    exercise_data = res[0]
    send_ex_gif(chat_id, exercise_data)

@bot.message_handler(commands=['random'])
def random_training(message):
    muscle = random.choice(list(MUSCLES.values()))
    url = f"https://exercisedb.p.rapidapi.com/exercises/bodyPart/{muscle}?limit=150"

    res = requests.get(url, headers=HEADERS).json()

    if not isinstance(res, list):
        print(res)
        bot.send_message(message.chat.id,"API вернул ошибку")
        return

    workout = random.sample(res, 3)
    text = "Рандомная тренировка:\n\n"
    for w in workout:
        text += f"{w['name']}\n"


    save_history(message.chat.id, workout)
    bot.send_message(message.chat.id, text)

    for ex in workout:
        send_ex_gif(message.chat.id, ex)

@bot.message_handler(commands=['muscle'])
def train_muscle(message):
    keyboard = types.ReplyKeyboardMarkup()
    for muscle in MUSCLES.keys():
        keyboard.add(muscle)
    bot.send_message(message.chat.id,"Выбери группу мышц: ",reply_markup=keyboard)
    bot.register_next_step_handler(message, select_muscle)

def select_muscle(message):
    name = message.text
    if name not in MUSCLES:
        bot.send_message(message.chat.id,"Такой группы мышц нет,выбери другую командой /muscle",reply_markup=ReplyKeyboardRemove())
        return

    muscle = MUSCLES[name]

    url = f"https://exercisedb.p.rapidapi.com/exercises/bodyPart/{muscle}?limit=20"
    res = requests.get(url, headers=HEADERS).json()

    if not isinstance(res, list):
        bot.send_message(message.chat.id,"API вернул ошибку")
        print(res)
        return

    workout = random.sample(res, 3)
    text = f"Тренировка: {name}\n\n"

    for ex in workout:
        text += f"{ex['name']}\n"

    save_history(message.chat.id, workout)

    bot.send_message(message.chat.id,text,reply_markup=ReplyKeyboardRemove())

    for ex in workout:
        send_ex_gif(message.chat.id, ex)


@bot.message_handler(commands=['full'])
def train_full(message):
    workout = []
    for name, muscle in MUSCLES.items():
        url = f"https://exercisedb.p.rapidapi.com/exercises/bodyPart/{muscle}?limit=150"
        resp = requests.get(url, headers=HEADERS).json()

        ex = random.choice(resp)
        workout.append(ex)

    text = "Тренировка на все тело: \n\n"

    for ex in workout:
        text += f"{ex['name']} ({ex['target']})\n"

    save_history(message.chat.id, workout)

    bot.send_message(message.chat.id,text)

    for ex in workout:
        send_ex_gif(message.chat.id, ex)

@bot.message_handler(commands=['history'])
def train_history(message):
    user_history = history.get(message.chat.id, [])
    if not user_history:
        bot.send_message(message.chat.id, "Тренировок нет")
        return

    text = "История последних тренировок:\n\n"


    for idx, workout in enumerate(user_history[-10:], 1):
        if not workout or not isinstance(workout, list):
            continue


        exercise_names = [ex.get("name", "Неизвестное") for ex in workout if isinstance(ex, dict)]
        if exercise_names:
            text += f"{idx}. {', '.join(exercise_names)}\n"

    bot.send_message(message.chat.id, text)



@bot.message_handler(commands=['advice'])
def train_advice(message):
    adv = [
        "Пей больше воды",
        "Ешь много белка",
        "Сон важнее,чем ты думаешь",
        "Не тренируй одну группу мышц каждый день",
        "Держи спину ровной при каждом упражнении"
    ]
    bot.send_message(message.chat.id,random.choice(adv))


@bot.message_handler(commands=['mealplan'])
def meal_plan(message):
    chat_id = message.chat.id
    profile = profiles.get(chat_id)

    if not profile or "weight" not in profile or "height" not in profile or "goal" not in profile:
        bot.send_message(chat_id, "Сначала нужно заполнить профиль командой /start")
        return

    goal = profile["goal"]
    weight = profile["weight"]
    height = profile["height"]
    age = profile.get("age", 25)


    bmi = weight / ((height/100)**2)
    if goal == "похудение":
        cal = int(2000 - 300)
    elif goal == "набор массы":
        cal = int(2000 + 300)
    else:
        cal = 2000

    bot.send_message(chat_id, f"Твой дневной калораж примерно: {cal} ккал.\nВот примерный план питания:")

    for meal_type in ["breakfast", "lunch", "dinner"]:
        url = f"https://api.spoonacular.com/recipes/complexSearch?query={meal_type}&number=1&apiKey={spoon}"
        res = requests.get(url).json()

        if not res.get("results"):
            bot.send_message(chat_id, f"Блюдо для {meal_type} не найдено")
            continue

        recipe = res["results"][0]
        title = recipe.get("title")
        image = recipe.get("image")
        link = f"https://spoonacular.com/recipes/{'-'.join(title.lower().split())}-{recipe.get('id')}"

        bot.send_photo(chat_id, photo=image, caption=f"{meal_type.title()}: {title}\nСсылка: {link}")



def send_ex_gif(chat_id, ex):
    exercise_id = ex.get("id")
    name = ex.get("name","Упражнения")
    if not exercise_id:
        bot.send_message(chat_id,f"ID упражнения не найден для {name}")
        return

    resolution = "360"
    gif_url = f"https://exercisedb.p.rapidapi.com/image?exerciseId={exercise_id}&resolution={resolution}&rapidapi-key={exercise}"

    try:
        bot.send_animation(chat_id,gif_url,caption=name)
    except Exception as e:
        bot.send_message(chat_id,f"Не удалось отправить GIF: {e}")

def save_history(user_id, workout):
    if user_id not in history:
        history[user_id] = []
    history[user_id].append(workout)

bot.polling(none_stop=True)