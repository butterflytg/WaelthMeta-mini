from datetime import datetime
from agent.workflow import WorkFlow
from db.SQLiteDB import SQLiteDB
from log.logger import Logger

sqLite= SQLiteDB("storedInfo.db")
timestamp = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
logger = Logger(f"test_{timestamp}", user_name="gty")
workflow = WorkFlow(sqLite, logger)

while True:
    user_input = input("请输入内容（输入 'exit' 退出）：")  # 从控制台获取用户输入
    if user_input.lower() == "exit":  # 输入 'exit' 退出循环
        break
    workflow.run({"require": user_input})  # 传递用户输入

