import React, { useState } from "react";
import { api } from "../api";
import { useI18n } from "../i18n";

const REASONS = [
  ["WRONG_PART", "report.wrongPart"],
  ["FALSE_AVAILABILITY", "report.falseYes"],
  ["OTHER", "report.other"],
];

export default function ReportModal({ sellerId, orderId, chatId, onClose }) {
  const { t } = useI18n();
  const [reason, setReason] = useState("FALSE_AVAILABILITY");
  const [comment, setComment] = useState("");
  const [msg, setMsg] = useState("");
  const [busy, setBusy] = useState(false);

  async function send() {
    setBusy(true);
    setMsg("");
    try {
      await api("/reports", { method: "POST", body: { seller_id: sellerId, order_id: orderId || null, chat_id: chatId || null, reason, comment } });
      setMsg(t("report.sent"));
      setTimeout(onClose, 900);
    } catch (e) {
      setMsg(e.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="modal-back" onClick={onClose}>
      <div className="card modal-card" onClick={(e) => e.stopPropagation()}>
        <h3>{t("report.title")}</h3>
        <div className="stack">
          {REASONS.map(([id, key]) => (
            <button key={id} className={`seg ${reason === id ? "active" : ""}`} type="button" onClick={() => setReason(id)}>
              {t(key)}
            </button>
          ))}
        </div>
        <label>{t("report.comment")}</label>
        <textarea className="text-input" rows={3} value={comment} onChange={(e) => setComment(e.target.value)} />
        {msg && <p className="muted">{msg}</p>}
        <div className="row" style={{ marginTop: 12 }}>
          <button className="btn danger" disabled={busy} onClick={send}>{t("common.send")}</button>
          <button className="btn ghost" type="button" onClick={onClose}>{t("common.cancel")}</button>
        </div>
      </div>
    </div>
  );
}
