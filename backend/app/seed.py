"""Idempotent demo seed. Safe to run on every container start."""

from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.config import settings
from app.database import SessionLocal
from app.models import (
    Availability,
    Category,
    Chat,
    ChatParticipant,
    City,
    Country,
    Message,
    Order,
    OrderItem,
    OrderItemStatus,
    OrderLocation,
    OrderStatus,
    OrderSellerAssignment,
    AssignmentStatus,
    Payment,
    PaymentStatus,
    PlatformSettings,
    PopularPart,
    Rating,
    Region,
    Report,
    SearchMode,
    SellerCategory,
    SellerCity,
    SellerOffer,
    SellerOfferItem,
    SellerProfile,
    SellerStatus,
    User,
    UserRole,
    UserVehicle,
    VehicleBrand,
    VehicleModel,
)
from app.schema_upgrade import ensure_schema
from app.services.auth import hash_password
from app.services.reputation import refresh_reputation
from app.services.scoring import refresh_seller_scores

DEMO_PASSWORD = settings.DEMO_PASSWORD

CATEGORIES = [
    ("consumables", "Расходники", "Consumables", "Сарптоочу материалдар"),
    ("engine", "Детали двигателя", "Engine parts", "Кыймылдаткыч тетиктери"),
    ("suspension", "Подвеска", "Suspension", "Асма"),
    ("brakes", "Тормозная система", "Brakes", "Тормоз системасы"),
    ("electrics", "Электрика", "Electrics", "Электрика"),
    ("body", "Кузовные детали", "Body parts", "Кузов тетиктери"),
    ("transmission", "Трансмиссия", "Transmission", "Трансмиссия"),
    ("cooling", "Система охлаждения", "Cooling", "Муздатуу системасы"),
    ("steering", "Рулевое управление", "Steering", "Руль башкаруусу"),
    ("optics", "Оптика", "Lights", "Оптика"),
    ("interior", "Салон", "Interior", "Салон"),
    ("tires", "Шины и диски", "Tires and wheels", "Дөңгөлөктөр жана дисктер"),
]

REGIONS_CITIES = {
    "город Бишкек": ["Бишкек"],
    "Чуйская область": ["Токмок", "Кант", "Кара-Балта", "Сокулук", "Шопоков", "Каинды", "Кемин"],
    "Ошская область": ["Ош", "Узген", "Кара-Суу", "Ноокат"],
    "Иссык-Кульская область": ["Каракол", "Чолпон-Ата", "Балыкчы"],
    "Джалал-Абадская область": ["Джалал-Абад", "Майлуу-Суу", "Кочкор-Ата", "Токтогул", "Кербен", "Таш-Кумыр"],
    "Нарынская область": ["Нарын", "Ат-Башы", "Кочкор"],
    "Таласская область": ["Талас"],
    "Баткенская область": ["Баткен", "Кызыл-Кия", "Исфана", "Сулюкта", "Кадамжай"],
}

REGION_I18N = {
    "город Бишкек": ("Bishkek city", "Бишкек шаары"),
    "Чуйская область": ("Chuy Region", "Чүй облусу"),
    "Ошская область": ("Osh Region", "Ош облусу"),
    "Иссык-Кульская область": ("Issyk-Kul Region", "Ысык-Көл облусу"),
    "Джалал-Абадская область": ("Jalal-Abad Region", "Жалал-Абад облусу"),
    "Нарынская область": ("Naryn Region", "Нарын облусу"),
    "Таласская область": ("Talas Region", "Талас облусу"),
    "Баткенская область": ("Batken Region", "Баткен облусу"),
}

