from flask import Flask, request, jsonify
from connection import connect_db, huggingFace_vectorizer, LLM_pipeline
from chunks import extract_text_from_pdf, ChunkData, CreateDataObjects
import weaviate.classes.config as wc
import weaviate.classes as wvc
import os
import tempfile
import atexit

app = Flask(__name__)


client = connect_db()


atexit.register(lambda: client.close())

collection_name = "HR_doc"

if collection_name not in client.collections.list_all():
    client.collections.create(
        name=collection_name,
        vectorizer_config=huggingFace_vectorizer(),
        properties=[wc.Property(name="body", data_type=wc.DataType.TEXT)],
    )

collection = client.collections.get(collection_name)


@app.route("/upload", methods=["POST"])
def upload():
    try:
        if "file" not in request.files:
            return jsonify({"message": "No file part"}), 400
        file = request.files["file"]
        if file.filename == "":
            return jsonify({"message": "No selected file"}), 400
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp:
            file.save(temp.name)
            text = extract_text_from_pdf(temp.name)
            chunks = ChunkData(text)
            CreateDataObjects(chunks, collection)
        return jsonify({"message": "PDF processed and data stored successfully."})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/chat", methods=["POST"])
def chat():
    try:
        data = request.get_json()
        query = data.get("query", "")
        response = collection.query.near_text(
            query=query,
            limit=1,
            return_metadata=wvc.query.MetadataQuery(score=True, explain_score=True),
        )
        if response.objects:
            context = response.objects[0].properties["body"]
            prompt = f"Context: {context}\n\nQuestion: {query}"
            answer = LLM_pipeline(prompt)
            return jsonify({"response": answer})
        else:
            return jsonify(
                {"response": "I'm sorry, I couldn't find relevant information."}
            )
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/end_chat", methods=["POST"])
def end_chat():
    try:
        if collection_name in client.collections.list_all():
            client.collections.delete(collection_name)
            print(f"Collection '{collection_name}' deleted successfully.")
            return jsonify(
                {"message": f"Collection '{collection_name}' deleted successfully."}
            )
        else:
            return (
                jsonify({"message": f"Collection '{collection_name}' does not exist."}),
                404,
            )
    except Exception as e:
        print(f"Error deleting collection: {e}")
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True)
