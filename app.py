from flask import Flask, render_template, request, jsonify
import os
from pypdf import PdfReader
from urllib.parse import quote
from openai import OpenAI

app = Flask(__name__)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

PDF_PATH = "Institucional_Caviver.pdf"

WHATSAPP_ATENDENTE = "5585982035619"
LINK_AGENDAMENTO_ONLINE = "https://visaosolidaria.agende.ai"

# Memória simples da conversa
conversas = {}


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


texto_pdf = carregar_texto_pdf(PDF_PATH)


def gerar_link_whatsapp(numero, mensagem):
    return f"https://wa.me/{numero}?text={quote(mensagem)}"


def normalizar(mensagem):
    return mensagem.lower().strip()


def obter_id_usuario(data):
    return (
        data.get("telefone")
        or data.get("phone")
        or data.get("numero")
        or data.get("user_id")
        or "usuario_teste"
    )


def contem_alguma(mensagem, palavras):
    mensagem = normalizar(mensagem)
    return any(p in mensagem for p in palavras)


def paciente_saudacao(mensagem):
    return normalizar(mensagem) in [
        "oi", "olá", "ola", "bom dia", "boa tarde", "boa noite",
        "e aí", "eai", "opa"
    ]


def paciente_quer_atendente(mensagem):
    gatilhos = [
        "atendente", "humano", "pessoa", "recepção", "recepcao",
        "falar com alguém", "falar com alguem",
        "falar com atendente", "quero atendente",
        "me chama", "me liga", "telefone", "whatsapp",
        "tirar dúvidas", "tirar duvidas"
    ]
    return contem_alguma(mensagem, gatilhos)


def paciente_quer_agendamento(mensagem):
    gatilhos = [
        "agendar", "marcar", "consulta", "quero consulta",
        "quero agendar", "quero marcar", "agendamento",
        "link", "horário", "horario", "atendimento",
        "oftalmologista", "exame de vista"
    ]
    return contem_alguma(mensagem, gatilhos)


def paciente_tem_urgencia(mensagem):
    gatilhos = [
        "perdi a visão", "perdi a visao", "perda de visão", "perda de visao",
        "dor forte", "dor intensa", "trauma", "bati o olho",
        "sangrando", "não estou enxergando", "nao estou enxergando",
        "urgência", "urgencia", "emergência", "emergencia",
        "consulta urgente", "urgente"
    ]
    return contem_alguma(mensagem, gatilhos)


def resposta_inicial():
    return """Olá! 👋 Seja bem-vindo ao CAVIVER.

Como posso te ajudar hoje?

Você pode me dizer, por exemplo:
• Quero agendar uma consulta
• Quero falar com atendente
• Quero saber sobre exames
• Quero saber sobre consultas"""


def resposta_pedir_nome():
    return """Claro 😊
Vou te ajudar com o agendamento.

Qual é o nome do paciente?"""


def resposta_agendamento(nome, link_atendente):
    if nome:
        saudacao = f"Perfeito, {nome} 😊"
    else:
        saudacao = "Perfeito 😊"

    return f"""{saudacao}

Para fazer seu agendamento, clique no link abaixo e escolha o melhor dia e horário:

{LINK_AGENDAMENTO_ONLINE}

Se preferir, também pode falar com uma atendente:
{link_atendente}"""


def resposta_atendente(link_atendente):
    return f"""Claro 😊

Você pode falar com uma atendente pelo link abaixo:

{link_atendente}"""


def resposta_urgencia(link_atendente):
    return f"""Sinto muito por isso.

Em caso de dor forte, perda súbita de visão, trauma no olho ou piora rápida, procure falar com atendente imediatamente.

{link_atendente}"""


def resposta_confirmacao_agendamento(nome):
    if nome:
        return f"""Que bom, {nome}! 😊

Agendamento realizado com sucesso.

No dia marcado, compareça com seus documentos pessoais."""
    
    return """Que bom! 😊

Agendamento realizado com sucesso.

No dia marcado, compareça com seus documentos pessoais."""


def parece_nome(mensagem):
    msg = mensagem.strip()

    if len(msg) < 2:
        return False

    bloqueios = [
        "agendar", "consulta", "atendente", "exame", "valor",
        "preço", "preco", "horário", "horario", "link",
        "sim", "não", "nao", "quero"
    ]

    if contem_alguma(msg, bloqueios):
        return False

    return True


