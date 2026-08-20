import React, { useEffect, useState } from "react";
import { Link, NavLink, Route, Routes, useParams } from "react-router-dom";
import { api, STATUS_LABEL } from "../api";

function AdminNav() {
  const items = [
    ["/admin", "Dashboard"],
    ["/admin/users", "Users"],
    ["/admin/sellers", "Sellers"],
    ["/admin/reports", "Reports"],
    ["/admin/false-answers", "False YES"],
    ["/admin/rotation", "Rotation"],
    ["/admin/orders", "Orders"],
    ["/admin/payments", "Payments"],
    ["/admin/chats", "Chats"],
    ["/admin/categories", "Categories"],
    ["/admin/locations", "Regions"],
    ["/admin/audit", "Audit"],
  ];
  return (
    <div className="admin-nav">
      {items.map(([to, label]) => (
        <NavLink key={to} to={to} end={to === "/admin"} className={({ isActive }) => `chip-btn ${isActive ? "active" : ""}`}>
          {label}
        </NavLink>
      ))}
    </div>
  );
}

function Dashboard() {
  const [d, setD] = useState(null);
  useEffect(() => {
    api("/admin/dashboard").then(setD);
  }, []);
  if (!d) return <p>Загрузка…</p>;
  const cards = [
    ["Пользователи", d.users],
    ["Продавцы", d.sellers],
    ["Подтверждённые", d.approved_sellers],
    ["Заказы", d.orders],
    ["Активные", d.active_orders],
    ["Завершённые", d.completed_orders],
    ["Жалобы", d.pending_reports],
    ["Ложные YES", d.false_answers],
    ["Платежи", d.payments],
    ["Сумма, сом", d.payments_sum],
  ];
  return (
    <div className="stats">
      {cards.map(([k, v]) => (
        <div className="stat" key={k}>
          <span className="muted">{k}</span>
          <b>{v}</b>
        </div>
      ))}
    </div>
  );
}

