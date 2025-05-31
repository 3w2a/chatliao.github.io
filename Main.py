from flask import Flask, render_template_string, request
from flask_socketio import SocketIO, emit
from datetime import datetime
import secrets
from flask_cors import CORS

app = Flask(__name__)
app.config['SECRET_KEY'] = secrets.token_hex(16)
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*", logger=True, engineio_logger=True)

# 存储聊天消息和在线用户
messages = []
online_users = set()

@app.route('/')
def home():
    return """
    <h1>Socket.IO 聊天服务器</h1>
    <p>访问 <a href="/connect">连接页面</a> 开始使用</p>
    <p>WebSocket 地址: <code>ws://{你的IP}:5000</code></p>
    """

@app.route('/connect')
def connect_page():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <meta http-equiv="refresh" content="0; url=connect.html">
    </head>
    <body>
        <p>正在跳转到连接页面...</p>
    </body>
    </html>
    """

@app.route('/chat')
def chat_page():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <meta http-equiv="refresh" content="0; url=chat.html">
    </head>
    <body>
        <p>正在跳转到聊天页面...</p>
    </body>
    </html>
    """

@socketio.on('connect')
def handle_connect():
    client_id = request.sid
    print(f'客户端已连接: {client_id}')
    emit('connect_response', {'status': 'connected', 'sid': client_id})

@socketio.on('disconnect')
def handle_disconnect():
    client_id = request.sid
    print(f'客户端已断开: {client_id}')
    
    # 清理断开连接的用户
    for user in list(online_users):
        if user['sid'] == client_id:
            online_users.remove(user)
            emit('update_users', {'count': len(online_users)}, broadcast=True)
            emit('receive_message', {
                'username': '系统',
                'text': f"{user['username']} 已离开",
                'time': datetime.now().strftime('%H:%M')
            }, broadcast=True)
            break

@socketio.on('user_joined')
def handle_user_joined(data):
    client_id = request.sid
    username = data.get('username', '匿名')
    
    # 检查用户名是否已存在
    if any(user['username'] == username for user in online_users):
        emit('receive_message', {
            'username': '系统',
            'text': '用户名已被使用，请更换',
            'time': datetime.now().strftime('%H:%M')
        })
        return
    
    user_data = {'username': username, 'sid': client_id}
    online_users.add(user_data)
    print(f'{username} 加入聊天室 (SID: {client_id})')
    
    # 通知所有用户
    emit('update_users', {'count': len(online_users)}, broadcast=True)
    emit('receive_message', {
        'username': '系统',
        'text': f"{username} 加入了聊天",
        'time': datetime.now().strftime('%H:%M')
    }, broadcast=True)
    
    # 发送历史消息
    for msg in messages[-10:]:  # 只发送最近的10条消息
        emit('receive_message', msg)

@socketio.on('send_message')
def handle_message(data):
    username = data.get('username', '匿名')
    message_text = data.get('text', '')
    message_time = data.get('time', datetime.now().strftime('%H:%M'))
    
    if not message_text:
        return
    
    print(f'收到消息: {username}: {message_text}')
    
    # 创建消息对象
    message = {
        'username': username,
        'text': message_text,
        'time': message_time
    }
    
    # 保存消息 (最多保留100条)
    messages.append(message)
    if len(messages) > 100:
        messages.pop(0)
    
    # 广播消息
    emit('receive_message', message, broadcast=True)

if __name__ == '__main__':
    print("""
    ====================================
    自定义聊天服务器已启动
    访问 http://localhost:5000 查看使用说明
    访问 http://localhost:5000/connect 跳转到连接页面
    
    其他用户可以使用以下地址连接:
    ws://[你的IP]:5000
    ====================================
    """)
    socketio.run(app, 
                debug=True, 
                host='0.0.0.0', 
                port=5000, 
                allow_unsafe_werkzeug=True)