
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import (
    Booking,
    Coupon,
    Event,
    Notification,
    Payment,
    Ticket,
    User,
)
from app.schemas import PaymentCreate, PaymentResponse

router = APIRouter(
    prefix="/api/v1/payments",
    tags=["Payments"],
)


def calculate_coupon_discount(booking, coupon):
    """Calculate the discount on the server, never from frontend totals."""
    now = datetime.utcnow()

    if not coupon.is_active:
        raise HTTPException(status_code=400, detail="Coupon is inactive.")

    if coupon.expiry_date and coupon.expiry_date < now:
        raise HTTPException(status_code=400, detail="Coupon has expired.")

    if (
        coupon.usage_limit is not None
        and coupon.used_count >= coupon.usage_limit
    ):
        raise HTTPException(
            status_code=400,
            detail="Coupon usage limit has been reached.",
        )

    original_amount = float(booking.total_price)

    if original_amount < float(coupon.minimum_amount or 0):
        raise HTTPException(
            status_code=400,
            detail="Booking does not meet the coupon minimum amount.",
        )

    if coupon.discount_type == "PERCENTAGE":
        if not 0 < float(coupon.discount_value) <= 100:
            raise HTTPException(
                status_code=400,
                detail="Invalid percentage discount.",
            )
        discount = original_amount * float(coupon.discount_value) / 100

    elif coupon.discount_type == "FIXED":
        if float(coupon.discount_value) <= 0:
            raise HTTPException(
                status_code=400,
                detail="Invalid fixed discount.",
            )
        discount = float(coupon.discount_value)

    else:
        raise HTTPException(
            status_code=400,
            detail="Unsupported coupon discount type.",
        )

    discount = min(discount, original_amount)
    final_amount = max(0.0, original_amount - discount)

    return round(discount, 2), round(final_amount, 2)


# =========================================================
# CREATE PAYMENT
# =========================================================

@router.post("/", response_model=PaymentResponse)
def create_payment(
    data: PaymentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    booking = (
        db.query(Booking)
        .filter(
            Booking.id == data.booking_id,
            Booking.user_id == current_user.id,
        )
        .with_for_update()
        .first()
    )

    if booking is None:
        raise HTTPException(status_code=404, detail="Booking not found.")

    if booking.booking_status == "CANCELLED":
        raise HTTPException(
            status_code=400,
            detail="Cannot pay for a cancelled booking.",
        )

    if booking.booking_status == "CONFIRMED":
        raise HTTPException(
            status_code=409,
            detail="This booking is already confirmed.",
        )

    existing_success = (
        db.query(Payment)
        .filter(
            Payment.booking_id == booking.id,
            Payment.payment_status == "SUCCESS",
        )
        .first()
    )

    if existing_success:
        raise HTTPException(
            status_code=409,
            detail="This booking has already been paid.",
        )

    # Reuse pending payment only when its coupon selection matches.
    coupon_code = getattr(data, "coupon_code", None)
    coupon = None
    discount_amount = 0.0
    final_amount = round(float(booking.total_price), 2)

    if coupon_code:
        normalized_code = coupon_code.strip().upper()
        coupon = (
            db.query(Coupon)
            .filter(Coupon.code == normalized_code)
            .with_for_update()
            .first()
        )

        if coupon is None:
            raise HTTPException(
                status_code=400,
                detail="Coupon code was not found.",
            )

        discount_amount, final_amount = calculate_coupon_discount(
            booking, coupon
        )

    existing_pending = (
        db.query(Payment)
        .filter(
            Payment.booking_id == booking.id,
            Payment.payment_status == "PENDING",
        )
        .first()
    )

    if existing_pending:
        same_coupon = (
            (existing_pending.coupon_code or None)
            == (coupon.code if coupon else None)
        )

        if same_coupon:
            return existing_pending

        raise HTTPException(
            status_code=409,
            detail=(
                "A pending payment already exists for this booking. "
                "Resolve that payment before changing the coupon."
            ),
        )

    try:
        payment = Payment(
            booking_id=booking.id,
            payment_method=data.payment_method,
            payment_status="PENDING",
            transaction_id=f"SIM-{uuid.uuid4().hex.upper()}",
            amount=final_amount,
            coupon_code=coupon.code if coupon else None,
            discount_amount=discount_amount,
        )

        db.add(payment)
        db.commit()
        db.refresh(payment)
        return payment

    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Unable to create payment record.",
        )


# =========================================================
# SIMULATE PAYMENT RESULT — DEMO ONLY
# =========================================================

