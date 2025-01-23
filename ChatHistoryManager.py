from uuid import uuid4
from datetime import datetime
import json

class ChatHistoryManager:
    def __init__(self, resource_manager=None):
        self.resource_manager = resource_manager

    def append(self, customer_id, user_id, by, type, content):
        chat_record = {
            "chat_id": str(uuid4()),
            "from": by,
            "timestamp": str(datetime.now()),
            "type": type,
            "content": content
        }
        
        config = self.resource_manager.get("file_system/database/environment/config.json")
        user_context = self.resource_manager.get(f"user_context/{customer_id}{user_id}")

        if not user_context:
            raise Exception("User has not connected yet. chat history unavailable. please use the /connect endpoint to do the same")
        
        if not user_context.get("chat_history"):
            user_context["chat_history_size"] = 0
            user_context["chat_history"]= []
        
        if not user_context.get("chat_history_size"):
            user_context["chat_history_size"] = len(user_context.get("chat_history"))
        
        if user_context["chat_history_size"] + 1 > config.get("chat_history_window_limit"):
            print('aalu')
            user_context["chat_history"].pop(0)  # Remove the oldest chat
            print("gobi")
            user_context["chat_history_size"] -= 1
        
        print('baian')
        user_context["chat_history"].append(chat_record)
        user_context["chat_history_size"] += 1

        self.resource_manager.set(f'user_context/{customer_id}{user_id}', user_context)

        return chat_record
