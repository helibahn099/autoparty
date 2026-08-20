import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";
import { useI18n } from "../i18n";

export default function OrdersPage() {
  const { t } = useI18n();
  const [orders, setOrders] = useState(null);

  useEffect(() => {
    api("/profile/orders").then(setOrders).catch(() => setOrders([]));
  }, []);

  if (!orders) return <div className="container page">{t("common.loading")}</div>;

  return (
    <div className="container page">
      <div className="kicker">{t("nav.orders")}</div>
      <div className="section-head">
        <h2 style={{ margin: 0 }}>{t("orders.title")}</h2>
        <Link className="btn small" to="/search">{t("home.start")}</Link>
      </div>
      {orders.length === 0 && (
        <div className="card" style={{ marginTop: 16 }}>
          <p className="muted">{t("orders.empty")}</p>
          <Link className="btn" to="/search">{t("home.start")}</Link>
        </div>
      )}
      <div className="stack" style={{ marginTop: 14 }}>
        {orders.map((o) => (
          <Link
            key={o.id}
            className="order-mini card"
            to={o.status === "WAITING_FOR_PAYMENT" ? `/orders/${o.id}/pay` : `/orders/${o.id}`}
          >
            <div className="chat-row">
              <div>
                <b>#{o.id} · {o.vehicle}</b>
                <div className="muted">{(o.items || []).map((i) => i.description).join(", ")}</div>
              </div>
              <span className="status">{t(`status.${o.status}`)}</span>
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}
