from datetime import date, timedelta
from unittest.mock import patch

import notification_service
import pytest

from app import store
from app.models.book import Book
from app.models.loan import Loan
from app.models.member import Member
from app.models.reservation import Reservation


def add_book(title, copies=2):
    book_id = store.next_id("book")
    store.books[book_id] = Book(
        id=book_id,
        title=title,
        author="Frank Herbert",
        isbn="9780441013593",
        total_copies=copies,
        available_copies=copies,
    )
    return book_id


def add_member(name):
    member_id = store.next_id("member")
    store.members[member_id] = Member(id=member_id, name=name, email="jimbo@example.com")
    return member_id


def add_loan(book_id, member_id):
    loan_id = store.next_id("loan")
    store.loans[loan_id] = Loan(
        id=loan_id,
        book_id=book_id,
        member_id=member_id,
        due_date=Loan.default_due_date(),
    )
    return loan_id


def add_overdue_loan(book_title, member_name, days_overdue=5):
    book_id = add_book(book_title)
    member_id = add_member(member_name)
    loan_id = add_loan(book_id, member_id)
    store.loans[loan_id].due_date = date.today() - timedelta(days=days_overdue)
    return loan_id, book_id, member_id


def add_reservation(book_id, member_id):
    reservation_id = store.next_id("reservation")
    store.reservations[reservation_id] = Reservation(
        id=reservation_id,
        book_id=book_id,
        member_id=member_id,
        reservation_date=date.today(),
        fulfilled=False,
    )
    return reservation_id


# ---- views.py ----


def test_home_page_renders(client):
    resp = client.get("/")
    assert resp.status_code == 200


def test_books_page_lists_existing_books(client):
    add_book("Dune")
    resp = client.get("/ui/books")
    assert resp.status_code == 200
    assert b"Dune" in resp.data


def test_create_book_stores_book_and_redirects(client):
    before = set(store.books)
    resp = client.post(
        "/ui/books",
        data={"title": "Dune 2", "author": "Frank Herbert", "isbn": "123", "total_copies": "3"},
    )
    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/ui/books")
    created = [store.books[i] for i in set(store.books) - before]
    assert len(created) == 1
    assert created[0].title == "Dune 2"
    assert created[0].total_copies == 3
    assert created[0].available_copies == 3


@pytest.mark.parametrize("url, data, store_name", [
    ("/ui/books", {"author": "Frank Herbert", "isbn": "1", "total_copies": "1"}, "books"),
    ("/ui/members", {"name": "Jimbo James 3"}, "members"),
])
def test_form_missing_field_returns_400(client, url, data, store_name):
    before = len(getattr(store, store_name))
    resp = client.post(url, data=data)
    assert resp.status_code == 400
    assert len(getattr(store, store_name)) == before


def test_delete_book_removes_it_and_unknown_id_is_ignored(client):
    book_id = add_book("Dune 3")
    resp = client.post(f"/ui/books/{book_id}/delete")
    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/ui/books")
    assert book_id not in store.books
    before = len(store.books)
    resp = client.post("/ui/books/99999/delete")
    assert resp.status_code == 302
    assert len(store.books) == before


def test_members_page_lists_existing_members(client):
    add_member("Jimbo James 1")
    resp = client.get("/ui/members")
    assert resp.status_code == 200
    assert b"Jimbo James 1" in resp.data


def test_create_member_stores_member_and_redirects(client):
    before = set(store.members)
    resp = client.post("/ui/members", data={"name": "Jimbo James 2", "email": "jimbo2@example.com"})
    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/ui/members")
    created = [store.members[i] for i in set(store.members) - before]
    assert len(created) == 1
    assert created[0].name == "Jimbo James 2"
    assert created[0].email == "jimbo2@example.com"


def test_delete_member_removes_it_and_unknown_id_is_ignored(client):
    member_id = add_member("Jimbo James 4")
    resp = client.post(f"/ui/members/{member_id}/delete")
    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/ui/members")
    assert member_id not in store.members
    before = len(store.members)
    resp = client.post("/ui/members/99999/delete")
    assert resp.status_code == 302
    assert len(store.members) == before


def test_loans_page_renders(client):
    resp = client.get("/ui/loans")
    assert resp.status_code == 200


def test_create_loan_decrements_copies_and_records_loan(client):
    book_id = add_book("Dune 4", copies=2)
    member_id = add_member("Jimbo James 5")
    before = set(store.loans)
    resp = client.post("/ui/loans", data={"book_id": str(book_id), "member_id": str(member_id)})
    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/ui/loans")
    created = [store.loans[i] for i in set(store.loans) - before]
    assert len(created) == 1
    assert created[0].book_id == book_id
    assert created[0].member_id == member_id
    assert created[0].return_date is None
    assert created[0].due_date is not None
    assert store.books[book_id].available_copies == 1


def test_create_loan_unknown_book_creates_nothing(client):
    member_id = add_member("Jimbo James 6")
    before = len(store.loans)
    resp = client.post("/ui/loans", data={"book_id": "99999", "member_id": str(member_id)})
    assert resp.status_code == 302
    assert len(store.loans) == before


