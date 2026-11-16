
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
