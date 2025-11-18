from vosk import Model, KaldiRecognizer
import json
import pyaudio  # 需单独安装：pip install pyaudio
# 初始化模型和识别器
model = Model("voskModel")
recognizer = KaldiRecognizer(model, 16000)  # 16kHz 采样率
# 音频流处理
p = pyaudio.PyAudio()
stream = p.open(format=pyaudio.paInt16, channels=1,
                rate=16000, input=True, frames_per_buffer=4096)
while True:
    data = stream.read(4096)
    if recognizer.AcceptWaveform(data):
        result = json.loads(recognizer.Result())
        print("识别结果:", result["text"])

# def recognize_from_file(audio_path, model_path):
#     model = Model(model_path)
#     recognizer = KaldiRecognizer(model, 16000)
#     with open(audio_path, "rb") as f:
#         while True:
#             data = f.read(4096)
#             if len(data) == 0:
#                 break
#             if recognizer.AcceptWaveform(data):
#                 print(json.loads(recognizer.FinalResult())["text"])
# # 使用示例
# recognize_from_file("test.wav", "./model/vosk-model-en-us-0.22")