def test_create_loan_missing_member_returns_400(client):
    book_id = add_book("Dune 5", copies=1)
    resp = client.post("/ui/loans", data={"book_id": str(book_id)})
    assert resp.status_code == 400
    assert store.books[book_id].available_copies == 1


@pytest.mark.xfail(reason="view does not check available_copies before lending", strict=False)
def test_create_loan_rejected_when_no_copies_available(client):
    book_id = add_book("Dune 6", copies=1)
    member_id = add_member("Jimbo James 7")
    store.books[book_id].available_copies = 0
    before = len(store.loans)
    client.post("/ui/loans", data={"book_id": str(book_id), "member_id": str(member_id)})
    assert len(store.loans) == before
    assert store.books[book_id].available_copies == 0


def test_return_loan_sets_return_date_and_restores_copy(client):
    book_id = add_book("Dune 7", copies=2)
    member_id = add_member("Jimbo James 8")
    loan_id = add_loan(book_id, member_id)
    store.books[book_id].available_copies = 1
    resp = client.post(f"/ui/loans/{loan_id}/return")
    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/ui/loans")
    assert store.loans[loan_id].return_date == date.today()
    assert store.books[book_id].available_copies == 2


def test_return_already_returned_loan_does_not_double_count(client):
    book_id = add_book("Dune 8", copies=2)
    member_id = add_member("Jimbo James 9")
    loan_id = add_loan(book_id, member_id)
    store.books[book_id].available_copies = 1
    client.post(f"/ui/loans/{loan_id}/return")
    client.post(f"/ui/loans/{loan_id}/return")
    assert store.books[book_id].available_copies == 2


def test_return_unknown_loan_redirects_without_changes(client):
    book_id = add_book("Dune 9", copies=2)
    resp = client.post("/ui/loans/99999/return")
    assert resp.status_code == 302
    assert store.books[book_id].available_copies == 2


def test_return_loan_whose_book_was_deleted(client):
    book_id = add_book("Dune 10")
    member_id = add_member("Jimbo James 10")
    loan_id = add_loan(book_id, member_id)
    del store.books[book_id]
    resp = client.post(f"/ui/loans/{loan_id}/return")
    assert resp.status_code == 302
    assert store.loans[loan_id].return_date == date.today()


# ---- reservations.py ----


@pytest.mark.parametrize("filter_by", ["book_id", "member_id"])
def test_list_reservations_filters_by_single_field(client, filter_by):
    book_a = add_book("Dune 11")
    book_b = add_book("Dune 12")
    member_a = add_member("Jimbo James 11")
    member_b = add_member("Jimbo James 12")
    res_a = add_reservation(book_a, member_a)
    res_b = add_reservation(book_b, member_b)
    value = book_a if filter_by == "book_id" else member_a
    resp = client.get(f"/reservations?{filter_by}={value}")
    assert resp.status_code == 200
    ids = [r["id"] for r in resp.get_json()]
    assert res_a in ids
    assert res_b not in ids
    assert all(r[filter_by] == value for r in resp.get_json())


def test_list_reservations_filters_by_book_and_member(client):
    book_a = add_book("Dune 13")
    book_b = add_book("Dune 14")
    member_a = add_member("Jimbo James 13")
    member_b = add_member("Jimbo James 14")
    target = add_reservation(book_a, member_a)
    add_reservation(book_a, member_b)
    add_reservation(book_b, member_a)
    resp = client.get(f"/reservations?book_id={book_a}&member_id={member_a}")
    assert resp.status_code == 200
    assert [r["id"] for r in resp.get_json()] == [target]


def test_list_reservations_filter_with_no_match_returns_empty_list(client):
    resp = client.get("/reservations?book_id=99999")
    assert resp.status_code == 200
    assert resp.get_json() == []


def test_create_reservation_success(client):
    book_id = add_book("Dune 15")
    member_id = add_member("Jimbo James 15")
    before = set(store.reservations)
    resp = client.post("/reservations", json={"book_id": book_id, "member_id": member_id})
    assert resp.status_code == 201
    body = resp.get_json()
    assert body["book_id"] == book_id
    assert body["member_id"] == member_id
    created = set(store.reservations) - before
    assert len(created) == 1
    reservation = store.reservations[created.pop()]
    assert reservation.book_id == book_id
    assert reservation.member_id == member_id
    assert reservation.reservation_date == date.today()
    assert reservation.fulfilled is False


def test_create_reservation_unknown_book_returns_404(client):
    member_id = add_member("Jimbo James 16")
    before = len(store.reservations)
    resp = client.post("/reservations", json={"book_id": 99999, "member_id": member_id})
    assert resp.status_code == 404
    assert resp.get_json() == {"error": "Book not found"}
    assert len(store.reservations) == before


