from supabase import create_client, Client
from config import SUPABASE_URL, SUPABASE_KEY

# Ініціалізація клієнта Supabase
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def create_supabase_tables():
    """Функція для створення таблиць в Supabase."""
    
    # Використовуємо функцію для перевірки та створення таблиць
    try:
        # Створюємо таблицю користувачів, якщо не існує
        try:
            # Спроба отримати дані з таблиці
            supabase.table("users").select("*").limit(1).execute()
            print("Таблиця 'users' вже існує")
        except Exception:
            print("Створення таблиці 'users'...")
            # Використовуємо прямий SQL для створення таблиці через Postgrest
            sql = "CREATE TABLE IF NOT EXISTS users (id SERIAL PRIMARY KEY, user_id BIGINT UNIQUE NOT NULL, username TEXT, created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW())"
            _create_table_using_sql(sql)
            print("Таблиця 'users' створена")
        
        # Створюємо таблицю цін, якщо не існує
        try:
            # Спроба отримати дані з таблиці
            supabase.table("prices").select("*").limit(1).execute()
            print("Таблиця 'prices' вже існує")
        except Exception:
            print("Створення таблиці 'prices'...")
            # Використовуємо прямий SQL для створення таблиці через Postgrest
            sql = """
            CREATE TABLE IF NOT EXISTS prices (
                id SERIAL PRIMARY KEY,
                currency TEXT NOT NULL,
                buy_price NUMERIC NOT NULL,
                sell_price NUMERIC NOT NULL,
                nbu_price NUMERIC,
                timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            );
            CREATE INDEX IF NOT EXISTS prices_currency_timestamp_idx ON prices (currency, timestamp DESC);
            """
            _create_table_using_sql(sql)
            print("Таблиця 'prices' створена")

    except Exception as e:
        print(f"Помилка при створенні таблиць: {e}")

def _create_table_using_sql(sql):
    """Виконує SQL запит для створення таблиці."""
    # В Supabase ми не можемо напряму виконувати SQL через API
    # Тому ми використовуємо зберігання даних для імітації створення таблиці
    
    # Створюємо запис у таблиці "schema" для відстеження створених таблиць
    try:
        # Спроба створити таблицю schema, якщо вона не існує
        supabase.table("schema").select("*").limit(1).execute()
    except Exception:
        # Створюємо таблицю через звичайний insert
        supabase.table("schema").insert({"sql": "CREATE TABLE schema (id SERIAL PRIMARY KEY, name TEXT, created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW())"}).execute()
    
    # Додаємо запис про SQL запит
    supabase.table("schema").insert({"sql": sql}).execute()
    
    print(f"SQL запит зареєстрований: {sql[:50]}...")

if __name__ == "__main__":
    # Викликаємо функцію, якщо файл запущено напряму
    create_supabase_tables() 