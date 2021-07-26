from app.db.client.client import MySQLConnection
from app.db.exceptions import UserNotFoundException, OperationalErrorException
from app.db.models.models import Base, User
from loguru import logger
from sqlalchemy import exc

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
            self.create_tables()
            # self.create_table_musical_compositions()

    def create_tables(self):
        if not self.engine.dialect.has_table(self.engine, 'users'):
            Base.metadata.tables['users'].create(self.engine)  # Создание таблицы из моделей если нет такой
        else:
            # pass
            self.mysql_connection.execute_query('DROP TABLE IF EXISTS users')  # Грохаем таблицу если такая есть
            Base.metadata.tables['users'].create(self.engine)
            logger.info('Table users deleted')

    # def create_table_musical_compositions(self):
    #    if not self.engine.dialect.has_table(self.engine, 'musical_compositions'):
    #        Base.metadata.tables['musical_compositions'].create(self.engine)  # Создание таблицы из моделей если нет такой
    #    else:
    #        self.mysql_connection.execute_query('DROP TABLE IF EXISTS musical_compositions')  # Грохаем таблицу если такая есть
    #        Base.metadata.tables['musical_compositions'].create(self.engine)

    def add_user(self, uuid, username, email, phone, gender, gender_search, balance, birthday):
        try:
            user = User(
                uuid=uuid,
                username=username,
                email=email,
                phone=phone,
                gender=gender,
                gender_search=gender_search,
                balance=balance,
                birthday=birthday
            )
            self.mysql_connection.session.add(user)
            return self.get_user_info(uuid)
        except exc.OperationalError as e:
            # Ошибки операций с БД пишем в лог и возвращаем 400 ошибку с пояснением.
            logger.error(e)
            raise OperationalErrorException('Bad request. Check types for parameters.')

    def check_username(self, username):
        user = self.mysql_connection.session.query(User).filter_by(username=username).first()
        if user:
            return True
        else:
            return False

    def check_uuid(self, uuid):
        try:
            uuid = self.mysql_connection.session.query(User).filter_by(uuid=uuid).first()
        except Exception as e:
            logger.error(f'exception: {e}')
            return 'UUID bad value'
        if uuid:
            #logger.info(f'uuid: {uuid}')
            return True
        else:
            return False

    def check_email(self, email):
        email = self.mysql_connection.session.query(User).filter_by(email=email).first()
        if email is not None:
            logger.info(f'email: {str(email)}')
            return True
        else:
            return False

    def check_phone(self, phone):
        email = self.mysql_connection.session.query(User).filter_by(phone=phone).first()
        if email:
            return True
        else:
            return False

    def get_user_info(self, uuid):
        # Находим пользователя в базе
        user = self.mysql_connection.session.query(User).filter_by(uuid=uuid).first()
        if user:
            self.mysql_connection.session.expire_all()
            return {'uuid': user.uuid, 'username': user.username, 'email': user.email, 'phone': user.phone,
                    'Gender': user.gender, 'gender_search': user.gender_search, 'balance': user.balance,
                    'birthday': user.birthday}
        else:
            raise UserNotFoundException('User not found')

    def edit_user_info(self, uuid, new_username=None, new_email=None, new_phone=None, new_gender=None, new_gender_search=None, new_balance=None, new_birthday=None):
        user = self.mysql_connection.session.query(User).filter_by(uuid=uuid).first()
        #logger.info(f'new_phone: {new_phone}')
        if user:
            if new_username is not None and new_username != '':
                user.username = new_username
            elif new_email is not None:
                user.email = new_email
            elif new_phone is not None:
                #logger.info(f'new_phone: {new_phone}')
                user.phone = new_phone
            elif new_gender is not None:
                user.gender = new_gender
            elif new_gender_search is not None:
                user.gender_search = new_gender_search
            elif new_balance is not None:
                user.balance = new_balance
            elif new_birthday is not None:
                user.birthday = new_birthday
            return self.get_user_info(uuid)
#            return self.get_user_info(username if new_username is None else new_username)
        else:
            raise UserNotFoundException('User not found')
