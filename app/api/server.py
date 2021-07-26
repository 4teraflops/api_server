import threading
import requests
import argparse
from flask import Flask, request, jsonify
from werkzeug.exceptions import abort
from pymysql.err import IntegrityError
from flask_httpauth import HTTPBasicAuth
from app.api.utils import config_parser
from app.db.exceptions import UserNotFoundException, OperationalErrorException
from app.db.interaction.interaction import DBInteraction
from werkzeug.security import generate_password_hash, check_password_hash
import sys

from loguru import logger

logger.add(f'log/{__name__}.log', format='{time} {level} {message}', level='DEBUG', rotation='10 MB', compression='zip')

# поднимаем парсер конфига
parser = argparse.ArgumentParser()
parser.add_argument('--config', type=str, dest='config')
args = parser.parse_args()
config = config_parser(args.config)
# Вытаскиваем разрешенных пользователей
auth = HTTPBasicAuth()
basic_password = config['BASIC_PASSWORD']
allow_api_users = {"admin": generate_password_hash(f"{basic_password}")}


class Server:

    def __init__(self, host, port, db_host, db_port, user, password, db_name, rebuild_db=True):
        self.host = host
        self.port = port

        self.db_interaction = DBInteraction(
            host=db_host,
            port=db_port,
            user=user,
            password=password,
            db_name=db_name,
            rebuild_db=rebuild_db  # Это чтоб каждый раз работать с чистой базой
        )

        self.app = Flask(__name__)

#        self.app.add_url_rule('/shutdown', view_func=self.shutdown)
        self.app.add_url_rule('/', view_func=self.get_home)
        self.app.add_url_rule('/home', view_func=self.get_home)
        self.app.add_url_rule('/add_user', view_func=self.add_user, methods=['POST'])
        self.app.add_url_rule('/get_user_info/<uuid>', view_func=self.get_user_info)
        self.app.add_url_rule('/edit_user_info/<uuid>', view_func=self.edit_user_info, methods=['POST'])

        self.app.register_error_handler(404, self.page_not_found)

    @auth.verify_password
    def verify_password(username, password):
        if username in allow_api_users and \
                check_password_hash(allow_api_users.get(username), password):
            return username

    def page_not_found(self, error_description):  # Кастомная ошибка 404
        return jsonify(error=str(error_description)), 404

    def runserver(self):
        self.server = threading.Thread(target=self.app.run, kwargs={'host': self.host, 'port': self.port})
        self.server.start()
        return self.server

#    def shutdown_server_from_function(self):
#        request.get(f'http://{self.host}:{self.port}/shutdown')

