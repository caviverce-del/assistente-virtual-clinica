from flask import Flask, render_template, request, jsonify
import openai
import os
from pypdf import PdfReader
from urllib.parse import quote

app = Flask(__name__)

openai.api_key = os.getenv("OPENAI_API_KEY")

PDF_PATH = "Institucional_Caviver.pdf"

WHATSAPP_RECEPCAO = "5585982035619"
LINK_AGENDAMENTO_ONLINE = "https://visaosolidaria.agende.ai"


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
        "recepção", "recepcao", "atendente", "humano", "pessoa",
        "falar com alguém", "falar com alguem",
        "quero falar com alguém", "quero falar com alguem",
        "encaminhe", "transferir"
    ]

    return any(t in mensagem for t in gatilhos)


def paciente_quer_agendamento(mensagem):
    mensagem = mensagem.lower()

    gatilhos = [
        "agendamento", "agendar", "marcar", "consulta",
        "marcar consulta", "agendar consulta",
        "quero marcar", "quero agendar",
        "como faço para agendar", "como agendar"
    ]

    return any(t in mensagem for t in gatilhos)


def gerar_link_whatsapp(numero, mensagem):
    return f"https://wa.me/{numero}?text={quote(mensagem)}"


texto_pdf = carregar_texto_pdf(PDF_PATH)


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json()
    mensagem = data.get("mensagem", "").strip()

    if not mensagem:
        return jsonify({"resposta": "Digite uma mensagem.", "transferir": False})

    mensagem_whatsapp = f"Olá, gostaria de tirar dúvidas sobre o Caviver.\n\nMensagem: {mensagem}"
    link_recepcao = gerar_link_whatsapp(WHATSAPP_RECEPCAO, mensagem_whatsapp)

    if paciente_quer_agendamento(mensagem):
        resposta_agendamento = f"""Você prefere falar com uma atendente ou realizar o agendamento online?

👉 Agendamento online:
{LINK_AGENDAMENTO_ONLINE}

👉 Falar com atendente:
{link_recepcao}"""

        return jsonify({
            "resposta": resposta_agendamento,
            "transferir": False,
            "link_whatsapp": link_recepcao
        })

    if paciente_quer_recepcao(mensagem):
        return jsonify({
            "resposta": f"Claro. Você pode falar com uma atendente pelo link abaixo:\n\n{link_recepcao}",
            "transferir": True,
            "link_whatsapp": link_recepcao
        })

    try:
        prompt = f"""
Você é um assistente virtual da clínica Caviver.

Regras importantes:
1. Responda sempre de forma educada, clara, objetiva e profissional.
2. Use as informações da base de conhecimento abaixo.
3. Não invente informações.
4. Se não souber responder, oriente a pessoa a falar com a recepção.
5. Sempre que o usuário perguntar sobre agendamento, marcar consulta ou consulta, responda obrigatoriamente perguntando se ele prefere falar com uma atendente ou realizar o agendamento online.

Regra obrigatória de agendamento:
Se a pergunta envolver agendamento, consulta ou marcar consulta, responda exatamente com as opções:

Você prefere falar com uma atendente ou realizar o agendamento online?

👉 Agendamento online:
{LINK_AGENDAMENTO_ONLINE}

👉 Falar com atendente:
{link_recepcao}

Base de conhecimento:
{texto_pdf}

Pergunta do usuário:
{mensagem}
"""

        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system",
                    "content": "Você é um assistente virtual da clínica Caviver. Seja claro, educado e não invente informações."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        )

        resposta = response["choices"][0]["message"]["content"]

        return jsonify({
            "resposta": resposta,
            "transferir": False
        })

    except Exception as e:
        return jsonify({
            "resposta": f"Erro: {str(e)}",
            "transferir": False
        })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)