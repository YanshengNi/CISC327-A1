
from datetime import date, timedelta
from unittest.mock import patch

from app import store


def create_overdue_loan(client):
    member = client.post("/members", json={
        "name": "Test Member",
        "email": "member@example.com"
    }).get_json()

    book = client.post("/books", json={
        "title": "Clean Code",
        "author": "Robert C. Martin",
        "isbn": "123456789",
        "total_copies": 2
    }).get_json()

    loan = client.post("/loans", json={
        "member_id": member["id"],
        "book_id": book["id"]
    }).get_json()

    stored_loan = store.loans[loan["id"]]
    stored_loan.due_date = date.today() - timedelta(days=2)

    return stored_loan


# Member A: Stub success scenario
def test_overdue_notification_success_stub(client, monkeypatch):
    loan = create_overdue_loan(client)

    monkeypatch.setattr(
        "app.routes.loans.send_notification",
        lambda recipient, subject, message: True
    )

    response = client.post(f"/loans/{loan.id}/remind")

    assert response.status_code == 200
    assert response.get_json()["notified"] is True
    assert store.loans[loan.id].return_date is None
    assert store.loans[loan.id].due_date == loan.due_date


# Member A: Mock interaction scenario
def test_overdue_notification_correct_mock(client):
    loan = create_overdue_loan(client)

    with patch(
        "app.routes.loans.send_notification",
        return_value=True
    ) as mock_send:
        response = client.post(f"/loans/{loan.id}/remind")

    assert response.status_code == 200
    assert response.get_json()["notified"] is True
    assert store.loans[loan.id].return_date is None

    mock_send.assert_called_once_with(
        "member@example.com",
        "Overdue Library Book",
        (
            f"Please return 'Clean Code'. "
            f"It was due on {loan.due_date.isoformat()}."
        )
    )




# Member A: Coverage-directed tests for views.py

def test_ui_create_and_delete_book(client):
    response = client.post("/ui/books", data={
        "title": "Python Basics",
        "author": "Test Author",
        "isbn": "1234567890",
        "total_copies": "2"
    })

    assert response.status_code == 302
    assert len(store.books) == 1

    book = next(iter(store.books.values()))
    assert book.title == "Python Basics"
    assert book.available_copies == 2

    response = client.post(f"/ui/books/{book.id}/delete")

    assert response.status_code == 302
    assert len(store.books) == 0


def test_ui_create_and_delete_member(client):
    response = client.post("/ui/members", data={
        "name": "Alice",
        "email": "alice@example.com"
    })

    assert response.status_code == 302
    assert len(store.members) == 1

    member = next(iter(store.members.values()))
    assert member.name == "Alice"
    assert member.email == "alice@example.com"

    response = client.post(f"/ui/members/{member.id}/delete")

    assert response.status_code == 302
    assert len(store.members) == 0


def test_ui_checkout_and_return_book(client):
    book = client.post("/books", json={
        "title": "Software Testing",
        "author": "Test Author",
        "isbn": "9876543210",
        "total_copies": 2
    }).get_json()

    member = client.post("/members", json={
        "name": "Bob",
        "email": "bob@example.com"
    }).get_json()

    response = client.post("/ui/loans", data={
        "book_id": str(book["id"]),
        "member_id": str(member["id"])
    })

    assert response.status_code == 302
    assert len(store.loans) == 1
    assert store.books[book["id"]].available_copies == 1

    loan = next(iter(store.loans.values()))
    assert loan.member_id == member["id"]

    response = client.post(f"/ui/loans/{loan.id}/return")

    assert response.status_code == 302
    assert loan.return_date == date.today()
    assert store.books[book["id"]].available_copies == 2

    # Returning the same loan twice must not add copies.
    response = client.post(f"/ui/loans/{loan.id}/return")

    assert response.status_code == 302
    assert store.books[book["id"]].available_copies == 2


def test_ui_checkout_missing_book(client):
    response = client.post("/ui/loans", data={
        "book_id": "999",
        "member_id": "1"
    })

    assert response.status_code == 302
    assert len(store.loans) == 0


def test_ui_pages_load(client):
    for url in ["/", "/ui/books", "/ui/members", "/ui/loans"]:
        response = client.get(url)
        assert response.status_code == 200
