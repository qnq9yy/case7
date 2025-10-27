import os
from dotenv import load_dotenv

dotenv_path = os.path.join(os.getcwd(), ".env")
print("Checking .env file at:", dotenv_path)

if os.path.exists(dotenv_path):
    print(".env file FOUND ✅")
    load_dotenv(dotenv_path)
else:
    print(".env file NOT FOUND ❌")

print("STORAGE_ACCOUNT_URL =", os.getenv("STORAGE_ACCOUNT_URL"))
print("IMAGES_CONTAINER =", os.getenv("IMAGES_CONTAINER"))
print("AZURE_STORAGE_CONNECTION_STRING =", os.getenv("AZURE_STORAGE_CONNECTION_STRING")[:60], "...")
