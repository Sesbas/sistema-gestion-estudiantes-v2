"""API contract tests with a temporary SQLite database, not a MySQL certification."""
import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import bcrypt
import jwt
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import create_app

SECRET = 'test-secret-with-at-least-thirty-two-characters'
SCHEMA = '''
CREATE TABLE usuarios(id INTEGER PRIMARY KEY, username TEXT UNIQUE COLLATE NOCASE, email TEXT UNIQUE COLLATE NOCASE, password_hash TEXT, rol TEXT, fecha_creacion TEXT DEFAULT CURRENT_TIMESTAMP, ultimo_acceso TEXT);
CREATE TABLE estudiantes(id INTEGER PRIMARY KEY, nombre TEXT, apellido TEXT, edad INTEGER, carrera TEXT, email TEXT UNIQUE COLLATE NOCASE, telefono TEXT, creado_por INTEGER, actualizado_por INTEGER, fecha_creacion TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE tokens_revocados(jti TEXT PRIMARY KEY, exp INTEGER);
CREATE VIEW vista_estadisticas AS SELECT COUNT(*) total_estudiantes, COALESCE(AVG(edad),0) promedio_edad, MIN(edad) edad_minima, MAX(edad) edad_maxima FROM estudiantes;
CREATE VIEW vista_estudiantes_por_carrera AS SELECT carrera, COUNT(*) cantidad FROM estudiantes GROUP BY carrera;
'''


@pytest.fixture
def client(tmp_path):
    path = tmp_path / 'test.sqlite'
    db = sqlite3.connect(path)
    db.executescript(SCHEMA)
    db.execute('INSERT INTO usuarios(username,email,password_hash,rol) VALUES (?,?,?,?)',
        ('admin', 'admin@unilibre.edu.co', bcrypt.hashpw(b'admin123', bcrypt.gensalt()).decode(), 'admin'))
    db.commit(); db.close()
    app = create_app({'TESTING': True, 'SECRET_KEY': SECRET, 'TEST_DATABASE': str(path)})
    return app.test_client()


def login(client, username='admin', password='admin123'):
    response = client.post('/api/auth/login', json=dict(username=username, password=password))
    assert response.status_code == 200
    return {'Authorization': 'Bearer ' + response.json['token']}


def student(**changes):
    data = dict(nombre='María', apellido='Pérez', edad=22, carrera='Ingeniería de Sistemas',
        email='maria@unilibre.edu.co', telefono='+57 310 1234567')
    return {**data, **changes}


def test_auth_and_revocation(client):
    assert client.get('/api/estudiantes').status_code == 401
    assert client.post('/api/auth/login', json={'username': 'admin', 'password': 'wrong'}).status_code == 401
    headers = login(client)
    claims = jwt.decode(headers['Authorization'][7:], SECRET, algorithms=['HS256'])
    assert claims['exp'] - claims['iat'] == 3600
    assert client.get('/api/auth/perfil', headers=headers).json['usuario']['rol'] == 'admin'
    assert client.post('/api/auth/logout', headers=headers).status_code == 200
    assert client.get('/api/auth/perfil', headers=headers).status_code == 401
    # Revocation survives app instances because it lives in the database.
    other = create_app(dict(client.application.config)).test_client()
    assert other.get('/api/estudiantes', headers=headers).status_code == 401


def test_expired_and_forged_tokens(client):
    claims = {'usuario_id': 1, 'username': 'admin', 'rol': 'admin', 'jti': 'old',
        'iat': datetime.now(timezone.utc) - timedelta(hours=2), 'exp': datetime.now(timezone.utc) - timedelta(hours=1)}
    for key in (SECRET, 'another-long-secret-with-more-than-32-characters'):
        token = jwt.encode(claims, key, algorithm='HS256')
        assert client.get('/api/estudiantes', headers={'Authorization': 'Bearer ' + token}).status_code == 401