CITY_I18N = {
    "Бишкек": ("Bishkek", "Бишкек"),
    "Ош": ("Osh", "Ош"),
    "Каракол": ("Karakol", "Каракол"),
    "Джалал-Абад": ("Jalal-Abad", "Жалал-Абад"),
    "Нарын": ("Naryn", "Нарын"),
    "Талас": ("Talas", "Талас"),
    "Баткен": ("Batken", "Баткен"),
    "Токмок": ("Tokmok", "Токмок"),
    "Кант": ("Kant", "Кант"),
    "Кара-Балта": ("Kara-Balta", "Кара-Балта"),
    "Узген": ("Uzgen", "Өзгөн"),
    "Чолпон-Ата": ("Cholpon-Ata", "Чолпон-Ата"),
    "Балыкчы": ("Balykchy", "Балыкчы"),
    "Кызыл-Кия": ("Kyzyl-Kiya", "Кызыл-Кыя"),
    "Сокулук": ("Sokuluk", "Сокулук"),
    "Шопоков": ("Shopokov", "Шопоков"),
    "Каинды": ("Kaindy", "Кайыңды"),
    "Кемин": ("Kemin", "Кемин"),
    "Кара-Суу": ("Kara-Suu", "Кара-Суу"),
    "Ноокат": ("Nookat", "Ноокат"),
    "Майлуу-Суу": ("Mayluu-Suu", "Майлуу-Суу"),
    "Кочкор-Ата": ("Kochkor-Ata", "Кочкор-Ата"),
    "Токтогул": ("Toktogul", "Токтогул"),
    "Кербен": ("Kerben", "Кербен"),
    "Таш-Кумыр": ("Tash-Kumyr", "Таш-Көмүр"),
    "Ат-Башы": ("At-Bashy", "Ат-Башы"),
    "Кочкор": ("Kochkor", "Кочкор"),
    "Исфана": ("Isfana", "Исфана"),
    "Сулюкта": ("Sulukta", "Сүлүктү"),
    "Кадамжай": ("Kadamjay", "Кадамжай"),
}

CITY_COORDS = {
    "Бишкек": (42.8746, 74.5698, 12),
    "Ош": (40.5283, 72.7985, 9),
    "Каракол": (42.4907, 78.3936, 7),
    "Джалал-Абад": (40.9330, 73.0000, 8),
    "Нарын": (41.4287, 75.9911, 6),
    "Талас": (42.5228, 72.2427, 6),
    "Баткен": (40.0664, 70.8194, 6),
    "Токмок": (42.8419, 75.3014, 6),
    "Кант": (42.8911, 74.8506, 5),
    "Кара-Балта": (42.8142, 73.8481, 6),
    "Узген": (40.7697, 73.3006, 5),
    "Чолпон-Ата": (42.6494, 77.0825, 5),
    "Балыкчы": (42.4602, 76.1871, 6),
    "Кызыл-Кия": (40.2568, 72.1279, 5),
    "Сокулук": (42.8630, 74.0050, 5),
    "Шопоков": (42.8540, 74.3180, 4),
    "Каинды": (42.8240, 73.6770, 4),
    "Кемин": (42.7840, 75.7680, 5),
    "Кара-Суу": (40.7050, 72.8700, 5),
    "Ноокат": (40.2660, 72.6180, 5),
    "Майлуу-Суу": (41.2560, 72.4430, 5),
    "Кочкор-Ата": (41.0370, 72.4830, 5),
    "Токтогул": (41.9040, 72.9400, 5),
    "Кербен": (41.5030, 71.7480, 5),
    "Таш-Кумыр": (41.3470, 72.2170, 5),
    "Ат-Башы": (41.1700, 75.8010, 5),
    "Кочкор": (42.2160, 75.7480, 5),
    "Исфана": (39.8390, 69.5270, 5),
    "Сулюкта": (39.9370, 69.5670, 5),
    "Кадамжай": (40.1330, 71.7330, 5),
}

SELLER_PLACES = {
    "seller1@autoparty.demo": {
        "address": "ул. Киевская 148, Бишкек",
        "lat": 42.8746,
        "lng": 74.5698,
        "whatsapp": "996555222001",
        "telegram": "avtosklad_kg",
        "instagram": "avtosklad.kg",
        "pickup_note": "Самовывоз 09:00–19:00, доставка по Бишкеку",
    },
    "seller2@autoparty.demo": {
        "address": "ул. Ахунбаева 95, Бишкек",
        "lat": 42.8554,
        "lng": 74.6122,
        "whatsapp": "996555222002",
        "telegram": "oshparts",
        "instagram": "osh.parts",
        "pickup_note": "Самовывоз и доставка по Бишкеку / Ошу",
    },
    "seller3@autoparty.demo": {
        "address": "ул. Гагарина 12, Каракол",
        "lat": 42.4907,
        "lng": 78.3936,
        "whatsapp": "996555222003",
        "telegram": "issykkulauto",
        "instagram": "issykkul.auto",
        "pickup_note": "Самовывоз, доставка по Иссык-Кулю",
    },
    "seller4@autoparty.demo": {
        "address": "ул. Ленина 220, Ош",
        "lat": 40.5283,
        "lng": 72.7985,
        "whatsapp": "996555222004",
        "telegram": "yugauto",
        "instagram": "yug.auto",
        "pickup_note": "Самовывоз в Оше, доставка по югу",
    },
}

