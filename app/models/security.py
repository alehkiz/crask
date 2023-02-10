from typing import Optional
from flask import current_app as app
from flask_security.utils import hash_password, verify_password
from sqlalchemy import cast, extract, Date
from sqlalchemy.ext.hybrid import hybrid_property
from datetime import date, datetime
from flask_security.models import fsqla_v3 as fsqla
from flask_security import UserMixin, RoleMixin
from flask_sqlalchemy import BaseQuery
from sqlalchemy.orm import mapped_column, Mapped
import uuid
from sqlalchemy.dialects.postgresql import UUID


from app.core.db import db
from app.utils.kernel import validate_password
from app.utils.datetime import format_elapsed_time
from app.models.base import BaseModel, str_32, str_512, str_128, str_256
from datetime import datetime



roles_users = db.Table('roles_users',
                            db.Column('user_id', UUID(as_uuid=True), db.ForeignKey('user.id')),
                            db.Column('role_id', UUID(as_uuid=True), db.ForeignKey('role.id')))

# services_users = db.Table('services_users',
#                             db.Column('user_id', UUID(as_uuid=True), db.ForeignKey('user.id')),
#                             db.Column('service_id', UUID(as_uuid=True), db.ForeignKey('service.id')))
group_services_users = db.Table('group_services_users',
                            db.Column('user_id', UUID(as_uuid=True), db.ForeignKey('user.id')),
                            db.Column('group_service_id', UUID(as_uuid=True), db.ForeignKey('group_service.id')))

class User(BaseModel, UserMixin):
    __abstract__ = False
    username : Mapped[str_32] = db.Column(index=True, nullable=False, unique=True)
    name : Mapped[str_512] = db.Column(index=True, nullable=False)
    email : Mapped[str_128] = db.Column(db.String(128), index=True, unique=True, nullable=False)
    _password : Mapped[str_512] = db.Column(nullable=False)
    temp_password : Mapped[bool] = db.Column(nullable=False, default=True)
    about_me : Mapped[str_512] = db.Column()
    last_seen : Mapped[datetime] = db.Column(db.DateTime(timezone=True), default=datetime.utcnow())
    location : Mapped[str_128] = db.Column(nullable=True)
    active : Mapped[bool]  = db.Column(db.Boolean, default=False)
    created_network_id : Mapped[uuid.UUID] = db.Column(db.ForeignKey('network.id'), nullable=False)
    confirmed_network_id : Mapped[uuid.UUID] = db.Column(db.ForeignKey('network.id'))
    confirmed_at  : Mapped[datetime] = db.Column(nullable=True)
    login_count  : Mapped[int] = db.Column(nullable=True, default=0)
    # session_token = db.Column(db.String(256), index=True) 
    current_login_network_id  : Mapped[uuid.UUID] = db.Column(db.ForeignKey('network.id'))
    fs_uniquifier  : Mapped[str_256] = db.Column(unique=True, nullable=False, default=uuid.uuid4)
    

    roles = db.relationship('Role', 
                secondary=roles_users, 
                backref=db.backref('users', lazy='dynamic'), 
                lazy='dynamic')
    # services = db.relationship('Service', 
    #             secondary=services_users, 
    #             backref=db.backref('users', lazy='dynamic'), 
    #             lazy='dynamic')
    # group_services = db.relationship('GroupService', 
    #             secondary=group_services_users, 
    #             backref=db.backref('group_services', lazy='dynamic'), 
    #             lazy='dynamic')
    sessions = db.relationship('LoginSession', backref='user', lazy='dynamic', order_by='LoginSession.create_at.desc()')
    sended_messages = db.relationship('Message', backref=db.backref('sender'), lazy='dynamic', foreign_keys='[Message.user_sender_id]')
    received_messages = db.relationship('Message', backref=db.backref('receiver'), lazy='dynamic', foreign_keys='[Message._user_destiny_id]')
    # current_login_network = db.relationship('Network', backref=db.backref('current_user_login'), lazy='dynamic', foreign_keys='[User.current_login_network_id]')
    tickets = db.relationship('Ticket', secondary='ticket_stage_event', back_populates='users', lazy='dynamic')
    tickets_stage_event = db.relationship('TicketStageEvent', back_populates='user', viewonly=True)

    def get_id(self):                                                           
        return str(self.fs_uniquifier)

    

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
        if self.sessions.first() is None:
            return None
        return self.sessions.first().ip


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
        try:
            db.session.commit()
        except Exception as e:
            app.logger.error(app.config.get('_ERRORS').get('DB_COMMIT_ERROR'))
            app.logger.error(e)
            raise Exception('Não foi possível salvar o IP')

    
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
    def format_create_date(self) -> str:
        return self.created_at.strftime("%d/%m/%Y")

    @property
    def format_active(self) -> str:
        return 'Sim' if self.active else 'Não'

    @property
    def questions_liked_count(self) -> int:
        return self.question_like.count()

    @property
    def questions_saved_count(self) -> int:
        return self.question_save.count()
    
    @property
    def first_name(self) -> str:
        return self.name.split()[0]

    def __repr__(self) -> str:
        return f'<User {self.username}>'


    ####### QUERIES ##############

    def tickets_datetime_deadline(self, dt:Optional[datetime] = None) -> BaseQuery:
        from app.models.ticket import TicketStageEvent
        
        if dt is None:
            dt = datetime.now()
        return db.session.query(TicketStageEvent)\
            .join(User, TicketStageEvent.user)\
            .filter(User.id == self.id, TicketStageEvent.deadline < dt, TicketStageEvent.closed != False)
    
    def tickets_delay_from_now(self) -> BaseQuery:
        from app.models.ticket import TicketStageEvent
        dt = datetime.now()
        return self.tickets_datetime_deadline(dt)

    @property
    def unreaded_messages(self):
        from app.models.chat import Message
        total_messages = db.session.query(db.func.count(Message.id).label('cnt')).join(User.received_messages).filter(User.id == self.id).subquery()

        read_msg = db.session.query(db.func.count(Message.id).label('cnt'))\
                        .join(User.readed_messages)\
                            .filter(User.id == self.id)\
                                .subquery()
        count_unread = db.session.query(total_messages.c.cnt - read_msg.c.cnt).scalar()
        return count_unread

    @property
    def teams_ordered_by_last_message(self):
        from app.models.team import Team
        from app.models.chat import Message
        query = db.session.query(Team).join(Team.users).join(Team.messages).filter(User.id == self.id).order_by(Message.create_at.desc())
        return query

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

class Role(BaseModel, RoleMixin):
    __abstract__ = False
    __metaclass__ = db.Model
    level : Mapped[int] = db.Column(db.Integer, unique=False, nullable=False)
    name : Mapped[str_128] = db.Column(nullable=False, unique=True)
    description : Mapped[str_256]= db.Column(nullable=True)

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


class LoginSession(BaseModel):
    __abstract__ = False
    user_id : Mapped[uuid.UUID] = db.Column(db.ForeignKey('user.id'), nullable=False)
    location : Mapped[str_128]= db.Column(nullable=True)
    network_id : Mapped[uuid.UUID]= db.Column(db.ForeignKey('network.id'))
