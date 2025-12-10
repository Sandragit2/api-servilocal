from flask_sqlalchemy import SQLAlchemy
from enum import Enum as PyEnum
from sqlalchemy import Enum

db = SQLAlchemy()

# ============================================================
# USUARIOS (clientes, trabajadores, administradores)
# ============================================================
class Usuarios(db.Model):
    __tablename__ = "usuarios"

    id_usuario = db.Column(db.Integer, primary_key=True, autoincrement=True)
    nombre = db.Column(db.String(100), nullable=False)
    apellidos = db.Column(db.String(100))
    correo = db.Column(db.String(100), unique=True, nullable=False)
    direccion = db.Column(db.String(255), nullable=True)
    telefono = db.Column(db.String(13), nullable=True)
    contrasena = db.Column(db.String(255), nullable=False)
    rol = db.Column(db.Enum('cliente', 'trabajador', 'administrador', name='rol_usuario'), default='cliente')

    # Relaciones
    trabajador = db.relationship('Trabajadores', back_populates='usuario', uselist=False)
    administrador = db.relationship('Administradores', back_populates='usuario', uselist=False)
    solicitudes = db.relationship('SolicitudesServicios', back_populates='usuario', lazy=True)
    pagos = db.relationship('Pagos', back_populates='usuario', lazy=True)
    mensajes = db.relationship('Mensajes', back_populates='usuario', lazy=True)
    direcciones = db.relationship('Direcciones', back_populates='usuario', lazy=True)
    notificaciones = db.relationship('Notificaciones', back_populates='usuario', lazy=True)
    resenas = db.relationship('Resenas', back_populates='usuario', lazy=True)

    def to_dict(self):
        return {
            "id_usuario": self.id_usuario,
            "nombre": self.nombre,
            "apellidos": self.apellidos,
            "correo": self.correo,
            "direccion": self.direccion,
            "telefono": self.telefono,
            "rol": self.rol
        }


# ============================================================
# TRABAJADORES (perfil extendido del usuario)
# ============================================================
class Trabajadores(db.Model):
    __tablename__ = 'trabajadores'

    id_trabajador = db.Column(db.Integer, primary_key=True, autoincrement=True)
    id_usuario = db.Column(db.Integer, db.ForeignKey('usuarios.id_usuario'))
    categoria = db.Column(db.String(100))
    descripcion_trabajo = db.Column(db.String(255))
    experiencia = db.Column(db.String(500))
    habilidades = db.Column(db.String(500))
    ubicacion = db.Column(db.String(200))
    foto_trabajador = db.Column(db.String(255))

    usuario = db.relationship('Usuarios', back_populates='trabajador')
    servicios = db.relationship('Servicios', back_populates='trabajador', lazy=True)
    disponibilidades = db.relationship('Disponibilidad', back_populates='trabajador', lazy=True)
    resenas = db.relationship('Resenas', back_populates='trabajador', lazy=True)
    mensajes = db.relationship('Mensajes', back_populates='trabajador', lazy=True)
    notificaciones = db.relationship('Notificaciones', back_populates='trabajador', lazy=True)

    def to_dict(self):
        # Calcular promedio de reseñas
        promedio = None
        if self.resenas and len(self.resenas) > 0:
            promedio = round(sum(r.calificacion for r in self.resenas) / len(self.resenas), 1)

        return {
            "id_trabajador": self.id_trabajador,
            "nombre": self.usuario.nombre if self.usuario else None,
            "apellidos": self.usuario.apellidos if self.usuario else None,
            "categoria": self.categoria,
            "descripcion_trabajo": self.descripcion_trabajo,
            "experiencia": self.experiencia,
            "habilidades": self.habilidades,
            # Usa ubicación propia o dirección del usuario si está vacía
            "ubicacion": self.ubicacion or (self.usuario.direccion if self.usuario else None),
            "foto_trabajador": self.foto_trabajador,
            "correo": self.usuario.correo if self.usuario else None,
            "telefono": self.usuario.telefono if self.usuario else None,
            "calificacion_promedio": promedio
        }


