from app.core.db import db
from app.models.base import BaseModel,str_128, str_10, str_256, str_64
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.hybrid import hybrid_property
from typing import Optional
from sqlalchemy.orm import mapped_column, Mapped
import uuid

from app.utils.kernel import only_numbers



class Address(BaseModel):
    __abstract__ = False
    name : Mapped[str_128] = db.Column( index=True, nullable=False, unique=False)#CEP
    postcode_id : Mapped[uuid.UUID] = db.Column(db.ForeignKey('address_postcode.id'), nullable=False)
    address_type_id : Mapped[uuid.UUID] = db.Column(db.ForeignKey('address_type.id'), nullable=False)#rua, avenida, estrada
    _number : Mapped[int] = db.Column(nullable=True, default=0)
    city_id : Mapped[uuid.UUID] = db.Column(db.ForeignKey('city.id'), nullable=False)

    costumers = db.relationship('Costumer', backref='address', lazy='dynamic')

    @hybrid_property
    def number(self) -> Optional[int]:
        if self._number == 0:
            return None
        return self._number
    
    @number.setter
    def number(self, value:int) -> None:
        self._number = value

class AddressPostcode(BaseModel):
    __abstract__ = False
    _code : Mapped[str_10] = db.Column(index=True, nullable=False, unique=True)#CEP
    adresses = db.relationship('Address', backref='code', lazy='dynamic')

    @hybrid_property
    def code(self):
        self._code

    @code.setter
    def code(self, value: str) -> None:
        match len(value):
            case 9:
                self._code = only_numbers(value)
            case 8:
                self._code = only_numbers(value)
            case _:
                raise Exception('Houve um erro em atribuir `postcode`')



class AddressType(BaseModel):
    __abstract__ = False
    type : Mapped[str] = db.Column(db.String(32), index=True, nullable=False, unique=True)
    adresses = db.relationship('Address', backref='type', lazy='dynamic')

class City(BaseModel):
    __abstract__ = False
    city : Mapped[str_256] = db.Column(db.String(256), index=True, nullable=False, unique=False)
    uf_id : Mapped[uuid.UUID] = db.Column(UUID(as_uuid=True), db.ForeignKey('state_location.id'), nullable=False)#rua, avenida, estrada
    adresses = db.relationship('Address', backref='city', lazy='dynamic')

class StateLocation(BaseModel):
    __abstract__ = False
    state : Mapped[str_64] = db.Column(index=True, nullable=False, unique=True)
    uf : Mapped[str] = db.Column(index=True, nullable=False, unique=True)
    cities = db.relationship('City', backref='state', lazy='dynamic')