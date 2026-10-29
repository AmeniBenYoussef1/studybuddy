# StudyBuddy: notes for Claude Code

Multimodal AI study assistant on Telegram, built on AWS by Ameni as a portfolio project.
The full specification lives in the "StudyBuddy – Specification" doc; this file holds what you
need while coding.

## Layout

- `src/shared/` config, JSON logging, Telegram client and update parsing
- `src/webhook/` API Gateway → verify secret, allowlist, enqueue to SQS, return 200 fast
- `src/worker/` SQS consumer: dedup in DynamoDB, build reply, send to Telegram
- `infra/` CDK app (Python), single stack `StudyBuddy`, region eu-north-1
- `tests/` unittest-style tests, run with `pytest`
- `scripts/` PowerShell: deploy, set-token, set-webhook, logs, destroy
- `docs/adr/` architecture decision records

## Rules

- Lambda code uses only the standard library + boto3 (bundled in the runtime). Ask before adding
  a dependency; if one is needed, add bundling in CDK.
- Never put secrets in code, logs or Git. The bot token lives in Secrets Manager.
- Logic that must never be wrong (access control, quotas, deletion, citation format) is plain
  code with unit tests, not prompts.
- Keep costs low: serverless only, no NAT gateway, no OpenSearch Serverless, Claude Haiku by
  default. Total project budget is about $40.
- Every change: tests pass (`pytest`), `ruff check .` and `mypy` clean.
- Significant design choices get a new ADR in `docs/adr/`.
- The owner is learning: explain what each AWS change does before running it.

## Roadmap

1. Week 1 (done): Telegram → API Gateway → webhook → SQS → worker → reply.
2. Week 2: Strands agent on Bedrock AgentCore (Claude Haiku), system prompt, commands. Replace
   `worker.respond` with an agent call.
3. Week 3: voice (Transcribe in, Polly out), photos (Claude vision), hints-first for exercises.
4. Week 4: PDF/PPTX ingestion → Titan embeddings → S3 Vectors; cited answers; AgentCore Memory.
5. Week 5: quizzes, /forget, quotas, Bedrock Guardrails, Nova Canvas images, observability.
6. Week 6: eval sets, model comparison, CI eval gate, README results, demo video.
