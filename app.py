from flask import Flask, request, jsonify
from database_manager import DatabaseManager
from cache_manager import CacheManager

from rag import Loader, Splitter, Embedder, Retriever
from agents import ImageToDescriptionAgent, QueryPreprocessingAgent, SummarizingAgent, QueryAnsweringAgent, ImageDescriptionRelavancyCheckAgent 

import os
from uuid import uuid4
from datetime import datetime

app = Flask(__name__)
db = DatabaseManager()

def chat_context_read_callback(key):
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

def chat_context_write_callback(key,value):
    split_key = key.split("-")
    customer_id = split_key[0]
    user_id = split_key[1]
    db.write_json(f'database/services/{customer_id}/{user_id}.json',value)

config = db.read_json("database/environment/config.json")
chat_cache_size = config["chat_cache_size"]
chat_cache = CacheManager(max_length=chat_cache_size,load_callback=chat_context_read_callback,store_callback=chat_context_write_callback)

@app.route('/')
def handle_root():
    return jsonify({
        "success":"true",
        "message":"welcome to Toofan chat !"
    })

@app.route('/chat/connect', methods=['POST'])
def handle_connect():
    body = request.get_json()
    customer_id = body.get("customer_id")

    if not os.path.isdir(f'database/services/{customer_id}'):
        return jsonify({
            "success":"false",
            "message":f'{customer_id} customer does not exist (invalid customer id)'
        })

    user_id = body.get("user_id")
    key = f'{customer_id}-{user_id}'
    
    config = db.read_json(f'database/services/{customer_id}/config.json')
    custom_welcome_message = config["custom_welcome_message"]

    welcome_chat_context = append_chat_record_to_chat_history(key, "bot", "text", custom_welcome_message)

    return jsonify({
            "success":"true",
            "message":"connected successfully",
            "response":[{**welcome_chat_context }]
        })


@app.route('/chat/query', methods=['POST'])
def handle_query():
    body = request.get_json()
    customer_id = body.get("customer_id")

    if not os.path.isdir(f'database/services/{customer_id}'):
        return jsonify({
            "success":"false",
            "message":f'{customer_id} customer does not exist (invalid customer id)'
        })
    
    user_id = body.get("user_id")
    query = body.get("query")

    print("GETTING VECTOR STORE...")
    vector_store = Embedder().get_vector_store(f'database/services/{customer_id}/knowledge_base/vector_store')
    image_vector_store = Embedder().get_vector_store(f'database/services/{customer_id}/knowledge_base/image_vector_store')

    print("INITIALIZING RETRIEVER...")
    retriever = Retriever(vector_store)
    image_retriever = Retriever(image_vector_store)

    print("BREAKING QUERY...")
    queries = QueryPreprocessingAgent().break_query(query)
    print(queries)

    print("RETRIEVING RELATED DOCUMENTS")
    retrieved_documents = []
    for q in queries:
        retrieved_documents += retriever.retrieve(q)

    print("MERGING RETRIEVED DOCUMENTS CONTENT...")
    context = Splitter().merge_documents_to_text(retrieved_documents)

    key = f'{customer_id}-{user_id}'
    context = f"previous chat summary : {chat_cache.get(key)["chat_history_summary"]}\n{context}"
    
    print(f'EVALUATING {query}')
    response = QueryAnsweringAgent().answer_query(query, context)

    # change query to context to get images relavant to context
    image_description_documents = image_retriever.retrieve(query)
    merged_descriptions = Splitter().merge_documents_to_text(image_description_documents)
    # change merged_descriptions to context to get context relavant images, or maybe we can keep it directly relavant to the query
    relavancy_check_response = ImageDescriptionRelavancyCheckAgent().answer_query(query, merged_descriptions, merged_descriptions)
    
    response_array = []
    
    append_chat_record_to_chat_history(key, "user", "text", query)
    response_array.append(append_chat_record_to_chat_history(key, "bot", "text", response))
    
    if "yes" in relavancy_check_response.lower():
        response_array.append(append_chat_record_to_chat_history(key, "bot", "image", db.read_image(image_description_documents[0].metadata.get("source"))))
        image_relavant_response = QueryAnsweringAgent().answer_query(query, merged_descriptions)
        response_array.append(append_chat_record_to_chat_history(key, "bot", "text", image_relavant_response))

    return jsonify({
            "success":"true",
            "message":"query evaluated successfully",
            "response":response_array
        })

@app.route('/upload', methods = ['POST'])
def handle_upload():
    file = request.files.get("file")
    customer_id = request.form.get("customer_id")
    moderator_id = request.form.get("moderator_id")

    if file:   
        print("file exists")
        if file.filename.lower().endswith(".pdf"):
            path = f'database/services/{customer_id}/knowledge_base/{str(uuid4())}{file.filename}'
            file.save(path)
            pages = Loader().load_pdf(path)
            image_descriptions = Loader().load_images_from_pdf(path)
            chunks = Splitter().split(pages)
            vector_store = Embedder().embed(f'database/services/{customer_id}/knowledge_base/vector_store',chunks)
            image_vector_store = Embedder().embed(f'database/services/{customer_id}/knowledge_base/image_vector_store',image_descriptions)
            print(f"meow {image_descriptions}")

        if file.filename.lower().endswith(".txt"):
            path = f'database/services/{customer_id}/knowledge_base/{str(uuid4())}{file.filename}'
            file.save(path)
            pages = Loader().load_text(path)
            chunks = Splitter().split(pages)
            vector_store = Embedder().embed(f'database/services/{customer_id}/knowledge_base/vector_store',chunks)
            print(vector_store.index.ntotal)

        if file.filename.lower().endswith((".png", ".jpg", ".jpeg")):
            print("file is an image")
            path = f'database/services/{customer_id}/knowledge_base/{str(uuid4())}{file.filename}'
            file.save(path)
            image_descriptions = Loader().load_image(path)
            vector_store = Embedder().embed(f'database/services/{customer_id}/knowledge_base/image_vector_store',image_descriptions)
            print(vector_store.index.ntotal)

        return jsonify({
            "success":"true",
            "message":"file uploaded successfully"
        })

    return jsonify({
            "success":"false",
            "message":"file upload failed. no file provided or invalid file format (.pdf, .txt, .jpg, .jpeg, .png) allowed"
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

    return chat_record

if __name__ == '__main__':
    app.run(debug=True)

# to do-
# to wite only those chat contexts to the db which have been modified... maintain a modified flag