#    @auth.login_required
#    def shutdown(self):
#        terminate_func = request.environ.get('werkzeug.server.shutdown')
#        if terminate_func:
#            terminate_func()
#            return 'Success', 200

    @auth.login_required
    def get_home(self):
        return 'Hello from api server!'

    @auth.login_required
    def add_user(self):
        request_body = dict(request.json)  # Берем тело из запроса
        if request_body is None:
            return 'request body is null', 400

        # Try и except на случай, если какие-то необязательные параметры не были переданы
        try:
            uuid = request_body['uuid']
            if uuid == '':
                return 'UUID can not be null', 400
            if uuid is not None:
                check_uuid = self.db_interaction.check_uuid(uuid)
                if check_uuid == 'UUID bad value':
                    #logger.error(f'check_uuid" {check_uuid}')
                    return 'UUID Type error', 400
                elif check_uuid is True:
                    return 'UUID already used', 400
                #logger.info(f'uuid: {uuid}, uuid type: {type(uuid)}')
                #logger.info(f'uuid bytes_size: {sys.getsizeof(uuid)}')
        except KeyError:
            return 'UUID id can be null', 400

        try:
            username = request_body['username']
            if username == '':
                username = None
            if username is not None:
                check_username = self.db_interaction.check_username(username)
                if check_username is True:
                    return f'username already used', 400
        except KeyError:
            username = None

        try:
            email = request_body['email']
            if email == '':
                email = None
            #logger.info(f'email: {email}')
            if email is not None:
                check_email = self.db_interaction.check_email(email)
                if check_email is True:
                    return f'Email already used', 400
        except KeyError:
            email = None

        try:
            phone = request_body['phone']
            if phone == '':
                phone = None
            if phone is not None:
                check_phone = self.db_interaction.check_phone(phone)
                if check_phone is True:
                    return 'Phone already used', 400
        except KeyError:
            phone = None

        try:
            gender = request_body['gender']
            if gender == '':
                return 'gender can not be null', 400
        except KeyError:
            return 'gender can not be null', 400

        try:
            gender_search = request_body['gender_search']
            if gender_search == '':
                return 'gender_search can not be null', 400
        except KeyError:
            return 'gender_search can not be null', 400

        try:
            balance = request_body['balance']
            if balance == '':
                balance = 0
        except KeyError:
            balance = 0

        try:
            birthday = request_body['birthday']
            if birthday == '':
                return 'birthday can not be null', 400
        except KeyError:
            return 'birthday can not be null', 400

        # Валидируем параметры на соответствие требованиям sql
        # Необязательные параметры
        if username is not None and email is not None and phone is not None:
            if len(username) > 50:
                return f'username is more than 50 characters ', 400
            elif len(email) > 40:
                return f'email is more 40 characters', 400
            elif len(phone) > 20:
                return 'phone is more 20 characters', 400

        #logger.info(f'check_username" {check_username}')
        #logger.info(f'check_email: {check_email}')
        #if sys.getsizeof(uuid) != 16:
        #    return f'UUID must be 16 bytes string. Not {sys.getsizeof(uuid)}.'

        try:
            self.db_interaction.add_user(
                uuid=uuid,
                username=username,
                email=email,
                phone=phone,
                gender=gender,
                gender_search=gender_search,
                balance=balance,
                birthday=birthday
            )
            # Берем из БД объект user и возвращаем на запрос.
            user = self.db_interaction.get_user_info(uuid)
            return f'Success added User: {user}', 201  # Вместе с http status code
        except OperationalErrorException:
            abort(400, description='Bad request. Check types for parameters.')

    @auth.login_required
    def get_user_info(self, uuid):
        try:
            #logger.info(f'username" {username}')
            # Проверка UUID на наличие в базе
            check_uuid = self.db_interaction.check_uuid(uuid)
            # Возможно под это надо свой exception сделать
            if check_uuid is False:
                abort(404, description='User not found')

            # Валидация
            elif type(uuid) != str:
                return f'Parameter UUID must be a string', 400
            user_info = self.db_interaction.get_user_info(uuid)
            return user_info
        except UserNotFoundException:
            abort(404, description='User not found')

    @auth.login_required
    def edit_user_info(self, uuid):
        # проверим есть ли такой username в базе
        check_uuid = self.db_interaction.check_uuid(uuid)
        #logger.info(f'check_uuid: {check_uuid}')
        if check_uuid is False:
            abort(404, description=f'UUID {uuid} not found')
        try:
            request_body = dict(request.json)  # Берем тело из запроса
        except TypeError:
            return 'Bad request body', 400

        try:
            new_username = request_body['new_username']
            # сначала проверим на уникальность
            check = self.db_interaction.check_username(new_username)
            if check is True:
                return f'new_username already used', 400
            elif len(new_username) > 50:
                return 'username cannot be more than 50 characters', 400
            elif type(new_username) is not str:
                return 'type parameter new_username must be a string', 400
        except KeyError:
            new_username = None
            #logger.info(f'new_username: {new_username}')

        try:
            new_email = request_body['new_email']
            check = self.db_interaction.check_email(new_email)
            if check is True:
                return 'new_email already used', 400
            elif len(new_email) > 20:
                return 'new_email cannot be more than 20 characters', 400
            elif type(new_email) is not str:
                return 'type parameter new_email must be a string', 400
        except KeyError:
            new_email = None

        try:
            new_phone = request_body['new_phone']
            #logger.info(f'new_phone: {new_phone}')
            check_phone = self.db_interaction.check_phone(new_phone)
            if check_phone is True:
                return 'new_phone already used', 400
            elif len(new_phone) > 20:
                return 'new_phone cannot be more than 20 characters', 400
            elif type(new_phone) is not str:
                return 'type new_phone must be a string', 400
        except KeyError:
            new_phone = None

        try:
            new_gender = request_body['new_gender']
            if len(new_gender) > 10:
                return 'new_gender cannot be more than 10 characters'
            elif type(new_gender) != str:
                return 'new_gender must be a string', 400
        except KeyError:
            new_gender = None

        try:
            new_gender_search = request_body['new_gender_search']
            if len(new_gender_search) > 10:
                return 'new_gender_search cannot be more than 10 characters'
            elif type(new_gender_search) != str:
                return 'new_gender_search must be a string', 400
        except KeyError:
            new_gender_search = None

        try:
            new_balance = request_body['new_balance']
            if type(new_balance) != int:
                return 'new_gender_search must be a integer', 400
        except KeyError:
            new_balance = None

        try:
            new_birthday = request_body['new_birthday']
        except KeyError:
            new_birthday = None

        self.db_interaction.edit_user_info(
            uuid=uuid,
            new_username=new_username,
            new_email=new_email,
            new_phone=new_phone,
            new_gender=new_gender,
            new_gender_search=new_gender_search,
            new_balance=new_balance,
            new_birthday=new_birthday
        )
        new_user_info = self.get_user_info(uuid)
        return f'Success edit user info: {new_user_info}', 200


if __name__ == '__main__':

    server_host = config['SERVER_HOST']
    server_port = config['SERVER_PORT']
    db_host = config['DB_HOST']
    db_port = config['DB_PORT']
    db_user = config['DB_USER']
    db_password = config['DB_PASSWORD']
    db_name = config['DB_NAME']

    server = Server(
        host=server_host,
        port=server_port,
        db_port=db_port,
        db_host=db_host,
        user=db_user,
        password=db_password,
        db_name=db_name
    )
    server.runserver()
