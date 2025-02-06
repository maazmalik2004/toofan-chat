from flask import Flask, request, jsonify
import asyncio
import os
from uuid import uuid4
from datetime import datetime
import json
from pprint import pprint
import requests
import mimetypes
import filetype
import re

from FileSystemInterface import FileSystemInterface
from UserContextInterface import UserContextInterface
from CustomerConfigInterface import CustomerConfigInterface
from ResourceManager import ResourceManager
from ChatHistoryManager import   ChatHistoryManager
from DefaultConfigManager import DefaultConfigManager

from rag import KnowledgeArtifactLoader, LangchainDocumentsSplitter,LangchainDocumentsMerger, VectorStoreManager
from agents import QueryPreprocessingAgent, SummarizingAgent, QueryAnsweringAgent, ImageDescriptionRelavancyCheckAgent, WatchmanAgent, GeneralQueryAnsweringAgent

from dotenv import load_dotenv
load_dotenv()

app = Flask(__name__)

rm = ResourceManager(location_interface_map = {
             "file_system": FileSystemInterface(),
             "user_context": UserContextInterface(filename="database/environment/user_contexts.json"),
             "customer_config":CustomerConfigInterface(db_url = "mongodb://localhost:27017/")
         })
chat_history_manager = ChatHistoryManager(resource_manager=rm)
default_config_manager = DefaultConfigManager(resource_manager=rm)
vsi = VectorStoreManager(db_url = "mongodb://localhost:27017/", db_name = "toofan_local")

# rm.set("chat_history/1",{
#     "some data":"some object"
# })

# rm.set("chat_history/2",{
#     "some other data":"some other object"
# })

# print(rm.get("chat_history/1"))
# print(rm.get("chat_history/2"))

@app.route('/chatbot/api/v1/health', methods=["GET"])
def handle_health_check():
    return jsonify({
        "status":"healthy"
    }),200

@app.route('/chatbot/api/v1/connect', methods=['POST'])
async def handle_connect():
    try:
        body = request.get_json()
        customer_id = body.get("customer_id")
        user_id = body.get("user_id")
        user_context = body.get("context")

        if not user_context:
            user_context = {}
        
        if not user_context.get("chat_history"):
            user_context["chat_history"] = []

        print(user_context)

        rm.set(f"user_context/{customer_id}{user_id}", user_context)
        
        # config = rm.get(f'file_system/database/services/{customer_id}/config.json')
        config = rm.get(f'customer_config/{customer_id}')

        if not config:
            raise Exception("customer config not found. maybe customer doesnt exist. use /config endpoint to create customer config")
        
        welcome_chat_context = chat_history_manager.append(customer_id, user_id, "bot", "text", config["custom_welcome_message"])
        
        return jsonify({
                "result":"true",
                "message":"connected",
                "chat_response":[{**welcome_chat_context }]
            }),200
    
    except Exception as e:
        print(e)
        return jsonify({
            "result":"false",
            "message":str(e),
        }),400

@app.route("/chatbot/api/v1/config", methods = ["PUT"])
async def handle_config_update():
    try:
        print("MODIFYING CONFIGURATION")
        body = request.get_json()
        customer_id = body.get("customer_id")
        config_updates = body.get("config")

        print("meow")
        config = rm.get(f'customer_config/{customer_id}')
        print("woof")
        config_already_exists = False

        if not config:
            # creating config with default value
            config = default_config_manager.get_default_config(customer_id)
            print("before setting default config")
            rm.set(f'customer_config/{customer_id}', config)
            print("after setting default config")
            config_already_exists = True

        # updating config
        for key, value in config_updates.items():
            config[key] = value
        
        rm.set(f'customer_config/{customer_id}', config)

        if config_already_exists:
            return jsonify({
                "result":"true",
                "message":"config created",
            }),201

        return jsonify({
            "result":"true",
            "message":"config updated",
        }),200
    except Exception as e:
        print(e)
        return jsonify({
            "result":"false",
            "message":"invalid request",
        }),400