# ============================================================
# ADMINISTRADORES
# ============================================================
class Administradores(db.Model):
    __tablename__ = 'administradores'

    id_administrador = db.Column(db.Integer, primary_key=True, autoincrement=True)
    id_usuario = db.Column(db.Integer, db.ForeignKey('usuarios.id_usuario'))
    nivel_acceso = db.Column(db.Integer, nullable=False)

    usuario = db.relationship('Usuarios', back_populates='administrador')

    def to_dict(self):
        return {
            "id_administrador": self.id_administrador,
            "correo": self.usuario.correo if self.usuario else None,
            "nivel_acceso": self.nivel_acceso
        }


# ============================================================
# SERVICIOS Y RELACIONES
# ============================================================
class Servicios(db.Model):
    __tablename__ = 'servicios'

    id_servicio = db.Column(db.Integer, primary_key=True, autoincrement=True)
    tipo_servicio = db.Column(db.String(100), nullable=False)
    descripcion = db.Column(db.String(255), nullable=False)
    tarifa = db.Column(db.Integer, nullable=False)
    tipo_tarifa = db.Column(db.String(100))

    id_trabajador = db.Column(db.Integer, db.ForeignKey("trabajadores.id_trabajador"), nullable=False)
    trabajador = db.relationship('Trabajadores', back_populates='servicios')
    solicitudes = db.relationship('SolicitudesServicios', back_populates='servicio', lazy=True)

    def to_dict(self):
        return {
            "id_servicio": self.id_servicio,
            "tipo_servicio": self.tipo_servicio,
            "descripcion": self.descripcion,
            "tarifa": self.tarifa,
            "tipo_tarifa": self.tipo_tarifa
        }


# ============================================================
# DISPONIBILIDAD
# ============================================================
class Estado(PyEnum):
    DISPONIBLE = 'disponible'
    OCUPADO = 'ocupado'
    INACTIVO = 'inactivo'

class Disponibilidad(db.Model):
    __tablename__ = 'disponibilidad_trabajadores'

    id_disponibilidad = db.Column(db.Integer, primary_key=True, autoincrement=True)
    fecha = db.Column(db.DateTime, nullable=False)
    hora_inicio = db.Column(db.Time, nullable=False)
    hora_fin = db.Column(db.Time, nullable=False)
    estado = db.Column(Enum(Estado), default=Estado.DISPONIBLE)

    id_trabajador = db.Column(db.Integer, db.ForeignKey("trabajadores.id_trabajador"), nullable=False)
    trabajador = db.relationship('Trabajadores', back_populates='disponibilidades')


# ============================================================
# SOLICITUDES, PAGOS, RESEÑAS, ETC.
# ============================================================
class SolicitudesServicios(db.Model):
    __tablename__ = 'solicitudes_servicios'

    id_solicitud = db.Column(db.Integer, primary_key=True, autoincrement=True)
    fecha_solicitud = db.Column(db.DateTime, nullable=False)
    direccion_servicio = db.Column(db.String(255), nullable=False)
    descripcion_servicio = db.Column(db.String(255), nullable=False)

    id_usuario = db.Column(db.Integer, db.ForeignKey("usuarios.id_usuario"), nullable=False)
    id_servicio = db.Column(db.Integer, db.ForeignKey("servicios.id_servicio"), nullable=False)

    usuario = db.relationship('Usuarios', back_populates='solicitudes')
    servicio = db.relationship('Servicios', back_populates='solicitudes')
    pagos = db.relationship('Pagos', back_populates='solicitud', lazy=True)
    resenas = db.relationship('Resenas', back_populates='solicitud', lazy=True)
    mensajes = db.relationship('Mensajes', back_populates='solicitud', lazy=True)


class Pagos(db.Model):
    __tablename__ = "pagos"

    id_pago = db.Column(db.Integer, primary_key=True, autoincrement=True)
    total = db.Column(db.Integer, nullable=False)
    fecha_pago = db.Column(db.DateTime, nullable=False)
    id_solicitud = db.Column(db.Integer, db.ForeignKey("solicitudes_servicios.id_solicitud"), nullable=False)
    id_usuario = db.Column(db.Integer, db.ForeignKey("usuarios.id_usuario"), nullable=False)

    solicitud = db.relationship('SolicitudesServicios', back_populates='pagos')
    usuario = db.relationship('Usuarios', back_populates='pagos')


