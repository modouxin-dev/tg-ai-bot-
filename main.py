"""
Telegram AI Bot - 双模型（Groq / Gemini）可切换
部署到 Render（Web Service + Webhook 模式）

环境变量：
  TELEGRAM_TOKEN   Telegram Bot Token
  GROQ_API_KEY     Groq API Key
  GEMINI_API_KEY   Gemini API Key
"""

import os
import json
import urllib.request

# ---------- 从环境变量读取凭证 ----------
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

# ---------- 模型配置 ----------
GROQ_MODEL = "llama-3.3-70b-versatile"
GEMINI_MODEL = "gemini-2.0-flash"

USER_MODEL = {}

# ---------- 工具函数 ----------
def tg_call(method, data):
    url = "https://api.telegram.org/bot{}/{}".format(TELEGRAM_TOKEN, method)
    body = json.dumps(data).encode("utf-8")
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def tg_send_message(chat_id, text):
    if len(text) > 4000:
        text = text[:4000] + "\n...(截断)"
    return tg_call("sendMessage", {"chat_id": chat_id, "text": text})


def groq_chat(messages):
    url = "https://api.groq.com/openai/v1/chat/completions"
    data = json.dumps({
        "model": GROQ_MODEL,
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 1000,
    }).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={
        "Content-Type": "application/json",
        "Authorization": "Bearer {}".format(GROQ_API_KEY),
    })
    with urllib.request.urlopen(req, timeout=60) as resp:
        result = json.loads(resp.read().decode("utf-8"))
    return result["choices"][0]["message"]["content"]


def gemini_chat(messages):
    contents = []
    system = ""
    for m in messages:
        if m["role"] == "system":
            system = m["content"]
        elif m["role"] == "user":
            contents.append({"role": "user", "parts": [{"text": m["content"]}]})
        elif m["role"] == "assistant":
            contents.append({"role": "model", "parts": [{"text": m["content"]}]})

    url = ("https://generativelanguage.googleapis.com/v1beta/models/"
           "{}:generateContent?key={}".format(GEMINI_MODEL, GEMINI_API_KEY))
    payload = {"contents": contents}
    if system:
        payload["systemInstruction"] = {"parts": [{"text": system}]}

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        result = json.loads(resp.read().decode("utf-8"))
    return result["candidates"][0]["content"]["parts"][0]["text"]


def call_model(chat_id, messages):
    model = USER_MODEL.get(chat_id, "groq")
    if model == "gemini":
        return gemini_chat(messages)
    return groq_chat(messages)


SYSTEM_PROMPT = "你是一个简洁、友好、靠谱的 AI 助手，用中文回答。"


def handle_message(update):
    message = update.get("message")
    if not message:
        return

    chat_id = message["chat"]["id"]
    text = message.get("text", "").strip()

    if text.startswith("/"):
        cmd = text.split()[0].lower()
        if cmd == "/start":
            tg_send_message(chat_id, "你好！我是 AI 助手\n\n"
                             "直接发消息即可对话。\n"
                             "/groq 切换到 Groq\n"
                             "/gemini 切换到 Gemini\n"
                             "/model 查看当前模型")
        elif cmd in ("/groq", "/gemini"):
            model = cmd[1:]
            USER_MODEL[chat_id] = model
            tg_send_message(chat_id, "已切换到 {}".format(model.upper()))
        elif cmd == "/model":
            m = USER_MODEL.get(chat_id, "groq")
            tg_send_message(chat_id, "当前模型：{}".format(m.upper()))
        else:
            tg_send_message(chat_id, "未知命令，可用 /start 查看帮助")
        return

    try:
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": text},
        ]
        reply = call_model(chat_id, messages)
        tg_send_message(chat_id, reply)
    except Exception as e:
        tg_send_message(chat_id, "出错了：{}".format(e))


def webhook(event):
    body = event.get("body", "{}")
    update = json.loads(body)
    handle_message(update)
    return {"statusCode": 200, "body": "ok"}


from flask import Flask, request
app = Flask(__name__)


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        update = request.get_json()
        handle_message(update)
    return "ok"


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)