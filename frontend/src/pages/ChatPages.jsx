import React, { useEffect, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api";
import { useAuth } from "../auth";
import { useI18n } from "../i18n";
import ReportModal from "../components/ReportModal";

export function ChatListPage() {
  const { t } = useI18n();
  const [chats, setChats] = useState([]);
  useEffect(() => {
    api("/chats").then(setChats).catch(() => {});
  }, []);
  return (
    <div className="container page">
      <div className="card chat-list">
        <h3>{t("chats.title")}</h3>
        {chats.length === 0 && <p className="muted">{t("chats.empty")}</p>}
        {chats.map((c) => (
          <Link key={c.id} to={`/chats/${c.id}`} className="order-mini" style={{ marginBottom: 8, display: "block" }}>
            <div className="chat-row">
              <div>
                <b>{c.other_name}</b>
                <div className="muted">Заказ #{c.order_id} · {c.last_message || "нет сообщений"}</div>
              </div>
              {c.unread > 0 && <span className="badge" style={{ position: "static" }}>{c.unread}</span>}
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}

export function ChatPage() {
  const { id } = useParams();
  const { user } = useAuth();
  const { t } = useI18n();
  const [chat, setChat] = useState(null);
  const [text, setText] = useState("");
  const [file, setFile] = useState(null);
  const [report, setReport] = useState(false);
  const bottom = useRef(null);

  async function load() {
    const data = await api(`/chats/${id}`);
    setChat(data);
    window.dispatchEvent(new Event("avtoparty-unread"));
  }

  useEffect(() => {
    load().catch(() => {});
    const onWs = (e) => {
      if (e.detail?.event === "chat.message" && String(e.detail.data?.chat_id) === String(id)) {
        setChat((prev) => prev ? { ...prev, messages: [...(prev.messages || []), e.detail.data] } : prev);
      }
    };
    window.addEventListener("avtoparty-ws", onWs);
    return () => window.removeEventListener("avtoparty-ws", onWs);
  }, [id]);

  useEffect(() => {
    bottom.current?.scrollIntoView({ behavior: "smooth" });
  }, [chat?.messages?.length]);

  async function send(e) {
    e.preventDefault();
    const form = new FormData();
    if (text) form.append("text", text);
    if (file) form.append("files", file);
    await api(`/chats/${id}/messages`, { method: "POST", form });
    setText("");
    setFile(null);
    await load();
  }

  if (!chat) return <div className="container page">{t("common.loading")}</div>;

  return (
    <div className="container page">
      <div className="card">
        <div className="chat-row">
          <div>
            <b>{chat.other_name}</b>
            <div className="muted">{t("common.order")} #{chat.order_id}</div>
          </div>
          <div className="row">
            {user?.role === "CLIENT" && (
              <button className="btn small ghost" type="button" onClick={() => setReport(true)}>{t("common.report")}</button>
            )}
            <Link className="btn small ghost" to={`/orders/${chat.order_id}`}>{t("common.order")}</Link>
          </div>
        </div>
        <div className="messages">
          {(chat.messages || []).map((m) => (
            <div key={m.id} className={`bubble ${m.sender_id === user.id ? "me" : ""}`}>
              {m.text}
              {m.attachments?.map((a) => (
                <img key={a.id} src={a.url} alt={a.original_name} />
              ))}
            </div>
          ))}
          <div ref={bottom} />
        </div>
        <form className="composer-bar" onSubmit={send}>
          <input className="text-input" value={text} onChange={(e) => setText(e.target.value)} placeholder={t("chats.message")} />
          <input type="file" accept="image/jpeg,image/png,image/webp" onChange={(e) => setFile(e.target.files[0])} />
          <button className="btn" type="submit">{t("common.send")}</button>
        </form>
      </div>
      {report && user?.role === "CLIENT" && (
        <ReportModal sellerId={chat.seller_id} orderId={chat.order_id} chatId={chat.id} onClose={() => setReport(false)} />
      )}
    </div>
  );
}
