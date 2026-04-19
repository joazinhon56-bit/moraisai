import os
import urllib.parse
import requests # NOVO: Precisamos disto para a API do Hugging Face
import io # NOVO: Para lidar com a imagem gerada
import base64 # NOVO: Para converter a imagem para mostrar no site
from flask import Flask, render_template, request, jsonify
from groq import Groq

app = Flask(__name__)

# --- CONFIGURAÇÃO HUGGING FACE (NOVO) ---
# Copia o teu token do Hugging Face e cola-o aqui!
# --- CONFIGURAÇÃO HUGGING FACE (NOVO) ---
HF_TOKEN = os.environ.get("HF_TOKEN")

# URL de um modelo de imagem potente e gratuito (Stable Diffusion XL)
# Se este estiver lento, podes tentar "black-forest-labs/FLUX.1-dev" (mas este pode ser mais lento a acordar)
API_URL = "https://api-inference.huggingface.co/models/stabilityai/stable-diffusion-xl-base-1.0"
headers = {"Authorization": f"Bearer {HF_TOKEN}"}

# Função dedicada para gerar a imagem de alta qualidade
def gerar_imagem_inteligente(tema):
    try:
        # Criamos um "Prompt Rico" para ajudar a IA a desenhar melhor
        # Ex: Se o tema for "camelo", o prompt fica:
        # "An ultra-realistic, highly detailed photograph of a camelo, cinematic lighting, 8k resolution, photorealistic masterpiece."
        prompt_rico = f"An ultra-realistic, highly detailed photograph of a {tema}, cinematic lighting, 8k resolution, photorealistic masterpiece, no text, no watermark."
        
        payload = {"inputs": prompt_rico, "options": {"wait_for_model": True}}
        response = requests.post(API_URL, headers=headers, json=payload)
        
        # Se a API der erro (ex: modelo a acordar), lançamos uma exceção
        response.raise_for_status()
        
        # Convertemos a imagem binária recebida para Base64 para mostrar no HTML
        image_bytes = response.content
        encoded_image = base64.b64encode(image_bytes).decode('utf-8')
        return f"data:image/jpeg;base64,{encoded_image}"
        
    except Exception as e:
        print(f"Erro ao gerar imagem no HF: {e}")
        return None


@app.route('/')
def index():
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    try:
        dados = request.json
        pergunta = dados.get('msg', '')
        imagem_b64 = dados.get('image')

        # --- LÓGICA INTELIGENTE DE IMAGENS (ATUALIZADA) ---
        texto_min = pergunta.lower()
        
        gatilhos_imagem = [
            "gera uma imagem", "gerar uma imagem", "gera imagem", "gera-me uma",
            "cria uma imagem", "criar uma imagem", "cria imagem", "cria-me uma",
            "desenha", "desenhar", "faz um desenho", "fazer um desenho",
            "faz uma imagem", "fazer uma imagem", "faz uma foto", "faz-me um desenho",
            "quero uma imagem", "quero um desenho", "gostaria de uma imagem",
            "podes desenhar", "podes gerar", "podes criar", "imagina"
        ]

        if any(gatilho in texto_min for gatilho in gatilhos_imagem):
            
            prompt_imagem = texto_min
            for gatilho in gatilhos_imagem:
                prompt_imagem = prompt_imagem.replace(gatilho, "")
            prompt_imagem = prompt_imagem.replace(" de ", " ").replace(" um ", " ").replace(" uma ", " ").strip()
            
            if not prompt_imagem:
                prompt_imagem = "arte abstrata colorida"
            
            # --- NOVA CHAMADA À IA INTELIGENTE ---
            appendUI_ia('A desenhar a tua imagem... Isto pode demorar uns segundos.', 'ia', 'loading_img') # Mensagem de espera
            
            url_imagem_final = gerar_imagem_inteligente(prompt_imagem)
            
            # Removemos a mensagem de espera
            # (Isto precisa de ser feito no index.html, mas para simplificar o app.py, 
            # vamos apenas devolver a resposta final que o index.html vai renderizar)

            if url_imagem_final:
                resposta = f"🎨 Aqui está o {prompt_imagem} que pediste à IA inteligente:\n<br><img src='{url_imagem_final}' style='max-width: 100%; border-radius: 12px; margin-top: 10px; border: 1px solid #444;'>"
            else:
                # Se o Hugging Face falhar (ex: por limite de taxa), voltamos ao Pollinations como backup rápido
                prompt_encoded = urllib.parse.quote(prompt_imagem)
                url_backup = f"https://image.pollinations.ai/prompt/{prompt_encoded}?width=800&height=600&nologo=true"
                resposta = f"⚠️ A IA inteligente estava ocupada, mas pedi a um assistente rápido para desenhar isto (pode não ser perfeito):\n<br><img src='{url_backup}' style='max-width: 100%; border-radius: 12px; margin-top: 10px; border: 1px solid #444;'>"
                
            return jsonify({"resposta": resposta})


        # --- LÓGICA NORMAL (CONVERSA E LEITURA FOTOS) - SEM ALTERAÇÕES ---
        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            return jsonify({"resposta": "Erro: Configura a GROQ_API_KEY no Render."})

        client = Groq(api_key=api_key)

        system_prompt = (
            "És o Morais AI. Responde sempre de forma extremamente organizada. "
            "Usa parágrafos curtos, listas com marcas (bullet points) e negrito em títulos ou palavras-chave. "
            "Nunca envies blocos de texto compactos ou confusos."
        )

        if imagem_b64:
            # Modelo de Visão (llama-3.2-11b-vision-preview) - Corrigido
            modelo = "llama-3.2-11b-vision-preview"
            conteudo = []
            if pergunta:
                conteudo.append({"type": "text", "text": pergunta})
            else:
                conteudo.append({"type": "text", "text": "Descreve o que vês nesta imagem."})
            conteudo.append({"type": "image_url", "image_url": {"url": imagem_b64}})
        else:
            # Modelo de Texto super rápido
            modelo = "llama-3.1-8b-instant"
            conteudo = pergunta

        completion = client.chat.completions.create(
            model=modelo,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": conteudo}
            ]
        )

        resposta_ia = completion.choices[0].message.content
        return jsonify({"resposta": resposta_ia})

    except Exception as e:
        print(f"Erro no chat: {e}")
        return jsonify({"resposta": f"Ops, ocorreu um erro na IA: {str(e)}"})


# Função auxiliar para enviar mensagens de espera (precisa de ser adaptada no index.html)
def appendUI_ia(t, type, id=''):
    # Esta função no app.py não faz nada diretamente no browser, 
    # a lógica de loading deve estar no index.html. Removi para evitar confusão.
    pass

@app.route('/googleacfc2899a70cedc3.html')
def google_verification():
    return "google-site-verification: googleacfc2899a70cedc3.html"

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)