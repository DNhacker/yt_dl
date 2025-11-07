import os
import sys
from typing import Optional, Tuple
from pytube import YouTube
from pathlib import Path
from pytube.exceptions import PytubeError
from moviepy.editor import VideoFileClip, AudioFileClip
from tqdm import tqdm
import tempfile
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class YouTubeDownloader:
    """
    A class to download YouTube videos in HD MP4 and MP3 formats.
    """
    
    def __init__(self, output_path: str = "./downloads"):
        """
        Initialize the downloader.
        
        Args:
            output_path (str): Directory where files will be saved
        """
        self.output_path = output_path
        self._ensure_output_directory()
    
    def _ensure_output_directory(self):
        """Create output directory if it doesn't exist."""
        os.makedirs(self.output_path, exist_ok=True)
    
    def _get_video_stream(self, yt: YouTube, resolution: str = "720p") -> Optional[any]:
        """
        Get the best video stream for the specified resolution.
        
        Args:
            yt: YouTube object
            resolution: Video resolution (e.g., "720p", "1080p")
            
        Returns:
            Video stream or None if not found
        """
        try:
            # Try to get progressive stream (video + audio)
            streams = yt.streams.filter(
                progressive=True, 
                file_extension='mp4',
                resolution=resolution
            ).order_by('resolution').desc()
            
            if streams:
                return streams.first()
            
            # If no progressive stream, get adaptive video stream
            video_streams = yt.streams.filter(
                adaptive=True,
                only_video=True,
                file_extension='mp4',
                resolution=resolution
            ).order_by('resolution').desc()
            
            return video_streams.first() if video_streams else None
            
        except Exception as e:
            logger.error(f"Error getting video stream: {e}")
            return None
    
    def _get_audio_stream(self, yt: YouTube) -> Optional[any]:
        """
        Get the best audio stream.
        
        Args:
            yt: YouTube object
            
        Returns:
            Audio stream or None if not found
        """
        try:
            audio_streams = yt.streams.filter(
                only_audio=True,
                file_extension='mp4'
            ).order_by('abr').desc()
            
            return audio_streams.first() if audio_streams else None
        except Exception as e:
            logger.error(f"Error getting audio stream: {e}")
            return None
    
    def download_mp4(self, url: str, filename: str = None, resolution: str = "720p") -> str:
        """
        Download YouTube video as MP4.
        
        Args:
            url: YouTube video URL
            filename: Output filename (without extension)
            resolution: Video resolution ("720p", "1080p", etc.)
            
        Returns:
            Path to downloaded file
            
        Raises:
            Exception: If download fails
        """
        try:
            yt = YouTube(url)
            
            if filename is None:
                filename = self._sanitize_filename(yt.title)
            
            # Get video stream
            video_stream = self._get_video_stream(yt, resolution)
            
            if not video_stream:
                # Fallback to highest resolution available
                video_stream = yt.streams.filter(
                    progressive=True, file_extension='mp4'
                ).order_by('resolution').desc().first()
                
                if not video_stream:
                    video_stream = yt.streams.get_highest_resolution()
            
            logger.info(f"Downloading: {yt.title}")
            logger.info(f"Resolution: {video_stream.resolution}")
            
            # Download with progress bar
            file_path = video_stream.download(
                output_path=self.output_path,
                filename=filename
            )
            
            # Ensure .mp4 extension
            if not file_path.endswith('.mp4'):
                new_path = file_path + '.mp4'
                os.rename(file_path, new_path)
                file_path = new_path
            
            logger.info(f"Download completed: {file_path}")
            return file_path
            
        except PytubeError as e:
            logger.error(f"Pytube error: {e}")
            raise Exception(f"Failed to download video: {e}")
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            raise Exception(f"Failed to download video: {e}")
    
    def download_mp3(self, url: str, filename: str = None) -> str:
        """
        Download YouTube video as MP3 audio.
        
        Args:
            url: YouTube video URL
            filename: Output filename (without extension)
            
        Returns:
            Path to downloaded MP3 file
            
        Raises:
            Exception: If download or conversion fails
        """
        try:
            yt = YouTube(url)
            
            if filename is None:
                filename = self._sanitize_filename(yt.title)
            
            # Get audio stream
            audio_stream = self._get_audio_stream(yt)
            
            if not audio_stream:
                raise Exception("No suitable audio stream found")
            
            logger.info(f"Downloading audio: {yt.title}")
            
            # Download audio to temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as temp_file:
                temp_path = temp_file.name
            
            audio_stream.download(filename=temp_path)
            
            # Convert to MP3
            output_path = os.path.join(self.output_path, f"{filename}.mp3")
            
            logger.info("Converting to MP3...")
            audio_clip = AudioFileClip(temp_path)
            audio_clip.write_audiofile(output_path, verbose=False, logger=None)
            audio_clip.close()
            
            # Clean up temporary file
            os.unlink(temp_path)
            
            logger.info(f"MP3 conversion completed: {output_path}")
            return output_path
            
        except PytubeError as e:
            logger.error(f"Pytube error: {e}")
            raise Exception(f"Failed to download audio: {e}")
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            raise Exception(f"Failed to download audio: {e}")
    
    def _sanitize_filename(self, filename: str) -> str:
        """
        Sanitize filename by removing invalid characters.
        
        Args:
            filename: Original filename
            
        Returns:
            Sanitized filename
        """
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            filename = filename.replace(char, '_')
        return filename.strip()
    
    def get_video_info(self, url: str) -> dict:
        """
        Get video information.
        
        Args:
            url: YouTube video URL
            
        Returns:
            Dictionary with video information
        """
        try:
            yt = YouTube(url)
            return {
                'title': yt.title,
                'author': yt.author,
                'length': yt.length,
                'views': yt.views,
                'publish_date': yt.publish_date,
                'description': yt.description[:200] + '...' if yt.description and len(yt.description) > 200 else yt.description
            }
        except Exception as e:
            logger.error(f"Error getting video info: {e}")
            return {}


def main():
    """Command-line interface."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Download YouTube videos in HD MP4 and MP3 formats')
    parser.add_argument('url', help='YouTube video URL')
    parser.add_argument('-t', '--type', choices=['mp4', 'mp3'], default='mp4', 
                       help='Download type (mp4 or mp3)')
    parser.add_argument('-o', '--output', help='Output filename (without extension)')
    parser.add_argument('-r', '--resolution', default='720p', 
                       help='Video resolution for MP4 (e.g., 720p, 1080p)')
    parser.add_argument('--output-dir', default='./downloads', 
                       help='Output directory')
    
    args = parser.parse_args()
    
    try:
        downloader = YouTubeDownloader(output_path=args.output_dir)
        
        if args.type == 'mp4':
            file_path = downloader.download_mp4(
                args.url, 
                args.output, 
                args.resolution
            )
        else:
            file_path = downloader.download_mp3(args.url, args.output)
        
        print(f"Download completed: {file_path}")
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
