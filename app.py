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
            "chat_history_summary":"",
            "chat_history_size":0
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

@app.route('/chat/connect', methods=['POST'])
def connect():
    print("CONNECT REQUESTED")
    body = request.get_json()
    customer_id = body.get("customer_id")

    if not os.path.isdir(f'database/services/{customer_id}'):
        return jsonify({
            "success":"false",
            "message":f'{customer_id} customer does not exist (invalid customer id)'
        })

    user_id = body.get("user_id")
    key = f'{customer_id}-{user_id}'
    
    config_path = f'database/services/{customer_id}/config.json'
    config = db.read_json(config_path)
    custom_welcome_message = config["custom_welcome_message"]

    append_chat_record_to_chat_history(key, "bot", "text", custom_welcome_message)

    return jsonify({
            "success":"true",
            "type":"text",
            "message":custom_welcome_message
        })


@app.route('/chat/query', methods=['POST'])
def handle_query():
    print("QUERY RECEIVED. PROCESSING QUERY...")
    body = request.get_json()
    customer_id = body.get("customer_id")

    if not os.path.isdir(f'database/services/{customer_id}'):
        return jsonify({
            "success":"false",
            "message":f'{customer_id} customer does not exist (invalid customer id)'
        })
    
    user_id = body.get("user_id")
    query = body.get("query")

    vector_store_path = f'database/services/{customer_id}/rag_context/vector_store'
    print("LOADING VECTOR STORE...")
    vector_store = Embedder().get_vector_store(vector_store_path)

    print("INITIALIZING RETRIEVER...")
    retriever = Retriever(vector_store)

    print("BREAKING QUERY...")
    queries = QueryPreprocessingAgent().break_query(query)
    print(queries)

    print("RETRIEVING RELATED DOCUMENTS")
    
    retrieved_documents = []
    for q in queries:
        print(f"aalu {q}")
        retrieved_documents += retriever.retrieve(q)

    context = Splitter().merge_documents_to_text(retrieved_documents)

    key = f'{customer_id}-{user_id}'
    context = chat_cache.get(key)["chat_history_summary"] + "\n" + context
    
    print(f'EVALUATING {query}')
    response = QueryAnsweringAgent().answer_query(query, context)
    print(response)
    
    # UPDATING CHAT CONTEXT
    append_chat_record_to_chat_history(key, "user", "text", query)
    append_chat_record_to_chat_history(key, "bot", "text", response)

    return jsonify({
            "success":"true",
            "type":"text",
            "message":response
        })

def append_chat_record_to_chat_history(key, by, type, content):
    # required tasks to be performed  1)insert the new chat at the beginning of the chat history
                                    # 2)cyclically remove old chats given a predefined limit
                                    # 3)update chat_history_summary with a new summary

    chat_record = {
        "chat_id":str(uuid4()),
        "from": by,
        "timestamp":str(datetime.now()),
        "type": type,
        "content": content
    }
    chat_context = chat_cache.get(key)

    split_key = key.split("-")
    customer_id = split_key[0]

    config_path = f'database/services/{customer_id}/config.json'
    config = db.read_json(config_path)

    if(chat_context["chat_history_size"]+1 > config["chat_history_window_limit"]):
        chat_context["chat_history"].pop(0)
        chat_context["chat_history_size"] = chat_context["chat_history_size"] - 1

    chat_context["chat_history"].append(chat_record)
    chat_context["chat_history_size"] = chat_context["chat_history_size"] + 1
    chat_context["chat_history_summary"] = SummarizingAgent().summarize_query(f"{chat_context["chat_history_summary"]}\n{content}")

    chat_cache.update(key, chat_context)

if __name__ == '__main__':
    app.run(debug=True)

# to do-
# to wite only those chat contexts to the db which have been modified... maintain a modified flag