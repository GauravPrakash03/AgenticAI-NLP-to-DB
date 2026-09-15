import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.llm_pick import pick_llm
from utils.etl_tools import ETL_tools
from Models.schema import AgentSchema, ETLAgentSchema, RouterSchema, DataAgentSchema
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langgraph.graph import StateGraph, START, END
from langchain.tools import tool
#from agents import etl_analyst, sql_analyst
from agents.etl_analyst import etl_analyst
from agents.sql_analyst import sql_analyst

from IPython.display import display, Image

from dotenv import load_dotenv
load_dotenv()

#------------------ DATA AGENT GRAPH -------------------#

def router_node(state:DataAgentSchema):

    llm = pick_llm("low")
    llm_router = llm.with_structured_output(RouterSchema)

    message=state.messages[-1].content
    router_result = llm_router.invoke(message)

    if isinstance(router_result, RouterSchema):
        route_response = router_result.answer

    elif isinstance(router_result, dict):
        route_response = router_result["answer"]

    else:
        raise TypeError("Unexpected router response type")

    state.route_response = route_response

    return state

def etl_node(state:DataAgentSchema):

    message = state.messages[-1].content

    response = etl_analyst.invoke({"messages":[HumanMessage(content=f"""{message}""")]})
    child_messages = response.get("messages", [])
    final_message = child_messages[-1] if child_messages else None
    state.user_question = str(message)
    if final_message is not None:
        state.final_answer = str(final_message.content)
        state.etl_result = state.final_answer
        state.messages = state.messages + [
            AIMessage(content=state.final_answer)
        ]

    return state

def sql_node(state:DataAgentSchema):

    message = state.messages[-1].content

    input_schema = {
        "messages" : [],
        "user_question" : f"{message}",
        "curated_ques" : "",
        "prompt_query_context" : "",
        "generated_sql_query" : "",
        "is_safe" : "No",
        "comments" : "",
        "sql_query_execution_result" : "",
        "final_answer" : ""
    }

    response = sql_analyst.invoke(input_schema)
    state.user_question = message
    state.curated_ques = str(response["curated_ques"])
    state.generated_sql_query = str(response["generated_sql_query"])
    state.is_safe = str(response["is_safe"])
    state.comments = str(response["comments"])
    state.sql_query_execution_result = str(response["sql_query_execution_result"])
    state.final_answer = str(response["final_answer"])

    state.messages = state.messages + [
        AIMessage(content=state.final_answer)
    ]

    return state

data_agent_graph = StateGraph(DataAgentSchema)

data_agent_graph.add_node("router_node", router_node)
data_agent_graph.add_node("etl_node", etl_node)
data_agent_graph.add_node("sql_node", sql_node)

data_agent_graph.add_edge(START, "router_node")

def route_edge(state: DataAgentSchema) -> str:
    if state.route_response == "sql":
        return "sql_node"
    elif state.route_response == "etl":
        return "etl_node"
    else:
        raise ValueError(f"Invalid route response: {state.route_response}")


data_agent_graph.add_conditional_edges("router_node", route_edge,
                                      {
                                          "sql_node": "sql_node",
                                          "etl_node": "etl_node"
                                      })

data_agent = data_agent_graph.compile()


if __name__ == "__main__":

    # Optional

#    img = Image(data_agent.get_graph().draw_mermaid_png())
#    with open("data_agent_graph.png", "wb") as f:
#        f.write(img.data)

    response = data_agent.invoke(
        DataAgentSchema(
            messages=[HumanMessage(content="I want to extract the data from the API endpoint 'https://pokeapi.co/api/v2/pokemon' and save it to data/extract folder in the csv format. Once the data is extracted, I want to also transform the data and store the transformed data into data/transform folder.")],
            route_response=""
            )
            )

    print(response)