@app.route('/chatbot/api/v1/query', methods=['POST'])
async def handle_query():
    try:
        body = request.get_json()
        customer_id = body.get("customer_id")
        user_id = body.get("user_id")
        query = body.get("query")

        customer_config = rm.get(f'customer_config/{customer_id}')
        print(customer_config)
        if not customer_config:
            raise Exception("customer doesnt exist. configure customer using /config")
        
        system_config = rm.get(f'file_system/database/environment/config.json')
        query_response_codes = system_config.get("query_response_codes")
        default_response_code = system_config.get("default_response_code")
        print(query_response_codes)
        print(default_response_code)
        
        allow_multimodal_for_images = customer_config["allow_multimodal_for_images"]
        use_query_filtering = customer_config["use_query_filtering"]
        
        vector_store_name = f"{customer_id}_vector_store"
        image_vector_store_name = f"{customer_id}_image_vector_store"
        
        image_vector_store = None
        # image_retriever = None
        top_image_document = None
        relavancy_check_decision = None
        
        # print("GETTING VECTOR STORE...")
        # vector_store = LangchainDocumentChunksEmbedder().get_vector_store(f'database/services/{customer_id}/knowledge_base/vector_store')
        
        # if vector_store.index.ntotal == 0:
        #     raise Exception("knowledge base is empty. you are querying an empty knowledge base !")
        
        # if allow_multimodal_for_images:     
        #     image_vector_store = LangchainDocumentChunksEmbedder().get_vector_store(f'database/services/{customer_id}/knowledge_base/image_vector_store')

        # if allow_multimodal_for_images and image_vector_store.index.ntotal == 0:
        #     raise Exception("image knowledge base is empty. either disable 'allow_multimodal_for_images' or upload image content to the knowledge base. you are querying an empty image knowldge base")
        
        # print("INITIALIZING RETRIEVER...")
        # retriever = LangchainDocumentChunksRetriever()
        # if allow_multimodal_for_images:  
        #     image_retriever = LangchainDocumentChunksRetriever(image_vector_store)

        print("BREAKING QUERY...")
        queries = QueryPreprocessingAgent().break_query(query)
        print(queries)

        print("FETCHING KNOWLEDGE SUMMARIES")
        aggregate_summary = ""
        knowledge_summaries = customer_config["knowledge_summaries"]
        for ks in knowledge_summaries:
            # print(ks.get("artifact_id"))
            aggregate_summary = aggregate_summary + "\n" + ks.get("artifact_summary")
        # print(aggregate_summary)

        # aggregate_of_general_queries = ""
        retrieved_documents = []
        images_array = []

        for q in queries:
            if use_query_filtering:
                watchman_agent_decision = WatchmanAgent().guard(q, aggregate_summary)
                if "yes" in watchman_agent_decision.lower():
                    print(f'{q} is general')
                    # aggregate_of_general_queries = aggregate_of_general_queries + "\n" + q
                else:
                    print(f'{q} is specific')
                    retrieved_documents.extend(vsi.retrieve(vector_store_name,q))
                    if allow_multimodal_for_images:
                        retrieved_image_documents = vsi.retrieve(image_vector_store_name,q)
                        if len(retrieved_image_documents) != 0:
                            top_image_document = retrieved_image_documents[0]
                            relavancy_check_decision = ImageDescriptionRelavancyCheckAgent().answer_query(q, top_image_document.page_content, top_image_document.page_content)
                            print(relavancy_check_decision)
                            if "yes" in relavancy_check_decision.lower():
                                retrieved_documents.append(top_image_document)
                                images_array.append(chat_history_manager.append(customer_id, user_id, "bot", "image", rm.get(f'file_system/{top_image_document.metadata.get("source")}')))
                        else:
                            raise Exception("[UPLOAD:ERROR] IMAGE VECTOR STORE IS EMPTY, DISABLE allow_multimodal_for_images")
            else:
                retrieved_documents.extend(vsi.retrieve(vector_store_name,q))
                if allow_multimodal_for_images:
                    retrieved_image_documents = vsi.retrieve(image_vector_store_name,q)
                    if len(retrieved_image_documents) != 0:
                        top_image_document = retrieved_image_documents[0]
                        relavancy_check_decision = ImageDescriptionRelavancyCheckAgent().answer_query(q, top_image_document.page_content, top_image_document.page_content)
                        print(relavancy_check_decision)
                        if "yes" in relavancy_check_decision.lower():
                            retrieved_documents.append(top_image_document)
                            images_array.append(chat_history_manager.append(customer_id, user_id, "bot", "image", rm.get(f'file_system/{top_image_document.metadata.get("source")}')))
                    else:
                        raise Exception("[UPLOAD:ERROR] IMAGE VECTOR STORE IS EMPTY, DISABLE allow_multimodal_for_images")

        print(retrieved_documents)
        aggregate_context = LangchainDocumentsMerger().merge_documents_to_string(retrieved_documents)
        specific_response = QueryAnsweringAgent().answer(query, aggregate_context)

        pattern = r"^(" + "|".join(re.escape(match) for match in query_response_codes) + ")"
        response_code = default_response_code
        match = re.match(pattern, specific_response)
        if match:
            response_code = match.group(0)
            specific_response = specific_response[match.end():].strip()

        chat_history_manager.append(customer_id, user_id, "user", "text", query)
        text_block = chat_history_manager.append(customer_id, user_id, "bot", "text", specific_response)

        return jsonify({
                "result":"true",
                "message":"success",
                "response":{
                    "paragraph":text_block,
                    "images":images_array
                },
                "response_code":response_code
            })
    except Exception as e:
        print(e)
        return jsonify({
            "result":"false",
            "message":str(e)
        })

