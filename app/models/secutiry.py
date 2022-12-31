from flask import current_app as app
from flask_security import UserMixin, RoleMixin
from flask_security.utils import hash_password, verify_password
from sqlalchemy import cast, extract, Date
from sqlalchemy.ext.hybrid import hybrid_property
from datetime import date, datetime



from app.core.db import db
from app.utils.kernel import validate_password, format_elapsed_time
from datetime import datetime


roles_users = db.Table('roles_users',
                            db.Column('user_id', db.Integer(), db.ForeignKey('user.id')),
                            db.Column('role_id', db.Integer(), db.ForeignKey('role.id')))

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(32), index=True, nullable=False, unique=True)
    name = db.Column(db.String(512), index=True, nullable=False)
    email = db.Column(db.String(128), index=True, unique=True, nullable=False)
    _password = db.Column(db.String(512), nullable=False)
    temp_password = db.Column(db.Boolean, nullable=False, default=True)
    about_me = db.Column(db.String(512))
    last_seen = db.Column(db.DateTime, default=datetime.utcnow())
    location = db.Column(db.String(128), nullable=True)
    active = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow())
    created_network_id = db.Column(db.Integer, db.ForeignKey('network.id'), nullable=False)
    confirmed_network_id = db.Column(db.Integer, db.ForeignKey('network.id'))
    confirmed_at = db.Column(db.DateTime, nullable=True)
    login_count = db.Column(db.Integer, nullable=True, default=0)
    roles = db.relationship('Role', 
                secondary=roles_users, 
                backref=db.backref('users', lazy='dynamic'), 
                lazy='dynamic')
    sessions = db.relationship('LoginSession', backref='user', lazy='dynamic')
    
    @property
    def is_admin(self):
        if any([role.is_admin for role in self.roles.all()]):
            return True
        return False
    @property
    def is_manager_user(self):
        if any([role.is_manager_user for role in self.roles.all()]):
            return True
        return False
    @property
    def is_editor(self):
        if any([role.is_editor for role in self.roles.all()]):
            return True
        return False
    
    @property
    def is_aux_editor(self):
        if any([role.is_aux_editor for role in self.roles.all()]):
            return True
        return False

    @property
    def can_edit(self):
        if any([role.can_edit for role in self.roles.all()]):
            return True
        return False
    @property
    def is_support(self):
        if any([role.is_support for role in self.roles.all()]):
            return True
        return False
    @property
    def has_support(self):
        if any([role.has_support for role in self.roles.all()]):
            return True
        return False
    
    @property
    def is_viewer(self):
        if any([role.is_viewer for role in self.roles.all()]):
            return True
        return False
    @property
    def is_temp_password(self):
        return self.temp_password is True
    @hybrid_property
    def current_login_ip(self):
        if self.current_login_network is None:
            return None
        return self.current_login_network.ip


    @current_login_ip.setter
    def current_login_ip(self, ip):
        from app.models.network import Network
        network = Network.query.filter(Network.ip == ip).first()
        if network is None:
            network = Network()
            network.ip = ip
            try:
                db.session.add(network)
                db.session.commit()
            except Exception as e:
                app.logger.error(app.config.get('_ERRORS').get('DB_COMMIT_ERROR'))
                app.logger.error(e)
                raise Exception('Não foi possível salvar o IP')
        self.current_login_network_id = network.id
        # try:
        #     db.session.commit()
        # except Exception as e:
        #     app.logger.error(app.config.get('_ERRORS').get('DB_COMMIT_ERROR'))
        #     app.logger.error(e)
        #     raise Exception('Não foi possível salvar o IP')

    
    @hybrid_property
    def password(self):
        return self._password

    @password.setter
    def password(self, password):
        _validate_password = validate_password(password)
        if _validate_password['ok']:
            self._password = hash_password(password)
        else:
            raise ValueError('Não foi possível validar a senha')
    @property
    def last_seen_elapsed(self):
        return format_elapsed_time(self.last_seen)
    def check_password(self, password):
        return verify_password(password, self.password)

    @property
    def format_create_date(self):
        return self.created_at.strftime("%d/%m/%Y")

    @property
    def format_active(self):
        return 'Sim' if self.active else 'Não'

    @property
    def questions_liked_count(self):
        return self.question_like.count()

    @property
    def questions_saved_count(self):
        return self.question_save.count()
    
    @property
    def first_name(self):
        return self.name.split()[0]

    def __repr__(self):
        return f'<User {self.username}>'
    
    @staticmethod
    def query_by_month_year(year : int, month : int):
        return User.query.filter(extract('year', User.created_at) == year, extract('month', User.created_at) == month)
    @staticmethod
    def query_by_year(year : int):
        return User.query.filter(extract('year', User.created_at) == year)
    @staticmethod
    def query_by_date(date: date):
        return User.query.filter(cast(User.created_at, Date) == date)
    
    @staticmethod
    def query_by_interval(start : date, end: date):
        return User.query.filter(cast(User.created_at, Date) == start, cast(User.created_at, Date) == end)

class Role(RoleMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    level = db.Column(db.Integer, unique=False, nullable=False)
    name = db.Column(db.String(128), nullable=False, unique=True)
    description = db.Column(db.String(255), nullable=True)

    @property
    def is_admin(self):
        if self.level == 0:
            return True
        return False
    
    @property
    def is_manager_user(self):
        if self.level == 1:
            return True
        return False

    @property
    def is_editor(self):
        if self.level == 2:
            return True
        return False

    @property
    def is_aux_editor(self):
        if self.level == 3:
            return True
        return False
    
    @property
    def is_support(self):
        if self.level in [0, 1 ,2, 3, 4]:
            return True
        return False
    @property
    def has_support(self):
        if self.level in [0,2,3,4,5]:
            return True
        return False

    @property
    def is_viewer(self):
        if self.level == 5:
            return True
        return False

    @property
    def can_edit(self):
        if self.level in [0, 2, 3]:
            return True
        return False

    def __repr__(self):
        return f'<Role {self.name}>'


class LoginSession(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    datetime = db.Column(db.DateTime, default=datetime.utcnow())
    location = db.Column(db.String(128), nullable=True)
    network_id = db.Column(db.Integer, db.ForeignKey('network.id'))