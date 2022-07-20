from datetime import datetime
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from library import db, login_manager, app
from flask_login import UserMixin


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))



UsersBooks = db.Table('UserBooks',
                      db.Column('user_id', db.Integer, db.ForeignKey('user.id')),
                      db.Column('book_id', db.Integer, db.ForeignKey('book.id'))
                      )


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(80), nullable=False)
    is_admin = db.Column(db.Boolean(), default=False, nullable=False)
    image_file = db.Column(db.String(120), default='default.jpg', nullable=False)
    time_created = db.Column(db.DateTime(), default=datetime.utcnow())
    borrowed_books = db.relationship('Book', secondary=UsersBooks, backref='borrowers')
    money= db.Column(db.Integer, nullable=False , default=1000)

    def get_reset_token(self, expires_sec=300):
        s = Serializer(app.config['SECRET_KEY'], expires_sec)
        return s.dumps({'user_id': self.id}).decode('utf-8')

    @staticmethod
    def verify_reset_token(token):
        s = Serializer(app.config['SECRET_KEY'])
        try:
            user_id = s.loads(token)['user_id']
        except:
            return None
        return User.query.get(user_id)

    def __repr__(self):
        return f"User('{self.username}', '{self.email}', '{self.image_file}')"



class Book(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    category = db.Column(db.Integer, nullable=False)
    description = db.Column(db.Text, default='No Info')
    author = db.Column(db.String(150), default='No Info', nullable=False)
    quantity = db.Column(db.Integer, default=1, nullable=False)
    published_at = db.Column(db.DateTime(), default=datetime.utcnow(), nullable=False)
    thumbnail = db.Column(db.String(120), default='default.jpg', nullable=False)
    price_per_month= db.Column(db.Integer, nullable=False)

    def __repr__(self):
        return f"Book('{self.name}', '{self.published_at}')"