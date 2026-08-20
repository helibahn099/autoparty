import React, { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "../api";
import { useAuth } from "../auth";
import { useI18n } from "../i18n";

export default function ProfilePage() {
  const { user, logout, refresh } = useAuth();
  const { t } = useI18n();
  const nav = useNavigate();
  const [form, setForm] = useState({ name: user?.name || "", phone: user?.phone || "" });
  const [chats, setChats] = useState([]);
  const [garage, setGarage] = useState([]);
  const [meta, setMeta] = useState({});
  const [msg, setMsg] = useState("");

  useEffect(() => {
    api("/profile/chats").then(setChats).catch(() => {});
    api("/meta").then(setMeta).catch(() => {});
    api("/garage").then(setGarage).catch(() => {});
  }, []);

  async function save(e) {
    e.preventDefault();
    await api("/profile", { method: "PATCH", body: form });
    await refresh();
    setMsg("Сохранено");
  }

  return (
    <div className="container page">
      <div className="grid-2">
        <form className="card" onSubmit={save}>
          <h3>{t("nav.profile")}</h3>
          <label>{t("auth.name")}</label>
          <input className="text-input" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
          <label>{t("auth.phone")}</label>
          <input className="text-input" value={form.phone || ""} onChange={(e) => setForm({ ...form, phone: e.target.value })} />
          <label>Email</label>
          <input className="text-input" value={user.email} disabled />
          <p className="muted">Роль: {user.role}</p>
          {msg && <p className="muted">{msg}</p>}
          <div className="row">
            <button className="btn" type="submit">{t("common.save")}</button>
            <button className="btn ghost" type="button" onClick={() => { logout(); nav("/"); }}>{t("common.logout")}</button>
          </div>
          {user.role === "CLIENT" && (
            <p style={{ marginTop: 16 }}>
              {/* TODO: replace seller registration placeholder with real seller registration service */}
              <a className="btn secondary small" href={meta.become_seller_url || "https://www.youtube.com/watch?v=dQw4w9WgXcQ"} target="_blank" rel="noreferrer">
                Стать продавцом
              </a>
            </p>
          )}
          {user.role === "SELLER" && (
            <p style={{ marginTop: 16 }}><Link className="btn small" to="/seller/profile">Профиль продавца</Link></p>
          )}
        </form>
        <div className="card">
          <h3>{t("nav.chats")}</h3>
          {chats.length === 0 && <p className="muted">Пока нет переписок</p>}
          <div className="stack">
            {chats.map((c) => (
              <Link key={c.id} className="order-mini" to={`/chats/${c.id}`}>
                <b>{c.other_name}</b>
                <div className="muted">Заказ #{c.order_id} · {c.last_message || "нет сообщений"}</div>
              </Link>
            ))}
          </div>
        </div>
      </div>
      <div className="card" style={{ marginTop: 12 }}>
        <h3>{t("profile.garage")}</h3>
        {garage.length === 0 && <p className="muted">{t("home.emptyGarage")}</p>}
        <div className="chips">
          {garage.map((car) => (
            <span className="car-chip on" key={car.id}>{car.label}</span>
          ))}
        </div>
      </div>
      <div className="card" style={{ marginTop: 12 }}>
        <div className="section-head">
          <h3 style={{ margin: 0 }}>{t("profile.orders")}</h3>
          <Link className="btn small ghost" to="/orders">{t("nav.orders")}</Link>
        </div>
      </div>
    </div>
  );
}
