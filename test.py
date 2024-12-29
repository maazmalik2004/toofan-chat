from flask import Flask, request

app = Flask(__name__)

@app.route('/upload', methods=['POST'])
def upload():
    file = request.files.get('file')
    value = request.form.get('value')

    print(file)
    print(value)

    # Print the received file and value
    if file:
        print(f"Received file: {file.filename}")
    if value:
        print(f"Received value: {value}")

    return "File and value received successfully"

if __name__ == '__main__':
    app.run(debug=True)
