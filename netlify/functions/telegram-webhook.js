// Telegram sales bot webhook — no external dependencies, runs on Netlify Functions (Node 18+ runtime).
//
// Env vars required (set in Netlify site settings -> Environment variables):
//   TELEGRAM_BOT_TOKEN — token from @BotFather
//   ELENA_CHAT_ID       — Elena's numeric Telegram chat id (get it by messaging @userinfobot)
//
// After deploy, register the webhook once by visiting in a browser:
//   https://api.telegram.org/bot<TOKEN>/setWebhook?url=https://<your-site>.netlify.app/.netlify/functions/telegram-webhook

const CODEWORDS = ['ПРАКТИКУМ', 'ДИАГНОСТИКА', 'СИСТЕМА'];

const PITCH = `Здравствуйте! Расскажу коротко и по делу.

Практикум по системному мышлению — 14–16 сентября, 19:00 по Казахстану, 3 онлайн-вечера, 9 990 ₸.

Это для тех, кто застрял на месте — в личной ситуации, в работе с клиентами или в бизнесе — и хочет не очередную теорию, а разбор того, что конкретно повторяется у вас.

Хотите записаться — напишите, пожалуйста, ваше имя и номер телефона, и я передам их Елене.`;

const RELAY_CONFIRM = 'Спасибо! Передала ваше сообщение — Елена ответит вам лично.';

export default async (req) => {
  if (req.method !== 'POST') {
    return new Response('OK', { status: 200 });
  }

  const BOT_TOKEN = process.env.TELEGRAM_BOT_TOKEN;
  const ELENA_CHAT_ID = process.env.ELENA_CHAT_ID;

  if (!BOT_TOKEN) {
    return new Response('Missing TELEGRAM_BOT_TOKEN', { status: 500 });
  }

  let update;
  try {
    update = await req.json();
  } catch {
    return new Response('OK', { status: 200 });
  }

  const message = update.message;
  if (!message || !message.text) {
    return new Response('OK', { status: 200 });
  }

  const chatId = message.chat.id;
  const text = message.text.trim();
  const textUpper = text.toUpperCase();
  const matchedCodeword = CODEWORDS.find((w) => textUpper.includes(w));

  const apiUrl = `https://api.telegram.org/bot${BOT_TOKEN}/sendMessage`;

  async function send(toChatId, body) {
    await fetch(apiUrl, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ chat_id: toChatId, text: body }),
    });
  }

  if (matchedCodeword) {
    await send(chatId, PITCH);
  } else {
    const fromName = [message.from?.first_name, message.from?.last_name].filter(Boolean).join(' ') || 'Без имени';
    const username = message.from?.username ? `@${message.from.username}` : 'без username';
    if (ELENA_CHAT_ID) {
      await send(
        ELENA_CHAT_ID,
        `Новое сообщение от ${fromName} (${username}, chat_id: ${chatId}):\n\n${text}`
      );
    }
    await send(chatId, RELAY_CONFIRM);
  }

  return new Response('OK', { status: 200 });
};
