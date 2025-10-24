from flask import Flask, request, jsonify
import requests
import os
import base64
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

app = Flask(__name__)

# Конфигурация
DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY', 'sk-8f3a7976db454796890e1fb2c4c38553')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
if not TELEGRAM_TOKEN:
    print("❌ TELEGRAM_BOT_TOKEN not set!")

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        logging.info("🔔 WEBHOOK CALLED!")
        data = request.json
        logging.info(f"📨 Update ID: {data.get('update_id')}")
        
        # Проверяем токен
        if not TELEGRAM_TOKEN or TELEGRAM_TOKEN == 'xxx':
            logging.error("❌ ERROR: TELEGRAM_TOKEN not configured!")
            return jsonify({"status": "error", "message": "Token not configured"}), 500
            
        if 'message' in data:
            user = data['message'].get('from', {})
            logging.info(f"💬 Message from: {user.get('first_name')} (ID: {user.get('id')})")
            
            if 'photo' in data['message']:
                logging.info("🖼️ Photo received!")
                return jsonify({"status": "success", "message": "Photo received!"})
            else:
                text = data['message'].get('text', '')
                logging.info(f"📝 Text: {text}")
                return jsonify({"status": "success", "message": f"Text received: {text}"})
        
        return jsonify({"status": "success"})
        
    except Exception as e:
        logging.error(f"❌ Error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/health', methods=['GET'])
def health():
    """Проверка работы сервера"""
    return jsonify({
        "status": "running", 
        "message": "🚀 Telegram Bot is running!",
        "version": "1.0"
    })

@app.route('/test', methods=['GET'])
def test():
    """Тестовая страница"""
    return """
    <h1>Telegram Bot</h1>
    <p>Сервер работает корректно!</p>
    <ul>
        <li><a href="/health">Health Check</a></li>
        <li>Webhook: POST /webhook</li>
    </ul>
    """

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)
