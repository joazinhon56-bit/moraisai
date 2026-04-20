import os
import urllib.parse
import requests
import base64
import google.generativeai as genai
from flask import Flask, render_template, request, jsonify, send_from_directory

app = Flask(__name__)

# --- 1. CONFIGURAÇÃO GOOGLE GEMINI ---
GOOGLE_API_KEY = "AIzaSyChjICCd4heMJzGI1i1iggDK1pkGCcX3hE"
genai.configure(api_key=GOOGLE_API_KEY)
# O modelo 1.5-flash é o melhor: rápido, gratuito e vê imagens!
model_gemini = genai.GenerativeModel('gemini-1.5-flash')

# --- 2. CONFIGURAÇÃO GERAÇÃO DE IMAGENS (Hugging Face) ---
HF_TOKEN = os.environ.get("HF_TOKEN")
HF_API_URL = "https://api-inference.huggingface.co/models/stabilityai/stable-diffusion-xl-base-1.0"

def gerar_imagem_ia(tema):
    """Gera uma imagem via Hugging Face."""
    try:
        if not HF_TOKEN:
            return None
        prompt_rico = f"An ultra-realistic photograph of {tema}, cinematic lighting, 8k resolution, photorealistic."
        headers = {"Authorization": f"Bearer {HF_TOKEN}"}
        payload = {"inputs": prompt_rico, "options": {"wait_for_model": True}}
        response = requests.post(HF_API_URL, headers=headers, json=payload)
        response.raise_for_status()
        encoded_image = base64.b64encode(response.content).decode('utf-8')
        return f"data:image/jpeg;base64,{encoded_image}"
    except Exception as e:
        print(f"Erro HF: {e}")
        return None

# --- 3. ROTAS ---

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    try:
        dados = request.json
        pergunta = dados.get('msg', '')
        imagem_b64 = dados.get('image')
        texto_min = pergunta.lower()

        # --- LÓGICA DE GERAÇÃO DE IMAGENS ---
        gatilhos = ["gera uma imagem", "cria uma imagem", "desenha", "faz um desenho"]
        if any(g in texto_min for g in gatilhos):
            prompt_limpo = texto_min
            for g in gatilhos: prompt_limpo = prompt_limpo.replace(g, "")
            url_img = gerar_imagem_ia(prompt_limpo.strip() or "uma paisagem")
            if url_img:
                return jsonify({"resposta": f"🎨 Aqui está:<br><img src='{url_img}' style='max-width:100%; border-radius:12px; margin-top:10px;'>" })

        # --- LÓGICA DE CONVERSA E VISÃO (Gemini) ---
        contents = []
        
        # Se o utilizador enviou uma imagem para análise
        if imagem_b64:
            img_data = imagem_b64.split(",")[1] if "," in imagem_b64 else imagem_b64
            contents.append({
                "inline_data": {
                    "mime_type": "image/png",
                    "data": img_data
                }
            })
        
        # Prompt de personalidade + pergunta
        prompt_final = (
            "És o Morais AI. Responde de forma organizada com negritos e listas. "
            f"Pergunta: {pergunta or 'O que vês nesta imagem?'}"
        )
        contents.append(prompt_final)

        # Resposta do Gemini
        response = model_gemini.generate_content(contents)
        return jsonify({"resposta": response.text})

    except Exception as e:
        print(f"Erro: {e}")
        return jsonify({"resposta": f"Ops! Erro técnico: {str(e)}"})

# --- UTILIDADES ---
@app.route('/googleacfc2899a70cedc3.html')
def google_verification():
    return "google-site-verification: googleacfc2899a70cedc3.html"

@app.route('/manifest.json')
def serve_manifest():
    return send_from_directory('static', 'manifest.json')

@app.route('/sw.js')
def serve_sw():
    return send_from_directory('static', 'sw.js')

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)