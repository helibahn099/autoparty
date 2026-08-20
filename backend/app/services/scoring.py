"""Deterministic seller quality scoring.

score (0-100) =
    0.40 * rating_component
  + 0.12 * rating_volume_component
  + 0.20 * response_rate_component
  + 0.08 * speed_component
  + 0.12 * experience_component      # fulfilled / selected orders
  + partner bonus
  − report penalty

An honest "нет в наличии" still increases response_rate and activity.
"""

from app.config import settings
from app.models import SellerProfile


RATING_WEIGHT = 0.40
VOLUME_WEIGHT = 0.12
RESPONSE_WEIGHT = 0.20
SPEED_WEIGHT = 0.08
EXPERIENCE_WEIGHT = 0.12


def compute_quality_score(seller: SellerProfile) -> float:
    rating_src = seller.display_rating if seller.display_rating else seller.user_rating_avg
    rating_component = (float(rating_src or 0) / 5.0) * 100.0
    volume_component = min((seller.user_rating_count or 0) / 20.0, 1.0) * 100.0
    assigned = max(seller.assigned_requests_count or 0, 1)
    responded = seller.responded_requests_count or 0
    response_component = min(responded / assigned, 1.0) * 100.0
    avg_sec = float(seller.avg_response_seconds or 0)
    speed_component = max(0.0, 1.0 - min(avg_sec / 3600.0, 1.0)) * 100.0
    experience_component = min((seller.completed_orders_count or seller.processed_requests_count or 0) / 40.0, 1.0) * 100.0

    score = (
        RATING_WEIGHT * rating_component
        + VOLUME_WEIGHT * volume_component
        + RESPONSE_WEIGHT * response_component
        + SPEED_WEIGHT * speed_component
        + EXPERIENCE_WEIGHT * experience_component
    )
    score -= min((seller.confirmed_reports_count or 0) * 12.0, 40.0)
    score -= min((seller.false_availability_count or 0) * 8.0, 24.0)
    if seller.is_partner:
        score += (seller.partner_level or 1) * 4.0
    return round(max(0.0, min(100.0, score)), 2)


def compute_activity_score(seller: SellerProfile) -> float:
    assigned = max(seller.assigned_requests_count or 0, 1)
    response_rate = min((seller.responded_requests_count or 0) / assigned, 1.0)
    avg_sec = float(seller.avg_response_seconds or 0)
    speed = max(0.0, 1.0 - min(avg_sec / 3600.0, 1.0))
    volume = min((seller.completed_orders_count or seller.processed_requests_count or 0) / 50.0, 1.0)
    score = (0.50 * response_rate + 0.30 * speed + 0.20 * volume) * 100.0
    return round(score, 2)


def delay_for_score(score: float) -> int:
    if score >= settings.DISTRIBUTION_HIGH_THRESHOLD:
        return settings.DISTRIBUTION_HIGH_DELAY_SECONDS
    if score >= settings.DISTRIBUTION_MEDIUM_THRESHOLD:
        return settings.DISTRIBUTION_MEDIUM_DELAY_SECONDS
    return settings.DISTRIBUTION_LOW_DELAY_SECONDS


def refresh_seller_scores(seller: SellerProfile) -> None:
    seller.activity_score = compute_activity_score(seller)
    seller.quality_score = compute_quality_score(seller)
