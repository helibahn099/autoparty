import enum
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    Index,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class UserRole(str, enum.Enum):
    CLIENT = "CLIENT"
    SELLER = "SELLER"
    ADMIN = "ADMIN"


class SellerStatus(str, enum.Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    BLOCKED = "BLOCKED"


class OrderStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    WAITING_FOR_PAYMENT = "WAITING_FOR_PAYMENT"
    PAID = "PAID"
    SEARCHING = "SEARCHING"
    OFFERS_RECEIVED = "OFFERS_RECEIVED"
    SELLER_SELECTED = "SELLER_SELECTED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"


class SearchMode(str, enum.Enum):
    SINGLE = "SINGLE"
    MULTIPLE = "MULTIPLE"


class OrderItemStatus(str, enum.Enum):
    PENDING = "PENDING"
    FOUND = "FOUND"
    NOT_FOUND = "NOT_FOUND"


class PaymentStatus(str, enum.Enum):
    PENDING = "PENDING"
    PAID = "PAID"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class Availability(str, enum.Enum):
    YES = "YES"
    NO = "NO"
    PARTIAL = "PARTIAL"


class PartCondition(str, enum.Enum):
    NEW = "NEW"
    USED = "USED"


class ReportReason(str, enum.Enum):
    WRONG_PART = "WRONG_PART"
    FALSE_AVAILABILITY = "FALSE_AVAILABILITY"
    OTHER = "OTHER"


class ReportStatus(str, enum.Enum):
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    REJECTED = "REJECTED"


class AssignmentStatus(str, enum.Enum):
    SCHEDULED = "SCHEDULED"
    DELIVERED = "DELIVERED"


class NotificationType(str, enum.Enum):
    NEW_MESSAGE = "NEW_MESSAGE"
    NEW_OFFER = "NEW_OFFER"
    ORDER_STATUS = "ORDER_STATUS"
    NEW_REQUEST = "NEW_REQUEST"
    SELLER_SELECTED = "SELLER_SELECTED"
    RATING = "RATING"
    REPORT = "REPORT"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    name: Mapped[str] = mapped_column(String(120))
    phone: Mapped[str | None] = mapped_column(String(40), nullable=True)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), default=UserRole.CLIENT, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_blocked: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    seller_profile: Mapped["SellerProfile | None"] = relationship(back_populates="user", uselist=False)
    orders: Mapped[list["Order"]] = relationship(back_populates="client", foreign_keys="Order.client_id")
    notifications: Mapped[list["Notification"]] = relationship(back_populates="user")
    garage: Mapped[list["UserVehicle"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class SellerProfile(Base):
    __tablename__ = "seller_profiles"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    display_name: Mapped[str] = mapped_column(String(160))
    status: Mapped[SellerStatus] = mapped_column(Enum(SellerStatus), default=SellerStatus.PENDING, index=True)
    user_rating_avg: Mapped[float] = mapped_column(Float, default=0.0)
    user_rating_count: Mapped[int] = mapped_column(Integer, default=0)
    activity_score: Mapped[float] = mapped_column(Float, default=0.0)
    quality_score: Mapped[float] = mapped_column(Float, default=50.0)
    assigned_requests_count: Mapped[int] = mapped_column(Integer, default=0)
    responded_requests_count: Mapped[int] = mapped_column(Integer, default=0)
    processed_requests_count: Mapped[int] = mapped_column(Integer, default=0)
    avg_response_seconds: Mapped[float] = mapped_column(Float, default=0.0)
    address: Mapped[str | None] = mapped_column(String(255), nullable=True)
    lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    lng: Mapped[float | None] = mapped_column(Float, nullable=True)
    whatsapp: Mapped[str | None] = mapped_column(String(40), nullable=True)
    telegram: Mapped[str | None] = mapped_column(String(80), nullable=True)
    instagram: Mapped[str | None] = mapped_column(String(80), nullable=True)
    pickup_note: Mapped[str | None] = mapped_column(String(255), nullable=True)
    strike_count: Mapped[int] = mapped_column(Integer, default=0)
    new_orders_blocked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_orders_count: Mapped[int] = mapped_column(Integer, default=0)
    confirmed_reports_count: Mapped[int] = mapped_column(Integer, default=0)
    false_availability_count: Mapped[int] = mapped_column(Integer, default=0)
    is_partner: Mapped[bool] = mapped_column(Boolean, default=False)
    partner_level: Mapped[int | None] = mapped_column(Integer, nullable=True)
    display_rating: Mapped[float] = mapped_column(Float, default=4.2)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    user: Mapped[User] = relationship(back_populates="seller_profile")
    categories: Mapped[list["SellerCategory"]] = relationship(back_populates="seller", cascade="all, delete-orphan")
    cities: Mapped[list["SellerCity"]] = relationship(back_populates="seller", cascade="all, delete-orphan")


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120))
    name_en: Mapped[str | None] = mapped_column(String(120), nullable=True)
    name_ky: Mapped[str | None] = mapped_column(String(120), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class SellerCategory(Base):
    __tablename__ = "seller_categories"
    __table_args__ = (UniqueConstraint("seller_id", "category_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    seller_id: Mapped[int] = mapped_column(ForeignKey("seller_profiles.id", ondelete="CASCADE"))
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id", ondelete="CASCADE"))

    seller: Mapped[SellerProfile] = relationship(back_populates="categories")
    category: Mapped[Category] = relationship()


class Country(Base):
    __tablename__ = "countries"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(8), unique=True)
    name: Mapped[str] = mapped_column(String(120))
    name_en: Mapped[str | None] = mapped_column(String(120), nullable=True)
    name_ky: Mapped[str | None] = mapped_column(String(120), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    regions: Mapped[list["Region"]] = relationship(back_populates="country")


class Region(Base):
    __tablename__ = "regions"

    id: Mapped[int] = mapped_column(primary_key=True)
    country_id: Mapped[int] = mapped_column(ForeignKey("countries.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(120))
    name_en: Mapped[str | None] = mapped_column(String(120), nullable=True)
    name_ky: Mapped[str | None] = mapped_column(String(120), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    country: Mapped[Country] = relationship(back_populates="regions")
    cities: Mapped[list["City"]] = relationship(back_populates="region")


class City(Base):
    __tablename__ = "cities"

    id: Mapped[int] = mapped_column(primary_key=True)
    region_id: Mapped[int] = mapped_column(ForeignKey("regions.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(120), index=True)
    name_en: Mapped[str | None] = mapped_column(String(120), nullable=True)
    name_ky: Mapped[str | None] = mapped_column(String(120), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    lng: Mapped[float | None] = mapped_column(Float, nullable=True)
    search_radius_km: Mapped[float] = mapped_column(Float, default=8.0)

    region: Mapped[Region] = relationship(back_populates="cities")


class SellerCity(Base):
    __tablename__ = "seller_cities"
    __table_args__ = (UniqueConstraint("seller_id", "city_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    seller_id: Mapped[int] = mapped_column(ForeignKey("seller_profiles.id", ondelete="CASCADE"))
    city_id: Mapped[int] = mapped_column(ForeignKey("cities.id", ondelete="CASCADE"))

    seller: Mapped[SellerProfile] = relationship(back_populates="cities")
    city: Mapped[City] = relationship()


class VehicleBrand(Base):
    __tablename__ = "vehicle_brands"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80), unique=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    models: Mapped[list["VehicleModel"]] = relationship(back_populates="brand")


class VehicleModel(Base):
    __tablename__ = "vehicle_models"

    id: Mapped[int] = mapped_column(primary_key=True)
    brand_id: Mapped[int] = mapped_column(ForeignKey("vehicle_brands.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(80))
    year_from: Mapped[int | None] = mapped_column(Integer, nullable=True)
    year_to: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    brand: Mapped[VehicleBrand] = relationship(back_populates="models")


class PopularPart(Base):
    __tablename__ = "popular_parts"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(160))
    name_en: Mapped[str | None] = mapped_column(String(160), nullable=True)
    name_ky: Mapped[str | None] = mapped_column(String(160), nullable=True)
    category_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id"), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    category: Mapped[Category | None] = relationship()


class UserVehicle(Base):
    __tablename__ = "user_vehicles"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    brand_id: Mapped[int | None] = mapped_column(ForeignKey("vehicle_brands.id"), nullable=True)
    model_id: Mapped[int | None] = mapped_column(ForeignKey("vehicle_models.id"), nullable=True)
    year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    nickname: Mapped[str | None] = mapped_column(String(80), nullable=True)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    user: Mapped[User] = relationship(back_populates="garage")
    brand: Mapped["VehicleBrand | None"] = relationship()
    model: Mapped["VehicleModel | None"] = relationship()


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    status: Mapped[OrderStatus] = mapped_column(Enum(OrderStatus), default=OrderStatus.WAITING_FOR_PAYMENT, index=True)
    search_mode: Mapped[SearchMode] = mapped_column(Enum(SearchMode), default=SearchMode.SINGLE)
    vehicle_brand_id: Mapped[int | None] = mapped_column(ForeignKey("vehicle_brands.id"), nullable=True)
    vehicle_model_id: Mapped[int | None] = mapped_column(ForeignKey("vehicle_models.id"), nullable=True)
    vehicle_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    vehicle_text: Mapped[str | None] = mapped_column(String(255), nullable=True)
    search_price: Mapped[float] = mapped_column(Numeric(12, 2))
    currency: Mapped[str] = mapped_column(String(8), default="KGS")
    selected_offer_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    batch_id: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)

    client: Mapped[User] = relationship(back_populates="orders", foreign_keys=[client_id])
    brand: Mapped[VehicleBrand | None] = relationship()
    model: Mapped[VehicleModel | None] = relationship()
    items: Mapped[list["OrderItem"]] = relationship(back_populates="order", cascade="all, delete-orphan")
    locations: Mapped[list["OrderLocation"]] = relationship(back_populates="order", cascade="all, delete-orphan")
    offers: Mapped[list["SellerOffer"]] = relationship(
        back_populates="order", foreign_keys="SellerOffer.order_id", cascade="all, delete-orphan"
    )
    chats: Mapped[list["Chat"]] = relationship(back_populates="order", cascade="all, delete-orphan")
    assignments: Mapped[list["OrderSellerAssignment"]] = relationship(back_populates="order", cascade="all, delete-orphan")
    payments: Mapped[list["Payment"]] = relationship(back_populates="order")


class OrderItem(Base):
    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), index=True)
    description: Mapped[str] = mapped_column(String(500))
    category_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id"), nullable=True)
    status: Mapped[OrderItemStatus] = mapped_column(Enum(OrderItemStatus), default=OrderItemStatus.PENDING)

    order: Mapped[Order] = relationship(back_populates="items")
    category: Mapped[Category | None] = relationship()


class OrderLocation(Base):
    __tablename__ = "order_locations"
    __table_args__ = (UniqueConstraint("order_id", "city_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"))
    city_id: Mapped[int] = mapped_column(ForeignKey("cities.id"))

    order: Mapped[Order] = relationship(back_populates="locations")
    city: Mapped[City] = relationship()


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    amount: Mapped[float] = mapped_column(Numeric(12, 2))
    currency: Mapped[str] = mapped_column(String(8), default="KGS")
    status: Mapped[PaymentStatus] = mapped_column(Enum(PaymentStatus), default=PaymentStatus.PENDING, index=True)
    demo_token: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    batch_id: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    order: Mapped[Order] = relationship(back_populates="payments")
    user: Mapped[User] = relationship()


class OrderSellerAssignment(Base):
    __tablename__ = "order_seller_assignments"
    __table_args__ = (UniqueConstraint("order_id", "seller_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), index=True)
    seller_id: Mapped[int] = mapped_column(ForeignKey("seller_profiles.id"), index=True)
    quality_score: Mapped[float] = mapped_column(Float, default=0.0)
    delay_seconds: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[AssignmentStatus] = mapped_column(Enum(AssignmentStatus), default=AssignmentStatus.SCHEDULED)
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    order: Mapped[Order] = relationship(back_populates="assignments")
    seller: Mapped[SellerProfile] = relationship()


class SellerOffer(Base):
    __tablename__ = "seller_offers"
    __table_args__ = (UniqueConstraint("order_id", "seller_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), index=True)
    seller_id: Mapped[int] = mapped_column(ForeignKey("seller_profiles.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    order: Mapped[Order] = relationship(back_populates="offers", foreign_keys=[order_id])
    seller: Mapped[SellerProfile] = relationship()
    items: Mapped[list["SellerOfferItem"]] = relationship(back_populates="offer", cascade="all, delete-orphan")


class SellerOfferItem(Base):
    __tablename__ = "seller_offer_items"
    __table_args__ = (UniqueConstraint("offer_id", "order_item_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    offer_id: Mapped[int] = mapped_column(ForeignKey("seller_offers.id", ondelete="CASCADE"))
    order_item_id: Mapped[int] = mapped_column(ForeignKey("order_items.id", ondelete="CASCADE"))
    availability: Mapped[Availability] = mapped_column(Enum(Availability))
    price: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    comment: Mapped[str | None] = mapped_column(String(500), nullable=True)
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    condition: Mapped[str | None] = mapped_column(String(20), nullable=True)
    is_original: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    photo_path: Mapped[str | None] = mapped_column(String(255), nullable=True)

    offer: Mapped[SellerOffer] = relationship(back_populates="items")
    order_item: Mapped[OrderItem] = relationship()


class Chat(Base):
    __tablename__ = "chats"
    __table_args__ = (UniqueConstraint("order_id", "seller_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), index=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    seller_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    seller_id: Mapped[int] = mapped_column(ForeignKey("seller_profiles.id"))
    offer_id: Mapped[int | None] = mapped_column(ForeignKey("seller_offers.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    last_message_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    order: Mapped[Order] = relationship(back_populates="chats")
    messages: Mapped[list["Message"]] = relationship(back_populates="chat", cascade="all, delete-orphan")
    participants: Mapped[list["ChatParticipant"]] = relationship(back_populates="chat", cascade="all, delete-orphan")


class ChatParticipant(Base):
    __tablename__ = "chat_participants"
    __table_args__ = (UniqueConstraint("chat_id", "user_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    chat_id: Mapped[int] = mapped_column(ForeignKey("chats.id", ondelete="CASCADE"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    last_read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    chat: Mapped[Chat] = relationship(back_populates="participants")
    user: Mapped[User] = relationship()


class Message(Base):
    __tablename__ = "messages"
    __table_args__ = (Index("ix_messages_chat_created", "chat_id", "created_at"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    chat_id: Mapped[int] = mapped_column(ForeignKey("chats.id", ondelete="CASCADE"), index=True)
    sender_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    text: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    chat: Mapped[Chat] = relationship(back_populates="messages")
    sender: Mapped[User] = relationship()
    attachments: Mapped[list["MessageAttachment"]] = relationship(back_populates="message", cascade="all, delete-orphan")


class MessageAttachment(Base):
    __tablename__ = "message_attachments"

    id: Mapped[int] = mapped_column(primary_key=True)
    message_id: Mapped[int] = mapped_column(ForeignKey("messages.id", ondelete="CASCADE"))
    file_path: Mapped[str] = mapped_column(String(255))
    mime_type: Mapped[str] = mapped_column(String(80))
    original_name: Mapped[str] = mapped_column(String(255))

    message: Mapped[Message] = relationship(back_populates="attachments")


class Rating(Base):
    __tablename__ = "ratings"
    __table_args__ = (UniqueConstraint("order_id", "seller_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"))
    client_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    seller_id: Mapped[int] = mapped_column(ForeignKey("seller_profiles.id"))
    score: Mapped[int] = mapped_column(Integer)
    comment: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    seller: Mapped[SellerProfile] = relationship()
    client: Mapped[User] = relationship()


class Notification(Base):
    __tablename__ = "notifications"
    __table_args__ = (Index("ix_notifications_user_read", "user_id", "is_read"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    type: Mapped[NotificationType] = mapped_column(Enum(NotificationType))
    title: Mapped[str] = mapped_column(String(200))
    body: Mapped[str] = mapped_column(String(500))
    payload: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    user: Mapped[User] = relationship(back_populates="notifications")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    admin_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    action: Mapped[str] = mapped_column(String(80), index=True)
    target_type: Mapped[str] = mapped_column(String(80))
    target_id: Mapped[str] = mapped_column(String(40))
    old_value: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    new_value: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)

    admin: Mapped[User] = relationship()


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(primary_key=True)
    reporter_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    seller_id: Mapped[int] = mapped_column(ForeignKey("seller_profiles.id"), index=True)
    order_id: Mapped[int | None] = mapped_column(ForeignKey("orders.id"), nullable=True)
    chat_id: Mapped[int | None] = mapped_column(ForeignKey("chats.id"), nullable=True)
    reason: Mapped[str] = mapped_column(String(40), index=True)
    comment: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default=ReportStatus.PENDING.value, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reviewed_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)

    seller: Mapped[SellerProfile] = relationship()
    reporter: Mapped[User] = relationship(foreign_keys=[reporter_id])


class PlatformSettings(Base):
    __tablename__ = "platform_settings"

    id: Mapped[int] = mapped_column(primary_key=True)
    rotation_after_orders: Mapped[int] = mapped_column(Integer, default=20)
    rotation_lookback_hours: Mapped[int] = mapped_column(Integer, default=24)
    rotation_max_extra_delay: Mapped[int] = mapped_column(Integer, default=40)
    strike_limit: Mapped[int] = mapped_column(Integer, default=3)
    strike_ban_days: Mapped[int] = mapped_column(Integer, default=30)
