import { useState } from "react";
import { LockKeyhole, ArrowRight } from "lucide-react";
import { Shell, Card, Metrics, api, Json, ErrorBox, Empty, Badge } from "./ui";
export default function App() {
  const [text, setText] = useState(
      "请给 demo@example.com 写一封客服回复。联系电话 202-555-0142，测试卡号 4111 1111 1111 1111。\napi_key=synthetic_demo_123456",
    ),
    [result, setResult] = useState<any>(null),
    [response, setResponse] = useState(""),
    [restored, setRestored] = useState(""),
    [ttl, setTtl] = useState(300),
    [busy, setBusy] = useState(false),
    [error, setError] = useState("");
  async function action(fn: () => Promise<void>) {
    setBusy(true);
    setError("");
    try {
      await fn();
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }
  async function protect(relay = false) {
    await action(async () => {
      setRestored("");
      const d = await api(relay ? "/relay" : "/protect", { text, ttl });
      setResult(d);
      setResponse(d.model_output || d.text);
    });
  }
  return (
    <Shell
      title="Privacy Relay"
      subtitle="只让必要信息越过模型边界。会话内稳定替换、会话间不可关联，密钥永久遮盖，恢复权留在用户一侧。"
      number="05"
    >
      <Metrics
        items={[
          ["识别实体", result?.entities.length ?? "—"],
          ["不可恢复密钥", result?.irreversible ?? "—"],
          ["映射存储", "Ephemeral memory"],
        ]}
      />
      <ErrorBox error={error} />
      <div className="columns">
        <div>
          <Card title="输入隐私边界" kicker="01 / MINIMIZE">
            <Badge good>仅使用合成演示数据</Badge>
            <label htmlFor="text">即将发送的内容</label>
            <textarea
              id="text"
              value={text}
              rows={9}
              onChange={(e) => setText(e.target.value)}
            />
            <label htmlFor="ttl">映射有效期</label>
            <select
              id="ttl"
              value={ttl}
              onChange={(e) => setTtl(Number(e.target.value))}
            >
              <option value={30}>30 秒 · 过期演示</option>
              <option value={300}>5 分钟</option>
              <option value={900}>15 分钟</option>
            </select>
            <button
              className="primary"
              disabled={busy || !text}
              onClick={() => protect()}
            >
              <LockKeyhole size={16} />
              {busy ? "处理中…" : "识别并替换敏感信息"}
              <ArrowRight size={16} />
            </button>
            <button
              style={{ marginTop: 10, width: "100%" }}
              disabled={busy || !text}
              onClick={() => protect(true)}
            >
              脱敏后发送给本地 Ollama
            </button>
            <p className="note">
              普通检测不调用模型。Ollama
              需要服务端配置。识别范围为邮箱、手机号、Luhn
              校验卡号和部分密钥格式，不包含所有敏感信息。
            </p>
          </Card>
          <Card title="边界约束" kicker="DESIGN INVARIANTS">
            <div className="step">
              <b>原始 PII 不写入审计数据库</b>
              <span>NO RAW LOGS</span>
            </div>
            <div className="step">
              <b>会话到期、撤销或重启后失效</b>
              <span>EPHEMERAL</span>
            </div>
            <div className="step">
              <b>未知或跨会话令牌拒绝恢复</b>
              <span>FAIL CLOSED</span>
            </div>
          </Card>
        </div>
        <div>
          <Card title="跨边界内容" kicker="02 / PROTECT">
            {result ? (
              <>
                <div className="result-head">
                  <Badge good>PROTECTED</Badge>
                  <small>{result.restorable} 项可恢复</small>
                </div>
                <div className="token-output">{result.text}</div>
                <div className="samples" style={{ marginTop: 15 }}>
                  {result.entities.map((e: any, i: number) => (
                    <Badge key={i} good={e.kind !== "SECRET"}>
                      {e.kind} [{e.start}, {e.end}]
                    </Badge>
                  ))}
                </div>
                <p className="note">
                  映射过期时间：
                  {new Date(result.expires_at * 1000).toLocaleTimeString()}
                  。凭据仅保留在本页面内存中。
                </p>
                <Json value={{ ...result, session_token: "[REDACTED]" }} />
              </>
            ) : (
              <Empty text="先检测输入，查看模型会接收到的内容。" />
            )}
          </Card>
          {result && (
            <Card title="用户侧恢复" kicker="03 / RESTORE">
              <label htmlFor="response">模型输出或待恢复文本</label>
              <textarea
                id="response"
                rows={5}
                value={response}
                onChange={(e) => setResponse(e.target.value)}
              />
              <div className="row">
                <button
                  className="primary"
                  disabled={busy}
                  onClick={() =>
                    action(async () =>
                      setRestored(
                        (
                          await api("/restore", {
                            text: response,
                            session_token: result.session_token,
                          })
                        ).text,
                      ),
                    )
                  }
                >
                  在本会话恢复
                </button>
                <button
                  style={{ marginTop: 19 }}
                  disabled={busy}
                  onClick={() =>
                    action(async () => {
                      await api("/revoke", {
                        session_token: result.session_token,
                      });
                      setResult(null);
                      setResponse("");
                      setRestored("");
                    })
                  }
                >
                  撤销会话
                </button>
              </div>
              {restored && (
                <>
                  <label>恢复结果</label>
                  <div className="token-output">{restored}</div>
                </>
              )}
            </Card>
          )}
        </div>
      </div>
    </Shell>
  );
}
