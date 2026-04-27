from flask import Flask, jsonify, request
from flask_cors import CORS
import pandas as pd
import sqlite3
import os
from datetime import datetime

app = Flask(__name__)
CORS(app)

DB_PATH = 'alunos.db'
CAMINHO_PLANILHA = 'dados/alunos.xlsx'

def calcular_idade(data_nasc):
    try:
        nasc = datetime.strptime(data_nasc, '%Y-%m-%d')
        hoje = datetime.now()
        return hoje.year - nasc.year - ((hoje.month, hoje.day) < (nasc.month, nasc.day))
    except:
        return "-"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS alunos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT,
            telefone TEXT,
            email TEXT,
            matricula TEXT UNIQUE,
            nascimento TEXT,
            monitor TEXT,
            status TEXT
        )
    ''')
    
    # Se o banco estiver vazio, importa da planilha
    cursor.execute('SELECT COUNT(*) FROM alunos')
    if cursor.fetchone()[0] == 0 and os.path.exists(CAMINHO_PLANILHA):
        df = pd.read_excel(CAMINHO_PLANILHA, sheet_name=0)
        df.columns = [str(c).strip() for c in df.columns]
        
        # Mapeamento exato da sua planilha
        for _, row in df.iterrows():
            cursor.execute('''
                INSERT OR IGNORE INTO alunos (nome, telefone, email, matricula, nascimento, monitor, status)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                str(row.get('Nome', '-')),
                str(row.get('Celular', '-')),
                str(row.get('email', '-')),
                str(row.get('PDITA', '-')),
                str(row.get('Aniversário', '-'))[:10], # Pega apenas YYYY-MM-DD
                str(row.get('Agente de Sucesso', '-')),
                str(row.get('DECISÃO', 'Manter'))
            ))
    conn.commit()
    conn.close()

@app.route('/api/alunos', methods=['GET'])
def get_alunos():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM alunos')
    rows = cursor.fetchall()
    
    alunos = []
    for row in rows:
        aluno = dict(row)
        # Formata data para o padrão BR e calcula idade
        original_date = aluno['nascimento']
        try:
            date_obj = datetime.strptime(original_date, '%Y-%m-%d')
            aluno['nascimento_formatado'] = date_obj.strftime('%d/%m/%Y')
            aluno['idade'] = calcular_idade(original_date)
        except:
            aluno['nascimento_formatado'] = original_date
            aluno['idade'] = "-"
        alunos.append(aluno)
        
    conn.close()
    return jsonify(alunos)

@app.route('/api/alunos/update', methods=['POST'])
def update_aluno():
    dados = request.json
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE alunos 
        SET nome=?, telefone=?, email=?, nascimento=?, monitor=?, status=?
        WHERE matricula=?
    ''', (dados['nome'], dados['telefone'], dados['email'], dados['nascimento'], 
          dados['monitor'], dados['status'], dados['matricula']))
    conn.commit()
    conn.close()
    return jsonify({"status": "sucesso"})

if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=5000)