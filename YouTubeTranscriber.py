import whisper
import yt_dlp
import os
import re
import torch
import logging


# Whisper 설정
class YouTubeTranscriber:
    def __init__(self, model_size='base', language='ko'):
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model = whisper.load_model(model_size).to(self.device)
        self.language = language
        self.output_directory = "transcriptions"
        os.makedirs(self.output_directory, exist_ok=True)

    def _extract_video_id(self, url):
        match = re.search(r'(?:v=|\/)([0-9A-Za-z_-]{11}).*', url)
        return match.group(1) if match else None

    def download_audio(self, url):
        try:
            video_id = self._extract_video_id(url)
            ydl_opts = {
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'wav',
                    'preferredquality': '192',
                }],
                'outtmpl': os.path.join(self.output_directory, f'{video_id}.%(ext)s'),
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info_dict = ydl.extract_info(url, download=True)
                audio_filename = ydl.prepare_filename(info_dict)
                audio_path = audio_filename.rsplit(".", 1)[0] + ".wav"
                return audio_path
        except Exception as e:
            self.logger.error(f"Audio download error: {e}")
            return None

    def transcribe(self, url):
        try:
            audio_path = self.download_audio(url)
            if not audio_path:
                self.logger.error("Audio download failed.")
                return None
            
            result = self.model.transcribe(audio_path, language=self.language, fp16=torch.cuda.is_available())
            return result
        except Exception as e:
            self.logger.error(f"Whisper transcription error: {e}")
            return None
