export async function api(path, { method = "GET", body, form } = {}) {
  const token = localStorage.getItem("token");
  const headers = {
    "Accept-Language": localStorage.getItem("avtoparty_lang") || "ru",
  };
  if (token) headers.Authorization = `Bearer ${token}`;
  let payload;
  if (form) {
    payload = form;
  } else if (body !== undefined) {
    headers["Content-Type"] = "application/json";
    payload = JSON.stringify(body);
  }
  const res = await fetch(`/api${path}`, { method, headers, body: payload });
  const text = await res.text();
  let data = null;
  try {
    data = text ? JSON.parse(text) : null;
  } catch {
    data = { detail: text };
  }
  if (!res.ok) {
    const detail = data?.detail;
    const msg = Array.isArray(detail) ? detail.map((d) => d.msg).join(", ") : detail || "Ошибка запроса";
    throw new Error(typeof msg === "string" ? msg : JSON.stringify(msg));
  }
  return data;
}

export function offerTone(offer) {
  if (offer?.tone) return offer.tone;
  const av = (offer?.items || []).map((i) => i.availability);
  if (!av.length) return "wait";
  if (av.every((a) => a === "YES")) return "yes";
  if (av.every((a) => a === "NO")) return "no";
  return "partial";
}

export const STATUS_LABEL = {
  DRAFT: "Черновик",
  WAITING_FOR_PAYMENT: "Ожидает оплаты",
  PAID: "Оплачен",
  SEARCHING: "Ищем продавцов",
  OFFERS_RECEIVED: "Есть предложения",
  SELLER_SELECTED: "Продавец выбран",
  COMPLETED: "Завершён",
  CANCELLED: "Отменён",
  EXPIRED: "Истёк",
};
