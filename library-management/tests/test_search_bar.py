import pytest

from app import create_app, store


@pytest.fixture
def client():
    app = create_app()
    app.config["TESTING"] = True
    store.books.clear()
    with app.test_client() as c:
        yield c
    store.books.clear()


def add_book(client, title, author, isbn="123", copies=1):
    return client.post("/books", json={
        "title": title, "author": author, "isbn": isbn, "total_copies": copies,
    })


def titles(res):
    return [b["title"] for b in res.get_json()]


def test_search_matches_title(client):
    add_book(client, "Dune", "Frank Herbert")
    add_book(client, "Emma", "Jane Austen")
    assert titles(client.get("/books?search=dune")) == ["Dune"]


def test_search_matches_author(client):
    add_book(client, "Dune", "Frank Herbert")
    add_book(client, "Emma", "Jane Austen")
    assert titles(client.get("/books?search=austen")) == ["Emma"]


def test_search_is_case_insensitive(client):
    add_book(client, "Dune", "Frank Herbert")
    assert titles(client.get("/books?search=DUNE")) == ["Dune"]


def test_search_partial_match(client):
    add_book(client, "Dune", "Frank Herbert")
    assert titles(client.get("/books?search=herb")) == ["Dune"]


def test_search_no_match_returns_empty_list(client):
    add_book(client, "Dune", "Frank Herbert")
    res = client.get("/books?search=zzz")
    assert res.status_code == 200
    assert res.get_json() == []


def test_no_search_returns_all(client):
    add_book(client, "Dune", "Frank Herbert")
    add_book(client, "Emma", "Jane Austen")
    assert len(client.get("/books").get_json()) == 2


def test_create_sets_available_copies(client):
    res = add_book(client, "Dune", "Frank Herbert", copies=3)
    assert res.status_code == 201
    assert res.get_json()["available_copies"] == 3


def test_get_missing_book_404(client):
    assert client.get("/books/999").status_code == 404