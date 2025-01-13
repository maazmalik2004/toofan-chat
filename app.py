from flask import Flask, request, jsonify
import asyncio
import os
from uuid import uuid4
from datetime import datetime

from FileSystemInterface import FileSystemInterface
from ResourceManager import ResourceManager
from ChatHistoryManager import   ChatHistoryManager

from rag import KnowledgeArtifactLoader, LangchainDocumentsSplitter,LangchainDocumentsMerger,  LangchainDocumentChunksEmbedder, LangchainDocumentChunksRetriever
from agents import QueryPreprocessingAgent, SummarizingAgent, QueryAnsweringAgent, ImageDescriptionRelavancyCheckAgent, WatchmanAgent, GeneralQueryAnsweringAgent

from dotenv import load_dotenv
load_dotenv()

app = Flask(__name__)

rm = ResourceManager(location_interface_map = {
             "file_system": FileSystemInterface()
         })
chat_history_manager = ChatHistoryManager(resource_manager=rm)

# config = rm.get("file_system/database/environment/config.json")
@app.route('/')
def handle_root():
    return jsonify({
        "success":"true",
        "message":"welcome to Toofan chat !"
    })

@app.route('/chat/connect', methods=['POST'])
async def handle_connect():
    body = request.get_json()
    customer_id = body.get("customer_id")
    user_id = body.get("user_id")
    key = f'{customer_id}-{user_id}'
    
    config = rm.get(f'file_system/database/services/{customer_id}/config.json')
    welcome_chat_context = chat_history_manager.append(customer_id, user_id, "bot", "text", config["custom_welcome_message"])

    return jsonify({
            "success":"true",
            "message":"connected successfully",
            "response":[{**welcome_chat_context }]
        })


@app.route('/chat/query', methods=['POST'])
async def handle_query():
    body = request.get_json()
    customer_id = body.get("customer_id")
    user_id = body.get("user_id")
    query = body.get("query")

    customer_config = rm.get(f'file_system/database/services/{customer_id}/config.json')
    allow_multimodal_for_images = customer_config["allow_multimodal_for_images"]

    image_vector_store = None
    image_retriever = None
    top_image_document = None
    relavancy_check_decision = None
    
    print("GETTING VECTOR STORE...")
    vector_store = LangchainDocumentChunksEmbedder().get_vector_store(f'database/services/{customer_id}/knowledge_base/vector_store')
    if allow_multimodal_for_images:     
        image_vector_store = LangchainDocumentChunksEmbedder().get_vector_store(f'database/services/{customer_id}/knowledge_base/image_vector_store')

    print("INITIALIZING RETRIEVER...")
    retriever = LangchainDocumentChunksRetriever(vector_store)
    if allow_multimodal_for_images:  
        image_retriever = LangchainDocumentChunksRetriever(image_vector_store)

    print("BREAKING QUERY...")
    queries = QueryPreprocessingAgent().break_query(query)
    print(queries)

    # aggregate_of_general_queries = ""
    retrieved_documents = []
    response_array = []

    knowledge_summary = customer_config["knowledge_summary"]

    for q in queries:
        watchman_agent_decision = WatchmanAgent().guard(q, knowledge_summary)
        if "yes" in watchman_agent_decision.lower():
            print(f'{q} is general')
            # aggregate_of_general_queries = aggregate_of_general_queries + "\n" + q
        else:
            print(f'{q} is specific')
            retrieved_documents.extend(retriever.retrieve(q))
            if allow_multimodal_for_images:
                top_image_document = image_retriever.retrieve(q)[0]
                relavancy_check_decision = ImageDescriptionRelavancyCheckAgent().answer_query(query, top_image_document.page_content, top_image_document.page_content)
                print(relavancy_check_decision)
                if "yes" in relavancy_check_decision.lower():
                    retrieved_documents.append(top_image_document)
                    response_array.append(chat_history_manager.append(customer_id, user_id, "bot", "image", rm.get(f'file_system/{top_image_document.metadata.get("source")}')))

    print(retrieved_documents)
    aggregate_context = LangchainDocumentsMerger().merge_documents_to_string(retrieved_documents)
    # general_response = GeneralQueryAnsweringAgent().answer(aggregate_of_general_queries)
    specific_response = QueryAnsweringAgent().answer(query, aggregate_context)

    chat_history_manager.append(customer_id, user_id, "user", "text", query)
    # response_array.append(chat_history_manager.append(customer_id, user_id, "bot", "text", general_response))
    response_array.append(chat_history_manager.append(customer_id, user_id, "bot", "text", specific_response))

    # print("RETRIEVING RELATED DOCUMENTS")
    # retrieved_documents = []
    # response_array = []

    # for q in queries:
    #     retrieved_documents += retriever.retrieve(q)
    #     # if allow_multimodal_for_images:  
    #         # top_image_description_document = image_retriever.retrieve(q)[0]
    #         # relavancy_check_response = ImageDescriptionRelavancyCheckAgent().answer_query(query, top_image_description_document, top_image_description_document)
    #         # if "yes" in relavancy_check_response.lower():
    #         #     response_array.append(chat_history_manager.append(customer_id, user_id, "bot", "image", rm.get(f'file_system/{top_image_description_document.metadata.get("source")}')))
    #         #     image_relavant_response = QueryAnsweringAgent().answer_query(query, top_image_description_document)
    #         #     response_array.append(chat_history_manager.append(customer_id, user_id, "bot", "text", image_relavant_response))


    # print("MERGING RETRIEVED DOCUMENTS CONTENT...")
    # context = LangchainDocumentsMerger().merge_documents_to_string(retrieved_documents)

    # print(f'EVALUATING {query}')
    # response = QueryAnsweringAgent().answer_query(query, context)

    # # change query to context to get images relavant to context. but also want to retrieve images not bound to any context as well
    # # merged_descriptions = LangchainDocumentsMerger().merge_documents_to_string(image_description_documents)
    # # change merged_descriptions to context to get context relavant images, or maybe we can keep it directly relavant to the query
    # # relavancy_check_response = ImageDescriptionRelavancyCheckAgent().answer_query(query, merged_descriptions, merged_descriptions)

    # chat_history_manager.append(customer_id, user_id, "user", "text", query)
    # response_array.append(chat_history_manager.append(customer_id, user_id, "bot", "text", response))
    
    return jsonify({
            "success":"true",
            "message":"query evaluated successfully",
            "response":response_array
        })

