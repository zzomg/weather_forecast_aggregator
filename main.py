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


ALL_SERVICES = [OpenWeatherMapService, YandexWeatherService, AccuWeatherService]
TEST_SERVICES = [OpenWeatherMapService]


class Bot:
    def __init__(self):
        self.bot = telebot.TeleBot(BOT_TOKEN, parse_mode=None)

        @self.bot.message_handler(commands=['start'])
        def _parse_start(message):
            self.parse_start(message)

        @self.bot.message_handler(commands=['menu'])
        def _menu(message):
            self.send_menu(message)

        @self.bot.message_handler(content_types=['location'])
        def _handle_location(message):
            self.handle_location(message)

        @self.bot.inline_handler(lambda query: query.query)
        def _handle_query_text(inline_query):
            self.handle_query_text(inline_query)

        @self.bot.callback_query_handler(lambda call: call.data.startswith("location"))
        def _location_callback_(call):
            self.location_callback(call)

        @self.bot.callback_query_handler(lambda call: call.data.startswith("settings"))
        def _settings_callback_(call):
            self.settings_callback(call)

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

    @staticmethod
    def get_formatted_weather(forecast_dict):
        pprint_rep = f"Прогноз погоды на {len(forecast_dict)} дней:\n"
        for date in forecast_dict:
            pprint_rep += f'{date}:\t{round(forecast_dict[date], 2)}°C\n'

        return pprint_rep

    def send_menu(self, message):
        keyboard = types.InlineKeyboardMarkup(row_width=1)
        geo_butt = types.InlineKeyboardButton(text="Отправить местоположение 🗾", callback_data='location set')
        settings_butt = types.InlineKeyboardButton(text="Изменить настройки 🔧", callback_data='settings')
        keyboard.add(geo_butt, settings_butt)

        self.bot.send_message(message.chat.id, "Меню:", reply_markup=keyboard)

    def handle_query_text(self, inline_query):
        try:
            res = self.get_location_cityname(inline_query)
            # TODO: need full coordinates(int -> double) res['results'][0]['geometry']
            wi = WeatherInfo(coords=(res['results'][0]['annotations']['DMS']['lat'][:2],  # latitude
                                     res['results'][0]['annotations']['DMS']['lng'][:2]),  # longitude
                             services=TEST_SERVICES)
            forecast = wi.get_result()
            answer = types.InlineQueryResultArticle('1',
                                                    'Прогноз погоды ☁',
                                                    types.InputTextMessageContent(self.get_formatted_weather(forecast)))
            self.bot.answer_inline_query(inline_query.id, [answer])
        except Exception as e:
            print(e)

    def parse_start(self, message):

        keyboard = types.InlineKeyboardMarkup(row_width=1)
        geo_butt = types.InlineKeyboardButton(text="Отправить местоположение 🗾", callback_data='location set')
        settings_butt = types.InlineKeyboardButton(text="Изменить настройки 🔧", callback_data='settings')
        keyboard.add(geo_butt, settings_butt)
        self.bot.reply_to(message, "Привет 👋.\nЭтот бот поможет тебе узнать самую точную информацию о погоде.\n"
                                   "Мы собираем информацию сразу с нескольких ресурсов.\n", reply_markup=keyboard)

    def handle_location(self, message):

        coords = f"{message.location.latitude} {message.location.longitude}"

        keyboard = types.InlineKeyboardMarkup(row_width=1)
        day1_b = types.InlineKeyboardButton(text="Сегодня", callback_data='location today ' + coords)
        day3_b = types.InlineKeyboardButton(text="3 дня", callback_data='location 3day ' + coords)
        day7_b = types.InlineKeyboardButton(text="Неделя", callback_data='location week ' + coords)
        keyboard.add(day1_b, day3_b, day7_b)

        self.bot.send_message(message.chat.id,
                              "Выбери период, для которого хотел(а) бы получить прогноз:\n",
                              reply_markup=keyboard)

    def location_callback(self, call):
        if call.message:
            if call.data == 'location set':
                keyboard = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
                geo_butt = types.KeyboardButton(text="Отправить местоположение 🗾",
                                                request_location=True)
                keyboard.add(geo_butt)
                self.bot.send_message(call.message.chat.id, "Нажмите эту кнопку или прикрепите местоположение",
                                      reply_markup=keyboard)
                return

            days, lat, lng = call.data.split(" ")[1:]
            n_days = DEFAULT_N_DAYS

            if days == 'today':
                n_days = 1
            elif days == '3day':
                n_days = 3
            elif days == 'week':
                n_days = 7

            print(n_days)

            wi = WeatherInfo(coords=(lat, lng),
                             services=TEST_SERVICES,
                             n_days=n_days)
            forecast = wi.get_result()
            self.bot.send_message(call.message.chat.id, self.get_formatted_weather(forecast),
                                  reply_markup=types.ReplyKeyboardRemove())
            self.send_menu(call.message)

    def settings_callback(self, call):
        if call.message:
            data = call.data
            if data == 'settings':
                keyboard = types.InlineKeyboardMarkup(row_width=1)
                sc = types.InlineKeyboardButton(text="Задать город", callback_data='settings city')
                sd = types.InlineKeyboardButton(text="Задать количество дней", callback_data='settings days')
                ss = types.InlineKeyboardButton(text="Задать сайты для аггрегирования", callback_data='settings sites')
                keyboard.add(sc, sd, ss)

                self.bot.send_message(call.message.chat.id, "Изменить настройки:", reply_markup=keyboard)


if __name__ == '__main__':
    bot = Bot()
    bot.run()
