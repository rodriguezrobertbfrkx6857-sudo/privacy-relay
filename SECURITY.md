# Security model

## Intended scope

Privacy Relay is a single-user, local research workbench. Bind to loopback. Code publication on GitHub does not deploy a public service. Host/origin checks reduce browser-to-local attacks but do not provide user authentication. Except for Agent Permit's role-separated routes, APIs are local and unauthenticated. Before shared deployment, add identity, authorization, TLS, quotas, retention and tenant isolation.

## Trust boundaries

| Boundary | Control | Residual risk |
| --- | --- | --- |
| Browser → API | Local binding, trusted Host and Origin, strict body schema, 128 KiB limit | Local programs can still call the API; no global rate limit |
| Untrusted text → HTML | React text rendering; no raw HTML injection | Dependencies and browser extensions remain trusted |
| API → SQLite | Parameterized SQL, WAL, explicit write transactions | Local operator can read/modify DB; no at-rest encryption |
| Audit events → evidence | Metadata-only records, SHA256 chaining | No external anchor; truncation and complete rewrite undetectable |
| Server → optional model | Operator-controlled endpoint, bounded timeout, no redirects | Misconfigured endpoint or malicious provider still matters |

`TRUSTED_HOSTS` is an operator environment setting, comma-separated; defaults to localhost, 127.0.0.1 and testserver. Do not set a wildcard for a shared deployment. `APP_DB` chooses a local database path. Keep `data/`, `.env`, session capabilities and reviewer keys out of Git.

## Project-specific assumptions

- 模式识别不能覆盖姓名、地址、语义身份特征、所有地区手机号或经过编码的秘密，不是完整 DLP。
- 原始 PII 仍短暂存在服务端内存与用户页面中；不是加密计算，也不保护已被攻陷的服务器。
- 映射在重启后失效，单 worker 是当前要求；多 worker 或多副本需要独立安全 vault。
- TTL 在访问/新建会话时惰性清理；过期数据可能仍占内存至下一次访问，但不能再通过 API 恢复。
- session_token 是恢复权限凭据，不写入磁盘、URL 或审计；需防止客户端 XSS 与凭据泄露。

## Reporting

Use GitHub private vulnerability reporting if enabled. Otherwise open an issue containing only a minimal synthetic reproduction, never real secrets or customer data. This project does not claim production readiness or comprehensive LLM safety guarantees.
