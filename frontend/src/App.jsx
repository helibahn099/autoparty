import React, { useCallback, useEffect, useState } from "react";
import { Link, NavLink, Navigate, Route, Routes, useLocation } from "react-router-dom";
import { useAuth } from "./auth";
import { api } from "./api";
import HomePage from "./pages/HomePage";
import SearchPage from "./pages/SearchPage";
import MapPage from "./pages/MapPage";
import OrdersPage from "./pages/OrdersPage";
import { LoginPage, RegisterPage } from "./pages/AuthPages";
import ProfilePage from "./pages/ProfilePage";
import { OrderDetailPage, PayPage } from "./pages/OrderPages";
import { ChatListPage, ChatPage } from "./pages/ChatPages";
import { SellerRequestsPage, SellerRequestPage, SellerProfilePage } from "./pages/SellerPages";
import AdminApp from "./pages/AdminPages";
import { IconChat, IconHome, IconMap, IconUser, IconBox } from "./components/Icons";
import { useI18n } from "./i18n";
import SellerPublicPage from "./pages/SellerPublicPage";

function Layout({ children }) {
  const { user } = useAuth();
  const { t, lang, setLang } = useI18n();
  const [unread, setUnread] = useState(0);
  const [toast, setToast] = useState(null);
  const loc = useLocation();
  const isAdmin = loc.pathname.startsWith("/admin");

  const refreshUnread = useCallback(() => {
    if (!user) {
      setUnread(0);
      return;
    }
    api("/chats/unread-count")
      .then((d) => setUnread(d.chats || 0))
      .catch(() => {});
  }, [user]);

  useEffect(() => {
    refreshUnread();
  }, [refreshUnread, loc.pathname]);

  useEffect(() => {
    if (!user) return undefined;
    const token = localStorage.getItem("token");
    const proto = window.location.protocol === "https:" ? "wss" : "ws";
    const ws = new WebSocket(`${proto}://${window.location.host}/api/ws?token=${token}`);
    ws.onmessage = (ev) => {
      const msg = JSON.parse(ev.data);
      window.dispatchEvent(new CustomEvent("avtoparty-ws", { detail: msg }));
      if (msg.event === "chat.message" || msg.event === "notification") {
        refreshUnread();
      }
      if (msg.event === "notification") {
        setToast(msg.data?.title || "Уведомление");
        setTimeout(() => setToast(null), 3200);
      }
    };
    const onRefresh = () => refreshUnread();
    window.addEventListener("avtoparty-unread", onRefresh);
    return () => {
      ws.close();
      window.removeEventListener("avtoparty-unread", onRefresh);
    };
  }, [user, refreshUnread]);

  return (
    <div className={`app-shell ${isAdmin ? "no-tab" : ""}`}>
      <header className="topbar">
        <Link to="/" className="brand">
          <span className="logo-mark">ap</span>
          avtoparty
        </Link>
        <div className="top-actions">
          <div className="lang-switch">
            {["ru", "en", "ky"].map((code) => (
              <button key={code} className={lang === code ? "on" : ""} type="button" onClick={() => setLang(code)}>
                {t(`lang.${code}`)}
              </button>
            ))}
          </div>
          {user?.role === "SELLER" && <Link className="chip-btn" to="/seller">{t("nav.requests")}</Link>}
          {user?.role === "ADMIN" && <Link className="chip-btn" to="/admin">Admin</Link>}
          <Link className="icon-btn" to="/chats" title={t("nav.chats")}>
            <IconChat />
            {unread > 0 && <span className="badge">{unread > 9 ? "9+" : unread}</span>}
          </Link>
          {user ? (
            <Link className="chip-btn" to="/profile">{user.name.split(" ")[0]}</Link>
          ) : (
            <Link className="chip-btn" to="/login">{t("nav.login")}</Link>
          )}
        </div>
      </header>
      {toast && <div className="toast">{toast}</div>}
      {children}
      {!isAdmin && (
        <nav className="tabbar">
          <NavLink to="/" end className={({ isActive }) => (isActive ? "active" : "")}>
            <IconHome /> {t("nav.home")}
          </NavLink>
          <NavLink to="/map" className={({ isActive }) => (isActive ? "active" : "")}>
            <IconMap /> {t("nav.map")}
          </NavLink>
          {user?.role === "SELLER" ? (
            <NavLink to="/seller" className={({ isActive }) => (isActive ? "active" : "")}>
              <IconBox /> {t("nav.requests")}
            </NavLink>
          ) : (
            <NavLink to="/orders" className={({ isActive }) => (isActive ? "active" : "")}>
              <IconBox /> {t("nav.orders")}
            </NavLink>
          )}
          <NavLink to="/chats" className={({ isActive }) => (isActive ? "active" : "")}>
            <IconChat /> {t("nav.chats")}
          </NavLink>
          <NavLink to="/profile" className={({ isActive }) => (isActive ? "active" : "")}>
            <IconUser /> {t("nav.profile")}
          </NavLink>
        </nav>
      )}
    </div>
  );
}

function Private({ children, roles }) {
  const { user, ready } = useAuth();
  const loc = useLocation();
  if (!ready) return <div className="container page">Загрузка…</div>;
  if (!user) return <Navigate to="/login" state={{ from: loc.pathname }} replace />;
  if (roles && !roles.includes(user.role)) return <Navigate to="/" replace />;
  return children;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />
      <Route
        path="/*"
        element={
          <Layout>
            <Routes>
              <Route path="/" element={<HomePage />} />
              <Route path="/search" element={<SearchPage />} />
              <Route path="/map" element={<MapPage />} />
              <Route path="/sellers/:id" element={<SellerPublicPage />} />
              <Route path="/profile" element={<Private><ProfilePage /></Private>} />
              <Route path="/orders" element={<Private><OrdersPage /></Private>} />
              <Route path="/orders/:id" element={<Private><OrderDetailPage /></Private>} />
              <Route path="/orders/:id/pay" element={<Private><PayPage /></Private>} />
              <Route path="/chats" element={<Private><ChatListPage /></Private>} />
              <Route path="/chats/:id" element={<Private><ChatPage /></Private>} />
              <Route path="/seller" element={<Private roles={["SELLER"]}><SellerRequestsPage /></Private>} />
              <Route path="/seller/requests/:id" element={<Private roles={["SELLER"]}><SellerRequestPage /></Private>} />
              <Route path="/seller/profile" element={<Private roles={["SELLER"]}><SellerProfilePage /></Private>} />
              <Route path="/admin/*" element={<Private roles={["ADMIN"]}><AdminApp /></Private>} />
            </Routes>
          </Layout>
        }
      />
    </Routes>
  );
}
