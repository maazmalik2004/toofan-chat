from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_mongodb import MongoDBAtlasVectorSearch
from pymongo import MongoClient
from uuid import uuid4
from langchain_core.documents import Document

# mongodb+srv://maazmalik2004:abenzene1234@dspace.odk45.mongodb.net/?retryWrites=true&w=majority&appName=Dspace

class VectorStoreInterface:
    def __init__(self,embedder_model = "models/embedding-001" ,db_url = "mongodb+srv://Cluster65662:eFpffHVgX1hl@cluster65662.iuo3q.mongodb.net/toofan_local?retryWrites=true&w=majority"):
        self.embedder = GoogleGenerativeAIEmbeddings(model = embedder_model)
        self.dimensions = 768
        self.db_client = MongoClient(db_url)

    def embed(self, vector_store, documents):
        print("EMBEDDING DOCUMENTS TO VECTOR STORE")
        uuids = [str(uuid4()) for _ in range(len(documents))]
        vector_store.add_documents(
            documents = documents,
            ids = uuids
        )
        return vector_store
    
    def retrieve(self, vector_store, query):
        # query_embedding = self.embedder.embed_query(query)
        retrieved_documents = vector_store.similarity_search(query, k = 5)
        print(retrieved_documents)
        return retrieved_documents
    
    def collection_exists(self, db_name, collection_name):
        if collection_name in self.db_client[db_name].list_collection_names():
            print(f"collection {collection_name} exists in database {db_name}")
            return True
        return False
    
    def get_vector_store(self, collection, vector_store_name):
        vector_store = MongoDBAtlasVectorSearch(
            collection=collection,
            embedding=self.embedder,
            index_name=vector_store_name,
            relevance_score_fn="cosine"
        )
        print(vector_store)
        return vector_store
    
    def get_collection(self, db_name, collection_name):
        collection = self.db_client[db_name][collection_name]
        print(collection)
        return collection
    
    def create_vector_store(self, collection, vector_store_name):
        vector_store = MongoDBAtlasVectorSearch(
            collection=collection,
            embedding=self.embedder,
            index_name=vector_store_name,
            relevance_score_fn="cosine"
        )

        vector_store.create_vector_search_index(dimensions=self.dimensions)

        # default_document = [Document(
        #     page_content="default",
        #     metadata = {
        #         "source" : "default"
        #     }
        # )]

        # uuids = [str(uuid4()) for _ in range(len(default_document))]
        # vector_store.add_documents(documents=default_document, ids=uuids)

        print(vector_store)
        return vector_store

# cluster(url)
#     database toofan
#         collection customer 1234 -  vector_store, 
#                                     image-vector-store
#         collection customer 0000 -  vector_store, 
#                                     image-vector-store

vsi = VectorStoreInterface()
collection = vsi.get_collection("customer_1","vector_store")

vector_store = vsi.create_vector_store(collection, "vector_store")

# vector_store = vsi.get_vector_store(collection, "vector_store")
# # for doc in collection.find():
# #     print(doc)

circle_documents = [
    Document(page_content="A circle is a perfect geometric shape where all points are equidistant from the center.", metadata={"source": "geometry_basics.txt", "topic": "circle"}),
    Document(page_content="The circumference of a circle is calculated by multiplying the diameter by pi (π).", metadata={"source": "circle_math.txt", "topic": "circle_properties"}),
    Document(page_content="Circles have infinite lines of symmetry that pass through their center.", metadata={"source": "symmetry_guide.txt", "topic": "circle_symmetry"})
]

# # # Documents about aliens
# alien_documents = [
#     Document(page_content="Extraterrestrial life could exist in various forms beyond our current understanding of biology.", metadata={"source": "astrobiology_research.txt", "topic": "alien_life"}),
#     Document(page_content="The Drake Equation attempts to estimate the number of communicative alien civilizations in our galaxy.", metadata={"source": "seti_reports.txt", "topic": "alien_probability"}),
#     Document(page_content="Potential alien life might exist in extreme environments, such as on moons with subsurface oceans.", metadata={"source": "exoplanet_studies.txt", "topic": "alien_habitats"})
# ]

vsi.embed(vector_store, circle_documents)
# vsi.embed(vector_store, alien_documents)
# # # vsi.embed(image_vector_store, alien_documents)

# vsi.retrieve(vector_store, "A circle is a perfect geometric shape where all points")