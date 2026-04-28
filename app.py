from flask import Flask, render_template, request, jsonify
import openai
import os
from pypdf import PdfReader
from urllib.parse import quote

app = Flask(__name__)

openai.api_key = os.getenv("OPENAI_API_KEY")

PDF_PATH = "Institucional_Caviver.pdf"

WHATSAPP_ATENDENTE = "5585982035619"
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


def paciente_quer_atendente(mensagem):
    mensagem = mensagem.lower()

    gatilhos = [
        "recepção", "recepcao", "atendente", "humano", "pessoa",
        "falar com alguém", "falar com alguem",
        "quero falar com alguém", "quero falar com alguem",
        "falar com atendente", "quero atendente",
        "encaminhe", "transferir", "tirar dúvidas", "tirar duvidas"
    ]

    return any(t in mensagem for t in gatilhos)


def paciente_quer_agendamento(mensagem):
    mensagem = mensagem.lower()

    gatilhos = [
        "agendamento", "agendar", "marcar", "consulta",
        "marcar consulta", "agendar consulta",
        "quero marcar", "quero agendar",
        "como faço para agendar", "como agendar",
        "exame", "atendimento", "oftalmo", "oftalmologista"
    ]

    return any(t in mensagem for t in gatilhos)


def paciente_tem_urgencia(mensagem):
    mensagem = mensagem.lower()

    gatilhos = [
        "perdi a visão", "perdi a visao", "perda de visão", "perda de visao",
        "dor forte", "dor intensa", "trauma", "bati o olho",
        "sangrando", "não estou enxergando", "nao estou enxergando",
        "urgência", "urgencia", "emergência", "emergencia"
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

    mensagem_whatsapp = f"Olá, gostaria de tirar dúvidas sobre o Visão Solidária.\n\nMensagem: {mensagem}"
    link_atendente = gerar_link_whatsapp(WHATSAPP_ATENDENTE, mensagem_whatsapp)

    if paciente_tem_urgencia(mensagem):
        resposta_urgencia = f"""Sinto muito por isso. Em casos de dor forte, perda súbita de visão, trauma no olho ou piora rápida, procure atendimento médico imediatamente.

Se quiser tirar dúvidas sobre o Visão Solidária, você também pode falar com uma atendente:
{link_atendente}"""

        return jsonify({
            "resposta": resposta_urgencia,
            "transferir": True,
            "link_whatsapp": link_atendente
        })

    if paciente_quer_agendamento(mensagem):
        resposta_agendamento = f"""Você prefere fazer o agendamento online ou falar com uma atendente?

👉 Agendamento online:
{LINK_AGENDAMENTO_ONLINE}

👉 Falar com atendente:
{link_atendente}"""

        return jsonify({
            "resposta": resposta_agendamento,
            "transferir": False,
            "link_whatsapp": link_atendente
        })

    if paciente_quer_atendente(mensagem):
        return jsonify({
            "resposta": f"Claro. Você pode falar com uma atendente pelo link abaixo:\n\n{link_atendente}",
            "transferir": True,
            "link_whatsapp": link_atendente
        })

    try:
        prompt = f"""
Você é o assistente virtual do Visão Solidária.

O Visão Solidária é um programa que oferece atendimentos oftalmológicos com valores mais acessíveis.

Seu objetivo:
- Tirar dúvidas dos pacientes.
- Explicar o que é o Visão Solidária.
- Orientar sobre consultas, exames e atendimento oftalmológico.
- Incentivar o agendamento online quando o paciente demonstrar interesse.
- Encaminhar para uma atendente quando necessário.

Tom de voz:
- Educado.
- Acolhedor.
- Simples.
- Profissional.
- Humano.
- Nunca frio ou robótico.

Regras importantes:
1. Responda sempre de forma curta, clara e objetiva.
2. Use as informações da base de conhecimento abaixo.
3. Não invente valores, horários, endereços ou serviços.
4. Se não souber responder, diga que uma atendente pode ajudar.
5. Nunca dê diagnóstico médico.
6. Se o paciente relatar dor forte, perda súbita de visão, trauma no olho ou urgência, oriente procurar atendimento médico imediatamente.
7. Sempre que o paciente perguntar sobre agendamento, consulta, exame, atendimento ou marcar consulta, responda obrigatoriamente perguntando se ele prefere fazer o agendamento online ou falar com uma atendente.

Regra obrigatória de agendamento:
Se a pergunta envolver agendamento, consulta, exame, atendimento ou marcar consulta, responda com estas opções:

Você prefere fazer o agendamento online ou falar com uma atendente?

👉 Agendamento online:
{LINK_AGENDAMENTO_ONLINE}

👉 Falar com atendente:
{link_atendente}

Base de conhecimento:
{texto_pdf}

Pergunta do paciente:
{mensagem}
"""

        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system",
                    "content": "Você é o assistente virtual do Visão Solidária. Seja educado, claro, objetivo e não invente informações."
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