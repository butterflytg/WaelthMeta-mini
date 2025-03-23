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
from typing import Annotated, Literal, Any,Dict

class SubmitFinalAnswer(BaseModel):
    """Submit the final answer to the user based on the query results."""

    final_answer: Dict[str, Any] = Field(..., description="The final answer to the user")

class WorkFlow:
    sqLite= None
    def __init__(self,sqLite,logger=None):

        self.logger=logger
        WorkFlow.sqLite=sqLite
        toolkit = SQLDatabaseToolkit(db=sqLite.get_sqlDatabase(), llm=get_new_llm())
        tools = toolkit.get_tools()

        self.list_tables_tool = next(tool for tool in tools if tool.name == "sql_db_list_tables")
        self.get_schema_tool = next(tool for tool in tools if tool.name == "sql_db_schema")

        self.workflow = StateGraph(AgentState)

        self.workflow.add_node("login", self.login)

        self.workflow.add_node("judge_query", self.judge_query)

        self.workflow.add_node("first_tool_call", self.first_tool_call)
        self.workflow.add_node("list_tables_tool", self.create_tool_node_with_fallback([self.list_tables_tool]))

        self.model_get_schema = get_new_llm().bind_tools([self.get_schema_tool])
        self.workflow.add_node(
            "model_get_schema",
            lambda state: {
                "messages": [self.model_get_schema.invoke(state["messages"])],
            },
        )
        self.workflow.add_node("get_schema_tool", self.create_tool_node_with_fallback([self.get_schema_tool]))
        self.workflow.add_node("query_gen", self.query_gen_node)
        self.workflow.add_node("correct_query", self.model_check_query)
        self.workflow.add_node("execute_query", self.create_tool_node_with_fallback([self.db_query_tool]))
        self.workflow.add_node("conclude",self.conclude)


        self.workflow.add_conditional_edges(START, self.judge_login_route)

        self.workflow.add_conditional_edges("login", self.should_continue_login)


        self.workflow.add_conditional_edges("judge_query", self.route)

        #self.workflow.add_edge(START, "first_tool_call")
        self.workflow.add_edge("first_tool_call", "list_tables_tool")
        self.workflow.add_edge("list_tables_tool", "model_get_schema")
        self.workflow.add_edge("model_get_schema", "get_schema_tool")
        self.workflow.add_edge("get_schema_tool", "query_gen")
        #self.workflow.add_conditional_edges("query_gen",self.should_continue)
        #self.workflow.add_edge("query_gen", "correct_query")
        self.workflow.add_edge("query_gen", "execute_query")
        #self.workflow.add_edge("correct_query", "execute_query")
        #self.workflow.add_edge("execute_query", "query_gen")
        self.workflow.add_edge("execute_query", "conclude")
        #self.workflow.add_conditional_edges("conclude", self.should_end)
        self.workflow.add_edge("conclude", END)


        self.app = self.workflow.compile()


    def run(self,input):
        result=self.app.invoke(input)
        messages = result["messages"][-1].tool_calls[0]["args"]["final_answer"]["message"]
        user_name=result["user_name"]

        return user_name,messages


    def route(self,state):
        if state["judge_result"]=="only_db":
            return "first_tool_call"
        elif state["judge_result"]=="db_rag":
            return "rag_retrieval"

    def login(self,state):
        prompt_file = get_prompt_file("judge_username.txt")
        message = get_llm_chain(llm=get_new_llm().bind_tools([self.list_tables_tool,SubmitFinalAnswer],tool_choice="required"), prompt_file=prompt_file, require=state["require"],logger=self.logger)
        return {"messages": [message]}

    def should_continue_login(self,state: AgentState) -> Literal[END, "list_tables_tool"]:
        messages = state["messages"]
        last_message = messages[-1]
        if last_message.tool_calls[0]["name"]=="sql_db_list_tables":
            return "list_tables_tool"
        elif last_message.tool_calls[0]["name"]=="SubmitFinalAnswer":
            return END

    def judge_login_route(self,state):
        if state.get("user_name")=="" or state.get("user_name") is None:
            return "login"
        else:
            return "judge_query"

    def create_tool_node_with_fallback(self,tools: list) -> RunnableWithFallbacks[Any, dict]:
        """
        Create a ToolNode with a fallback to handle errors and surface them to the agent.
        """
        return ToolNode(tools).with_fallbacks(
            [RunnableLambda(self.handle_tool_error)], exception_key="error"
        )

    def handle_tool_error(self,state) -> dict:
        error = state.get("error")
        tool_calls = state["messages"][-1].tool_calls
        return {
            "messages": [
                ToolMessage(
                    content=f"Error: {repr(error)}\n please fix your mistakes.",
                    tool_call_id=tc["id"],
                )
                for tc in tool_calls
            ]
        }

    def should_continue(self,state: AgentState) -> Literal[END, "correct_query", "query_gen"]:
        messages = state["messages"]
        last_message = messages[-1]
        # If there is a tool call, then we finish
        if getattr(last_message, "tool_calls", None):
            return END
        if last_message.content.startswith("错误"):
            return "query_gen"
        else:
            return "correct_query"

    def first_tool_call(self,state: AgentState) -> dict[str, list[AIMessage]]:
        return {
            "messages": [
                AIMessage(
                    content="",
                    tool_calls=[
                        {
                            "name": "sql_db_list_tables",
                            "args": {},
                            "id": "tool_abcd123",
                        }
                    ],
                )
            ]
        }

    def query_gen_node(self,state: AgentState):

        if "list_tables_tool_result" not in state or not state["list_tables_tool_result"]:
            state["list_tables_tool_result"] = None  # 或者设置一个默认值

        if "get_schema_tool_result" not in state or not state["get_schema_tool_result"]:
            state["get_schema_tool_result"] = None  # 或者设置一个默认值

        # if "sql_and_result" not in state or not state["sql_and_result"]:
        #     state["sql_and_result"] = []  # 或者设置一个默认值
        #
        # if "tool_feedback" not in state or not state["tool_feedback"]:
        #     state["tool_feedback"] = []  # 或者设置一个默认值

        # if "user_name" not in state or not state["user_name"]:
        #     state["user_name"] = None  # 或者设置一个默认值

        messages = state.get("messages", [])
        for message in messages:
            if message.type == "tool":
                if message.name == "sql_db_list_tables":
                    state["list_tables_tool_result"] = message.content
                elif message.name == "sql_db_schema":
                    state["get_schema_tool_result"] = message.content
                # elif message.name == "db_query_tool":
                #     tool_call_id = message.tool_call_id
                #     for message_temp in messages:
                #         if message_temp.type == "ai" and message_temp.tool_calls:
                #             for tool_call in message_temp.tool_calls:
                #                 if tool_call["id"] == tool_call_id:
                #                     state["sql_and_result"].append({tool_call["args"]["query"]: message.content})
                # elif message.name == "SubmitFinalAnswer":
                #     state["tool_feedback"].append(message.content)




        # Sometimes, the LLM will hallucinate and call the wrong tool. We need to catch this and return an error message.
        prompt_file = get_prompt_file("sql_generate.txt")
        message = get_llm_chain(llm=get_new_llm().bind_tools([self.db_query_tool], tool_choice="required"),
                                prompt_file=prompt_file,require=state["require"],
                                list_tables_tool_result=state["list_tables_tool_result"],
                                get_schema_tool_result=state["get_schema_tool_result"],
                                user_name=state["user_name"],
                                current_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                #tool_feedback=state["tool_feedback"],
                                logger=self.logger)
        # tool_messages = []
        # if message.tool_calls:
        #     for tc in message.tool_calls:
        #         if tc["name"] != "SubmitFinalAnswer":
        #             tool_messages.append(
        #                 ToolMessage(
        #                     content=f"错误：调用了错误的工具：{tc['name']}。请修正您的错误。请记住，仅允许调用 SubmitFinalAnswer 来提交最终答案。生成的查询应直接输出，不应使用工具调用。",
        #                     tool_call_id=tc["id"],
        #                     name=tc["name"]
        #                 )
        #             )
        #         else:
        #             if "user_name" in tc["args"]["final_answer"]:
        #                 state["user_name"] = tc["args"]["final_answer"]["user_name"]
        #             if len(state["sql_and_result"]) == 0:
        #                 tool_messages.append(
        #                     ToolMessage(
        #                         content=f"错误：调用了错误的工具：{tc['name']}。请修正您的错误。必须根据sql执行的结果来生成最终答案。",
        #                         tool_call_id=tc["id"],
        #                         name=tc["name"]
        #                     )
        #                 )
        # else:
        #     tool_messages = []
        return {"messages": [message]}
                #"user_name": state["user_name"],
                #"tool_feedback":state["tool_feedback"]}


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
            # 处理 SELECT 语句
            if sql_type == "SELECT":
                cursor.execute(query)
                result = cursor.fetchall()
                cursor.close()
                return result if result else "message: 没有查询到信息."

            # 处理 INSERT / UPDATE / DELETE 语句
            cursor.execute(query)
            connection.commit()  # 确保事务提交
            affected_rows = cursor.rowcount
            cursor.close()
            return f"message: {sql_type} 成功，受影响行数: {affected_rows}"

        except SQLAlchemyError as e:
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