# 从datetime模块导入datetime类，用于处理日期和时间
from datetime import datetime
# 导入gradio库，用于快速构建机器学习和数据科学的Web界面
import gradio as gr
from flask import Flask, request, jsonify
from flask_cors import CORS

# 从agent.workflow模块导入WorkFlow类，该类可能包含系统的核心业务逻辑
from agent.workflow import WorkFlow
# 从db.SQLiteDB模块导入SQLiteDB类，用于与SQLite数据库进行交互
from db.SQLiteDB import SQLiteDB
# 从log.logger模块导入Logger类，用于记录系统运行日志
from log.logger import Logger

app = Flask(__name__)
CORS(app)

# 设置应用的标题为"财小助"
title = "财小助"
# 定义应用的描述信息，使用HTML标签进行格式设置
description = """🔎 <strong>财小助，你的私人记账助手~ </strong>"""
# 设置提交按钮上显示的文本为"发送"
submit_btn = '发送'
# 定义示例输入列表，每个元素是一个包含用户输入和风格选项的列表
examples = [["我今天买奶茶花了20", None], ["我前天花300买了件衣服", None], ["我上个月的支出情况", None]]
# 定义支持的语气风格选项列表
style_options = ["轻松", "幽默", "正式"]
# 创建一个下拉框组件，用户可以从style_options中选择语气风格，默认值为"轻松"
# 设置label为空字符串，去掉多余文字，并添加提示信息
style_dropdown = gr.Dropdown(choices=style_options, value="轻松", info="请选择语气风格", label="")

# 定义预测函数，用于处理用户输入并返回响应
def predict(message, history, style):
    # 使用global关键字声明user_name为全局变量
    global user_name
    # 创建一个字典，包含用户输入的消息
    dictionary = {'prompt': message}
    # 打印字典内容，方便调试
    print(dictionary)
    # 如果历史对话记录为空，则将其初始化为空列表
    if history is None:
        history = []
    # 只保留最近的20条对话记录，避免内存占用过多
    history = history[-20:]
    # 初始化模型输入列表
    model_input = []
    # 遍历历史对话记录，将每条对话转换为适合模型输入的格式
    for chat in history:
        # 添加用户的消息字典到模型输入列表
        model_input.append({"role": "user", "content": chat[0]})
        # 添加助手的回复到模型输入列表
        model_input.append({"role": "assistant", "content": chat[1]})
    # 添加当前用户输入的消息到模型输入列表
    model_input.append({"role": "user", "content": message})
    # 打印模型输入列表，方便调试
    print(model_input)
    try:
        # 调用workflow对象的run方法，传入用户需求和用户名，获取处理结果
        user_name, response = workflow.run({"require": message, "user_name": user_name})
        # 打印处理结果，方便调试
        print(response)
        # 根据用户选择的语气风格对回复进行处理
        if style == "幽默":
            # 如果是幽默风格，在回复前添加"哎嘛~ "
            response = "幽默地说： " + response
        elif style == "正式":
            # 如果是正式风格，在回复前添加"尊敬的用户，"
            response = "正式地说： " + response
        else:  # 默认轻松回复
            # 如果是其他风格（默认轻松风格），在回复前添加"嘿嘿~ "
            response = "轻松地说： " + response
        # 将当前用户输入和处理后的回复添加到历史对话记录中
        history.append((message, response))
        # 返回更新后的历史对话记录
        return history
    except Exception as e:
        # 如果在处理过程中出现异常，打印错误信息
        print(f"workflow.run 方法执行出错: {e}")
        # 将错误提示添加到历史对话记录中
        history.append((message, "很抱歉！宕机了！"))
        # 返回更新后的历史对话记录
        return history

# 使用gr.Blocks创建一个Gradio界面，设置标题和主题
with gr.Blocks(title=title,theme="soft") as demo:
    # 在界面上显示应用的描述信息
    gr.Markdown(description)
    # 创建一个聊天机器人组件，用于显示对话历史
    chatbot = gr.Chatbot()
    # 渲染语气风格下拉框组件
    style_dropdown.render()
    # 创建一个文本框组件，用于用户输入消息，设置占位符和不显示标签
    input_text = gr.Textbox(placeholder="Type a message.", show_label=False, scale=8)
    # 创建一个提交按钮，显示文本为submit_btn
    submit = gr.Button(submit_btn, scale=1)
    # 创建示例组件，显示预定义的示例输入
    gr.Examples(examples=examples, inputs=[input_text, style_dropdown])

    # 为提交按钮的点击事件绑定predict函数，设置输入和输出组件；
    # chatbot 组件当前存储的对话历史，是一个列表，列表中的每个元素是一个包含用户输入和助手回复的元组。
    submit.click(predict, inputs=[input_text, chatbot, style_dropdown], outputs=chatbot, queue=True)
    # 为文本框的提交事件绑定predict函数，设置输入和输出组件
    input_text.submit(predict, inputs=[input_text, chatbot, style_dropdown], outputs=chatbot, queue=True)

@app.route('/')
def index():
    return jsonify({
        "status": "ok",
        "message": "服务器运行正常"
    })

@app.route('/api/chat', methods=['POST'])
def chat():
    try:
        data = request.json
        message = data.get('message', '')
        style = data.get('style', '轻松')
        user_name = data.get('user_name', '')
        
        # 调用workflow处理消息
        user_name, response = workflow.run({"require": message, "user_name": user_name})
        
        # 根据风格处理回复
        if style == "幽默":
            response = "幽默地说： " + response
        elif style == "正式":
            response = "正式地说： " + response
        else:  # 默认轻松回复
            response = "轻松地说： " + response
            
        return jsonify({
            "message": response,
            "user_name": user_name
        })
    except Exception as e:
        print(f"Error in chat endpoint: {e}")
        return jsonify({
            "message": "很抱歉！服务器出现错误，请稍后重试。",
            "user_name": user_name
        }), 500

# 如果该脚本作为主程序运行
if __name__ == "__main__":
    # 创建一个SQLiteDB对象，连接到名为"test.db"的数据库
    sqLite = SQLiteDB("storedInfo.db")
    # 获取当前时间，并将其格式化为指定的字符串
    timestamp = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
    # 创建一个Logger对象，用于记录日志，日志文件名包含时间戳
    logger = Logger(f"test_{timestamp}_gty")
    # 初始化用户名为空字符串
    user_name = ""
    # 创建一个WorkFlow对象，传入SQLiteDB对象和Logger对象
    workflow = WorkFlow(sqLite, logger)

    import threading
    
    # 启动Flask服务器
    def run_flask():
        app.run(host='0.0.0.0', port=7860, debug=False, use_reloader=False)
    
    # 启动Gradio界面
    def run_gradio():
        demo.launch(share=True, server_name="0.0.0.0", server_port=7861)
    
    # 创建并启动线程
    flask_thread = threading.Thread(target=run_flask)
    gradio_thread = threading.Thread(target=run_gradio)
    
    flask_thread.start()
    gradio_thread.start()
    
    # 等待线程结束
    flask_thread.join()
    gradio_thread.join()