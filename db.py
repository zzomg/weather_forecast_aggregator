from settings import DB_NAME, DB_HOST, DB_PORT, DB_USER, DB_USER_PASS

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import Column, Integer, String, Float, ForeignKey
from sqlalchemy.orm import relationship

engine = create_engine(f'postgresql+psycopg2://{DB_USER}:{DB_USER_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}', echo=True)
Base = declarative_base()


class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, autoincrement=True)
    tg_id = Column(Integer, unique=True)
    latitude = Column(Float)
    longitude = Column(Float)
    days_num = Column(Integer)
    state = Column(Integer)

    def __repr__(self):
        return f"<User(id={self.id}, tg_id={self.tg_id}, " \
               f"latitude={self.latitude}, longitude={self.longitude}, " \
               f"days_num={self.days_num}, state={self.state})>"


class Service(Base):
    __tablename__ = 'services'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, unique=True)

    def __repr__(self):
        return f"<Service(id={self.id}, name={self.name})>"


class UserService(Base):
    __tablename__ = 'user_services'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    service_id = Column(Integer, ForeignKey('services.id'))

    user = relationship("User", back_populates="user_services")
    service = relationship("Service", back_populates="service_users")

    def __repr__(self):
        return f"<UserService(id={self.id}, user={self.user}, service={self.service})>"


User.user_services = relationship("UserService", order_by=UserService.id, back_populates="user")
Service.service_users = relationship("UserService", order_by=UserService.id, back_populates="service")

Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)
session = Session()
