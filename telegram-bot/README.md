# Telegram-продажник — что нужно сделать один раз

1. Получить токен бота через @BotFather в Telegram (команда /newbot).
2. Узнать свой numeric chat_id — написать боту @userinfobot, он пришлёт цифры.
3. Зайти на app.netlify.com -> Add new site -> Import an existing project -> GitHub -> выбрать репозиторий `praktikum-kaminskaya`, ветку `telegram-sales-bot`.
4. В настройках сайта (Site configuration -> Environment variables) добавить:
   - `TELEGRAM_BOT_TOKEN` = токен из шага 1
   - `ELENA_CHAT_ID` = число из шага 2
5. Deploy. После деплоя скопировать адрес сайта (например `https://xxxxx.netlify.app`).
6. Один раз открыть в браузере (подставив свой токен и адрес сайта):
   `https://api.telegram.org/bot<TOKEN>/setWebhook?url=https://<ваш-сайт>.netlify.app/.netlify/functions/telegram-webhook`

После этого бот работает сам: на кодовые слова ПРАКТИКУМ / ДИАГНОСТИКА / СИСТЕМА отвечает питчем практикума, всё остальное пересылает Елене напрямую в Telegram.
