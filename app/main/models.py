from datetime import datetime, timezone
from app import db
from flask_login import UserMixin, current_user


class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    memories = db.relationship('Memory', backref='author', lazy=True, foreign_keys='Memory.created_by')
    photos = db.relationship('Photo', backref='uploader', lazy=True, foreign_keys='Photo.uploaded_by')

    sent_letters = db.relationship(
        'SecretLetter',
        foreign_keys='SecretLetter.user_id',
        backref='sender',
        lazy=True,
        cascade='all, delete-orphan'
    )
    received_letters = db.relationship(
        'SecretLetter',
        foreign_keys='SecretLetter.recipient_id',
        backref='recipient',
        lazy=True
    )

    def __init__(self, **kwargs):
        if 'display_name' in kwargs and 'name' not in kwargs:
            kwargs['name'] = kwargs.pop('display_name')
        super().__init__(**kwargs)

    @property
    def display_name(self):
        return self.name

    @display_name.setter
    def display_name(self, value):
        self.name = value

    def __repr__(self):
        return f''


class Memory(db.Model):
    __tablename__ = 'memories'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    memory_date = db.Column(db.Date, nullable=False)
    location = db.Column(db.String(200), nullable=True)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    photos = db.relationship('Photo', backref='memory', lazy=True, cascade='all, delete-orphan')

    def __init__(self, **kwargs):
        if 'date' in kwargs and 'memory_date' not in kwargs:
            kwargs['memory_date'] = kwargs.pop('date')
        if 'user_id' in kwargs and 'created_by' not in kwargs:
            kwargs['created_by'] = kwargs.pop('user_id')
        super().__init__(**kwargs)

    @property
    def date(self):
        return self.memory_date

    @date.setter
    def date(self, value):
        self.memory_date = value

    @property
    def user_id(self):
        return self.created_by

    @user_id.setter
    def user_id(self, value):
        self.created_by = value

    def __repr__(self):
        return f''


class Photo(db.Model):
    __tablename__ = 'photos'

    id = db.Column(db.Integer, primary_key=True)
    file_path = db.Column(db.String(255), nullable=False)
    caption = db.Column(db.String(300), nullable=True)
    uploaded_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    memory_id = db.Column(db.Integer, db.ForeignKey('memories.id'), nullable=True)
    uploaded_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    def __init__(self, **kwargs):
        if 'filename' in kwargs and 'file_path' not in kwargs:
            kwargs['file_path'] = kwargs.pop('filename')

        if 'user_id' in kwargs and 'uploaded_by' not in kwargs:
            kwargs['uploaded_by'] = kwargs.pop('user_id')
        elif 'created_by' in kwargs and 'uploaded_by' not in kwargs:
            kwargs['uploaded_by'] = kwargs.pop('created_by')

        if 'uploaded_by' not in kwargs:
            if hasattr(current_user, 'id') and current_user.is_authenticated:
                kwargs['uploaded_by'] = current_user.id

        super().__init__(**kwargs)

    @property
    def filename(self):
        return self.file_path

    @filename.setter
    def filename(self, value):
        self.file_path = value

    @property
    def user_id(self):
        return self.uploaded_by

    @user_id.setter
    def user_id(self, value):
        self.uploaded_by = value

    def __repr__(self):
        return f''


class SecretLetter(db.Model):
    __tablename__ = 'secret_letters'

    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(30), nullable=False, default='letter')
    title = db.Column(db.String(200), nullable=False)
    body = db.Column(db.Text, nullable=False)
    unlock_date = db.Column(db.Date, nullable=True)
    cover_hint = db.Column(db.String(255), nullable=True)
    mood_tag = db.Column(db.String(50), nullable=True)
    box_type = db.Column(db.String(50), nullable=True, default='gift')

    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    recipient_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    def is_unlocked(self):
        if not self.unlock_date:
            return True
        today = datetime.now(timezone.utc).date()
        return today >= self.unlock_date

    def days_remaining(self):
        if not self.unlock_date:
            return 0
        today = datetime.now(timezone.utc).date()
        delta = (self.unlock_date - today).days
        return max(0, delta)

    def __repr__(self):
        return f''