VEHICLES = {
    "Toyota": ["Camry", "RAV4"],
    "Honda": ["CR-V", "Civic"],
    "BMW": ["3 Series", "X5"],
    "Mercedes-Benz": ["C-Class", "E-Class"],
    "Volkswagen": ["Polo", "Tiguan"],
    "Hyundai": ["Tucson", "Sonata"],
    "Kia": ["Sportage", "Rio"],
    "Lexus": ["RX"],
    "Nissan": ["Qashqai", "X-Trail"],
    "Chevrolet": ["Cruze"],
}

PARTS = [
    ("Тормозные колодки", "Brake pads", "Тормоз калодкалары", "brakes"),
    ("Тормозные диски", "Brake discs", "Тормоз дисктери", "brakes"),
    ("Амортизатор передний левый", "Front left shock absorber", "Алдыңкы сол амортизатор", "suspension"),
    ("Амортизатор передний правый", "Front right shock absorber", "Алдыңкы оң амортизатор", "suspension"),
    ("Стойка амортизатора", "Strut", "Амортизатор стойкасы", "suspension"),
    ("Свечи зажигания", "Spark plugs", "От алдыруу свечалары", "consumables"),
    ("Масляный фильтр", "Oil filter", "Май чыпкасы", "consumables"),
    ("Воздушный фильтр", "Air filter", "Аба чыпкасы", "consumables"),
    ("Аккумулятор", "Battery", "Аккумулятор", "electrics"),
    ("Генератор", "Alternator", "Генератор", "electrics"),
    ("Стартер", "Starter", "Стартер", "electrics"),
    ("Радиатор", "Radiator", "Радиатор", "cooling"),
    ("Фара", "Headlight", "Фара", "optics"),
    ("Бампер", "Bumper", "Бампер", "body"),
    ("Зеркало боковое", "Side mirror", "Каптал күзгү", "body"),
    ("Сцепление", "Clutch", "Муфта", "transmission"),
    ("Помпа", "Water pump", "Помпа", "cooling"),
    ("Рулевая рейка", "Steering rack", "Руль рейкасы", "steering"),
    ("Катушка зажигания", "Ignition coil", "От алдыруу катушкасы", "electrics"),
    ("Ступичный подшипник", "Wheel bearing", "Ступица подшипниги", "suspension"),
]


def get_or_create(db: Session, model, defaults: dict, **kwargs):
    row = db.query(model).filter_by(**kwargs).first()
    if row:
        return row, False
    row = model(**kwargs, **defaults)
    db.add(row)
    db.flush()
    return row, True


def seed_geo(db: Session):
    country, _ = get_or_create(
        db,
        Country,
        {"name": "Кыргызстан", "name_en": "Kyrgyzstan", "name_ky": "Кыргызстан", "is_active": True},
        code="KG",
    )
    country.name_en = "Kyrgyzstan"
    country.name_ky = "Кыргызстан"
    city_map: dict[str, City] = {}
    for region_name, cities in REGIONS_CITIES.items():
        en, ky = REGION_I18N.get(region_name, (region_name, region_name))
        region, _ = get_or_create(
            db, Region, {"is_active": True, "country_id": country.id, "name_en": en, "name_ky": ky}, name=region_name
        )
        if region.country_id != country.id:
            region.country_id = country.id
        region.name_en, region.name_ky = en, ky
        for city_name in cities:
            city, _ = get_or_create(db, City, {"is_active": True, "region_id": region.id}, name=city_name)
            coords = CITY_COORDS.get(city_name)
            if coords:
                city.lat, city.lng = coords[0], coords[1]
                city.search_radius_km = coords[2] if len(coords) > 2 else 8
            names = CITY_I18N.get(city_name)
            if names:
                city.name_en, city.name_ky = names
            city_map[city_name] = city
    return city_map


def seed_categories(db: Session) -> dict[str, Category]:
    result = {}
    for slug, name, name_en, name_ky in CATEGORIES:
        cat, _ = get_or_create(db, Category, {"name": name, "is_active": True}, slug=slug)
        cat.name = name
        cat.name_en = name_en
        cat.name_ky = name_ky
        result[slug] = cat
    return result


def seed_vehicles(db: Session):
    for brand_name, models in VEHICLES.items():
        brand, _ = get_or_create(db, VehicleBrand, {"is_active": True}, name=brand_name)
        for model_name in models:
            get_or_create(
                db,
                VehicleModel,
                {"is_active": True, "year_from": 2010, "year_to": 2026},
                brand_id=brand.id,
                name=model_name,
            )


