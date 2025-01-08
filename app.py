from flask import Flask, request, jsonify
from database_manager import DatabaseManager
from cache_manager import CacheManager

from rag import Loader, Splitter, Embedder, Retriever
from agents import QueryPreprocessingAgent, SummarizingAgent, QueryAnsweringAgent, ImageDescriptionRelavancyCheckAgent 

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
chat_cache = CacheManager(max_length=config["chat_cache_size"],load_callback=chat_context_read_callback,store_callback=chat_context_write_callback)

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
    welcome_chat_context = append_chat_record_to_chat_history(key, "bot", "text", config["custom_welcome_message"])

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
    key = f'{customer_id}-{user_id}'

    customer_config = db.read_json(f'database/services/{customer_id}/config.json')
    allow_multimodal_for_images = customer_config["allow_multimodal_for_images"]

    image_vector_store = None
    image_retriever = None
    top_image_description_document = None
    relavancy_check_response = None
    
    print("GETTING VECTOR STORE...")
    vector_store = Embedder().get_vector_store(f'database/services/{customer_id}/knowledge_base/vector_store')
    if allow_multimodal_for_images:     
        image_vector_store = Embedder().get_vector_store(f'database/services/{customer_id}/knowledge_base/image_vector_store')

    print("INITIALIZING RETRIEVER...")
    retriever = Retriever(vector_store)
    if allow_multimodal_for_images:  
        image_retriever = Retriever(image_vector_store)

    print("BREAKING QUERY...")
    queries = QueryPreprocessingAgent().break_query(query)
    print(queries)

    print("RETRIEVING RELATED DOCUMENTS")
    retrieved_documents = []
    response_array = []

    for q in queries:
        retrieved_documents += retriever.retrieve(q)
        if allow_multimodal_for_images:  
            top_image_description_document = image_retriever.retrieve(q)[0]
            relavancy_check_response = ImageDescriptionRelavancyCheckAgent().answer_query(query, top_image_description_document, top_image_description_document)
            if "yes" in relavancy_check_response.lower():
                response_array.append(append_chat_record_to_chat_history(key, "bot", "image", db.read_image(top_image_description_document.metadata.get("source"))))
                image_relavant_response = QueryAnsweringAgent().answer_query(query, top_image_description_document)
                response_array.append(append_chat_record_to_chat_history(key, "bot", "text", image_relavant_response))


    print("MERGING RETRIEVED DOCUMENTS CONTENT...")
    context = Splitter().merge_documents_to_text(retrieved_documents)

    context = f"PREVIOUS CHAT SUMMARY : {chat_cache.get(key)["chat_history_summary"]}\n{context}"
    
    print(f'EVALUATING {query}')
    response = QueryAnsweringAgent().answer_query(query, context)

    # change query to context to get images relavant to context. but also want to retrieve images not bound to any context as well
    # merged_descriptions = Splitter().merge_documents_to_text(image_description_documents)
    # change merged_descriptions to context to get context relavant images, or maybe we can keep it directly relavant to the query
    # relavancy_check_response = ImageDescriptionRelavancyCheckAgent().answer_query(query, merged_descriptions, merged_descriptions)

    append_chat_record_to_chat_history(key, "user", "text", query)
    response_array.append(append_chat_record_to_chat_history(key, "bot", "text", response))
    
    return jsonify({
            "success":"true",
            "message":"query evaluated successfully",
            "response":response_array
        })

@app.route("/chat/history", methods = ["POST"])
def handle_history():
    # we receive request and we send a page of chat history let say 3...
    # request format
    # [0 1 2 3 4 5 6 7 8 9(most recent)] for 0th page... (len - 1) to (len-page_size*page_number-page_size)...for 1'st page (len-page_size*page_number-1) to (len-len-page_size*page_number-page_size) if start is less than 0, start should be 0 and end should be 
    # if end is greater than len-1, end should be len-1... case will never be achieved
    """
    {
        customer_id
        user_id
        page_number
        page_size
    }
    """
    body = request.get_json()
    customer_id = body.get("customer_id")

    if not os.path.isdir(f'database/services/{customer_id}'):
        return jsonify({
            "success":"false",
            "message":f'{customer_id} customer does not exist (invalid customer id)'
        })
    
    user_id = body.get("user_id")
    query = body.get("query")
    page_number = body.get("page_number")
    page_size = body.get("page_size")
    key = f'{customer_id}-{user_id}'

    chat_context = chat_cache.get(key)
    chat_history = chat_context["chat_history"]
    chat_history_size = chat_context["chat_history_size"]

    end = chat_history_size - page_number*page_size - 1
    start = chat_history_size - page_number*page_size - page_size

    print(start)
    print(end)

    if start<0:
        start = 0
    
    if end < 0:
        end = -1
            
    print(start)
    print(end)
    print(len(chat_history[start:end+1]))
    
    return jsonify({
        "success":"true",
        "message":"page fetched successfully (0th page refers to the most recent chats)",
        "chat_history_page":chat_history[start:end+1]
    })

@app.route('/moderator/upload', methods = ['POST'])
def handle_upload():
    file = request.files.get("file")
    customer_id = request.form.get("customer_id")
    moderator_id = request.form.get("moderator_id")

    if file:   
        if file.filename.lower().endswith(".pdf"):
            path = f'database/services/{customer_id}/knowledge_base/{str(uuid4())}{file.filename}'
            file.save(path)
            pages = Loader().load_pdf(path)
            image_descriptions = Loader().load_images_from_pdf(path)
            chunks = Splitter().split(pages)
            vector_store = Embedder().embed(f'database/services/{customer_id}/knowledge_base/vector_store',chunks)
            image_vector_store = Embedder().embed(f'database/services/{customer_id}/knowledge_base/image_vector_store',image_descriptions)

        if file.filename.lower().endswith(".txt"):
            path = f'database/services/{customer_id}/knowledge_base/{str(uuid4())}{file.filename}'
            file.save(path)
            pages = Loader().load_text(path)
            chunks = Splitter().split(pages)
            vector_store = Embedder().embed(f'database/services/{customer_id}/knowledge_base/vector_store',chunks)
            print(vector_store.index.ntotal)

        if file.filename.lower().endswith((".png", ".jpg", ".jpeg")):
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

    config = db.read_json("database/environment/config.json")

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