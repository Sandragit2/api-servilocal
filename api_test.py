import os
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from flask_migrate import Migrate
from werkzeug.utils import secure_filename
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
#from models import db, Usuarios, Trabajadores
from models import (
    db,
    Usuarios,
    Trabajadores,
    SolicitudesServicios,
    Pagos,
    Notificaciones
)
import bcrypt
import mercadopago
from mercadopago.config import RequestOptions
from datetime import datetime


app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

#app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:@localhost/prueba_servilocal'

#app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:LTfMFcXrRlDTrUOUKOaxilTeczzAEpZa@switchyard.proxy.rlwy.net:55122/prueba_servilocal'

app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:DMqnooIJVoIyfkwJOhIzLZUOnJSOVvLg@shuttle.proxy.rlwy.net:21890/prueba_servilocal'

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

app.config['JWT_SECRET_KEY'] = 'clave_super_secreta_123'  
jwt = JWTManager(app)

UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

db.init_app(app)
migrate = Migrate(app, db)
sdk = mercadopago.SDK("TEST-3294946827363641-112610-9ab12ed9107ea78b76a49b0fee76f597-1132859484")
# es lo que se agrego
@app.route("/preferencemp", methods=["GET"])
def crear_preferencia():

    preference_data = {
        "items": [
            {
                "title": "Nombre del Producto",
                "quantity": 1,
                "unit_price": 100.00
            }
        ],

        "back_urls": {
            "success": "https://servilocal.pages.dev/success",
            "failure": "https://servilocal.pages.dev/failure",
            "pending": "https://servilocal.pages.dev/pending"
        },
        "auto_return": "approved",
    }

    # Crear preferencia
    preference_response = sdk.preference().create(preference_data)
    preference = preference_response["response"]

    data = {
        "id": preference["id"],
        "init_point": preference["init_point"],
        "sandbox_init_point": preference["sandbox_init_point"]
    }
    respuesta = {
        "mensaje" : "Mensaje de Exito",
        "status" : "success",
        "data" : data

    }

    return jsonify(respuesta), 200

######lo nuevo
@app.route('/processpayment', methods=['POST'])
@jwt_required()
def processPayment():
    parameters = request.get_json(silent=True)

    payment = parameters.get('formdata')
    iddevice = parameters.get('iddevice')
    trabajador = parameters.get("trabajador")

    if not payment or not payment.get('token'):
        return jsonify({"error": "Faltan datos obligatorios"}), 400

    amount = payment.get('transaction_amount')
    email = payment.get('payer').get('email')

    payment_data = {
        "transaction_amount": float(amount),
        "token": payment.get('token'),
        "payment_method_id": payment.get('payment_method_id'),
        "issuer_id": payment.get('issuer_id'),
        "description": "Pago por contratación de servicio",
        "installments": 1,
        "payer": {
            "first_name": "Cliente",
            "last_name": "ServiLocal",
            "email": email,
        },
        "additional_info": {
            "items": [
                {
                    "title": trabajador.get("categoria"),
                    "quantity": 1,
                    "unit_price": float(amount)
                }
            ]
        }
    }

    request_options = RequestOptions()
    import uuid
    request_options.custom_headers = {
        "X-Idempotency-Key": str(uuid.uuid4()),
        "X-meli-session-id": iddevice
    }

    result = sdk.payment().create(payment_data, request_options)
    paymentMP = result.get("response", {})

    # -------------------------------------------------------
    # AQUI DENTRO VA EL IF. NO FUERA.
    # -------------------------------------------------------
    if paymentMP.get("status") == "approved" and paymentMP.get("status_detail") == "accredited":

        identity = get_jwt_identity()
        id_usuario = int(identity)

        id_trabajador = trabajador.get("id_trabajador")

        nueva_solicitud = SolicitudesServicios(
            fecha_solicitud=datetime.now(),
            direccion_servicio="",
            descripcion_servicio=f"Solicitud para {trabajador.get('categoria')}",
            id_usuario=id_usuario,
            id_servicio=id_trabajador
        )
        db.session.add(nueva_solicitud)
        db.session.commit()

        nuevo_pago = Pagos(
            total=float(amount),
            fecha_pago=datetime.now(),
            id_solicitud=nueva_solicitud.id_solicitud,
            id_usuario=id_usuario
        )
        db.session.add(nuevo_pago)
        db.session.commit()

        nueva_notificacion = Notificaciones(
            tipo_notificacion="nueva_contratacion",
            mensaje=f"Tienes una nueva contratación. Solicitud #{nueva_solicitud.id_solicitud}",
            fecha_creacion=datetime.now(),
            id_trabajador=id_trabajador
        )
        db.session.add(nueva_notificacion)
        db.session.commit()

        return jsonify({
            "mensaje": "Pago aprobado y solicitud creada",
            "status": "success",
            "solicitud": nueva_solicitud.id_solicitud,
            "data": paymentMP
        }), 200

    # Pago fallido
    return jsonify({
        "mensaje": "Pago rechazado",
        "status": "error",
        "data": paymentMP
    }), 400



#################################



