from datetime import datetime
from flask import current_app
from flask_login import UserMixin
from foosbam import db, login
import jwt
import sqlalchemy as sa 
import sqlalchemy.orm as so
from time import time
from werkzeug.security import generate_password_hash, check_password_hash

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id: so.Mapped[int] = so.mapped_column(primary_key=True, autoincrement=True)
    username: so.Mapped[str] = so.mapped_column(sa.String(64), unique=True, nullable=False)
    email: so.Mapped[str] = so.mapped_column(sa.String(256), unique=True, nullable=False)
    password_hash: so.Mapped[str] = so.mapped_column(sa.String(256), nullable=False)

    def __repr__(self):
        return f'<User {self.username}>'
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password_hash(self, password):
        return check_password_hash(self.password_hash, password)
    
    def get_reset_password_token(self, expires_in=600):
        return jwt.encode(
            {'user_id': self.id,
             'exp': time() + expires_in},
            current_app.config['SECRET_KEY'],
            algorithm='HS256'
        )
    
    @staticmethod
    def verify_reset_password_token(token):
        try:
            id = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=['HS256'])['user_id']
        except:
            return
        return db.session.get(User, id)
    
    @login.user_loader
    def load_user(id):
        return(db.session.get(User, int(id)))
    
class Match(db.Model):
    __tablename__ = 'matches'
    id: so.Mapped[int] = so.mapped_column(primary_key=True, autoincrement=True)
    played_at: so.Mapped[datetime] = so.mapped_column(sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False, index=True)
    season: so.Mapped[int] = so.mapped_column(nullable=True) # temp nullable
    att_black: so.Mapped[int] = so.mapped_column(sa.ForeignKey(User.id), nullable=False)
    att_white: so.Mapped[int] = so.mapped_column(sa.ForeignKey(User.id), nullable=False)
    def_black: so.Mapped[int] = so.mapped_column(sa.ForeignKey(User.id), nullable=False)
    def_white: so.Mapped[int] = so.mapped_column(sa.ForeignKey(User.id), nullable=False)

class Result(db.Model):
    __tablename__ = 'results'
    id: so.Mapped[int] = so.mapped_column(primary_key=True, autoincrement=True)
    match_id: so.Mapped[int] = so.mapped_column(sa.ForeignKey(Match.id), nullable=False)
    created_at: so.Mapped[datetime] = so.mapped_column(sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False, index=True)
    created_by: so.Mapped[int] = so.mapped_column(sa.ForeignKey(User.id), nullable=False)
    checked_at: so.Mapped[datetime] = so.mapped_column(sa.DateTime(timezone=True), nullable=True)
    checked_by: so.Mapped[int] = so.mapped_column(sa.ForeignKey(User.id), nullable=True)
    status: so.Mapped[str] = so.mapped_column(sa.String(64), nullable=False)
    score_black: so.Mapped[int] = so.mapped_column(nullable=False)
    score_white: so.Mapped[int] = so.mapped_column(nullable=False)
    klinker_att_black: so.Mapped[int] = so.mapped_column(nullable=False)
    klinker_att_white: so.Mapped[int] = so.mapped_column(nullable=False)
    klinker_def_black: so.Mapped[int] = so.mapped_column(nullable=False)
    klinker_def_white: so.Mapped[int] = so.mapped_column(nullable=False)
    keeper_black: so.Mapped[int] = so.mapped_column(nullable=False)
    keeper_white: so.Mapped[int] = so.mapped_column(nullable=False)

class Rating(db.Model):
    __tablename__ = 'ratings'
    id: so.Mapped[int] = so.mapped_column(primary_key=True, autoincrement=True)
    user_id: so.Mapped[int] = so.mapped_column(sa.ForeignKey(User.id), nullable=False)
    match_id: so.Mapped[int] = so.mapped_column(sa.ForeignKey(Match.id), nullable=True) # nulls allowed for initial ratings
    since: so.Mapped[datetime] = so.mapped_column(sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False, index=True)
    season: so.Mapped[int] = so.mapped_column(nullable=True) # temp nullable
    previous_rating: so.Mapped[int] = so.mapped_column(nullable=True) # nulls allowed for initial ratings
    rating: so.Mapped[int] = so.mapped_column(nullable=False)
    previous_rating_season: so.Mapped[int] = so.mapped_column(nullable=True) # nulls allowed for initial ratings (at start of each season)
    rating_season: so.Mapped[int] = so.mapped_column(nullable=True) # nulls allowed for initial ratings
