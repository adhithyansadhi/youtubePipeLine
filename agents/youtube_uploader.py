import os
import json
from datetime import datetime, timedelta
import pytz
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
    Supports auto-scheduling based on .env configuration.
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

        # -- Scheduling Logic --
        scheduling_enabled = os.getenv("SCHEDULE_ENABLE", "false").lower() == "true"
        publish_at_iso = None
        
        if scheduling_enabled:
            publish_at_iso = self._get_publish_time()
            if publish_at_iso:
                console.print(f"  [YouTubeUploaderAgent] [bold blue]Scheduling video for: {publish_at_iso}[/bold blue]")

        if mock_mode:
            console.print("  [YouTubeUploaderAgent] [yellow][MOCK] Simulating YouTube upload...[/yellow]")
            return {
                "status": "UPLOAD_SUCCESSFUL",
                "video_id": "MOCK_VIDEO_ID",
                "url": "https://youtu.be/mock_id",
                "privacy": "private" if scheduling_enabled else "public",
                "scheduled_at": publish_at_iso
            }

        title = input_data.get("title", f"Amazing Fact: {input_data.get('selected_topic', 'Short')}")
        title = title[:100]
        
        original_script = input_data.get("script", "")
        description = f"{original_script}\n\n#shorts #facts #viral #education"
        
        # Scheduling requires privacyStatus to be 'private'
        if scheduling_enabled:
            privacy = "private"
        else:
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

            if scheduling_enabled and publish_at_iso:
                body['status']['publishAt'] = publish_at_iso

            # Create media upload object
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
            if scheduling_enabled:
                console.print(f"    - Scheduled for: {publish_at_iso}")
            console.print(f"    - Video ID: {video_id}")
            console.print(f"    - URL: {video_url}")
            
            return {
                "status": "UPLOAD_SUCCESSFUL",
                "video_id": video_id,
                "url": video_url,
                "privacy": privacy,
                "scheduled_at": publish_at_iso
            }
            
        except Exception as exc:
            console.print(f"  [bold red]✗ YouTube Upload Failed:[/bold red] {exc}")
            return {"status": "UPLOAD_FAILED", "reason": str(exc)}

    def _get_publish_time(self) -> str | None:
        """
        Calculate the next available ISO 8601 timestamp for scheduling.
        Uses SCHEDULE_TIME and SCHEDULE_TIMEZONE from .env.
        """
        try:
            tz_str = os.getenv("SCHEDULE_TIMEZONE", "Asia/Kolkata")
            time_str = os.getenv("SCHEDULE_TIME", "20:00")
            
            tz = pytz.timezone(tz_str)
            now = datetime.now(tz)
            
            target_hour, target_min = map(int, time_str.split(':'))
            
            # Create target time for today
            target_time = now.replace(hour=target_hour, minute=target_min, second=0, microsecond=0)
            
            # If target time has already passed today, schedule for tomorrow
            if now >= target_time:
                target_time += timedelta(days=1)
            
            # YouTube API requires UTC ISO 8601 format
            utc_time = target_time.astimezone(pytz.UTC)
            return utc_time.strftime("%Y-%m-%dT%H:%M:%SZ")

        except Exception as e:
            console.print(f"  [yellow][YouTubeUploaderAgent] Error calculating schedule time: {e}[/yellow]")
            return None
