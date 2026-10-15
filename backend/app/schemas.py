
from datetime import datetime
from typing import Literal, Optional

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    model_validator,
)


# =========================================================
# MODULE 7: AUTHENTICATION AND RBAC
# =========================================================

RoleType = Literal["USER", "ORGANIZER", "ADMIN"]

EventStatusType = Literal[
    "UPCOMING",
    "ONGOING",
    "COMPLETED",
    "CANCELLED",
]


class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=100)
    email: EmailStr
    password: str = Field(min_length=6, max_length=100)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: int
    username: str
    email: EmailStr
    role: RoleType = "USER"
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# =========================================================
# MODULES 8, 10, 16: EVENTS
# =========================================================

class EventCreate(BaseModel):
    title: str = Field(min_length=2, max_length=200)
    description: str
    category: str = Field(min_length=1, max_length=50)
    location: str = Field(min_length=1, max_length=255)
    event_date: datetime
    event_end_date: Optional[datetime] = None
    ticket_price: float = Field(ge=0)
    banner_image: Optional[str] = None
    total_tickets: int = Field(default=100, gt=0)

    @model_validator(mode="after")
    def validate_event_dates(self):
        if (
            self.event_end_date is not None
            and self.event_end_date <= self.event_date
        ):
            raise ValueError(
                "event_end_date must be after event_date."
            )
        return self


class EventUpdate(BaseModel):
    title: Optional[str] = Field(
        default=None, min_length=2, max_length=200
    )
    description: Optional[str] = None
    category: Optional[str] = Field(
        default=None, min_length=1, max_length=50
    )
    location: Optional[str] = Field(
        default=None, min_length=1, max_length=255
    )
    event_date: Optional[datetime] = None
    event_end_date: Optional[datetime] = None
    ticket_price: Optional[float] = Field(default=None, ge=0)
    banner_image: Optional[str] = None
    total_tickets: Optional[int] = Field(default=None, gt=0)

    @model_validator(mode="after")
    def validate_supplied_dates(self):
        if (
            self.event_date is not None
            and self.event_end_date is not None
            and self.event_end_date <= self.event_date
        ):
            raise ValueError(
                "event_end_date must be after event_date."
            )
        return self


class EventResponse(BaseModel):
    id: int
    title: str
    description: str
    category: str
    location: str
    event_date: datetime
    event_end_date: Optional[datetime] = None
    ticket_price: float
    banner_image: Optional[str] = None
    total_tickets: int
    available_tickets: int
    organizer_id: Optional[int] = None
    event_status: EventStatusType = "UPCOMING"
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# =========================================================
# MODULES 8, 9, 11, 12, 13: BOOKINGS
# =========================================================

class BookingCreate(BaseModel):
    event_id: int = Field(gt=0)
    ticket_quantity: int = Field(gt=0, le=10)


class BookingResponse(BaseModel):
    id: int
    user_id: int
    event_id: int
    ticket_quantity: int
    total_price: float
    booking_status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# =========================================================
# TICKETS
# =========================================================

class TicketResponse(BaseModel):
    id: int
    booking_id: int
    ticket_code: str
    qr_code_url: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# =========================================================
# MODULE 15: ADVANCED NOTIFICATIONS
# =========================================================

NotificationType = Literal[
    "EVENT",
    "BOOKING",
    "PAYMENT",
    "SYSTEM",
]


class NotificationResponse(BaseModel):
    id: int
    user_id: int
    title: str
    message: str
    type: NotificationType
    is_read: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UnreadNotificationCount(BaseModel):
    unread_count: int


class MarkAllNotificationsReadResponse(BaseModel):
    message: str
    updated_count: int


# =========================================================
# MODULE 12: PAYMENTS + MODULE 13: COUPON DISCOUNTS
# =========================================================

PaymentStatusType = Literal["PENDING", "SUCCESS", "FAILED"]


class PaymentCreate(BaseModel):
    booking_id: int = Field(gt=0)
    payment_method: Literal["SIMULATED"] = "SIMULATED"
    coupon_code: Optional[str] = Field(
        default=None, min_length=3, max_length=50
    )

    @model_validator(mode="after")
    def normalize_coupon_code(self):
        if self.coupon_code is not None:
            self.coupon_code = self.coupon_code.strip().upper()

            if not self.coupon_code:
                raise ValueError("Coupon code cannot be empty.")

        return self


