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

bot = telebot.TeleBot(token)

profiles = {}

HEADERS = {
    "X-RapidAPI-Key": exercise,
    "X-RapidAPI-Host": "exercisedb.p.rapidapi.com"
}

history = {}

MUSCLES = {
    "Грудь":"chest",
    "Спина":"back",
    "Ноги":"upper legs",
    "Руки":"upper arms",
    "Плечи":"shoulders",
    "Пресс":"waist"
}

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.send_message(message.chat.id,"Привет я твой фитнес тренер\n"
                                     "Список команд /help")

@bot.message_handler(commands=['help'])
def com_help(message):
    bot.send_message(message.chat.id,"/start - Запустить фитнес тренера\n"
                                     "/random - Случайная тренировка\n"
                                     "/muscle - Выбрать мышцу\n"
                                     "/full - Тренировка на все тело\n"
                                     "/history - История тренировок\n"
                                     "/advice - Совет дня\n"
                                     "/bmi - Расчет ИМТ\n"
                                     "/profile - Профиль")

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
        bot.send_message(message.chat.id,"Такой группы мышц нет,выбери другую командой /muscle")
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
    user = history.get(message.chat.id ,[])
    if not user:
        bot.send_message(message.chat.id,"Тренировок нет")
        return

    text = "История тренировок: \n\n"
    for num,w in enumerate(user[-10:],1):
        if not w or not isinstance(w, list):
            continue

        names = [exercise["name"] for exercise in w if isinstance(exercise, dict) and "name" in exercise]
        if names:
            text += f"{num}. {','.join(names)}\n"

    bot.send_message(message.chat.id,text)



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


@bot.message_handler(commands=['bmi'])
def body_bmi(message):
    bot.send_message(message.chat.id,"Введи свой вес в кг:")
    bot.register_next_step_handler(message, bmi_weight)

def bmi_weight(message):
    try:
        weight = float(message.text)
        bot.send_message(message.chat.id,"Введи свой рост в см:")
        bot.register_next_step_handler(message, bmi_height,weight)
    except:
        bot.send_message(message.chat.id,"Введи число!")
        bot.register_next_step_handler(message, bmi_weight)

def bmi_height(message, weight):
    try:
        height = float(message.text) / 100
        bmi = weight / (height ** 2)

        if bmi < 18.5:
            category = "Недостаток веса"
        elif bmi < 25:
            category = "Норма"
        elif bmi < 30:
            category = "Лишний вес"
        else:
            category = "Лишний вес"

        bot.send_message(message.chat.id,f"Твой ИМТ:{bmi:.1f}\nКатегория:{category}")
    except:
        bot.send_message(message.chat.id,"Введи число!")
        bot.register_next_step_handler(message, bmi_height, weight)


@bot.message_handler(commands=['profile'])
def profiless(message):
    p = profiles.get(message.chat.id)

    keyboard = types.ReplyKeyboardMarkup()
    btn = types.KeyboardButton("Изменить профиль")
    keyboard.add(btn)

    if not p or "age" not in p or "weight" not in p or "height" not in p:
        profiles[message.chat.id] = {}
        bot.send_message(message.chat.id,"Профиль пуст,введи возраст:", reply_markup=keyboard)

        bot.register_next_step_handler(message, profile_age)
        return


    bot.send_message(message.chat.id,f"Твой профиль:\n"
                                         f"Возраст: {p['age']}\n"
                                         f"Вес: {p['weight']}кг\n"
                                         f"Рост: {p['height']}см",
                         reply_markup=keyboard)


@bot.message_handler(func=lambda msg: msg.text == "Изменить профиль")
def ch_profile(message):
    profiles[message.chat.id] = {}
    bot.send_message(message.chat.id,"Профиль сброшен,введи возраст:",reply_markup=ReplyKeyboardRemove())
    bot.register_next_step_handler(message, profile_age)



def profile_age(message):
    try:
        age = int(message.text)
        profiles[message.chat.id] = {"age":age}
        bot.send_message(message.chat.id,"Теперь введи свой вес(кг):")
        bot.register_next_step_handler(message, profile_weight)
    except:
        bot.send_message(message.chat.id,"Введи возраст числом!")
        bot.register_next_step_handler(message, profile_age)

def profile_weight(message):
    try:
        weight = float(message.text)
        profiles[message.chat.id]["weight"] = float(message.text)
        bot.send_message(message.chat.id,"Теперь введи свой рост(см):")
        bot.register_next_step_handler(message, profile_height)
    except:
        bot.send_message(message.chat.id,"Введи рост числом!")
        bot.register_next_step_handler(message, profile_weight)

def profile_height(message):
    try:
        profiles[message.chat.id]["height"] = float(message.text)
        bot.send_message(message.chat.id,"Профиль сохранен")
    except:
        bot.send_message(message.chat.id,"Введи число!")
        bot.register_next_step_handler(message, profile_height)




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