@router.post("/{payment_id}/simulate")
def simulate_payment(
    payment_id: int,
    success: bool = Query(
        ...,
        description="Set true for simulated success or false for failure.",
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    payment = (
        db.query(Payment)
        .join(Booking, Payment.booking_id == Booking.id)
        .filter(
            Payment.id == payment_id,
            Booking.user_id == current_user.id,
        )
        .with_for_update()
        .first()
    )

    if payment is None:
        raise HTTPException(status_code=404, detail="Payment not found.")

    booking = (
        db.query(Booking)
        .filter(Booking.id == payment.booking_id)
        .with_for_update()
        .first()
    )

    if booking is None:
        raise HTTPException(
            status_code=404,
            detail="Associated booking not found.",
        )

    if booking.booking_status == "CANCELLED":
        raise HTTPException(
            status_code=400,
            detail="Cannot process payment for a cancelled booking.",
        )

    if payment.payment_status != "PENDING":
        raise HTTPException(
            status_code=409,
            detail=f"Payment has already been processed: {payment.payment_status}.",
        )

    existing_success = (
        db.query(Payment)
        .filter(
            Payment.booking_id == booking.id,
            Payment.payment_status == "SUCCESS",
            Payment.id != payment.id,
        )
        .first()
    )

    if existing_success:
        raise HTTPException(
            status_code=409,
            detail="Another successful payment already exists.",
        )

    event = db.query(Event).filter(Event.id == booking.event_id).first()

    if event is None:
        raise HTTPException(
            status_code=404,
            detail="Associated event not found.",
        )

    try:
        if success:
            # Recheck coupon eligibility before marking payment successful.
            if payment.coupon_code:
                coupon = (
                    db.query(Coupon)
                    .filter(Coupon.code == payment.coupon_code)
                    .with_for_update()
                    .first()
                )

                if coupon is None:
                    raise HTTPException(
                        status_code=400,
                        detail="The payment's coupon no longer exists.",
                    )

                # Revalidate expiry, activation, and usage limits.
                # Discount amount was fixed when the pending payment was made.
                if not coupon.is_active:
                    raise HTTPException(
                        status_code=400,
                        detail="Coupon is now inactive.",
                    )

                if coupon.expiry_date and coupon.expiry_date < datetime.utcnow():
                    raise HTTPException(
                        status_code=400,
                        detail="Coupon has expired.",
                    )

                if (
                    coupon.usage_limit is not None
                    and coupon.used_count >= coupon.usage_limit
                ):
                    raise HTTPException(
                        status_code=400,
                        detail="Coupon usage limit has been reached.",
                    )

                coupon.used_count += 1

            payment.payment_status = "SUCCESS"
            booking.booking_status = "CONFIRMED"

            existing_tickets = (
                db.query(Ticket)
                .filter(Ticket.booking_id == booking.id)
                .count()
            )

            if existing_tickets == 0:
                for _ in range(booking.ticket_quantity):
                    db.add(
                        Ticket(
                            booking_id=booking.id,
                            ticket_code=uuid.uuid4().hex.upper(),
                        )
                    )

            notification = Notification(
                user_id=current_user.id,
                title="Payment Successful",
                message=(
                    f"Payment for booking #{booking.id} succeeded. "
                    f"Your booking for {event.title} is confirmed."
                ),
                type="PAYMENT",
            )

            message = (
                "Payment successful. Booking confirmed and tickets generated."
            )

        else:
            payment.payment_status = "FAILED"

            notification = Notification(
                user_id=current_user.id,
                title="Payment Failed",
                message=(
                    f"Payment for booking #{booking.id} failed. "
                    "Please retry payment or cancel the booking."
                ),
                type="PAYMENT",
            )

            message = (
                "Payment failed. The booking remains pending. "
                "Retry payment or cancel the booking."
            )

        db.add(notification)
        db.commit()
        db.refresh(payment)

        return {
            "message": message,
            "payment_id": payment.id,
            "booking_id": booking.id,
            "payment_status": payment.payment_status,
            "booking_status": booking.booking_status,
            "amount": payment.amount,
            "discount_amount": payment.discount_amount,
            "coupon_code": payment.coupon_code,
        }

    except HTTPException:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Unable to process simulated payment.",
        )


# =========================================================
# GET CURRENT USER'S PAYMENTS
# =========================================================

@router.get("/my", response_model=list[PaymentResponse])
def get_my_payments(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return (
        db.query(Payment)
        .join(Booking, Payment.booking_id == Booking.id)
        .filter(Booking.user_id == current_user.id)
        .order_by(Payment.created_at.desc())
        .all()
    )


