# 导入所需的Python标准库
from datetime import datetime  # 用于处理日期和时间

# 导入LangChain相关的库
from langchain_community.agent_toolkits import SQLDatabaseToolkit  # SQL数据库工具包
from langchain_core.messages import AIMessage, ToolMessage  # 消息类型定义
from langchain_core.runnables import RunnableWithFallbacks, RunnableLambda  # 可运行对象和Lambda函数
from langgraph.graph import END, StateGraph, START  # 图状态管理
from langgraph.prebuilt import ToolNode  # 预构建的工具节点
from langchain_core.tools import tool  # 工具装饰器

# 导入Pydantic用于数据验证
from pydantic import BaseModel, Field  # 数据模型和字段定义
from sqlalchemy.exc import SQLAlchemyError  # SQL异常处理

# 导入自定义工具和类型
from utils.LLMUtil import get_llm_chain, AgentState, get_prompt_file, get_new_llm  # 工具函数
from typing import Annotated, Literal, Any, Dict  # 类型注解

class SubmitFinalAnswer(BaseModel):
    """提交最终答案给用户的模型类
    
    这个类用于格式化和验证返回给用户的最终答案。它继承自Pydantic的BaseModel，
    确保数据的类型安全和验证。
    """

    final_answer: Dict[str, Any] = Field(
        ...,  # 表示这是一个必需字段
        description="返回给用户的最终答案，支持任意键值对的字典格式"
    )