def test_create_reservation_unknown_member_returns_404(client):
    book_id = add_book("Dune 16")
    before = len(store.reservations)
    resp = client.post("/reservations", json={"book_id": book_id, "member_id": 99999})
    assert resp.status_code == 404
    assert resp.get_json() == {"error": "Member not found"}
    assert len(store.reservations) == before


# ---- loans.py: renew, fine ----


def test_renew_unknown_loan_returns_404(client):
    resp = client.put("/loans/99999/renew")
    assert resp.status_code == 404
    assert resp.get_json() == {"error": "Loan not found"}


def test_fine_unknown_loan_returns_404(client):
    resp = client.get("/loans/99999/fine")
    assert resp.status_code == 404
    assert resp.get_json() == {"error": "Loan not found"}


@pytest.mark.parametrize("days_overdue, expected_fine", [(4, 1.0), (1, 0.25), (0, 0.0), (-5, 0.0)])
def test_fine_amount_by_days_overdue(client, days_overdue, expected_fine):
    loan_id, _, _ = add_overdue_loan(f"Dune {days_overdue}", f"Jimbo James {days_overdue}", days_overdue)
    resp = client.get(f"/loans/{loan_id}/fine")
    assert resp.status_code == 200
    assert resp.get_json() == {"loan_id": loan_id, "fine_amount": expected_fine}


# ---- loans.py: overdue reminder notifications ----


def test_remind_unknown_loan_returns_404_and_sends_nothing(client):
    with patch("app.routes.loans.send_notification") as mock_send:
        resp = client.post("/loans/99999/remind")
    assert resp.status_code == 404
    assert resp.get_json() == {"error": "Loan not found"}
    mock_send.assert_not_called()


def test_remind_returned_loan_is_rejected_and_sends_nothing(client):
    loan_id, _, _ = add_overdue_loan("Dune 24", "Jimbo James 24")
    store.loans[loan_id].return_date = date.today()
    with patch("app.routes.loans.send_notification") as mock_send:
        resp = client.post(f"/loans/{loan_id}/remind")
    assert resp.status_code == 400
    assert resp.get_json() == {"error": "Book already returned", "notified": False}
    mock_send.assert_not_called()


@pytest.mark.parametrize("days_overdue", [-3, 0])
def test_remind_loan_not_overdue_is_rejected_and_sends_nothing(client, days_overdue):
    loan_id, _, _ = add_overdue_loan("Dune 25", "Jimbo James 25", days_overdue)
    with patch("app.routes.loans.send_notification") as mock_send:
        resp = client.post(f"/loans/{loan_id}/remind")
    assert resp.status_code == 400
    assert resp.get_json() == {"error": "Book is not overdue", "notified": False}
    mock_send.assert_not_called()


@pytest.mark.parametrize("missing", ["member", "book"])
def test_remind_missing_member_or_book_returns_404_and_sends_nothing(client, missing):
    loan_id, book_id, member_id = add_overdue_loan("Dune 27", "Jimbo James 27")
    if missing == "member":
        del store.members[member_id]
    else:
        del store.books[book_id]
    with patch("app.routes.loans.send_notification") as mock_send:
        resp = client.post(f"/loans/{loan_id}/remind")
    assert resp.status_code == 404
    assert resp.get_json() == {"error": "Member or book not found"}
    mock_send.assert_not_called()


def test_remind_failed_send_is_attempted_once_and_reported(client):
    loan_id, _, _ = add_overdue_loan("Dune 29", "Jimbo James 29")
    with patch("app.routes.loans.send_notification", return_value=False) as mock_send:
        resp = client.post(f"/loans/{loan_id}/remind")
    assert resp.status_code == 200
    assert resp.get_json() == {"loan_id": loan_id, "notified": False}
    assert store.loans[loan_id].return_date is None
    mock_send.assert_called_once()


@pytest.mark.parametrize("bad_email", ["not-an-email", "   "])
def test_remind_invalid_recipient_reports_failure(client, bad_email):
    loan_id, _, member_id = add_overdue_loan("Dune 31", "Jimbo James 31")
    store.members[member_id].email = bad_email
    notification_service.clear_notifications()
    resp = client.post(f"/loans/{loan_id}/remind")
    assert resp.status_code == 200
    assert resp.get_json() == {"loan_id": loan_id, "notified": False}
    assert notification_service.get_notifications() == []
    notification_service.clear_notifications()


def test_remind_succeeds_after_service_recovers(client, monkeypatch):
    loan_id, _, _ = add_overdue_loan("Dune 34", "Jimbo James 34")
    notification_service.clear_notifications()
    monkeypatch.setattr("notification_service.is_service_available", lambda: False)
    first = client.post(f"/loans/{loan_id}/remind")
    assert first.get_json()["notified"] is False
    assert notification_service.get_notifications() == []
    monkeypatch.setattr("notification_service.is_service_available", lambda: True)
    second = client.post(f"/loans/{loan_id}/remind")
    assert second.get_json() == {"loan_id": loan_id, "notified": True}
    assert len(notification_service.get_notifications()) == 1
    notification_service.clear_notifications()