# init_db.py
from app import app, db

with app.app_context():
    print("Iniciando a criação do banco de dados...")
    db.create_all()
    print("Banco de dados e tabelas criados com sucesso!")