const BISHKEK = { lat: 42.8746, lng: 74.5698 };

let pending = null;

export function getGoogleMapsKey() {
  return String(import.meta.env.VITE_GOOGLE_MAPS_API_KEY || "").trim();
}

export function toLatLng(center) {
  if (!center) return BISHKEK;
  if (Array.isArray(center) && center.length >= 2) {
    return { lat: Number(center[0]), lng: Number(center[1]) };
  }
  if (center.lat != null && center.lng != null) {
    return { lat: Number(center.lat), lng: Number(center.lng) };
  }
  return BISHKEK;
}

function mapsLanguage(lang) {
  if (lang === "en") return "en";
  if (lang === "ky") return "ky";
  return "ru";
}

export function loadGoogleMaps(lang = "ru") {
  const key = getGoogleMapsKey();
  if (!key) return Promise.reject(new Error("missing-key"));
  if (window.google?.maps?.Map) return Promise.resolve(window.google.maps);
  if (pending) return pending;

  pending = new Promise((resolve, reject) => {
    const existing = document.querySelector("script[data-avtoparty-gmaps]");
    if (existing) {
      existing.addEventListener("load", () => resolve(window.google.maps), { once: true });
      existing.addEventListener("error", () => reject(new Error("load-failed")), { once: true });
      return;
    }
    const script = document.createElement("script");
    const params = new URLSearchParams({
      key,
      v: "weekly",
      language: mapsLanguage(lang),
      region: "KG",
    });
    script.src = `https://maps.googleapis.com/maps/api/js?${params}`;
    script.async = true;
    script.dataset.avtopartyGmaps = "1";
    script.onload = () => {
      if (!window.google?.maps?.Map) {
        pending = null;
        reject(new Error("load-failed"));
        return;
      }
      resolve(window.google.maps);
    };
    script.onerror = () => {
      pending = null;
      reject(new Error("load-failed"));
    };
    document.head.appendChild(script);
  });

  return pending;
}

export function createHtmlMarkerClass(maps) {
  return class HtmlMarker extends maps.OverlayView {
    constructor({ position, html, map, onClick }) {
      super();
      this.position = position instanceof maps.LatLng ? position : new maps.LatLng(position.lat, position.lng);
      this.html = html;
      this.onClick = onClick;
      this.div = null;
      this.setMap(map);
    }

    onAdd() {
      this.div = document.createElement("div");
      this.div.className = "map-pin-wrap";
      this.div.innerHTML = this.html;
      this.div.addEventListener("click", (e) => {
        e.stopPropagation();
        this.onClick?.();
      });
      this.getPanes().overlayMouseTarget.appendChild(this.div);
    }

    draw() {
      const projection = this.getProjection();
      if (!projection || !this.div) return;
      const point = projection.fromLatLngToDivPixel(this.position);
      if (!point) return;
      this.div.style.left = `${point.x}px`;
      this.div.style.top = `${point.y}px`;
    }

    onRemove() {
      this.div?.remove();
      this.div = null;
    }
  };
}
