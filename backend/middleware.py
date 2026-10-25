from functools import wraps
import jwt
from flask import current_app, g, jsonify, request
from db import query


def token_requerido(fn):
    @wraps(fn)
    def wrapped(*args, **kwargs):
        header = request.headers.get('Authorization', '').split()
        if len(header) != 2 or header[0].lower() != 'bearer':
            return jsonify(error='Debes iniciar sesión.'), 401
        try:
            claims = jwt.decode(header[1], current_app.config['SECRET_KEY'], algorithms=['HS256'],
                options={'require': ['exp', 'iat', 'jti', 'usuario_id', 'username', 'rol']})
        except jwt.ExpiredSignatureError:
            return jsonify(error='Token expirado. Inicia sesión nuevamente.'), 401
        except jwt.InvalidTokenError:
            return jsonify(error='Token inválido.'), 401
        if query('SELECT jti FROM tokens_revocados WHERE jti=%s', (claims['jti'],), one=True):
            return jsonify(error='La sesión fue cerrada.'), 401
        user = query('SELECT id, username, email, rol, fecha_creacion, ultimo_acceso FROM usuarios WHERE id=%s', (claims['usuario_id'],), one=True)
        if not user:
            return jsonify(error='Usuario no disponible.'), 401
        g.user, g.claims = user, claims
        return fn(*args, **kwargs)
    return wrapped


def admin_requerido(fn):
    @token_requerido
    @wraps(fn)
    def wrapped(*args, **kwargs):
        if g.user['rol'] != 'admin':
            return jsonify(error='Solo los administradores pueden eliminar estudiantes.'), 403
        return fn(*args, **kwargs)
    return wrapped
