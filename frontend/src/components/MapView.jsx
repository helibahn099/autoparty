import React, { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useI18n } from "../i18n";
import { createHtmlMarkerClass, getGoogleMapsKey, loadGoogleMaps, toLatLng } from "../maps/loadGoogleMaps";

function pinClass(kind) {
  if (kind === "mine") return "map-pin mine";
  if (kind === "partner") return "map-pin partner";
  if (kind === "city") return "map-pin city";
  return "map-pin";
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function popupHtml(p, t) {
  const parts = (p.parts || []).slice(0, 3).join(", ");
  const price = p.price_from ? t("common.priceFrom", { price: p.price_from }) : "";
  return `
    <div class="map-pop">
      <b>${escapeHtml(p.title)}</b>
      <div class="muted">${escapeHtml(p.subtitle)}</div>
      ${p.vehicle ? `<div class="muted">${escapeHtml(p.vehicle)}</div>` : ""}
      ${parts ? `<div>${escapeHtml(parts)}</div>` : ""}
      ${price ? `<div><b>${escapeHtml(price)}</b></div>` : ""}
    </div>`;
}

export default function MapView({
  data,
  height = 280,
  interactive = true,
  onSelect,
  onCityClick,
  selectedCityIds = [],
  fill = false,
  showCities = true,
}) {
  const nav = useNavigate();
  const { t, lang } = useI18n();
  const langRef = useRef(lang);
  const ref = useRef(null);
  const mapRef = useRef(null);
  const overlaysRef = useRef([]);
  const infoRef = useRef(null);
  const [status, setStatus] = useState(() => (getGoogleMapsKey() ? "loading" : "missing-key"));

  useEffect(() => {
    if (!ref.current || !getGoogleMapsKey()) return undefined;
    let cancelled = false;
    let ro;

    loadGoogleMaps(langRef.current)
      .then((maps) => {
        if (cancelled || !ref.current) return;
        const map = new maps.Map(ref.current, {
          center: toLatLng(),
          zoom: 12,
          disableDefaultUI: true,
          zoomControl: interactive,
          fullscreenControl: false,
          mapTypeControl: false,
          streetViewControl: false,
          clickableIcons: false,
          gestureHandling: interactive ? "greedy" : "none",
          keyboardShortcuts: interactive,
          backgroundColor: "#dfe6ee",
        });
        mapRef.current = map;
        infoRef.current = new maps.InfoWindow({ maxWidth: 280 });
        ro = new ResizeObserver(() => {
          maps.event.trigger(map, "resize");
        });
        ro.observe(ref.current);
        window.gm_authFailure = () => {
          if (!cancelled) setStatus("error");
        };
        setStatus("ready");
      })
      .catch((err) => {
        if (cancelled) return;
        setStatus(err.message === "missing-key" ? "missing-key" : "error");
      });

    return () => {
      cancelled = true;
      ro?.disconnect();
      overlaysRef.current.forEach((item) => item.setMap?.(null));
      overlaysRef.current = [];
      infoRef.current?.close();
      infoRef.current = null;
      mapRef.current = null;
    };
  }, [interactive]);

  useEffect(() => {
    const map = mapRef.current;
    const maps = window.google?.maps;
    if (status !== "ready" || !map || !maps || !data) return;

    overlaysRef.current.forEach((item) => item.setMap?.(null));
    overlaysRef.current = [];
    infoRef.current?.close();

    const HtmlMarker = createHtmlMarkerClass(maps);
    const bounds = new maps.LatLngBounds();
    let boundCount = 0;
    const selected = new Set(selectedCityIds);

    if (showCities) {
      (data.cities || []).forEach((c) => {
        if (c.lat == null) return;
        const on = selected.has(c.id);
        const circle = new maps.Circle({
          map,
          center: { lat: c.lat, lng: c.lng },
          radius: (c.search_radius_km || 8) * 1000,
          strokeColor: on ? "#2ecc71" : "#5d6678",
          strokeWeight: on ? 2 : 1,
          strokeOpacity: 0.9,
          fillColor: on ? "#2ecc71" : "#5d6678",
          fillOpacity: on ? 0.2 : 0.06,
          clickable: true,
        });
        circle.addListener("click", () => {
          infoRef.current?.setContent(`<div class="map-pop"><b>${escapeHtml(c.name)}</b></div>`);
          infoRef.current?.setPosition({ lat: c.lat, lng: c.lng });
          infoRef.current?.open({ map });
          onCityClick?.(c);
        });
        overlaysRef.current.push(circle);
        if (on) {
          bounds.extend({ lat: c.lat, lng: c.lng });
          boundCount += 1;
        }
      });
    }

    (data.points || []).forEach((p) => {
      const position = { lat: p.lat, lng: p.lng };
      const marker = new HtmlMarker({
        map,
        position,
        html: `<div class="${pinClass(p.kind)}"></div>`,
        onClick: () => {
          infoRef.current?.setContent(popupHtml(p, t));
          infoRef.current?.setPosition(position);
          infoRef.current?.open({ map });
          onSelect?.(p);
        },
      });
      overlaysRef.current.push(marker);
      bounds.extend(position);
      boundCount += 1;
    });

    if (boundCount === 1) {
      map.setCenter(bounds.getCenter());
      map.setZoom(12);
    } else if (boundCount > 1) {
      map.fitBounds(bounds, { top: 48, right: 48, bottom: 48, left: 48 });
      maps.event.addListenerOnce(map, "bounds_changed", () => {
        if (map.getZoom() > 13) map.setZoom(13);
      });
    } else if (data.center) {
      map.setCenter(toLatLng(data.center));
      map.setZoom(data.zoom || 11);
    }
  }, [data, onSelect, onCityClick, selectedCityIds, showCities, status, t]);

  const style = fill ? { height: "100%" } : { height };
  const message = status === "missing-key" ? t("map.missingKey") : status === "error" ? t("map.loadError") : "";

  return (
    <div className={`map-wrap ${fill ? "fill" : ""}`} style={style}>
      <div ref={ref} className="map-canvas" />
      {message && (
        <div className="map-fallback" role="status">
          {message}
        </div>
      )}
      {!interactive && (
        <button className="map-open" type="button" onClick={() => nav("/map")}>
          {t("map.open")}
        </button>
      )}
    </div>
  );
}
