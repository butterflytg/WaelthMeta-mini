import sqlite3
import os
from langchain_community.utilities import SQLDatabase


class SQLiteDB:
    def __init__(self, db_name: str):
        """
        初始化SQLite数据库连接并设置基本结构
        
        参数:
            db_name (str): 数据库文件名
            
        功能:
            1. 在db目录下创建或连接到指定的SQLite数据库
            2. 如果数据库不存在，自动创建必要的表结构
            3. 设置数据库连接，支持多线程访问
        """
        # 在db目录下创建数据库文件
        self.db_name = f"db/{db_name}"  
        # 确保db目录存在
        os.makedirs(os.path.dirname(self.db_name), exist_ok=True)

        # 检查数据库文件是否已存在
        db_exists = os.path.exists(self.db_name)

        # 创建数据库连接，设置check_same_thread=False以支持多线程访问
        self.conn = sqlite3.connect(self.db_name, check_same_thread=False)

        # 如果是新数据库，创建必要的表结构
        if not db_exists:
            self._create_tables()

        # 创建SQLDatabase对象用于执行查询操作,将自然语言查询转换为SQL语句查询
        self.sqlDatabase = SQLDatabase.from_uri(f"sqlite:///{self.db_name}")

    def _create_tables(self):
        """
        创建数据库必要的表结构
        
        创建两个主要表：
        1. users表：存储用户信息
           - user_id: 用户唯一标识符
           - user_name: 用户名（唯一）
           
        2. bill表：存储账单记录
           - bill_id: 账单唯一标识符
           - user_id: 关联的用户ID
           - timestamp: 记录时间（默认为当前时间）
           - amount: 金额
           - category: 消费类别
           - description: 描述信息
           - income_expense: 收入或支出标记
        """
        # 创建用户表SQL语句
        create_users_table = """
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_name TEXT NOT NULL UNIQUE
        );
        """

        # 创建账单表SQL语句
        create_bill_table = """
        CREATE TABLE IF NOT EXISTS bill (
            bill_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            amount REAL NOT NULL,
            category TEXT NOT NULL,
            description TEXT,
            income_expense TEXT CHECK(income_expense IN ('income', 'expense')) NOT NULL, 
            FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE
        );
        """

        # 执行建表操作
        with self.conn as conn:
            cursor = conn.cursor()
            cursor.execute(create_users_table)
            cursor.execute(create_bill_table)
            conn.commit()
        print("数据库和表已创建。")
        

    def register_user(self, username):
        """
        注册新用户
        
        Args:
            username: 用户名
            
        Returns:
            成功返回用户ID，如果用户名已存在则返回None
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute("INSERT INTO users (user_name) VALUES (?)", (username,))
            self.conn.commit()
            return cursor.lastrowid
        except sqlite3.IntegrityError:
            # 用户名已存在
            return None
            
    def login_user(self, username):
        """
        验证用户登录
        
        Args:
            username: 用户名
            
        Returns:
            成功返回用户ID，如果用户不存在则返回None
        """
        cursor = self.conn.cursor()
        cursor.execute("SELECT user_id FROM users WHERE user_name = ?", (username,))
        result = cursor.fetchone()
        return result[0] if result else None
        
    def get_user_by_name(self, username):
        """
        通过用户名获取用户信息
        
        Args:
            username: 用户名
            
        Returns:
            用户信息字典，如果用户不存在则返回None
        """
        cursor = self.conn.cursor()
        cursor.execute("SELECT user_id, user_name FROM users WHERE user_name = ?", (username,))
        result = cursor.fetchone()
        if result:
            return {"user_id": result[0], "user_name": result[1]}
        return None

    def get_sqlDatabase(self):
        """返回 SQLDatabase 对象"""
        return self.sqlDatabase
        
    def close(self):
        """关闭数据库连接"""
        self.conn.close()
        print("数据库连接已关闭。")

    def get_monthly_stats(self, year):
        """获取指定年份的月度统计数据"""
        try:
            cursor = self.conn.cursor()
            
            # 查询收入数据
            income_query = """
            SELECT strftime('%m', timestamp) as month, SUM(amount) as total
            FROM bill
            WHERE income_expense = 'income'
            AND strftime('%Y', timestamp) = ?
            GROUP BY month
            """
            
            # 查询支出数据
            expense_query = """
            SELECT strftime('%m', timestamp) as month, SUM(amount) as total
            FROM bill
            WHERE income_expense = 'expense'
            AND strftime('%Y', timestamp) = ?
            GROUP BY month
            """
            
            cursor.execute(income_query, (str(year),))
            income_data = {row[0]: row[1] for row in cursor.fetchall()}
            
            cursor.execute(expense_query, (str(year),))
            expense_data = {row[0]: row[1] for row in cursor.fetchall()}
            
            # 合并数据
            monthly_stats = []
            for month in range(1, 13):
                month_str = f"{month:02d}"
                monthly_stats.append({
                    'month': month,
                    'income': float(income_data.get(month_str, 0)),
                    'expense': float(expense_data.get(month_str, 0))
                })
            
            # print(monthly_stats)
                
            return monthly_stats
            
        except Exception as e:
            print(f"获取月度统计数据失败: {str(e)}")
            return []

# 测试创建数据库
if __name__ == "__main__":
    db = SQLiteDB("storedInfo.db")
    db.get_monthly_stats(2025)
    db.close()