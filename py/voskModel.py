# 实时识别

import os
from vosk import Model
model_path = "./model/vosk-model-cn-0.22"
from vosk import Model, KaldiRecognizer
import json
import pyaudio  # 需单独安装：pip install pyaudio
# 初始化模型和识别器
model = Model(model_path)
recognizer = KaldiRecognizer(model, 16000)  # 16kHz 采样率
# 音频流处理
p = pyaudio.PyAudio()
stream = p.open(format=pyaudio.paInt16, channels=1,
                rate=16000, input=True, frames_per_buffer=4096)
while True:
    data = stream.read(4096)
    if recognizer.AcceptWaveform(data):
        result = json.loads(recognizer.Result())
        # if result["text"] != "":
        print("识别结果:", result["text"])
