import React, { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { api } from "../api";
import { useAuth } from "../auth";
import { useI18n } from "../i18n";
import ReportModal from "../components/ReportModal";
import { SellerContacts } from "./MapPage";

export default function SellerPublicPage() {
  const { id } = useParams();
  const { user } = useAuth();
  const { t } = useI18n();
  const [seller, setSeller] = useState(null);
  const [report, setReport] = useState(false);

  useEffect(() => {
    api(`/sellers/${id}`).then(setSeller).catch(() => {});
  }, [id]);

  if (!seller) return <div className="container page">{t("common.loading")}</div>;

  return (
    <div className="container page">
      <div className="card">
        <div className="step">{t("seller.profile")}</div>
        <h2 style={{ margin: "6px 0" }}>{seller.display_name}</h2>
        <p>
          {t("seller.rating")}: <b>{seller.display_rating} / 5</b>
          {seller.user_rating_count ? ` · ${seller.user_rating_count}` : ""}
        </p>
        <p className="muted">{t("seller.completed")}: {seller.completed_orders_count || 0}</p>
        {seller.address && <p><b>{seller.address}</b></p>}
        {seller.pickup_note && <p className="muted">{seller.pickup_note}</p>}
        <SellerContacts seller={seller} address={seller.address} />
        {user?.role === "CLIENT" && (
          <button className="btn ghost danger-outline" style={{ marginTop: 16 }} onClick={() => setReport(true)}>
            {t("common.report")}
          </button>
        )}
      </div>
      {report && <ReportModal sellerId={seller.id} onClose={() => setReport(false)} />}
    </div>
  );
}
