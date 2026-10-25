import re
from flask import request
from werkzeug.exceptions import BadRequest

EMAIL = re.compile(r'^[A-Za-z0-9.!#$%&\x27*+/=?^_`{|}~-]+@[A-Za-z0-9](?:[A-Za-z0-9.-]*[A-Za-z0-9])?\.[A-Za-z]{2,}$')
NAME = re.compile(r'^[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]+(?:[ -][A-Za-zÁÉÍÓÚÜÑáéíóúüñ]+)*$')
STUDENT_FIELDS = {'nombre', 'apellido', 'edad', 'carrera', 'email', 'telefono'}


def body():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise BadRequest('Envía un objeto JSON válido.')
    return data


def text(data, field):
    value = data.get(field)
    return value.strip() if isinstance(value, str) else ''


def validate_student(data):
    clean, errors = {}, {}
    for field in ('nombre', 'apellido'):
        value = text(data, field)
        clean[field] = value
        if not 2 <= len(value) <= 60 or not NAME.fullmatch(value):
            errors[field] = 'Usa entre 2 y 60 letras, espacios o guiones.'
    age = data.get('edad')
    if type(age) is not int or not 15 <= age <= 100:
        errors['edad'] = 'La edad debe ser un entero entre 15 y 100.'
    clean['edad'] = age
    clean['carrera'] = text(data, 'carrera')
    if not 3 <= len(clean['carrera']) <= 100 or not re.fullmatch(r'[\wÁÉÍÓÚÜÑáéíóúüñ .()&-]+', clean['carrera']):
        errors['carrera'] = 'Usa entre 3 y 100 caracteres válidos.'
    clean['email'] = text(data, 'email').lower()
    if len(clean['email']) > 254 or not EMAIL.fullmatch(clean['email']):
        errors['email'] = 'Ingresa un correo electrónico válido.'
    clean['telefono'] = text(data, 'telefono')
    if clean['telefono'] and (not re.fullmatch(r'\+?[0-9 ()-]{7,25}', clean['telefono']) or not 7 <= len(re.sub(r'\D', '', clean['telefono'])) <= 15):
        errors['telefono'] = 'Usa entre 7 y 15 dígitos; se permiten +, espacios, paréntesis y guiones.'
    if set(data) - STUDENT_FIELDS:
        errors['general'] = 'Hay campos no permitidos.'
    return clean, errors


def validate_registration(data):
    clean = {field: text(data, field) for field in ('username', 'email')}
    clean['email'] = clean['email'].lower()
    password = data.get('password')
    errors = {}
    if not re.fullmatch(r'[A-Za-z0-9_]{3,30}', clean['username']):
        errors['username'] = 'Usa entre 3 y 30 letras, números o guiones bajos.'
    if len(clean['email']) > 254 or not EMAIL.fullmatch(clean['email']):
        errors['email'] = 'Ingresa un correo electrónico válido.'
    if not isinstance(password, str) or len(password) < 6 or len(password.encode('utf-8')) > 72:
        errors['password'] = 'Usa al menos 6 caracteres y como máximo 72 bytes UTF-8.'
    clean['password'] = password
    if set(data) - {'username', 'email', 'password'}:
        errors['general'] = 'Hay campos no permitidos.'
    return clean, errors
