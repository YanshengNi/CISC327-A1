from datetime import date

import pytest

from app import store
from app.models.book import Book
from app.models.loan import Loan
from app.models.member import Member


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


def test_create_book_missing_field_returns_400(client):
    before = len(store.books)
    resp = client.post("/ui/books", data={"author": "Frank Herbert", "isbn": "1", "total_copies": "1"})
    assert resp.status_code == 400
    assert len(store.books) == before


def test_delete_book_removes_it(client):
    book_id = add_book("Dune 3")
    resp = client.post(f"/ui/books/{book_id}/delete")
    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/ui/books")
    assert book_id not in store.books


def test_delete_unknown_book_still_redirects(client):
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


def test_create_member_missing_email_returns_400(client):
    before = len(store.members)
    resp = client.post("/ui/members", data={"name": "Jimbo James 3"})
    assert resp.status_code == 400
    assert len(store.members) == before


def test_delete_member_removes_it(client):
    member_id = add_member("Jimbo James 4")
    resp = client.post(f"/ui/members/{member_id}/delete")
    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/ui/members")
    assert member_id not in store.members


def test_delete_unknown_member_still_redirects(client):
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