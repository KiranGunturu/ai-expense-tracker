from openai import OpenAI
from dotenv import load_dotenv
import json
import os

from mydb import run_query, execute_query, get_schema, get_tables

# Load environment variables from .env file
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Initialize the OpenAI client with the API key
client = OpenAI(api_key=OPENAI_API_KEY)

my_tools = [
    {
        "type": "function",
        "name": "get_schema",
        "description": "Get the schema of a table in the dbo schema and evaluate the columns and their data types to narrow down"
            "the ones most relevant to the query. This will help in constructing the SQL query.",
        "parameters": {
            "type": "object",
            "properties": {
                "table_name": {
                    "type": "string",
                    "description": "The name of the table"
                }
            },
            "required": ["table_name"]
        }
    },
    {
        "type": "function",
        "name": "get_tables",
        "description": "Get all user tables in the dbo schema of the retail database. This will help in constructing the SQL query.",
        "parameters": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "type": "function",
        "name": "execute_query",
        "description": "Execute one parameterized INSERT, UPDATE, or DELETE query against the retail database and commit it. Use this immediately when the user states a purchase or requests a change. Never ask for confirmation.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "One INSERT, UPDATE, or DELETE statement using named parameters such as :amount"
                },
                "params": {
                    "type": "object",
                    "description": "Values for the named SQL parameters"
                }
            },
            "required": ["query"]
        }
    },
    {
        "type": "function",
        "name": "run_query",
        "description": "Run a SQL query and return the result as a DataFrame. This can answer questions about purchases and perform approved data operations.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The SQL query to run"
                },
                "params": {
                    "type": "object",
                    "description": "The parameters for the SQL query"
                }
            },
            "required": ["query"]
        }
    }
]

while True:
    try:
        user_input = input("enter your query:  (or type 'exit' to quit): ")
    except KeyboardInterrupt:
        print("\nExiting the program.")
        break

    if user_input.lower() in ['exit', 'quit']:
        print("Exiting the program.")
        break
    if not user_input.strip():
        print("Please enter a valid query.")
        continue

    response = client.responses.create(
        model="gpt-5.6-sol",
        input=(
            "Record the user's purchase immediately when the message describes a purchase. "
            "Use execute_query for INSERT, and use run_query for read-only questions.\n\n"
            f"User request: {user_input}"
        ),
        tools=my_tools,
        tool_choice="required",
    )
    #print(response.output_text)

    while True:
        function_calls = [
            item for item in response.output if item.type == "function_call"
        ]

        if not function_calls:
            print(response.output_text)
            break

        tool_outputs = []
        print(f"Model requested {len(function_calls)} tool call(s):")
        for call_number, tool_call in enumerate(function_calls, start=1):
            arguments = json.loads(tool_call.arguments)
            print(
                f"  {call_number}. {tool_call.name} "
                f"{arguments}"
            )

            try:
                if tool_call.name == "get_schema":
                    result = get_schema(arguments["table_name"])
                    result = result.to_json(orient="records", date_format="iso")
                elif tool_call.name == "get_tables":
                    result = get_tables().to_json(orient="records")
                elif tool_call.name == "run_query":
                    result = run_query(arguments["query"], arguments.get("params")).to_json(
                        orient="records", date_format="iso"
                    )
                elif tool_call.name == "execute_query":
                    result = execute_query(arguments["query"], arguments.get("params"))
                else:
                    raise ValueError(f"Unknown tool: {tool_call.name}")
                tool_outputs.append({
                    "type": "function_call_output",
                    "call_id": tool_call.call_id,
                    "output": json.dumps(result, default=str),
                })
            except Exception as error:
                tool_outputs.append({
                    "type": "function_call_output",
                    "call_id": tool_call.call_id,
                    "output": json.dumps({"error": str(error)}),
                })

        response = client.responses.create(
            model="gpt-5.6-sol",
            previous_response_id=response.id,
            input=tool_outputs,
            tools=my_tools,
        )