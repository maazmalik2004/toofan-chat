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

        if "chat_history" not in config:
            config["chat_history"] = []
            config["chat_history_size"] = 0

        if config["chat_history_size"] + 1 > config.get("chat_history_window_limit", 100):
            config["chat_history"].pop(0)  # Remove the oldest chat
            config["chat_history_size"] -= 1

        config["chat_history"].append(chat_record)
        config["chat_history_size"] += 1

        # (Optional) Summarize chat history (uncomment and fix if needed)
        # config["chat_history_summary"] = SummarizingAgent().summarize_query(
        #     f"{config['chat_history_summary']}\n{content}"
        # )

        # Save the updated context back to the resource manager
        self.resource_manager.set(f'file_system/database/services/{customer_id}/{user_id}.json', config)

        return chat_record
