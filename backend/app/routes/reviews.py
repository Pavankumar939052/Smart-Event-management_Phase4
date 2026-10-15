
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import Booking, Event, Review
from app.schemas import (
    EventReviewSummary,
    ReviewCreate,
    ReviewResponse,
    ReviewUpdate,
)

router = APIRouter(
    prefix="/api/v1/reviews",
    tags=["Event Reviews"],
)


# ---------------------------------------------------------
# Helper: Check whether a user is eligible to review
# ---------------------------------------------------------

def check_review_eligibility(
    db: Session,
    event_id: int,
    user_id: int,
) -> None:
    event = (
        db.query(Event)
        .filter(Event.id == event_id)
        .first()
    )

    if event is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found.",
        )

    # The event must have ended.
    event_end = getattr(event, "event_end_date", None)

    if event_end is None:
        event_end = getattr(event, "event_date", None)

    if event_end is None or event_end > datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can review an event only after it has ended.",
        )

    # A confirmed booking is required.
    booking = (
        db.query(Booking)
        .filter(
            Booking.user_id == user_id,
            Booking.event_id == event_id,
            func.upper(Booking.booking_status) == "CONFIRMED",
        )
        .first()
    )

    if booking is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only users with a confirmed booking can review this event.",
        )


# ---------------------------------------------------------
# GET: Fetch reviews and average rating for an event
# ---------------------------------------------------------

@router.get(
    "/events/{event_id}",
    response_model=EventReviewSummary,
)
def get_event_reviews(
    event_id: int,
    db: Session = Depends(get_db),
):
    event = (
        db.query(Event)
        .filter(Event.id == event_id)
        .first()
    )

    if event is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found.",
        )

    reviews = (
        db.query(Review)
        .filter(Review.event_id == event_id)
        .order_by(Review.created_at.desc())
        .all()
    )

    average_rating = (
        db.query(func.avg(Review.rating))
        .filter(Review.event_id == event_id)
        .scalar()
    )

    return {
        "event_id": event_id,
        "average_rating": (
            round(float(average_rating), 2)
            if average_rating is not None
            else 0.0
        ),
        "total_reviews": len(reviews),
        "reviews": reviews,
    }


# ---------------------------------------------------------
# POST: Submit a review
# ---------------------------------------------------------

@router.post(
    "/events/{event_id}",
    response_model=ReviewResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_review(
    event_id: int,
    payload: ReviewCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    user_id = current_user.id

    check_review_eligibility(
        db=db,
        event_id=event_id,
        user_id=user_id,
    )

    existing_review = (
        db.query(Review)
        .filter(
            Review.user_id == user_id,
            Review.event_id == event_id,
        )
        .first()
    )

    if existing_review is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You have already reviewed this event. Edit your existing review.",
        )

    review_text = payload.review_text.strip()

    if not review_text:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Review text cannot be empty.",
        )

    review = Review(
        user_id=user_id,
        event_id=event_id,
        rating=payload.rating,
        review_text=review_text,
    )

    db.add(review)
    db.commit()
    db.refresh(review)

    return review


# ---------------------------------------------------------
# PUT: Edit your own review
# ---------------------------------------------------------

@router.put(
    "/{review_id}",
    response_model=ReviewResponse,
)
def update_review(
    review_id: int,
    payload: ReviewUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    review = (
        db.query(Review)
        .filter(Review.id == review_id)
        .first()
    )

    if review is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Review not found.",
        )

    if review.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can edit only your own review.",
        )

    review_text = payload.review_text.strip()

    if not review_text:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Review text cannot be empty.",
        )

    review.rating = payload.rating
    review.review_text = review_text

    db.commit()
    db.refresh(review)

    return review


# ---------------------------------------------------------
# DELETE: Delete your own review
# ---------------------------------------------------------

@router.delete(
    "/{review_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_review(
    review_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    review = (
        db.query(Review)
        .filter(Review.id == review_id)
        .first()
    )

    if review is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Review not found.",
        )

    if review.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can delete only your own review.",
        )

    db.delete(review)
    db.commit()

    return None
