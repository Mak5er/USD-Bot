import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
import re


def fetch_page_content(url):
    """Завантажує HTML-контент сторінки з рандомним User-Agent."""
    try:
        ua = UserAgent()
        headers = {
            'User-Agent': ua.random,
            'Accept-Language': 'en-US,en;q=0.9',
            'Referer': 'https://www.google.com/',
        }
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.text
    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"Помилка при завантаженні сторінки: {e}")


def parse_exchange_section(soup):
    """Знаходить секцію 'exchange module-attachment'."""
    exchange_section = soup.find('section', class_='exchange module-attachment')
    if not exchange_section:
        raise ValueError("Секція 'exchange module-attachment' не знайдена.")
    return exchange_section


def parse_container(exchange_section):
    """Знаходить контейнер 'container' у секції."""
    container = exchange_section.find('div', class_='container')
    if not container:
        raise ValueError("Контейнер 'container' не знайдений.")
    return container


def parse_tab_section(container):
    """Знаходить секцію з класом 'module-exchange__tab'."""
    tab_section = container.find('div', class_='module-exchange__tab')
    if not tab_section:
        raise ValueError("Секція з класом 'module-exchange__tab' не знайдена.")
    return tab_section


def parse_online_list(tab_section):
    """Знаходить список 'module-exchange__list--online' у секції."""
    online_list = tab_section.find('ul', class_='module-exchange__list--online')
    if not online_list:
        raise ValueError("Список з класом 'module-exchange__list--online' не знайдений.")
    return online_list


def parse_first_item(online_list):
    """Отримує текст першого елемента 'module-exchange__item' зі списку."""
    first_item = online_list.find('li', class_='module-exchange__item')
    if not first_item:
        raise ValueError("Елемент з класом 'module-exchange__item' не знайдений.")
    return first_item.get_text(strip=True)


def extract_prices(data):
    """Витягує значення після 'Купівля online' та 'Продаж online'."""
    buy_online_match = re.search(r"Купівля online([\d.]+)", data)
    sell_online_match = re.search(r"Продаж online([\d.]+)", data)

    buy_online = buy_online_match.group(1) if buy_online_match else "Невідомо"
    sell_online = sell_online_match.group(1) if sell_online_match else "Невідомо"

    return buy_online, sell_online


def get_prices():
    url = "https://ukrsibbank.com/currency-cash/"
    try:
        # Завантажуємо HTML-контент
        html_content = fetch_page_content(url)

        # Парсимо HTML за допомогою BeautifulSoup
        soup = BeautifulSoup(html_content, 'html.parser')

        # Крок 1: Знаходимо секцію 'exchange module-attachment'
        exchange_section = parse_exchange_section(soup)

        # Крок 2: Знаходимо контейнер 'container'
        container = parse_container(exchange_section)

        # Крок 3: Знаходимо секцію 'module-exchange__tab'
        tab_section = parse_tab_section(container)

        # Крок 4: Знаходимо список 'module-exchange__list--online'
        online_list = parse_online_list(tab_section)

        # Крок 5: Отримуємо текст першого елемента 'module-exchange__item'
        first_item_data = parse_first_item(online_list)

        # Крок 6: Витягуємо значення після 'Купівля online' і 'Продаж online'
        buy_online, sell_online = extract_prices(first_item_data)

        # Виводимо результат
        return {"buy_price": float(buy_online), "sell_price": float(sell_online)}

    except (RuntimeError, ValueError) as e:
        return e
