from flask import Flask, request, jsonify
import requests
import os
import base64
import logging
from PIL import Image  # ← ДОБАВИТЬ ЭТО
import io              # ← ДОБАВИТЬ ЭТО

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

app = Flask(__name__)

# Конфигурация
TELEGRAM_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY')

# ↓ ДОБАВИТЬ ЭТУ ФУНКЦИЮ ПРЯМО ЗДЕСЬ ↓
def resize_image(image_bytes, max_size=(800, 800)):
    """Уменьшаем размер изображения"""
    try:
        # Открываем изображение
        image = Image.open(io.BytesIO(image_bytes))
        
        # Уменьшаем размер
        image.thumbnail(max_size, Image.Resampling.LANCZOS)
        
        # Конвертируем обратно в bytes
        output = io.BytesIO()
        image.save(output, format='JPEG', quality=85, optimize=True)
        
        logging.info(f"📐 Image resized: {len(image_bytes)} -> {len(output.getvalue())} bytes")
        return output.getvalue()
        
    except Exception as e:
        logging.error(f"❌ Image resize error: {e}")
        return image_bytes  # Возвращаем оригинал если ошибка

def download_telegram_file(file_id):
    """Скачиваем файл из Telegram"""
    try:
        logging.info(f"📥 Downloading file: {file_id}")
        
        # 1. Получаем file_path
        file_info_url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getFile"
        file_info_response = requests.post(file_info_url, json={"file_id": file_id})
        file_info = file_info_response.json()
        
        if not file_info['ok']:
            logging.error(f"❌ File info error: {file_info}")
            return None
            
        file_path = file_info['result']['file_path']
        logging.info(f"📁 File path: {file_path}")
        
        # 2. Скачиваем файл
        file_url = f"https://api.telegram.org/file/bot{TELEGRAM_TOKEN}/{file_path}"
        file_response = requests.get(file_url)
        
        if file_response.status_code == 200:
            logging.info(f"✅ File downloaded, size: {len(file_response.content)} bytes")
            return file_response.content
        else:
            logging.error(f"❌ Download failed: {file_response.status_code}")
            return None
            
    except Exception as e:
        logging.error(f"❌ Download error: {e}")
        return None

def process_with_deepseek(image_bytes):
    """Отправляем фото в DeepSeek API"""
    try:
        logging.info("🔄 Sending to DeepSeek API...")
        
        # Кодируем в base64
        base64_image = base64.b64encode(image_bytes).decode('utf-8')
        
        # ВАЖНО: Используем другой формат - только текстовый промпт с ссылкой
        response = requests.post(
            'https://api.deepseek.com/chat/completions',
            headers={'Authorization': f'Bearer {DEEPSEEK_API_KEY}'},
            json={
                'model': 'deepseek-chat',
                'messages': [{
                    'role': 'user',
                    'content': f'Распознай документ на этом изображении: data:image/jpeg;base64,{base64_image} и верни ТОЛЬКО JSON: {{"участок":"значение","изделие":"значение","номер":"значение","дата":"значение"}}. Если поле не найдено - null.'
                }],
                'temperature': 0.1,
                'max_tokens': 1000
            }
        )
        
        if response.status_code == 200:
            result = response.json()
            logging.info(f"✅ DeepSeek response received")
            
            if 'choices' in result and len(result['choices']) > 0:
                message_content = result['choices'][0]['message']['content']
                logging.info(f"📄 DeepSeek content: {message_content}")
                return message_content
            
        logging.error(f"❌ DeepSeek API error: {response.status_code} - {response.text}")
        return None
            
    except Exception as e:
        logging.error(f"❌ DeepSeek processing error: {e}")
        return None

def send_telegram_message(chat_id, text):
    """Отправляем сообщение обратно в Telegram"""
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        payload = {
            'chat_id': chat_id,
            'text': text
        }
        response = requests.post(url, json=payload)
        return response.json()
    except Exception as e:
        logging.error(f"❌ Telegram send error: {e}")
        return None

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        logging.info("🔔 WEBHOOK CALLED!")
        data = request.json
        
        if 'message' in data:
            chat_id = data['message']['chat']['id']
            user_name = data['message']['from'].get('first_name', 'User')
            
            if 'photo' in data['message']:
                logging.info(f"🖼️ Photo from {user_name}")
                
                # Получаем file_id самого большого фото
                photo = data['message']['photo'][-1]
                file_id = photo['file_id']
                logging.info(f"📸 File ID: {file_id}")
                
                # Скачиваем фото
                image_data = download_telegram_file(file_id)
                if image_data:
                    # Отправляем в DeepSeek
                    deepseek_result = process_with_deepseek(image_data)
                    
                    if deepseek_result:
                        # Отправляем результат пользователю
                        send_telegram_message(chat_id, f"✅ Документ распознан:\n{deepseek_result}")
                        return jsonify({"status": "success", "message": "Фото обработано"})
                    else:
                        send_telegram_message(chat_id, "❌ Ошибка распознавания документа")
                        return jsonify({"status": "error", "message": "DeepSeek processing failed"})
                else:
                    send_telegram_message(chat_id, "❌ Не удалось загрузить фото")
                    return jsonify({"status": "error", "message": "File download failed"})
            else:
                text = data['message'].get('text', '')
                logging.info(f"💬 Text from {user_name}: {text}")
                send_telegram_message(chat_id, f"📝 Вы написали: {text}\nОтправьте фото документа для распознавания.")
                return jsonify({"status": "success", "message": "Text processed"})
        
        return jsonify({"status": "success"})
        
    except Exception as e:
        logging.error(f"❌ Webhook error: {e}")
        return jsonify({"status": "error"}), 200

@app.route('/health', methods=['GET'])
def health():
    return jsonify({
        "status": "running", 
        "message": "🚀 Telegram Bot is running!",
        "version": "1.0"
    })

@app.route('/')
def home():
    return '''
    <h1>🤖 Telegram Document Recognition Bot</h1>
    <p>Сервер работает корректно!</p>
    <ul>
        <li><a href="/health">Health Check</a></li>
        <li>Webhook: POST /webhook</li>
    </ul>
    '''

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)
