class DefaultConfigManager:
    def __init__(self, resource_manager = None):
        self.resource_manager = resource_manager

    def get_default_config(self, customer_id):
        default_config = self.resource_manager.get("file_system/database/environment/default_config.json")
        default_config["customer_id"] = customer_id
        return default_config