from sqlalchemy import Column, Integer, ForeignKey, VARCHAR, UniqueConstraint, INT, SMALLINT, DATE
from sqlalchemy.ext.declarative import declarative_base  # База объектов, из которой будем импортировать все наши модели
from sqlalchemy.orm import relationship
from sqlalchemy_utils import UUIDType
import uuid

Base = declarative_base()

"""Описание таблиц"""


class User(Base):
    __tablename__ = 'users'

    uuid = Column(UUIDType(binary=False), primary_key=True)
    username = Column(VARCHAR(50), nullable=True, default=None)
    email = Column(VARCHAR(40), nullable=True, default=None)
    phone = Column(VARCHAR(20), nullable=True, default=None)
    gender = Column(VARCHAR(10), nullable=False)
    gender_search = Column(VARCHAR(10), nullable=False)
    balance = Column(INT, default=0, nullable=False)
    birthday = Column(DATE, nullable=False)

    UniqueConstraint(uuid, name='uuid')
    UniqueConstraint(email, name='email')
    UniqueConstraint(phone, name='phone')

# class MusicalComposition(Base):
#    __tablename__ = 'musical_compositions'
#
#    id = Column(Integer, primary_key=True, autoincrement=True, nullable=False)
#
#    # В kwargs в качестве переменных указано на какое поле бдуем ссылаться
#    # Переменными указано на случай, если имя таблицы будет меняться
#    user_id = Column(Integer, ForeignKey(f'{User.__tablename__}.{User.id.name}'), nullable=False)
#
#    url = Column(VARCHAR(60), nullable=True)
#
#    # Обратная ссылка, чтоб получить весь список композиций, которые относятся к пользователю
#    user = relationship('User', backref='musical_composition')
