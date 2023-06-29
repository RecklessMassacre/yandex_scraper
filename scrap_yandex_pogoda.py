import requests
import json
from bs4 import BeautifulSoup
from geopy.geocoders import Nominatim
from argparse import ArgumentParser


def main():
    base_url = "https://yandex.ru"
    url = r"https://yandex.ru/pogoda/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                      " (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,"
                  "*/*;q=0.8,application/signed-exchange;v=b3;q=0.7"
    }

    forecast = {}

    parser = ArgumentParser(description="Provides 3-days forecast in a given city")
    parser.add_argument("-c", default="Москва", help="City name. Can be written in russian", type=str)

    args = parser.parse_args()
    city = args.c

    # Пользуемся geopy для определения широты и долготы
    geolocator = Nominatim(user_agent="YPS")
    location = geolocator.geocode(city)
    if location is None:
        print(f"There's no such city as {city}. Or geopy failed to retrieve location")
        return

    # Запрос на главную страницу
    try:
        req = requests.get(url=url + f"?lat={location.latitude}&lon={location.longitude}&via=hnav", headers=headers)
    except Exception as e:
        print(f"Exception {e} has occurred during GET request. Shutting down the script")
        return

    scr = req.text
    soup = BeautifulSoup(scr, "lxml")

    title = soup.find(id="main_title").text  # Название Города и раойна

    # Забираем ссылку на прогноз на 10 дней
    days_link = soup.find(class_="link link_theme_normal forecast-briefly__header-button i-bem").get("href")
    if days_link is None:
        print(f"There is a problem with html you have received. Its missing the 10 days forecast link")
        return

    # Запрос на страницу с 10-дневным прогнозом
    try:
        req = requests.get(url=base_url + days_link, headers=headers)
    except Exception as e:
        print(f"Exception {e} has occurred during GET request. Shutting down the script")
        return

    scr = req.text
    soup = BeautifulSoup(scr, "lxml")

    # Парсим все необходимые данные со страницы
    try:
        days = [item.find_parent() for item in soup.find_all(class_="forecast-details__day")]
        for i, day in enumerate(days):
            day_number = day.find(class_="forecast-details__day-number").text
            day_month = day.find(class_="forecast-details__day-month").text
            date = day_number + " " + day_month

            table_rows = day.find_all(class_="weather-table__row")
            day_forecast = {}
            day_temp, night_temp = -300, -300
            for row in table_rows:
                humidity = row.find(class_="weather-table__body-cell weather-table__body-cell_type_humidity").text
                weather_type = row.find(class_="weather-table__body-cell weather-table__body-cell_type_condition").text
                wind_speed = row.find(class_="wind-speed").text
                wind_direction = row.find(class_="weather-table__wind-direction").text

                day_part = row.find(class_="weather-table__daypart").text
                if day_part == "днём":
                    weather_tab = row.find(class_="weather-table__body-cell weather-table__body-cell_type_daypart "
                                                  "weather-table__body-cell_wrapper")
                    day_temp = max([int(item.text) for item in weather_tab.find_all(class_="temp__value "
                                                                                           "temp__value_with-unit")])

                if day_part == "ночью":
                    weather_tab = row.find(class_="weather-table__body-cell weather-table__body-cell_type_daypart "
                                                  "weather-table__body-cell_wrapper")
                    night_temp = min([int(item.text) for item in weather_tab.find_all(class_="temp__value "
                                                                                             "temp__value_with-unit")])

                day_forecast[day_part] = {
                    "Влажность": humidity,
                    "Облачность": weather_type,
                    "Ветер": f"{wind_speed} м/с, {wind_direction}",
                }

            forecast[date] = [
                day_forecast,
                {"Максимальная температура днем": f"{day_temp} °C"},
                {"Минимальная температура ночью": f"{night_temp} °C"}
            ]

            # Так как нужно только 3 дня
            if i == 2:
                break

    except Exception as e:
        print(f"exception {e} has occurred during parsing data")
        return

    # Результат пакуем в json формат
    with open("forecast.json", "w") as f:
        json.dump({title: forecast}, f, indent=4, ensure_ascii=False)
        print("Done")


if __name__ == "__main__":
    main()