@app.route('/auth/register', methods=['POST'])
def register():
    data = request.get_json()

    nombre = data.get('nombre')
    apellidos = data.get('apellidos')
    correo = data.get('correo')
    telefono = data.get('telefono')
    contrasena = data.get('contrasena')
    rol = data.get('rol')

    if not all([nombre, correo, contrasena, rol]):
        return jsonify({"mensaje": "Faltan datos requeridos", "status": "error"}), 400

    if Usuarios.query.filter_by(correo=correo).first():
        return jsonify({"mensaje": "El correo ya está registrado", "status": "error"}), 409

    # 🔐 Cifrar contraseña
    hashed_password = bcrypt.hashpw(contrasena.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    nuevo_usuario = Usuarios(
        nombre=nombre,
        apellidos=apellidos,
        correo=correo,
        telefono=telefono,
        contrasena=hashed_password,
        rol=rol
    )

    db.session.add(nuevo_usuario)
    db.session.commit()

    return jsonify({"mensaje": "Usuario registrado correctamente", "status": "success"}), 201


@app.route('/auth/login', methods=['POST'])
def login():
    data = request.get_json()

    correo = data.get('correo')
    contrasena = data.get('contrasena')
    rol = data.get('rol')

    if not correo or not contrasena or not rol:
        return jsonify({"status": "error", "mensaje": "Todos los campos son obligatorios"}), 400

    usuario = Usuarios.query.filter_by(correo=correo, rol=rol).first()

    if not usuario:
        return jsonify({"status": "error", "mensaje": "Usuario o rol incorrecto"}), 401

    if not bcrypt.checkpw(contrasena.encode('utf-8'), usuario.contrasena.encode('utf-8')):
        return jsonify({"status": "error", "mensaje": "Contraseña incorrecta"}), 401

    # 🔥 TOKEN CORRECTO (identity debe ser STRING)
    token = create_access_token(
        identity=str(usuario.id_usuario),     # sub = id del usuario
        additional_claims={                  # datos adicionales
            "nombre": usuario.nombre,
            "rol": usuario.rol
        }
    )

    return jsonify({
        "status": "success",
        "mensaje": f"Bienvenido {usuario.nombre}",
        "token": token,
        "usuario": {
            "id": usuario.id_usuario,
            "nombre": usuario.nombre,
            "rol": usuario.rol
        }
    }), 200




@app.route('/auth/perfil', methods=['GET', 'PUT'])
@jwt_required()
def perfil_usuario():

    # identity ahora es solo un string con el ID del usuario
    identity = get_jwt_identity()
    user = Usuarios.query.get(int(identity))  # <--- ESTA ES LA LÍNEA CORRECTA

    if not user:
        return jsonify({"mensaje": "Usuario no encontrado"}), 404

    # GET: Obtener perfil
    if request.method == 'GET':
        return jsonify({
            "usuario": user.to_dict(),
            "status": "success"
        }), 200

    # PUT: Actualizar perfil
    if request.method == 'PUT':
        data = request.get_json()

        user.nombre = data.get("nombre", user.nombre)
        user.apellidos = data.get("apellidos", user.apellidos)
        user.telefono = data.get("telefono", user.telefono)
        user.direccion = data.get("direccion", user.direccion)

        db.session.commit()

        return jsonify({
            "mensaje": "Perfil actualizado",
            "usuario": user.to_dict(),
            "status": "success"
        }), 200




@app.route('/store/store', methods=['GET'])
def get_trabajadores():
    trabajadores = Trabajadores.query.order_by(Trabajadores.id_trabajador.asc()).all()
    lista_trabajadores = [trabajador.to_dict() for trabajador in trabajadores]

    respuesta = {
        "mensaje": "Lista de trabajadores obtenida correctamente",
        "status": "success",
        "lista_trabajadores": lista_trabajadores
    }

    return jsonify(respuesta), 200


@app.route('/store/trabajadores/<tipo>', methods=['GET'])
def get_trabajadores_por_tipo(tipo):
    trabajadores = Trabajadores.query.filter(
        Trabajadores.categoria.ilike(f"%{tipo}%")
    ).all()

    lista_trabajadores = [t.to_dict() for t in trabajadores]

    if not lista_trabajadores:
        return jsonify({
            "mensaje": f"No hay trabajadores para el servicio '{tipo}'",
            "status": "empty",
            "lista_trabajadores": []
        }), 200

    return jsonify({
        "mensaje": f"Lista de trabajadores en la categoría '{tipo}' obtenida correctamente",
        "status": "success",
        "lista_trabajadores": lista_trabajadores
    }), 200


@app.route('/store/trabajador/<int:id_trabajador>', methods=['GET'])
def get_trabajador_detalle(id_trabajador):
    trabajador = Trabajadores.query.get(id_trabajador)

    if not trabajador:
        return jsonify({"status": "error", "mensaje": "Trabajador no encontrado"}), 404

    data = trabajador.to_dict()

    resenas_data = []
    for resena in trabajador.resenas:
        resenas_data.append({
            "id_resena": resena.id_resena,
            "calificacion": resena.calificacion,
            "comentarios": resena.comentarios,
            "fecha_resena": resena.fecha_resena.strftime("%Y-%m-%d"),
            "cliente": f"{resena.usuario.nombre} {resena.usuario.apellidos}" if resena.usuario else "Anónimo"
        })

    return jsonify({
        "status": "success",
        "mensaje": "Información del trabajador obtenida correctamente",
        "trabajador": data,
        "resenas": resenas_data
    }), 200


@app.route('/upload_foto/<int:trabajador_id>', methods=['POST'])
def upload_foto(trabajador_id):
    if 'foto_trabajador' not in request.files:
        return jsonify({"mensaje": "No se envió ninguna imagen"}), 400

    file = request.files['foto_trabajador']
    if file.filename == '':
        return jsonify({"mensaje": "Nombre de archivo vacío"}), 400

    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)

    trabajador = Trabajadores.query.get(trabajador_id)
    if not trabajador:
        return jsonify({"mensaje": "Trabajador no encontrado"}), 404

    trabajador.foto_trabajador = f"static/uploads/{filename}"
    db.session.commit()

    return jsonify({
        "mensaje": "Foto subida correctamente",
        "ruta_foto": trabajador.foto_trabajador
    }), 200


@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


if __name__ == "__main__":
    app.run(debug=True)




                 