import os
from datetime import datetime
from flask import Flask, request, jsonify
from werkzeug.utils import secure_filename
from azure.storage.blob import BlobServiceClient, ContentSettings
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

STORAGE_CONNECTION_STRING = os.getenv("STORAGE_CONNECTION_STRING")
CONTAINER_NAME = os.getenv("IMAGES_CONTAINER", "lanternfly-images")

# Initialize Azure Blob Service
try:
    blob_service_client = BlobServiceClient.from_connection_string(STORAGE_CONNECTION_STRING)
    container_client = blob_service_client.get_container_client(CONTAINER_NAME)

    # Auto-create container if it doesn't exist
    try:
        container_client.create_container()
        print(f"🆕 Created container: {CONTAINER_NAME}")
    except Exception:
        pass  # already exists

    print("✅ Blob service initialized!")
except Exception as e:
    print("❌ Failed to initialize blob service:", e)
    blob_service_client = None
    container_client = None

# Initialize Flask app
app = Flask(__name__)

# Health check endpoint
@app.route("/api/v1/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "message": "Server is running"}), 200

# Upload endpoint
@app.route("/api/v1/upload", methods=["POST"])
def upload_image():
    if not blob_service_client:
        return jsonify({"ok": False, "error": "Blob service not initialized"}), 500

    if "file" not in request.files:
        return jsonify({"ok": False, "error": "No file part in the request"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"ok": False, "error": "No file selected"}), 400

    # Safe filename with timestamp
    safe_name = secure_filename(file.filename)
    timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%S")
    blob_name = f"{timestamp}-{safe_name}"

    try:
        container_client.upload_blob(
            name=blob_name,
            data=file,
            overwrite=True,
            content_settings=ContentSettings(content_type=file.content_type)
        )

        blob_url = f"https://{blob_service_client.account_name}.blob.core.windows.net/{CONTAINER_NAME}/{blob_name}"
        return jsonify({"ok": True, "url": blob_url}), 200
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

# Gallery endpoint
@app.route("/api/v1/gallery", methods=["GET"])
def gallery():
    if not blob_service_client:
        return jsonify({"ok": False, "error": "Blob service not initialized"}), 500

    try:
        blobs = container_client.list_blobs()
        urls = [
            f"https://{blob_service_client.account_name}.blob.core.windows.net/{CONTAINER_NAME}/{blob.name}"
            for blob in blobs
        ]
        return jsonify({"ok": True, "gallery": urls}), 200
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

# Root route (optional)
@app.route("/", methods=["GET"])
def index():
    return "Flask app running!"

# Run Flask app
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
