# Library Management System (LMS)

A small Flask REST API for tracking books, members, and loans. Data is stored
**in memory** (plain Python objects, no database) and is reset every time the
app restarts — this project is meant to run before you've covered databases.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python run.py
```

The API runs at `http://127.0.0.1:5000`.

## Web UI

Open `http://127.0.0.1:5000/` in a browser for a basic HTML front end (plain
forms and tables, no JavaScript) to add/delete books and members, and check
books in/out:

| Page | Path |
|---|---|
| Home | `/` |
| Books | `/ui/books` |
| Members | `/ui/members` |
| Loans | `/ui/loans` |

This UI is separate from the JSON API below — it's there so you can see the
app working without a REST client, and calls the same in-memory store.


## Book Search

Searches books and has a second copy of the book table that is hidden until something is typed.
Updates every 250 ms to prevent it from updating every tick and/or every keystroke.
Implemented directly into the Books frontend in `books.html`

## Entities

- **Book**: `id, title, author, isbn, total_copies, available_copies`
- **Member**: `id, name, email, membership_date`
- **Loan**: `id, book_id, member_id, loan_date, due_date, return_date`

## JSON API Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/books` | List all books |
| POST | `/books` | Create a book |
| GET | `/books/<id>` | Get one book |
| PUT | `/books/<id>` | Update a book |
| DELETE | `/books/<id>` | Delete a book |
| GET | `/members` | List all members |
| POST | `/members` | Create a member |
| GET | `/members/<id>` | Get one member |
| PUT | `/members/<id>` | Update a member |
| DELETE | `/members/<id>` | Delete a member |
| POST | `/loans` | Check out a book (`book_id`, `member_id`) |
| PUT | `/loans/<id>/return` | Return a loaned book |
| POST | `/loans/<id>/remind` | Send an overdue-book reminder |
| PUT | `/loans/<id>/renew` | Renew a loan |
| GET | `/loans/<id>/fine` | Calculate an overdue fine |
| GET | `/loans?member_id=&book_id=` | Look up loans |
| GET | `/books?available=true` | List only books with available copies |




### Filter Available Books

Users can filter the book catalog to show only books that
currently have at least one available copy.

**Endpoint:** `GET /books?available=true`

Books with `available_copies = 0` are excluded.

Example:
`GET /books?available=true&search=Pytho

This combines book searching with availability filtering.



## Notification Service (Assignment 3)

The Library Management System includes a simulated
notification service for overdue books.

The notification service is implemented in
`notification_service.py`.

### Overdue Book Reminder

Endpoint: `POST /loans/<id>/remind`

When a reminder is requested, the system:

1. Checks whether the loan exists.
2. Verifies that the book has not been returned.
3. Checks whether the book is overdue.
4. Retrieves the member's email and book information.
5. Calls `send_notification()` to simulate a reminder.

If the notification succeeds, the response contains
`"notified": true`.

If notification delivery fails, the response contains
`"notified": false`.

The service does not send real emails.

### Testing

Assignment 3 uses pytest stubs and mocks to test
notification behavior without contacting an external service.

Member A tests are located in:

`tests/test_a3_yansheng.py`






## Tests

Run all tests:

```bash
python -m pytest -v
```

Run tests with coverage:

```bash
python -m pytest --cov=app --cov-report=term-missing --cov-report=html
```

Run Member A Assignment 3 tests:

```bash
python -m pytest tests/test_a3_yansheng.py -v
```

The project requires at least 90% application line coverage
for Assignment 3.
