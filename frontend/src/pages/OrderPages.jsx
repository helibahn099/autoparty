import React, { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api, offerTone, STATUS_LABEL } from "../api";
import { useAuth } from "../auth";
import MapView from "../components/MapView";
import { SellerContacts } from "./MapPage";
import ReportModal from "../components/ReportModal";
import { useI18n } from "../i18n";

export function PayPage() {
  const { id } = useParams();
  const nav = useNavigate();
  const [payment, setPayment] = useState(null);
  const [order, setOrder] = useState(null);
  const [error, setError] = useState("");

  async function load() {
    const o = await api(`/orders/${id}`);
    setOrder(o);
    if (o.status !== "WAITING_FOR_PAYMENT") {
      nav(`/orders/${id}`, { replace: true });
      return;
    }
    const p = await api("/payments/demo/create", { method: "POST", body: { order_id: Number(id) } });
    setPayment(p);
  }

  useEffect(() => {
    load().catch((e) => setError(e.message));
  }, [id]);

  useEffect(() => {
    const t = setInterval(async () => {
      try {
        const p = await api(`/payments/by-order/${id}`);
        setPayment(p);
        if (p.status === "PAID") nav(`/orders/${id}`);
      } catch {}
    }, 2000);
    return () => clearInterval(t);
  }, [id, nav]);

  async function simulate() {
    await api("/payments/demo/callback", { method: "POST", body: { order_id: Number(id) } });
    nav(`/orders/${id}`);
  }

  if (error) return <div className="container page error">{error}</div>;
  if (!payment || !order) return <div className="container page">Готовим оплату…</div>;

  return (
    <div className="container page">
      <div className="card qr-box">
        <div className="step">Demo-оплата</div>
        <h2>Поиск запчасти</h2>
        <p className="muted">Это не платёж О!Банка. QR открывает заглушку и помечает заказ оплаченным.</p>
        <div className="price">{order.search_price || 200} {order.currency}</div>
        <p>Заказ #{order.id}{order.batch_id ? " · несколько авто в одном поиске" : ""}</p>
        <a href={payment.scan_url} target="_blank" rel="noreferrer">
          <img src={payment.qr_url} alt="QR для demo-оплаты" />
        </a>
        <div className="row" style={{ justifyContent: "center", marginTop: 12 }}>
          <a className="btn" href={payment.scan_url} target="_blank" rel="noreferrer">Открыть QR-ссылку</a>
          <button className="btn ghost" onClick={simulate}>Имитировать callback</button>
        </div>
      </div>
    </div>
  );
}

