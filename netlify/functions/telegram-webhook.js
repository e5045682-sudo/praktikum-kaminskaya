// Telegram sales bot webhook — AI-driven, reads live instructions from a public Google Doc on every message.
// Runs on Netlify Functions (Node 18+ runtime).
//
// Env vars required (Netlify site settings -> Environment variables):
//   TELEGRAM_BOT_TOKEN  — token from @BotFather
//   ELENA_CHAT_ID        — Elena's numeric Telegram chat id (from @userinfobot)
//   ANTHROPIC_API_KEY    — Claude API key (console.anthropic.com -> API Keys)
//
// The sales script lives in a public Google Doc (edit it any time — no redeploy needed):
//   https://docs.google.com/document/d/1CLNgI1qkDGfn7VAmxitI0HLzGnEcFSK18CLk96LLRUo/edit
//
// Broadcast: everyone who has ever messaged the bot is remembered (Netlify Blobs).
// Elena can send "/рассылка <текст>" (or "/broadcast <текст>") from her own chat with
// the bot to message everyone who has written in before — Telegram bots cannot message
// people who never started a conversation with them first.

import { getStore } from '@netlify/blobs';

const INSTRUCTIONS_URL = 'https://docs.google.com/document/d/1CLNgI1qkDGfn7VAmxitI0HLzGnEcFSK18CLk96LLRUo/export?format=txt';

const FALLBACK_INSTRUCTIONS = 'Скрипт временно недоступен. Отвечай кратко и вежливо, скажи что передашь вопрос Елене лично.';

function usersStore() {
  return getStore('bot-users');
}

async function rememberUser(chatId, meta) {
  try {
    const store = usersStore();
    const existing = await store.get(String(chatId));
    if (!existing) {
      await store.setJSON(String(chatId), meta);
    }
  } catch {
    // best-effort — don't block replies if Blobs is unavailable
  }
}

async function listUserChatIds() {
  try {
    const { blobs } = await usersStore().list();
    return blobs.map((b) => b.key);
  } catch {
    return [];
  }
}

async function fetchInstructions() {
  try {
    const r = await fetch(INSTRUCTIONS_URL);
    if (!r.ok) return FALLBACK_INSTRUCTIONS;
    const t = await r.text();
    return t && t.trim() ? t : FALLBACK_INSTRUCTIONS;
  } catch {
    return FALLBACK_INSTRUCTIONS;
  }
}

function buildSystemPrompt(instructions) {
  return `Ты — продажник практикума Елены Каминской «Системное мышление» (системные бизнес-расстановки), отвечаешь лидам в Telegram.

Ведёшь диалог строго по инструкции ниже — она обновляется вживую, следуй именно ей, а не своим общим знаниям о продажах.

Правила:
- Отвечай по-русски, коротко (2–5 предложений), как в живой переписке — без markdown, без звёздочек, без списков.
- Не начинай с цены — сначала диагностика по инструкции.
- Никогда не обещай гарантированный результат.
- Никогда не совмещай в одном сообщении обещание про личные изменения и про доход.
- Если вопрос выходит за рамки инструкции, или ситуация нестандартная — прямо скажи, что передашь вопрос Елене лично, и не выдумывай ответ.

--- ИНСТРУКЦИЯ (скрипт продаж) ---
${instructions}`;
}

export default async (req) => {
  if (req.method !== 'POST') {
    return new Response('OK', { status: 200 });
  }

  const BOT_TOKEN = process.env.TELEGRAM_BOT_TOKEN;
  const ELENA_CHAT_ID = process.env.ELENA_CHAT_ID;
  const ANTHROPIC_API_KEY = process.env.ANTHROPIC_API_KEY;

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

  const apiUrl = `https://api.telegram.org/bot${BOT_TOKEN}/sendMessage`;

  async function send(toChatId, body) {
    await fetch(apiUrl, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ chat_id: toChatId, text: body }),
    });
  }

  const fromName = [message.from?.first_name, message.from?.last_name].filter(Boolean).join(' ') || 'Без имени';
  const username = message.from?.username ? `@${message.from.username}` : 'без username';

  await rememberUser(chatId, { name: fromName, username, firstSeen: new Date().toISOString() });

  const isFromElena = ELENA_CHAT_ID && String(chatId) === String(ELENA_CHAT_ID);
  const broadcastMatch = text.match(/^\/(?:рассылка|broadcast)\s+([\s\S]+)/i);

  if (isFromElena && broadcastMatch) {
    const broadcastText = broadcastMatch[1].trim();
    const chatIds = await listUserChatIds();
    let sentCount = 0;
    for (const id of chatIds) {
      if (String(id) === String(ELENA_CHAT_ID)) continue;
      try {
        await send(id, broadcastText);
        sentCount++;
        await new Promise((r) => setTimeout(r, 60));
      } catch {
        // skip failed sends (e.g. user blocked the bot)
      }
    }
    await send(ELENA_CHAT_ID, `Рассылка отправлена: ${sentCount} из ${chatIds.length - 1} получателей.`);
    return new Response('OK', { status: 200 });
  }

  if (ELENA_CHAT_ID) {
    await send(
      ELENA_CHAT_ID,
      `Лид ${fromName} (${username}, chat_id: ${chatId}) написал:\n\n${text}`
    );
  }

  if (!ANTHROPIC_API_KEY) {
    await send(chatId, 'Спасибо! Передала ваше сообщение — Елена ответит вам лично.');
    return new Response('OK', { status: 200 });
  }

  const instructions = await fetchInstructions();
  const systemPrompt = buildSystemPrompt(instructions);

  let reply = 'Спасибо! Передала ваше сообщение — Елена ответит вам лично.';
  try {
    const aiResp = await fetch('https://api.anthropic.com/v1/messages', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'x-api-key': ANTHROPIC_API_KEY,
        'anthropic-version': '2023-06-01',
      },
      body: JSON.stringify({
        model: 'claude-sonnet-5',
        max_tokens: 400,
        system: systemPrompt,
        messages: [{ role: 'user', content: text }],
      }),
    });
    const data = await aiResp.json();
    if (data && data.content && data.content[0] && data.content[0].text) {
      reply = data.content[0].text;
    }
  } catch {
    // keep fallback reply
  }

  await send(chatId, reply);

  return new Response('OK', { status: 200 });
};
