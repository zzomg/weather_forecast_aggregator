import time

import requests
import yandex_weather_api as yapi

from settings import OWM_APPID, YAN_APPID, ACCUW_APPID, DEFAULT_N_DAYS


class WeatherService:
    """
    Интерфейс для парсеров сайтов различных видов.
    """

    def get_info(self, coords: tuple, n_days: int) -> dict:
        """
        :param coords: [longitude, latitude] = [долгота, ширина] координаты юзера
        :param n_days: на какой период нужно предоставить прогноз
        :return: возвращает словарь с результатами {'date': 'temp'}.
         Во всех возвращаемых словарях даты _обязаны_ совпадать.
        """
        pass

# TODO: need catching exceptions with "try" when end limit of requests(Accu and maybe other)
# TODO: get also pressure and humidity


class OpenWeatherMapService(WeatherService):
    @staticmethod
    def date_converter(epoch_time):
        return time.strftime('%Y-%m-%d', time.localtime(epoch_time))

    def get_info(self, coords, n_days):
        r = requests.get('http://api.openweathermap.org/data/2.5/forecast/daily',
                               params={'lat': coords[0],
                                       'lon': coords[1],
                                       'appid': OWM_APPID,
                                       'cnt': n_days,
                                       'units': 'metric'})
        if r.status_code != requests.codes.ok:
            raise Exception("Unable to obtain data from OpenWeatherMap")
        res = r.json()
        forecast = {}
        for i in range(n_days):
            date = self.date_converter(float(res['list'][i]['dt']))
            temp_day = res['list'][i]['temp']['day']        # day temperature
            temp_night = res['list'][i]['temp']['night']    # night temperature
            forecast[date] = float((temp_day + temp_night)/2)
        return forecast


class YandexWeatherService(WeatherService):
    def get_info(self, coords, n_days):
        r = yapi.get(session=requests,
                     api_key=YAN_APPID,
                     rate='forecast',
                     lat=coords[0],
                     lon=coords[1],
                     limit=n_days)
        # TODO: проверка кода возврата запроса
        res = r.to_dict()
        forecast = {}
        for i in range(n_days):
            date = res['forecasts'][i]['date']
            temp_day = res['forecasts'][i]['parts']['day_short']['temp']        # day temperature
            temp_night = res['forecasts'][i]['parts']['night_short']['temp']    # night temperature
            forecast[date] = float((temp_day + temp_night)/2)
        return forecast


class AccuWeatherService(WeatherService):
    def get_info(self, coords, n_days):
        if n_days > 5:  # нам API больше не позволяет :)
            n_days = 5

        loc_req = requests.get(
            f'http://dataservice.accuweather.com/locations/v1/cities/geoposition/search?apikey={ACCUW_APPID}&q={coords[0]}%2C{coords[1]}')
        if loc_req.status_code != requests.codes.ok:
            raise Exception("Unable to obtain location from AccuWeather")
        loc_res = loc_req.json()
        loc_id = loc_res['Key']

        if n_days >= 1:
            r = requests.get(
                f'http://dataservice.accuweather.com/forecasts/v1/daily/5day/{loc_id}?apikey={ACCUW_APPID}&metric=true')
        else:
            r = requests.get(
                f'http://dataservice.accuweather.com/forecasts/v1/daily/1day/{loc_id}?apikey={ACCUW_APPID}&metric=true')
        if r.status_code != requests.codes.ok:
            raise Exception("Unable to obtain data from AccuWeather")
        res = r.json()

        forecast = {}
        for i in range(n_days):
            date = res['DailyForecasts'][i]['Date'][:10]
            temp_min = res['DailyForecasts'][i]['Temperature']['Minimum']['Value']  # min temperature
            temp_max = res['DailyForecasts'][i]['Temperature']['Maximum']['Value']  # max temperature
            forecast[date] = float((temp_max + temp_min)/2)

        return forecast


if __name__ == '__main__':
    ya = YandexWeatherService()
    ya.get_info((53, 83), DEFAULT_N_DAYS)