class PaymentResponse(BaseModel):
    id: int
    booking_id: int
    payment_method: str
    payment_status: PaymentStatusType
    transaction_id: Optional[str] = None
    amount: float
    coupon_code: Optional[str] = None
    discount_amount: float = 0.0
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# =========================================================
# MODULE 9: ORGANIZER ANALYTICS
# =========================================================

class OrganizerEventAnalytics(BaseModel):
    event_id: int
    event_title: str
    total_tickets: int
    tickets_sold: int
    remaining_tickets: int
    total_revenue: float
    booking_count: int


# =========================================================
# MODULE 11: ADMIN ANALYTICS
# =========================================================

class AdminAnalyticsResponse(BaseModel):
    total_users: int
    total_events: int
    total_tickets_sold: int
    total_bookings: int
    platform_revenue: float


class DailyTicketSales(BaseModel):
    date: str
    tickets_sold: int


class MonthlyBookingTrend(BaseModel):
    month: str
    booking_count: int
    total_revenue: float


class PopularEventResponse(BaseModel):
    event_id: int
    event_title: str
    tickets_sold: int
    booking_count: int
    total_revenue: float


# =========================================================
# MODULE 13: COUPON AND DISCOUNT SYSTEM
# =========================================================

CouponDiscountType = Literal["PERCENTAGE", "FIXED"]


class CouponCreate(BaseModel):
    code: str = Field(min_length=3, max_length=50)
    discount_type: CouponDiscountType
    discount_value: float = Field(gt=0)
    minimum_amount: float = Field(default=0.0, ge=0)
    expiry_date: Optional[datetime] = None
    usage_limit: Optional[int] = Field(default=None, gt=0)
    is_active: bool = True

    @model_validator(mode="after")
    def validate_discount_value(self):
        self.code = self.code.strip().upper()

        if not self.code:
            raise ValueError("Coupon code cannot be empty.")

        if (
            self.discount_type == "PERCENTAGE"
            and self.discount_value > 100
        ):
            raise ValueError(
                "Percentage discount cannot exceed 100."
            )

        return self


class CouponResponse(BaseModel):
    id: int
    code: str
    discount_type: CouponDiscountType
    discount_value: float
    minimum_amount: float
    expiry_date: Optional[datetime] = None
    usage_limit: Optional[int] = None
    used_count: int
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CouponValidateRequest(BaseModel):
    code: str = Field(min_length=3, max_length=50)
    booking_id: int = Field(gt=0)

    @model_validator(mode="after")
    def normalize_coupon_code(self):
        self.code = self.code.strip().upper()

        if not self.code:
            raise ValueError("Coupon code cannot be empty.")

        return self


class CouponValidateResponse(BaseModel):
    code: str
    discount_type: CouponDiscountType
    original_amount: float
    discount_amount: float
    final_amount: float
    message: str


# =========================================================
# MODULE 14: EVENT FEEDBACK AND RATINGS
# =========================================================

class ReviewCreate(BaseModel):
    rating: int = Field(ge=1, le=5)
    review_text: str = Field(min_length=1, max_length=2000)

    @model_validator(mode="after")
    def validate_review_text(self):
        self.review_text = self.review_text.strip()

        if not self.review_text:
            raise ValueError("Review text cannot be empty.")

        return self


class ReviewUpdate(BaseModel):
    rating: int = Field(ge=1, le=5)
    review_text: str = Field(min_length=1, max_length=2000)

    @model_validator(mode="after")
    def validate_review_text(self):
        self.review_text = self.review_text.strip()

        if not self.review_text:
            raise ValueError("Review text cannot be empty.")

        return self


class ReviewResponse(BaseModel):
    id: int
    user_id: int
    event_id: int
    rating: int
    review_text: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class EventReviewSummary(BaseModel):
    event_id: int
    average_rating: float
    total_reviews: int
    reviews: list[ReviewResponse]








# PHASE 4 schemas
class ProfileUpdate(BaseModel):
    username: Optional[str] = Field(default=None, min_length=3, max_length=100)
    email: Optional[EmailStr] = None

class WishlistResponse(BaseModel):
    id: int
    user_id: int
    event_id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class EventUpdateCreate(BaseModel):
    message: str = Field(min_length=2, max_length=2000)

class EventUpdateResponse(BaseModel):
    id: int
    event_id: int
    user_id: int
    message: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=1000)
