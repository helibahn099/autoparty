import React, { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api, offerTone, STATUS_LABEL } from "../api";
import { useI18n } from "../i18n";

function emptyAnswer() {
  return { availability: "NO", price: "", comment: "", detail: "", condition: "NEW", is_original: true };
}

export function SellerRequestsPage() {
  const { t } = useI18n();
  const [rows, setRows] = useState([]);
  async function load() {
    const data = await api("/seller/requests");
    setRows(data);
  }
  useEffect(() => {
    load();
    const onWs = (e) => {
      if (e.detail?.event === "notification" && e.detail.data?.type === "NEW_REQUEST") load();
    };
    window.addEventListener("avtoparty-ws", onWs);
    const timer = setInterval(load, 4000);
    return () => {
      window.removeEventListener("avtoparty-ws", onWs);
      clearInterval(timer);
    };
  }, []);

  return (
    <div className="container page">
      <div className="card">
        <h2>{t("seller.requests")}</h2>
        <p className="muted">{t("seller.requestsHint")}</p>
        {rows.length === 0 && <p className="muted">{t("seller.empty")}</p>}
        <div className="stack">
          {rows.map((o) => {
            const tone = o.my_offer ? offerTone(o.my_offer) : "wait";
            return (
              <Link key={o.id} className={`order-mini tone-${tone}`} to={`/seller/requests/${o.id}`}>
                <div className="chat-row">
                  <div>
                    <b>#{o.id} · {o.vehicle}</b>
                    <div className="muted">{o.items.map((i) => i.description).join(", ")}</div>
                    <div className="muted">{o.cities.map((c) => c.name).join(", ")}</div>
                  </div>
                  <span className={`status tone-${tone}`}>{o.my_offer ? t("seller.answered") : STATUS_LABEL[o.status]}</span>
                </div>
              </Link>
            );
          })}
        </div>
      </div>
    </div>
  );
}

export function SellerRequestPage() {
  const { id } = useParams();
  const { t } = useI18n();
  const [order, setOrder] = useState(null);
  const [answers, setAnswers] = useState({});
  const [partial, setPartial] = useState(false);
  const [selected, setSelected] = useState({});
  const [msg, setMsg] = useState("");

  async function load() {
    const data = await api(`/seller/requests/${id}`);
    setOrder(data);
    const mine = (data.offers || [])[0];
    if (mine) {
      const map = {};
      mine.items.forEach((it) => {
        map[it.order_item_id] = {
          availability: it.availability,
          price: it.price || "",
          comment: it.comment || "",
          detail: it.detail || "",
          condition: it.condition || "NEW",
          is_original: it.is_original !== false,
        };
      });
      setAnswers(map);
    }
  }

  useEffect(() => {
    load().catch((e) => setMsg(e.message));
  }, [id]);

  function setAns(itemId, patch) {
    setAnswers((prev) => ({ ...prev, [itemId]: { ...emptyAnswer(), ...prev[itemId], ...patch } }));
  }

  async function submit() {
    const items = order.items
      .filter((it) => !partial || selected[it.id])
      .map((it) => {
        const a = answers[it.id] || emptyAnswer();
        return {
          order_item_id: it.id,
          availability: a.availability || "NO",
          price: a.availability === "NO" ? null : Number(a.price),
          comment: a.comment || null,
          detail: a.detail || null,
          condition: a.availability === "NO" ? null : a.condition,
          is_original: a.availability === "NO" ? null : a.is_original,
        };
      });
    await api("/seller/offers", { method: "POST", body: { order_id: order.id, items } });
    setMsg(t("common.saved"));
    await load();
  }

  if (!order) return <div className="container page">{msg || t("common.loading")}</div>;

  return (
    <div className="container page">
      <div className="card">
        <h2>#{order.id} · {order.vehicle}</h2>
        <p className="muted">{order.cities.map((c) => c.name).join(", ")} · {order.client?.name}</p>
        <div className="row">
          <button className={`seg ${!partial ? "active" : ""}`} onClick={() => setPartial(false)}>{t("seller.whole")}</button>
          <button className={`seg ${partial ? "active" : ""}`} onClick={() => setPartial(true)}>{t("seller.part")}</button>
        </div>
        {order.items.map((it) => {
          const a = answers[it.id] || emptyAnswer();
          const tone = a.availability === "YES" ? "yes" : a.availability === "PARTIAL" ? "partial" : a.availability === "NO" ? "no" : "wait";
          return (
            <div className={`offer tone-${tone}`} key={it.id}>
              {partial && (
                <label>
                  <input type="checkbox" checked={!!selected[it.id]} onChange={(e) => setSelected({ ...selected, [it.id]: e.target.checked })} /> {it.description}
                </label>
              )}
              {!partial && <b>{it.description}</b>}
              <div className="row tone-row">
                <button className={`seg yes ${a.availability === "YES" ? "active" : ""}`} onClick={() => setAns(it.id, { availability: "YES" })}>{t("seller.yes")}</button>
                <button className={`seg partial ${a.availability === "PARTIAL" ? "active" : ""}`} onClick={() => setAns(it.id, { availability: "PARTIAL" })}>{t("seller.partial")}</button>
                <button className={`seg no ${a.availability === "NO" ? "active" : ""}`} onClick={() => setAns(it.id, { availability: "NO" })}>{t("seller.no")}</button>
              </div>
              {a.availability !== "NO" && (
                <>
                  <label>{t("seller.price")}</label>
                  <input className="text-input" type="number" value={a.price} onChange={(e) => setAns(it.id, { price: e.target.value })} />
                  <div className="grid-2">
                    <div>
                      <label>{t("seller.condition")}</label>
                      <div className="row">
                        <button className={`seg ${a.condition === "NEW" ? "active" : ""}`} type="button" onClick={() => setAns(it.id, { condition: "NEW" })}>{t("seller.new")}</button>
                        <button className={`seg ${a.condition === "USED" ? "active" : ""}`} type="button" onClick={() => setAns(it.id, { condition: "USED" })}>{t("seller.used")}</button>
                      </div>
                    </div>
                    <div>
                      <label>{t("seller.original")}</label>
                      <div className="row">
                        <button className={`seg ${a.is_original ? "active" : ""}`} type="button" onClick={() => setAns(it.id, { is_original: true })}>{t("seller.original")}</button>
                        <button className={`seg ${a.is_original === false ? "active" : ""}`} type="button" onClick={() => setAns(it.id, { is_original: false })}>{t("seller.aftermarket")}</button>
                      </div>
                    </div>
                  </div>
                  <label>{t("seller.detail")}</label>
                  <textarea className="text-input" rows={3} value={a.detail} onChange={(e) => setAns(it.id, { detail: e.target.value })} />
                </>
              )}
            </div>
          );
        })}
        {msg && <p className="muted">{msg}</p>}
        <button className="btn" onClick={submit}>{t("seller.submit")}</button>
        {order.chats?.[0] && <Link style={{ marginLeft: 8 }} className="btn ghost" to={`/chats/${order.chats[0].id}`}>{t("common.chat")}</Link>}
      </div>
    </div>
  );
}

