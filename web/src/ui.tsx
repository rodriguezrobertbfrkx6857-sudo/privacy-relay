import { useState, type ReactNode } from "react";
import {
  ShieldCheck,
  ArrowUpRight,
  Activity,
  Braces,
  FileCheck2,
  Github,
} from "lucide-react";
export async function api<T = any>(
  path: string,
  body?: unknown,
  method?: string,
): Promise<T> {
  const r = await fetch("/api" + path, {
    method: method || (body === undefined ? "GET" : "POST"),
    headers: body === undefined ? {} : { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  const data = await r.json();
  if (!r.ok)
    throw new Error(
      typeof data.detail === "string"
        ? data.detail
        : JSON.stringify(data.detail),
    );
  return data;
}
export function Shell({
  title,
  subtitle,
  number,
  children,
}: {
  title: string;
  subtitle: string;
  number: string;
  children: ReactNode;
}) {
  const [tab, setTab] = useState("workbench");
  const [audit, setAudit] = useState<any>(null);
  const [error, setError] = useState("");
  async function history() {
    setTab("audit");
    try {
      setAudit(await api("/audit"));
      setError("");
    } catch (e) {
      setError(String(e));
    }
  }
  return (
    <div className="layout">
      <aside>
        <a className="brand" href="/">
          <ShieldCheck size={28} />
          <span>
            BOUNDARY<span className="brand-sub">AI SECURITY LAB</span>
          </span>
        </a>
        <div className="nav-label">WORKSPACE / {number}</div>
        <button
          className={tab === "workbench" ? "nav active" : "nav"}
          onClick={() => setTab("workbench")}
        >
          <Activity size={18} />
          实验工作台 <span>↗</span>
        </button>
        <button
          className={tab === "audit" ? "nav active" : "nav"}
          onClick={history}
        >
          <FileCheck2 size={18} />
          审计证据
        </button>
        <a className="nav" href="/docs" target="_blank" rel="noreferrer">
          <Braces size={18} />
          API 文档
          <ArrowUpRight size={14} />
        </a>
        <div className="aside-bottom">
          <div className="status">
            <i /> LOCAL RESEARCH MODE
          </div>
          <p>
            Make the boundary visible.
            <br />
            Make the evidence reproducible.
          </p>
          <a
            href="https://github.com/rodriguezrobertbfrkx6857-sudo"
            target="_blank"
            rel="noreferrer"
          >
            <Github size={16} /> GitHub portfolio ↗
          </a>
        </div>
      </aside>
      <main>
        <header>
          <span>
            安全工程 / <b>{title}</b>
          </span>
          <span className="version">v0.1 · Research workbench</span>
        </header>
        <div className="page">
          <div className="eyebrow">
            EXPERIMENT {number} <span>—</span> TRUST, VERIFIED.
          </div>
          <h1>
            {title}
            <span>.</span>
          </h1>
          <p className="subtitle">{subtitle}</p>
          {tab === "workbench" ? (
            children
          ) : (
            <>
              <div className="section-title">
                <h2>审计链 / Audit trail</h2>
                <button onClick={history}>刷新</button>
              </div>
              <ErrorBox error={error} />
              {audit && (
                <>
                  <Metrics
                    items={[
                      ["事件", audit.count],
                      ["链校验", audit.valid ? "VALID" : "TAMPERED"],
                      ["存储", "SQLite / WAL"],
                    ]}
                  />
                  <p className="note">
                    仅保存元数据。哈希链可检测内容修改；未外部锚定，无法检测尾部截断。
                  </p>
                  <Json value={audit} />
                </>
              )}
            </>
          )}
        </div>
        <footer>
          BOUNDARY LAB{" "}
          <span>Built for inspection. Designed for extension.</span>
          <span>Python + TypeScript</span>
        </footer>
      </main>
    </div>
  );
}
export function Card({
  title,
  kicker,
  children,
}: {
  title: string;
  kicker?: string;
  children: ReactNode;
}) {
  return (
    <section className="card">
      <div className="card-head">
        <h2>{title}</h2>
        <span>{kicker}</span>
      </div>
      {children}
    </section>
  );
}
export function Metrics({ items }: { items: [string, string | number][] }) {
  return (
    <div className="metrics">
      {items.map(([label, value]) => (
        <div key={label}>
          <span>{label}</span>
          <strong>{value}</strong>
        </div>
      ))}
    </div>
  );
}
export function Json({ value }: { value: unknown }) {
  return (
    <details className="json">
      <summary>查看结构化证据 / JSON</summary>
      <pre>{JSON.stringify(value, null, 2)}</pre>
    </details>
  );
}
export function ErrorBox({ error }: { error: string }) {
  return error ? (
    <div className="error" role="alert">
      {error}
    </div>
  ) : null;
}
export function Empty({
  text = "运行一次实验，查看证据与决策。",
}: {
  text?: string;
}) {
  return (
    <div className="empty">
      <ShieldCheck size={38} />
      <h3>Evidence starts here</h3>
      <p>{text}</p>
      <div className="empty-line" />
    </div>
  );
}
export function Badge({
  children,
  good = false,
}: {
  children: ReactNode;
  good?: boolean;
}) {
  return <span className={"badge " + (good ? "good" : "")}>{children}</span>;
}
export function download(name: string, value: unknown) {
  const a = document.createElement("a");
  const url = URL.createObjectURL(
    new Blob([JSON.stringify(value, null, 2)], { type: "application/json" }),
  );
  a.href = url;
  a.download = name;
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
