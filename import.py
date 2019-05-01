import csv
import os

from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))

def main():
    f = open("books.csv")
    reader = csv.reader(f)
    for isbn, name, author, year in reader:
        db.execute("INSERT INTO books (isbn, name, author, year, count_review, avg_rating) VALUES (:isbn, :name, :author, :year, :count_review, :avg_rating)",
                    {"isbn": isbn, "name": name, "author": author, "year": year, 'count_review': 0, 'avg_rating': 0})
    db.commit()

if __name__ == "__main__":
    main()
