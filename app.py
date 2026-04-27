from flask import Flask, render_template, request, jsonify
import openai
import os
from pypdf import PdfReader
from urllib.parse import quote
import os

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
        "recepção",
        "recepcao",
        "atendente",
        "humano",
        "pessoa",
        "falar com alguém",
        "falar com alguem",
        "quero falar com alguém",
        "quero falar com alguem",
        "quero falar com a recepção",
        "quero falar com a recepcao",
        "encaminhe",
        "transferir",
        "transferência",
        "transferencia"
    ]

    for termo in gatilhos:
        if termo in mensagem:
            return True

    return False


def ia_pediu_transferencia(resposta_ia):
    if not resposta_ia:
        return False

    resposta_ia = resposta_ia.lower()

    gatilhos = [
        "vou encaminhar",
        "posso encaminhar",
        "encaminhar você para a recepção",
        "encaminhar voce para a recepcao",
        "encaminhar para a recepção",
        "encaminhar para a recepcao",
        "transferir para a recepção",
        "transferir para a recepcao",
        "vou te transferir",
        "vou transferir você",
        "vou transferir voce",
        "falar com a recepção",
        "falar com a recepcao"
    ]

    for termo in gatilhos:
        if termo in resposta_ia:
            return True

    return False


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

    if not texto_pdf:
        return jsonify({
            "resposta": "Não consegui ler o PDF da clínica. Verifique se o arquivo está na pasta correta.",
            "transferir": False
        })

    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Você é um assistente virtual da clínica Caviver. Seja claro, educado e objetivo."},
                {"role": "user", "content": mensagem}
            ]
        )

        resposta = response["choices"][0]["message"]["content"]

Você é um assistente virtual da clínica Caviver.

Regras:
- Responda com educação, clareza e objetividade.
- Use somente as informações da base de conhecimento fornecida.
- Se a informação não estiver na base, diga:
  "Não encontrei essa informação no momento. Posso encaminhar você para a recepção."
- Se a pessoa quiser falar com humano, atendente, recepção ou alguém da equipe, diga claramente que vai encaminhar para a recepção.
- Se a pessoa quiser agendar, oriente com educação.
- Quando for caso de encaminhamento, use frases claras como:
  "Vou encaminhar você para a recepção."
""",
            input=f"""
BASE DE CONHECIMENTO DA CLÍNICA:
{texto_pdf}

PERGUNTA DO PACIENTE:
{mensagem}
"""
        )

        resposta = response.output_text

        if not resposta:
            resposta = "Não consegui gerar resposta."

        precisa_transferir = ia_pediu_transferencia(resposta)

        if precisa_transferir:
            return jsonify({
                "resposta": resposta,
                "transferir": True,
                "link_whatsapp": gerar_link_whatsapp(WHATSAPP_RECEPCAO, mensagem_whatsapp)
            })

        return jsonify({
            "resposta": resposta,
            "transferir": False
        })

    except Exception as e:
        erro = str(e)
        print("ERRO:", erro)
        return jsonify({
            "resposta": f"Erro ao usar a IA: {erro}",
            "transferir": False
        })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)