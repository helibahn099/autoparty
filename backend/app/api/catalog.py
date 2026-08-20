from math import asin, cos, radians, sin, sqrt

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session, joinedload

from app.config import settings
from app.database import get_db
from app.i18n import localized_name, request_lang
from app.models import Category, City, Country, PopularPart, Region, SellerProfile, VehicleBrand, VehicleModel
from app.serializers import seller_public

router = APIRouter(prefix="/api", tags=["catalog"])


def _haversine_km(lat1, lng1, lat2, lng2) -> float:
    r = 6371.0
    dlat = radians(lat2 - lat1)
    dlng = radians(lng2 - lng1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlng / 2) ** 2
    return 2 * r * asin(sqrt(a))


@router.get("/meta")
def meta():
    return {
        "search_price": settings.SEARCH_PRICE_KGS,
        "currency": settings.SEARCH_CURRENCY,
        "become_seller_url": settings.SELLER_REGISTRATION_URL,
        "demo_payment": True,
        "payment_note": "QR/payment is a demo implementation and is not a real payment.",
        "languages": ["ru", "en", "ky"],
    }


@router.get("/categories")
def categories(request: Request, db: Session = Depends(get_db)):
    lang = request_lang(request)
    rows = db.query(Category).filter(Category.is_active.is_(True)).order_by(Category.name).all()
    return [
        {
            "id": c.id,
            "slug": c.slug,
            "name": localized_name(c, lang) or c.name,
            "name_ru": c.name,
            "name_en": c.name_en,
            "name_ky": c.name_ky,
        }
        for c in rows
    ]


@router.get("/locations")
def locations(request: Request, db: Session = Depends(get_db)):
    lang = request_lang(request)
    countries = db.query(Country).filter(Country.is_active.is_(True)).options(joinedload(Country.regions)).all()
    result = []
    for country in countries:
        regions_out = []
        for region in country.regions:
            if not region.is_active:
                continue
            cities = (
                db.query(City)
                .filter(City.region_id == region.id, City.is_active.is_(True))
                .order_by(City.name)
                .all()
            )
            regions_out.append(
                {
                    "id": region.id,
                    "name": localized_name(region, lang) or region.name,
                    "name_ru": region.name,
                    "cities": [
                        {
                            "id": c.id,
                            "name": localized_name(c, lang) or c.name,
                            "name_ru": c.name,
                            "name_en": c.name_en,
                            "name_ky": c.name_ky,
                            "lat": c.lat,
                            "lng": c.lng,
                            "search_radius_km": c.search_radius_km or 8,
                        }
                        for c in cities
                    ],
                }
            )
        result.append(
            {
                "id": country.id,
                "code": country.code,
                "name": localized_name(country, lang) or country.name,
                "regions": regions_out,
            }
        )
    return result


@router.get("/locations/nearest")
def nearest_city(
    request: Request,
    lat: float = Query(...),
    lng: float = Query(...),
    db: Session = Depends(get_db),
):
    lang = request_lang(request)
    cities = db.query(City).filter(City.is_active.is_(True), City.lat.isnot(None), City.lng.isnot(None)).all()
    if not cities:
        return {"city": None}
    best = min(cities, key=lambda c: _haversine_km(lat, lng, c.lat, c.lng))
    distance = _haversine_km(lat, lng, best.lat, best.lng)
    return {
        "city": {
            "id": best.id,
            "name": localized_name(best, lang) or best.name,
            "lat": best.lat,
            "lng": best.lng,
            "search_radius_km": best.search_radius_km or 8,
            "region": best.region.name if best.region else None,
        },
        "distance_km": round(distance, 2),
        "confident": distance <= 40,
    }


@router.get("/vehicles/brands")
def brands(db: Session = Depends(get_db)):
    rows = db.query(VehicleBrand).filter(VehicleBrand.is_active.is_(True)).order_by(VehicleBrand.name).all()
    return [{"id": b.id, "name": b.name} for b in rows]


@router.get("/vehicles/models")
def models(brand_id: int, db: Session = Depends(get_db)):
    rows = (
        db.query(VehicleModel)
        .filter(VehicleModel.brand_id == brand_id, VehicleModel.is_active.is_(True))
        .order_by(VehicleModel.name)
        .all()
    )
    return [
        {"id": m.id, "name": m.name, "brand_id": m.brand_id, "year_from": m.year_from, "year_to": m.year_to}
        for m in rows
    ]


@router.get("/parts/popular")
def popular_parts(request: Request, db: Session = Depends(get_db)):
    lang = request_lang(request)
    rows = (
        db.query(PopularPart)
        .options(joinedload(PopularPart.category))
        .order_by(PopularPart.sort_order, PopularPart.id)
        .all()
    )
    return [
        {
            "id": p.id,
            "name": localized_name(p, lang) or p.name,
            "name_ru": p.name,
            "category_id": p.category_id,
            "category": localized_name(p.category, lang) if p.category else None,
        }
        for p in rows
    ]


@router.get("/sellers/{seller_id}")
def public_seller(seller_id: int, db: Session = Depends(get_db)):
    seller = db.query(SellerProfile).filter(SellerProfile.id == seller_id).first()
    if not seller:
        raise HTTPException(status_code=404, detail="Продавец не найден")
    return seller_public(seller)
