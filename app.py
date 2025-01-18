from flask import Flask, request, jsonify
import asyncio
import os
from uuid import uuid4
from datetime import datetime
import json
from pprint import pprint

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
    use_query_filtering = customer_config["use_query_filtering"]

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

    aggregate_summary = ""
    knowledge_summaries = customer_config["knowledge_summaries"]
    for ks in knowledge_summaries:
        print(ks.get("artifact_id"))
        aggregate_summary = aggregate_summary + "\n" + ks.get("artifact_summary")
    print(aggregate_summary)

    # aggregate_of_general_queries = ""
    retrieved_documents = []
    response_array = []

    for q in queries:
        if use_query_filtering:
            watchman_agent_decision = WatchmanAgent().guard(q, aggregate_summary)
            if "yes" in watchman_agent_decision.lower():
                print(f'{q} is general')
                # aggregate_of_general_queries = aggregate_of_general_queries + "\n" + q
            else:
                print(f'{q} is specific')
                retrieved_documents.extend(retriever.retrieve(q))
                if allow_multimodal_for_images:
                    top_image_document = image_retriever.retrieve(q)[0]
                    relavancy_check_decision = ImageDescriptionRelavancyCheckAgent().answer_query(q, top_image_document.page_content, top_image_document.page_content)
                    print(relavancy_check_decision)
                    if "yes" in relavancy_check_decision.lower():
                        retrieved_documents.append(top_image_document)
                        response_array.append(chat_history_manager.append(customer_id, user_id, "bot", "image", rm.get(f'file_system/{top_image_document.metadata.get("source")}')))
        else:
            retrieved_documents.extend(retriever.retrieve(q))
            if allow_multimodal_for_images:
                top_image_document = image_retriever.retrieve(q)[0]
                relavancy_check_decision = ImageDescriptionRelavancyCheckAgent().answer_query(q, top_image_document.page_content, top_image_document.page_content)
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

    
    return jsonify({
            "success":"true",
            "message":"query evaluated successfully",
            "response":response_array
        })

@app.route("/chat/history", methods = ["POST"])
async def handle_history():
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

@app.route('/bot/knowledge', methods = ['POST'])
async def handle_upload():
    files = request.files.getlist("files")
    customer_id = request.form.get("customer_id")
    admin_id = request.form.get("admin_id")

    customer_config = rm.get(f'file_system/database/services/{customer_id}/config.json')
    knowledge_summaries = customer_config.get("knowledge_summaries")

    uploaded_artifacts = []

    for file in files:
        artifact_id = str(uuid4())
        
        if file.filename.lower().endswith(".pdf"):
            path = f'database/services/{customer_id}/knowledge_base/{artifact_id}.pdf'
            file.save(path)
            # image_descriptions_task =  asyncio.create_task(asyncio.to_thread(KnowledgeArtifactLoader().load_images_from_pdf(path)))
            # pages_task = asyncio.create_task(asyncio.to_thread(KnowledgeArtifactLoader().load_pdf(path)))
            # image_descriptions, pages = await asyncio.gather(image_descriptions_task, pages_task)
            pages = KnowledgeArtifactLoader().load_pdf(path, artifact_id)
            summary = SummarizingAgent().summarize_from_documents(pages)
            knowledge_summaries.append({
                "artifact_id":artifact_id,
                "artifact_summary":summary
            })
            image_descriptions = KnowledgeArtifactLoader().load_images_from_pdf(path, artifact_id)
            chunks = LangchainDocumentsSplitter().split(pages)
            vector_store = LangchainDocumentChunksEmbedder().embed(f'database/services/{customer_id}/knowledge_base/vector_store',chunks)
            image_vector_store = LangchainDocumentChunksEmbedder().embed(f'database/services/{customer_id}/knowledge_base/image_vector_store',image_descriptions)
            uploaded_artifacts.append({
                "artifact_name":file.filename,
                "artifact_id":artifact_id
            })

        if file.filename.lower().endswith(".txt"):
            path = f'database/services/{customer_id}/knowledge_base/{artifact_id}.txt'
            file.save(path)
            pages = KnowledgeArtifactLoader().load_text(path, artifact_id)
            summary = SummarizingAgent().summarize_from_documents(pages)
            knowledge_summaries.append({
                "artifact_id":artifact_id,
                "artifact_summary":summary
            })
            chunks = LangchainDocumentsSplitter().split(pages)
            vector_store = LangchainDocumentChunksEmbedder().embed(f'database/services/{customer_id}/knowledge_base/vector_store',chunks)
            print(vector_store.index.ntotal)
            uploaded_artifacts.append({
                "artifact_name":file.filename,
                "artifact_id":artifact_id
            })

        if file.filename.lower().endswith((".png", ".jpg", ".jpeg")):
            fname, fextension = os.path.splitext(file.filename)
            path = f'database/services/{customer_id}/knowledge_base/{str(uuid4())}{fextension.lower()}'
            file.save(path)
            image_descriptions = KnowledgeArtifactLoader().load_image(path, artifact_id)
            summary = SummarizingAgent().summarize_from_documents(image_descriptions)
            knowledge_summaries.append({
                "artifact_id":artifact_id,
                "artifact_summary":summary
            })
            vector_store = LangchainDocumentChunksEmbedder().embed(f'database/services/{customer_id}/knowledge_base/image_vector_store',image_descriptions)
            print(vector_store.index.ntotal)
            uploaded_artifacts.append({
                "artifact_name":file.filename,
                "artifact_id":artifact_id
            })

    rm.set(f'file_system/database/services/{customer_id}/config.json', customer_config)

    return jsonify({
            "success":"true",
            "message":"files uploaded successfully",
            "uploaded_artifacts":uploaded_artifacts
        })

