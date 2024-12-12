import asyncio
import os
import requests
from tqdm import tqdm
import instaloader
from TikTokApi import TikTokApi
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# Async function to download a video from Instagram
async def download_instagram_video(post_url, save_path="videos"):
    # Initialize instaloader to interact with Instagram
    L = instaloader.Instaloader()
    
    # Extract post shortcode from the URL and get the post object
    post = instaloader.Post.from_shortcode(L.context, post_url.split("/")[-2])
    
    # Get the video URL from the Instagram post
    video_url = post.video_url
    
    # Make a request to download the video stream
    response = requests.get(video_url, stream=True)
    
    # Define the file path to save the downloaded video
    file_path = os.path.join(save_path, f"instagram_{post.shortcode}.mp4")
    
    # Open the file in write-binary mode to save the video
    with open(file_path, 'wb') as f:
        total_size = int(response.headers.get('content-length', 0))  # Get total size of video for progress bar
        # Use tqdm to display a progress bar during the download
        with tqdm(total=total_size, unit='B', unit_scale=True, desc="Instagram Video Downloading") as pbar:
            # Download the video in chunks and update the progress bar
            for chunk in response.iter_content(chunk_size=1024):
                if chunk:
                    f.write(chunk)
                    pbar.update(len(chunk))
    print(f"Instagram video saved to {file_path}")

# Async function to download a video from TikTok
async def download_tiktok_video(post_url, save_path="videos"):
    # Initialize TikTokApi to interact with TikTok
    api = TikTokApi.get_instance()
    
    # Extract the video ID from the TikTok URL
    video_id = post_url.split('/')[-1]
    
    # Get the video object using the TikTokApi and retrieve the video bytes
    video = api.video(id=video_id)
    video_bytes = video.bytes()
    
    # Define the file path to save the downloaded video
    file_path = os.path.join(save_path, f"tiktok_{video_id}.mp4")
    
    # Write the video bytes to a file
    with open(file_path, 'wb') as f:
        f.write(video_bytes)
    print(f"TikTok video saved to {file_path}")

# Async function to download videos from both Instagram and TikTok based on the platform
async def download_video(post_url, platform, save_path="videos"):
    if platform.lower() == "instagram":
        # If the platform is Instagram, call the Instagram download function
        await download_instagram_video(post_url, save_path)
    elif platform.lower() == "tiktok":
        # If the platform is TikTok, call the TikTok download function
        await download_tiktok_video(post_url, save_path)

# Async function to get the upload URL from the server
async def get_upload_url(token):
    headers = {
        "Flic-Token": token,
        "Content-Type": "application/json"
    }
    # Make a GET request to get the pre-signed upload URL
    response = requests.get("https://api.socialverseapp.com/posts/generate-upload-url", headers=headers)
    return response.json()['upload_url']  # Extract the upload URL from the response

# Async function to upload a video to the server
async def upload_video(file_path):
    token = "flic_f67e3e6704d8b29c9c62244720f01bc45de3a6378f0e4c01e8b3d1b2a07a4bfc"  # Replace with actual token
    upload_url = await get_upload_url(token)  # Get the pre-signed upload URL
    
    # Open the video file in binary mode to upload
    with open(file_path, "rb") as video_file:
        # Make a PUT request to upload the video to the server
        response = requests.put(upload_url, files={"file": video_file})
        if response.status_code == 200:
            # If upload is successful, remove the local video file
            os.remove(file_path)
            print(f"Uploaded and deleted: {file_path}")
        else:
            print(f"Upload failed for: {file_path}")

# Class to handle new files created in the monitored directory
class VideoHandler(FileSystemEventHandler):
    def on_created(self, event):
        if event.src_path.endswith(".mp4"):  # Check if the created file is a .mp4 video
            # If it is a video, create an async task to upload it
            asyncio.create_task(upload_video(event.src_path))

# Function to monitor the directory for new video files
async def monitor_directory(path='/videos'):
    event_handler = VideoHandler()  # Initialize the event handler
    observer = Observer()  # Initialize the observer to watch the directory
    observer.schedule(event_handler, path, recursive=False)  # Watch the specified path for new files
    observer.start()  # Start monitoring the directory
    
    try:
        while True:
            pass  # Keep the monitoring running
    except KeyboardInterrupt:
        observer.stop()  # Stop the observer if the program is interrupted
    observer.join()

# Main function to handle the downloading of multiple videos concurrently
async def main():
    # Example video URLs from Instagram and TikTok
    instagram_url = "https://www.instagram.com/p/VIDEO_ID/"
    tiktok_url = "https://www.tiktok.com/@username/video/VIDEO_ID"
    
    save_path = "videos"  # Directory to save the downloaded videos
    
    os.makedirs(save_path, exist_ok=True)  # Create the save directory if it doesn't exist
    
    # Download both Instagram and TikTok videos concurrently
    await asyncio.gather(
        download_video(instagram_url, "instagram", save_path),
        download_video(tiktok_url, "tiktok", save_path)
    )
    
    # Start monitoring the directory for new video files
    await asyncio.to_thread(monitor_directory)

# Run the async tasks (downloads and monitoring)
asyncio.run(main())