def gerar_resposta_ia(mensagem, nome, link_atendente):
    nome_texto = nome if nome else "paciente"

    prompt = f"""
Você é o assistente virtual do Visão Solidária/CAVIVER.

Seu papel não é apenas responder.
Seu papel é conduzir o paciente até a solução com mensagens curtas, humanas e objetivas.

Contexto:
O paciente se chama: {nome_texto}

Regras principais:
Você é o assistente virtual do Visão Solidária/CAVIVER.

Seu papel não é apenas responder.
Seu papel é conduzir o paciente até a solução com mensagens curtas, humanas e objetivas.

Regras principais:
- Nunca envie mensagens longas.
- Nunca dê muitas opções ao mesmo tempo.
- Sempre termine com uma pergunta simples ou uma próxima ação clara.
- Use linguagem natural, acolhedora e profissional.
- Não pare a conversa sem orientar o próximo passo.
- Nunca dê diagnóstico médico.
- Se o paciente quiser agendar, peça apenas o nome.
- Depois do nome, envie diretamente o link de agendamento online e a opção de falar com atendente.
- Não peça CPF, endereço, data de nascimento ou telefone. Esses dados serão preenchidos no agendamento online.
- Se o paciente demonstrar dúvida, explique de forma simples e depois conduza.
- Se o paciente perguntar valor, diga que o valor da consulta é R$150,00 e os valores dos exames podem variar conforme o exame.
- Se o paciente pedir atendente, envie o link da atendente.
- Se não souber responder, diga que uma atendente pode ajudar.
- Se houver urgência médica, oriente falar com a atendente imediatamente.

Formato das respostas:
- Máximo de 4 linhas.
- Tom humano.
- Sem parecer robô.
- Sempre guiando o paciente.


Links importantes:
Agendamento online: {LINK_AGENDAMENTO_ONLINE}
Atendente: {link_atendente}

Base de conhecimento:
{texto_pdf}

Mensagem do paciente:
{mensagem}
"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": "Você é o assistente virtual do Visão Solidária/CAVIVER. Seja humano, curto, claro, acolhedor e sempre guie o paciente."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0.5
    )

    return response.choices[0].message.content.strip()


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/chat", methods=["POST"])
def chat():
    try:
        data = request.get_json()
        mensagem = data.get("mensagem", "").strip()

        if not mensagem:
            return jsonify({
                "resposta": "Digite uma mensagem para eu te ajudar 😊",
                "transferir": False
            })

        user_id = obter_id_usuario(data)

        if user_id not in conversas:
            conversas[user_id] = {
                "etapa": "inicio",
                "nome": "",
                "intencao": ""
            }

        conversa = conversas[user_id]

        mensagem_atendente = f"""Olá, gostaria de atendimento pelo Visão Solidária.

Mensagem do paciente:
{mensagem}"""

        link_atendente = gerar_link_whatsapp(
            WHATSAPP_ATENDENTE,
            mensagem_atendente
        )

        msg = normalizar(mensagem)

        # Confirmação de agendamento
        if msg in ["agendei", "já agendei", "ja agendei", "consegui", "marquei", "finalizei"]:
            conversa["etapa"] = "finalizado"
            return jsonify({
                "resposta": resposta_confirmacao_agendamento(conversa.get("nome")),
                "transferir": False
            })

        # Urgência
        if paciente_tem_urgencia(mensagem):
            conversa["etapa"] = "urgencia"
            return jsonify({
                "resposta": resposta_urgencia(link_atendente),
                "transferir": True,
                "link_whatsapp": link_atendente
            })

        # Saudação inicial
        if paciente_saudacao(mensagem) and conversa["etapa"] == "inicio":
            return jsonify({
                "resposta": resposta_inicial(),
                "transferir": False
            })

        # Atendente
        if paciente_quer_atendente(mensagem):
            conversa["etapa"] = "atendente"
            return jsonify({
                "resposta": resposta_atendente(link_atendente),
                "transferir": True,
                "link_whatsapp": link_atendente
            })

        # Pedido claro de agendamento
        if paciente_quer_agendamento(mensagem) and conversa["etapa"] in ["inicio", "duvida", "finalizado"]:
            conversa["etapa"] = "aguardando_nome"
            conversa["intencao"] = "agendamento"
            return jsonify({
                "resposta": resposta_pedir_nome(),
                "transferir": False
            })

        # Captura do nome
        if conversa["etapa"] == "aguardando_nome":
            if parece_nome(mensagem):
                conversa["nome"] = mensagem.title()
                conversa["etapa"] = "agendamento_enviado"

                return jsonify({
                    "resposta": resposta_agendamento(conversa["nome"], link_atendente),
                    "transferir": False,
                    "link_agendamento": LINK_AGENDAMENTO_ONLINE,
                    "link_whatsapp": link_atendente
                })

            return jsonify({
                "resposta": "Me informe apenas o nome do paciente, por favor 😊",
                "transferir": False
            })

        # Se a pessoa pedir o link depois
        if msg in ["online", "agendamento online", "quero online", "pelo site", "site"]:
            conversa["etapa"] = "agendamento_enviado"
            return jsonify({
                "resposta": resposta_agendamento(conversa.get("nome"), link_atendente),
                "transferir": False,
                "link_agendamento": LINK_AGENDAMENTO_ONLINE
            })

        # Resposta com IA para dúvidas gerais
        resposta = gerar_resposta_ia(
            mensagem=mensagem,
            nome=conversa.get("nome"),
            link_atendente=link_atendente
        )

        conversa["etapa"] = "duvida"

        return jsonify({
            "resposta": resposta,
            "transferir": False
        })

    except Exception as e:
        print("ERRO NO CHAT:", e)

        return jsonify({
            "resposta": "Tive uma instabilidade aqui, mas posso te direcionar para uma atendente 😊",
            "transferir": False
        })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)