class Resenas(db.Model):
    __tablename__ = "resenas"

    id_resena = db.Column(db.Integer, primary_key=True, autoincrement=True)
    calificacion = db.Column(db.Integer, nullable=False)
    comentarios = db.Column(db.String(500), nullable=False)
    fecha_resena = db.Column(db.DateTime, nullable=False)
    id_solicitud = db.Column(db.Integer, db.ForeignKey("solicitudes_servicios.id_solicitud"), nullable=False)
    id_usuario = db.Column(db.Integer, db.ForeignKey("usuarios.id_usuario"), nullable=False)
    id_trabajador = db.Column(db.Integer, db.ForeignKey("trabajadores.id_trabajador"), nullable=False)

    solicitud = db.relationship('SolicitudesServicios', back_populates='resenas')
    usuario = db.relationship('Usuarios', back_populates='resenas')
    trabajador = db.relationship('Trabajadores', back_populates='resenas')


class Mensajes(db.Model):
    __tablename__ = 'mensajes'

    id_mensaje = db.Column(db.Integer, primary_key=True, autoincrement=True)
    contenido = db.Column(db.String(500))
    fecha_envio = db.Column(db.DateTime)
    id_solicitud = db.Column(db.Integer, db.ForeignKey("solicitudes_servicios.id_solicitud"))
    id_usuario = db.Column(db.Integer, db.ForeignKey("usuarios.id_usuario"))
    id_trabajador = db.Column(db.Integer, db.ForeignKey("trabajadores.id_trabajador"))

    solicitud = db.relationship('SolicitudesServicios', back_populates='mensajes')
    usuario = db.relationship('Usuarios', back_populates='mensajes')
    trabajador = db.relationship('Trabajadores', back_populates='mensajes')


class Direcciones(db.Model):
    __tablename__ = 'direcciones'

    id_direccion = db.Column(db.Integer, primary_key=True, autoincrement=True)
    latitud = db.Column(db.Float)
    longitud = db.Column(db.Float)
    direccion_completa = db.Column(db.String(255))
    id_usuario = db.Column(db.Integer, db.ForeignKey("usuarios.id_usuario"), nullable=False)

    usuario = db.relationship('Usuarios', back_populates='direcciones')


class Notificaciones(db.Model):
    __tablename__ = 'notificaciones'

    id_notificacion = db.Column(db.Integer, primary_key=True, autoincrement=True)
    tipo_notificacion = db.Column(db.String(255))
    mensaje = db.Column(db.Text)
    fecha_creacion = db.Column(db.DateTime)
    leido = db.Column(db.Boolean, default=False)
    id_usuario = db.Column(db.Integer, db.ForeignKey("usuarios.id_usuario"))
    id_trabajador = db.Column(db.Integer, db.ForeignKey("trabajadores.id_trabajador"))

    usuario = db.relationship('Usuarios', back_populates='notificaciones')
    trabajador = db.relationship('Trabajadores', back_populates='notificaciones')


class BitacoraAccesos(db.Model):
    __tablename__ = "bitacora_accesos"

    id_log = db.Column(db.Integer, primary_key=True, autoincrement=True)
    id_usuario = db.Column(db.Integer, db.ForeignKey('usuarios.id_usuario'))
    accion = db.Column(db.String(255), nullable=False)
    ip = db.Column(db.String(50))
    user_agent = db.Column(db.String(300))
    fecha = db.Column(db.DateTime, server_default=db.func.now())

    usuario = db.relationship('Usuarios', backref='logs')

    def to_dict(self):
        return {
            "id_log": self.id_log,
            "usuario": self.usuario.nombre if self.usuario else "Sistema",
            "accion": self.accion,
            "ip": self.ip,
            "user_agent": self.user_agent,
            "fecha": self.fecha
        }
