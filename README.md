# 🎵 Music Stream Recommender Bot

Telegram-бот, который помогает менеджерам и клиентам подобрать музыкальный поток
для бизнеса. Задаёт 3 вопроса (тип бизнеса → темп → вокал) и возвращает топ-10
подходящих потоков из каталога.

База — 99 потоков из таблицы «Шаблонные потоки (все тарифы)», вкладка «Комфорт РФ».

## Структура

```
.
├── bot.py            # основная логика (aiogram 3, FSM)
├── data.py           # потоки и категории
├── requirements.txt  # зависимости
├── .env.example      # пример настроек
└── README.md
```

## Запуск локально

1. **Получите токен бота:**
   - Откройте Telegram, найдите `@BotFather`
   - Команда `/newbot`, придумайте имя и username
   - Скопируйте полученный токен

2. **Подготовьте окружение:**
   ```bash
   python3.11 -m venv venv
   source venv/bin/activate           # macOS / Linux
   # venv\Scripts\activate            # Windows
   pip install -r requirements.txt
   ```

3. **Настройте `.env`:**
   ```bash
   cp .env.example .env
   # откройте .env и впишите ваш токен в BOT_TOKEN
   ```

4. **Запустите:**
   ```bash
   python bot.py
   ```

5. В Telegram откройте своего бота и нажмите Start.

## Деплой в облаке (бесплатные варианты)

### Вариант A — Render.com

1. Зарегистрируйтесь на [render.com](https://render.com)
2. New → Background Worker → Connect a GitHub repo (или Public Git)
3. Build Command: `pip install -r requirements.txt`
4. Start Command: `python bot.py`
5. Environment → добавьте переменную `BOT_TOKEN` со значением вашего токена
6. Deploy

### Вариант B — Fly.io

1. Установите [flyctl](https://fly.io/docs/hands-on/install-flyctl/)
2. В директории проекта:
   ```bash
   fly launch                       # сгенерирует fly.toml, нажимайте N на постгрес/редис
   fly secrets set BOT_TOKEN=ваш_токен
   fly deploy
   ```

### Вариант C — VPS / собственный сервер

```bash
git clone <ваш репозиторий>
cd music-stream-bot
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
echo "BOT_TOKEN=ваш_токен" > .env
# запуск через systemd / supervisor / pm2 / tmux
python bot.py
```

Пример systemd-юнита (`/etc/systemd/system/music-bot.service`):

```ini
[Unit]
Description=Music Stream Telegram Bot
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/music-stream-bot
EnvironmentFile=/home/ubuntu/music-stream-bot/.env
ExecStart=/home/ubuntu/music-stream-bot/venv/bin/python bot.py
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable music-bot
sudo systemctl start music-bot
sudo journalctl -u music-bot -f      # логи
```

## Как работает алгоритм подбора

При выборе пользователем параметров каждый поток получает score:

| Совпадение           | Баллы |
|----------------------|-------|
| Бизнес точно подходит | +4    |
| Бизнес = «универсальное» (fallback) | +1 |
| Бизнес не подходит   | поток исключается полностью |
| Темп совпадает       | +2    |
| Темп = «разный»      | +1    |
| Темп не совпадает    | −1    |
| Вокал совпадает      | +2    |
| Вокал = «и так, и так» | +1  |
| Вокал не совпадает   | −1    |

Дальше сортировка по сумме баллов, показ топ-10.

## Команды бота

- `/start` — начать подбор
- `/reset` — то же самое, начать заново
- `/help` — справка

## Что можно добавить позже

- Постер/превью потока (Yandex Disk ссылки уже есть в исходной таблице — колонка D)
- Прямая ссылка на поток в каталоге
- Жанры (фильтр и теги)
- Аналитика: какие комбинации запрашивают чаще
- Подбор по другим вкладкам (Тематические, КЗ, РБ, РАО, Базовый)
- Автоматическая синхронизация с Google Sheets (через API, чтобы данные обновлялись)

## Обновление данных

Сейчас потоки лежат в `data.py` как список словарей. Чтобы обновить:

1. Откройте `data.py`
2. Найдите нужный поток по `id` или название
3. Поправьте поля (`b` — бизнесы, `t` — темп, `v` — вокал)
4. Перезапустите бота

Если потоков станет больше — можно перейти на чтение из Google Sheets API
или из локального JSON/CSV.
