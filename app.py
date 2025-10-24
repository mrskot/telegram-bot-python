from flask import Flask, request, jsonify
import requests
import os
import base64

app = Flask(__name__)

# Конфигурация
DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY', 'sk-8f3a7976db454796890e1fb2c4c38553')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
if not TELEGRAM_TOKEN:
    print("❌ TELEGRAM_BOT_TOKEN not set!")

@app.route('/webhook', methods=['POST'])
def webhook():
    """Основной webhook для Telegram"""
    try:
        data = request.json
        print("📨 Received Telegram update")
        
        # Проверяем есть ли фото
        if 'message' in data and 'photo' in data['message']:
            return jsonify({
                "status": "success", 
                "message": "Фото получено! Обработка будет добавлена."
            })
        else:
            return jsonify({
                "status": "success", 
                "message": "Сообщение получено (не фото)"
            })
            
    except Exception as e:
        print("❌ Error:", e)
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
