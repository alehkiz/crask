from typing import Optional
from flask import current_app as app
from flask_security.utils import hash_password, verify_password
from sqlalchemy import cast, extract, Date
from sqlalchemy.ext.hybrid import hybrid_property
from datetime import date, datetime, timedelta
from flask_security.models import fsqla_v3 as fsqla
from flask_security import UserMixin, RoleMixin
from flask_sqlalchemy import BaseQuery
from sqlalchemy.orm import mapped_column, Mapped
import uuid
from sqlalchemy.dialects.postgresql import UUID

from app.core.db import db
from app.utils.kernel import validate_password
from app.utils.datetime import format_elapsed_time
from app.models.base import BaseModel, str_32, str_512, str_128, str_256, BaseRole
from datetime import datetime
from typing import List
from sqlalchemy.schema import Sequence


roles_users = db.Table(
    "roles_users",
    db.Column("user_id", UUID(as_uuid=True), db.ForeignKey("user.id")),
    db.Column("role_id", UUID(as_uuid=True), db.ForeignKey("role.id")),
)

# services_users = db.Table('services_users',
#                             db.mapped_column('user_id', UUID(as_uuid=True), db.ForeignKey('user.id')),
#                             db.mapped_column('service_id', UUID(as_uuid=True), db.ForeignKey('service.id')))
group_services_users = db.Table(
    "group_services_users",
    db.Column("user_id", UUID(as_uuid=True), db.ForeignKey("user.id")),
    db.Column(
        "group_service_id", UUID(as_uuid=True), db.ForeignKey("group_service.id")
    ),
)


