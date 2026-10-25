CREATE DATABASE IF NOT EXISTS universidad_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE universidad_db;

CREATE TABLE IF NOT EXISTS usuarios (
  id INT PRIMARY KEY AUTO_INCREMENT,
  username VARCHAR(30) NOT NULL UNIQUE,
  email VARCHAR(254) NOT NULL UNIQUE,
  password_hash VARCHAR(100) NOT NULL,
  rol ENUM('admin','usuario') NOT NULL DEFAULT 'usuario',
  fecha_creacion TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  ultimo_acceso TIMESTAMP NULL
);
CREATE TABLE IF NOT EXISTS estudiantes (
  id INT PRIMARY KEY AUTO_INCREMENT,
  nombre VARCHAR(60) NOT NULL,
  apellido VARCHAR(60) NOT NULL,
  edad INT NOT NULL CHECK (edad BETWEEN 15 AND 100),
  carrera VARCHAR(100) NOT NULL,
  email VARCHAR(254) NOT NULL UNIQUE,
  telefono VARCHAR(25) NOT NULL DEFAULT '',
  creado_por INT NOT NULL,
  actualizado_por INT NOT NULL,
  fecha_creacion TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  fecha_actualizacion TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  FOREIGN KEY (creado_por) REFERENCES usuarios(id),
  FOREIGN KEY (actualizado_por) REFERENCES usuarios(id),
  INDEX idx_nombre (nombre), INDEX idx_apellido (apellido),
  INDEX idx_edad (edad), INDEX idx_carrera (carrera)
);
CREATE TABLE IF NOT EXISTS tokens_revocados (
  jti VARCHAR(36) PRIMARY KEY,
  exp BIGINT NOT NULL,
  INDEX idx_exp (exp)
);
CREATE TABLE IF NOT EXISTS auditoria_estudiantes (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  estudiante_id INT NOT NULL,
  accion ENUM('INSERT','UPDATE','DELETE') NOT NULL,
  usuario_id INT NOT NULL,
  fecha TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  datos_anteriores JSON,
  datos_nuevos JSON,
  INDEX idx_auditoria_estudiante (estudiante_id, fecha)
);

CREATE OR REPLACE VIEW vista_estadisticas AS
 SELECT COUNT(*) AS total_estudiantes, COALESCE(AVG(edad),0) AS promedio_edad,
 MIN(edad) AS edad_minima, MAX(edad) AS edad_maxima FROM estudiantes;
CREATE OR REPLACE VIEW vista_estudiantes_por_carrera AS
 SELECT carrera, COUNT(*) AS cantidad FROM estudiantes GROUP BY carrera;

DROP TRIGGER IF EXISTS estudiantes_insert;
DROP TRIGGER IF EXISTS estudiantes_update;
DROP TRIGGER IF EXISTS estudiantes_delete;
DELIMITER $$
CREATE TRIGGER estudiantes_insert AFTER INSERT ON estudiantes FOR EACH ROW
BEGIN
 INSERT INTO auditoria_estudiantes (estudiante_id,accion,usuario_id,datos_nuevos)
 VALUES (NEW.id,'INSERT',NEW.creado_por,JSON_OBJECT('nombre',NEW.nombre,'apellido',NEW.apellido,'edad',NEW.edad,'carrera',NEW.carrera,'email',NEW.email,'telefono',NEW.telefono));
END$$
CREATE TRIGGER estudiantes_update AFTER UPDATE ON estudiantes FOR EACH ROW
BEGIN
 IF NOT (OLD.nombre <=> NEW.nombre AND OLD.apellido <=> NEW.apellido AND OLD.edad <=> NEW.edad AND OLD.carrera <=> NEW.carrera AND OLD.email <=> NEW.email AND OLD.telefono <=> NEW.telefono) THEN
 INSERT INTO auditoria_estudiantes (estudiante_id,accion,usuario_id,datos_anteriores,datos_nuevos)
 VALUES (NEW.id,'UPDATE',NEW.actualizado_por,
 JSON_OBJECT('nombre',OLD.nombre,'apellido',OLD.apellido,'edad',OLD.edad,'carrera',OLD.carrera,'email',OLD.email,'telefono',OLD.telefono),
 JSON_OBJECT('nombre',NEW.nombre,'apellido',NEW.apellido,'edad',NEW.edad,'carrera',NEW.carrera,'email',NEW.email,'telefono',NEW.telefono));
 END IF;
END$$
CREATE TRIGGER estudiantes_delete AFTER DELETE ON estudiantes FOR EACH ROW
BEGIN
 INSERT INTO auditoria_estudiantes (estudiante_id,accion,usuario_id,datos_anteriores)
 VALUES (OLD.id,'DELETE',OLD.actualizado_por,JSON_OBJECT('nombre',OLD.nombre,'apellido',OLD.apellido,'edad',OLD.edad,'carrera',OLD.carrera,'email',OLD.email,'telefono',OLD.telefono));
END$$
DELIMITER ;
