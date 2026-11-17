
from datetime import date

from app import store
from app.models.reservation import Reservation


def make_book(client, title="Test Book"):
    response = client.post("/books", json={
        "title": title,
        "author": "Test Author",
        "isbn": "1234567890",
        "total_copies": 2
    })
    assert response.status_code == 201
    return response.get_json()["id"]


def make_member(client, name="Test Member"):
    response = client.post("/members", json={
        "name": name,
        "email": "test@example.com"
    })
    assert response.status_code == 201
    return response.get_json()["id"]


def make_reservation(client, book_id, member_id):
    return client.post("/reservations", json={
        "book_id": book_id,
        "member_id": member_id
    })


def test_list_reservations_empty(client):
    response = client.get("/reservations")

    assert response.status_code == 200
    assert response.get_json() == []


def test_create_reservation_success(client):
    book_id = make_book(client)
    member_id = make_member(client)

    response = make_reservation(
        client, book_id, member_id
    )

    assert response.status_code == 201

    data = response.get_json()

    assert data["book_id"] == book_id
    assert data["member_id"] == member_id
    assert data["fulfilled"] is False
    assert data["reservation_date"] == date.today().isoformat()
    assert data["id"] in store.reservations


def test_reservation_missing_book(client):
    member_id = make_member(client)

    response = make_reservation(
        client, 999, member_id
    )

    assert response.status_code == 404
    assert response.get_json()["error"] == "Book not found"
    assert len(store.reservations) == 0


def test_reservation_missing_member(client):
    book_id = make_book(client)

    response = make_reservation(
        client, book_id, 999
    )

    assert response.status_code == 404
    assert response.get_json()["error"] == "Member not found"
    assert len(store.reservations) == 0


def test_reservation_filters(client):
    book1 = make_book(client, "Book One")
    book2 = make_book(client, "Book Two")

    member1 = make_member(client, "Alice")
    member2 = make_member(client, "Bob")

    for book_id, member_id in [
        (book1, member1),
        (book1, member2),
        (book2, member1)
    ]:
        assert make_reservation(
            client, book_id, member_id
        ).status_code == 201

    response = client.get("/reservations")
    assert len(response.get_json()) == 3

    response = client.get(
        f"/reservations?book_id={book1}"
    )
    assert response.status_code == 200
    assert len(response.get_json()) == 2
    assert all(
        r["book_id"] == book1
        for r in response.get_json()
    )

    response = client.get(
        f"/reservations?member_id={member1}"
    )
    assert len(response.get_json()) == 2
    assert all(
        r["member_id"] == member1
        for r in response.get_json()
    )

    response = client.get(
        f"/reservations?book_id={book2}&member_id={member2}"
    )
    assert response.get_json() == []


def test_reservation_model_default_date():
    reservation = Reservation(
        id=1,
        book_id=2,
        member_id=3
    )

    result = reservation.to_dict()

    assert result["id"] == 1
    assert result["book_id"] == 2
    assert result["member_id"] == 3
    assert result["fulfilled"] is False
    assert result["reservation_date"] == date.today().isoformat()
