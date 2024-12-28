from flask import Flask, redirect
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

@app.route('/')
def handle_root():
    # to return API usage information
    return redirect("https://www.example.com",code=302)

@app.route('/chat')
def chat():
    customer_id = "1234"
    user_id = "2345"

    key = f'{customer_id}-{user_id}'

    chat_cache.get(key)

    print("------------------")

    chat_cache.get(key)

    print("------------------")

    get_data = chat_cache.get(key)
    get_data["chat_history_summary"] = "update1"
    get_data["chat_history"][0]["chat_id"] = "update2"
    chat_cache.update(key, get_data)

    return [get_data]

if __name__ == '__main__':
    app.run(debug=True)