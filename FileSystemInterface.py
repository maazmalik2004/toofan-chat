import json
import base64
import shutil
from pathlib import Path
from typing import Any, Literal
import fitz  # PyMuPDF

class FileSystemInterface:
    def __init__(self):
        self.supported_extensions = {
            '.json': self._handle_json,
            '.jpg': self._handle_image,
            '.jpeg': self._handle_image,
            '.png': self._handle_image,
            '.gif': self._handle_image,
            '.pdf': self._handle_pdf
        }
    
    def _ensure_directory(self, path: Path):
        """Ensure the directory exists for the given path."""
        path.parent.mkdir(parents=True, exist_ok=True)
    
    def read(self, file_path: str) -> Any:
        path = Path(file_path).resolve()
        extension = path.suffix.lower()
        
        if extension not in self.supported_extensions:
            raise ValueError(f"Unsupported file extension: {extension}")

        # Create directory if it doesn't exist
        self._ensure_directory(path)

        if extension == '.json' and not path.exists():
            return None

        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        return self.supported_extensions[extension](path, 'read')
    
    def write(self, file_path: str, content: Any):
        path = Path(file_path).resolve()
        extension = path.suffix.lower()
        
        if extension not in self.supported_extensions:
            raise ValueError(f"Unsupported file extension: {extension}")
        
        # Create directory if it doesn't exist
        self._ensure_directory(path)
        self.supported_extensions[extension](path, 'write', content)
    
    def delete(self, file_path: str):
        path = Path(file_path).resolve()
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        path.unlink()
    
    def move_file(self, source: str, destination: str):
        src_path = Path(source).resolve()
        dst_path = Path(destination).resolve()
        
        if not src_path.exists():
            raise FileNotFoundError(f"Source file not found: {source}")
            
        if dst_path.exists():
            raise FileExistsError(f"Destination file already exists: {destination}")
        
        self._ensure_directory(dst_path)
        shutil.move(str(src_path), str(dst_path))
    
    def copy_file(self, source: str, destination: str):
        src_path = Path(source).resolve()
        dst_path = Path(destination).resolve()
        
        if not src_path.exists():
            raise FileNotFoundError(f"Source file not found: {source}")
            
        if dst_path.exists():
            raise FileExistsError(f"Destination file already exists: {destination}")
        
        self._ensure_directory(dst_path)
        shutil.copy2(str(src_path), str(dst_path))
    
    def file_exists(self, file_path: str) -> bool:
        return Path(file_path).resolve().exists()
    
    def _handle_json(self, file_path: Path, operation: Literal['read', 'write'], content: Any = None):
        if operation == 'read':
            if not file_path.exists():
                return None
            with open(file_path, 'r') as f:
                return json.load(f)
        else:
            with open(file_path, 'w') as f:
                json.dump(content, f, indent=4)
    
    def _handle_image(self, file_path: Path, operation: Literal['read', 'write'], content: Any = None):
        if operation == 'read':
            with open(file_path, 'rb') as f:
                return base64.b64encode(f.read()).decode('utf-8')
        else:
            image_data = base64.b64decode(content)
            with open(file_path, 'wb') as f:
                f.write(image_data)
    
    def _handle_pdf(self, file_path: Path, operation: Literal['read', 'write'], content: Any = None):
        if operation == 'read':
            return fitz.open(file_path)
        else:
            if not isinstance(content, fitz.Document):
                raise TypeError("Content must be a fitz.Document object for PDF writing")
            content.save(str(file_path))

# import json
# import base64
# import shutil
# import zlib
# from pathlib import Path
# from typing import Any, Union, Dict, Optional, Literal
# import asyncio
# import aiofiles
# from contextlib import contextmanager
# import fitz  # PyMuPDF

# class FileSystemInterface:
#     def __init__(self, cache_size: int = 128, compress_cache: bool = False):
#         if cache_size <= 0:
#             raise ValueError("Cache size must be positive")
        
#         self.supported_extensions = {
#             '.json': self._handle_json,
#             '.jpg': self._handle_image,
#             '.jpeg': self._handle_image,
#             '.png': self._handle_image,
#             '.gif': self._handle_image,
#             '.pdf': self._handle_pdf
#         }
#         self.cache_size = cache_size
#         self._cache: Dict[str, Union[bytes, Any]] = {}
#         self.compress_cache = compress_cache
#         self._lock = asyncio.Lock()
    
#     def _compress_content(self, content: Any, content_type: str) -> bytes:
#         if content_type == 'json':
#             return zlib.compress(json.dumps(content).encode())
#         elif content_type == 'image':
#             return zlib.compress(content.encode() if isinstance(content, str) else content)
#         elif content_type == 'pdf':
#             return zlib.compress(content)
#         raise ValueError(f"Unsupported content type: {content_type}")
    
