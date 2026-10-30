
# CISC 327 Assignment 2
# Member and Loan Unit Tests - Xander Lynch

import pytest


def create_member(client, name="Alex Reader", email="alex@example.com"):
    response = client.post("/members", json={
        "name": name,
        "email": email
    })
    assert response.status_code == 201
    return response.get_json()


def create_book(client, copies=1):
    response = client.post("/books", json={
        "title": "Library Test Book",
        "author": "Test Author",
        "isbn": "LOAN-001",
        "total_copies": copies
    })
    assert response.status_code == 201
    return response.get_json()


def checkout(client, member_id, book_id):
    return client.post("/loans", json={
        "member_id": member_id,
        "book_id": book_id
    })


def test_create_member_and_retrieve_record(client):
    member = create_member(client)

    assert member["name"] == "Alex Reader"
    assert member["email"] == "alex@example.com"

    response = client.get(f"/members/{member['id']}")
    assert response.status_code == 200
    assert response.get_json()["email"] == "alex@example.com"


def test_list_members_after_creation(client):
    create_member(client, "Alex Reader", "alex@example.com")
    create_member(client, "Sam Reader", "sam@example.com")

    response = client.get("/members")

    assert response.status_code == 200
    names = {m["name"] for m in response.get_json()}
    assert names == {"Alex Reader", "Sam Reader"}


def test_checkout_reduces_available_copies(client):
    member = create_member(client)
    book = create_book(client)

    response = checkout(client, member["id"], book["id"])

    assert response.status_code == 201

    loan = response.get_json()
    assert loan["member_id"] == member["id"]
    assert loan["book_id"] == book["id"]
    assert loan["due_date"] is not None

    updated_book = client.get(f"/books/{book['id']}").get_json()
    assert updated_book["available_copies"] == 0


def test_return_restores_available_copies(client):
    member = create_member(client)
    book = create_book(client)

    loan = checkout(client, member["id"], book["id"]).get_json()

    response = client.put(f"/loans/{loan['id']}/return")

    assert response.status_code == 200
    assert response.get_json()["return_date"] is not None

    updated_book = client.get(f"/books/{book['id']}").get_json()
    assert updated_book["available_copies"] == 1


def test_checkout_when_no_copies_remain_is_rejected(client):
    member = create_member(client)
    book = create_book(client, copies=1)

    first = checkout(client, member["id"], book["id"])
    assert first.status_code == 201

    second = checkout(client, member["id"], book["id"])

    # This test exposes a known bug in loans.py.
    # The application currently accepts the second checkout.
    assert second.status_code in (400, 409)

    updated_book = client.get(f"/books/{book['id']}").get_json()
    assert updated_book["available_copies"] == 0


def test_checkout_nonexistent_book_returns_404(client):
    member = create_member(client)

    response = checkout(client, member["id"], 99999)

    assert response.status_code == 404
    assert response.get_json()["error"] == "Book not found"


def test_return_nonexistent_loan_returns_404(client):
    response = client.put("/loans/99999/return")

    assert response.status_code == 404
    assert response.get_json()["error"] == "Loan not found"


def test_cannot_return_same_loan_twice(client):
    member = create_member(client)
    book = create_book(client)
    loan = checkout(client, member["id"], book["id"]).get_json()

    first = client.put(f"/loans/{loan['id']}/return")
    second = client.put(f"/loans/{loan['id']}/return")

    assert first.status_code == 200
    assert second.status_code == 400
    assert second.get_json()["error"] == "Loan already returned"

    updated_book = client.get(f"/books/{book['id']}").get_json()
    assert updated_book["available_copies"] == 1


def test_renew_loan_extends_due_date(client):
    member = create_member(client)
    book = create_book(client)
    loan = checkout(client, member["id"], book["id"]).get_json()

    original_due_date = loan["due_date"]

    response = client.put(f"/loans/{loan['id']}/renew")

    assert response.status_code == 200
    assert response.get_json()["due_date"] > original_due_date


def test_cannot_renew_returned_loan(client):
    member = create_member(client)
    book = create_book(client)
    loan = checkout(client, member["id"], book["id"]).get_json()

    client.put(f"/loans/{loan['id']}/return")

    response = client.put(f"/loans/{loan['id']}/renew")

    assert response.status_code == 400
    assert response.get_json()["error"] == "Loan already returned"


def test_list_loans_filter_by_book_id(client):
    member = create_member(client)
    book1 = create_book(client)
    book2 = create_book(client)

    checkout(client, member["id"], book1["id"])
    checkout(client, member["id"], book2["id"])

    response = client.get(f"/loans?book_id={book1['id']}")

    assert response.status_code == 200
    loans = response.get_json()
    assert len(loans) == 1
    assert loans[0]["book_id"] == book1["id"]


def test_list_loans_filter_by_member_id(client):
    member1 = create_member(client, "Alex", "alex@example.com")
    member2 = create_member(client, "Sam", "sam@example.com")
    book1 = create_book(client)
    book2 = create_book(client)

    checkout(client, member1["id"], book1["id"])
    checkout(client, member2["id"], book2["id"])

    response = client.get(f"/loans?member_id={member1['id']}")

    assert response.status_code == 200
    loans = response.get_json()

    # This test detects the incorrect member filter in loans.py.
    assert len(loans) == 1
    assert loans[0]["member_id"] == member1["id"]
