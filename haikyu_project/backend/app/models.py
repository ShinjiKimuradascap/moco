from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
import datetime
from .database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    paid_wings = Column(Integer, default=0)
    free_wings = Column(Integer, default=0)
    gold = Column(Integer, default=0)
    mileage = Column(Integer, default=0)
    stamina = Column(Integer, default=100)
    last_stamina_update = Column(DateTime, default=datetime.datetime.utcnow)

    characters = relationship("Character", back_populates="owner")
    teams = relationship("Team", back_populates="owner")
    items = relationship("Item", back_populates="owner")

class Character(Base):
    __tablename__ = "characters"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    master_id = Column(Integer) # ID from master data JSON
    level = Column(Integer, default=1)
    exp = Column(Integer, default=0)
    star_rank = Column(Integer, default=1)
    shards = Column(Integer, default=0)

    owner = relationship("User", back_populates="characters")

class Team(Base):
    __tablename__ = "teams"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    name = Column(String)
    formation = Column(JSON) # JSON string to store position info

    owner = relationship("User", back_populates="teams")

class Item(Base):
    __tablename__ = "items"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    master_id = Column(Integer)
    quantity = Column(Integer, default=0)

    owner = relationship("User", back_populates="items")
