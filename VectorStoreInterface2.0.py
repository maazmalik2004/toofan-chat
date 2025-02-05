from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_mongodb import MongoDBAtlasVectorSearch
from pymongo import MongoClient
from uuid import uuid4
from langchain_core.documents import Document
from sklearn.metrics.pairwise import cosine_similarity
import heapq

class VectorStoreInterface:
    def __init__(self, embedder_model = "models/embedding-001" ,db_url = None, db_name = None):
        if not db_url and not db_name:
            raise Exception(f"[VECTOR STORE INTERFACE:ERROR] db_url OR db_name FIELD NOT PROVIDED DURING INITIALIZATION")
        
        self.embedder = GoogleGenerativeAIEmbeddings(model = embedder_model)
        self.embedding_dimensions = 768
        self.db_client = MongoClient(db_url)
        self.db = self.db_client[db_name]

    # vector store will be equivalent to a collection.
    # the name of the vector_store/collection will be {customer_id}_{vector_store/image_vector_store}
    def get_vector_store(self, vector_store_name):
        print(f"[VECTOR STORE INTERFACE] GETTING VECTOR STORE : {vector_store_name}")
        collection_name = vector_store_name
        collection = self.db[collection_name]
        
        if not collection_name in self.db.list_collection_names():
            print(f"[VECTOR STORE INTERFACE] CREATING VECTOR STORE SINCE IT DOESN'T ALREADY EXIST : {vector_store_name}")
            self.db.create_collection(collection_name)
        
        return collection

    def embed(self, vector_store_name, documents):
        print(f"[VECTOR STORE INTERFACE] EMBEDDING {len(documents)} DOCUMENTS : {vector_store_name}")
        collection_name = vector_store_name
        collection = self.get_vector_store(collection_name)

        to_be_inserted = []
        for d in documents:
            vector = self.embedder.embed_query(d.page_content)
            d = d.dict()
            
            d["embedding"] = vector
            id = str(uuid4())
            d["id"] = id
            d["metadata"]["id"] = id

            to_be_inserted.append(d)

        collection.insert_many(to_be_inserted)
        return collection
    
    def retrieve(self, vector_store_name, query, k=5):
        print(f"[VECTOR STORE INTERFACE] RETRIEVING TOP {k} MOST SIMILAR DOCUMENTS : {vector_store_name}")
        query_vector = self.embedder.embed_query(query)

        collection_name = vector_store_name
        collection = self.get_vector_store(collection_name)

        min_heap = []

        # iterating over all documents in the vector store
        for d in collection.find({}):
            similarity = cosine_similarity([query_vector], [d["embedding"]])[0][0]
            print(d["page_content"])
            print(f"COSINE SIMILARITY : {similarity}\n")

            if len(min_heap) < k:
                heapq.heappush(min_heap, (similarity, d))
            else:
                heapq.heappushpop(min_heap, (similarity, d))

        most_similar_documents = [doc for _, doc in sorted(min_heap, reverse=True)]

        langchain_documents = []
        for d in most_similar_documents:
            document_data = {key:d[key] for key in d}
            langchain_documents.append(Document(
                **document_data
            ))
        
        print(f"[VECTOR STORE INTERFACE] RETRIEVED DOCUMENTS : {langchain_documents}")
        return langchain_documents
    
    def delete(self, vector_store_name, ids):
        print(f"[VECTOR STORE INTERFACE] DELETING DOCUMENTS : {ids}")
        collection_name = vector_store_name
        collection = self.get_vector_store(collection_name)

        collection.delete_many({
            "id":{
                "$in":ids
            }
        })

    def delete_by_field(self, vector_store_name, key, values):
        collection_name = vector_store_name
        collection = self.get_vector_store(collection_name)

        field_exists = collection.find_one({key: {"$exists": True}}) is not None

        if not field_exists:
            raise Exception(f"[VECTOR STORE INTERFACE:ERROR] INVALID FIELD PROVIDED : {key}")
        
        collection.delete_many({
            key: {
                "$in": values
            }
        })

    
# vsi = VectorStoreInterface(db_url = "mongodb://localhost:27017/", db_name = "toofan_local")
# print(vsi)

# from langchain.schema import Document

# documents = [
#     # Existing circle-related documents
#     Document(page_content="A circle is a perfect geometric shape where all points are equidistant from the center.", metadata={"source": "geometry_basics.txt", "topic": "circle"}),
#     Document(page_content="The circumference of a circle is calculated by multiplying the diameter by pi (π).", metadata={"source": "circle_math.txt", "topic": "circle_properties"}),
#     Document(page_content="Circles have infinite lines of symmetry that pass through their center.", metadata={"source": "symmetry_guide.txt", "topic": "circle_symmetry"}),

#     # New random topics
#     Document(page_content="Honeybees communicate through a unique dance known as the waggle dance to convey the location of flowers.", metadata={"source": "bee_facts.txt", "topic": "biology"}),
#     Document(page_content="The Eiffel Tower can grow taller in the summer due to the expansion of metal in heat.", metadata={"source": "eiffel_tower.txt", "topic": "physics"}),
#     Document(page_content="Quantum entanglement is a phenomenon where two particles remain connected regardless of distance.", metadata={"source": "quantum_physics.txt", "topic": "science"}),
#     Document(page_content="Mount Everest, the highest mountain on Earth, grows approximately 4 millimeters taller each year due to tectonic activity.", metadata={"source": "mountains.txt", "topic": "geography"}),
#     Document(page_content="The Mona Lisa has no clearly defined eyebrows because they were either never painted or have faded over time.", metadata={"source": "art_history.txt", "topic": "art"}),
#     Document(page_content="Shakespeare invented over 1,700 words, including 'bedazzled' and 'swagger'.", metadata={"source": "literature_facts.txt", "topic": "language"}),
#     Document(page_content="Octopuses have three hearts, and their blood is blue due to the presence of hemocyanin.", metadata={"source": "marine_life.txt", "topic": "biology"}),
#     Document(page_content="Bananas are berries, but strawberries are not, according to botanical definitions.", metadata={"source": "fruit_facts.txt", "topic": "botany"}),
#     Document(page_content="Chess grandmasters can burn up to 6,000 calories a day due to intense mental exertion.", metadata={"source": "chess_trivia.txt", "topic": "games"}),
#     Document(page_content="The speed of light is approximately 299,792,458 meters per second in a vacuum.", metadata={"source": "physics_basics.txt", "topic": "science"})
# ]

# # vsi.embed("1234_vector_store", documents)
# # vsi.retrieve("1234_vector_store", "circle", k=5)
# # vsi.delete("1234_vector_store",["91f3567a-04df-46ee-bebe-e8ba1a03ce79", "20be7bd8-de23-4374-8b54-6a6415ee1004", "9e0e685e-de51-4fcc-ae8a-8b5f90f2cd38"])
# vsi.delete_by_field("1234_vector_store","id",["3fe45f97-d778-41bb-ab2e-bc43d875cc42", "87bd25c9-0ce4-46ba-aad4-00034316902e", "98243f5e-a60d-46ca-a946-45c52000bcd7"])
