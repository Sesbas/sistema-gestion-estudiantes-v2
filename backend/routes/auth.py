from datetime import datetime, timedelta, timezone
from uuid import uuid4
import bcrypt
import jwt
from flask import Blueprint, current_app, g, jsonify
from db import query, transaction
from middleware import token_requerido
from models import body, text, validate_registration

bp = Blueprint('auth', __name__, url_prefix='/api/auth')


@bp.post('/registro')
def register():
    data, errors = validate_registration(body())
    if errors:
        return jsonify(error='Revisa los campos.', errores=errors), 400
    with transaction():
        errors = {}
        for field in ('username', 'email'):
            if query(f'SELECT id FROM usuarios WHERE {field}=%s', (data[field],), one=True):
                errors[field] = 'Este valor ya está registrado.'
        if errors:
            return jsonify(error='El usuario ya existe.', errores=errors), 409
        hashed = bcrypt.hashpw(data['password'].encode(), bcrypt.gensalt()).decode()
        uid = query('INSERT INTO usuarios (username,email,password_hash,rol) VALUES (%s,%s,%s,%s)',
            (data['username'], data['email'], hashed, 'usuario'))
    return jsonify(mensaje='Usuario registrado exitosamente', usuario={'id': uid, 'username': data['username'], 'email': data['email']}), 201


@bp.post('/login')
def login():
    data = body()
    username, password = text(data, 'username'), data.get('password')
    if not username or not isinstance(password, str) or not 1 <= len(password.encode()) <= 72:
        return jsonify(error='Usuario o contraseña incorrectos.'), 401
    user = query('SELECT * FROM usuarios WHERE username=%s', (username,), one=True)
    # Check a dummy hash as well to reduce username enumeration by response time.
    hashed = user['password_hash'] if user else current_app.config['DUMMY_HASH']
    if not bcrypt.checkpw(password.encode(), hashed.encode()) or not user:
        return jsonify(error='Usuario o contraseña incorrectos.'), 401
    now = datetime.now(timezone.utc)
    claims = {'usuario_id': user['id'], 'username': user['username'], 'rol': user['rol'],
        'iat': now, 'exp': now + timedelta(seconds=current_app.config['JWT_SECONDS']), 'jti': str(uuid4())}
    with transaction():
        query('UPDATE usuarios SET ultimo_acceso=CURRENT_TIMESTAMP WHERE id=%s', (user['id'],))
    return jsonify(mensaje='Login exitoso', token=jwt.encode(claims, current_app.config['SECRET_KEY'], algorithm='HS256'),
        usuario={k: user[k] for k in ('id', 'username', 'email', 'rol')})


@bp.post('/logout')
@token_requerido
def logout():
    with transaction():
        query('DELETE FROM tokens_revocados WHERE exp < %s', (int(datetime.now(timezone.utc).timestamp()),))
        query('INSERT INTO tokens_revocados (jti,exp) VALUES (%s,%s)', (g.claims['jti'], g.claims['exp']))
    return jsonify(mensaje='Logout exitoso')


@bp.get('/perfil')
@token_requerido
def profile():
    return jsonify(usuario=g.user)
