from langchain_core.language_models import BaseChatModel
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, HumanMessagePromptTemplate
from typing import Any

from utils.PrintUtils import *

class LlmChainGenerate:
    def __init__(
            self,
            llm: BaseChatModel,  # 语言模型实例（如ChatOpenAI）
            prompt_file: str,     # 提示文件路径（如"prompts/query_prompt.txt"）
            useStrOutputParser: bool = False,  # 是否使用字符串输出解析器
            **kwargs: Any         # 其他参数（如用户信息、数据库连接等）
    ):
        self.llm = llm  # 保存语言模型实例
        self.prompt_file = prompt_file  # 保存提示文件路径
        self.params = kwargs  # 保存额外参数
        self.logger = self.params.pop('logger', None)  # 提取日志记录器（如果存在）
        self.useStrOutputParser = useStrOutputParser  # 是否使用字符串解析器
        self.__init_prompt_templates()  # 初始化提示模板

    def __init_prompt_templates(self):
        """
        初始化提示模板
        
        功能：
        1. 读取提示文件内容
        2. 创建ChatPromptTemplate实例
        3. 绑定额外参数（如用户名称、数据库模式等）
        """
        with open(self.prompt_file, 'r', encoding='utf-8') as f:
            # 从文件内容创建人类消息模板
            human_prompt = HumanMessagePromptTemplate.from_template(f.read())
            # 创建聊天提示模板（包含单一人类消息）
            self.prompt = ChatPromptTemplate.from_messages([human_prompt])
            # 绑定额外参数（通过partial方法）
            self.prompt = self.prompt.partial(**self.params)

    def run(self):
        """
        运行语言模型链
        
        返回：
            str: 模型生成的响应内容
            
        功能：
        1. 根据配置选择流式或非流式处理
        2. 记录提示和响应到日志（如果启用）
        3. 处理颜色输出（用于调试）
        """
        if self.useStrOutputParser:
            # 使用字符串输出解析器（流式处理）
            response = ""
            # 构建模型链：提示 -> 模型 -> 字符串解析
            chain = self.prompt | self.llm | StrOutputParser()
            # 流式处理响应
            for i, s in enumerate(chain.stream({})):
                # 颜色打印（用于区分不同类型的输出）
                color_print(s, THOUGHT_COLOR, end="")
                response += s
        else:
            # 非流式处理（直接获取完整响应）
            chain = self.prompt | self.llm
            response = chain.invoke({})

        print("\n")  # 换行分隔输出
        # 记录日志（如果存在日志记录器）
        if self.logger is not None:
            self.logger.info(f"prompt: \n{self.prompt}", printOnScreen=False)
            self.logger.info(f"LLM: \n{response}", printOnScreen=False)
        return response