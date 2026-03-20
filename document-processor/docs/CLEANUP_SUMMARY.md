# Environment Configuration Reference

This document describes the environment variables used by the document processor.
**Never commit real secrets.** Copy from `env.example` and fill in your values locally.

## AWS Configuration

- `AWS_ACCESS_KEY_ID` — Your AWS access key
- `AWS_SECRET_ACCESS_KEY` — Your AWS secret key
- `AWS_REGION` — e.g. us-east-1
- `S3_BUCKET_NAME` — S3 bucket for document storage
- `SQS_QUEUE_URL` — SQS queue URL for PDF processing
- `SQS_DLQ_URL` — Dead-letter queue URL

## LlamaCloud Configuration

- `LLAMA_CLOUD_API_KEY` — Get from https://cloud.llamaindex.ai/api-key

## OpenAI Configuration

- `OPENAI_API_KEY` — Get from https://platform.openai.com/api-keys

## PostgreSQL Configuration

- `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_DB`
- `POSTGRES_USER`, `POSTGRES_PASSWORD`

## Redis Configuration

- `REDIS_HOST`, `REDIS_PORT`, `REDIS_DB`, `REDIS_PASSWORD`

## Application Configuration

- `STORAGE_PATH`, `MAX_FILE_SIZE_MB`, `MAX_FILES_PER_REQUEST`
- `RATE_LIMIT_REQUESTS`, `RATE_LIMIT_WINDOW`
- `TASK_RESULT_TTL`
