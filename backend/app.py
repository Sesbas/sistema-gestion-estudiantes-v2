import os
import sqlite3
from pathlib import Path
import bcrypt
import click
import pymysql
from flask import Flask, jsonify
from flask_cors import CORS
from werkzeug.exceptions import HTTPException
from config import Config
from db import close_db, query, transaction
from routes.auth import bp as auth_bp
from routes.estudiantes import bp as students_bp


def create_app(test_config=None):
    frontend = Path(__file__).resolve().parents[1] / 'frontend'
    app = Flask(__name__, static_folder=str(frontend), static_url_path='')
    app.config.from_object(Config)
    if test_config:
        app.config.update(test_config)
    if len(app.config['SECRET_KEY']) < 32:
        raise RuntimeError('Configura JWT_SECRET con al menos 32 caracteres en backend/.env.')
    app.config['DUMMY_HASH'] = bcrypt.hashpw(b'dummy-password', bcrypt.gensalt()).decode()
    CORS(app, resources={r'/api/*': {'origins': app.config['CORS_ORIGINS'],
        'methods': ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'], 'allow_headers': ['Content-Type', 'Authorization']}})
    app.teardown_appcontext(close_db)
    app.register_blueprint(auth_bp)
    app.register_blueprint(students_bp)

    @app.get('/')
    def index():
        return app.send_static_file('index.html')

    @app.errorhandler(HTTPException)
    def http_error(error):
        return jsonify(error=error.description), error.code

    @app.errorhandler(pymysql.IntegrityError)
    @app.errorhandler(sqlite3.IntegrityError)
    def duplicate(_error):
        return jsonify(error='El correo o usuario ya está registrado.', errores={'general': 'Hay datos duplicados o una referencia inválida.'}), 409

    @app.errorhandler(pymysql.MySQLError)
    def database_error(error):
        app.logger.exception('Error de base de datos: %s', error)
        return jsonify(error='No fue posible acceder a MySQL. Revisa la configuración y el esquema.'), 503

    @app.cli.command('crear-admin')
    @click.option('--username', default='admin', prompt=True)
    @click.option('--email', default='admin@unilibre.edu.co', prompt=True)
    @click.option('--password', prompt=True, hide_input=True, confirmation_prompt=True)
    def create_admin(username, email, password):
        from models import validate_registration
        data, errors = validate_registration(dict(username=username, email=email, password=password))
        if errors:
            raise click.ClickException(str(errors))
        with transaction():
            if query('SELECT id FROM usuarios WHERE username=%s OR email=%s', (data['username'], data['email']), one=True):
                raise click.ClickException('El usuario o correo ya existe.')
            query('INSERT INTO usuarios (username,email,password_hash,rol) VALUES (%s,%s,%s,%s)',
                (data['username'], data['email'], bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode(), 'admin'))
        click.echo('Administrador creado.')

    return app


if __name__ == '__main__':
    create_app().run(host='127.0.0.1', port=int(os.getenv('PORT', '5000')), debug=False)
