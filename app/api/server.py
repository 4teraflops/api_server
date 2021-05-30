import threading
import requests
import argparse
from flask import Flask, request, jsonify
from werkzeug.exceptions import abort
from pymysql.err import IntegrityError
from flask_httpauth import HTTPBasicAuth
from app.api.utils import config_parser
from app.db.exceptions import UserNotFoundException
from app.db.interaction.interaction import DBInteraction
from werkzeug.security import generate_password_hash, check_password_hash

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
users = {"admin": generate_password_hash(f"{basic_password}")}


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
            rebuild_db=rebuild_db  # Это чтоб каждый раз работать с чистой базой (отключено)
        )

        self.app = Flask(__name__)

        self.app.add_url_rule('/shutdown', view_func=self.shutdown)
        self.app.add_url_rule('/', view_func=self.get_home)
        self.app.add_url_rule('/home', view_func=self.get_home)
        self.app.add_url_rule('/add_user', view_func=self.add_user, methods=['POST'])
        self.app.add_url_rule('/get_user_info/<username>', view_func=self.get_user_info)
        self.app.add_url_rule('/edit_user_info/<username>', view_func=self.edit_user_info, methods=['POST'])

        self.app.register_error_handler(404, self.page_not_found)

    @auth.verify_password
    def verify_password(username, password):
        if username in users and \
                check_password_hash(users.get(username), password):
            return username

    def page_not_found(self, error_description):  # Кастомная ошибка 404
        return jsonify(error=str(error_description)), 404

    def runserver(self):
        self.server = threading.Thread(target=self.app.run, kwargs={'host': self.host, 'port': self.port})
        self.server.start()
        return self.server

    def shutdown_server_from_function(self):
        request.get(f'http://{self.host}:{self.port}/shutdown')

    @auth.login_required
    def shutdown(self):
        terminate_func = request.environ.get('werkzeug.server.shutdown')
        if terminate_func:
            terminate_func()
            return 'Success', 200

    @auth.login_required
    def get_home(self):
        return 'Hello it api server!'

    @auth.login_required
    def add_user(self):
        request_body = dict(request.json)  # Берем тело из запроса
        # Try и except на случай, если какие-то необязательные параметры не были переданы
        try:
            username = request_body['username']
        except KeyError:
            return 'username is null', 400
        try:
            password = request_body['password']
        except KeyError:
            return 'password is null', 400
        try:
            email = request_body['email']
        except KeyError:
            return 'email is null', 400
        try:
            phone = request_body['phone']
        except KeyError:
            return 'phone is null', 400
        try:
            gender = request_body['gender']
        except KeyError:
            return 'gender is null', 400
        try:
            gender_search = request_body['gender_search']
        except KeyError:
            return 'gender_search is null', 400
        try:
            balance = request_body['balance']
        except KeyError:
            balance = 0
        try:
            age = request_body['age']
        except KeyError:
            return 'age is null', 400

        # Валидируем параметры на соответствие требованиям sql
        if len(username) > 50:
            return f'username is more than 50 characters ', 400
        elif len(email) > 40:
            return f'email is more 40 characters', 400
        elif len(password) > 300:
            return f'password is more 300 characters', 400
        elif len(phone) > 20:
            return 'phone is more 20 characters', 400
        elif type(username) != str or type(password) != str or type(email) != str or type(phone) != str or type(gender) != str or type(gender_search) != str:
            return f'Parameters values must be a string', 400
        elif type(balance) != int or type(age) != int:
            return f'Parameters age and balance must be int', 400
        # Проверка возраста на реальность
        elif age <= 16 or age >= 110:
            return f'age must be > 16 and < 110', 400


        # Валидируем username, email и phone на занятость
        check_username = self.db_interaction.check_username(username)
        check_email = self.db_interaction.check_email(email)
        check_phone = self.db_interaction.check_phone(phone)
        #logger.info(f'check_username" {check_username}')
        #logger.info(f'check_email: {check_email}')
        if check_username is False and check_email is False and check_phone is False:
            self.db_interaction.add_user(
                username=username,
                password=password,
                email=email,
                phone=phone,
                gender=gender,
                gender_search=gender_search,
                balance=balance,
                age=age
            )
        elif check_email is True:
            return f'Email already used', 400
        elif check_username is True:
            return f'username already used', 400
        elif check_phone is True:
            return 'phone already used'
        # Берем из БД объект user и возвращаем на запрос.
        user = self.db_interaction.get_user_info(username)
        return f'Success added {username} : {user}', 201  # Вместе с http status code

    @auth.login_required
    def get_user_info(self, username):
        try:
            #logger.info(f'username" {username}')
            # Валидация
            if len(username) > 50:
                return 'username cannot be more than 50 characters', 400
            elif type(username) != str:
                return f'Username must be a string', 400
            user_info = self.db_interaction.get_user_info(username)
            return user_info, 200
        except UserNotFoundException:
            abort(404, description='User not found')

    @auth.login_required
    def edit_user_info(self, username):
        # проверим есть ли такой username в базе
        availability_check = self.db_interaction.check_username(username)
        if availability_check is False:
            abort(404, description='User not found')
        try:
            request_body = dict(request.json)  # Берем тело из запроса
        except TypeError:
            return 'Request body is Null', 400
        try:
            new_username = request_body['new_username']
            # сначала проверим на уникальность
            check = self.db_interaction.check_username(new_username)
            if check is True:
                return f'new_username: already used', 400
            elif len(new_username) > 50:
                return 'username cannot be more than 50 characters', 400
            elif type(new_username) is not str:
                return 'type parameter new_username must be a string', 400
        except KeyError:
            new_username = None
            #logger.info(f'new_username: {new_username}')
        try:
            new_password = request_body['new_password']
        except KeyError:
            new_password = None
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
            check = self.db_interaction.check_phone(new_phone)
            if check is True:
                return 'new_phone already used', 400
            elif len(new_phone) > 20:
                return 'new_phone cannot be more than 20 characters', 400
            elif type(new_phone) is not str:
                return 'type new_phone new_email must be a string', 400
        except KeyError:
            new_phone = None
        self.db_interaction.edit_user_info(
            username=username,
            new_username=new_username,
            new_password=new_password,
            new_email=new_email,
            new_phone=new_phone
        )

        return 'Success', 200


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
