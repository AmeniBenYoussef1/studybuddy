# ADR-001: Telegram first, WhatsApp later

- **Status:** Accepted
- **Date:** 2026-10-13

## Context

StudyBuddy needs a chat channel that supports text, voice notes, photos and files.
The project that inspired it (marceloacosta/multimodal-whatsapp-bot-aws) uses WhatsApp.

## Decision

Build v1 on Telegram. Add WhatsApp as a second channel in v2.

## Alternatives considered

| Option | Pros | Cons |
| --- | --- | --- |
| **Telegram Bot API** | Bot created in 2 minutes via BotFather; free; no business verification; webhooks with a secret token | Fewer users than WhatsApp in some countries |
| WhatsApp Cloud API | Most-used messenger | Needs a Meta developer app and business setup; test numbers have limits; per-conversation pricing rules |
| AWS End User Messaging (WhatsApp) | AWS-native | Same Meta prerequisites, more setup |

## Consequences

- Week 1 can focus on the AWS architecture instead of channel onboarding.
- The channel code is isolated in `src/shared/telegram.py` and the webhook, so a WhatsApp
  adapter can be added later without touching the agent.
