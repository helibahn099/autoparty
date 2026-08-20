import React, { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "../api";
import MapView from "../components/MapView";
import { useAuth } from "../auth";
import { useI18n } from "../i18n";

export default function MapPage() {
  const { t } = useI18n();
  const { user } = useAuth();
  const nav = useNavigate();
  const [data, setData] = useState(null);
  const [selected, setSelected] = useState(null);

  useEffect(() => {
    api("/map/points")
      .then((d) => {
        setData(d);
        setSelected(null);
      })
      .catch(() => {});
  }, [user]);

  const offers = data?.offer_count || 0;
  const partners = data?.partner_count || 0;

  return (
    <div className="map-page">
      <div className="map-stage">
        <MapView data={data} fill interactive showCities={false} onSelect={setSelected} />
        <div className="map-ui">
          <div className="map-legend card">
            <b>{offers ? t("map.answers", { n: offers }) : t("map.partners", { n: partners })}</b>
            <div className="muted">{t("map.lede")}</div>
          </div>
          <button className="btn" type="button" onClick={() => nav(user ? "/search" : "/login")}>
            {t("home.start")}
          </button>
        </div>
        {selected && (
          <aside className="map-aside card">
            <div className="step">{selected.kind === "partner" ? t("map.partner") : t("map.pickup")}</div>
            <h3 style={{ margin: "6px 0" }}>{selected.title}</h3>
            <p><b>{selected.subtitle}</b></p>
            {selected.seller?.pickup_note && <p className="muted">{selected.seller.pickup_note}</p>}
            {selected.vehicle && <p className="muted">{selected.vehicle}</p>}
            {selected.parts?.length > 0 && <p>{selected.parts.join(", ")}</p>}
            {selected.price_from && <p className="price">{t("common.priceFrom", { price: selected.price_from })}</p>}
            <SellerContacts seller={selected.seller} address={selected.subtitle} />
            <div className="contact-actions">
              {selected.order_id && <Link className="btn ghost small" to={`/orders/${selected.order_id}`}>{t("common.order")}</Link>}
              {selected.chat_id && <Link className="btn small" to={`/chats/${selected.chat_id}`}>{t("common.chat")}</Link>}
              {selected.seller?.id && <Link className="btn ghost small" to={`/sellers/${selected.seller.id}`}>{t("seller.profile")}</Link>}
            </div>
          </aside>
        )}
      </div>
    </div>
  );
}

export function SellerContacts({ seller, address }) {
  const { t } = useI18n();
  if (!seller) return null;
  const wa = seller.whatsapp ? `https://wa.me/${String(seller.whatsapp).replace(/\D/g, "")}` : null;
  const tg = seller.telegram ? `https://t.me/${seller.telegram.replace("@", "")}` : null;
  const ig = seller.instagram ? `https://instagram.com/${seller.instagram.replace("@", "")}` : null;
  return (
    <div className="contact-actions">
      {address && (
        <button className="btn small" type="button" onClick={() => navigator.clipboard.writeText(address)}>
          {t("common.copyAddress")}
        </button>
      )}
      {wa && <a className="btn small secondary" href={wa} target="_blank" rel="noreferrer">WhatsApp</a>}
      {tg && <a className="btn ghost small" href={tg} target="_blank" rel="noreferrer">Telegram</a>}
      {ig && <a className="btn ghost small" href={ig} target="_blank" rel="noreferrer">Instagram</a>}
    </div>
  );
}