@app.route("/<customer_id>/bot/knowledge", methods=["DELETE"])
async def handle_delete(customer_id):
    print("DELETING PROVIDED KNOWLEDGE")
    
    body = request.get_json()
    artifact_ids = body.get("artifacts")
    artifact_ids = set(artifact_ids)

    customer_config = rm.get(f'file_system/database/services/{customer_id}/config.json')
    knowledge_summaries = customer_config.get("knowledge_summaries")

    customer_config["knowledge_summaries"] = [ks for ks in knowledge_summaries if ks["artifact_id"] not in artifact_ids]

    rm.set(f'file_system/database/services/{customer_id}/config.json', customer_config)

    vector_store = LangchainDocumentChunksEmbedder().get_vector_store(f'database/services/{customer_id}/knowledge_base/vector_store')
    
    dictionary = vector_store.docstore._dict
    pprint(dictionary)
    print(len(dictionary))

    # for key, value in dictionary.items():
    #     value.metadata["test_value"] = 10

    vector_store_ids_to_be_deleted = []
    for key, value in dictionary.items():
        if value.metadata.get("artifact_id") in artifact_ids:
            vector_store_ids_to_be_deleted.append(key)

    print(vector_store.delete(ids = vector_store_ids_to_be_deleted))

    LangchainDocumentChunksEmbedder().set_vector_store(f'database/services/{customer_id}/knowledge_base/vector_store', vector_store)
    
    await asyncio.sleep(10)

    vector_store = None
    dictionary = None
    vector_store = LangchainDocumentChunksEmbedder().get_vector_store(f'database/services/{customer_id}/knowledge_base/vector_store')

    dictionary = vector_store.docstore._dict
    pprint(dictionary)
    print(len(dictionary))

    return jsonify({
        "success":"true",
        "message": "Knowledge deleted successfully"
    })


@app.route("/bot/config", methods = ["POST"])
async def handle_config_update():
    print("MODIFYING CONFIGURATION")
    body = request.get_json()
    customer_id = body.get("customer_id")
    config_updates = body.get("config")

    config = rm.get(f"file_system/database/services/{customer_id}/config.json")

    for key, value in config_updates.items():
        config[key] = value

    rm.set(f"file_system/database/services/{customer_id}/config.json", config)

    return jsonify({
        "success":"true",
        "message":"config updated successfully",
        "updated_config":config
    })

if __name__ == '__main__':
    app.run(debug=True)
