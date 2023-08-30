from flask import Flask, render_template, redirect, url_for, request
from flask_bootstrap import Bootstrap5
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired
import requests
import tkinter
from tkinter import messagebox
import os


MOVIE_DB_API_KEY = os.environ.get("API_KEY")
MOVIE_DB_API_TOP_RATED_URL = 'https://api.themoviedb.org/3/movie/top_rated'
MOVIE_DB_SEARCH_URL = "https://api.themoviedb.org/3/search/movie"
MOVIE_DB_INFO_URL = "https://api.themoviedb.org/3/movie"
MOVIE_DB_IMAGE_URL = "https://image.tmdb.org/t/p/w500"


app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get("FLASK_KEY")
Bootstrap5(app)

# create DB
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get("DB_URI", "sqlite:///movies.db")
db = SQLAlchemy()
db.init_app(app)


# create Table
class Movie(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(250), unique=True, nullable=False)
    year = db.Column(db.Integer, nullable=False)
    description = db.Column(db.String(500), nullable=False)
    rating = db.Column(db.Float, nullable=True)
    review = db.Column(db.String(250), nullable=True)
    img_url = db.Column(db.String(250), nullable=False)


class MyMovie(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(250), nullable=False)
    year = db.Column(db.Integer, nullable=False)
    description = db.Column(db.String(500), nullable=False)
    rating = db.Column(db.Float, nullable=True)
    review = db.Column(db.String(250), nullable=True)
    img_url = db.Column(db.String(250), nullable=False)


with app.app_context():
    db.create_all()


class SearchMovieForm(FlaskForm):
    title = StringField("Movie Title", validators=[DataRequired()])
    submit = SubmitField("Search Movie")


class ReviewMovieForm(FlaskForm):
    review = StringField("Your Review")
    submit = SubmitField("Done")


with app.app_context():
    x = db.session.query(Movie).first()
if not x:
    data = []
    for i in range(1, 6):
        response = requests.get(MOVIE_DB_API_TOP_RATED_URL, params={"api_key": MOVIE_DB_API_KEY, "page": i})
        extra = response.json()["results"]
        data += extra

    for i in range(len(data)):
        new_movie = Movie(
                title=data[i]["title"],
                year=data[i]["release_date"].split("-")[0],
                description=data[i]["overview"],
                rating=data[i]["vote_average"],
                review="-",
                img_url=f"{MOVIE_DB_IMAGE_URL}{data[i]['poster_path']}",
            )
        with app.app_context():
            db.session.add(new_movie)
            db.session.commit()


@app.route("/")
def home():
    result = db.session.execute(db.select(Movie))
    all_movies = result.scalars()
    return render_template("index.html", movies=all_movies)


@app.route("/mylist")
def my_list():
    my_movies = MyMovie.query.order_by(MyMovie.rating.desc()).all()
    db.session.commit()
    return render_template("my_list.html", movies=my_movies)


@app.route("/add")
def add_movie():
    movie_title = request.args.get("title")
    titles = []
    for s in MyMovie.query.all():
        title = s.title
        titles.append(title)
    if movie_title in titles:
        root = tkinter.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        tkinter.messagebox.showerror(title="Already selected", message="This movie has been already selected")
        root.mainloop()
        return redirect(url_for('home'))
    else:
        my_response = requests.get(MOVIE_DB_SEARCH_URL, params={"api_key": MOVIE_DB_API_KEY, "query": movie_title})
        my_data = my_response.json()["results"][0]
        my_movie = MyMovie(
                title=my_data["title"],
                year=my_data["release_date"].split("-")[0],
                description=my_data["overview"],
                rating=my_data["vote_average"],
                review="Not reviewed",
                img_url=f"{MOVIE_DB_IMAGE_URL}{my_data['poster_path']}",
        )
        with app.app_context():
            db.session.add(my_movie)
            db.session.commit()
        my_movies = MyMovie.query.order_by(MyMovie.rating.desc()).all()
        db.session.commit()
        return render_template("my_list.html", movies=my_movies)


@app.route("/search", methods=["GET", "POST"])
def search_movie():
    form = SearchMovieForm()
    if form.validate_on_submit():
        movie_title = form.title.data
        response = requests.get(MOVIE_DB_SEARCH_URL, params={"api_key": MOVIE_DB_API_KEY, "query": movie_title})
        data = response.json()["results"]
        return render_template("select.html", options=data)
    return render_template("search.html", form=form)


@app.route("/find")
def find_movie():
    movie_api_id = request.args.get("id")
    if movie_api_id:
        movie_api_url = f"{MOVIE_DB_INFO_URL}/{movie_api_id}"
        response = requests.get(movie_api_url, params={"api_key": MOVIE_DB_API_KEY})
        new_data = response.json()
        new_movie = MyMovie(
            title=new_data["title"],
            year=new_data["release_date"].split("-")[0],
            description=new_data["overview"],
            rating=new_data["vote_average"],
            review="Not reviewed",
            img_url=f"{MOVIE_DB_IMAGE_URL}{new_data['poster_path']}",
        )
        db.session.add(new_movie)
        db.session.commit()
        return redirect(url_for("my_list"))


@app.route("/review", methods=["GET", "POST"])
def review_movie():
    form = ReviewMovieForm()
    movie_id = request.args.get("id")
    movie = db.get_or_404(MyMovie, movie_id)
    if form.validate_on_submit():
        movie.review = form.review.data
        db.session.commit()
        return redirect(url_for('my_list'))
    return render_template("review.html", movie=movie, form=form)


@app.route("/delete")
def delete_movie():
    movie_id = request.args.get("id")
    movie = db.get_or_404(MyMovie, movie_id)
    db.session.delete(movie)
    db.session.commit()
    return redirect(url_for("my_list"))


if __name__ == '__main__':
    app.run(debug=False)