export function SellerProfilePage() {
  const { t } = useI18n();
  const [profile, setProfile] = useState(null);
  const [categories, setCategories] = useState([]);
  const [locations, setLocations] = useState([]);
  const [selectedCats, setSelectedCats] = useState([]);
  const [selectedCities, setSelectedCities] = useState([]);
  const [name, setName] = useState("");
  const [contact, setContact] = useState({ address: "", whatsapp: "", telegram: "", instagram: "", pickup_note: "", lat: "", lng: "" });

  useEffect(() => {
    Promise.all([api("/seller/profile"), api("/categories"), api("/locations")]).then(([p, cats, loc]) => {
      setProfile(p);
      setName(p.display_name);
      setContact({
        address: p.address || "",
        whatsapp: p.whatsapp || "",
        telegram: p.telegram || "",
        instagram: p.instagram || "",
        pickup_note: p.pickup_note || "",
        lat: p.lat || "",
        lng: p.lng || "",
      });
      setCategories(cats);
      setLocations(loc);
      setSelectedCats(cats.filter((c) => p.categories.includes(c.name) || p.categories.includes(c.name_ru)).map((c) => c.id));
      const cities = loc.flatMap((c) => c.regions.flatMap((r) => r.cities));
      setSelectedCities(cities.filter((c) => p.cities.includes(c.name) || p.cities.includes(c.name_ru)).map((c) => c.id));
    });
  }, []);

  async function save() {
    const p = await api("/seller/profile", {
      method: "PATCH",
      body: {
        display_name: name,
        category_ids: selectedCats,
        city_ids: selectedCities,
        address: contact.address,
        whatsapp: contact.whatsapp,
        telegram: contact.telegram,
        instagram: contact.instagram,
        pickup_note: contact.pickup_note,
        lat: contact.lat ? Number(contact.lat) : null,
        lng: contact.lng ? Number(contact.lng) : null,
      },
    });
    setProfile(p);
  }

  if (!profile) return <div className="container page">{t("common.loading")}</div>;
  const cities = locations.flatMap((c) => c.regions.flatMap((r) => r.cities));

  return (
    <div className="container page">
      <div className="card">
        <h2>{profile.display_name}</h2>
        <p>{t("seller.rating")}: <b>{profile.display_rating} / 5</b> ({profile.user_rating_count})</p>
        <p className="muted">{t("seller.completed")}: {profile.completed_orders_count || 0}</p>
        <label>{t("auth.name")}</label>
        <input className="text-input" value={name} onChange={(e) => setName(e.target.value)} />
        <label>Address</label>
        <input className="text-input" value={contact.address} onChange={(e) => setContact({ ...contact, address: e.target.value })} />
        <div className="grid-2">
          <div>
            <label>WhatsApp</label>
            <input className="text-input" value={contact.whatsapp} onChange={(e) => setContact({ ...contact, whatsapp: e.target.value })} />
          </div>
          <div>
            <label>Telegram</label>
            <input className="text-input" value={contact.telegram} onChange={(e) => setContact({ ...contact, telegram: e.target.value })} />
          </div>
        </div>
        <label>Instagram</label>
        <input className="text-input" value={contact.instagram} onChange={(e) => setContact({ ...contact, instagram: e.target.value })} />
        <label>Pickup</label>
        <input className="text-input" value={contact.pickup_note} onChange={(e) => setContact({ ...contact, pickup_note: e.target.value })} />
        <div className="cities" style={{ marginTop: 12 }}>
          {categories.map((c) => (
            <button key={c.id} className={`city ${selectedCats.includes(c.id) ? "on" : ""}`} onClick={() => setSelectedCats((ids) => ids.includes(c.id) ? ids.filter((x) => x !== c.id) : [...ids, c.id])}>{c.name}</button>
          ))}
        </div>
        <div className="cities" style={{ marginTop: 12 }}>
          {cities.map((c) => (
            <button key={c.id} className={`city ${selectedCities.includes(c.id) ? "on" : ""}`} onClick={() => setSelectedCities((ids) => ids.includes(c.id) ? ids.filter((x) => x !== c.id) : [...ids, c.id])}>{c.name}</button>
          ))}
        </div>
        <button className="btn" style={{ marginTop: 16 }} onClick={save}>{t("common.save")}</button>
      </div>
    </div>
  );
}
