from langchain_community.document_loaders import PyPDFLoader, TextLoader
from ResourceManager import ResourceManager
from agents import ImageToDescriptionAgent
from langchain_core.documents import Document
from langchain_experimental.text_splitter import SemanticChunker
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from io import StringIO
from langchain_community.vectorstores import FAISS
from uuid import uuid4
import os
import fitz

# temporary imports for testing
from dotenv import load_dotenv
load_dotenv()

from FileSystemInterface import FileSystemInterface

class KnowledgeArtifactLoader:
    def __init__(self):
        self.resource_manager = ResourceManager(location_interface_map = {
             "file_system": FileSystemInterface()
         })
        self.image_description_generator = ImageToDescriptionAgent()

    def load_text(self, path, artifact_id):
        try:
            print("LOADING TEXT")
            loader = TextLoader(path)
            document = loader.load()
            for d in document:
                d.metadata = {"source": path, "artifact_id":artifact_id}
            return document
        except Exception as e:
            print(f"ERROR LOADING TEXT FILE: {e}")
            raise

    def load_image(self, path, artifact_id):
        try:
            print("LOADING IMAGE")
            base_64_image = self.resource_manager.get(f'file_system/{path}')
            description = self.image_description_generator.describe(base_64_image)
            document = [Document(
                page_content=description,
                metadata={"source": path, "artifact_id":artifact_id}
            )]
            return document
        except Exception as e:
            print(f"ERROR LOADING AND PROCESSING IMAGE: {e}")
            raise

    def load_pdf(self, path, artifact_id):
        try:
            print("LOADING PDF")
            loader = PyPDFLoader(path)
            documents = []
            for doc in loader.lazy_load():
                doc.metadata = {"source": path, "artifact_id":artifact_id}
                documents.append(doc)
            return documents
        
        except Exception as e:
            print(f"ERROR LOADING PDF: {e}")
            raise

    def load_images_from_pdf(self, path, artifact_id):
        # take in pdf,
        # extract images and save
        # for each image, load_image(path to image)
        # return array of documents... we wont split these documents but simply embed it directly.

        try:
            print("EXTRACTING IMAGES FROM PDF")
            pdf = self.resource_manager.get(f'file_system/{path}')
            documents = []
            
            for page in pdf:
                images = page.get_images(full = True)
                for i in images:
                    xref = i[0]
                    base_image = pdf.extract_image(xref)
                    image_bytes = base_image["image"]
                    image_ext = base_image["ext"]
                    image_path = f"{os.path.dirname(path)}/{str(uuid4())}.{image_ext}"

                    with open(image_path,"wb") as image_file:
                        image_file.write(image_bytes)

                    documents = documents + self.load_image(image_path, artifact_id)

            pdf.close()
            print(documents)
            return documents
        except Exception as e:
            print(f"ERROR LOADING IMAGES FROM PDF: {e}")
            raise
        
class LangchainDocumentsSplitter:
    def __init__(self):
        self.merger = LangchainDocumentsMerger()

    def split(self, documents):
        content = self.merger.merge_documents_to_string(documents)
        splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=100)
        split_texts = splitter.split_text(content)
        split_documents = []
        for text in split_texts:
            metadata = documents[0].metadata if documents else {}
            split_documents.append(Document(page_content=text, metadata=metadata))
        return split_documents

class LangchainDocumentsMerger:
    def __init__(self):
        pass

    def merge_documents_to_string(self, documents):
        buffer = StringIO()
        for document in documents:
            buffer.write(document.page_content + "\n")
        merged_content = buffer.getvalue()
        buffer.close()
        return merged_content
    
    def merge_documents_to_document(self, documents):
        merged_content = self.merge_documents_to_string(documents)
        document = [Document(
            page_content=merged_content,
            metadata = {}
        )]
        return document
    
# class LangchainDocumentChunksEmbedder:
#     def __init__(self, model = "models/embedding-001"):
#         self.embedder = GoogleGenerativeAIEmbeddings(model=model)

#     def embed(self, vector_store_path, documents):
#         if not os.path.exists(vector_store_path):
#             vector_store = FAISS.from_documents(documents, embedding=self.embedder)
#             vector_store.save_local(vector_store_path)
        
#         vector_store = FAISS.load_local(
#             vector_store_path, embeddings = self.embedder, allow_dangerous_deserialization=True
#         )
#         uuids = [str(uuid4()) for _ in range(len(documents))]
#         vector_store.add_documents(documents=documents, ids=uuids)
#         vector_store.save_local(vector_store_path)
#         return vector_store
    
#     def get_vector_store(self, vector_store_path):
#         if not os.path.exists(vector_store_path):
#             vector_store = FAISS.from_documents([], embedding=self.embedder)
#             vector_store.save_local(vector_store_path)
#         else:
#             vector_store = FAISS.load_local(
#                 vector_store_path, embeddings=self.embedder, allow_dangerous_deserialization=True
#             )
#         return vector_store
    
#     def set_vector_store(self, path, vector_store):
#         vector_store.save_local(path)

# soon to be handled by a seprate interface via resource manager
class LangchainDocumentChunksEmbedder:
    def __init__(self, model="models/embedding-001"):
        self.embedder = GoogleGenerativeAIEmbeddings(model=model)

    def embed(self, vector_store_path, documents):
        # Check if the directory exists, create it if it doesn't
        directory = os.path.dirname(vector_store_path)
        if not os.path.exists(directory):
            os.makedirs(directory)  # Create the directory path if it doesn't exist

        if not os.path.exists(vector_store_path):
            vector_store = FAISS.from_documents(documents, embedding=self.embedder)
            vector_store.save_local(vector_store_path)
        
        vector_store = FAISS.load_local(
            vector_store_path, embeddings=self.embedder, allow_dangerous_deserialization=True
        )
        uuids = [str(uuid4()) for _ in range(len(documents))]
        vector_store.add_documents(documents=documents, ids=uuids)
        vector_store.save_local(vector_store_path)
        return vector_store
    
    def get_vector_store(self, vector_store_path):
        # Check if the directory exists, create it if it doesn't
        directory = os.path.dirname(vector_store_path)
        if not os.path.exists(directory):
            os.makedirs(directory)  # Create the directory path if it doesn't exist

        if not os.path.exists(vector_store_path):
            vector_store = FAISS.from_documents([Document(
                page_content="default",
                metadata={"source": "default", "artifact_id":"default"}
            )], embedding=self.embedder)
            vector_store.save_local(vector_store_path)
        else:
            vector_store = FAISS.load_local(
                vector_store_path, embeddings=self.embedder, allow_dangerous_deserialization=True
            )
        return vector_store
    
    def set_vector_store(self, path, vector_store):
        # Ensure the directory exists before saving
        directory = os.path.dirname(path)
        if not os.path.exists(directory):
            os.makedirs(directory)
        vector_store.save_local(path)
    
class LangchainDocumentChunksRetriever:
    def __init__(self, vector_store, number_of_results = 5):
        self.vector_store = vector_store
        self.number_of_results = number_of_results

    def retrieve(self, query):
        retriever = self.vector_store.as_retriever(search_kwargs={"k": self.number_of_results})
        return retriever.invoke(query)