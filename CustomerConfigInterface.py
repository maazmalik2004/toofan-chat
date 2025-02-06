# from pymongo import MongoClient

# class CustomerConfigInterface():
#     def __init__(self, db_url = None):
#         self.collection = MongoClient(db_url)["toofan_local"]["customer_configs"]

#     def read(self, id):
#         print(f"[CUSTOMER CONFIG INTERFACE] READING CUSTOMER CONFIG {id}")
#         id = str(id)
#         found_record = self.collection.find_one({
#             "customer_id":id
#         })
#         return found_record

#     def write(self, id, value):
#         print(f"[CUSTOMER CONFIG INTERFACE] WRITING CUSTOMER CONFIG {id}")
#         id = str(id)
#         print(f"database write config {id}")
#         self.collection.replace_one({"customer_id": id}, value, upsert=True)
       
from pymongo import MongoClient

class CustomerConfigInterface():
    def __init__(self, db_url=None):
        self.collection = MongoClient(db_url)["toofan_local"]["customer_configs"]

    def read(self, id):
        print(f"[CUSTOMER CONFIG INTERFACE] READING CUSTOMER CONFIG {id}")
        id = str(id)
        found_record = self.collection.find_one({"customer_id": id})
        return found_record

    def write(self, id, value):
        print(f"[CUSTOMER CONFIG INTERFACE] WRITING CUSTOMER CONFIG {id}")
        id = str(id)

        # Ensure customer_id is included in the value
        value["customer_id"] = id

        # Update the record if it exists, otherwise insert a new one
        self.collection.update_one(
            {"customer_id": id}, 
            {"$set": value}, 
            upsert=True
        )
        print(f"[CUSTOMER CONFIG INTERFACE] CONFIG UPDATED FOR CUSTOMER {id}")
