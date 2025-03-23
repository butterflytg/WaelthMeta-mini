import json
import os
import sys

from loguru import logger


def loadLogConfig(config_file='log/log_config.json'):
    """
    加载日志配置文件
    
    参数:
        config_file (str): 配置文件路径，默认为'log/log_config.json'
    
    返回:
        dict: 解析后的配置字典
    
    功能:
        1. 检查配置文件是否存在
        2. 读取并解析JSON格式的配置文件
    """
    if not os.path.exists(config_file):
        raise FileNotFoundError(f"配置文件 {config_file} 不存在")

    with open(config_file, 'r', encoding='utf-8') as f:
        return json.load(f)


class Logger:
    def __init__(self, outputFileName: str, outputFilePath=None, user_name: str = 'default',
                 configFilePath: str = "./log/log_config.json"):
        """
        初始化日志记录器
        
        参数:
            outputFileName (str): 日志文件名
            outputFilePath (str, 可选): 日志文件输出路径，默认为None
            user_name (str): 用户名，用于区分不同用户的日志，默认为'default'
            configFilePath (str): 日志配置文件路径，默认为'./log/log_config.json'
            
        功能:
            1. 加载日志配置文件
            2. 设置日志文件的存储路径和命名规则
            3. 配置日志文件的轮转、保留和压缩策略
        """
        # 加载日志配置文件
        self.config = loadLogConfig(configFilePath)  
        # 记录当前操作用户名
        self.user_name = user_name  
        # 设置日志存储目录：
        # 1. 优先使用传入的outputFilePath
        # 2. 否则使用配置文件中的log_dir字段
        # 3. 默认使用'./log'
        self.logDir = outputFilePath if outputFilePath is not None else self.config.get('log_dir', './log')
        # 日志轮转条件（文件大小）
        self.rotation = self.config.get('rotation', '10 MB')  
        # 日志保留时间
        self.retention = self.config.get('retention', '30 days')  
        # 日志压缩格式
        self.compression = self.config.get('compression', 'zip')  
        # 日志文件名
        self.outputFileName = outputFileName  

    def info(self, printStr: str, printOnScreen: bool = True):
        """
        记录INFO级别的日志信息
        
        参数:
            printStr (str): 需要记录的日志信息
            printOnScreen (bool): 是否同时在控制台显示日志，默认为True
            
        功能:
            1. 在用户专属的INFO目录下创建日志文件
            2. 配置日志记录器的输出格式和文件管理策略
            3. 根据需要同时输出到文件和控制台
        """
        # 创建用户专属的INFO日志目录
        # 路径格式：log_dir/username/INFO
        dirPath = self.logDir + f"/{self.user_name}/INFO"
        # 如果目录不存在则创建
        if not os.path.exists(dirPath):
            os.makedirs(dirPath)
        
        # 拼接完整的日志文件路径
        logFile = os.path.join(dirPath, f"{self.outputFileName}.log")
        
        # 移除之前的日志处理器（避免重复记录）
        logger.remove()
        
        # 添加文件日志处理器
        logger.add(
            logFile,           # 日志文件路径
            level='INFO',      # 日志级别
            rotation=self.rotation,  # 轮转条件（文件大小）
            compression=self.compression,  # 压缩格式
            retention=self.retention,     # 保留时间
            encoding="utf-8",            # 文件编码
            # 日志格式：时间 | 级别 | 消息内容
            format='{time:YYYY-MM-DD HH:mm:ss.sss} | {level} | {message}'
        )
        
        # 如果需要同时输出到控制台
        if printOnScreen:
            logger.add(
                sys.stdout,      # 输出到标准输出
                level='INFO',
                format='{time:YYYY-MM-DD HH:mm:ss.sss} | {level} | {message}'
            )
        
        # 记录日志信息（换行符保证每条日志独立一行）
        logger.info(f"{printStr}\n")

    def debug(self, printStr: str):
        """
        记录DEBUG级别的日志信息
        
        参数:
            printStr (str): 需要记录的日志信息
            
        功能:
            1. 在用户专属的DEBUG目录下创建日志文件
            2. 配置DEBUG级别日志的文件管理策略
            3. 同时输出到文件和控制台
        """
        # 创建用户专属的DEBUG日志目录
        dirPath = self.logDir + f"/{self.user_name}/DEBUG"
        if not os.path.exists(dirPath):
            os.makedirs(dirPath)
        # 日志文件路径
        logFile = os.path.join(dirPath, f"{self.outputFileName}.log")
        # 移除旧处理器
        logger.remove()
        # 添加文件处理器
        logger.add(logFile,
                   level='DEBUG',
                   rotation=self.rotation,  # 轮转大小条件
                   compression=self.compression,  # 日志文件压缩格式
                   retention=self.retention,
                   encoding="utf-8",
                   format='{time:YYYY-MM-DD HH:mm:ss.sss} | {level} | {message}')
        # 添加控制台输出
        logger.add(sys.stdout, level='DEBUG', format='{time:YYYY-MM-DD HH:mm:ss.sss} | {level} | {message}')
        # 记录日志
        logger.debug(f"{printStr}\n")

    def error(self, printStr: str):
        """
        记录ERROR级别的日志信息
        
        参数:
            printStr (str): 需要记录的日志信息
            
        功能:
            1. 在用户专属的ERROR目录下创建日志文件
            2. 配置ERROR级别日志的文件管理策略
            3. 同时输出到文件和控制台
        """
        # 创建用户专属的ERROR日志目录
        dirPath = self.logDir + f"/{self.user_name}/ERROR"
        if not os.path.exists(dirPath):
            os.makedirs(dirPath)
        # 日志文件路径
        logFile = os.path.join(dirPath, f"{self.outputFileName}.log")
        # 移除旧处理器
        logger.remove()
        # 添加文件处理器
        logger.add(logFile,
                   level='ERROR',
                   rotation=self.rotation,  # 轮转大小条件
                   compression=self.compression,  # 日志文件压缩格式
                   retention=self.retention,
                   encoding="utf-8",
                   format='{time:YYYY-MM-DD HH:mm:ss.sss} | {level} | {message}')
        # 添加控制台输出
        logger.add(sys.stdout, level='ERROR', format='{time:YYYY-MM-DD HH:mm:ss.sss} | {level} | {message}')
        # 记录日志
        logger.error(f"{printStr}\n")