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
            'Accept-Language': 'uk-UA,uk;q=0.9',
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


def parse_first_item(online_list, index=0):
    """Отримує текст вказаного елемента 'module-exchange__item' зі списку.
    За замовчуванням повертає перший елемент (USD), якщо index=1, повертає другий елемент (EUR)."""
    items = online_list.find_all('li', class_='module-exchange__item')
    if not items or len(items) <= index:
        raise ValueError(f"Елемент з класом 'module-exchange__item' з індексом {index} не знайдений.")
    return items[index].get_text(strip=True)


def extract_prices(data):
    """Витягує значення після 'Купівля online', 'Продаж online' та 'НБУ'."""
    # Перевіряємо, чи це євро
    if data.startswith("EUR"):
        # Євро формат: наприклад "EURЄвро46.6546.4547.3947.4547.00"
        # Витягуємо всі числа з даних
        all_numbers = re.findall(r"\d{2}\.\d{2}", data)

        if len(all_numbers) >= 5:
            # Перше, третє і п'яте число згідно з вимогами
            buy_online = all_numbers[0]  # Перше число (46.65)
            sell_online = all_numbers[2]  # Третє число (47.39)
            nbu = all_numbers[4]  # П'яте число (47.00) - курс НБУ
        else:
            buy_online = "Невідомо"
            sell_online = "Невідомо"
            nbu = "Невідомо"
    else:
        # Стандартний формат для долара
        buy_online_match = re.search(r"Купівля online([\d.]+)", data)
        sell_online_match = re.search(r"Продаж online([\d.]+)", data)
        nbu_match = re.search(r"НБУ([\d.]+)", data)

        buy_online = buy_online_match.group(1) if buy_online_match else "Невідомо"
        sell_online = sell_online_match.group(1) if sell_online_match else "Невідомо"
        nbu = nbu_match.group(1) if nbu_match else "Невідомо"

    return buy_online, sell_online, nbu


def get_prices(currency_index=0):
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

        # Крок 5: Отримуємо текст елемента 'module-exchange__item' за індексом
        item_data = parse_first_item(online_list, currency_index)

        # Крок 6: Витягуємо значення після 'Купівля online', 'Продаж online' та 'НБУ'
        buy_online, sell_online, nbu = extract_prices(item_data)

        # Виводимо результат
        return {"buy_price": float(buy_online), "sell_price": float(sell_online), "nbu_price": float(nbu)}

    except (RuntimeError, ValueError) as e:
        print(f"Помилка при отриманні курсів валют: {e}")
        return e


def get_usd_prices():
    """Функція, що повертає курси для USD (індекс 0)"""
    return get_prices(currency_index=0)


def get_eur_prices():
    """Функція, що повертає курси для EUR (індекс 1)"""
    return get_prices(currency_index=1)
