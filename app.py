from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import psycopg2
import requests
import hashlib
import json
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__)
CORS(app)

# ========== 数据库连接函数 ==========
def get_db_conn():
    return psycopg2.connect(os.getenv("DATABASE_URL"))

# ========== 【易支通配置，从Railway环境变量读取】 ==========
YZ_MCH_ID = os.getenv("YZ_MCH_ID")       # 易支通商户ID
YZ_MCH_KEY = os.getenv("YZ_MCH_KEY")     # 易支通商户密钥
YZ_API_URL = "这里替换成易支通V2下单接口地址" # 易支通给你的V2网关地址

# V2签名算法（易支通V2通用签名）
def yz_v2_sign(params, mch_key):
    sorted_items = sorted(params.items())
    raw = "".join([f"{k}{v}" for k, v in sorted_items]) + mch_key
    sign = hashlib.md5(raw.encode("utf-8")).hexdigest()
    return sign

# ========== 接口1：创建支付订单，前端调用 ==========
@app.route('/create-order', methods=['POST'])
def create_order():
    data = request.get_json()
    amount = data.get("amount")
    remark = data.get("remark", "麓光队宝马小学助学捐赠")

    # 构造易支通V2请求参数
    order_params = {
        "mch_id": YZ_MCH_ID,
        "out_trade_no": f"LG{os.urandom(4).hex()}", # 生成唯一订单号
        "total_amount": amount,
        "body": "长白山宝马小学助学捐赠",
        "notify_url": "https://chao-production.up.railway.app/pay-notify" # 你的回调地址，改成你自己的Railway域名
    }
    # 生成V2签名
    order_params["sign"] = yz_v2_sign(order_params, YZ_MCH_KEY)
    # 请求易支通
    resp = requests.post(YZ_API_URL, data=order_params)
    res_data = resp.json()

    # 存入数据库订单记录
    conn = get_db_conn()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO orders(out_trade_no, amount, status, remark)
        VALUES (%s, %s, 'pending', %s)
    """, (order_params["out_trade_no"], amount, remark))
    conn.commit()
    cur.close()
    conn.close()

    return jsonify(res_data)

# ========== 接口2：支付回调接口（易支通服务器自动访问） ==========
@app.route('/pay-notify', methods=['POST'])
def pay_notify():
    data = request.form.to_dict()
    # 校验签名
    sign_recv = data.pop("sign")
    sign_calc = yz_v2_sign(data, YZ_MCH_KEY)
    if sign_recv != sign_calc:
        return "sign error",400

    # 校验成功，更新订单状态为已支付
    out_trade_no = data["out_trade_no"]
    trade_status = data["trade_status"]
    conn = get_db_conn()
    cur = conn.cursor()
    if trade_status == "SUCCESS":
        cur.execute("UPDATE orders SET status='success' WHERE out_trade_no=%s",(out_trade_no,))
    conn.commit()
    cur.close()
    conn.close()
    return "success" # 必须返回success字符串给易支通

# ========== 原来的验证码接口（保留，你后续想用可以继续用） ==========
@app.route('/send-code', methods=['POST'])
def send_code():
    data = request.get_json()
    phone = data.get("phone")
    return jsonify({"msg":"验证码已发送","phone":phone})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 3000)))
