"""Streamlit UI for the SQL Server AI expense tracker."""

import json
import os
from datetime import date

import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI

from mydb import execute_query, get_schema, run_query


load_dotenv()

TOOLS = [
    {
        "type": "function",
        "name": "get_schema",
        "description": "Get columns and data types for a table in the dbo schema.",
        "parameters": {
            "type": "object",
            "properties": {"table_name": {"type": "string"}},
            "required": ["table_name"],
        },
    },
    {
        "type": "function",
        "name": "execute_query",
        "description": (
            "Execute one parameterized INSERT, UPDATE, or DELETE query against SQL Server. "
            "Use this immediately when the user records a purchase or requests a change."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "params": {"type": "object"},
            },
            "required": ["query"],
        },
    },
    {
        "type": "function",
        "name": "run_query",
        "description": "Run one read-only SELECT query for expenses, totals, reports, or searches.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "params": {"type": "object"},
            },
            "required": ["query"],
        },
    },
]


@st.cache_resource
def get_openai_client(api_key: str) -> OpenAI:
    return OpenAI(api_key=api_key)


def execute_tool(tool_name: str, arguments: dict) -> object:
    if tool_name == "get_schema":
        return get_schema(arguments["table_name"]).to_dict(orient="records")
    if tool_name == "run_query":
        return run_query(
            arguments["query"], arguments.get("params")
        ).to_dict(orient="records")
    if tool_name == "execute_query":
        return execute_query(arguments["query"], arguments.get("params"))
    raise ValueError(f"Unknown tool: {tool_name}")


def ask_expense_agent(
    conversation: list[dict], client: OpenAI, model: str
) -> tuple[str, list[dict]]:
    transcript = "\n".join(
        f"{message['role'].upper()}: {message['content']}"
        for message in conversation
    )
    response = client.responses.create(
        model=model,
        input=(
            "You are an AI expense tracker connected to SQL Server database retail. "
            "The canonical purchase table is dbo.expenses. Never ask the user to "
            "choose between expenses, Purchases, or orders. Use dbo.expenses for all "
            "expense records. Use execute_query immediately when the conversation has "
            "enough details for a purchase. If a required value such as amount is "
            "missing, ask only for that missing value. Treat follow-up messages such "
            "as answers to earlier messages and preserve their context. Use run_query "
            "for read-only questions. Never generate SQL in your final answer without "
            "using the appropriate tool. Today's date is "
            f"{date.today().isoformat()}.\n\nConversation:\n{transcript}"
        ),
        tools=TOOLS,
        tool_choice="auto",
    )
    activity = []

    while True:
        function_calls = [item for item in response.output if item.type == "function_call"]
        if not function_calls:
            return response.output_text, activity

        tool_outputs = []
        for function_call in function_calls:
            arguments = json.loads(function_call.arguments)
            record = {"tool": function_call.name, "arguments": arguments}
            try:
                result = execute_tool(function_call.name, arguments)
                record["result"] = result
                output = {"success": True, "result": result}
            except Exception as error:
                record["error"] = str(error)
                output = {"success": False, "error": str(error)}
            activity.append(record)
            tool_outputs.append(
                {
                    "type": "function_call_output",
                    "call_id": function_call.call_id,
                    "output": json.dumps(output, default=str),
                }
            )

        response = client.responses.create(
            model=model,
            previous_response_id=response.id,
            input=tool_outputs,
            tools=TOOLS,
        )


def show_activity(activity: list[dict]) -> None:
    if not activity:
        return
    tool_names = ", ".join(item["tool"] for item in activity)
    st.info(f"Tool called: `{tool_names}`")
    with st.expander("Database activity details", expanded=False):
        for item in activity:
            st.write(f"**Tool:** `{item['tool']}`")
            st.write("**Arguments:**")
            st.json(item["arguments"])
            if "error" in item:
                st.error(item["error"])
            else:
                st.json(item.get("result", {}))


def main() -> None:
    st.set_page_config(page_title="AI Expense Tracker", page_icon="$", layout="wide")
    st.title("AI Expense Tracker")
    st.caption("Record purchases and manage SQL Server data using natural language.")

    with st.sidebar:
        st.header("Settings")
        model = st.text_input("OpenAI model", os.getenv("OPENAI_MODEL", "gpt-5.6-sol"))
        st.caption("SQL Server: localhost\\MSSQLSERVER03")
        st.caption("Database: retail")
        if st.button("Clear chat"):
            st.session_state.messages = []
            st.rerun()

    if "messages" not in st.session_state:
        st.session_state.messages = []

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            show_activity(message.get("activity", []))

    user_question = st.chat_input("Try: I ate a burger today for $20")
    if not user_question:
        return

    st.session_state.messages.append({"role": "user", "content": user_question})
    with st.chat_message("user"):
        st.markdown(user_question)

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        st.error("OPENAI_API_KEY is missing. Add it to your .env file.")
        return

    with st.chat_message("assistant"):
        with st.spinner("Working with your expense data..."):
            try:
                answer, activity = ask_expense_agent(
                    st.session_state.messages, get_openai_client(api_key), model
                )
                st.markdown(answer)
                show_activity(activity)
                st.session_state.messages.append(
                    {"role": "assistant", "content": answer, "activity": activity}
                )
            except Exception as error:
                st.error(f"Request failed: {error}")


if __name__ == "__main__":
    main()
