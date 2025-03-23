import sqlite3
import logging

logger = logging.getLogger(__name__)

class DB:
    def get_monthly_stats(self, year):
        """获取指定年份的月度统计数据"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 查询收入数据
            income_query = """
            SELECT strftime('%m', date) as month, SUM(amount) as total
            FROM transactions
            WHERE type = 'income'
            AND strftime('%Y', date) = ?
            GROUP BY month
            """
            
            # 查询支出数据
            expense_query = """
            SELECT strftime('%m', date) as month, SUM(amount) as total
            FROM transactions
            WHERE type = 'expense'
            AND strftime('%Y', date) = ?
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
                
            return monthly_stats
            
        except Exception as e:
            logger.error(f"获取月度统计数据失败: {str(e)}")
            raise
        finally:
            if conn:
                conn.close() 