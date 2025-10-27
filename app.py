import os
from flask import Flask, request, jsonify, render_template
from azure.storage.blob import BlobServiceClient, ContentSettings
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

load_dotenv()

# ---------------------------
# Flask app setup
# ---------------------------
app = Flask(__name__)

# ---------------------------
# Azure Blob Storage setup
# ---------------------------
CONTAINER_NAME = os.getenv("IMAGES_CONTAINER", "lanternfly-images")
CONN_STR = os.getenv("STORAGE_CONNECTION_STRING")

blob_service_client = None

try:
    if CONN_STR:
        blob_service_client = BlobServiceClient.from_connection_string(CONN_STR)
        print("✅ Connected to Azure Blob Storage")
    else:
        print("⚠️ STORAGE_CONNECTION_STRING not set")
except Exception as e:
    print("❌ Failed to connect to Blob Storage:", e)

# ---------------------------
# Health check
# ---------------------------
@app.route("/api/v1/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "message": "Server is running"}), 200

# ---------------------------
# Upload endpoint
# ---------------------------
@app.route("/api/v1/upload", methods=["POST"])
def upload_image():
    if not blob_service_client:
        return jsonify({"ok": False, "error": "Blob service not initialized"}), 500

    if "file" not in request.files:
        return jsonify({"ok": False, "error": "No file uploaded"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"ok": False, "error": "No file selected"}), 400

    safe_name = secure_filename(file.filename)
    blob_name = f"{safe_name}"

    try:
        container_client = blob_service_client.get_container_client(CONTAINER_NAME)
        # Upload blob (will create container if not exists)
        try:
            container_client.create_container()
        except Exception:
            pass  # container likely exists

        container_client.upload_blob(
            name=blob_name,
            data=file,
            overwrite=True,
            content_settings=ContentSettings(content_type=file.content_type)
        )

        url = f"https://{blob_service_client.account_name}.blob.core.windows.net/{CONTAINER_NAME}/{blob_name}"
        return jsonify({"ok": True, "url": url}), 200

    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

# ---------------------------
# Gallery endpoint
# ---------------------------
@app.route("/api/v1/gallery", methods=["GET"])
def gallery():
    if not blob_service_client:
        return jsonify({"ok": False, "error": "Blob service not initialized"}), 500

    try:
        container_client = blob_service_client.get_container_client(CONTAINER_NAME)
        blob_list = container_client.list_blobs()
        urls = [
            f"https://{blob_service_client.account_name}.blob.core.windows.net/{CONTAINER_NAME}/{blob.name}"
            for blob in blob_list
        ]
        return jsonify({"ok": True, "gallery": urls}), 200
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

# ---------------------------
# Optional index page
# ---------------------------
@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")

# ---------------------------
# Run the app
# ---------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