#     def _decompress_content(self, content: bytes, content_type: str) -> Any:
#         decompressed = zlib.decompress(content)
#         if content_type == 'json':
#             return json.loads(decompressed.decode())
#         elif content_type == 'image':
#             return decompressed.decode()
#         elif content_type == 'pdf':
#             return decompressed
#         raise ValueError(f"Unsupported content type: {content_type}")
    
#     def _get_content_type(self, extension: str) -> str:
#         if extension == '.json':
#             return 'json'
#         elif extension == '.pdf':
#             return 'pdf'
#         return 'image'
    
#     @contextmanager
#     def _cache_operation(self, cache_key: str):
#         try:
#             yield
#         except Exception as e:
#             self._cache.pop(cache_key, None)
#             raise e
    
#     def read(self, file_path: str) -> Any:
#         path = Path(file_path).resolve()
#         cache_key = str(path)
        
#         if cache_key in self._cache:
#             content = self._cache[cache_key]
#             content_type = self._get_content_type(path.suffix.lower())
#             if content_type == 'pdf':
#                 decompressed = self._decompress_content(content, content_type) if self.compress_cache else content
#                 return fitz.open("pdf", decompressed)
#             return self._decompress_content(content, content_type) if self.compress_cache else content
        
#         if not path.exists():
#             raise FileNotFoundError(f"File not found: {file_path}")
        
#         extension = path.suffix.lower()
#         if extension not in self.supported_extensions:
#             raise ValueError(f"Unsupported file extension: {extension}")
        
#         with self._cache_operation(cache_key):
#             content = self.supported_extensions[extension](path, 'read')
            
#             if len(self._cache) >= self.cache_size:
#                 lru_key = next(iter(self._cache))
#                 self._cache.pop(lru_key)
            
#             if extension == '.pdf':
#                 # For PDFs, cache the raw bytes
#                 pdf_bytes = content.tobytes() if hasattr(content, 'tobytes') else None
#                 if pdf_bytes:
#                     if self.compress_cache:
#                         self._cache[cache_key] = self._compress_content(pdf_bytes, 'pdf')
#                     else:
#                         self._cache[cache_key] = pdf_bytes
#             else:
#                 if self.compress_cache:
#                     self._cache[cache_key] = self._compress_content(content, self._get_content_type(extension))
#                 else:
#                     self._cache[cache_key] = content
            
#             return content
    
#     async def read_file_async(self, file_path: str, max_retries: int = 3) -> Any:
#         path = Path(file_path).resolve()
#         cache_key = str(path)
        
#         if cache_key in self._cache:
#             content = self._cache[cache_key]
#             content_type = self._get_content_type(path.suffix.lower())
#             if content_type == 'pdf':
#                 decompressed = self._decompress_content(content, content_type) if self.compress_cache else content
#                 return fitz.open("pdf", decompressed)
#             return self._decompress_content(content, content_type) if self.compress_cache else content
        
#         if not path.exists():
#             raise FileNotFoundError(f"File not found: {file_path}")
        
#         extension = path.suffix.lower()
#         if extension not in self.supported_extensions:
#             raise ValueError(f"Unsupported file extension: {extension}")
        
#         async with self._lock:
#             for attempt in range(max_retries):
#                 try:
#                     if extension == '.json':
#                         async with aiofiles.open(path, 'r') as f:
#                             content = json.loads(await f.read())
#                     elif extension == '.pdf':
#                         async with aiofiles.open(path, 'rb') as f:
#                             pdf_bytes = await f.read()
#                             content = fitz.open("pdf", pdf_bytes)
#                             if self.compress_cache:
#                                 self._cache[cache_key] = self._compress_content(pdf_bytes, 'pdf')
#                             else:
#                                 self._cache[cache_key] = pdf_bytes
#                             return content
#                     else:
#                         async with aiofiles.open(path, 'rb') as f:
#                             content = base64.b64encode(await f.read()).decode('utf-8')
                    
#                     if len(self._cache) >= self.cache_size:
#                         lru_key = next(iter(self._cache))
#                         self._cache.pop(lru_key)
                    
#                     if self.compress_cache and extension != '.pdf':
#                         self._cache[cache_key] = self._compress_content(content, self._get_content_type(extension))
#                     elif extension != '.pdf':
#                         self._cache[cache_key] = content
                    
#                     return content
                    
#                 except (IOError, json.JSONDecodeError) as e:
#                     if attempt == max_retries - 1:
#                         raise
#                     await asyncio.sleep(0.1 * (attempt + 1))
    
#     def write(self, file_path: str, content: Any):
#         path = Path(file_path).resolve()
#         cache_key = str(path)
#         extension = path.suffix.lower()
        
#         if extension not in self.supported_extensions:
#             raise ValueError(f"Unsupported file extension: {extension}")
        
#         with self._cache_operation(cache_key):
#             self.supported_extensions[extension](path, 'write', content)
            
#             if len(self._cache) >= self.cache_size:
#                 lru_key = next(iter(self._cache))
#                 self._cache.pop(lru_key)
            
