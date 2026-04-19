import os
import urllib.parse
import requests
import base64
from flask import Flask, render_template, request, jsonify
from groq import Groq

app = Flask(__name__)

# --- CONFIGURAÇÕES DE AMBIENTE ---
# Estas chaves devem estar configuradas no painel do Render (Environment Variables)
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
HF_TOKEN = os.environ.get("HF_TOKEN")

# URL do modelo de geração de imagem profissional (Hugging Face)
HF_API_URL = "https://api-inference.huggingface.co/models/stabilityai/stable-diffusion-xl-base-1.0"

def gerar_imagem_ia(tema):
    """Envia o pedido para a IA do Hugging Face e devolve a imagem em Base64."""
    try:
        if not HF_TOKEN:
            return None
        
        # Prompt 'rico' para forçar a IA a desenhar com qualidade máxima
        prompt_rico = f"An ultra-realistic, highly detailed photograph of {tema}, cinematic lighting, 8k resolution, photorealistic masterpiece, no text, no watermark."
        
        headers = {"Authorization": f"Bearer {HF_TOKEN}"}
        payload = {"inputs": prompt_rico, "options": {"wait_for_model": True}}
        
        response = requests.post(HF_API_URL, headers=headers, json=payload)
        response.raise_for_status() # Verifica se houve erro na API
        
        # Converte os bytes da imagem para uma string que o navegador entende
        encoded_image = base64.b64encode(response.content).decode('utf-8')
        return f"data:image/jpeg;base64,{encoded_image}"
    except Exception as e:
        print(f"Erro na geração de imagem (HF): {e}")
        return None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    try:
        if not GROQ_API_KEY:
            return jsonify({"resposta": "Erro: GROQ_API_KEY não configurada no Render."})

        client = Groq(api_key=GROQ_API_KEY)
        dados = request.json
        pergunta = dados.get('msg', '')
        imagem_b64 = dados.get('image')

        texto_min = pergunta.lower()

        # --- 1. LÓGICA DE GERAÇÃO DE IMAGENS ---
        gatilhos_imagem = [
            "gera uma imagem", "gerar uma imagem", "gera imagem", "cria uma imagem", 
            "criar uma imagem", "cria imagem", "desenha", "desenhar", "faz um desenho",
            "podes desenhar", "imagina", "faz-me um"
        ]

        if any(gatilho in texto_min for gatilho in gatilhos_imagem):
            # Limpa o pedido para focar apenas no tema
            prompt_limpo = texto_min
            for g in gatilhos_imagem:
                prompt_limpo = prompt_limpo.replace(g, "")
            prompt_limpo = prompt_limpo.replace(" de ", " ").replace(" um ", " ").replace(" uma ", " ").strip()
            
            if not prompt_limpo: prompt_limpo = "uma paisagem futurista"
            
            # Tenta gerar com a IA de alta qualidade (Hugging Face)
            url_img = gerar_imagem_ia(prompt_limpo)
            
            if url_img:
                return jsonify({
                    "resposta": f"🎨 Aqui está a imagem de **{prompt_limpo}** que criei para ti:<br><img src='{url_img}' style='max-width:100%; border-radius:12px; margin-top:10px; border:1px solid #444;'>"
                })
            else:
                # Backup rápido (Pollinations) se a IA principal falhar ou estiver ocupada
                prompt_enc = urllib.parse.quote(prompt_limpo)
                url_backup = f"https://image.pollinations.ai/prompt/{prompt_enc}?width=800&height=600&nologo=true"
                return jsonify({
                    "resposta": f"⚠️ A IA principal está ocupada, mas aqui tens um esboço rápido:<br><img src='{url_backup}' style='max-width:100%; border-radius:12px; margin-top:10px; border:1px solid #444;'>"
                })

        # --- 2. LÓGICA DE CONVERSA (TEXTO E VISÃO) ---
        system_prompt = (
            "És o Morais AI. Responde sempre de forma extremamente organizada: "
            "usa parágrafos curtos, listas com marcas (bullet points) e negrito em palavras-chave. "
            "Sê profissional, prestável e nunca envies blocos de texto compactos."
        )

        if imagem_b64:
            # Usamos o modelo de VISÃO para analisar a foto
            modelo = "llama-3.2-11b-vision-preview"
            conteudo = [
                {"type": "text", "text": pergunta or "O que vês nesta imagem?"},
                {"type": "image_url", "image_url": {"url": imagem_b64}}
            ]
        else:
            # Usamos o modelo de TEXTO normal
            modelo = "llama-3.1-8b-instant"
            conteudo = pergunta

        completion = client.chat.completions.create(
            model=modelo,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": conteudo}
            ]
        )

        return jsonify({"resposta": completion.choices[0].message.content})

    except Exception as e:
        print(f"Erro no Servidor: {e}")
        return jsonify({"resposta": f"Ops! Ocorreu um erro técnico: {str(e)}"})

@app.route('/googleacfc2899a70cedc3.html')
def google_verification():
    return "google-site-verification: googleacfc2899a70cedc3.html"

if __name__ == '__main__':
    # O Render fornece a porta automaticamente através da variável de ambiente PORT
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)