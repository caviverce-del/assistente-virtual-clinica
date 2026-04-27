from flask import Flask, render_template, request, jsonify
import openai
import os
from pypdf import PdfReader
from urllib.parse import quote

app = Flask(__name__)

openai.api_key = os.getenv("OPENAI_API_KEY")

PDF_PATH = "Institucional_Caviver.pdf"
WHATSAPP_RECEPCAO = "5585996046227"


def carregar_texto_pdf(caminho_pdf):
    try:
        reader = PdfReader(caminho_pdf)
        texto_completo = ""

        for pagina in reader.pages:
            texto_pagina = pagina.extract_text()
            if texto_pagina:
                texto_completo += texto_pagina + "\n"

        return texto_completo.strip()

    except Exception as e:
        print("ERRO AO LER PDF:", e)
        return ""


def paciente_quer_recepcao(mensagem):
    mensagem = mensagem.lower()

    gatilhos = [
        "recepção","recepcao","atendente","humano","pessoa",
        "falar com alguém","falar com alguem",
        "quero falar com alguém","quero falar com alguem",
        "quero falar com a recepção","quero falar com a recepcao",
        "encaminhe","transferir","transferência","transferencia"
    ]

    return any(termo in mensagem for termo in gatilhos)


def gerar_link_whatsapp(numero, mensagem):
    mensagem_codificada = quote(mensagem)
    return f"https://wa.me/{numero}?text={mensagem_codificada}"


texto_pdf = carregar_texto_pdf(PDF_PATH)


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json()
    mensagem = data.get("mensagem", "").strip()

    if not mensagem:
        return jsonify({"resposta": "Você não digitou nenhuma mensagem.", "transferir": False})

    mensagem_whatsapp = f"Olá, vim do assistente virtual.\n\nMensagem do paciente: {mensagem}"

    if paciente_quer_recepcao(mensagem):
        return jsonify({
            "resposta": "Claro. Vou te encaminhar para a recepção.",
            "transferir": True,
            "link_whatsapp": gerar_link_whatsapp(WHATSAPP_RECEPCAO, mensagem_whatsapp)
        })

    try:
        prompt = f"""
Você é um assistente virtual da clínica Caviver.

Use as informações abaixo para responder:

{texto_pdf}

Pergunta do paciente:
{mensagem}
"""

        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Seja claro, educado e objetivo."},
                {"role": "user", "content": prompt}
            ]
        )

        resposta = response["choices"][0]["message"]["content"]

        return jsonify({
            "resposta": resposta,
            "transferir": False
        })

    except Exception as e:
        print("ERRO:", e)
        return jsonify({
            "resposta": f"Erro ao usar a IA: {str(e)}",
            "transferir": False
        })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)