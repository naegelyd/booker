import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

os.environ["DATABASE_URL"] = "sqlite:///./test.db"

from booker.main import app, get_db
from booker.models import Base


engine = create_engine(
    os.environ["DATABASE_URL"], connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(bind=engine)


def override_get_db():
    test_db = TestingSessionLocal()
    try:
        yield test_db
    finally:
        test_db.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


@pytest.fixture(scope="module", autouse=True)
def setup_database():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


def test_create_room():
    response = client.post("/rooms", json={"name": "Room 27", "location": "Floor 1"})
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Room 27"
    assert data["location"] == "Floor 1"
    assert "id" in data


def test_get_all_rooms():
    num_existing_rooms = len(client.get("/rooms").json())
    num_rooms = 10
    for i in range(num_rooms):
        response = client.post(
            "/rooms", json={"name": f"Room{i}", "location": f"Floor{i}"}
        )
        assert response.status_code == 200
    response = client.get("/rooms")
    assert isinstance(response.json(), list)
    assert len(response.json()) - num_existing_rooms == num_rooms


def test_get_single_room():
    all_rooms = client.get("/rooms").json()
    room_id = all_rooms[0]["id"]
    response = client.get(f"/rooms/{room_id}")
    assert response.status_code == 200
    assert response.json()["id"] == room_id


def test_get_nonexistent_room():
    response = client.get("/rooms/123456789")
    assert response.status_code == 404


def test_delete_room():
    response = client.post("/rooms", json={"name": "Room 1", "location": "Floor 4"})
    room_id = response.json()["id"]
    del_response = client.delete(f"/rooms/{room_id}")
    assert del_response.status_code == 204
    get_response = client.get(f"/rooms/{room_id}")
    assert get_response.status_code == 404


def test_create_booking_for_nonexistent_room():
    """
    Booking a room that is non-existent room should 404.
    """
    payload = {
        "room_id": 12345678,
        "user_name": "Guest1",
        "start_datetime": "2025-06-08T10:00:00",
        "end_datetime": "2025-06-08T11:00:00",
    }
    response = client.post("/bookings", json=payload)
    assert response.status_code == 404


def test_create_conflicting_booking():
    """
    Booking a room that is unavailable during the requested start/end range should 400.
    """
    room = client.post("/rooms", json={"name": "Room 4", "location": "Floor 1"}).json()
    room_id = room["id"]

    booking1 = {
        "room_id": room_id,
        "user_name": "Guest1",
        "start_datetime": "2025-06-08T14:00:00",
        "end_datetime": "2025-06-11T10:00:00",
    }
    response1 = client.post("/bookings", json=booking1)
    assert response1.status_code == 200

    # End date overlaps with existing booking.
    booking2 = {
        "room_id": room_id,
        "user_name": "Guest2",
        "start_datetime": "2025-06-07T14:00:00",
        "end_datetime": "2025-06-09T10:30:00",
    }
    response = client.post("/bookings", json=booking2)
    assert response.status_code == 400

    # Start date overlaps with existing booking.
    booking3 = {
        "room_id": room_id,
        "user_name": "Guest2",
        "start_datetime": "2025-06-10T14:00:00",
        "end_datetime": "2025-06-12T11:30:00",
    }
    response = client.post("/bookings", json=booking3)
    assert response.status_code == 400

    # New booking fully contained within existing booking.
    booking4 = {
        "room_id": room_id,
        "user_name": "Guest2",
        "start_datetime": "2025-06-09T14:00:00",
        "end_datetime": "2025-06-10T11:30:00",
    }
    response = client.post("/bookings", json=booking4)
    assert response.status_code == 400


def test_create_non_conflicting_booking():
    """
    Booking an existing room with no conflicts should 200 and return the booking.
    """
    rooms = client.get("/rooms").json()
    room_id = rooms[0]["id"]

    booking = {
        "room_id": room_id,
        "user_name": "Guest",
        "start_datetime": "2025-06-08T11:00:00",
        "end_datetime": "2025-06-08T12:00:00",
    }
    response = client.post("/bookings", json=booking)
    assert response.status_code == 200
    assert response.json()["user_name"] == "Guest"


def test_list_bookings():
    room_response = client.post("/rooms", json={"name": "Guest Room 1"})
    assert room_response.status_code == 200
    room1 = room_response.json()
    room_response = client.post("/rooms", json={"name": "Guest Room 2"})
    assert room_response.status_code == 200
    room2 = room_response.json()

    booking1 = {
        "room_id": room1["id"],
        "user_name": "Guest1",
        "start_datetime": "2025-07-01T22:00:00",
        "end_datetime": "2025-07-08T12:00:00",
    }
    booking2 = {
        "room_id": room2["id"],
        "user_name": "Guest2",
        "start_datetime": "2025-07-10T11:00:00",
        "end_datetime": "2025-07-18T12:00:00",
    }
    assert client.post("/bookings", json=booking1).status_code == 200
    assert client.post("/bookings", json=booking2).status_code == 200

    response = client.get(f"/bookings?room_id={room1['id']}")
    assert response.status_code == 200
    [booking] = response.json()
    booking["room_id"] == room1["id"]

    # Filtering by just one of the date options should be supported
    response = client.get("/bookings?start_date=2025-07-10")
    assert response.status_code == 200
    [booking] = response.json()
    assert booking["user_name"] == booking2["user_name"]

    # Date ranges should also be supported
    response = client.get("/bookings?start_date=2025-06-30&end_date=2025-07-07")
    assert response.status_code == 200
    [booking] = response.json()
    assert booking["user_name"] == booking1["user_name"]

    # Make sure empty result is still properly returned.
    empty_res = client.get("/bookings?start_date=2000-01-01&end_date=2000-01-02")
    assert empty_res.status_code == 200
    assert empty_res.json() == []