#             if extension == '.pdf':
#                 pdf_bytes = content.tobytes() if hasattr(content, 'tobytes') else None
#                 if pdf_bytes:
#                     if self.compress_cache:
#                         self._cache[cache_key] = self._compress_content(pdf_bytes, 'pdf')
#                     else:
#                         self._cache[cache_key] = pdf_bytes
#             else:
#                 if self.compress_cache:
#                     self._cache[cache_key] = self._compress_content(content, self._get_content_type(extension))
#                 else:
#                     self._cache[cache_key] = content
    
#     async def write_file_async(self, file_path: str, content: Any, max_retries: int = 3):
#         path = Path(file_path).resolve()
#         cache_key = str(path)
#         extension = path.suffix.lower()
        
#         if extension not in self.supported_extensions:
#             raise ValueError(f"Unsupported file extension: {extension}")
        
#         async with self._lock:
#             for attempt in range(max_retries):
#                 try:
#                     if extension == '.json':
#                         async with aiofiles.open(path, 'w') as f:
#                             await f.write(json.dumps(content, indent=4))
#                     elif extension == '.pdf':
#                         # PDF writing needs to be done synchronously since fitz doesn't support async
#                         content.save(str(path))
#                         pdf_bytes = content.tobytes() if hasattr(content, 'tobytes') else None
#                         if pdf_bytes:
#                             if self.compress_cache:
#                                 self._cache[cache_key] = self._compress_content(pdf_bytes, 'pdf')
#                             else:
#                                 self._cache[cache_key] = pdf_bytes
#                     else:
#                         image_data = base64.b64decode(content)
#                         async with aiofiles.open(path, 'wb') as f:
#                             await f.write(image_data)
                    
#                     if len(self._cache) >= self.cache_size:
#                         lru_key = next(iter(self._cache))
#                         self._cache.pop(lru_key)
                    
#                     if extension != '.pdf':
#                         if self.compress_cache:
#                             self._cache[cache_key] = self._compress_content(content, self._get_content_type(extension))
#                         else:
#                             self._cache[cache_key] = content
                    
#                     return
                    
#                 except IOError as e:
#                     if attempt == max_retries - 1:
#                         raise
#                     await asyncio.sleep(0.1 * (attempt + 1))
    
#     def delete(self, file_path: str):
#         path = Path(file_path).resolve()
#         if not path.exists():
#             raise FileNotFoundError(f"File not found: {file_path}")
#         path.unlink()
#         self._cache.pop(str(path), None)
    
#     def move_file(self, source: str, destination: str):
#         src_path = Path(source).resolve()
#         dst_path = Path(destination).resolve()
        
#         if not src_path.exists():
#             raise FileNotFoundError(f"Source file not found: {source}")
            
#         if dst_path.exists():
#             raise FileExistsError(f"Destination file already exists: {destination}")
        
#         shutil.move(str(src_path), str(dst_path))
#         src_cache_key = str(src_path)
#         dst_cache_key = str(dst_path)
        
#         if src_cache_key in self._cache:
#             self._cache[dst_cache_key] = self._cache.pop(src_cache_key)
    
#     def copy_file(self, source: str, destination: str):
#         src_path = Path(source).resolve()
#         dst_path = Path(destination).resolve()
        
#         if not src_path.exists():
#             raise FileNotFoundError(f"Source file not found: {source}")
            
#         if dst_path.exists():
#             raise FileExistsError(f"Destination file already exists: {destination}")
        
#         shutil.copy2(str(src_path), str(dst_path))
        
#         src_cache_key = str(src_path)
#         if src_cache_key in self._cache:
#             self._cache[str(dst_path)] = self._cache[src_cache_key]
    
#     def file_exists(self, file_path: str) -> bool:
#         return Path(file_path).resolve().exists()
    
#     def clear_cache(self, file_path: Optional[str] = None):
#         if file_path:
#             cache_key = str(Path(file_path).resolve())
#             self._cache.pop(cache_key, None)
#         else:
#             self._cache.clear()
    
#     def _handle_json(self, file_path: Path, operation: Literal['read', 'write'], content: Any = None):
#         if operation == 'read':
#             with open(file_path, 'r') as f:
#                 return json.load(f)
#         else:
#             with open(file_path, 'w') as f:
#                 json.dump(content, f, indent=4)
    
#     def _handle_image(self, file_path: Path, operation: Literal['read', 'write'], content: Any = None):
#         if operation == 'read':
#             with open(file_path, 'rb') as f:
#                 return base64.b64encode(f.read()).decode('utf-8')
#         else:
#             image_data = base64.b64decode(content)
#             with open(file_path, 'wb') as f:
#                 f.write(image_data)
    
#     def _handle_pdf(self, file_path: Path, operation: Literal['read', 'write'], content: Any = None):
#         if operation == 'read':
#             return fitz.open(file_path)
#         else:
#             if not isinstance(content, fitz.Document):
#                 raise TypeError("Content must be a fitz.Document object for PDF writing")
#             content.save(str(file_path))

