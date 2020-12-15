import telebot
import telebot.types as types

from settings import BOT_TOKEN, GEOCODE_APPID
from weather_info import WeatherInfo
from weather_service import *
from weather_service import OpenWeatherMapService, YandexWeatherService, AccuWeatherService

from db import User, Service, UserService, session

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

        @self.bot.message_handler(commands=['q'])
        def _getting_forecast_quickly_(message):
            self.getting_forecast_quickly(message)

        @self.bot.message_handler(content_types=['location'])
        def _handle_location(message):
            if session.query(User).filter_by(tg_id=message.from_user.id).first().state == 1:
                self.setting_city(message)
            else:
                self.handle_location(message)

        @self.bot.message_handler(content_types=['text'])
        def _handle_text(message):
            if session.query(User).filter_by(tg_id=message.from_user.id).first().state == 1:
                coords = self.get_location_cityname(message.text)
                message.location = types.Location(coords[1], coords[0])
                self.setting_city(message)

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
    def get_location_cityname(city):
        print(city)
        r = requests.get('https://api.opencagedata.com/geocode/v1/json',
                         params={'q': city,
                                 'key': GEOCODE_APPID,
                                 'language': 'ru'})
        res = r.json()
        return res['results'][0]['geometry']['lat'], res['results'][0]['geometry']['lng']

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

        self.bot.send_message(message.from_user.id, "Меню:", reply_markup=keyboard)

    def handle_query_text(self, inline_query):
        try:
            wi = WeatherInfo(coords=self.get_location_cityname(inline_query.query),
                             services=TEST_SERVICES)
            forecast = wi.get_result()
            answer = types.InlineQueryResultArticle('1',
                                                    'Прогноз погоды ☁',
                                                    types.InputTextMessageContent(self.get_formatted_weather(forecast)))
            self.bot.answer_inline_query(inline_query.id, [answer])
        except Exception as e:
            print(e)

    def parse_start(self, message):

        u = session.query(User).filter_by(tg_id=message.from_user.id).first()
        if u is None:
            u = User(tg_id=message.from_user.id, latitude=0, longitude=0, days_num=1, state=0)
            s = session.query(Service).filter_by(id=1).first()
            us = UserService(user=u, service=s)

            session.add(u)
            session.add(us)
            session.commit()

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
                ret = types.InlineKeyboardButton(text="<-", callback_data='settings menu')
                keyboard.add(sc, sd, ss, ret)

                self.bot.send_message(call.from_user.id, "Изменить настройки:", reply_markup=keyboard)

            if data == 'settings menu':
                self.send_menu(call)

            if data == 'settings city':
                u = session.query(User).filter_by(tg_id=call.from_user.id).first()
                u.state = 1
                session.add(u)
                session.commit()

                keyboard = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
                geo_butt = types.KeyboardButton(text="Отправить местоположение 🗾", request_location=True)
                keyboard.add(geo_butt)
                self.bot.send_message(call.from_user.id, "Нажмите эту кнопку или введите название города.",
                                      reply_markup=keyboard)

            if data.startswith('settings days'):
                if data == 'settings days':
                    keyboard = types.InlineKeyboardMarkup(row_width=1)
                    s1 = types.InlineKeyboardButton(text="1", callback_data='settings days 1')
                    s3 = types.InlineKeyboardButton(text="3", callback_data='settings days 3')
                    s7 = types.InlineKeyboardButton(text="7", callback_data='settings days 7')
                    ret = types.InlineKeyboardButton(text="<-", callback_data='settings')
                    keyboard.add(s1, s3, s7, ret)

                    self.bot.send_message(call.from_user.id, "Задать количество дней:", reply_markup=keyboard)
                else:
                    n_days = int(data.split(' ')[-1])

                    u = session.query(User).filter_by(tg_id=call.from_user.id).first()
                    u.days_num = n_days
                    session.add(u)
                    session.commit()

                    self.bot.send_message(call.from_user.id, "Количество дней успешно изменено.",
                                          reply_markup=types.ReplyKeyboardRemove())
                    self.send_menu(call)

            if data.startswith('settings sites'):
                if data == 'settings sites':
                    keyboard = types.InlineKeyboardMarkup(row_width=1)

                    al = session.query(Service).all()
                    all_sites = {site.id: site.name for site in session.query(Service).all()}
                    u = session.query(User).filter_by(tg_id=call.from_user.id).first()
                    user_sites = [site.service_id for site in session.query(UserService).filter_by(user=u)]

                    for s_id, name in all_sites.items():
                        keyboard.add(types.InlineKeyboardButton(text=f"{name[:-7]}{'✅' if s_id in user_sites else '✖'}",
                                                                callback_data='settings sites ' + str(s_id)))

                    ret = types.InlineKeyboardButton(text="<-", callback_data='settings')
                    keyboard.add(ret)

                    self.bot.send_message(call.from_user.id, "Задать сайты для агрегирования:", reply_markup=keyboard)
                else:
                    s_id = int(data.split(' ')[-1])
                    us = session.query(UserService).filter_by(service_id=s_id).first()

                    if us is None:
                        u = session.query(User).filter_by(tg_id=call.from_user.id).first()
                        # s = session.query(Service).filter_by(id=s_id)
                        us = UserService(user=u, service_id=s_id)
                        session.add(us)
                        mess = "Сайт успешно добавлен."
                    else:
                        session.delete(us)
                        mess = "Сайт успешно удалён."
                    session.commit()

                    self.bot.send_message(call.from_user.id, mess)
                    self.send_menu(call)

    def setting_city(self, message):
        u = session.query(User).filter_by(tg_id=message.from_user.id).first()
        u.latitude = message.location.latitude
        u.longitude = message.location.longitude
        u.state = 0
        session.add(u)
        session.commit()

        self.bot.send_message(message.from_user.id, "Город успешно изменён.", reply_markup=types.ReplyKeyboardRemove())
        self.send_menu(message)

    def getting_forecast_quickly(self, message):
        u = session.query(User).filter_by(tg_id=message.from_user.id).first()
        if u.latitude == 0:
            self.bot.send_message(message.from_user.id, "Сначала задайте город в настройках.")
            self.send_menu(message)
        else:

            services = []
            for s in u.user_services:
                services.append(globals()[s.service.name])
            wi = WeatherInfo(coords=(u.latitude, u.longitude),
                             services=services,
                             n_days=u.days_num)
            forecast = wi.get_result()
            self.bot.send_message(message.chat.id, self.get_formatted_weather(forecast),
                                  reply_markup=types.ReplyKeyboardRemove())
            self.send_menu(message)


if __name__ == '__main__':
    bot = Bot()
    bot.run()
