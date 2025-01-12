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

        chat_context_raw = self.resource_manager.get(f'file_system/database/services/{customer_id}/{user_id}.json')
        config_raw = self.resource_manager.get("file_system/database/environment/config.json")

        chat_context = json.loads(chat_context_raw) if isinstance(chat_context_raw, str) else chat_context_raw
        config = json.loads(config_raw) if isinstance(config_raw, str) else config_raw

        if "chat_history" not in chat_context:
            chat_context["chat_history"] = []
            chat_context["chat_history_size"] = 0

        if chat_context["chat_history_size"] + 1 > config.get("chat_history_window_limit", 100):
            chat_context["chat_history"].pop(0)  # Remove the oldest chat
            chat_context["chat_history_size"] -= 1

        chat_context["chat_history"].append(chat_record)
        chat_context["chat_history_size"] += 1

        # (Optional) Summarize chat history (uncomment and fix if needed)
        # chat_context["chat_history_summary"] = SummarizingAgent().summarize_query(
        #     f"{chat_context['chat_history_summary']}\n{content}"
        # )

        # Save the updated context back to the resource manager
        self.resource_manager.set(f'file_system/database/services/{customer_id}/{user_id}.json', chat_context)

        return chat_record
