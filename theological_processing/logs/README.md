# Processing Logs

This directory contains logs from the theological text processing pipeline.

## Log Files

- `processing.log` - Main processing log with timestamps and stage information
- `errors.log` - Error logs for failed processing attempts
- `approvals.log` - Human approval tracking

## Log Format

```
TIMESTAMP | STAGE | SOURCE_FILE → CHUNK_COUNT → OUTPUT_FILE
2024-01-15T10:30:00 | CHUNKED | orthodoxy.xml → 45 chunks → ORTHODOXY_CHEST_chunks.jsonl
2024-01-15T10:35:00 | ANNOTATED | ORTHODOXY_CHEST_chunks.jsonl → 45 chunks → ORTHODOXY_CHEST_annotated.jsonl
```
