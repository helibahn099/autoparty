import React, { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api";
import { useAuth } from "../auth";
import { useI18n } from "../i18n";

const YEARS = Array.from({ length: 27 }, (_, i) => 2026 - i);
const CITY_KEY = "avtoparty_city_ids";
const CONSENT_KEY = "avtoparty_cookie_ok";
const BISHKEK_CENTER = [42.8746, 74.5698];

function findBishkek(cities) {
  return (
    cities.find((c) => (c.name_ru || c.name) === "Бишкек") ||
    cities.find((c) => String(c.name_en || c.name || "").toLowerCase() === "bishkek") ||
    cities.find((c) => c.lat != null && Math.abs(c.lat - BISHKEK_CENTER[0]) < 0.05)
  );
}

function readSavedCities() {
  try {
    const raw = localStorage.getItem(CITY_KEY);
    if (raw) return JSON.parse(raw).map(Number).filter(Boolean);
  } catch {}
  return [];
}

function persistCities(ids, cookies) {
  localStorage.setItem(CITY_KEY, JSON.stringify(ids));
  if (cookies) {
    document.cookie = `avtoparty_city=${ids.join(",")};max-age=31536000;path=/;SameSite=Lax`;
  }
}

export default function SearchPage() {
  const { user } = useAuth();
  const { t, lang } = useI18n();
  const nav = useNavigate();
  const [meta, setMeta] = useState({ search_price: 200, currency: "KGS" });
  const [brands, setBrands] = useState([]);
  const [models, setModels] = useState([]);
  const [locations, setLocations] = useState([]);
  const [popular, setPopular] = useState([]);
  const [garage, setGarage] = useState([]);
  const [draft, setDraft] = useState("");
  const [items, setItems] = useState([]);
  const [selectedCars, setSelectedCars] = useState([]);
  const [sameParts, setSameParts] = useState(true);
  const [cityIds, setCityIds] = useState(readSavedCities);
  const [showAdd, setShowAdd] = useState(false);
  const [newCar, setNewCar] = useState({ brand_id: "", model_id: "", year: "", nickname: "" });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [geoState, setGeoState] = useState("idle");
  const [showPicker, setShowPicker] = useState(false);
  const [showCookie, setShowCookie] = useState(false);
  const [cityQuery, setCityQuery] = useState("");
  const [geoNote, setGeoNote] = useState("");

  const cities = useMemo(
    () => locations.flatMap((c) => (c.regions || []).flatMap((r) => (r.cities || []).map((city) => ({ ...city, region: r.name })))),
    [locations]
  );

  useEffect(() => {
    api("/meta").then(setMeta).catch(() => {});
    api("/vehicles/brands").then(setBrands).catch(() => {});
    api("/locations").then(setLocations).catch(() => {});
    api("/parts/popular").then(setPopular).catch(() => {});
  }, [lang]);

  useEffect(() => {
    if (!user) return;
    api("/garage")
      .then((rows) => {
        setGarage(rows);
        if (rows.length && selectedCars.length === 0) {
          const def = rows.find((r) => r.is_default) || rows[0];
          setSelectedCars([def.id]);
        }
      })
      .catch(() => {});
  }, [user]);

  function applyCities(ids, { askCookie = false } = {}) {
    const unique = [...new Set(ids)];
    setCityIds(unique);
    persistCities(unique, localStorage.getItem(CONSENT_KEY) === "1");
    if (askCookie && localStorage.getItem(CONSENT_KEY) == null) setShowCookie(true);
    setGeoState("idle");
  }

  useEffect(() => {
    if (!cities.length || cityIds.length) return;
    const bishkek = findBishkek(cities);
    if (bishkek) applyCities([bishkek.id]);
  }, [cities, cityIds.length]);

  function detectGeo() {
    setGeoNote("");
    setGeoState("detecting");
    if (!navigator.geolocation) {
      setGeoState("idle");
      setGeoNote(t("city.geoDenied"));
      return;
    }
    navigator.geolocation.getCurrentPosition(
      async (pos) => {
        try {
          const data = await api(`/locations/nearest?lat=${pos.coords.latitude}&lng=${pos.coords.longitude}`);
          if (data.city?.id) {
            applyCities([data.city.id], { askCookie: true });
            setShowPicker(false);
          } else {
            setGeoState("idle");
            setGeoNote(t("city.geoDenied"));
          }
        } catch {
          setGeoState("idle");
          setGeoNote(t("city.geoDenied"));
        }
      },
      () => {
        setGeoState("idle");
        setGeoNote(t("city.geoDenied"));
      },
      { timeout: 8000, maximumAge: 600000 }
    );
  }

  function addItem(name, categoryId) {
    const text = (name || draft).trim();
    if (!text) return;
    setItems((prev) => {
      if (prev.some((p) => p.description.toLowerCase() === text.toLowerCase())) return prev;
      return [...prev, { description: text, category_id: categoryId || null }];
    });
    setDraft("");
  }

  function toggleCar(id) {
    setSelectedCars((ids) => (ids.includes(id) ? ids.filter((x) => x !== id) : [...ids, id]));
  }

  function toggleCity(id) {
    applyCities(cityIds.includes(id) ? cityIds.filter((x) => x !== id) : [...cityIds, id]);
  }

  async function saveCar() {
    const row = await api("/garage", {
      method: "POST",
      body: {
        brand_id: newCar.brand_id ? Number(newCar.brand_id) : null,
        model_id: newCar.model_id ? Number(newCar.model_id) : null,
        year: newCar.year ? Number(newCar.year) : null,
        nickname: newCar.nickname || null,
      },
    });
    setGarage((g) => (g.some((x) => x.id === row.id) ? g : [...g, row]));
    setSelectedCars((ids) => (ids.includes(row.id) ? ids : [...ids, row.id]));
    setShowAdd(false);
    setNewCar({ brand_id: "", model_id: "", year: "", nickname: "" });
  }

  async function submit() {
    setError("");
    if (!user) {
      nav("/login");
      return;
    }
    let payloadItems = items;
    if (!payloadItems.length && draft.trim()) payloadItems = [{ description: draft.trim(), category_id: null }];
    if (!payloadItems.length) {
      setError(t("home.needPart"));
      return;
    }
    if (!selectedCars.length) {
      setError(t("home.needCar"));
      return;
    }
    if (!cityIds.length) {
      setError(t("home.needCity"));
      return;
    }
    setBusy(true);
    try {
      const batch = await api("/orders/batch", {
        method: "POST",
        body: {
          city_ids: cityIds,
          same_parts: sameParts,
          items: payloadItems,
          vehicles: selectedCars.map((id) => ({ garage_id: id })),
        },
      });
      nav(`/orders/${batch.pay_order_id}/pay`);
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }

  const filteredCities = cities.filter((c) => (c.name || "").toLowerCase().includes(cityQuery.trim().toLowerCase()));

  return (
    <div className="container page search-page">
      <div className="kicker">{t("nav.search")}</div>
      <h2 style={{ marginTop: 0 }}>{t("home.searchCta")}</h2>
      <p className="lede">{t("home.whatHint")}</p>

      <div className="card search-card">
        <div className="step">01 · {t("home.what")}</div>
        <input className="search-input" placeholder={t("home.placeholder")} value={draft} onChange={(e) => setDraft(e.target.value)} onKeyDown={(e) => e.key === "Enter" && addItem()} />
        <div className="chips" style={{ marginTop: 10 }}>
          {items.map((it, i) => (
            <span className="pill on" key={i}>
              {it.description}
              <button className="linkish" style={{ marginLeft: 8 }} onClick={() => setItems(items.filter((_, idx) => idx !== i))}>×</button>
            </span>
          ))}
        </div>
        <div className="popular" style={{ marginTop: 10 }}>
          {popular.slice(0, 10).map((p) => (
            <button key={p.id} className="pill" onClick={() => addItem(p.name, p.category_id)}>{p.name}</button>
          ))}
        </div>

        <div className="section">
          <div className="section-head">
            <div className="step">02 · {t("home.forCar")}</div>
            {user && <button className="seg" type="button" onClick={() => setShowAdd((v) => !v)}>{t("home.addCar")}</button>}
          </div>
          <p className="muted" style={{ marginTop: 0 }}>{t("home.forCarHint")}</p>
          {!user && <p className="muted">{t("home.needLogin")}</p>}
          <div className="chips">
            {garage.map((car) => (
              <button key={car.id} className={`car-chip ${selectedCars.includes(car.id) ? "on" : ""}`} onClick={() => toggleCar(car.id)}>{car.label}</button>
            ))}
            {user && garage.length === 0 && <span className="muted">{t("home.emptyGarage")}</span>}
          </div>
          {selectedCars.length > 1 && (
            <label style={{ display: "flex", gap: 8, alignItems: "center", marginTop: 10, textTransform: "none", letterSpacing: 0, color: "var(--ink)" }}>
              <input type="checkbox" checked={sameParts} onChange={(e) => setSameParts(e.target.checked)} />
              {t("home.sameParts")}
            </label>
          )}
          {showAdd && (
            <div className="add-car">
              <div className="grid-2">
                <select value={newCar.brand_id} onChange={(e) => setNewCar({ ...newCar, brand_id: e.target.value, model_id: "" })}>
                  <option value="">—</option>
                  {brands.map((b) => <option key={b.id} value={b.id}>{b.name}</option>)}
                </select>
                <select value={newCar.model_id} onChange={(e) => setNewCar({ ...newCar, model_id: e.target.value })}>
                  <option value="">—</option>
                  {models.map((m) => <option key={m.id} value={m.id}>{m.name}</option>)}
                </select>
                <select value={newCar.year} onChange={(e) => setNewCar({ ...newCar, year: e.target.value })}>
                  <option value="">—</option>
                  {YEARS.map((y) => <option key={y} value={y}>{y}</option>)}
                </select>
                <input className="text-input" value={newCar.nickname} onChange={(e) => setNewCar({ ...newCar, nickname: e.target.value })} />
              </div>
              <button className="btn small" style={{ marginTop: 10 }} type="button" onClick={saveCar}>{t("common.save")}</button>
            </div>
          )}
        </div>

        <div className="section">
          <div className="step">03 · {t("home.where")}</div>
          <p className="muted">{t("home.whereHint")}</p>
          {geoNote && <p className="muted">{geoNote}</p>}
          <div className="cities">
            {cities.slice(0, 12).map((c) => (
              <button key={c.id} className={`city ${cityIds.includes(c.id) ? "on" : ""}`} onClick={() => toggleCity(c.id)}>{c.name}</button>
            ))}
            <button className="seg" type="button" onClick={() => setShowPicker(true)}>{t("city.change")}</button>
            <button className="seg" type="button" disabled={geoState === "detecting"} onClick={detectGeo}>
              {geoState === "detecting" ? t("city.detecting") : t("city.allow")}
            </button>
          </div>
        </div>

        <div className="price-bar">
          <div>
            <div className="muted">{t("home.searchService")}{selectedCars.length > 1 ? ` · ${t("home.carsCount", { n: selectedCars.length })}` : ""}</div>
            <div className="price">{meta.search_price} {meta.currency}</div>
          </div>
          <button className="btn" disabled={busy} onClick={submit}>{busy ? t("home.creating") : t("home.pay")}</button>
        </div>
        {error && <p className="error">{error}</p>}
      </div>

      {showCookie && (
        <div className="card" style={{ marginTop: 12 }}>
          <b>{t("cookie.title")}</b>
          <p className="muted">{t("cookie.body")}</p>
          <div className="row">
            <button className="btn" type="button" onClick={() => { localStorage.setItem(CONSENT_KEY, "1"); persistCities(cityIds, true); setShowCookie(false); }}>{t("cookie.accept")}</button>
            <button className="btn ghost" type="button" onClick={() => { localStorage.setItem(CONSENT_KEY, "0"); setShowCookie(false); }}>{t("cookie.reject")}</button>
          </div>
        </div>
      )}

      {showPicker && (
        <div className="modal-back" onClick={() => setShowPicker(false)}>
          <div className="card modal-card" onClick={(e) => e.stopPropagation()}>
            <h3>{t("city.pickTitle")}</h3>
            <p className="muted">{t("city.pickHint")}</p>
            <input className="text-input" value={cityQuery} onChange={(e) => setCityQuery(e.target.value)} placeholder={t("city.pickTitle")} />
            <div className="cities" style={{ marginTop: 12, maxHeight: 280, overflow: "auto" }}>
              {filteredCities.map((c) => (
                <button key={c.id} className={`city ${cityIds.includes(c.id) ? "on" : ""}`} onClick={() => toggleCity(c.id)}>
                  {c.name}
                </button>
              ))}
            </div>
            <button className="btn" style={{ marginTop: 14 }} type="button" onClick={() => { if (cityIds.length) { applyCities(cityIds, { askCookie: true }); setShowPicker(false); } }}>{t("common.save")}</button>
          </div>
        </div>
      )}
    </div>
  );
}
