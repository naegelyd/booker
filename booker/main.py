from datetime import date, datetime
from typing import Optional

from fastapi import FastAPI, HTTPException, Depends, Query
from sqlalchemy.orm import Session

from booker.schemas import BookingCreate, BookingRead, RoomCreate, RoomRead
from booker.models import Booking, Room
from booker.db import get_db

app = FastAPI(title="Booker", description="API to manage Rooms and Bookings")


@app.post("/rooms", response_model=RoomRead)
def create_room(room: RoomCreate, db: Session = Depends(get_db)):
    existing = db.query(Room).filter_by(name=room.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Room name already exists.")
    new_room = Room(name=room.name, location=room.location)
    db.add(new_room)
    db.commit()
    db.refresh(new_room)
    return new_room


@app.get("/rooms", response_model=list[RoomRead])
def list_rooms(db: Session = Depends(get_db)):
    return db.query(Room).all()


@app.get("/rooms/{id}", response_model=RoomRead)
def get_room(id: int, db: Session = Depends(get_db)):
    room = db.query(Room).get(id)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    return room


@app.delete("/rooms/{id}", status_code=204)
def delete_room(id: int, db: Session = Depends(get_db)):
    room = db.query(Room).get(id)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    db.delete(room)
    db.commit()


@app.post("/bookings", response_model=BookingRead)
def create_booking(booking: BookingCreate, db: Session = Depends(get_db)):
    # Check room exists
    room = db.query(Room).get(booking.room_id)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    # Check for booking conflicts:
    conflict = (
        db.query(Booking)
        .filter(
            Booking.room_id == booking.room_id,
            # Overlapping time ranges:
            Booking.start_datetime < booking.end_datetime,
            Booking.end_datetime > booking.start_datetime,
        )
        .first()
    )

    if conflict:
        raise HTTPException(
            status_code=400, detail="Booking time conflicts with existing booking"
        )

    new_booking = Booking(
        room_id=booking.room_id,
        user_name=booking.user_name,
        start_datetime=booking.start_datetime,
        end_datetime=booking.end_datetime,
    )
    db.add(new_booking)
    db.commit()
    db.refresh(new_booking)
    return new_booking


@app.get("/bookings", response_model=list[BookingRead])
def list_bookings(
    db: Session = Depends(get_db),
    room_id: Optional[int] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
):
    query = db.query(Booking)

    if room_id is not None:
        query = query.filter(Booking.room_id == room_id)

    if start_date is not None:
        # bookings ending after or on start_date
        query = query.filter(
            Booking.end_datetime >= datetime.combine(start_date, datetime.min.time())
        )

    if end_date is not None:
        # bookings starting before or on end_date
        query = query.filter(
            Booking.start_datetime <= datetime.combine(end_date, datetime.max.time())
        )

    return query.all()


@app.delete("/bookings/{id}", status_code=204)
def delete_booking(id: int, db: Session = Depends(get_db)):
    booking = db.query(Booking).get(id)
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    db.delete(booking)
    db.commit()
