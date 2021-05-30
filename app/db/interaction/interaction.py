from app.db.client.client import MySQLConnection
from app.db.exceptions import UserNotFoundException
from app.db.models.models import Base, User
from loguru import logger

logger.add(f'log/{__name__}.log', format='{time} {level} {message}', level='DEBUG', rotation='10 MB', compression='zip')


class DBInteraction:

    def __init__(self, host, port, user, password, db_name, rebuild_db=False):
        self.mysql_connection = MySQLConnection(
            host=host,
            port=port,
            user=user,
            password=password,
            db_name=db_name,
            rebuild_db=rebuild_db
        )

        self.engine = self.mysql_connection.connection.engine

        if rebuild_db:
            self.create_table_users()
            #self.create_table_musical_compositions()

    def create_table_users(self):
        if not self.engine.dialect.has_table(self.engine, 'users'):
            Base.metadata.tables['users'].create(self.engine)  # Создание таблицы из моделей если нет такой
        else:
            #pass
            self.mysql_connection.execute_query('DROP TABLE IF EXISTS users')  # Грохаем таблицу если такая есть
            Base.metadata.tables['users'].create(self.engine)
            logger.info('Table users deleted')

    #def create_table_musical_compositions(self):
    #    if not self.engine.dialect.has_table(self.engine, 'musical_compositions'):
    #        Base.metadata.tables['musical_compositions'].create(self.engine)  # Создание таблицы из моделей если нет такой
    #    else:
    #        self.mysql_connection.execute_query('DROP TABLE IF EXISTS musical_compositions')  # Грохаем таблицу если такая есть
    #        Base.metadata.tables['musical_compositions'].create(self.engine)

    def add_user(self, username, email, password, phone, gender, gender_search, balance, age):
        user = User(
            username=username,
            email=email,
            password=password,
            phone=phone,
            gender=gender,
            gender_search=gender_search,
            balance=balance,
            age=age
        )
        self.mysql_connection.session.add(user)
        return self.get_user_info(username)

    def check_username(self, username):
        user = self.mysql_connection.session.query(User).filter_by(username=username).first()
        if user:
            return True
        else:
            return False

    def check_email(self, email):
        email = self.mysql_connection.session.query(User).filter_by(email=email).first()
        if email:
            return True
        else:
            return False

    def check_phone(self, phone):
        email = self.mysql_connection.session.query(User).filter_by(phone=phone).first()
        if email:
            return True
        else:
            return False

    def get_user_info(self, username):
        # Находим пользователя в базе
        user = self.mysql_connection.session.query(User).filter_by(username=username).first()
        if user:
            self.mysql_connection.session.expire_all()
            return {'uuid': user.uuid, 'username': user.username, 'email': user.email, 'password': user.password, 'Phone': user.phone, 'Gender': user.gender, 'gender_search': user.gender_search, 'balance': user.balance, 'age': user.age}
        else:
            raise UserNotFoundException('User not found')

    def edit_user_info(self, username, new_username=None, new_email=None, new_password=None, new_phone=None):  # Последние 3 переменные установлены по-умолчанию None
        user = self.mysql_connection.session.query(User).filter_by(username=username).first()
        if user:
            if new_username is not None:
                user.username = new_username
            elif new_email is not None:
                user.email = new_email
            elif new_password is not None:
                user.password = new_password
            elif new_phone is not None:
                user.phone = new_phone
            return self.get_user_info(username if new_username is None else new_username)
        else:
            raise UserNotFoundException('User not found')
