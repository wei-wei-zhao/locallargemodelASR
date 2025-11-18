import queue
import threading
from vosk import Model, KaldiRecognizer
import json
import pyaudio  # 需单独安装：pip install pyaudio

class RealTimeCaptioner:
    def __init__(self, model_path):
        self.model = Model(model_path)
        self.recognizer = KaldiRecognizer(self.model, 16000)
        self.text_queue = queue.Queue()
    def audio_callback(self, in_data, frame_count, time_info, status):
        if self.recognizer.AcceptWaveform(in_data):
            result = json.loads(self.recognizer.Result())
            self.text_queue.put(result["text"])
        return (in_data, pyaudio.paContinue)
    def start_streaming(self):
        p = pyaudio.PyAudio()
        stream = p.open(format=pyaudio.paInt16, channels=1,
                        rate=16000, input=True,
                        stream_callback=self.audio_callback,
                        frames_per_buffer=4096)
        while True:
            try:
                print("字幕:", self.text_queue.get_nowait())
            except queue.Empty:
                pass


if __name__ == "__main__":
    print('启动完成')
    model_path = "./model/vosk-model-cn-0.22"
    captioner = RealTimeCaptioner(model_path)
    captioner.start_streaming()