import React, { useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../auth";
import { useI18n } from "../i18n";

export function LoginPage() {
  const { login } = useAuth();
  const { t, lang, setLang } = useI18n();
  const nav = useNavigate();
  const loc = useLocation();
  const [email, setEmail] = useState("client1@autoparty.demo");
  const [password, setPassword] = useState("qweasdzxc");
  const [error, setError] = useState("");

  async function onSubmit(e) {
    e.preventDefault();
    setError("");
    try {
      const user = await login(email, password);
      const to = loc.state?.from || (user.role === "ADMIN" ? "/admin" : "/");
      nav(to);
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <div className="auth-wrap">
      <form className="auth-card" onSubmit={onSubmit}>
        <div className="brand" style={{ marginBottom: 16 }}>
          <span className="logo-mark">ap</span> autoparty
        </div>
        <h2>{t("auth.login")}</h2>
        <p className="muted">{t("auth.demo")}</p>
        <div className="lang-switch" style={{ marginBottom: 8 }}>
          {["ru", "en", "ky"].map((code) => (
            <button key={code} className={lang === code ? "on" : ""} type="button" onClick={() => setLang(code)}>{t(`lang.${code}`)}</button>
          ))}
        </div>
        <label>Email</label>
        <input className="text-input" value={email} onChange={(e) => setEmail(e.target.value)} />
        <label>{t("auth.password")}</label>
        <input className="text-input" type="password" value={password} onChange={(e) => setPassword(e.target.value)} />
        {error && <p className="error">{error}</p>}
        <button className="btn full" style={{ marginTop: 16 }} type="submit">{t("auth.submit")}</button>
        <p className="muted" style={{ marginTop: 14 }}>
          {t("auth.noAccount")} <Link to="/register">{t("auth.register")}</Link>
        </p>
      </form>
    </div>
  );
}

export function RegisterPage() {
  const { register } = useAuth();
  const { t } = useI18n();
  const nav = useNavigate();
  const [form, setForm] = useState({ email: "", password: "", name: "", phone: "" });
  const [error, setError] = useState("");

  async function onSubmit(e) {
    e.preventDefault();
    setError("");
    try {
      await register(form);
      nav("/");
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <div className="auth-wrap">
      <form className="auth-card" onSubmit={onSubmit}>
        <h2>{t("auth.register")}</h2>
        <label>{t("auth.name")}</label>
        <input className="text-input" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
        <label>{t("auth.phone")}</label>
        <input className="text-input" value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} />
        <label>Email</label>
        <input className="text-input" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} />
        <label>{t("auth.password")}</label>
        <input className="text-input" type="password" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} />
        {error && <p className="error">{error}</p>}
        <button className="btn full" style={{ marginTop: 16 }} type="submit">{t("auth.create")}</button>
        <p className="muted" style={{ marginTop: 14 }}>
          {t("auth.hasAccount")} <Link to="/login">{t("auth.login")}</Link>
        </p>
      </form>
    </div>
  );
}