def test_registration_roles_crud(client):
    account = {'username': 'alumno', 'email': 'alumno@example.com', 'password': 'pass123'}
    assert client.post('/api/auth/registro', json={**account, 'rol': 'admin'}).status_code == 400
    assert client.post('/api/auth/registro', json=account).status_code == 201
    assert client.post('/api/auth/registro', json=account).status_code == 409
    headers = login(client, 'alumno', 'pass123')
    assert client.get('/api/auth/perfil', headers=headers).json['usuario']['rol'] == 'usuario'
    created = client.post('/api/estudiantes', json=student(), headers=headers)
    assert created.status_code == 201
    sid = created.json['id']; url = f'/api/estudiantes/{sid}'
    assert client.get(url, headers=headers).json['nombre'] == 'María'
    assert client.put(url, json={'edad': 23}, headers=headers).status_code == 200
    assert client.get(url, headers=headers).json['email'] == student()['email']
    assert client.delete(url, headers=headers).status_code == 403
    assert client.delete(url, headers=login(client)).status_code == 200
    assert client.get(url, headers=headers).status_code == 404


@pytest.mark.parametrize('change,field', [({'nombre': '<script>'}, 'nombre'), ({'edad': 14}, 'edad'),
    ({'edad': True}, 'edad'), ({'edad': 20.5}, 'edad'), ({'email': 'no-email'}, 'email'),
    ({'telefono': 'abc'}, 'telefono'), ({'carrera': ''}, 'carrera'), ({'edad': 101}, 'edad')])
def test_validation(client, change, field):
    response = client.post('/api/estudiantes', json=student(**change), headers=login(client))
    assert response.status_code == 400
    assert field in response.json['errores']


def test_unique_email_partial_update_and_malformed_json(client):
    headers = login(client)
    sid = client.post('/api/estudiantes', json=student(), headers=headers).json['id']
    assert client.post('/api/estudiantes', json=student(), headers=headers).status_code == 409
    assert client.put(f'/api/estudiantes/{sid}', json={'edad': 24}, headers=headers).status_code == 200
    for data in ([], None, 'text'):
        assert client.post('/api/estudiantes', json=data, headers=headers).status_code == 400


def test_pagination_search_sort_stats(client):
    headers = login(client)
    for i in range(7):
        assert client.post('/api/estudiantes', json=student(email=f'est{i}@example.com', edad=20+i,
            carrera='Derecho' if i < 3 else 'Ingeniería'), headers=headers).status_code == 201
    result = client.get('/api/estudiantes?per_page=5&orden=edad,apellido&direccion=desc,asc', headers=headers).json
    assert len(result['estudiantes']) == 5
    assert result['estudiantes'][0]['edad'] == 26
    assert result['paginacion']['total_pages'] == 2
    result = client.get('/api/estudiantes?page=2', headers=headers).json
    assert len(result['estudiantes']) == 2 and result['paginacion']['has_prev']
    assert client.get('/api/estudiantes?search=Derecho', headers=headers).json['paginacion']['total_items'] == 3
    assert client.get('/api/estudiantes?search=%25', headers=headers).json['paginacion']['total_items'] == 0
    for query in ('page=0', 'page=no', 'per_page=51', 'orden=nombre;DROP TABLE estudiantes', 'direccion=oops'):
        assert client.get('/api/estudiantes?' + query, headers=headers).status_code == 400
    stats = client.get('/api/estudiantes/stats/general', headers=headers).json
    assert stats['total_estudiantes'] == 7 and stats['promedio_edad'] == 23
    assert len(stats['estudiantes_por_carrera']) == 2


def test_cors(client):
    allowed = client.options('/api/estudiantes', headers={'Origin': 'http://localhost:8000', 'Access-Control-Request-Method': 'POST', 'Access-Control-Request-Headers': 'Authorization,Content-Type'})
    assert allowed.headers['Access-Control-Allow-Origin'] == 'http://localhost:8000'
    denied = client.options('/api/estudiantes', headers={'Origin': 'https://example.org'})
    assert 'Access-Control-Allow-Origin' not in denied.headers


def test_mysql_script_has_audit_and_views():
    sql = Path(__file__).resolve().parents[1].joinpath('universidad_db.sql').read_text(encoding='utf-8')
    assert sql.count('CREATE TRIGGER') == 3
    assert sql.count('CREATE OR REPLACE VIEW') == 2


def test_flask_serves_frontend_and_keeps_api_protected(client):
    assert b'<!doctype html>' in client.get('/').data
    assert client.get('/css/styles.css').status_code == 200
    script = client.get('/js/app.js')
    assert script.status_code == 200
    assert b'location.origin' in script.data
    assert client.get('/api/estudiantes').status_code == 401
    assert client.get('/backend/.env').status_code == 404