export function OrderDetailPage() {
  const { id } = useParams();
  const { user } = useAuth();
  const { t } = useI18n();
  const [order, setOrder] = useState(null);
  const [mapData, setMapData] = useState(null);
  const [error, setError] = useState("");
  const [score, setScore] = useState(5);
  const [comment, setComment] = useState("");
  const [rated, setRated] = useState(false);
  const [reportSeller, setReportSeller] = useState(null);

  async function load() {
    const o = await api(`/orders/${id}`);
    setOrder(o);
    const map = await api("/map/points");
    const points = (map.points || []).filter((p) => String(p.order_id) === String(id));
    setMapData({ ...map, points });
  }

  useEffect(() => {
    load().catch((e) => setError(e.message));
    const onWs = (e) => {
      const msg = e.detail;
      if (msg?.data?.order_id == id || msg.event === "offer.new") load().catch(() => {});
    };
    window.addEventListener("autoparty-ws", onWs);
    const t = setInterval(() => load().catch(() => {}), 5000);
    return () => {
      window.removeEventListener("autoparty-ws", onWs);
      clearInterval(t);
    };
  }, [id]);

  if (error) return <div className="container page error">{error}</div>;
  if (!order) return <div className="container page">Загрузка…</div>;

  const selected = order.offers.find((o) => o.id === order.selected_offer_id);
  const yesOffers = order.offers.filter((o) => o.items.some((i) => i.availability === "YES" || i.availability === "PARTIAL"));

  async function selectSeller(offerId) {
    await api(`/orders/${order.id}/select-seller`, { method: "POST", body: { offer_id: offerId } });
    await load();
  }

  async function rate() {
    if (!selected) return;
    await api("/ratings", { method: "POST", body: { order_id: order.id, seller_id: selected.seller_id, score, comment } });
    setRated(true);
    await load();
  }

  return (
    <div className="container page">
      <div className="home-grid">
        <div className="card">
          <div className="chat-row">
            <div>
              <div className="step">Заказ #{order.id}</div>
              <h2 style={{ margin: "6px 0" }}>{order.vehicle}</h2>
              <div className="muted">{order.cities.map((c) => c.name).join(", ")}</div>
            </div>
            <span className="status">{STATUS_LABEL[order.status]}</span>
          </div>
          <div className="stack" style={{ marginTop: 14 }}>
            {order.items.map((it) => (
              <div className="part-row" key={it.id}>
                <div>
                  <b>{it.description}</b>
                  <div className="muted">{it.category || "без категории"}</div>
                </div>
              </div>
            ))}
          </div>
          {order.status === "WAITING_FOR_PAYMENT" && (
            <Link className="btn" style={{ marginTop: 14, display: "inline-block" }} to={`/orders/${order.id}/pay`}>Оплатить поиск</Link>
          )}
        </div>
        <div className="card map-card">
          <div className="map-head">
            <div className="step">{t("order.where")}</div>
            <b>{yesOffers.length ? t("home.points", { n: yesOffers.length }) : t("order.waiting")}</b>
          </div>
          <MapView data={mapData} height={280} interactive />
        </div>
      </div>

      <div className="card" style={{ marginTop: 14 }}>
        <h3>{t("order.answers")}</h3>
        {order.offers.length === 0 && <p className="muted">{t("order.waiting")}</p>}
        {order.offers.map((offer) => {
          const chat = order.chats.find((c) => c.seller_id === offer.seller_id);
          const has = offer.items.some((i) => i.availability === "YES" || i.availability === "PARTIAL");
          const tone = offerTone(offer);
          return (
            <div className={`offer tone-${tone} ${order.selected_offer_id === offer.id ? "selected" : ""}`} key={offer.id}>
              <div className="chat-row">
                <div>
                  <Link to={`/sellers/${offer.seller?.id}`}><b>{offer.seller?.display_name}</b></Link>
                  <div className="muted">{offer.seller?.display_rating} / 5 · {t("seller.completed")}: {offer.seller?.completed_orders_count || 0}</div>
                  <div className="muted">{offer.seller?.address || ""}</div>
                </div>
                {chat && <Link className="btn small ghost" to={`/chats/${chat.id}`}>{t("common.chat")}</Link>}
              </div>
              {offer.items.map((it) => (
                <div className={`item-line tone-${it.availability === "YES" ? "yes" : it.availability === "PARTIAL" ? "partial" : "no"}`} key={it.id} style={{ marginTop: 8 }}>
                  <div>
                    <span>{it.description}</span>
                    <div className="muted">
                      {it.condition === "USED" ? t("seller.used") : it.condition === "NEW" ? t("seller.new") : ""}
                      {it.is_original === true ? ` · ${t("seller.original")}` : it.is_original === false ? ` · ${t("seller.aftermarket")}` : ""}
                    </div>
                    {it.detail && <div className="muted">{it.detail}</div>}
                  </div>
                  <b>{it.availability === "NO" ? t("seller.no") : `${it.price} сом`}</b>
                </div>
              ))}
              {has && <SellerContacts seller={offer.seller} address={offer.seller?.address} />}
              <div className="row" style={{ marginTop: 10 }}>
                {user.role === "CLIENT" && has && order.status !== "COMPLETED" && (
                  <button className="btn small" onClick={() => selectSeller(offer.id)}>{t("order.select")}</button>
                )}
                {user.role === "CLIENT" && (
                  <button className="btn small ghost" type="button" onClick={() => setReportSeller(offer.seller)}>{t("common.report")}</button>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {(order.status === "SELLER_SELECTED" || order.status === "COMPLETED") && selected && user.role === "CLIENT" && (
        <div className="card" style={{ marginTop: 14 }}>
          <h3>{t("order.rate")}</h3>
          {rated || order.status === "COMPLETED" ? (
            <p className="muted">Оценка сохранена.</p>
          ) : (
            <>
              <div className="stars">
                {[1, 2, 3, 4, 5].map((n) => (
                  <button key={n} type="button" onClick={() => setScore(n)}>{n <= score ? "★" : "☆"}</button>
                ))}
              </div>
              <textarea className="text-input" rows={3} value={comment} onChange={(e) => setComment(e.target.value)} placeholder="Комментарий" />
              <button className="btn" onClick={rate}>Отправить оценку</button>
            </>
          )}
        </div>
      )}
      {reportSeller && (
        <ReportModal sellerId={reportSeller.id} orderId={order.id} onClose={() => setReportSeller(null)} />
      )}
    </div>
  );
}
