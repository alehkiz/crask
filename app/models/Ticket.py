from datetime import datetime
from app.core.db import db
from app.models.base import BaseModel
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.hybrid import hybrid_property
from app.utils.datetime import format_elapsed_time
from sqlalchemy.ext.associationproxy import association_proxy
from sqlalchemy import event


class Ticket(BaseModel):
    __abstract__ = False
    name = db.Column(db.String(512), index=True, nullable=False)
    title = db.Column(db.String(512), index=True, nullable=False)
    info = db.Column(db.String(5000), index=True, nullable=False)
    _closed = db.Column(db.Boolean)
    deadline = db.Column(db.DateTime(timezone=True), nullable=False)
    _closed_at = db.Column(db.DateTime(timezone=True), nullable=True)
    type_id = db.Column(UUID(as_uuid=True), db.ForeignKey('ticket_type.id'), nullable=False)
    create_network_id = db.Column(UUID(as_uuid=True), db.ForeignKey('network.id'), nullable=False)
    create_user_id = db.Column(UUID(as_uuid=True), db.ForeignKey('user.id'), nullable=False)
    costumer_id = db.Column(UUID(as_uuid=True), db.ForeignKey('costumer.id'), nullable=True)#Cidadão pode ficar vazio
    service_id = db.Column(UUID(as_uuid=True), db.ForeignKey('service.id'), nullable=False)
    comments = db.relationship('Comment', backref='ticket', lazy='dynamic')
    costumer = db.relationship('Costumer', backref='tickets', uselist=False)
    stage_event = db.relationship('TicketStageEvent',
                            primaryjoin='ticket_stage_event.c.ticket_id==ticket.c.id',
                            backref=db.backref('ticket', overlaps="tickets,users"),
                            lazy='dynamic',
                            overlaps="tickets,users")
    users = db.relationship('User', secondary='ticket_stage_event', 
                primaryjoin=('ticket_stage_event.c.ticket_id==ticket.c.id'),
                secondaryjoin=('ticket_stage_event.c.user_id==user.c.id'),
                backref=db.backref('tickets', lazy='dynamic'), 
                lazy='dynamic'
                )
    stages =  association_proxy('stage_event', 'stage')



    # user_tickets = db.relationship('UserTicket',
    #                 primaryjoin=('user_ticket.c.ticket_id==ticket.c.id'),
    #                 backref=db.backref('tickets'),
    #                 lazy='dynamic'
    #                 )
    # stages = db.relationship('TicketStageEvent',# secondary='ticket_stage_event', 
    #             primaryjoin=('and_(ticket_stage_event.c.user_id==user.c.id, ticket_stage_event.c.ticket_id==ticket.c.id)'),
    #             # secondary=('join(UserTicket, UserTicket.ticket_id == Ticket.id)'),
    #             # secondaryjoin='and_(user_ticket.c.user_id == user.c.id, user_ticket.c.ticket_id== ticket.c.id)',
    #             # secondaryjoin='ticket_stage_event.c.user_id == user.c.id',
    #             backref=db.backref('tickets_stages', lazy='dynamic'),
    #             #viewonly=True,
    #             lazy='dynamic')

    @property
    def current_user(self):
        # from app.models.security import User
        if self.current_stage_event != None:
            return self.current_stage_event.user
        return None

    @property
    def current_stage(self):
        if self.current_stage != None:
            return self.current_stage_event.stage
        return None
    
    @property
    def current_stage_event(self):
        return db.session.query(TicketStageEvent)\
            .filter(TicketStageEvent.ticket_id == self.id)\
                .order_by(TicketStageEvent.create_at.desc()).limit(1).first()

    @hybrid_property
    def closed(self):
        return self.closed
    
    @closed.setter
    def closed(self, value):
        match value:
            case True:
                self._closed = True
                self.closed_at = datetime.utcnow()
            case False:
                self._closed = False
        
    @property
    def is_closed(self):
        if self._closed is True:
            return True
        else:
            return False

    @hybrid_property
    def closed_at(self):
        return self.closed_at
    
    @closed.setter
    def closed_at(self, value):
        raise Exception('Não é possível incluir ou alterar a data do fechamento por closed_at, altere o atributo closed')

    @property
    def closed_at_elapsed(self):
        return format_elapsed_time(self.closed_at)

    @property
    def deadline_elapsed(self):
        return format_elapsed_time(self.deadline)

        

class TicketType(BaseModel):
    __abstract__ = False
    type = db.Column(db.String(512), index=True, nullable=False, unique=True)
    tickets = db.relationship('Ticket', backref='type', lazy='dynamic', single_parent=True)


class TicketStage(BaseModel):
    __abstract__ = False
    name = db.Column(db.String(28), index=True, nullable=False, unique=True)
    level = db.Column(db.Integer, nullable=False, unique=True)

class TicketStageEvent(BaseModel):
    __abstract__ = False
    ticket_stage_id = db.Column(UUID(as_uuid=True), db.ForeignKey('ticket_stage.id'), nullable=False)
    user_id = db.Column(UUID(as_uuid=True), db.ForeignKey('user.id'), nullable=False)
    ticket_id = db.Column(UUID(as_uuid=True), db.ForeignKey('ticket.id'), nullable=False)
    info = db.Column(db.Text)
    user = db.relationship('User', backref=db.backref('user_stage', overlaps="tickets,users"), overlaps="tickets,users")
    stage = db.relationship('TicketStage', backref='events')
    user_name = association_proxy('user', 'name')
    stage_name = association_proxy('stage', 'name')
    stage_level = association_proxy('stage', 'level')
    
    def __init__(self, ticket_stage_id, user_id, ticket_id, info) -> None:
        self.ticket_stage_id = ticket_stage_id
        self.user_id = user_id
        self.ticket_id = ticket_id
        self.info = info


        


# @event.listens_for(TicketStage.collection, 'append', propagate=True)
# def my_append_listener(target, value, initiator):
#     print("received append event for target: %s" % target)
