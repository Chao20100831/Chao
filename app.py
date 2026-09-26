from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__)
CORS(app) # 允许跨域，前端网页可以访问后端

# 数据库连接
def get_db_conn():
    return psycopg2.connect(os.getenv("DATABASE_URL"))

# 示例接口：发送验证码接口
@app.route('/send-code', methods=['POST'])
def send_code():
    data = request.get_json()
    phone = data.get("phone")
    return jsonify({"msg":"验证码已发送","phone":phone})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 3000)))
