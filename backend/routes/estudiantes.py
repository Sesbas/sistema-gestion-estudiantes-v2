import math
from flask import Blueprint, g, jsonify, request
from db import query, transaction
from middleware import token_requerido, admin_requerido
from models import body, validate_student, STUDENT_FIELDS

bp = Blueprint('estudiantes', __name__, url_prefix='/api/estudiantes')


@bp.get('')
@token_requerido
def list_students():
    try:
        page, per_page = int(request.args.get('page', 1)), int(request.args.get('per_page', 5))
        if page < 1 or not 1 <= per_page <= 50:
            raise ValueError()
    except ValueError:
        return jsonify(error='page debe ser positivo y per_page debe estar entre 1 y 50.'), 400
    fields = request.args.get('orden', 'id').split(',')
    directions = request.args.get('direccion', 'asc').lower().split(',')
    if len(directions) == 1:
        directions *= len(fields)
    if len(fields) > 4 or len(directions) != len(fields) or any(f not in {'id', 'nombre', 'apellido', 'edad'} for f in fields) or any(d not in {'asc', 'desc'} for d in directions):
        return jsonify(error='Ordenamiento inválido.'), 400
    ordering = ', '.join(f'{f} {d}' for f, d in zip(fields, directions))
    if 'id' not in fields:
        ordering += ', id asc'
    search = request.args.get('search', '').strip()
    if len(search) > 100:
        return jsonify(error='La búsqueda admite hasta 100 caracteres.'), 400
    # Literal search: wildcard characters supplied by the user have no SQL meaning.
    pattern = '%' + search.replace('!', '!!').replace('%', '!%').replace('_', '!_') + '%'
    where = "WHERE nombre LIKE %s ESCAPE '!' OR apellido LIKE %s ESCAPE '!' OR carrera LIKE %s ESCAPE '!'"
    params = (pattern,) * 3
    total = query(f'SELECT COUNT(*) AS total FROM estudiantes {where}', params, one=True)['total']
    rows = query(f'SELECT * FROM estudiantes {where} ORDER BY {ordering} LIMIT %s OFFSET %s', params + (per_page, (page - 1) * per_page))
    return jsonify(estudiantes=rows, paginacion={'page': page, 'per_page': per_page, 'total_items': total,
        'total_pages': math.ceil(total / per_page), 'has_prev': page > 1, 'has_next': page * per_page < total})


@bp.get('/<int:sid>')
@token_requerido
def get_student(sid):
    row = query('SELECT * FROM estudiantes WHERE id=%s', (sid,), one=True)
    return jsonify(row) if row else (jsonify(error='Estudiante no encontrado.'), 404)


def save_student(sid=None):
    data = body()
    if sid is not None:
        original = query('SELECT * FROM estudiantes WHERE id=%s', (sid,), one=True)
        if not original:
            return jsonify(error='Estudiante no encontrado.'), 404
        data = {**{k: original[k] for k in STUDENT_FIELDS}, **data}
    clean, errors = validate_student(data)
    duplicate = query('SELECT id FROM estudiantes WHERE email=%s AND id<>%s', (clean['email'], sid or 0), one=True)
    if duplicate:
        errors['email'] = 'Este correo ya pertenece a otro estudiante.'
    if errors:
        return jsonify(error='Revisa los campos.', errores=errors), 409 if duplicate else 400
    columns = ('nombre', 'apellido', 'edad', 'carrera', 'email', 'telefono')
    with transaction():
        if sid is None:
            sid = query('INSERT INTO estudiantes (nombre,apellido,edad,carrera,email,telefono,creado_por,actualizado_por) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)',
                tuple(clean[k] for k in columns) + (g.user['id'], g.user['id']))
            return jsonify(mensaje='Estudiante creado exitosamente', id=sid, creado_por=g.user['username']), 201
        query('UPDATE estudiantes SET nombre=%s,apellido=%s,edad=%s,carrera=%s,email=%s,telefono=%s,actualizado_por=%s WHERE id=%s',
            tuple(clean[k] for k in columns) + (g.user['id'], sid))
    return jsonify(mensaje='Estudiante actualizado exitosamente', actualizado_por=g.user['username'])


@bp.post('')
@token_requerido
def create_student():
    return save_student()


@bp.put('/<int:sid>')
@token_requerido
def update_student(sid):
    return save_student(sid)


@bp.delete('/<int:sid>')
@admin_requerido
def delete_student(sid):
    with transaction():
        if not query('SELECT id FROM estudiantes WHERE id=%s', (sid,), one=True):
            return jsonify(error='Estudiante no encontrado.'), 404
        # The delete trigger records actualizado_por as the actor.
        query('UPDATE estudiantes SET actualizado_por=%s WHERE id=%s', (g.user['id'], sid))
        query('DELETE FROM estudiantes WHERE id=%s', (sid,))
    return jsonify(mensaje='Estudiante eliminado exitosamente', eliminado_por=g.user['username'])


@bp.get('/stats/general')
@token_requerido
def stats():
    result = query('SELECT * FROM vista_estadisticas', one=True)
    result['estudiantes_por_carrera'] = query('SELECT * FROM vista_estudiantes_por_carrera ORDER BY cantidad DESC, carrera ASC')
    return jsonify(result)