def seed_parts(db: Session, categories: dict[str, Category]):
    for i, (name, name_en, name_ky, slug) in enumerate(PARTS):
        existing = db.query(PopularPart).filter(PopularPart.name == name).first()
        if existing:
            existing.name_en = name_en
            existing.name_ky = name_ky
            continue
        db.add(PopularPart(name=name, name_en=name_en, name_ky=name_ky, category_id=categories[slug].id, sort_order=i))


def ensure_user(db: Session, email: str, name: str, role: UserRole, phone: str) -> User:
    user = db.query(User).filter(User.email == email).first()
    if user:
        return user
    user = User(
        email=email,
        password_hash=hash_password(DEMO_PASSWORD),
        name=name,
        phone=phone,
        role=role,
        is_active=True,
        is_blocked=False,
    )
    db.add(user)
    db.flush()
    return user


def set_seller_links(db: Session, seller: SellerProfile, cat_slugs: list[str], city_names: list[str], categories, cities):
    db.query(SellerCategory).filter(SellerCategory.seller_id == seller.id).delete()
    db.query(SellerCity).filter(SellerCity.seller_id == seller.id).delete()
    for slug in cat_slugs:
        db.add(SellerCategory(seller_id=seller.id, category_id=categories[slug].id))
    for name in city_names:
        db.add(SellerCity(seller_id=seller.id, city_id=cities[name].id))


def ensure_seller(
    db: Session,
    user: User,
    display_name: str,
    stats: dict,
    cat_slugs: list[str],
    city_names: list[str],
    categories,
    cities,
) -> SellerProfile:
    seller = db.query(SellerProfile).filter(SellerProfile.user_id == user.id).first()
    if not seller:
        seller = SellerProfile(user_id=user.id, display_name=display_name, status=SellerStatus.APPROVED)
        db.add(seller)
        db.flush()
    seller.display_name = display_name
    seller.status = SellerStatus.APPROVED
    seller.user_rating_avg = stats["rating"]
    seller.user_rating_count = stats["rating_count"]
    seller.assigned_requests_count = stats["assigned"]
    seller.responded_requests_count = stats["responded"]
    seller.processed_requests_count = stats["processed"]
    seller.avg_response_seconds = stats["avg_sec"]
    set_seller_links(db, seller, cat_slugs, city_names, categories, cities)
    place = SELLER_PLACES.get(user.email)
    if place:
        seller.address = place["address"]
        seller.lat = place["lat"]
        seller.lng = place["lng"]
        seller.whatsapp = place["whatsapp"]
        seller.telegram = place["telegram"]
        seller.instagram = place["instagram"]
        seller.pickup_note = place["pickup_note"]
    if user.email == "seller1@autoparty.demo":
        seller.is_partner = True
        seller.partner_level = 5
    refresh_seller_scores(seller)
    return seller


