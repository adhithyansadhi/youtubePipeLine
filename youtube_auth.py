import os
import google_auth_oauthlib.flow
import googleapiclient.discovery
import google.auth.transport.requests
from google.oauth2.credentials import Credentials

# Scopes required for uploading videos
SCOPES = ["https://www.googleapis.com/auth/youtube.upload", "https://www.googleapis.com/auth/youtube.readonly"]
TOKEN_FILE = "token.json"
CLIENT_SECRET_FILE = "client_secret.json"

def get_youtube_client():
    """
    Load credentials from token.json or perform initial OAuth2 flow.
    Returns an authenticated YouTube service object.
    """
    creds = None
    
    # Check if we have a saved token
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    
    # If no valid creds, perform login
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("  [YouTube Auth] Refreshing expired token...")
            creds.refresh(google.auth.transport.requests.Request())
        else:
            if not os.path.exists(CLIENT_SECRET_FILE):
                raise FileNotFoundError(
                    f"CRITICAL: {CLIENT_SECRET_FILE} not found. "
                    "Please follow the setup guide to create OAuth Desktop credentials."
                )
            
            print("  [YouTube Auth] Starting initial login flow...")
            print("  [YouTube Auth] A browser window should open shortly.")
            
            flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(
                CLIENT_SECRET_FILE, SCOPES
            )
            # This will launch a local server and wait for the user to auth in browser
            creds = flow.run_local_server(port=0, host="localhost", open_browser=True)
            
        # Save the credentials for next time
        with open(TOKEN_FILE, "w") as token:
            token.write(creds.to_json())
            print(f"  [YouTube Auth] Success! Credentials saved to {TOKEN_FILE}")
            
    return googleapiclient.discovery.build("youtube", "v3", credentials=creds)

if __name__ == "__main__":
    # Test function
    try:
        print("Testing YouTube API connection...")
        youtube = get_youtube_client()
        # Fetch channel info as a test
        request = youtube.channels().list(part="snippet,contentDetails,statistics", mine=True)
        response = request.execute()
        channel_name = response['items'][0]['snippet']['title']
        print(f"CONNECTED: Authenticated as channel '{channel_name}'")
    except Exception as e:
        print(f"ERROR: {e}")
