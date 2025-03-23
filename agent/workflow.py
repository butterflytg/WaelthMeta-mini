from datetime import datetime

from langchain_community.agent_toolkits import SQLDatabaseToolkit
from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.runnables import RunnableWithFallbacks, RunnableLambda
from langgraph.graph import END, StateGraph, START
from langgraph.prebuilt import ToolNode
from langchain_core.tools import tool

from pydantic import BaseModel, Field
from sqlalchemy.exc import SQLAlchemyError

from utils.LLMUtil import get_llm_chain, AgentState, get_prompt_file, get_new_llm
from typing import Annotated, Literal, Any, Dict, Union, Sequence


class SubmitFinalAnswer(BaseModel):
    """Submit the final answer to the user based on the query results."""
    final_answer: Dict[str, Any] = Field(..., description="The final answer to the user")


class WorkFlow:
    sqLite = None

    def __init__(self, sqLite, logger=None):
        self.logger = logger
        WorkFlow.sqLite = sqLite
        toolkit = SQLDatabaseToolkit(db=sqLite.get_sqlDatabase(), llm=get_new_llm())
        tools = toolkit.get_tools()

        self.list_tables_tool = next(tool for tool in tools if tool.name == "sql_db_list_tables")
        self.get_schema_tool = next(tool for tool in tools if tool.name == "sql_db_schema")

        self.workflow = StateGraph(AgentState)

        # 添加节点和边
        self.workflow.add_node("login", self.login)
        self.workflow.add_node("judge_query", self.judge_query)
        self.workflow.add_node("first_tool_call", self.first_tool_call)
        self.workflow.add_node("list_tables_tool", self.create_tool_node_with_fallback([self.list_tables_tool]))
        self.model_get_schema = get_new_llm().bind_tools([self.get_schema_tool])
        self.workflow.add_node("model_get_schema", lambda state: {"messages": [self.model_get_schema.invoke(state["messages"])]})
        self.workflow.add_node("get_schema_tool", self.create_tool_node_with_fallback([self.get_schema_tool]))
        self.workflow.add_node("query_gen", self.query_gen_node)
        self.workflow.add_node("correct_query", self.model_check_query)
        self.workflow.add_node("execute_query", self.create_tool_node_with_fallback([self.db_query_tool]))
        self.workflow.add_node("conclude", self.conclude)

        # 添加条件边和普通边
        self.workflow.add_conditional_edges(START, self.judge_login_route)
        self.workflow.add_conditional_edges("login", self.should_continue_login)
        self.workflow.add_conditional_edges("judge_query", self.route)
        self.workflow.add_edge("first_tool_call", "list_tables_tool")
        self.workflow.add_edge("list_tables_tool", "model_get_schema")
        self.workflow.add_edge("model_get_schema", "get_schema_tool")
        self.workflow.add_edge("get_schema_tool", "query_gen")
        self.workflow.add_edge("query_gen", "execute_query")
        self.workflow.add_edge("execute_query", "conclude")
        self.workflow.add_edge("conclude", END)

        self.app = self.workflow.compile()

    def run(self, input):
        try:
            result = self.app.invoke(input)
            user_name = result.get("user_name", "")
            messages = result.get("messages", [])

            if not messages:
                return user_name, "没有获取到响应消息"

            last_message = messages[-1]

            if hasattr(last_message, "tool_calls") and last_message.tool_calls:
                tool_call = last_message.tool_calls[0]
                args = tool_call.get("args", {})
                final_answer = args.get("final_answer", {})
                message = final_answer.get("message", "没有获取到有效回答")
            else:
                message = getattr(last_message, "content", "没有获取到有效回答")

            return user_name, message
        except Exception as e:
            print(f"处理响应时出错: {str(e)}")
            return "", f"处理响应时出错: {str(e)}"

    def route(self, state):
        judge_result = state.get("judge_result", "")
        if judge_result == "only_db":
            return "first_tool_call"
        elif judge_result == "db_rag":
            return "rag_retrieval"
        else:
            return "judge_query"  # 默认路由

    def login(self, state):
        prompt_file = get_prompt_file("judge_username.txt")
        message = get_llm_chain(
            llm=get_new_llm().bind_tools([self.list_tables_tool, SubmitFinalAnswer], tool_choice="required"),
            prompt_file=prompt_file,
            require=state["require"],
            logger=self.logger
        )
        return {"messages": [message]}

    def should_continue_login(self, state: AgentState) -> Literal[END, "list_tables_tool"]:
        messages = state.get("messages", [])
        if not messages:
            return END

        last_message = messages[-1]
        tool_calls = last_message.tool_calls if hasattr(last_message, "tool_calls") else []

        if tool_calls and tool_calls[0].get("name") == "sql_db_list_tables":
            return "list_tables_tool"
        elif tool_calls and tool_calls[0].get("name") == "SubmitFinalAnswer":
            return END
        else:
            return END

    def judge_login_route(self, state):
        user_name = state.get("user_name", "")
        return "login" if user_name == "" else "judge_query"

    def create_tool_node_with_fallback(self, tools: list) -> RunnableWithFallbacks[Any, dict]:
        return ToolNode(tools).with_fallbacks(
            [RunnableLambda(self.handle_tool_error)], exception_key="error"
        )

    def handle_tool_error(self, state) -> dict:
        error = state.get("error")
        tool_calls = state["messages"][-1].tool_calls if state.get("messages") else []
        return {
            "messages": [
                ToolMessage(
                    content=f"Error: {repr(error)}\n请修正您的错误。",
                    tool_call_id=tc["id"],
                )
                for tc in tool_calls
            ]
        }

    def should_continue(self, state: AgentState) -> Literal[END, "correct_query", "query_gen"]:
        messages = state.get("messages", [])
        if not messages:
            return END

        last_message = messages[-1]
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            return END
        if last_message.content.startswith("错误"):
            return "query_gen"
        else:
            return "correct_query"

    def first_tool_call(self, state: AgentState) -> dict[str, list[AIMessage]]:
        return {
            "messages": [
                AIMessage(
                    content="",
                    tool_calls=[{
                        "name": "sql_db_list_tables",
                        "args": {},
                        "id": "tool_abcd123",
                    }]
                )
            ]
        }

    def query_gen_node(self, state: AgentState):
        state.setdefault("list_tables_tool_result", None)
        state.setdefault("get_schema_tool_result", None)

        messages = state.get("messages", [])
        for message in messages:
            if message.type == "tool":
                if message.name == "sql_db_list_tables":
                    state["list_tables_tool_result"] = message.content
                elif message.name == "sql_db_schema":
                    state["get_schema_tool_result"] = message.content

        prompt_file = get_prompt_file("sql_generate.txt")
        message = get_llm_chain(
            llm=get_new_llm().bind_tools([self.db_query_tool], tool_choice="required"),
            prompt_file=prompt_file,
            require=state["require"],
            list_tables_tool_result=state["list_tables_tool_result"],
            get_schema_tool_result=state["get_schema_tool_result"],
            user_name=state["user_name"],
            current_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            logger=self.logger
        )
        return {"messages": [message]}

    @staticmethod
    @tool
    def db_query_tool(query: str) -> str:
        """
        执行 SQL 语句（支持 SELECT、INSERT、UPDATE、DELETE），并返回执行结果。

        **支持的 SQL 语句类型:**
        1. **SELECT** 查询：返回查询结果列表，如果无数据，则返回 `"message: 没有查询到信息."`
        2. **INSERT** 插入：返回 `"message: INSERT 成功，受影响行数: X"`
        3. **UPDATE** 更新：返回 `"message: UPDATE 成功，受影响行数: X"`
        4. **DELETE** 删除：返回 `"message: DELETE 成功，受影响行数: X"`

        **错误处理:**
        - 如果 SQL 语句错误或执行失败，返回 `"message: SQL 执行失败，错误信息: {error}"`

        :param query: 需要执行的 SQL 语句（字符串）
        :return: 查询结果或执行状态信息（字符串）
        """
        try:
            sql_type = query.strip().split()[0].upper()
            connection = WorkFlow.sqLite.conn
            cursor = connection.cursor()

            if sql_type == "SELECT":
                cursor.execute(query)
                result = cursor.fetchall()
                cursor.close()
                return result if result else "message: 没有查询到信息."

            cursor.execute(query)
            connection.commit()
            affected_rows = cursor.rowcount
            cursor.close()
            return f"message: {sql_type} 成功，受影响行数: {affected_rows}"

        except SQLAlchemyError as e:
            return f"message: SQL 执行失败，错误信息: {str(e)}"

    def model_check_query(self, state: AgentState) -> dict[str, list[AIMessage]]:
        prompt_file = get_prompt_file("sql_check.txt")
        message = get_llm_chain(
            llm=get_new_llm().bind_tools([self.db_query_tool], tool_choice="required"),
            prompt_file=prompt_file,
            to_check_sql=state["messages"][-1].content,
            logger=self.logger
        )
        return {"messages": [message]}

    def judge_query(self, state):
        prompt_file = get_prompt_file("judge_query.txt")
        result = get_llm_chain(
            llm=get_new_llm(),
            prompt_file=prompt_file,
            require=state.get("require"),
            logger=self.logger
        )
        return {"judge_result": result.content}

    def rag_retrieval(self, state):
        prompt_file = ""
        result = get_llm_chain(llm=get_new_llm(), prompt_file=prompt_file, logger=self.logger)
        return result

    def conclude(self, state):
        state.setdefault("sql_and_result", [])
        messages = state.get("messages", [])

        for message in messages:
            if message.type == "tool" and message.name == "db_query_tool":
                tool_call_id = message.tool_call_id
                for msg in messages:
                    if msg.type == "ai" and msg.tool_calls:
                        for tc in msg.tool_calls:
                            if tc["id"] == tool_call_id:
                                state["sql_and_result"].append({tc["args"]["query"]: message.content})

        prompt_file = get_prompt_file("conclude.txt")
        message = get_llm_chain(
            llm=get_new_llm().bind_tools([SubmitFinalAnswer]),
            prompt_file=prompt_file,
            require=state["require"],
            sql_and_result=state["sql_and_result"],
            logger=self.logger
        )

        if message.tool_calls:
            for tc in message.tool_calls:
                if tc["name"] == "SubmitFinalAnswer":
                    state["user_name"] = tc["args"]["final_answer"].get("user_name", state["user_name"])

        return {"messages": [message], "user_name": state["user_name"]}

    def should_end(self, state: AgentState) -> Literal[END, "query_gen"]:
        messages = state.get("messages", [])
        if not messages:
            return END

        last_message = messages[-1]
        return END if hasattr(last_message, "tool_calls") else "correct_query"