import os
from typing import TypedDict, Annotated   # 用于定义类型结构, Annotated用于添加元数据
from langchain_core.language_models import BaseChatModel # 用于定义语言模型
from langchain_openai import ChatOpenAI 
from langgraph.graph.message import AnyMessage, add_messages # 用于定义消息结构

from agent.LlmChainGenerate import LlmChainGenerate
from log.logger import Logger


class AgentState(TypedDict):
    """
    定义代理状态的类型结构
    
    包含以下字段：
    - user_name: 用户名（字符串）
    - require: 用户输入的原始需求（字符串）
    - judge_result: 需求判断结果（字符串）
    - list_tables_tool_result: 表列表工具执行结果（字符串）
    - get_schema_tool_result: 表结构工具执行结果（字符串）
    - sql_and_result: SQL语句和执行结果列表（字典列表）
    - messages: 对话消息列表（AnyMessage类型，使用add_messages标记）
    - tool_feedback: 工具反馈列表（字符串列表）
    """
    user_name: str
    require: str
    judge_result: str
    list_tables_tool_result: str
    get_schema_tool_result: str
    sql_and_result: list[dict[str, str]]
    messages: Annotated[list[AnyMessage], add_messages]
    tool_feedback: list[str]


def get_prompt_file(filename):
    """
    获取提示文件的完整路径
    
    参数:
        filename (str): 提示文件名（如"financial_analysis.txt"）
        
    返回:
        str: 规范化后的完整路径（如"../prompts/financial_analysis.txt"）
    
    功能:
        1. 获取当前文件所在目录的绝对路径
        2. 向上跳转一级目录到项目根目录
        3. 拼接prompts文件夹路径
        4. 规范化路径（处理../和符号链接）
    """
    # 获取当前文件所在目录的绝对路径
    current_dir = os.path.dirname(os.path.abspath(__file__))
    # 构建提示文件路径：向上一级目录 -> prompts文件夹 -> 文件名
    prompt_file = os.path.join(current_dir, "..", "prompts", filename)
    # 规范化路径（处理多余的斜杠和符号链接）
    prompt_file = os.path.normpath(prompt_file)
    return prompt_file


def get_new_llm():
    """
    创建并返回一个新的语言模型实例
    
    返回:
        ChatOpenAI: 配置好的通义千问模型实例
        
    功能:
        1. 使用qwen-omni-turbo模型（通义千问全能加速版）
        2. 设置temperature=0（输出确定性高）
        3. 启用流式输出（逐字符返回结果）
        4. 配置DashScope兼容模式的API密钥和端点
    """
    return ChatOpenAI(
        model_name="qwen-max",  # 使用通义千问模型
        temperature=0,  # 温度参数设为0，输出稳定
        streaming=True,  # 启用流式输出（逐字符返回结果）
        openai_api_key="sk-ef92d07fb9764a94871d990058c0db9e",  # DashScope兼容模式API密钥
        openai_api_base="https://dashscope.aliyuncs.com/compatible-mode/v1"  # DashScope兼容模式端点
    )


def get_llm_chain(llm: BaseChatModel, prompt_file: str, useStrOutputParser: bool = False, **kwargs):
    """
    创建并运行语言模型链
    
    参数:
        llm (BaseChatModel): 语言模型实例
        prompt_file (str): 提示文件路径（通过get_prompt_file获取）
        useStrOutputParser (bool): 是否使用字符串输出解析器（默认False）
        **kwargs: 其他参数（如user_name, financial_data等）
        
    返回:
        str或其他类型: 根据useStrOutputParser返回不同类型的结果
        
    功能:
        1. 创建自定义的LlmChainGenerate实例
        2. 处理字符串输出的特殊情况（重试机制）
        3. 确保输出结果的有效性（长度>5）
    """
    # 创建自定义语言模型链
    agent = LlmChainGenerate(
        llm=llm,
        prompt_file=prompt_file,
        useStrOutputParser=useStrOutputParser,
        **kwargs
    )
    
    # 如果需要字符串输出解析（例如工具调用结果）
    if useStrOutputParser:
        answer = ''
        try_num = 0
        # 最多重试2次，直到获取有效回答（长度>5）
        while len(answer) < 5 and try_num < 2:
            answer = agent.run()
            try_num += 1
        return answer
    else:
        return agent.run()