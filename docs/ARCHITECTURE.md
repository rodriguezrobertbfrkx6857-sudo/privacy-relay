# Architecture and extension points

## Data flow

```mermaid
flowchart LR
    UserText --> EntityDetection
    EntityDetection --> OverlapResolution
    OverlapResolution --> EphemeralVault
    EphemeralVault --> ProtectedText
    ProtectedText --> OptionalLocalModel
    OptionalLocalModel --> OutputDLP
    OutputDLP --> ExplicitRestore
    EphemeralVault --> ExplicitRestore
    TTLOrRevoke --> DestroyMapping
```

## Module boundaries

`app/main.py` owns Pydantic contracts and HTTP behavior. The domain module owns scoring, retrieval, authorization, evaluation or privacy state. `app/platform.py` owns bounded HTTP bodies, local trust checks, metadata audit persistence and frontend mounting. The React workbench is a client of the same public API documented by FastAPI.

SQLite transactions use parameterized queries and close their connections at scope exit. WAL is selected for local read/write concurrency. Domain state and audit records are separate concerns: the audit append is not generally atomic with a domain state change. Deploy one process for Privacy Relay's in-memory vault.

## Decisions

| Decision | Reason | Tradeoff |
| --- | --- | --- |
| Small independent repository | Easy to clone, review, run and extend | Common workbench infrastructure is duplicated |
| FastAPI + React | Typed request validation and familiar full-stack interfaces | Shared types are not code-generated yet |
| SQLite | Zero external service and deterministic fixtures | Not a high-throughput multi-tenant design |
| Offline default | Reproducible demos without credentials or paid inference | Does not prove behavior of a live model |
| Inspectable algorithms | Failures can be explained during review | Baselines have documented recall/precision limits |

## Extension plan

1. 接入多语言 NER 与 Presidio 类识别器，建立按实体类型划分的精确率/召回率基准。
2. 使用独立加密 vault、密钥轮换和租户身份约束，支持多实例并发与严格定时销毁。
3. 增加敏感字段的数据流追踪、结构化 JSON 处理和跨工具输出策略。

Before implementing an extension, define its acceptance metric, failure budget and comparison baseline. Keep transport errors separate from successful defenses and keep external validation data separate from development fixtures.
