from flask import Flask, redirect, request, jsonify
from database_manager import DatabaseManager
from cache_manager import CacheManager

from rag import Loader, Splitter, Embedder, Retriever
from agents import ImageToDescriptionAgent, QueryPreprocessingAgent, SummarizingAgent, QueryAnsweringAgent, ImageDescriptionRelavancyCheckAgent 

import os
import json
from uuid import uuid4
from datetime import datetime

app = Flask(__name__)
db = DatabaseManager()

def db_read_json_callback(key):
    print("DB READ OPERATION")
    
    split_key = key.split("-")
    customer_id = split_key[0]
    user_id = split_key[1]
    path = f'database/services/{customer_id}/{user_id}.json'
    
    if not os.path.exists(path):
        default_chat_context = {
            "user_id":user_id,
            "chat_history":[],
            "chat_history_summary":""
        }
        
        db.write_json(path, default_chat_context)

    return db.read_json(path)

def db_write_json_callback(key,value):
    print("DB WRITE OPERATION")
    split_key = key.split("-")
    customer_id = split_key[0]
    user_id = split_key[1]
    db.write_json(f'database/services/{customer_id}/{user_id}.json',value)


chat_cache = CacheManager(max_length=10,load_callback=db_read_json_callback,store_callback=db_write_json_callback)

@app.route('/')
def handle_root():
    # to return API usage information
    return redirect("https://www.example.com",code=302)

@app.route('/upload', methods = ['POST'])
def upload():
    print("UPLOAD REQUEST RECEIVED")
    file = request.files.get("file")
    customer_id = request.form.get("customer_id")
    moderator_id = request.form.get("moderator_id")

    print(file)
    print(customer_id)
    print(moderator_id)

    if file and file.filename.lower().endswith(".pdf"):
        # handle file addition to vector store
        path = f'database/services/{customer_id}/rag_context/{file.filename}'
        file.save(path)

        print(path)
        
        pages = Loader().load_pdf(path)
        chunks = Splitter().split(pages)
        print(chunks)
        vector_store = Embedder().embed(f'database/services/{customer_id}/rag_context/vector_store',chunks)
        print(vector_store.index.ntotal)

    return "hello"

@app.route('/chat', methods=['POST'])
def chat():
    print("CHAT REQUEST RECEIVED")
    body = request.get_json()
    customer_id = body.get("customer_id")

    if not os.path.isdir(f'database/services/{customer_id}'):
        return "invalid customer_id"
    
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
    
    for q in queries:
        responses.append(evaluate_single_query(q))

    aggregate_response = ""
    for response in responses:
        aggregate_response += response+"\n"

    # UPDATING CHAT CONTEXT
    chat_context = chat_cache.get(key)

    user_chat_record = {
            "chat_id":str(uuid4()),
            "from": "user",
            "timestamp":str(datetime.now()),
            "type": "text",
            "content": query
        }
    
    bot_chat_record = {
            "chat_id":str(uuid4()),
            "from": "bot",
            "timestamp":str(datetime.now()),
            "type": "text",
            "content": aggregate_response
        }
    
    print("USER CHAT RECORD-------------------")
    print(user_chat_record)
    print("BOT CHAT RECORD-------------------")
    print(bot_chat_record)
    
    chat_context["chat_history"].append(user_chat_record)
    chat_context["chat_history"].append(bot_chat_record)
    print("UPDATED CHAT CONTEXT-------------------")
    print(chat_context)
    chat_cache.update(key, chat_context)

    # print("SUMMARIZING AGGREGATE RESPONSE...")
    # summarized_response = SummarizingAgent().summarize_query(aggregate_response)
    # print(summarized_response)

    return jsonify(aggregate_response)
    # first split the query into sub questions
    # evaluate each sub question independently

#     get_data = chat_cache.get(key)
#     get_data["chat_history_summary"] = "update1"
#     get_data["chat_history"][0]["chat_id"] = "update2"
#     chat_cache.update(key, get_data)

if __name__ == '__main__':
    app.run(debug=True)