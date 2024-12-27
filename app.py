from flask import Flask
from database_manager import DatabaseManager
from cache_manager import CacheManager

app = Flask(__name__)
db = DatabaseManager()

def db_read_json_callback(key):
    split_key = key.split("-")
    customer_id = split_key[0]
    user_id = split_key[1]
    print("DB READ OPERATION")
    return db.read_json(f'database/services/{customer_id}/{user_id}.json')

def db_write_json_callback(key,value):
    split_key = key.split("-")
    customer_id = split_key[0]
    user_id = split_key[1]
    print("DB WRITE OPERATION")
    db.write_json(f'database/services/{customer_id}/{user_id}.json',value)


chat_cache = CacheManager(max_length=10,load_callback=db_read_json_callback,store_callback=db_write_json_callback)

@app.route('/chat')
def chat():
    key1 = f'1234-1234'
    key2 = f'1234-2345'

    read_chat_context_1 = chat_cache.get(key1)
    read_chat_context_2 = chat_cache.get(key2)

    print("------------------")

    chat_cache.get(key1)
    chat_cache.get(key2)

    print("------------------")
    
    # chat_cache.activate(key1,read_chat_context_1)
    # chat_cache.activate(key2,read_chat_context_2)

    get_data_1 = chat_cache.get(key1)
    get_data_1["chat_history_summary"] = "lu"
    get_data_1["chat_history"][0]["chat_id"] = "bi"
    get_data_2 = chat_cache.get(key2)
    get_data_2["chat_history_summary"] = "ar"
    chat_cache.update(key1, get_data_1)
    chat_cache.update(key2, get_data_2)

    # chat_cache.deactivate(key1)
    # chat_cache.deactivate(key2)

    return [get_data_1,get_data_2]

if __name__ == '__main__':
    app.run(debug=True)