@app.route('/chatbot/api/v1/knowledge', methods = ['POST'])
async def handle_upload():
    try:
        body = request.get_json()
        artifacts = body.get("artifacts")
        customer_id = body.get("customer_id")

        # we can delete the file after embeddings have been created.
        system_config = rm.get("file_system/database/environment/config.json")
        persist_uploaded_files = system_config["persist_uploaded_files"]
        print(persist_uploaded_files)

        # ensuring the required folder exists
        knowledge_base_path = f'database/services/{customer_id}/knowledge_base'
        if not os.path.exists(knowledge_base_path):
            os.makedirs(knowledge_base_path)

        customer_config = rm.get(f'customer_config/{customer_id}')
        if not customer_config:
            raise Exception("customer config not found. maybe customer doesnt exist. use /config endpoint to create customer config")
        knowledge_summaries = customer_config.get("knowledge_summaries")
        
        upload_count = 0
        uploaded_artifacts = []
        for artifact in artifacts:
            artifact_id = artifact.get("artifact_id")
            artifact_url = artifact.get("artifact_url")
            
            download_response = requests.get(artifact_url, stream = True, allow_redirects=True)
            content_type = str(download_response.headers.get("Content-Type"))
            extension = mimetypes.guess_extension(content_type)
            
            download_path = f'database/services/{customer_id}/knowledge_base/{artifact_id}{extension}'
            
            if download_response.status_code == 200:
                with open(download_path, "wb") as tmp_file:
                    for chunk in download_response.iter_content(chunk_size=8192):
                        tmp_file.write(chunk)
            # download complete
  
            if extension and extension.lower() == ".pdf":
                path = download_path
                pages = KnowledgeArtifactLoader().load_pdf(path, artifact_id)
                summary = SummarizingAgent().summarize_from_documents(pages)
                knowledge_summaries.append({
                    "artifact_id":artifact_id,
                    "artifact_summary":summary
                })
                image_descriptions = KnowledgeArtifactLoader().load_images_from_pdf(path, artifact_id)
                chunks = LangchainDocumentsSplitter().split(pages)
                vsi.embed(f'{customer_id}_vector_store',chunks)
                vsi.embed(f'{customer_id}_image_vector_store',image_descriptions)
                uploaded_artifacts.append({
                    "artifact_url":artifact_url,
                    "artifact_id":artifact_id
                })
                upload_count = upload_count + 1
                if not persist_uploaded_files:
                    os.remove(path)

            if extension and extension.lower() == ".txt":
                path = download_path
                pages = KnowledgeArtifactLoader().load_text(path, artifact_id)
                summary = SummarizingAgent().summarize_from_documents(pages)
                knowledge_summaries.append({
                    "artifact_id":artifact_id,
                    "artifact_summary":summary
                })
                chunks = LangchainDocumentsSplitter().split(pages)
                vsi.embed(f'{customer_id}_vector_store',chunks)
                uploaded_artifacts.append({
                    "artifact_url":artifact_url,
                    "artifact_id":artifact_id
                })
                upload_count = upload_count + 1
                if not persist_uploaded_files:
                    os.remove(path)

            if extension and extension.lower() in (".png", ".jpg", ".jpeg"):
                path = download_path
                image_descriptions = KnowledgeArtifactLoader().load_image(path, artifact_id)
                summary = SummarizingAgent().summarize_from_documents(image_descriptions)
                knowledge_summaries.append({
                    "artifact_id":artifact_id,
                    "artifact_summary":summary
                })
                vsi.embed(f'{customer_id}_image_vector_store',image_descriptions)
                uploaded_artifacts.append({
                    "artifact_url":artifact_url,
                    "artifact_id":artifact_id
                })
                upload_count = upload_count + 1
                # images shall not be removed as they are required during retrieval with allow_multimodal_for_images

        rm.set(f'customer_config/{customer_id}', customer_config)

        return jsonify({
                "result":"true",
                "message":f"{upload_count} artifacts uploaded",
                "uploaded_artifacts":uploaded_artifacts
            }),200
    except Exception as e:
        return jsonify({
            "result":"false",
            "message":str(e)
        }),400

@app.route("/chatbot/api/v1/knowledge", methods=["DELETE"])
async def handle_delete():
    try:
        print("DELETING ARTIFACTS")
        
        body = request.get_json()
        customer_id = body.get("customer_id")
        artifact_ids = body.get("artifacts")
        no_of_artifacts = len(artifact_ids)

        # deleting document chunks from the vector store
        vsi.delete(f"{customer_id}_vector_store","metadata.artifact_id",artifact_ids)
        vsi.delete(f"{customer_id}_image_vector_store","metadata.artifact_id",artifact_ids)

        # deleting corresponding  knowledge summaries
        customer_config = rm.get(f'customer_config/{customer_id}')
        knowledge_summaries = customer_config.get("knowledge_summaries")
        customer_config["knowledge_summaries"] = [ks for ks in knowledge_summaries if ks["artifact_id"] not in artifact_ids]
        rm.set(f'customer_config/{customer_id}', customer_config)

        return jsonify({
            "result":"true",
            "message": f"{no_of_artifacts} artifacts deleted"
        }),200
    except Exception as e:
        print(str(e))
        return jsonify({
            "result":"false",
            "message":"invalid request"
        }),400

if __name__ == '__main__':
    app.run(port=8000, debug=True)