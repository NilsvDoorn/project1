import os

from flask import Flask, flash, session, redirect, render_template, request, jsonify
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from werkzeug.security import check_password_hash, generate_password_hash
import requests

from helpers import apology, login_required

app = Flask(__name__)

# Check for environment variable
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")

# Configure session to use filesystem
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Set up database
engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))


@app.route("/")
@login_required
def search():
    books = db.execute("SELECT * FROM books").fetchall()
    return render_template("search.html", portfolio=books)

@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        password = db.execute("SELECT password FROM users WHERE username = :username", {'username':request.form.get("username")}).fetchone()[0]

        # Ensure username exists and password is correct
        if not check_password_hash(password, request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        id = db.execute("SELECT id FROM users WHERE username = :username", {'username':request.form.get("username")}).fetchone()[0]
        session["user_id"] = id
        db.commit()

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")

@app.route("/logout")
@login_required
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")

@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username")

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password")

        # Ensure password was submitted
        elif not request.form.get("confirmation"):
            return apology("Confirm password")

        # Ensure same password was submitted
        elif not request.form.get("confirmation") == request.form.get("password"):
            return apology("must provide the same password")

        # Ensure Username isn't used before
        elif db.execute("SELECT * FROM users WHERE username = :username", {"username": request.form.get("username")}).rowcount == 1:
            return apology("This username is already in use")

        # safity, hash password
        hash = generate_password_hash(request.form.get("password"))

        # Add user to database
        db.execute("INSERT INTO users (username, password) VALUES(:username, :hash)", {'username':request.form.get("username"), 'hash':hash})

        # Remember which user has logged in
        id = db.execute("SELECT id FROM users WHERE username = :username", {'username':request.form.get("username")}).first()
        session["user_id"] = id
        db.commit()

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("register.html")

@app.route("/review", methods=["POST"])
@login_required
def review():
    book_id = request.form['book_id']
    book = db.execute("SELECT * FROM books WHERE id = :id", {'id':book_id}).fetchall()[0]
    if db.execute("SELECT review, rating, username FROM reviews JOIN users ON users.id = reviews.user_id WHERE reviews.book_id = :book_id", {'book_id':book_id}).rowcount == 0:
        reviews = []
        reviews_count = 0
        rating = 0
    else:
        reviews = db.execute("SELECT review, rating, username FROM reviews JOIN users ON users.id = reviews.user_id AND reviews.book_id = :book_id", {'book_id':book_id}).fetchall()
        reviews_count = len(reviews)
        rating = 0
        for note in reviews:
            rating += note[1]
        if not reviews_count == 0:
            rating = rating / reviews_count

    # get all info from goodreads
    res = requests.get("https://www.goodreads.com/book/review_counts.json", params={"key": "t1uyNnTKFM6rnjongcEFQ", "isbns": book[1]})
    goodreads = res.json()['books'][0]
    return render_template("review.html", reviews=reviews, book=book, reviews_count=reviews_count, rating=rating, goodreads=goodreads)

@app.route("/submit_review", methods=["POST"])
@login_required
def submit_review():
    # get all info seperated
    book_id = request.form['book']
    user = session["user_id"]
    review = request.form.get('review')
    rating = request.form.get('rating')
    if review == '' or rating == '':
        flash("You didn't add a text or a rating")
        return redirect("/")
    elif db.execute("SELECT * FROM reviews WHERE book_id = :book_id AND user_id= :user_id", {'book_id':book_id, 'user_id':session["user_id"]}).rowcount == 1:
        flash("You already reviewed this book")
        return redirect("/")

    #insert into reviews
    db.execute("INSERT INTO reviews (user_id, book_id, review, rating) VALUES(:user, :book, :review, :rating)", {'user':user, 'book':book_id, 'review':review, 'rating':rating})
    db.commit()
    flash("Your review has been added")
    return redirect("/")

@app.route("/api/<string:isbn>", methods=["GET"])
@login_required
def json(isbn):
    if db.execute("SELECT * FROM books WHERE isbn = :isbn", {'isbn':isbn}).rowcount == 0:
        return jsonify('not found')
    info = db.execute("SELECT * FROM books WHERE isbn = :isbn", {'isbn':isbn}).first()
    print(info)
    if db.execute("SELECT * FROM reviews WHERE book_id = :book_id", {'book_id':info[1]}).rowcount == 0:
        reviews_count = 0
        rating = 0
    else:
        reviews = db.execute("SELECT * FROM reviews WHERE book_id = :book_id", {'book_id':info[1]}).fetchall()
        reviews_count = len(reviews)
        rating = 0
        for note in reviews:
            rating += note[4]
        if not reviews_count == 0:
            rating = rating / reviews_count
    db.commit()
    dict = {'isbn': info[1], 'title': info[2], 'author': info[3], 'year': info[4], 'review count': reviews_count, 'average rating': rating}
    return jsonify(dict)
