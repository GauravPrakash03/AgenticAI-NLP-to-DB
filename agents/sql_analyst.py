import os, sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__),'..')))
from utils.llm_pick import pick_llm
from Models.schema import AgentSchema, JudgeSchema
from langchain_core.messages import HumanMessage, AIMessage
from utils.database import DatabaseUtil
from langgraph.graph import StateGraph, START, END

from IPython.display import Image, display

from dotenv import load_dotenv
load_dotenv()

#llm_obj = pick_llm("low")
#print(llm_obj.invoke("What is the capital of France?"))

##### AI Agent Code #####

def curate_question(state:AgentSchema)->AgentSchema:

    user_question=state.user_question #bscause this is pydantic model object
    llm=pick_llm("low") #Pick appropriate LLM based on level of the question

    response = llm.invoke(f"Curate the user question: {user_question}").content

    state.curated_ques = response
    state.messages = state.messages + [HumanMessage(content={response})]

    return state


def prompt_query_context(state:AgentSchema)->AgentSchema:

    curated_question = state.curated_ques
    conn_details = {
        "host": os.environ['host'],
        "port": int(os.environ['port']),
        "database": os.environ['database'],
        "user": os.environ['user'],
        "password": os.environ['password']
    }
    obj = DatabaseUtil(conn_details)

    schema_info = obj.schema_details("public")

    # Constructing the prompt query for the agent to generate the SQL query
    prompt = f"""
    You are an SQL analyst agent. Your task is to convert the user's natural language 
    query into Postgres SQL query that can be executed on the database. You are provided 
    with the user's original query and the schema details of the database, including
    table names, column names, data types, and sample data for each table so that 
    you can understand the structure of the database and generate an accurate SQL query.
    Unless user explicitly asks for specific number of rows, always limit the output to 10 rows.
    Note - Just generate the SQL query without any explanation or additional text because
    this query will be executed directly on the database. So, the output should be SQL
    ready to be executed without any modifications.

    User's original query: {curated_question}

    Database schema details: {schema_info}
    """

    state.prompt_query_context = prompt

    return state

# Generate SQL node

def generate_sql(state:AgentSchema)->AgentSchema:

    prompt = state.prompt_query_context

    llm = pick_llm("medium")
    generated_sql_query = llm.invoke(prompt).content
    state.generated_sql_query = generated_sql_query

    return state

# Is safe node

def is_safe_sql(state:AgentSchema)->AgentSchema:

    sql_query = state.generated_sql_query

    llm = pick_llm("medium")
    llm_judge = llm.with_structured_output(JudgeSchema)

    prompt = f"""
    You are an SQL Judge  for data security. Your task is to determine whether the SQL query is 
    safe or not. The SQL query should only be used for data retrieval and should not modify database
    objects in any way. Neither the SQL query nor the prompt should contain any SQL statements
    that can modify the database such as INSERT, UPDATE, DELETE, DROP, ALTER, TRUNCATE, CREATE or 
    any other SQL statement that could change the structure or content of the database. 
    If the SQL query is safe to execute, respond with "Yes" otherwise respond with "No". Additionally,
    provide comments explaining your decision. Here is the SQL query to evaluate:
    {sql_query}
    """

    response = llm_judge.invoke(prompt).model_dump()  #Get structured output in dectionary from pydantic object
    state.is_safe = response['answer']
    state.comments = response['comments']

    return state

def cancelled_sql(state:AgentSchema)->AgentSchema:

    comments = state.comments
    state.final_answer = f"The generated SQL was deemed unsafe to execute. The reason provided by the judge is: {comments}. Therefore, the SQL query will not be executed."
    state.messages = state.messages + [AIMessage(content=f"{state.final_answer}")] #Append the final answer to the message
    
    return state

# Execute the generated SQL node

def execute_sql(state:AgentSchema)->AgentSchema:

    sql_query = state.generated_sql_query

    conn_details = {
        "host": os.environ['host'],
        "port": int(os.environ['port']),
        "database": os.environ['database'],
        "user": os.environ['user'],
        "password": os.environ['password']
    }
    obj = DatabaseUtil(conn_details)
    execution_results = obj.execute_query(sql_query)
    state.sql_query_execution_result = execution_results

    return state


