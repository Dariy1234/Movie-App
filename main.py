from flask import Flask, render_template

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from flask_login import LoginManager, UserMixin,login_required
from dotenv import load_dotenv
import os
load_dotenv()
app = Flask(__name__,static_url_path='/static')
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URI")
app.config["SECRET_KEY"] = "THE BEST MOVIE APP IN THE WORLD"

DEBUG=os.getenv('DEBUG')
class Base(DeclarativeBase):
  pass
db = SQLAlchemy(model_class=Base)

# initialize the app with the extension
db.init_app(app)


login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "sign_in"
# login_manager.login_message = "Please log in to access this page."

class User(db.Model,UserMixin):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    comments = db.relationship("Comment", back_populates="user",lazy=True)
    likes = db.relationship("Like", back_populates="user",lazy=True)

    def __repr__(self):
        return f"<User {self.username}>"
    

from datetime import datetime
class Comment(db.Model):
    
    __tablename__ = "comments"
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.String(300), unique=False,  nullable=False)
    movie_id = db.Column(db.Integer,  nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)
    user = db.relationship("User", back_populates="comments")
 
class Like(db.Model):
    __tablename__ = "likes"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    movie_id = db.Column(db.Integer,  nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)
    user = db.relationship("User", back_populates="likes")
    
with app.app_context():
    db.create_all()
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(user_id)
users = []





@app.route("/")

def index():
    from back import get_popular_movies, get_top_rated_movies,get_upcoming_movies
    from flask_login import current_user
    
    movies_top = get_top_rated_movies()
    movies_popular = get_popular_movies()
    movies_upcoming = get_upcoming_movies()
    
    fav_movies = []
    if current_user.is_authenticated:
        fav_movies = [movie.movie_id for movie in current_user.likes]
        print("User favourite movies: ", fav_movies)
    return render_template("index.html",movies_popular=movies_popular, movies_top=movies_top, movies_upcoming=movies_upcoming,fav_movies=fav_movies)

@app.route("/movies/<movies_type>")
def movies_list(movies_type: str):
    from back import get_popular_movies, get_top_rated_movies,get_upcoming_movies
    from flask import request
    from flask_login import current_user
    page=request.args.get('page',1)
    if movies_type == "popular":
        movies = get_popular_movies(page)
    elif movies_type == "top_rated":
        movies = get_top_rated_movies()
    elif movies_type == "upcoming":
        movies =get_upcoming_movies ()
    else:
        movies = get_popular_movies()
    fav_movies = []
    if current_user.is_authenticated:
        fav_movies = [movie.movie_id for movie in current_user.likes]
        print("User favourite movies: ", fav_movies)
    return render_template("movies-list.html", movies=movies,fav_movies=fav_movies, movies_type=movies_type)
@app.route("/movies/<movies_type>/<movie_id>")

@app.route("/movie/<movie_id>/details", methods=["GET", "POST"])
def movie_details(movie_id):
    from back import get_movie_details,get_images_details,get_videos,get_recomended
    from flask import request, redirect
    from flask_login import current_user
    from flask import request, redirect
    movie = get_movie_details(movie_id)
    images = get_images_details(movie_id)
    videos = get_videos(movie_id)
    recommended = get_recomended(movie_id)
    video_key = videos[0].get('key') 
    filtered_videos = [
        video
        for video in videos
        if video.get("type", "") == "Trailer" and video.get("official", False)
    ]
    video_key = filtered_videos[0].get("key")
    if request.method == "POST":
        comment = request.form.get("content")

        print(comment)
        print(request.form)
        
        if not current_user.is_authenticated:
            return redirect("/sign_in")
        user_id = current_user.id
        new_comment = Comment(content=comment, movie_id=movie_id, user_id=user_id,user=current_user)
        db.session.add(new_comment)
        db.session.commit()

    comments = Comment.query.filter_by(movie_id=movie_id).all()
    
    fav_movies = []
    if current_user.is_authenticated:
        fav_movies = [movie.movie_id for movie in current_user.likes]
        print("User favourite movies: ", fav_movies)

    return render_template(
        "movies_detals.html",
        movie=movie,
        images=images,
        videos=videos,
        video_key=video_key,
        recommended=recommended,
        comments=comments
        ,fav_movies=fav_movies,
        
    )
@app.route("/movies/like/<movie_id>")
@login_required
def toggle_favourite_movie(movie_id):
    from flask_login import current_user
    from flask import redirect, request

    fav_movie = Like.query.filter_by(
        movie_id=movie_id, user=current_user
    ).first()
    if fav_movie:
        db.session.delete(fav_movie)
    else:
        fav_movie = Like(movie_id=movie_id, user=current_user)
        db.session.add(fav_movie)

    db.session.commit()
    return redirect(request.referrer or "/")

@app.route("/movies/search")
def search_movies():
    from flask import request
    from back import search_movies_list
    query = request.args.get("query", "")
    print("Search query:", query)
    movies = search_movies_list(query)
    return render_template("movies-list.html", movies=movies)

    
   
    
@app.route("/sign_in", methods=["GET", "POST"])
def sign_in():
    from flask import request, redirect
    from flask_login import LoginManager, login_user, UserMixin
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        user= User.query.filter_by(username=username).first()
        if not user:
            return render_template(
                "sign_in.html", error="Please enter username"
            )
        if user.password != password:
            return render_template(
                "sign_in.html", error="Please enter password"
            )
        login_user(user)
        
        return redirect("/")
    # for user in users:
        #     if user["username"] == username:
        #         if user["password"] != password:
        #             return render_template(
        #             "sign_in.html", error="Invalid username or password"
        # )
        #         return redirect("/")
        
    return render_template("sign_in.html")
@app.route("/registration", methods=["GET", "POST"])
def registration():
    from flask import request, redirect
    if request.method == "POST":
        username=request.form.get("username")
        password=request.form.get("password")
        email=request.form.get("email")
        if len(password.strip()) < 8:
            return render_template(
                "registration.html",error="Password must be at least 8 characters long"
            )
        if len(username.strip()) < 3:
            return render_template(
                "registration.html",error="Username must be at least 3 characters long"
            )
        if User.query.filter_by(username=username).first():
            return render_template("registration.html", error="Username already exists")

        if User.query.filter_by(email=email).first():
            return render_template("registration.html", error="Email already exists")
        users.append(
            {
                "username": username,
                "password": password,
                "email": email,
            }
        )
        user = User(username=username, password=password, email=email)
        db.session.add(user)
        db.session.commit()
        return redirect("/sign_in")

    return render_template("registration.html")
@app.route("/logout")
def logout():
    from flask import  redirect
    from flask_login import logout_user
    logout_user()
    return redirect('/sign_in')


# @app.route("/comments")
# def comments():
#     from flask import request
    
#     comments = request.form.get("comments")
    
#     if comments:
    
#         print("Comment received:", comments)
#     else:
#         comments = request.args.get("comments")
#     return render_template("comments.html", comments=comments)

@app.route("/comments/<comment_id>/delete")
@login_required
def delete_comment(comment_id):
    from flask import redirect, request
    
    comment = Comment.query.filter_by(id=comment_id).first()
    if not comment:
        return 'Comment not found', 404
    db.session.delete(comment)
    db.session.commit()
    return redirect(request.referrer or '/')


@app.route('/profile')
@login_required
def profile():
    
    from flask_login import current_user
    from back import get_movie_details
    
    favourite_movie=[
        get_movie_details(m.movie_id) for m in current_user.likes
    ]
    
    print("User favourite movies: ", favourite_movie)

    return render_template('Like.html', favourite_movie=favourite_movie)












app.run(debug=True)