class User(BaseModel, UserMixin):
    __abstract__ = False
    username: Mapped[str_32] = db.mapped_column(index=True, unique=True)
    name: Mapped[str_512] = db.mapped_column(index=True)
    email: Mapped[str_128] = db.mapped_column(db.String(128), index=True, unique=True)
    _password: Mapped[str_512]
    temp_password: Mapped[bool] = db.mapped_column(nullable=False, default=True)
    about_me: Mapped[Optional[str_512]]
    last_seen: Mapped[datetime] = db.mapped_column(
        db.DateTime(timezone=True), default=datetime.utcnow()
    )
    location: Mapped[Optional[str_128]]
    active: Mapped[bool] = db.mapped_column(db.Boolean, default=False)
    created_network_id: Mapped[uuid.UUID] = db.mapped_column(
        db.ForeignKey("network.id")
    )
    confirmed_network_id: Mapped[uuid.UUID] = db.mapped_column(
        db.ForeignKey("network.id")
    )
    confirmed_at: Mapped[Optional[datetime]]
    login_count: Mapped[Optional[int]] = db.mapped_column(default=0)
    # session_token = db.mapped_column(db.String(256), index=True)
    current_login_network_id: Mapped[Optional[uuid.UUID]] = db.mapped_column(
        db.ForeignKey("network.id")
    )
    fs_uniquifier: Mapped[str_256] = db.mapped_column(unique=True, default=uuid.uuid4)

    roles: Mapped[List["Role"]] = db.relationship(
        secondary=roles_users,
        backref=db.backref("users", lazy="dynamic"),
        lazy="dynamic",
    )
    sessions: Mapped[List["LoginSession"]] = db.relationship(
        backref="user",
        lazy="dynamic",
        order_by="LoginSession.create_at.desc()",
    )
    sended_messages: Mapped[List["Message"]] = db.relationship(
        backref=db.backref("sender"),
        lazy="dynamic",
        foreign_keys="[Message.user_sender_id]",
    )
    received_messages: Mapped[List["Message"]] = db.relationship(
        backref=db.backref("receiver"),
        lazy="dynamic",
        foreign_keys="[Message.user_destiny_id]",
    )
    # current_login_network = db.relationship('Network', backref=db.backref('current_user_login'), lazy='dynamic', foreign_keys='[User.current_login_network_id]')
    tickets: Mapped[List["Ticket"]] = db.relationship(
        secondary="ticket_stage_event", back_populates="users", lazy="dynamic"
    )
    tickets_stage_event: Mapped[List["TicketStageEvent"]] = db.relationship(
        back_populates="user", viewonly=True
    )
    # writed_comments = db.relationship("Comment", back_populates="writer", foreign_keys='[Comment.user_id]')
    comments_writed: Mapped[List["Comment"]] = db.relationship(
        backref="author", primaryjoin="user.c.id == comment.c.user_id"
    )

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
                app.logger.error(app.config.get("_ERRORS").get("DB_COMMIT_ERROR"))
                app.logger.error(e)
                raise Exception("Não foi possível salvar o IP")
        self.current_login_network_id = network.id
        try:
            db.session.commit()
        except Exception as e:
            app.logger.error(app.config.get("_ERRORS").get("DB_COMMIT_ERROR"))
            app.logger.error(e)
            raise Exception("Não foi possível salvar o IP")

    @hybrid_property
    def password(self):
        return self._password

    @password.setter
    def password(self, password):
        _validate_password = validate_password(password)
        if _validate_password["ok"]:
            self._password = hash_password(password)
        else:
            raise ValueError("Não foi possível validar a senha")

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
        return "Sim" if self.active else "Não"

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
        return f"<User {self.username}>"

    ####### QUERIES ##############

    def tickets_datetime_deadline(self, dt: Optional[datetime] = None) -> BaseQuery:
        from app.models.ticket import TicketStageEvent

        if dt is None:
            dt = (datetime.now() + timedelta(days=30))
        return (
            db.session.query(TicketStageEvent)
            .filter(
                TicketStageEvent.deadline < dt
            ).order_by(TicketStageEvent.deadline.desc())
        )

    def tickets_delay_from_now(self) -> BaseQuery:
        from app.models.ticket import TicketStageEvent

        dt = datetime.now()
        return self.tickets_datetime_deadline(dt)

    @property
    def unreaded_messages(self):
        from app.models.chat import Message

        total_messages = (
            db.session.query(db.func.count(Message.id).label("cnt"))
            .join(User.received_messages)
            .filter(User.id == self.id)
            .subquery()
        )

        read_msg = (
            db.session.query(db.func.count(Message.id).label("cnt"))
            .join(User.readed_messages)
            .filter(User.id == self.id)
            .subquery()
        )
        count_unread = db.session.query(total_messages.c.cnt - read_msg.c.cnt).scalar()
        return count_unread

    @property
    def teams_ordered_by_last_message(self):
        from app.models.team import Team
        from app.models.chat import Message

        query = (
            db.session.query(Team)
            .join(Team.users)
            .join(Team.messages)
            .filter(User.id == self.id)
            .order_by(Message.create_at.desc())
        )
        return query

    @staticmethod
    def query_by_month_year(year: int, month: int):
        return User.query.filter(
            extract("year", User.created_at) == year,
            extract("month", User.created_at) == month,
        )

    @staticmethod
    def query_by_year(year: int):
        return User.query.filter(extract("year", User.created_at) == year)

    @staticmethod
    def query_by_date(date: date):
        return User.query.filter(cast(User.created_at, Date) == date)

    @staticmethod
    def query_by_interval(start: date, end: date):
        return User.query.filter(
            cast(User.created_at, Date) == start, cast(User.created_at, Date) == end
        )


class Role(BaseModel, RoleMixin):
    __abstract__ = False
    __metaclass__ = db.Model
    name: Mapped[BaseRole] = db.mapped_column(unique=False, nullable=False)
    level: Mapped[int] = db.mapped_column(
        Sequence("role_level_seq", start=1, increment=1),
        unique=True,
        autoincrement=True,
    )
    description: Mapped[Optional[str_256]]

    @property
    def is_admin(self):
        if self.level == BaseRole.ADMIN:
            return True
        return False

    @property
    def is_manager_user(self):
        if self.level == BaseRole.MANAGER_USER:
            return True
        return False

    @property
    def is_support(self):
        if self.level in BaseRole.SUPPORT:
            return True
        return False

    @property
    def has_support(self):
        if self.level in [BaseRole.SUPPORT, BaseRole.MANAGER_USER, BaseRole.ADMIN]:
            return True
        return False

    def __repr__(self):
        return f"<Role {self.name.name}>"


class LoginSession(BaseModel):
    __abstract__ = False
    user_id: Mapped[uuid.UUID] = db.mapped_column(
        db.ForeignKey("user.id"), nullable=False
    )
    location: Mapped[str_128] = db.mapped_column(nullable=True)
    network_id: Mapped[uuid.UUID] = db.mapped_column(db.ForeignKey("network.id"))
