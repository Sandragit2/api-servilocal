from flask import Flask
from flask_migrate import Migrate
from models import db

app = Flask(__name__)

# --- Configuración de la base de datos ---
#app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:@localhost/prueba_servilocal'

app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:LTfMFcXrRlDTrUOUKOaxilTeczzAEpZa@switchyard.proxy.rlwy.net:55122/prueba_servilocal'


app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False


db.init_app(app)
migrate = Migrate(app, db)


#with app.app_context():
 #   db.create_all()

if __name__ == '__main__':
    app.run(debug=True)