from flask import Flask, redirect, request, jsonify
from database_manager import DatabaseManager
from cache_manager import CacheManager

from rag import Loader, Splitter, Embedder, Retriever
from agents import ImageToDescriptionAgent, QueryPreprocessingAgent, SummarizingAgent, QueryAnsweringAgent, ImageDescriptionRelavancyCheckAgent 

app = Flask(__name__)
db = DatabaseManager()

def db_read_json_callback(key):
    split_key = key.split("-")
    customer_id = split_key[0]
    user_id = split_key[1]
    print("DB READ OPERATION")
    return db.read_json(f'database/services/{customer_id}/{user_id}.json')

def db_write_json_callback(key,value):
    split_key = key.split("-")
    customer_id = split_key[0]
    user_id = split_key[1]
    print("DB WRITE OPERATION")
    db.write_json(f'database/services/{customer_id}/{user_id}.json',value)


chat_cache = CacheManager(max_length=10,load_callback=db_read_json_callback,store_callback=db_write_json_callback)

@app.route('/')
def handle_root():
    # to return API usage information
    return redirect("https://www.example.com",code=302)

@app.route('/chat', methods=['POST'])
def chat():
    print("REQUEST RECEIVED")
    body = request.get_json()
    customer_id = body.get("customer_id")
    user_id = body.get("user_id")
    query = body.get("query")
    key = f'{customer_id}-{user_id}'

    vector_store_path = f'database/services/{customer_id}/rag_context/vector_store'
    print("LOADING VECTOR STORE...")
    vector_store = Embedder().get_vector_store(vector_store_path)

    print(vector_store.index.ntotal)

    retriever = Retriever(vector_store)

    print("BREAKING QUERY...")
    queries = QueryPreprocessingAgent().break_query(query)
    print(queries)
    responses = []
    
    def evaluate_single_query(query):
        print("RETRIEVING RELATED DOCUMENTS")
        retrieved_documents = retriever.retrieve(query)
        context = Splitter().merge_documents_to_text(retrieved_documents)
        print(f'EVALUATING {query}')
        response = QueryAnsweringAgent().answer_query(query, context)
        print(response)
        return response
    
    for query in queries:
        responses.append(evaluate_single_query(query))

    return jsonify(responses)
    # first split the query into sub questions
    # evaluate each sub question independently

#     get_data = chat_cache.get(key)
#     get_data["chat_history_summary"] = "update1"
#     get_data["chat_history"][0]["chat_id"] = "update2"
#     chat_cache.update(key, get_data)

if __name__ == '__main__':
    app.run(debug=True)