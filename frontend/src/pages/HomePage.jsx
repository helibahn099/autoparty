import React, { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "../api";
import { useAuth } from "../auth";
import { useI18n } from "../i18n";
import { IconBox, IconChat, IconMap, IconSearch } from "../components/Icons";

const ACTIVE = new Set(["WAITING_FOR_PAYMENT", "PAID", "SEARCHING", "OFFERS_RECEIVED", "SELLER_SELECTED"]);

export default function HomePage() {
  const { user } = useAuth();
  const { t } = useI18n();
  const nav = useNavigate();
  const [mapData, setMapData] = useState(null);
  const [orders, setOrders] = useState([]);
  const [garage, setGarage] = useState([]);
  const [unread, setUnread] = useState(0);

  useEffect(() => {
    api("/map/points").then(setMapData).catch(() => {});
  }, []);

  useEffect(() => {
    if (!user) return;
    if (user.role === "CLIENT") {
      api("/profile/orders").then(setOrders).catch(() => {});
      api("/garage").then(setGarage).catch(() => {});
    }
    api("/chats/unread-count").then((d) => setUnread(d.chats || 0)).catch(() => {});
  }, [user]);

  const answers = mapData?.offer_count || 0;
  const partners = mapData?.partner_count || 0;
  const done = orders.filter((o) => o.status === "COMPLETED").length;
  const active = orders.filter((o) => ACTIVE.has(o.status)).length;
  const ordersTo = user?.role === "SELLER" ? "/seller" : user ? "/orders" : "/login";
  const startTo = !user ? "/login" : user.role === "SELLER" ? "/seller" : "/search";

  return (
    <div className="dash">
      <p className="kicker">{t("home.kicker")}</p>
      <h1 className="dash-title">{t("home.headline")}</h1>
      <p className="lede">{t("home.lede")}</p>

      <div className="dash-hero">
        <Link className="dash-tile dash-map" to="/map">
          <div className="map-preview" aria-hidden="true">
            <span className="map-preview-pin" style={{ left: "38%", top: "34%" }} />
            <span className="map-preview-pin partner" style={{ left: "58%", top: "48%" }} />
            <span className="map-preview-pin" style={{ left: "46%", top: "62%" }} />
          </div>
          <div className="map-preview-badge">
            {answers ? t("home.answers", { n: answers }) : t("home.partners", { n: partners })}
          </div>
          <div className="dash-tile-foot">
            <span className="dash-ico"><IconMap /></span>
            <span>
              <b>{t("nav.map")}</b>
              <span className="muted">{t("home.tileMapHint")}</span>
            </span>
          </div>
        </Link>

        <Link className="dash-tile dash-orders" to={ordersTo}>
          <span className="dash-ico lg"><IconBox /></span>
          <b>{user?.role === "SELLER" ? t("nav.requests") : t("nav.orders")}</b>
          <span className="muted">
            {user?.role === "SELLER"
              ? t("home.tileRequestsHint")
              : active
                ? t("home.tileOrdersActive", { n: active })
                : t("home.tileOrdersHint")}
          </span>
        </Link>

        <Link className="dash-tile dash-stat glow glow-green" to={user ? "/orders" : "/login"}>
          <span className="dash-num">{user ? done : "—"}</span>
          <b>{t("home.statDone")}</b>
          <span className="muted">{t("home.statDoneHint")}</span>
        </Link>

        <Link className="dash-tile dash-stat glow glow-violet" to={user ? "/profile" : "/login"}>
          <span className="dash-num">{user ? garage.length : "—"}</span>
          <b>{t("home.statGarage")}</b>
          <span className="muted">{t("home.statGarageHint")}</span>
        </Link>

        <button className="dash-tile dash-cta" type="button" onClick={() => nav(startTo)}>
          <span className="cta-arrow" aria-hidden="true">→</span>
          <b>{user?.role === "SELLER" ? t("nav.requests") : t("home.start")}</b>
          <span>{user?.role === "SELLER" ? t("home.tileRequestsHint") : t("home.startHint")}</span>
        </button>
      </div>

      <div className="dash-row">
        <article className="dash-promo">
          <b>{t("home.promoPayTitle")}</b>
          <p className="muted">{t("home.promoPayBody")}</p>
        </article>
        <article className="dash-promo">
          <b>{t("home.promoCompareTitle")}</b>
          <p className="muted">{t("home.promoCompareBody")}</p>
        </article>
        <article className="dash-promo">
          <b>{t("home.promoMapTitle")}</b>
          <p className="muted">{t("home.promoMapBody")}</p>
        </article>
        {user && (
          <Link className="dash-promo dash-promo-link" to="/chats">
            <span className="dash-ico"><IconChat /></span>
            <b>{t("nav.chats")}{unread ? ` · ${unread}` : ""}</b>
            <p className="muted">{t("home.tileChatsHint")}</p>
          </Link>
        )}
      </div>

      <div className="dash-mobile-cta">
        <Link className="btn full" to={startTo}>
          <IconSearch /> {t("home.start")}
        </Link>
      </div>
    </div>
  );
}
