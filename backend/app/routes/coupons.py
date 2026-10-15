
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import Booking, Coupon
from app.schemas import (
    CouponCreate,
    CouponResponse,
    CouponValidateRequest,
    CouponValidateResponse,
)


router = APIRouter(
    prefix="/api/v1/coupons",
    tags=["Coupons - Module 13"],
)


# =========================================================
# HELPERS
# =========================================================

def normalize_code(code: str) -> str:
    return code.strip().upper()


def calculate_discount(
    amount: float,
    discount_type: str,
    discount_value: float,
) -> float:
    original = Decimal(str(amount))
    value = Decimal(str(discount_value))

    if discount_type == "PERCENTAGE":
        discount = original * value / Decimal("100")
    elif discount_type == "FIXED":
        discount = value
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported coupon discount type.",
        )

    # A discount must never make the total negative.
    discount = min(discount, original)

    return float(
        discount.quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP,
        )
    )


def validate_coupon_eligibility(
    coupon: Coupon,
    amount: float,
) -> None:
    if not coupon.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This coupon is inactive.",
        )

    if (
        coupon.expiry_date is not None
        and coupon.expiry_date <= datetime.utcnow()
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This coupon has expired.",
        )

    if amount < coupon.minimum_amount:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Minimum order amount is "
                f"{coupon.minimum_amount:.2f}."
            ),
        )

    if (
        coupon.usage_limit is not None
        and coupon.used_count >= coupon.usage_limit
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This coupon has reached its usage limit.",
        )

    if coupon.discount_type == "PERCENTAGE":
        if not 0 < coupon.discount_value <= 100:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Coupon percentage must be between 0 and 100.",
            )

    elif coupon.discount_type == "FIXED":
        if coupon.discount_value <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Fixed discount must be greater than zero.",
            )

    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid coupon discount type.",
        )


# =========================================================
# CREATE COUPON — ADMIN ONLY
# =========================================================

@router.post(
    "/",
    response_model=CouponResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_coupon(
    coupon_data: CouponCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if str(current_user.role).upper() != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can create coupons.",
        )

    code = normalize_code(coupon_data.code)

    if not code:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Coupon code cannot be empty.",
        )

    existing_coupon = (
        db.query(Coupon)
        .filter(Coupon.code == code)
        .first()
    )

    if existing_coupon:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A coupon with this code already exists.",
        )

    if (
        coupon_data.discount_type == "PERCENTAGE"
        and coupon_data.discount_value > 100
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Percentage discount cannot exceed 100.",
        )

    if (
        coupon_data.expiry_date is not None
        and coupon_data.expiry_date <= datetime.utcnow()
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Expiry date must be in the future.",
        )

    coupon = Coupon(
        code=code,
        discount_type=coupon_data.discount_type,
        discount_value=coupon_data.discount_value,
        minimum_amount=coupon_data.minimum_amount,
        expiry_date=coupon_data.expiry_date,
        usage_limit=coupon_data.usage_limit,
        used_count=0,
        is_active=coupon_data.is_active,
    )

    db.add(coupon)

    try:
        db.commit()
        db.refresh(coupon)
    except Exception:
        db.rollback()
        raise

    return coupon


# =========================================================
# VALIDATE COUPON — AUTHENTICATED USER
# =========================================================

@router.post(
    "/validate",
    response_model=CouponValidateResponse,
)
def validate_coupon(
    request: CouponValidateRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    code = normalize_code(request.code)

    coupon = (
        db.query(Coupon)
        .filter(Coupon.code == code)
        .first()
    )

    if coupon is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Coupon code not found.",
        )

    booking = (
        db.query(Booking)
        .filter(
            Booking.id == request.booking_id,
            Booking.user_id == current_user.id,
        )
        .first()
    )

    if booking is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Booking not found for this user.",
        )

    if str(booking.booking_status).upper() == "CANCELLED":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot apply a coupon to a cancelled booking.",
        )

    original_amount = float(booking.total_price)

    validate_coupon_eligibility(
        coupon=coupon,
        amount=original_amount,
    )

    discount_amount = calculate_discount(
        amount=original_amount,
        discount_type=coupon.discount_type,
        discount_value=coupon.discount_value,
    )

    final_amount = round(
        original_amount - discount_amount,
        2,
    )

    return CouponValidateResponse(
        code=coupon.code,
        discount_type=coupon.discount_type,
        original_amount=round(original_amount, 2),
        discount_amount=discount_amount,
        final_amount=final_amount,
        message="Coupon applied successfully.",
    )


# =========================================================
# LIST COUPONS — ADMIN ONLY
# =========================================================

@router.get(
    "/",
    response_model=list[CouponResponse],
)
def list_coupons(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if str(current_user.role).upper() != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can view all coupons.",
        )

    return (
        db.query(Coupon)
        .order_by(Coupon.id.desc())
        .all()
    )
