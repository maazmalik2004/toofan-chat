from langchain_community.document_loaders import PyPDFLoader, TextLoader
from database_manager import DatabaseManager
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

class Loader:
    def __init__(self):
        self.database_manager = DatabaseManager()
        self.image_description_generator = ImageToDescriptionAgent()

    def load_text(self, path):
        try:
            loader = TextLoader(path)
            document = loader.load()
            return document
        except Exception as e:
            print(f"ERROR LOADING TEXT FILE: {e}")
            raise

    def load_image(self, path):
        try:
            base_64_image = self.database_manager.read_image(path)
            description = self.image_description_generator.describe(base_64_image)
            document = [Document(
                page_content=description,
                metadata={"source": path}
            )]
            return document
        except Exception as e:
            print(f"ERROR LOADING AND PROCESSING IMAGE: {e}")
            raise

    def load_pdf(self, path):
        try:
            loader = PyPDFLoader(path)
            documents = []
            for doc in loader.lazy_load():
                documents.append(doc)
            return documents
        
        except Exception as e:
            print(f"ERROR LOADING PDF: {e}")
            raise

    def load_images_from_pdf(self, path):
        # take in pdf,
        # extract images and save
        # for each image, load_image(path to image)
        # return array of documents... we wont split these documents but simply embed it directly.

        try:
            pdf = fitz.open(path)
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

                    documents = documents + self.load_image(image_path)

            pdf.close()
            print(documents)
            return documents
        except Exception as e:
            print(f"ERROR LOADING IMAGES FROM PDF: {e}")
            raise
        
class Splitter:
    def __init__(self):
        pass

    # def split(self, documents):
    #     content = self.merge_documents_to_text(documents)
    #     splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap = 100)
    #     split_documents = splitter.create_documents([content])
    #     return split_documents

    def split(self, documents):
        content = self.merge_documents_to_text(documents)
        splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=100)
        split_texts = splitter.split_text(content)
        split_documents = []
        for text in split_texts:
            metadata = documents[0].metadata if documents else {}
            split_documents.append(Document(page_content=text, metadata=metadata))
        return split_documents
    
    def merge_documents_to_text(self, documents):
        combined_text = StringIO()
        for document in documents:
            combined_text.write(document.page_content + "\n")
        text = combined_text.getvalue()
        combined_text.close()
        return text
    
class Embedder:
    def __init__(self, model = "models/embedding-001"):
        self.embedder = GoogleGenerativeAIEmbeddings(model=model)

    def embed(self, vector_store_path, documents):
        if not os.path.exists(vector_store_path):
            vector_store = FAISS.from_documents(documents, embedding=self.embedder)
            vector_store.save_local(vector_store_path)
        
        vector_store = FAISS.load_local(
            vector_store_path, embeddings = self.embedder, allow_dangerous_deserialization=True
        )
        uuids = [str(uuid4()) for _ in range(len(documents))]
        vector_store.add_documents(documents=documents, ids=uuids)
        vector_store.save_local(vector_store_path)
        return vector_store
    
    def get_vector_store(self, vector_store_path):
        if not os.path.exists(vector_store_path):
            vector_store = FAISS.from_documents([], embedding=self.embedder)
            vector_store.save_local(vector_store_path)
        else:
            vector_store = FAISS.load_local(
                vector_store_path, embeddings=self.embedder, allow_dangerous_deserialization=True
            )
        return vector_store

    
class Retriever:
    def __init__(self, vector_store, number_of_results = 5):
        self.vector_store = vector_store
        self.number_of_results = number_of_results

    def retrieve(self, query):
        retriever = self.vector_store.as_retriever(search_kwargs={"k": self.number_of_results})
        return retriever.invoke(query)

# loader = Loader()
# loader.load_images_from_pdf("database/services/1234/knowledge_base/FAI-03 entire.pdf")

# loader = Loader()
# splitter = Splitter()
# embedder = Embedder()

# --------------------------------------------------
# documents = loader.load_pdf("database/services/1234/rag_context/pdf document.pdf")
# chunks = splitter.split(documents)

# print(chunks)
# print(len(chunks))

# vector_store = embedder.embed("database/services/1234/rag_context/vector_store",chunks)
# print(vector_store)

# # second document
# documents = loader.load_pdf("database/services/1234/rag_context/pdf document 2.pdf")
# chunks = splitter.split(documents)

# print(chunks)
# print(len(chunks))

# updated_vector_store = embedder.embed("database/services/1234/rag_context/vector_store", chunks)
# ---------------------------------
# query = "how long did mr potato live"

# vector_store = embedder.get_vector_store("database/services/1234/rag_context/vector_store")
# retriever = Retriever(vector_store)
# output = retriever.retrieve(query)

# context = splitter.merge_documents_to_text(output)

# from agents import QueryAnsweringAgent
# print("QUERY-------------------------------------------")
# print(query)
# print("RESPONSE-------------------------------------------")
# print(QueryAnsweringAgent().answer_query(query,context))