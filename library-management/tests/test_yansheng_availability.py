
"""Tests for filtering available books - Yansheng Ni."""


def add_book(client, title, isbn, copies):
    response = client.post("/books", json={
        "title": title,
        "author": "Test Author",
        "isbn": isbn,
        "total_copies": copies
    })
    assert response.status_code == 201
    return response.get_json()


def test_filter_only_available_books(client):
    add_book(client, "Clean Code", "111", 3)
    add_book(client, "Python Basics", "222", 0)

    response = client.get("/books?available=true")

    assert response.status_code == 200
    titles = [book["title"] for book in response.get_json()]
    assert titles == ["Clean Code"]


def test_filter_when_no_books_available(client):
    add_book(client, "Unavailable Book", "333", 0)

    response = client.get("/books?available=true")

    assert response.status_code == 200
    assert response.get_json() == []
