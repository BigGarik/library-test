# Library Management System

REST API для управления библиотекой на FastAPI с JWT аутентификацией.

## Требования

- Python 3.9+
- PostgreSQL
- pip

## Установка и запуск

### 1. Клонирование и установка зависимостей
```bash
git clone <repository>
cd library-test
pip install -r requirements.txt
```

### 2. Настройка БД
```bash
# Создайте .env файл на основе .env.example
cp .env.example .env

# Отредактируйте .env с вашими данными PostgreSQL
DB_HOST=localhost
DB_PORT=5432
DATABASE=library_db
DB_USER=postgres
DB_PASSWORD=your_password
SECRET_KEY=your_secret_key_here
```

### 3. Миграции
```bash
alembic upgrade head
```

### 4. Запуск
```bash
uvicorn main:app --reload
```

API доступен по адресу: `http://localhost:8000`
Документация: `http://localhost:8000/docs`

### 5. Регистрация первого пользователя
```bash
curl -X POST "http://localhost:8000/auth/register" \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@library.com", "password": "password123"}'
```

## Структура проекта

```
app/
├── database/          # Подключение к БД
├── models/           # SQLAlchemy модели
├── schemas/          # Pydantic схемы
├── routes/           # API роуты
├── services/         # Бизнес-логика
├── utils/            # Вспомогательные функции
└── settings.py       # Конфигурация

alembic/              # Миграции БД
tests/                # Тесты
```

## Архитектура БД

### Принятые решения:

**1. Таблицы:**
- `users` - пользователи системы (JWT аутентификация)
- `books` - каталог книг
- `readers` - читатели библиотеки
- `borrowed_books` - журнал выдач/возвратов

**2. Ключевые решения:**
- **Разделение users и readers** - пользователи системы отдельно от читателей библиотеки
- **Мягкое удаление в borrowed_books** - return_date NULL = активная выдача
- **Constraint на copies** - количество экземпляров >= 0
- **Уникальные индексы** - email читателей, ISBN книг

### Схема связей:
```
books ──┐
        ├── borrowed_books ──── readers
users ──┘
```

## Реализация бизнес-логики

### Сложности и решения:

**4.1 Контроль количества экземпляров:**
- **Проблема:** Конкурентные запросы могут привести к отрицательному количеству
- **Решение:** Проверка `copies >= 1` перед выдачей + транзакции
- **Реализация:** `check_book_availability()` в `services/circulation.py`

**4.2 Лимит 3 книги на читателя:**
- **Проблема:** Подсчет активных выдач
- **Решение:** Запрос `WHERE return_date IS NULL` + проверка лимита
- **Реализация:** `check_borrow_limit()` подсчитывает невозвращенные книги

**4.3 Контроль возврата:**
- **Проблема:** Предотвращение повторного возврата
- **Решение:** Поиск записи с `return_date IS NULL`
- **Реализация:** `check_borrow_record()` проверяет существование активной выдачи

### Архитектурные решения:
- **Слой services** - вынос бизнес-логики из роутов
- **Атомарные операции** - все изменения в одной транзакции
- **Валидация на разных уровнях** - Pydantic + бизнес-правила

## Система аутентификации

### Технологии:
- **JWT токены** (библиотека `python-jose`)
- **Bcrypt** для хеширования паролей
- **OAuth2PasswordBearer** для извлечения токенов

### Принципы:
```python
# Генерация токена
access_token = jwt.encode(
    {"sub": user_id, "exp": expire_time}, 
    SECRET_KEY, 
    algorithm="HS256"
)

# Проверка токена
payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
```

### Защищенные эндпоинты:
- **Все CRUD операции** - требуют аутентификации
- **Публичный доступ** - только GET `/books/` (просмотр каталога)
- **Middleware** - `get_current_user()` dependency

### Почему JWT:
- Stateless - не требует хранения сессий
- Масштабируемость - подходит для микросервисов
- Простота - стандартный подход для REST API

## API Endpoints

### Аутентификация
- `POST /auth/register` - регистрация
- `POST /auth/login` - получение токена

### Книги
- `GET /books/` - список книг (публичный)
- `POST /books/` - добавить книгу 🔒
- `GET /books/{id}` - получить книгу 🔒
- `PUT /books/{id}` - обновить книгу 🔒
- `DELETE /books/{id}` - удалить книгу 🔒

### Читатели
- `GET /readers/` - список читателей 🔒
- `POST /readers/` - добавить читателя 🔒
- `GET /readers/{id}` - получить читателя 🔒
- `PUT /readers/{id}` - обновить читателя 🔒
- `DELETE /readers/{id}` - удалить читателя 🔒

### Выдача/возврат
- `POST /circulation/borrow` - выдать книгу 🔒
- `POST /circulation/return` - вернуть книгу 🔒
- `GET /circulation/{reader_id}` - книги читателя 🔒

🔒 - требует аутентификации

## Тестирование

```bash
# Установка тестовых зависимостей
pip install -r test_requirements.txt

# Запуск тестов
pytest tests/
```

## Дополнительная фича: Система бронирования

### Идея:
Читатели могут забронировать книгу, если все экземпляры выданы.

### Реализация:
```python
# Новая таблица
class BookReservation(Base):
    book_id: int
    reader_id: int 
    reservation_date: datetime
    expires_at: datetime  # 7 дней на получение
    status: enum  # ACTIVE, FULFILLED, EXPIRED
```

### Бизнес-логика:
1. **При выдаче** - проверить очередь бронирований
2. **При возврате** - уведомить следующего в очереди
3. **Автоматическое истечение** - celery task для очистки просроченных
4. **Уведомления** - email/SMS при доступности книги

### Новые endpoints:
- `POST /reservations/` - забронировать книгу
- `GET /reservations/my` - мои бронирования
- `DELETE /reservations/{id}` - отменить бронь

Это добавит справедливый механизм распределения популярных книг и улучшит пользовательский опыт.