class WorkFlow:
    """工作流程类，用于处理用户查询和数据库操作的核心类
    
    这个类实现了一个完整的工作流程，包括：
    1. 用户登录验证
    2. 查询类型判断
    3. SQL查询生成和执行
    4. 结果处理和返回
    """
    
    # 类级别的SQLite数据库实例
    sqLite = None
    
    def __init__(self, sqLite, logger=None):
        """初始化工作流程实例
        
        Args:
            sqLite: SQLite数据库实例
            logger: 日志记录器实例，默认为None
        """
        # 设置日志记录器
        self.logger = logger
        # 设置类级别的数据库实例
        WorkFlow.sqLite = sqLite
        # 创建SQL数据库工具包实例
        toolkit = SQLDatabaseToolkit(
            db=sqLite.get_sqlDatabase(),  # 获取数据库连接
            llm=get_new_llm()    # 获取语言模型实例
        )
        # 获取数据库操作工具集
        tools = toolkit.get_tools()

        # 从工具集中获取列表表格和获取模式的工具
        self.list_tables_tool = next(tool for tool in tools if tool.name == "sql_db_list_tables")  # 获取列出数据库表的工具
        self.get_schema_tool = next(tool for tool in tools if tool.name == "sql_db_schema")      # 获取数据库模式的工具

        # 创建状态图实例，用于管理工作流程的状态
        self.workflow = StateGraph(AgentState)

        # 添加工作流程的各个节点
        self.workflow.add_node("login", self.login)                # 登录验证节点
        self.workflow.add_node("judge_query", self.judge_query)    # 查询判断节点

        # 添加数据库操作相关的节点
        self.workflow.add_node("first_tool_call", self.first_tool_call)  # 初始工具调用节点
        # 添加列表工具节点，包含错误处理回退机制
        self.workflow.add_node("list_tables_tool", self.create_tool_node_with_fallback([self.list_tables_tool]))

        # 创建模式获取模型并绑定工具
        self.model_get_schema = get_new_llm().bind_tools([self.get_schema_tool])
        # 添加模式获取节点
        self.workflow.add_node(
            "model_get_schema",
            lambda state: {
                "messages": [self.model_get_schema.invoke(state["messages"])],  # 调用模型获取模式信息
            },
        )
        # 添加模式工具节点，包含错误处理回退机制
        self.workflow.add_node("get_schema_tool", self.create_tool_node_with_fallback([self.get_schema_tool]))
        
        # 添加查询生成和执行相关的节点
        self.workflow.add_node("query_gen", self.query_gen_node)        # 查询生成节点
        self.workflow.add_node("correct_query", self.model_check_query)  # 查询校正节点
        self.workflow.add_node("execute_query", self.create_tool_node_with_fallback([self.db_query_tool]))  # 查询执行节点
        self.workflow.add_node("conclude", self.conclude)               # 结果总结节点


        # 添加条件边缘，用于控制工作流程的路由
        self.workflow.add_conditional_edges(START, self.judge_login_route)  # 根据登录状态决定是否需要登录

        # 添加登录流程的条件边缘
        self.workflow.add_conditional_edges("login", self.should_continue_login)  # 判断登录是否成功

        # 添加查询类型判断的条件边缘
        self.workflow.add_conditional_edges("judge_query", self.route)  # 根据查询类型选择不同的处理路径

        # 添加数据库查询流程的边缘
        self.workflow.add_edge("first_tool_call", "list_tables_tool")          # 从初始工具调用到列出表格
        self.workflow.add_edge("list_tables_tool", "model_get_schema")        # 从表格列表到模式获取模型
        self.workflow.add_edge("model_get_schema", "get_schema_tool")         # 从模式获取模型到模式工具
        self.workflow.add_edge("get_schema_tool", "query_gen")               # 从模式工具到查询生成
        self.workflow.add_edge("query_gen", "execute_query")                # 从查询生成到查询执行
        self.workflow.add_edge("execute_query", "conclude")                 # 从查询执行到结果总结
        self.workflow.add_edge("conclude", END)                             # 从结果总结到结束


        # 编译工作流程图为可执行应用
        self.app = self.workflow.compile()


    def run(self, input):
        try:
            # 调用工作流程处理输入
            result = self.app.invoke(input)
            
            # 如果结果是字符串，直接返回
            if isinstance(result, str):
                return "", result
                
            # 获取最后一条消息
            messages = result.get("messages", [])
            if not messages:
                return "", "没有获取到响应消息"
                
            last_message = messages[-1]
            
            # 如果最后一条消息是字符串，直接返回
            if isinstance(last_message, str):
                return "", last_message
                
            # 处理最终答案
            if hasattr(last_message, "tool_calls") and last_message.tool_calls:
                tool_call = last_message.tool_calls[0]
                if isinstance(tool_call, dict):
                    args = tool_call.get("args", {})
                    if isinstance(args, dict):
                        final_answer = args.get("final_answer", {})
                        if isinstance(final_answer, dict):
                            message = final_answer.get("message", str(last_message.content))
                        else:
                            message = str(final_answer)
                    else:
                        message = str(args)
                else:
                    message = str(last_message.content)
            else:
                message = getattr(last_message, 'content', str(last_message))
            
            # 获取用户名
            user_name = result.get("user_name", "")
            
            return user_name, message
        
        except Exception as e:
            print(f"处理响应时出错: {str(e)}")
            return "", f"处理响应时出错: {str(e)}"


    def route(self, state):
        """根据查询判断结果选择处理路径
        
        Args:
            state: 当前状态，包含查询判断结果
            
        Returns:
            str: 下一个处理节点的名称
        """
        if state["judge_result"]=="only_db":
            return "first_tool_call"  # 如果是纯数据库查询，进入数据库查询流程
        elif state["judge_result"]=="db_rag":
            return "rag_retrieval"    # 如果需要RAG检索，进入RAG处理流程,暂时不支持

    def login(self, state):
        """处理用户登录验证
        
        Args:
            state: 当前状态，包含用户请求信息
            
        Returns:
            dict: 包含登录验证结果的消息
        """
        # 获取用户名判断的提示文件
        prompt_file = get_prompt_file("judge_username.txt")
        # 使用语言模型进行用户名验证
        message = get_llm_chain(
            llm=get_new_llm().bind_tools(
                [self.list_tables_tool, SubmitFinalAnswer],
                tool_choice="required"
            ),
            prompt_file=prompt_file,
            require=state["require"],
            logger=self.logger
        )
        return {"messages": [message]}

    def should_continue_login(self, state: AgentState) -> Literal[END, "list_tables_tool"]:
        """判断是否需要继续登录流程
        
        Args:
            state: 当前状态，包含消息历史
            
        Returns:
            Literal[END, "list_tables_tool"]: 返回结束或继续处理表格列表
        """
        messages = state["messages"]
        last_message = messages[-1]
        if last_message.tool_calls[0]["name"]=="sql_db_list_tables":
            return "list_tables_tool"  # 需要继续处理数据库表列表
        elif last_message.tool_calls[0]["name"]=="SubmitFinalAnswer":
            return END                  # 登录流程结束

    def judge_login_route(self, state):
        """判断是否需要进行登录验证
        
        Args:
            state: 当前状态，包含用户名信息
            
        Returns:
            str: 返回登录或查询判断节点
        """
        if state.get("user_name")=="" or state.get("user_name") is None:
            return "login"         # 用户名为空，需要登录
        else:
            return "judge_query"   # 已有用户名，进行查询判断

    def create_tool_node_with_fallback(self, tools: list) -> RunnableWithFallbacks[Any, dict]:
        """创建带有错误处理回退机制的工具节点
        
        Args:
            tools: 需要创建的工具列表
            
        Returns:
            RunnableWithFallbacks: 带有错误处理功能的可运行工具节点
        """
        return ToolNode(tools).with_fallbacks(
            [RunnableLambda(self.handle_tool_error)],  # 添加错误处理Lambda函数
            exception_key="error"                     # 设置异常信息的键名
        )

    def handle_tool_error(self, state) -> dict:
        """处理工具执行过程中的错误
        
        Args:
            state: 当前状态，包含错误信息和工具调用历史
            
        Returns:
            dict: 包含错误消息的工具响应
        """
        error = state.get("error")                # 获取错误信息
        tool_calls = state["messages"][-1].tool_calls  # 获取最后一次工具调用信息
        return {
            "messages": [
                ToolMessage(
                    content=f"Error: {repr(error)}\n please fix your mistakes.",  # 格式化错误消息
                    tool_call_id=tc["id"],                                      # 关联到对应的工具调用ID
                )
                for tc in tool_calls
            ]
        }

    def should_continue(self, state: AgentState) -> Literal[END, "correct_query", "query_gen"]:
        """判断工作流程是否需要继续执行
        
        Args:
            state: 当前状态，包含消息历史
            
        Returns:
            Literal: 返回结束、继续查询校正或重新生成查询
        """
        messages = state["messages"]           # 获取消息历史
        last_message = messages[-1]          # 获取最后一条消息
        # 如果存在工具调用，则结束流程
        if getattr(last_message, "tool_calls", None):
            return END
        # 如果消息内容以错误开头，则重新生成查询
        if last_message.content.startswith("错误"):
            return "query_gen"
        # 否则进行查询校正
        else:
            return "correct_query"

    def first_tool_call(self, state: AgentState) -> dict[str, list[AIMessage]]:
        """创建初始工具调用，用于列出数据库表
        
        Args:
            state: 当前状态
            
        Returns:
            dict: 包含列出数据库表的AI消息
        """
        return {
            "messages": [
                AIMessage(
                    content="",                     # 空内容，因为只需要工具调用
                    tool_calls=[
                        {
                            "name": "sql_db_list_tables",  # 调用列出表格的工具
                            "args": {},                    # 无需参数
                            "id": "tool_abcd123",         # 工具调用的唯一标识
                        }
                    ],
                )
            ]
        }

    def query_gen_node(self, state: AgentState):
        """生成SQL查询的节点
        
        这个方法负责处理和生成SQL查询，包括：
        1. 初始化和验证状态数据
        2. 处理工具消息和更新状态
        3. 生成SQL查询
        
        Args:
            state: 当前状态，包含查询所需的各种信息
            
        Returns:
            dict: 包含生成的查询消息
        """
        # 初始化状态数据，确保必要的字段存在
        if "list_tables_tool_result" not in state or not state["list_tables_tool_result"]:
            state["list_tables_tool_result"] = None  # 设置表格列表结果的默认值

        if "get_schema_tool_result" not in state or not state["get_schema_tool_result"]:
            state["get_schema_tool_result"] = None  # 设置模式结果的默认值

        # 处理消息历史，更新状态数据
        messages = state.get("messages", [])
        for message in messages:
            if message.type == "tool":
                if message.name == "sql_db_list_tables":
                    state["list_tables_tool_result"] = message.content    # 更新表格列表结果
                elif message.name == "sql_db_schema":
                    state["get_schema_tool_result"] = message.content    # 更新模式信息

        # 获取SQL生成的提示文件
        prompt_file = get_prompt_file("sql_generate.txt")
        
        # 使用语言模型生成SQL查询
        message = get_llm_chain(
            llm=get_new_llm().bind_tools(
                [self.db_query_tool],
                tool_choice="required"
            ),
            prompt_file=prompt_file,
            require=state["require"],                                 # 用户请求
            list_tables_tool_result=state["list_tables_tool_result"], # 表格列表
            get_schema_tool_result=state["get_schema_tool_result"],   # 数据库模式
            user_name=state["user_name"],                            # 用户名
            current_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"), # 当前时间
            logger=self.logger
        )
        
        return {"messages": [message]}  # 返回生成的查询消息


    @staticmethod
    @tool
    def db_query_tool(query: str) -> str:
        """数据库查询工具，用于执行SQL语句并返回结果
        
        这个工具支持以下类型的SQL操作：
        1. SELECT：执行查询操作
        2. INSERT：插入数据
        3. UPDATE：更新数据
        4. DELETE：删除数据
        
        Args:
            query: 要执行的SQL语句
            
        Returns:
            str: 查询结果或执行状态信息
            - 对于SELECT：返回查询结果列表或"没有查询到信息"
            - 对于其他操作：返回受影响的行数
            - 执行失败时返回错误信息
        """
        try:
            # 解析SQL语句类型
            sql_type = query.strip().split()[0].upper()
            # 获取数据库连接和游标
            connection = WorkFlow.sqLite.conn
            cursor = connection.cursor()
            
            # 处理SELECT查询
            if sql_type == "SELECT":
                cursor.execute(query)           # 执行查询
                result = cursor.fetchall()      # 获取所有结果
                cursor.close()                  # 关闭游标
                return result if result else "message: 没有查询到信息."

            # 处理INSERT/UPDATE/DELETE操作
            cursor.execute(query)               # 执行SQL语句
            connection.commit()                 # 提交事务
            affected_rows = cursor.rowcount     # 获取受影响的行数
            cursor.close()                     # 关闭游标
            return f"message: {sql_type} 成功，受影响行数: {affected_rows}"

        except SQLAlchemyError as e:
            # 处理SQL执行错误
            return f"message: SQL 执行失败，错误信息: {str(e)}"

    def model_check_query(self,state: AgentState) -> dict[str, list[AIMessage]]:
        """
        Use this tool to double-check if your query is correct before executing it.
        """
        prompt_file = get_prompt_file("sql_check.txt")
        message = get_llm_chain(llm=get_new_llm().bind_tools([self.db_query_tool], tool_choice="required"),
                                prompt_file=prompt_file,
                                to_check_sql=state["messages"][-1].content,
                                logger=self.logger)
        return {"messages":[message]}

    def judge_query(self,state):
        prompt_file = get_prompt_file("judge_query.txt")
        result = get_llm_chain(llm=get_new_llm(), prompt_file=prompt_file, require=state.get("require"),logger=self.logger)
        return {"judge_result":result.content}

    def rag_retrieval(self,state):
        prompt_file = ""
        result = get_llm_chain(llm=get_new_llm(), prompt_file=prompt_file,logger=self.logger)
        return result


    def conclude(self,state):
        if "sql_and_result" not in state or not state["sql_and_result"]:
            state["sql_and_result"] = []  # 或者设置一个默认值
        messages = state.get("messages", [])
        for message in messages:
            if message.type == "tool" and message.name == "db_query_tool":
                tool_call_id = message.tool_call_id
                for message_temp in messages:
                    if message_temp.type == "ai" and message_temp.tool_calls:
                        for tool_call in message_temp.tool_calls:
                            if tool_call["id"] == tool_call_id:
                                state["sql_and_result"].append({tool_call["args"]["query"]: message.content})


        prompt_file = get_prompt_file("conclude.txt")
        message = get_llm_chain(llm=get_new_llm().bind_tools([SubmitFinalAnswer]),
                                prompt_file=prompt_file,
                                require=state["require"],
                                sql_and_result=state["sql_and_result"],
                                logger=self.logger)
        if message.tool_calls:
            for tc in message.tool_calls:
                if tc["name"] == "SubmitFinalAnswer":
                    if "user_name" in tc["args"]["final_answer"]:
                        state["user_name"] = tc["args"]["final_answer"]["user_name"]

        return {"messages": [message],"user_name": state["user_name"]}

    def should_end(self,state: AgentState) -> Literal[END, "query_gen"]:
        messages = state["messages"]
        last_message = messages[-1]
        # If there is a tool call, then we finish
        if getattr(last_message, "tool_calls", None):
            return END
        else:
            return "correct_query"