function Users() {
  const [rows, setRows] = useState([]);
  const load = () => api("/admin/users").then(setRows);
  useEffect(() => { load(); }, []);
  async function patch(id, body) {
    await api(`/admin/users/${id}`, { method: "PATCH", body });
    load();
  }
  return (
    <div className="table-wrap card">
      <table>
        <thead><tr><th>ID</th><th>Email</th><th>Имя</th><th>Роль</th><th>Статус</th><th></th></tr></thead>
        <tbody>
          {rows.map((u) => (
            <tr key={u.id}>
              <td>{u.id}</td>
              <td>{u.email}</td>
              <td>{u.name}</td>
              <td>
                <select value={u.role} onChange={(e) => patch(u.id, { role: e.target.value })}>
                  {["CLIENT", "SELLER", "ADMIN"].map((r) => <option key={r}>{r}</option>)}
                </select>
              </td>
              <td>{u.is_blocked ? "блок" : "активен"}</td>
              <td>
                {u.is_blocked
                  ? <button className="btn small" onClick={() => api(`/admin/users/${u.id}/unblock`, { method: "POST" }).then(load)}>разблок</button>
                  : <button className="btn small danger" onClick={() => api(`/admin/users/${u.id}/block`, { method: "POST" }).then(load)}>блок</button>}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function Sellers() {
  const [rows, setRows] = useState([]);
  const load = () => api("/admin/sellers").then(setRows);
  useEffect(() => { load(); }, []);
  async function patch(id, body) {
    await api(`/admin/sellers/${id}`, { method: "PATCH", body });
    load();
  }
  return (
    <div className="stack">
      {rows.map((s) => (
        <div className="card" key={s.id}>
          <div className="chat-row">
            <div>
              <b>{s.display_name}</b> · {s.email}
              <div className="muted">{s.cities.join(", ")} · {s.categories.join(", ")}</div>
              <div className="muted">рейтинг {s.display_rating}/5 · исполнено {s.completed_orders_count} · страйки {s.strike_count} · ложные {s.false_availability_count}</div>
              {s.address && <div className="muted">{s.address}</div>}
              {s.new_orders_blocked && <div className="error">новые заказы заблокированы до {s.new_orders_blocked_until}</div>}
            </div>
            <div>
              <span className="status">{s.status}</span>
              {s.status !== "APPROVED" && (
                <button className="btn small" onClick={() => api(`/admin/sellers/${s.id}/approve`, { method: "POST" }).then(load)}>Подтвердить</button>
              )}
            </div>
          </div>
          <label className="partner-row">
            <input type="checkbox" checked={!!s.is_partner} onChange={(e) => patch(s.id, { is_partner: e.target.checked, partner_level: e.target.checked ? (s.partner_level || 3) : null })} />
            Партнёрство
          </label>
          {s.is_partner && (
            <label>
              Уровень 1–5
              <input className="text-input" type="range" min={1} max={5} value={s.partner_level || 1} onChange={(e) => patch(s.id, { is_partner: true, partner_level: Number(e.target.value) })} />
              <b>{s.partner_level || 1}</b>
            </label>
          )}
          {s.new_orders_blocked && (
            <button className="btn small ghost" onClick={() => patch(s.id, { clear_new_orders_block: true })}>Снять блок новых заказов</button>
          )}
        </div>
      ))}
    </div>
  );
}

function Orders() {
  const [rows, setRows] = useState([]);
  useEffect(() => { api("/admin/orders").then(setRows); }, []);
  return (
    <div className="table-wrap card">
      <table>
        <thead><tr><th>ID</th><th>Клиент</th><th>Авто</th><th>Статус</th><th>Цена поиска</th><th></th></tr></thead>
        <tbody>
          {rows.map((o) => (
            <tr key={o.id}>
              <td>{o.id}</td>
              <td>{o.client?.name}</td>
              <td>{o.vehicle}</td>
              <td>{STATUS_LABEL[o.status]}</td>
              <td>{o.search_price} {o.currency}</td>
              <td><Link to={`/admin/orders/${o.id}`}>открыть</Link></td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function OrderView() {
  const { id } = useParams();
  const [o, setO] = useState(null);
  useEffect(() => { api(`/admin/orders/${id}`).then(setO); }, [id]);
  if (!o) return <p>Загрузка…</p>;
  return (
    <div className="card">
      <h3>Заказ #{o.id}</h3>
      <p>{o.vehicle} · {STATUS_LABEL[o.status]}</p>
      <p>Детали: {o.items.map((i) => i.description).join(", ")}</p>
      <p>Города: {o.cities.map((c) => c.name).join(", ")}</p>
      <h4>Распределение</h4>
      {(o.assignments || []).map((a) => (
        <div key={a.id} className="muted">seller {a.seller_id} · score {a.quality_score} · delay {a.delay_seconds}s · {a.status}</div>
      ))}
      <h4>Предложения</h4>
      {o.offers.map((off) => (
        <div key={off.id} className="offer">
          {off.seller?.display_name}: {off.items.map((i) => `${i.description}=${i.availability}${i.price ? " " + i.price : ""}`).join("; ")}
        </div>
      ))}
      <h4>Чаты</h4>
      {o.chats.map((c) => <div key={c.id}><Link to={`/chats/${c.id}`}>чат #{c.id} · {c.other_name}</Link></div>)}
    </div>
  );
}

function Payments() {
  const [rows, setRows] = useState([]);
  useEffect(() => { api("/admin/payments").then(setRows); }, []);
  return (
    <div className="table-wrap card">
      <table>
        <thead><tr><th>ID</th><th>Заказ</th><th>Сумма</th><th>Статус</th><th>Дата</th></tr></thead>
        <tbody>
          {rows.map((p) => (
            <tr key={p.id}>
              <td>{p.id}</td><td>{p.order_id}</td><td>{p.amount} {p.currency}</td><td>{p.status}</td>
              <td>{new Date(p.created_at).toLocaleString()}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function Chats() {
  const [rows, setRows] = useState([]);
  useEffect(() => { api("/admin/chats").then(setRows); }, []);
  return (
    <div className="stack">
      {rows.map((c) => (
        <Link key={c.id} className="card" to={`/chats/${c.id}`}>
          #{c.id} заказ {c.order_id} · {c.other_name} · {c.last_message}
        </Link>
      ))}
    </div>
  );
}

function Categories() {
  const [rows, setRows] = useState([]);
  const [name, setName] = useState("");
  const load = () => api("/admin/categories").then(setRows);
  useEffect(() => { load(); }, []);
  return (
    <div className="card">
      <div className="row">
        <input className="text-input" value={name} onChange={(e) => setName(e.target.value)} placeholder="Новая категория" />
        <button className="btn" onClick={() => api("/admin/categories", { method: "POST", body: { name } }).then(() => { setName(""); load(); })}>Добавить</button>
      </div>
      {rows.map((c) => (
        <div className="part-row" key={c.id}>
          <b>{c.name}</b>
          <button className="linkish" onClick={() => api(`/admin/categories/${c.id}`, { method: "DELETE" }).then(load)}>скрыть</button>
        </div>
      ))}
    </div>
  );
}

function Locations() {
  const [data, setData] = useState([]);
  const [name, setName] = useState("");
  const [regionId, setRegionId] = useState("");
  const load = () => api("/admin/locations").then(setData);
  useEffect(() => { load(); }, []);
  const regions = data.flatMap((c) => c.regions.map((r) => ({ ...r, country: c.name })));
  return (
    <div className="card">
      <div className="row">
        <select value={regionId} onChange={(e) => setRegionId(e.target.value)}>
          <option value="">Регион</option>
          {regions.map((r) => <option key={r.id} value={r.id}>{r.country} / {r.name}</option>)}
        </select>
        <input className="text-input" value={name} onChange={(e) => setName(e.target.value)} placeholder="Населённый пункт" />
        <button className="btn" onClick={() => api("/admin/cities", { method: "POST", body: { name, region_id: Number(regionId) } }).then(() => { setName(""); load(); })}>Добавить</button>
      </div>
      {data.map((c) => (
        <div key={c.id}>
          <h4>{c.name}</h4>
          {c.regions.map((r) => (
            <p key={r.id} className="muted"><b>{r.name}:</b> {r.cities.map((x) => x.name).join(", ")}</p>
          ))}
        </div>
      ))}
    </div>
  );
}

function Audit() {
  const [rows, setRows] = useState([]);
  useEffect(() => { api("/admin/audit-logs").then(setRows); }, []);
  return (
    <div className="table-wrap card">
      <table>
        <thead><tr><th>Время</th><th>Admin</th><th>Action</th><th>Target</th><th>Old</th><th>New</th></tr></thead>
        <tbody>
          {rows.map((l) => (
            <tr key={l.id}>
              <td>{new Date(l.created_at).toLocaleString()}</td>
              <td>{l.admin_email}</td>
              <td>{l.action}</td>
              <td>{l.target_type} {l.target_id}</td>
              <td><code>{JSON.stringify(l.old_value)}</code></td>
              <td><code>{JSON.stringify(l.new_value)}</code></td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function Reports() {
  const [rows, setRows] = useState([]);
  const load = () => api("/reports").then(setRows);
  useEffect(() => { load(); }, []);
  async function review(id, status) {
    await api(`/reports/${id}`, { method: "PATCH", body: { status } });
    load();
  }
  return (
    <div className="stack">
      {rows.length === 0 && <p className="muted">Жалоб нет</p>}
      {rows.map((r) => (
        <div className="card" key={r.id}>
          <div className="chat-row">
            <div>
              <b>{r.seller_name}</b> · {r.reason}
              <div className="muted">{r.reporter_name} · заказ #{r.order_id} · {r.comment}</div>
            </div>
            <span className={`status ${r.status === "CONFIRMED" ? "bad" : r.status === "PENDING" ? "warn" : ""}`}>{r.status}</span>
          </div>
          {r.status === "PENDING" && (
            <div className="row" style={{ marginTop: 10 }}>
              <button className="btn small" onClick={() => review(r.id, "CONFIRMED")}>Подтвердить</button>
              <button className="btn small ghost" onClick={() => review(r.id, "REJECTED")}>Отклонить</button>
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

function FalseAnswers() {
  const [data, setData] = useState(null);
  useEffect(() => { api("/reports/false-answers").then(setData); }, []);
  if (!data) return <p>Загрузка…</p>;
  return (
    <div className="card">
      <h3>Ложные «есть»: {data.total}</h3>
      {data.sellers.map((s) => (
        <div className="offer tone-no" key={s.seller_id}>
          <b>{s.seller_name}</b> · {s.count} · рейтинг {s.display_rating}
          {s.reports.map((r) => (
            <div className="muted" key={r.id}>#{r.id} заказ {r.order_id} · {r.comment} · {r.reporter_name}</div>
          ))}
        </div>
      ))}
    </div>
  );
}

function Rotation() {
  const [s, setS] = useState(null);
  const load = () => api("/admin/rotation").then(setS);
  useEffect(() => { load(); }, []);
  async function save(patch) {
    const next = await api("/admin/rotation", { method: "PATCH", body: patch });
    setS(next);
  }
  if (!s) return <p>Загрузка…</p>;
  return (
    <div className="card">
      <h3>Ротация заказов</h3>
      <p className="muted">Пока оплаченных поисков меньше порога — запросы уходят всем подходящим. После порога продавцы, которые недавно много получали, видят заказ позже. Партнёры из этой задержки исключены.</p>
      <p>Сейчас оплаченных поисков: <b>{s.current_paid_orders}</b> · ротация {s.rotation_active ? "включена" : "ещё выключена"}</p>
      <label>Включать после N заказов (0 = сразу)</label>
      <input className="text-input" type="number" defaultValue={s.rotation_after_orders} onBlur={(e) => save({ rotation_after_orders: Number(e.target.value) })} />
      <label>Окно учёта, часов</label>
      <input className="text-input" type="number" defaultValue={s.rotation_lookback_hours} onBlur={(e) => save({ rotation_lookback_hours: Number(e.target.value) })} />
      <label>Макс. доп. задержка, сек</label>
      <input className="text-input" type="number" defaultValue={s.rotation_max_extra_delay} onBlur={(e) => save({ rotation_max_extra_delay: Number(e.target.value) })} />
    </div>
  );
}

export default function AdminApp() {
  return (
    <div className="container page">
      <h2>Админ-панель</h2>
      <AdminNav />
      <Routes>
        <Route index element={<Dashboard />} />
        <Route path="users" element={<Users />} />
        <Route path="sellers" element={<Sellers />} />
        <Route path="reports" element={<Reports />} />
        <Route path="false-answers" element={<FalseAnswers />} />
        <Route path="rotation" element={<Rotation />} />
        <Route path="orders" element={<Orders />} />
        <Route path="orders/:id" element={<OrderView />} />
        <Route path="payments" element={<Payments />} />
        <Route path="chats" element={<Chats />} />
        <Route path="categories" element={<Categories />} />
        <Route path="locations" element={<Locations />} />
        <Route path="audit" element={<Audit />} />
      </Routes>
    </div>
  );
}