def seed_demo_order(db: Session, client: User, sellers: list[SellerProfile], categories, cities, brand, model):
    marker = "DEMO-SEEDED-ORDER"
    existing = db.query(Order).filter(Order.vehicle_text == marker).first()
    if existing:
        return existing
    now = datetime.now(timezone.utc)
    order = Order(
        client_id=client.id,
        status=OrderStatus.COMPLETED,
        search_mode=SearchMode.MULTIPLE,
        vehicle_brand_id=brand.id if brand else None,
        vehicle_model_id=model.id if model else None,
        vehicle_year=2020,
        vehicle_text=marker,
        search_price=settings.SEARCH_PRICE_KGS,
        currency=settings.SEARCH_CURRENCY,
        created_at=now - timedelta(days=10),
        paid_at=now - timedelta(days=10),
        completed_at=now - timedelta(days=8),
    )
    db.add(order)
    db.flush()
    items_spec = [
        ("Передний левый амортизатор", "suspension"),
        ("Передний правый амортизатор", "suspension"),
        ("Тормозные диски", "brakes"),
        ("Тормозные колодки", "brakes"),
    ]
    items = []
    for desc, slug in items_spec:
        item = OrderItem(
            order_id=order.id,
            description=desc,
            category_id=categories[slug].id,
            status=OrderItemStatus.FOUND,
        )
        db.add(item)
        db.flush()
        items.append(item)
    db.add(OrderLocation(order_id=order.id, city_id=cities["Бишкек"].id))
    payment = Payment(
        order_id=order.id,
        user_id=client.id,
        amount=settings.SEARCH_PRICE_KGS,
        currency=settings.SEARCH_CURRENCY,
        status=PaymentStatus.PAID,
        demo_token="demo-seeded-payment-token",
        paid_at=order.paid_at,
        created_at=order.created_at,
    )
    db.add(payment)

    # Seller A answered all YES, selected
    offer_a = SellerOffer(order_id=order.id, seller_id=sellers[0].id, created_at=now - timedelta(days=9, hours=23))
    db.add(offer_a)
    db.flush()
    prices = [4500, 4500, 7200, 2100]
    for item, price in zip(items, prices):
        db.add(
            SellerOfferItem(
                offer_id=offer_a.id,
                order_item_id=item.id,
                availability=Availability.YES,
                price=price,
                comment="Оригинал, в наличии на складе",
                detail="KYB Excel-G, новые, оригинал. Самовывоз в день обращения.",
                condition="NEW",
                is_original=True,
            )
        )
    # Seller B partial: only brakes
    offer_b = SellerOffer(order_id=order.id, seller_id=sellers[1].id)
    db.add(offer_b)
    db.flush()
    db.add(
        SellerOfferItem(
            offer_id=offer_b.id,
            order_item_id=items[2].id,
            availability=Availability.YES,
            price=6800,
            comment="Диски Brembo, оригинал",
            detail="Оригинал Brembo, состояние новое.",
            condition="NEW",
            is_original=True,
        )
    )
    db.add(
        SellerOfferItem(
            offer_id=offer_b.id,
            order_item_id=items[3].id,
            availability=Availability.YES,
            price=1900,
        )
    )
    # Seller C: all NO
    offer_c = SellerOffer(order_id=order.id, seller_id=sellers[2].id)
    db.add(offer_c)
    db.flush()
    for item in items:
        db.add(
            SellerOfferItem(
                offer_id=offer_c.id,
                order_item_id=item.id,
                availability=Availability.NO,
                comment="Нет на складе",
            )
        )

    for seller, delay in zip(sellers, [0, 10, 30]):
        db.add(
            OrderSellerAssignment(
                order_id=order.id,
                seller_id=seller.id,
                quality_score=seller.quality_score,
                delay_seconds=delay,
                status=AssignmentStatus.DELIVERED,
                delivered_at=order.paid_at,
            )
        )

    chat = Chat(
        order_id=order.id,
        client_id=client.id,
        seller_user_id=sellers[0].user_id,
        seller_id=sellers[0].id,
        offer_id=offer_a.id,
        last_message_at=now - timedelta(days=8),
    )
    db.add(chat)
    db.flush()
    db.add(ChatParticipant(chat_id=chat.id, user_id=client.id, last_read_at=now))
    db.add(ChatParticipant(chat_id=chat.id, user_id=sellers[0].user_id, last_read_at=now))
    db.add(Message(chat_id=chat.id, sender_id=client.id, text="Здравствуйте! Амортизаторы оригинал или аналог?"))
    db.add(
        Message(
            chat_id=chat.id,
            sender_id=sellers[0].user_id,
            text="Оригинал KYB, можем отгрузить сегодня. Самовывоз Бишкек.",
        )
    )
    order.selected_offer_id = offer_a.id
    db.add(
        Rating(
            order_id=order.id,
            client_id=client.id,
            seller_id=sellers[0].id,
            score=5,
            comment="Быстро ответили, деталь как описали",
        )
    )
    return order


def seed_extra_ratings(db: Session, client: User, sellers: list[SellerProfile]):
    """Rating averages for demo sellers live on SellerProfile (denormalized).

    Unique (order_id, seller_id) prevents fabricating many rating rows for one order.
    """
    _ = (db, client, sellers)


def seed_reports(db: Session, client2: User, client3: User, seller3: SellerProfile, order: Order | None):
    if not order:
        return
    if db.query(Report).first():
        return
    now = datetime.now(timezone.utc)
    db.add(
        Report(
            reporter_id=client2.id,
            seller_id=seller3.id,
            order_id=order.id,
            reason="FALSE_AVAILABILITY",
            comment="Ответили «есть», на точке детали не оказалось",
            status="CONFIRMED",
            created_at=now - timedelta(days=3),
            reviewed_at=now - timedelta(days=2),
        )
    )
    db.add(
        Report(
            reporter_id=client3.id,
            seller_id=seller3.id,
            order_id=order.id,
            reason="WRONG_PART",
            comment="Привезли не ту стойку",
            status="PENDING",
            created_at=now - timedelta(hours=6),
        )
    )
    seller3.strike_count = 1


