from sqlalchemy import Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class Channels(Base):
    __tablename__ = 'channels'

    id = Column(Integer, primary_key=True)
    SlackId = Column(String)
    AccountId = Column(String)
    label = Column(String)

class Users(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    SlackId = Column(String)
    ContactId = Column(String)
    SalesforceUserId = Column(String)