# Representation Node


def represent_final_answer(state:AgentSchema)->AgentSchema:

    execution_result = state.sql_query_execution_result
    curated_question = state.curated_ques

    llm = pick_llm("low")

    prompt = f"""
    You are an SQL analyst agent. Your task is to provide a final answer to the user based on the
    execution result of the SQL query and the user's original question. The final answer should be
    concise, clear, and directly address the user's query. Avoid including any SQL code or technical
    details in the final answer. The final answer should be in a user-friendly format that is easy to
    understand. If the execution result is empty or does not provide a clear answer to the user's question, explain this in the final answer. \n
    Here is the execution result: {execution_result} \n
    Here is the user's original question: {curated_question}
    """

    llm_response = llm.invoke(prompt).content
    state.final_answer = llm_response
    state.messages = state.messages + [AIMessage(content=f"{state.final_answer}")] #Append the final answer to the message

    return state

#----------------------------------- Graph Building -------------------------------------#

# Nodes
sql_agent_graph = StateGraph(AgentSchema)

sql_agent_graph.add_node(curate_question, name="curate_question")
sql_agent_graph.add_node(prompt_query_context, name="prompt_query_context")
sql_agent_graph.add_node(generate_sql, name="generate_sql")
sql_agent_graph.add_node(is_safe_sql, name="is_safe_sql")
sql_agent_graph.add_node(cancelled_sql, name="cancelled_sql")
sql_agent_graph.add_node(execute_sql, name="execute_sql")
sql_agent_graph.add_node(represent_final_answer, name="represent_final_answer")

# Edges

sql_agent_graph.add_edge(START,"curate_question")
sql_agent_graph.add_edge("curate_question","prompt_query_context")
sql_agent_graph.add_edge("prompt_query_context","generate_sql")
sql_agent_graph.add_edge("generate_sql","is_safe_sql")

# Conditional Edge Function

def is_safe_sql_edge(state:AgentSchema)->str:
    is_safe = state.is_safe

    if is_safe.lower() == "yes":
        return "execute_sql"
    else:
        return "cancelled_sql"

sql_agent_graph.add_conditional_edges(
    "is_safe_sql",
    is_safe_sql_edge,
    {
        "execute_sql": "execute_sql",
        "cancelled_sql": "cancelled_sql",
    })

#sql_agent_graph.add_edge("is_safe_sql","execute_sql")
#sql_agent_graph.add_edge("is_safe_sql","cancelled_sql")

sql_agent_graph.add_edge("cancelled_sql",END)
sql_agent_graph.add_edge("execute_sql","represent_final_answer")
sql_agent_graph.add_edge("represent_final_answer",END)

if __name__ == "__main__":
    # Compile the graph
    
    sql_analyst = sql_agent_graph.compile()
    img = Image(sql_analyst.get_graph().draw_mermaid_png())

    with open("sql_analyst_graph.png", "wb") as f:
        f.write(img.data)

    input_schema = {
        "messages" : [],
        "user_question" : "What are the different types of payment methods that we have in our database?",
        "curated_ques" : "",
        "prompt_query_context" : "",
        "generated_sql_query" : "",
        "is_safe" : "No",
        "comments" : "",
        "sql_query_execution_result" : "",
        "final_answer" : ""
    }

    # Execute the Graph
    sql_analyst_response = sql_analyst.invoke(input_schema)
    print(sql_analyst_response['messages'])
    print("******************************")
    print(sql_analyst_response['user_question'])
    print("******************************")
    print(sql_analyst_response['curated_ques'])
    print("******************************")
    print(sql_analyst_response['generated_sql_query'])
    print("******************************")
    print(sql_analyst_response['sql_query_execution_result'])
    print("******************************")
    print(sql_analyst_response['prompt_query_context'])
    print("******************************")
    print(sql_analyst_response['comments'])
    print("******************************")
    print(sql_analyst_response['final_answer'])
            
