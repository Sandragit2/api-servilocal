import os
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from flask_migrate import Migrate
from werkzeug.utils import secure_filename
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from models import db, Usuarios, Trabajadores
import bcrypt
import mercadopago
from mercadopago.config import RequestOptions




app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "http://localhost:4200"}})

#app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:@localhost/prueba_servilocal'

app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:LTfMFcXrRlDTrUOUKOaxilTeczzAEpZa@switchyard.proxy.rlwy.net:55122/prueba_servilocal'
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
            "success": "https://servilocal.com/success",
            "failure": "https://servilocal.com/failure",
            "pending": "https://servilocal.com/pending"
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
def processPayment():
    parameters = request.get_json(silent=True)

    payment = parameters.get('formdata')
    idcarrito = parameters.get('idfoliocarrito')
    iddevice = parameters.get('iddevice')

    if not payment.get('token'):
        return jsonify({"error": "Faltan datos obligatorios"}), 400

    # PROCESAR LA COMPRA Y REGISTRAR/MODIFICAR LA BD SEGÚN LA LÓGICA DE NEGOCIO
    amount = payment.get('transaction_amount')
    email = payment.get('payer').get('email')
    #segun nuestro proceso de negocio, tenemos quen ajustarlo segun nuestro proyecto
    payment_data = { 
        "transaction_amount": float(amount),
        "token": payment.get('token'),
        "payment_method_id": payment.get('payment_method_id'),
        "issuer_id": payment.get('issuer_id'),
        "description": "Descripción del pago a realizar",
        "installments": 1,  # Pago en una sola exhibición
        "statement_descriptor": "Description",
        "payer": {
            "first_name": "Jonathan", #esto es jalado de la base de datos
            "last_name": "Guevara",
            "email": email,
        },
        "additional_info": {  #items de lo que nosostros estamos vendiendo, de acuerdo a la logica del producto de la tienda
            "items": [
                {
                    "title": "Nombre del Producto",
                    "quantity": 1,
                    "unit_price": float(amount)
                }
            ]
        },
        "capture": True,
        "binary_mode": False,
        # "device_id": iddevice  # si es necesario activarlo después
    }

    # OPCIONES DE REQUEST PARA MERCADOPAGO
    request_options = RequestOptions()

    import uuid
    UUID = str(uuid.uuid4())

    request_options.custom_headers = {
        "X-Idempotency-Key": UUID,
        "X-meli-session-id": iddevice
    }

    # EJECUTAR EL PAGO, guardar lo que mercado pago nos diga
    result = sdk.payment().create(payment_data, request_options)
    payment = result.get("response", {})
    
    #hasta aqui ya podriamos cobrar, pero no se cobra por lo de la validacion de las tarjetas de prueba de mercado
    # SI EL PAGO SE APRUEBA, nos devuelve el status y podemos continuar con alguna notificacion o seguir el proceso
    # podemos cambiar lo de si fue exitoso o con error aqui 
    if payment.get("status") == "approved" and payment.get("status_detail") == "accredited":
        respuesta = {
            "mensaje": "Mensaje de Éxito",
            "status": "success",
            "data": payment
        }
        return jsonify(respuesta), 200

    # PAGO RECHAZADO O ERROR
    respuesta = {
        "mensaje": "Mensaje de Error",
        "status": "error",
        "data": payment
    }
    return jsonify(respuesta), 400

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

    # Validar contraseña cifrada
    if not bcrypt.checkpw(contrasena.encode('utf-8'), usuario.contrasena.encode('utf-8')):
        return jsonify({"status": "error", "mensaje": "Contraseña incorrecta"}), 401

    # Crear token
    token = create_access_token(identity={
        "id_usuario": usuario.id_usuario,
        "nombre": usuario.nombre,
        "rol": usuario.rol
    })

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



@app.route('/auth/perfil', methods=['GET'])
@jwt_required()
def perfil_usuario():
    current_user = get_jwt_identity()
    return jsonify({
        "mensaje": "Perfil del usuario autenticado",
        "usuario": current_user
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




                 