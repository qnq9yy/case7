import os
from datetime import datetime
from flask import Flask, request, jsonify
from flask import render_template
from azure.storage.blob import BlobServiceClient, ContentSettings
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Load .env and configuration
# ---------------------------------------------------------------------------
dotenv_path = os.path.join(os.getcwd(), ".env")
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path=dotenv_path)
    print("✅ .env file loaded successfully!")
else:
    print("⚠️  .env file not found — using environment defaults")

STORAGE_ACCOUNT_URL = os.getenv("STORAGE_ACCOUNT_URL")
CONTAINER_NAME = os.getenv("IMAGES_CONTAINER", "lanternfly-images")
CONN_STR = os.getenv("STORAGE_CONNECTION_STRING")

# ---------------------------------------------------------------------------
# Azure connection
# ---------------------------------------------------------------------------
try:
    if CONN_STR:
        blob_service_client = BlobServiceClient.from_connection_string(CONN_STR)
    elif STORAGE_ACCOUNT_URL:
        blob_service_client = BlobServiceClient(account_url=STORAGE_ACCOUNT_URL)
    else:
        raise ValueError("Missing STORAGE_ACCOUNT_URL or STORAGE_CONNECTION_STRING")

    print("✅ Successfully connected to Azure Blob Storage!")
except Exception as e:
    print("❌ Failed to connect to Azure Blob Storage:", e)
    blob_service_client = None

# ---------------------------------------------------------------------------
# Flask setup
# ---------------------------------------------------------------------------
app = Flask(__name__)

# ---------------------------------------------------------------------------
# Health check endpoint
# ---------------------------------------------------------------------------
@app.route("/api/v1/health", methods=["GET"])
def health():
    """Simple health check endpoint"""
    return jsonify({"status": "ok", "message": "Server is running"}), 200

# ---------------------------------------------------------------------------
# Upload endpoint
# ---------------------------------------------------------------------------
@app.route("/api/v1/upload", methods=["POST"])
def upload_image():
    """Uploads an image to Azure Blob Storage (auto-creates container if missing)."""
    if not blob_service_client:
        return jsonify({"ok": False, "error": "Blob service not initialized"}), 500

    if "file" not in request.files:
        return jsonify({"ok": False, "error": "No file part in the request"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"ok": False, "error": "No file selected"}), 400

    # Sanitize filename and prepend timestamp
    safe_name = secure_filename(file.filename)
    timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%S")
    blob_name = f"{timestamp}-{safe_name}"

    try:
        container_client = blob_service_client.get_container_client(CONTAINER_NAME)

        # Auto-create the container if it doesn't exist
        try:
            container_client.create_container()
            print(f"🆕 Created container: {CONTAINER_NAME}")
        except Exception:
            pass  # likely already exists

        container_client.upload_blob(
            name=blob_name,
            data=file,
            overwrite=True,
            content_settings=ContentSettings(content_type=file.content_type),
        )

        blob_url = f"https://{blob_service_client.account_name}.blob.core.windows.net/{CONTAINER_NAME}/{blob_name}"
        print(f"✅ Uploaded: {blob_url}")

        return jsonify({"ok": True, "url": blob_url}), 200

    except Exception as e:
        print("❌ Upload failed:", e)
        return jsonify({"ok": False, "error": str(e)}), 500

# ---------------------------------------------------------------------------
# Gallery endpoint
# ---------------------------------------------------------------------------
@app.route("/api/v1/gallery", methods=["GET"])
def gallery():
    """List all image URLs in the container."""
    try:
        container_client = blob_service_client.get_container_client(CONTAINER_NAME)
        blob_list = container_client.list_blobs()

        urls = [
            f"https://{blob_service_client.account_name}.blob.core.windows.net/{CONTAINER_NAME}/{blob.name}"
            for blob in blob_list
        ]

        return jsonify({"ok": True, "gallery": urls}), 200
    except Exception as e:
        print("❌ Gallery load failed:", e)
        return jsonify({"ok": False, "error": str(e)}), 500

# ---------------------------------------------------------------------------
# Root route
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Run the app
# ---------------------------------------------------------------------------
# --------------------------------------------
# Run the Flask app only when executed directly
# --------------------------------------------


@app.get("/")
def index():
    return render_template("index.html")

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
