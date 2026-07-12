"""A simple Flask application for managing a book collection."""

# Import the necessary modules from Flask
from flask import Flask, jsonify, request

# Initialize the Flask application
app = Flask(__name__)

# In-memory storage for the book collection
# In a production environment, you would use a proper database
books = [
    {"id": 1, "title": "1984", "author": "George Orwell"},
    {"id": 2, "title": "Brave New World", "author": "Aldous Huxley"},
]


@app.route("/books", methods=["GET"])
def get_books():
    """Return the complete list of books."""
    # Return the books as a JSON response
    return jsonify(books)


@app.route("/books/<int:book_id>", methods=["GET"])
def get_book(book_id):
    """Return a single book by its ID."""
    # Search for the book with the given ID
    for book in books:
        if book["id"] == book_id:
            return jsonify(book)
    # If no book was found, return a 404 error
    return jsonify({"error": "Book not found"}), 404


@app.route("/books", methods=["POST"])
def add_book():
    """Add a new book to the collection."""
    data = request.get_json()

    # Validate that the required fields are present
    if not data or "title" not in data or "author" not in data:
        return jsonify({"error": "Title and author are required"}), 400

    # Create the new book entry
    new_book = {
        "id": len(books) + 1,
        "title": data["title"],
        "author": data["author"],
    }
    # Add the new book to the collection
    books.append(new_book)

    return jsonify(new_book), 201


@app.route("/books/<int:book_id>", methods=["DELETE"])
def delete_book(book_id):
    """Delete a book from the collection."""
    global books
    # Filter out the book with the matching ID
    books = [book for book in books if book["id"] != book_id]
    return "", 204


if __name__ == "__main__":
    # Run the application in debug mode
    # Note: Set debug=False in a production environment
    app.run(debug=True, port=5000)
