
"""CISC 327 A2 - Book management tests (Yansheng Ni)."""


def make_book(client, title="Clean Code", author="Robert C. Martin",
              isbn="9780132350884", copies=2):
    return client.post("/books", json={
        "title": title,
        "author": author,
        "isbn": isbn,
        "total_copies": copies
    })


def test_create_book_and_get_by_id(client):
    created = make_book(client, copies=3)
    assert created.status_code == 201

    book = created.get_json()
    assert book["title"] == "Clean Code"
    assert book["author"] == "Robert C. Martin"
    assert book["total_copies"] == 3
    assert book["available_copies"] == 3

    fetched = client.get(f"/books/{book['id']}")
    assert fetched.status_code == 200
    assert fetched.get_json()["isbn"] == "9780132350884"


def test_list_books_after_multiple_creations(client):
    make_book(client, title="Book One", isbn="111")
    make_book(client, title="Book Two", isbn="222")

    response = client.get("/books")
    assert response.status_code == 200
    assert {b["title"] for b in response.get_json()} == {
        "Book One", "Book Two"
    }


def test_search_by_title_and_author_case_insensitive(client):
    make_book(client, title="Software Engineering",
              author="Ian Sommerville", isbn="111")
    make_book(client, title="Database Systems",
              author="Jane Smith", isbn="222")

    by_title = client.get("/books?search=SOFTWARE")
    assert by_title.status_code == 200
    assert [b["title"] for b in by_title.get_json()] == [
        "Software Engineering"
    ]

    by_author = client.get("/books?search=jane")
    assert by_author.status_code == 200
    assert [b["title"] for b in by_author.get_json()] == [
        "Database Systems"
    ]


def test_search_no_match_returns_empty_list(client):
    make_book(client)

    response = client.get("/books?search=not-present")
    assert response.status_code == 200
    assert response.get_json() == []


def test_get_missing_book_returns_404(client):
    response = client.get("/books/99999")

    assert response.status_code == 404
    assert response.get_json()["error"] == "Book not found"


def test_update_book_persists_changes(client):
    book_id = make_book(client).get_json()["id"]

    response = client.put(
        f"/books/{book_id}",
        json={"title": "Updated Title"}
    )

    assert response.status_code == 200
    assert response.get_json()["title"] == "Updated Title"

    fetched = client.get(f"/books/{book_id}").get_json()
    assert fetched["title"] == "Updated Title"
    assert fetched["author"] == "Robert C. Martin"


def test_delete_book_removes_it_from_catalog(client):
    book_id = make_book(client).get_json()["id"]

    deleted = client.delete(f"/books/{book_id}")
    assert deleted.status_code == 204

    assert client.get(f"/books/{book_id}").status_code == 404
    assert client.get("/books").get_json() == []


def test_update_and_delete_missing_book_return_404(client):
    update = client.put(
        "/books/99999",
        json={"title": "Nope"}
    )
    delete = client.delete("/books/99999")

    assert update.status_code == 404
    assert delete.status_code == 404
