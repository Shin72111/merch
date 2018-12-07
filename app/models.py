from app import db
from flask_login import UserMixin
from flask import current_app
from werkzeug.security import generate_password_hash, check_password_hash
from app import db, login
from app.search import add_to_index, remove_from_index, query_index

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True)
    password_hash = db.Column(db.String(128))

    def __repr__(self):
        return '<User {}>'.format(self.username)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)



class Products(db.Model):
    __searchable__ = ['name', 'features']
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(184), index=True)
    asin = db.Column(db.String(32), unique=True, index=True)
    image = db.Column(db.String(256))
    rank = db.Column(db.Integer, index=True)
    display_rank = db.Column(db.String(16))
    features = db.Column(db.Text)

    @classmethod
    def search(cls, expression, page, per_page):
        ids, total = query_index(cls.__tablename__, expression, page, per_page)
        if total == 0:
            return cls.query.filter_by(id=0), 0
        return cls.query.filter(cls.id.in_(ids)).order_by(cls.rank.asc()), total

    @classmethod
    def before_commit(cls, session):
        session._changes = {
            'add': list(session.new),
            'update': list(session.dirty),
            'delete': list(session.deleted)
        }


    @classmethod
    def after_commit(cls, session):
        for obj in session._changes['add']:
            if isinstance(obj, Products):
                add_to_index(obj.__tablename__, obj)
        for obj in session._changes['update']:
            if isinstance(obj, Products):
                add_to_index(obj.__tablename__, obj)
        for obj in session._changes['delete']:
            if isinstance(obj, Products):
                remove_from_index(obj.__tablename__, obj)
        session._changes = None

    @classmethod
    def reindex(cls):
        for obj in cls.query:
            add_to_index(cls.__tablename__, obj)


db.event.listen(db.session, 'before_commit', Products.before_commit)
db.event.listen(db.session, 'after_commit', Products.after_commit)

@login.user_loader
def load_user(id):
    return User.query.get(int(id))
