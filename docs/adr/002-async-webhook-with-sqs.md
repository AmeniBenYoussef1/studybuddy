# ADR-002: Asynchronous processing with SQS

- **Status:** Accepted
- **Date:** 2026-10-13

## Context

Telegram expects the webhook to answer quickly and retries updates that fail or time out.
Answering a question will take several seconds (transcription, retrieval, model calls),
and some steps (voice, images) can take 10–30 seconds.

## Decision

Split the pipeline in two:

1. **Webhook Lambda** (API Gateway HTTP API): verifies the secret token, checks the allowlist,
   puts the update on an SQS queue and returns HTTP 200 in well under a second.
2. **Worker Lambda** (SQS trigger): does the slow work and replies through the Telegram Bot API.

Supporting choices:

- **Dead-letter queue** after 3 failed attempts, with a CloudWatch alarm.
- **Partial batch failure reporting**, so one bad message doesn't retry the whole batch.
- **Idempotency** with a DynamoDB conditional write on `update_id` (24 h TTL), because both
  Telegram and SQS can deliver the same update twice.

## Alternatives considered

- **One synchronous Lambda:** simpler, but slow answers would hit Telegram's timeout and
  trigger duplicate deliveries.
- **Step Functions:** better for long multi-step workflows; more cost and complexity than
  needed for v1.

## Consequences

- Fast, reliable acknowledgements; failures are visible (DLQ + alarm) instead of silent.
- One extra hop (SQS) adds a little latency, which is negligible compared with model calls.
