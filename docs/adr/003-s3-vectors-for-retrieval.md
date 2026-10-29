# ADR-003: S3 Vectors for retrieval (planned for week 4)

- **Status:** Proposed
- **Date:** 2026-10-13

## Context

StudyBuddy answers from the user's course material, so it needs a vector store.
The infrastructure runs in eu-north-1 (Stockholm) on an AWS Free Plan account with a
small budget (about $40 for the project).

## Decision

Store embeddings (Amazon Titan Text Embeddings V2) in **Amazon S3 Vectors** and implement
retrieval ourselves, instead of using Amazon Bedrock Knowledge Bases.

## Reasons

- Bedrock Knowledge Bases is not offered in eu-north-1 (to be re-checked in the console
  before week 4).
- Amazon OpenSearch Serverless, a common Knowledge Bases backend, has a minimum monthly
  charge even when idle, which does not fit the budget.
- S3 Vectors is pay-per-use, so the idle cost stays close to $0.
- Writing chunking and retrieval ourselves makes the RAG pipeline visible and testable.

## Consequences

- More code to own: chunking, metadata filters (per user / shared space), citations.
- Retrieval quality must be measured with the eval set (chunk size, top-k experiments).
