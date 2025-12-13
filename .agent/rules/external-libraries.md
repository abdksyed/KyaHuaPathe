---
trigger: always_on
---

We use `python-telegram-bot` for creating telegram bots, use the docs and APIs from `https://docs.python-telegram-bot.org/en/stable/telegram.bot.html`. You must always get the documentation from this when doing anything on telegram.

We also use Gemini API for AI related features, the API reference is here: https://ai.google.dev/api
Also for Gemini models, DO NOT USE older models, always use `gemini-flash-latest`.

We will use cerebras and groq for other models to speed, they are compatible with OpenAI chat completion api, here is cerebras docs https://inference-docs.cerebras.ai/api-reference/chat-completions and here is groq docs https://console.groq.com/docs/api-reference. We will mostly use GPT OSS 120B, `gpt-oss-120b` for cerebras and `openai/gpt-oss-120b` for groq.

We will be using Google Agent Development Kit (Google ADK) for managing different agents, tools etc. Docs: https://google.github.io/adk-docs/ Python API Referene: https://google.github.io/adk-docs/api-reference/python/