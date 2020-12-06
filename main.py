import telebot
import telebot.types as types

from settings import BOT_TOKEN, GEOCODE_APPID
from weather_info import WeatherInfo
from weather_service import *
from weather_service import OpenWeatherMapService, YandexWeatherService, AccuWeatherService

"""
inline - читаем название города -> перевод в координаты
обычный режим - просим местоположение -> сразу отправляем координаты
"""


class Bot:
    def __init__(self):
        self.bot = telebot.TeleBot(BOT_TOKEN, parse_mode=None)

        @self.bot.message_handler(commands=['start'])
        def _parse_start(message):
            self.parse_start(message)

        @self.bot.message_handler(content_types=['location'])
        def _handle_location(message):
            self.handle_location(message)

        @self.bot.inline_handler(lambda query: query.query)
        def _handle_query_text(inline_query):
            self.handle_query_text(inline_query)

    def run(self):
        self.bot.polling()

    @staticmethod
    def get_location_cityname(query):
        print(query.query)
        r = requests.get('https://api.opencagedata.com/geocode/v1/json',
                         params={'q': query.query,
                                 'key': GEOCODE_APPID,
                                 'language': 'ru'})
        return r.json()

    @staticmethod
    def get_location_coords(coords):
        print(coords)
        # TODO: f string to url + params
        r = requests.get(
            f'https://api.opencagedata.com/geocode/v1/json?q={coords[0]}%2C%20{coords[1]}&key={GEOCODE_APPID}&language=ru')
        return r.json()

    def handle_query_text(self, inline_query):
        try:
            res = self.get_location_cityname(inline_query)
            wi = WeatherInfo(coords=(res['results'][0]['annotations']['DMS']['lat'][:2],  # latitude
                                     res['results'][0]['annotations']['DMS']['lng'][:2]),  # longitude
                             services=[OpenWeatherMapService, YandexWeatherService, AccuWeatherService])
            forecast = wi.get_result()
            pprint_rep = f"Прогноз погоды на {DEFAULT_N_DAYS} дней:\n"
            for date in forecast:
                pprint_rep += f'{date}:\t{round(forecast[date], 2)}°C\n'
            answer = types.InlineQueryResultArticle('1',
                                                    'Прогноз погоды ☁',
                                                    types.InputTextMessageContent(pprint_rep))
            self.bot.answer_inline_query(inline_query.id, [answer])
        except Exception as e:
            print(e)

    def handle_location(self, message):
        res = self.get_location_coords((message.location.latitude, message.location.longitude))
        n_days = DEFAULT_N_DAYS
        keyboard = types.InlineKeyboardMarkup(row_width=1)
        day1_b = types.InlineKeyboardButton(text="Сегодня", callback_data='today')
        day3_b = types.InlineKeyboardButton(text="3 дня", callback_data='3day')
        day7_b = types.InlineKeyboardButton(text="Неделя", callback_data='week')
        keyboard.add(day1_b, day3_b, day7_b)
        if day1_b.callback_data == 'today':
            n_days = 1
        elif day3_b == '3day':
            n_days = 3
        print(n_days)
        self.bot.send_message(message.chat.id,
                              "Выбери период, для которого хотел(а) бы получить прогноз:\n",
                              reply_markup=keyboard)
        wi = WeatherInfo(coords=(res['results'][0]['annotations']['DMS']['lat'][:2],  # latitude
                                 res['results'][0]['annotations']['DMS']['lng'][:2]),  # longitude
                         services=[OpenWeatherMapService, YandexWeatherService, AccuWeatherService],
                         n_days=n_days)
        forecast = wi.get_result()
        pprint_rep = f"Прогноз погоды на {n_days} дней:\n"
        for date in forecast:
            pprint_rep += f'{date}:\t{round(forecast[date], 2)}°C\n'
        self.bot.send_message(message.chat.id, pprint_rep)

    def parse_start(self, message):
        self.bot.reply_to(message, "Привет 👋.\nЭтот бот поможет тебе узнать самую точную информацию о погоде.\n"
                                   "Мы собираем информацию сразу с нескольких ресурсов.\n")
        keyboard = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
        geo_butt = types.KeyboardButton(text="Отправить местоположение", request_location=True)
        keyboard.add(geo_butt)
        self.bot.send_message(message.chat.id,
                              "Пожалуйста, поделись своим местоположением:\n",
                              reply_markup=keyboard)


if __name__ == '__main__':
    bot = Bot()
    bot.run()
