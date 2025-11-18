from vosk import Model, KaldiRecognizer
import wave

# 加载模型（替换为你的实际路径）
# model_path = "/vosk-model-small-cn-0.22"
model_path = "/vosk-model-en-us-0.22"
model = Model(model_path)

# 读取音频文件（需 16kHz 单声道 WAV 格式）
wf = wave.open("./upload/rewav-1758616069310.wav", "rb")
rec = KaldiRecognizer(model, wf.getframerate())

# 逐帧识别
while True:
    data = wf.readframes(4000)
    if len(data) == 0:
        break
    if rec.AcceptWaveform(data):
        print(rec.Result())  # 输出识别结果

print(rec.FinalResult())  # 最终结果