@app.route("/chat/history", methods = ["POST"])
async def handle_history():
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
    user_id = body.get("user_id")
    query = body.get("query")
    page_number = body.get("page_number")
    page_size = body.get("page_size")
    key = f'{customer_id}-{user_id}'

    chat_context = rm.get(f'file_system/database/services/{customer_id}/{user_id}.json')
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
async def handle_upload():
    file = request.files.get("file")
    customer_id = request.form.get("customer_id")
    moderator_id = request.form.get("moderator_id")

    if file:   
        if file.filename.lower().endswith(".pdf"):
            path = f'database/services/{customer_id}/knowledge_base/{str(uuid4())}{file.filename}'
            file.save(path)
            pages = KnowledgeArtifactLoader().load_pdf(path)
            image_descriptions = KnowledgeArtifactLoader().load_images_from_pdf(path)
            chunks = LangchainDocumentsSplitter().split(pages)
            vector_store = LangchainDocumentChunksEmbedder().embed(f'database/services/{customer_id}/knowledge_base/vector_store',chunks)
            image_vector_store = LangchainDocumentChunksEmbedder().embed(f'database/services/{customer_id}/knowledge_base/image_vector_store',image_descriptions)

        if file.filename.lower().endswith(".txt"):
            path = f'database/services/{customer_id}/knowledge_base/{str(uuid4())}{file.filename}'
            file.save(path)
            pages = KnowledgeArtifactLoader().load_text(path)
            chunks = LangchainDocumentsSplitter().split(pages)
            vector_store = LangchainDocumentChunksEmbedder().embed(f'database/services/{customer_id}/knowledge_base/vector_store',chunks)
            print(vector_store.index.ntotal)

        if file.filename.lower().endswith((".png", ".jpg", ".jpeg")):
            path = f'database/services/{customer_id}/knowledge_base/{str(uuid4())}{file.filename}'
            file.save(path)
            image_descriptions = KnowledgeArtifactLoader().load_image(path)
            vector_store = LangchainDocumentChunksEmbedder().embed(f'database/services/{customer_id}/knowledge_base/image_vector_store',image_descriptions)
            print(vector_store.index.ntotal)

        return jsonify({
            "success":"true",
            "message":"file uploaded successfully"
        })

    return jsonify({
            "success":"false",
            "message":"file upload failed. no file provided or invalid file format (.pdf, .txt, .jpg, .jpeg, .png) allowed"
        })

if __name__ == '__main__':
    app.run(debug=True)
