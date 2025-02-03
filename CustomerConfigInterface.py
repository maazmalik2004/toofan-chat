from pymongo import MongoClient

class CustomerConfigInterface():
    def __init__(self, db_url = None):
        self.collection = MongoClient(db_url)["toofan_local"]["customer_configs"]

    def read(self, id):
        # id = str(id)
        found_record = self.collection.find_one({
            "customer_id":id
        })
        return found_record

    def write(self, id, value):
        # id = str(id)
        old_record = self.collection.find_one({
            "customer_id":id
        })
        if old_record:
            self.collection.replace_one(old_record, value)
            return True
        else:
            self.collection.insert_one(value)
            return True

# cli = CustomerConfigInterface(db_url = "mongodb://localhost:27017/")

# record = {
#     "customer_id":"1234",
#     "customer_name":"zomato",
#     "key1":"value1",
#     "key2":"valueupdated"
# }

# # print(cli.read("1234"))
# print(cli.write("1234", record))