def seed_settings(db: Session):
    row = db.query(PlatformSettings).filter(PlatformSettings.id == 1).first()
    if not row:
        db.add(PlatformSettings(id=1, rotation_after_orders=20, rotation_lookback_hours=24, rotation_max_extra_delay=40))


def run_seed() -> None:
    ensure_schema()
    db = SessionLocal()
    try:
        cities = seed_geo(db)
        categories = seed_categories(db)
        seed_vehicles(db)
        seed_parts(db, categories)

        admin = ensure_user(db, "admin@autoparty.demo", "Администратор", UserRole.ADMIN, "+996500000001")
        client1 = ensure_user(db, "client1@autoparty.demo", "Айбек Клиент", UserRole.CLIENT, "+996555111001")
        client2 = ensure_user(db, "client2@autoparty.demo", "Алина Клиент", UserRole.CLIENT, "+996555111002")
        client3 = ensure_user(db, "client3@autoparty.demo", "Нурлан Клиент", UserRole.CLIENT, "+996555111003")

        s1u = ensure_user(db, "seller1@autoparty.demo", "АвтоСклад Бишкек", UserRole.SELLER, "+996555222001")
        s2u = ensure_user(db, "seller2@autoparty.demo", "Osh Parts", UserRole.SELLER, "+996555222002")
        s3u = ensure_user(db, "seller3@autoparty.demo", "IssykKul Auto", UserRole.SELLER, "+996555222003")
        s4u = ensure_user(db, "seller4@autoparty.demo", "Юг Авто", UserRole.SELLER, "+996555222004")

        seller1 = ensure_seller(
            db,
            s1u,
            "АвтоСклад Бишкек",
            {"rating": 4.9, "rating_count": 20, "assigned": 40, "responded": 38, "processed": 38, "avg_sec": 120},
            ["engine", "brakes", "suspension"],
            ["Бишкек"],
            categories,
            cities,
        )
        seller2 = ensure_seller(
            db,
            s2u,
            "Osh Parts",
            {"rating": 4.2, "rating_count": 10, "assigned": 20, "responded": 14, "processed": 14, "avg_sec": 600},
            ["consumables", "electrics", "cooling", "brakes", "suspension"],
            ["Бишкек", "Ош"],
            categories,
            cities,
        )
        seller3 = ensure_seller(
            db,
            s3u,
            "IssykKul Auto",
            {"rating": 2.8, "rating_count": 5, "assigned": 16, "responded": 5, "processed": 5, "avg_sec": 2800},
            ["body", "optics", "tires", "brakes"],
            ["Каракол", "Бишкек"],
            categories,
            cities,
        )
        seller4 = ensure_seller(
            db,
            s4u,
            "Юг Авто",
            {"rating": 3.6, "rating_count": 8, "assigned": 12, "responded": 8, "processed": 8, "avg_sec": 900},
            ["transmission", "steering", "interior"],
            ["Ош", "Джалал-Абад"],
            categories,
            cities,
        )

        toyota = db.query(VehicleBrand).filter(VehicleBrand.name == "Toyota").first()
        camry = (
            db.query(VehicleModel).filter(VehicleModel.brand_id == toyota.id, VehicleModel.name == "Camry").first()
            if toyota
            else None
        )
        demo_order = seed_demo_order(db, client1, [seller1, seller2, seller3], categories, cities, toyota, camry)
        seed_extra_ratings(db, client1, [seller1, seller2, seller3])
        seed_reports(db, client2, client3, seller3, demo_order)
        seed_settings(db)
        honda = db.query(VehicleBrand).filter(VehicleBrand.name == "Honda").first()
        crv = (
            db.query(VehicleModel).filter(VehicleModel.brand_id == honda.id, VehicleModel.name == "CR-V").first()
            if honda
            else None
        )
        if toyota and camry and not db.query(UserVehicle).filter(UserVehicle.user_id == client1.id).first():
            db.add(UserVehicle(user_id=client1.id, brand_id=toyota.id, model_id=camry.id, year=2020, nickname="Camry", is_default=True))
            if honda and crv:
                db.add(UserVehicle(user_id=client1.id, brand_id=honda.id, model_id=crv.id, year=2018, nickname="CR-V"))
        for seller in (seller1, seller2, seller3, seller4):
            refresh_reputation(db, seller)
        db.commit()
        print("Seed completed: demo users, KY geography, vehicles, sellers, demo order.")
        _ = (admin, client2, client3)
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    run_seed()
