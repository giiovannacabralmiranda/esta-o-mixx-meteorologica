import json
import sqlite3
from datetime import datetime

from flask import Flask, jsonify, render_template
import paho.mqtt.client as mqtt

app = Flask(__name__)

BROKER = "broker.hivemq.com"
PORTA = 1883
TOPICO = "pd2/estacao_2026_7f3a/dados"
BANCO = "estacao.db"


def conectar_banco():
    with sqlite3.connect(BANCO) as conexao:
        conexao.execute("""
            CREATE TABLE IF NOT EXISTS medicoes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                data_hora TEXT,
                temperatura REAL,
                umidade REAL,
                pressao REAL,
                luminosidade REAL,
                qualidade_ar REAL,
                chuva_mm REAL
            )
        """)


def salvar_dados(leitura):
    campos = [
        "temperatura",
        "umidade",
        "pressao",
        "luminosidade",
        "qualidade_ar",
        "chuva_mm"
    ]

    valores = [float(leitura[campo]) for campo in campos]

    with sqlite3.connect(BANCO) as conexao:
        conexao.execute("""
            INSERT INTO medicoes
            (data_hora, temperatura, umidade, pressao,
             luminosidade, qualidade_ar, chuva_mm)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, [datetime.now().strftime("%d/%m/%Y %H:%M:%S")] + valores)


def ao_conectar(cliente, dados, flags, motivo, propriedades):
    if motivo == 0:
        print("Conectado ao MQTT!")
        cliente.subscribe(TOPICO)
        print("Aguardando dados do ESP32...")


def ao_receber(cliente, dados, mensagem):
    try:
        leitura = json.loads(mensagem.payload.decode())

        campos = [
            "temperatura",
            "umidade",
            "pressao",
            "luminosidade",
            "qualidade_ar",
            "chuva_mm"
        ]

        if not all(campo in leitura for campo in campos):
            print("Mensagem incompleta.")
            return

        salvar_dados(leitura)

        print("Medição recebida e salva:")
        print(leitura)

    except Exception as erro:
        print("Erro ao receber dados:", erro)


@app.route("/")
def inicio():
    return render_template("index.html")


@app.route("/api/medicoes")
def medicoes():
    with sqlite3.connect(BANCO) as conexao:
        conexao.row_factory = sqlite3.Row

        resultado = conexao.execute("""
            SELECT * FROM medicoes
            ORDER BY id DESC
            LIMIT 50
        """).fetchall()

    return jsonify([dict(linha) for linha in resultado])



conectar_banco()

cliente = mqtt.Client(
    mqtt.CallbackAPIVersion.VERSION2
)

cliente.on_connect = ao_conectar
cliente.on_message = ao_receber

try:
    cliente.connect(BROKER, PORTA, 60)
    cliente.loop_start()
    print("Conexão MQTT iniciada!")

except Exception as erro:
    print("Erro ao conectar ao MQTT:", erro)


if __name__ == "__main__":
    print("Servidor iniciado!")
    print("Dashboard: http://127.0.0.1:5000")

    app.run(
        host="127.0.0.1",
        port=5000,
        debug=False
    )
