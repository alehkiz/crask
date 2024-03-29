from typing import List, Optional
from app.models.security import User
from app.core.db import db
from app.models.base import BaseModel
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.hybrid import hybrid_property
from datetime import datetime
from sqlalchemy.orm import mapped_column, Mapped
import uuid

# group_users = db.Table(
#     "group_users",
#     db.mapped_column("user_id", UUID(as_uuid=True), db.ForeignKey("user.id")),
#     db.mapped_column("group_id", UUID(as_uuid=True), db.ForeignKey("chat_chat.id")),
#     db.mapped_column("joined_at", db.DateTime(timezone=True), default=datetime.utcnow),
# )

readed_messages = db.Table(
    "readed_messages",
    db.Column("user_id", UUID(as_uuid=True), db.ForeignKey("user.id")),
    db.Column("message_id", UUID(as_uuid=True), db.ForeignKey("message.id")),
    db.Column("readed_at", db.DateTime(timezone=True), default=datetime.utcnow),
)


class Message(BaseModel):
    __abstract__ = False
    message: Mapped[str] = mapped_column(db.Text)
    user_sender_id: Mapped[uuid.UUID] = mapped_column( db.ForeignKey("user.id"))
    user_destiny_id: Mapped[Optional[uuid.UUID]] = mapped_column(db.ForeignKey("user.id"))
    create_network_id: Mapped[uuid.UUID] = mapped_column(db.ForeignKey("network.id"))
    readed: Mapped[bool] = mapped_column(default=False)
    # _private: Mapped[bool] = mapped_column(default=False)
    message_id: Mapped[Optional[uuid.UUID]] = mapped_column(db.ForeignKey("message.id"))
    team_id: Mapped[Optional[uuid.UUID]] = mapped_column(db.ForeignKey("team.id"))
    replies_to : Mapped[List['Message']] = db.relationship(
        remote_side="Message.id",
        primaryjoin=("message.c.id==message.c.message_id"),
        backref=db.backref(
            "answers"
        ),  # lazy='dynamic' #TODO:Create a way to relationhip is lazy to query `answers`
    )
    users_readed : Mapped[List['User']] = db.relationship(
        secondary=readed_messages,
        primaryjoin=("readed_messages.c.message_id==message.c.id"),
        secondaryjoin=(readed_messages.c.user_id == User.id),
        backref=db.backref("readed_messages", lazy="dynamic"),
        lazy="dynamic",  # TODO:Create a way to relationhip is lazy to query `answers`
    )

    @hybrid_property
    def private(self) -> bool:
        return self._private

    @private.setter
    def private(self, value) -> None:
        raise Exception(
            "Não é possível setar a mensagem como privada, informe o usuário de destino para isso"
        )

    def user_can_read(self, user: User) -> bool:
        if self.team in user.teams:
            return True
        if self.sender == user:
            return True
        return False


# class GroupChat(BaseModel):
#     __abstract__ = False
#     name = db.mapped_column(db.String(100), nullable=False, unique=True)
#     users = db.relationship(
#         "User",
#         secondary=group_users,
#         backref=db.backref(
#             "groups", lazy="dynamic", order_by="desc(group_users.c.joined_at)"
#         ),
#         lazy="dynamic",
#         order_by="desc(group_users.c.joined_at)",
#     )
#     messages = db.relationship('Message', backref='group', lazy='dynamic')
