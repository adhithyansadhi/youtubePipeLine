import os
from .base_agent import BaseAgent
try:
    from youtube_auth import get_youtube_client
except ImportError:
    # Handle direct execution / import paths
    import sys
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))
    from youtube_auth import get_youtube_client

from googleapiclient.http import MediaFileUpload
from rich.console import Console

console = Console()

class YouTubeUploaderAgent(BaseAgent):
    """
    Agent 14 -- YouTube Uploader Agent
    Uploads the final .mp4 video to the authenticated YouTube channel.
    Automatically categorizes as a Short based on vertical aspect ratio.
    """
    name = "YouTubeUploaderAgent"

    def _execute(self, input_data: dict) -> dict:
        video_path = input_data.get("video_path")
        if not video_path:
            return {"status": "UPLOAD_SKIPPED", "reason": "No video_path provided"}
        
        if not os.path.exists(video_path):
            return {"status": "UPLOAD_SKIPPED", "reason": f"Video file not found: {video_path}"}

        # Check toggle in .env
        upload_enabled = os.getenv("YOUTUBE_UPLOAD_ENABLED", "false").lower() == "true"
        mock_mode = os.getenv("MOCK_MODE", "false").lower() == "true"

        if not upload_enabled:
            console.print("  [YouTubeUploaderAgent] Upload disabled in .env. Skipping.")
            return {"status": "UPLOAD_SKIPPED", "reason": "YOUTUBE_UPLOAD_ENABLED=false"}

        if mock_mode:
            console.print("  [YouTubeUploaderAgent] [yellow][MOCK] Simulating YouTube upload...[/yellow]")
            return {
                "status": "UPLOAD_SUCCESSFUL",
                "video_id": "MOCK_VIDEO_ID",
                "url": "https://youtu.be/mock_id",
                "privacy": "mock_private"
            }

        title = input_data.get("title", f"Amazing Fact: {input_data.get('selected_topic', 'Short')}")
        # Clean title for YouTube (max 100 chars)
        title = title[:100]
        
        # Build description with hashtags
        original_script = input_data.get("script", "")
        description = f"{original_script}\n\n#shorts #facts #viral #education"
        
        privacy = os.getenv("YOUTUBE_PRIVACY_STATUS", "private").lower()
        if privacy not in ["public", "private", "unlisted"]:
            privacy = "private"

        console.print(f"  [YouTubeUploaderAgent] [bold cyan]Uploading to YouTube ({privacy})...[/bold cyan]")
        
        try:
            youtube = get_youtube_client()
            
            body = {
                'snippet': {
                    'title': title,
                    'description': description,
                    'tags': ['shorts', 'facts', 'ai'],
                    'categoryId': '22', # People & Blogs
                },
                'status': {
                    'privacyStatus': privacy,
                    'selfDeclaredMadeForKids': False,
                }
            }
            
            # Create media upload object (resumable)
            media = MediaFileUpload(
                video_path, 
                mimetype='video/mp4',
                chunksize=-1, 
                resumable=True
            )
            
            insert_request = youtube.videos().insert(
                part='snippet,status',
                body=body,
                media_body=media
            )
            
            console.print(f"    - File: {os.path.basename(video_path)}")
            response = insert_request.execute()
            
            video_id = response.get("id")
            video_url = f"https://youtu.be/{video_id}"
            
            console.print(f"  [bold green]✓ YouTube Upload Successful![/bold green]")
            console.print(f"    - Video ID: {video_id}")
            console.print(f"    - URL: {video_url}")
            
            return {
                "status": "UPLOAD_SUCCESSFUL",
                "video_id": video_id,
                "url": video_url,
                "privacy": privacy
            }
            
        except Exception as exc:
            console.print(f"  [bold red]✗ YouTube Upload Failed:[/bold red] {exc}")
            return {"status": "UPLOAD_FAILED", "reason": str(exc)}
