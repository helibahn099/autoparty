from datetime import datetime
from typing import Any

from pydantic import BaseModel, EmailStr, Field

from app.models import Availability, OrderStatus, PartCondition, PaymentStatus, SearchMode, SellerStatus, UserRole


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: "UserOut"


class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)
    name: str = Field(min_length=2, max_length=120)
    phone: str | None = Field(default=None, max_length=40)


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: int
    email: str
    name: str
    phone: str | None
    role: UserRole
    is_active: bool
    is_blocked: bool
    seller_status: SellerStatus | None = None

    class Config:
        from_attributes = True


class ProfileUpdateIn(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    phone: str | None = Field(default=None, max_length=40)


class OrderItemIn(BaseModel):
    description: str = Field(min_length=2, max_length=500)
    category_id: int | None = None


class OrderCreateIn(BaseModel):
    search_mode: SearchMode = SearchMode.SINGLE
    items: list[OrderItemIn]
    city_ids: list[int]
    vehicle_brand_id: int | None = None
    vehicle_model_id: int | None = None
    vehicle_year: int | None = None
    vehicle_text: str | None = Field(default=None, max_length=255)
    save_to_garage: bool = True


class VehicleSearchIn(BaseModel):
    garage_id: int | None = None
    vehicle_brand_id: int | None = None
    vehicle_model_id: int | None = None
    vehicle_year: int | None = None
    vehicle_text: str | None = Field(default=None, max_length=255)
    items: list[OrderItemIn] | None = None


class BatchCreateIn(BaseModel):
    city_ids: list[int]
    same_parts: bool = True
    items: list[OrderItemIn] = []
    vehicles: list[VehicleSearchIn]


class GarageIn(BaseModel):
    brand_id: int | None = None
    model_id: int | None = None
    year: int | None = None
    nickname: str | None = Field(default=None, max_length=80)
    is_default: bool = False


class OfferItemIn(BaseModel):
    order_item_id: int
    availability: Availability
    price: float | None = None
    comment: str | None = Field(default=None, max_length=500)
    detail: str | None = Field(default=None, max_length=2000)
    condition: PartCondition | None = None
    is_original: bool | None = None


class OfferCreateIn(BaseModel):
    order_id: int
    items: list[OfferItemIn]


class SelectSellerIn(BaseModel):
    offer_id: int


class RatingIn(BaseModel):
    order_id: int
    seller_id: int
    score: int = Field(ge=1, le=5)
    comment: str | None = Field(default=None, max_length=500)


class SellerProfileUpdateIn(BaseModel):
    display_name: str | None = Field(default=None, min_length=2, max_length=160)
    category_ids: list[int] | None = None
    city_ids: list[int] | None = None
    address: str | None = Field(default=None, max_length=255)
    lat: float | None = None
    lng: float | None = None
    whatsapp: str | None = Field(default=None, max_length=40)
    telegram: str | None = Field(default=None, max_length=80)
    instagram: str | None = Field(default=None, max_length=80)
    pickup_note: str | None = Field(default=None, max_length=255)


class AdminUserUpdateIn(BaseModel):
    name: str | None = None
    phone: str | None = None
    role: UserRole | None = None
    is_active: bool | None = None
    is_blocked: bool | None = None


class AdminSellerUpdateIn(BaseModel):
    display_name: str | None = None
    status: SellerStatus | None = None
    category_ids: list[int] | None = None
    city_ids: list[int] | None = None
    is_partner: bool | None = None
    partner_level: int | None = Field(default=None, ge=1, le=5)
    strike_count: int | None = Field(default=None, ge=0)
    clear_new_orders_block: bool | None = None


class ReportIn(BaseModel):
    seller_id: int
    order_id: int | None = None
    chat_id: int | None = None
    reason: str = Field(min_length=3, max_length=40)
    comment: str | None = Field(default=None, max_length=1000)


class ReportReviewIn(BaseModel):
    status: str
    note: str | None = None


class RotationSettingsIn(BaseModel):
    rotation_after_orders: int | None = Field(default=None, ge=0, le=100000)
    rotation_lookback_hours: int | None = Field(default=None, ge=1, le=720)
    rotation_max_extra_delay: int | None = Field(default=None, ge=0, le=600)
    strike_limit: int | None = Field(default=None, ge=1, le=20)
    strike_ban_days: int | None = Field(default=None, ge=1, le=365)


class CategoryIn(BaseModel):
    name: str
    name_en: str | None = None
    name_ky: str | None = None
    slug: str | None = None
    is_active: bool = True


class CityIn(BaseModel):
    name: str
    name_en: str | None = None
    name_ky: str | None = None
    region_id: int
    is_active: bool = True
    lat: float | None = None
    lng: float | None = None


class RegionIn(BaseModel):
    name: str
    country_id: int
    is_active: bool = True


class OrderStatusIn(BaseModel):
    status: OrderStatus


class MessageOut(BaseModel):
    id: int
    chat_id: int
    sender_id: int
    text: str | None
    created_at: datetime
    attachments: list[dict[str, Any]] = []
