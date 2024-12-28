from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_core.documents import Document
from database_manager import DatabaseManager
from agents import ImageToDescriptionAgent

class Loader:
    def __init__(self):
        self.database_manager = DatabaseManager()
        self.image_description_generator = ImageToDescriptionAgent()

    def load_pdf(self, path):
        try:
            loader = PyPDFLoader(path)
            loaded_documents = loader.lazy_load()
            return list(loaded_documents)
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

loader = Loader()
documents = loader.load_image("database/services/1234/rag_context/image.jpeg")
print(documents)