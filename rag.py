from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_core.documents import Document
from database_manager import DatabaseManager
from agents import ImageToDescriptionAgent
from langchain_experimental.text_splitter import SemanticChunker
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from io import StringIO
import faiss
from langchain_community.docstore.in_memory import InMemoryDocstore
from langchain_community.vectorstores import FAISS
from dotenv import load_dotenv
from uuid import uuid4
import os

load_dotenv()

class Loader:
    def __init__(self):
        self.database_manager = DatabaseManager()
        self.image_description_generator = ImageToDescriptionAgent()

    def load_pdf(self, path):
        try:
            loader = PyPDFLoader(path)
            documents = []
            for doc in loader.lazy_load():
                documents.append(doc)

            return documents
        
        except Exception as e:
            print(f"Error loading PDF: {e}")
            return []

    def load_text(self, path):
        try:
            loader = TextLoader(path)
            document = loader.load()
            return document
        except Exception as e:
            print(f"Error loading text file: {e}")
            return []

    def load_image(self, path):
        try:
            base_64_image = self.database_manager.read_image(path)
            description = self.image_description_generator.generate_description(base_64_image)
            document = [Document(
                page_content=description,
                metadata={"source": path}
            )]
            return document
        except Exception as e:
            print(f"Error processing image: {e}")
            return []
        
class Splitter:
    def __init__(self):
        pass

    def split(self, content):
        # splitter = SemanticChunker(GoogleGenerativeAIEmbeddings(model="models/embedding-001"),breakpoint_threshold_type="percentile")
        # documents = semantic_splitter.create_documents([content])
        splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap = 100)
        split_documents = splitter.create_documents([content])

        return split_documents
    
    def merge_documents_to_text(self, documents):
        print("combining document content for splitting")
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
        else:
            vector_store = FAISS.load_local(
                vector_store_path, embeddings=self.embedder, allow_dangerous_deserialization=True
            )
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
# documents = loader.load_pdf("database/services/1234/rag_context/pdf document 2.pdf")

# splitter = Splitter()
# content = splitter.merge_documents_to_text(documents)
# chunks = splitter.split(content)
# print(chunks)
# print(len(chunks))

# embedder = Embedder()
# vector_store = embedder.embed("vector_store",chunks)
# print(vector_store)

# loader = Loader()
# documents = loader.load_pdf("database/services/1234/rag_context/pdf document 2.pdf")

# splitter = Splitter()
# content = splitter.merge_documents_to_text(documents)
# chunks = splitter.split(content)

# embedder = Embedder()
# updated_vector_store = embedder.embed_existing(vector_store, chunks)

# vector_store.save_local("faiss_store")
# vector_store = FAISS.load_local("faiss_store", embeddings=GoogleGenerativeAIEmbeddings(model="models/embedding-001"),allow_dangerous_deserialization=True)

# retriever = Retriever(vector_store)
# print(retriever)
# output = retriever.retrieve("what happens when the astronaut crosses the horizon")
# print(output)

# loader = Loader()
# documents = loader.load_pdf("database/services/1234/rag_context/pdf document 2.pdf")

# splitter = Splitter()
# content = splitter.merge_documents_to_text(documents)
# chunks = splitter.split(content)

# embedder = Embedder()
# updated_vector_store = embedder.embed_existing(vector_store, chunks)

# # Save the updated vector store
# updated_vector_store.save_local("faiss_store")

# # Load the updated vector store
# vector_store = FAISS.load_local("faiss_store", embeddings=GoogleGenerativeAIEmbeddings(model="models/embedding-001"), allow_dangerous_deserialization=True)


embedder = Embedder()
vector_store = embedder.get_vector_store("vector_store")
retriever = Retriever(vector_store)
print(retriever)
output = retriever.retrieve("explain alpha beta pruning with examples")
print(output)

context = "\n".join([doc.page_content for doc in output])

from agents import QueryAnsweringAgent
print(QueryAnsweringAgent().answer_query("explain alpha beta pruning with example",context))