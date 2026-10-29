# Telegram AI Bot（双模型 Groq / Gemini）

一个跑在 Render 免费层上的 Telegram 机器人，支持 Groq 和 Gemini 两个模型切换。

## 功能
- /start 查看帮助
- /groq 切换到 Groq
- /gemini 切换到 Gemini
- /model 查看当前模型
- 直接发消息即可对话

## 部署到 Render
1. 连接 GitHub 仓库
2. Build Command: pip install -r requirements.txt
3. Start Command: gunicorn main:app --workers 1 --bind 0.0.0.0:$PORT
4. 配置环境变量 TELEGRAM_TOKEN / GROQ_API_KEY / GEMINI_API_KEY

## 设置 Webhook
https://api.telegram.org/bot<TOKEN>/setWebhook?url=https://xxx.onrender.com