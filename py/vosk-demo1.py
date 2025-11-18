# 导入必要的库
from vosk import Model, KaldiRecognizer
import json
import os
import noisereduce as nr
import librosa
import soundfile as sf
from pydub import AudioSegment
from datetime import datetime

# 配置参数
MODEL_PATH = "./model/vosk-model-cn-0.22"
SAMPLE_RATE = 16000
TEMP_DIR = "./temp"
OUTPUT_RESULT_DIR = "../uploadsoutputresult"

# 初始化全局模型和识别器
try:
    print(f"正在加载模型: {MODEL_PATH}")
    model = Model(MODEL_PATH)
    recognizer = KaldiRecognizer(model, SAMPLE_RATE)
    print("模型加载成功")
except Exception as e:
    print(f"模型加载失败: {str(e)}")
    raise

def convert_and_preprocess_audio(input_path):
    """
    将音频转换为WAV格式（单声道、16位、16000采样率）并进行降噪处理
    
    参数:
        input_path: 输入音频文件路径
    
    返回:
        处理后的音频文件路径，失败时返回None
    """
    # 获取绝对路径以便更好地调试和确保路径正确性
    abs_input_path = os.path.abspath(input_path)
    
    # 检查输入文件是否存在
    if not os.path.exists(abs_input_path):
        error_msg = f"输入文件不存在: {abs_input_path}"
        print(f"音频预处理出错: {error_msg}")
        return None
    
    # 确保输出目录存在
    os.makedirs(TEMP_DIR, exist_ok=True)
    
    # 生成临时输出文件名
    base_name = os.path.basename(input_path)
    name_without_ext = os.path.splitext(base_name)[0]
    output_path = os.path.join(TEMP_DIR, f"{name_without_ext}_processed.wav")
    temp_wav_path = os.path.join(TEMP_DIR, f"{name_without_ext}_temp.wav")
    
    try:
        print(f"开始转换音频格式: {abs_input_path}")
        
        # 使用pydub转换音频格式
        audio = AudioSegment.from_file(abs_input_path)
        
        # 转换为WAV格式，单声道，16位，16000采样率
        audio = audio.set_channels(1)  # 单声道
        audio = audio.set_frame_rate(SAMPLE_RATE)  # 采样率16000
        audio = audio.set_sample_width(2)  # 16位
        
        # 导出临时WAV文件
        audio.export(temp_wav_path, format="wav")
        print(f"已转换为临时WAV文件: {temp_wav_path}")
        
        # 使用librosa读取音频数据进行降噪
        print("读取音频数据进行降噪处理...")
        y, sr = librosa.load(temp_wav_path, sr=SAMPLE_RATE)
        
        # 执行降噪
        print("执行降噪处理...")
        y_denoised = nr.reduce_noise(y=y, sr=sr, stationary=False)
        
        # 保存处理后的音频
        sf.write(output_path, y_denoised, sr, subtype='PCM_16')
        print(f"降噪完成，保存至: {output_path}")
        
        return output_path
        
    except Exception as e:
        error_msg = f"{str(e)}"
        print(f"音频预处理出错: {error_msg}")
        return None
    
    finally:
        # 清理临时文件
        if os.path.exists(temp_wav_path):
            try:
                os.remove(temp_wav_path)
                print(f"已清理临时文件: {temp_wav_path}")
            except Exception as e:
                print(f"清理临时文件失败: {str(e)}")

def save_recognition_result(audio_path, recognition_result, start_time=None, end_time=None, process_time=None):
    """
    将语音识别结果保存到本地文件
    
    参数:
        audio_path: 输入音频文件路径
        recognition_result: 语音识别结果
        start_time: 识别开始时间（可选）
        end_time: 识别结束时间（可选）
        process_time: 处理时长（可选，单位：秒）
        
    返回:
        保存的结果文件路径，失败时返回None
    """
    # 创建输出目录
    os.makedirs(OUTPUT_RESULT_DIR, exist_ok=True)
    
    # 生成输出文件名（直接使用音频名称）
    base_name = os.path.basename(audio_path)
    name_without_ext = os.path.splitext(base_name)[0]
    output_file = os.path.join(OUTPUT_RESULT_DIR, f"{name_without_ext}.txt")
    
    try:
        # 保存结果到文件
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("语音识别结果：\n")
            f.write(recognition_result)
            f.write("\n\n")
            f.write("真实结果：现在这边展示数据都不太准确，希望可以展示的更准确一些，和大屏可以对应的上。")
        
        print(f"识别结果已保存至: {output_file}")
        return output_file
    except Exception as e:
        print(f"保存识别结果出错: {str(e)}")
        return None

def recognize_from_file(audio_path):
    """
    从音频文件中识别语音并保存结果
    
    参数:
        audio_path: 输入音频文件路径
    """
    # 获取绝对路径以便更好地调试
    abs_audio_path = os.path.abspath(audio_path)
    print(f"开始处理音频文件: {abs_audio_path}")
    
    # 记录开始时间
    start_time = datetime.now()
    print(f"识别开始时间: {start_time}")
    
    # 检查输入文件是否存在
    if not os.path.exists(abs_audio_path):
        error_msg = f"输入文件不存在: {abs_audio_path}"
        print(f"识别失败: {error_msg}")
        # 记录结束时间和处理时长
        end_time = datetime.now()
        process_time = (end_time - start_time).total_seconds()
        save_recognition_result(audio_path, error_msg, start_time, end_time, process_time)
        return
    
    # 预处理音频：转换格式并降噪
    processed_audio_path = convert_and_preprocess_audio(abs_audio_path)
    
    # 检查预处理是否成功
    if processed_audio_path is None:
        error_msg = "音频预处理失败，无法继续识别"
        print(error_msg)
        # 记录结束时间和处理时长
        end_time = datetime.now()
        process_time = (end_time - start_time).total_seconds()
        save_recognition_result(abs_audio_path, error_msg, start_time, end_time, process_time)
        return
    
    # 用于存储完整识别结果的变量
    full_recognition_result = ""
    
    try:
        print("开始识别音频...")
        
        # 检查处理后的文件是否存在
        if not os.path.exists(processed_audio_path):
            raise FileNotFoundError(f"处理后的音频文件不存在: {processed_audio_path}")
        
        # 使用全局初始化的识别器
        with open(processed_audio_path, "rb") as f:
            while True:
                # 分块读取音频数据
                data = f.read(4096)
                
                if len(data) == 0:
                    print("已读取完所有音频数据")
                    # 获取最后剩余的语音内容
                    final_result = json.loads(recognizer.FinalResult())["text"]
                    if final_result:
                        print(f"语音识别结果(最终段): {final_result}")
                        full_recognition_result += final_result + " "
                    break
                    
                # 将音频数据传递给识别器
                if recognizer.AcceptWaveform(data):
                    # 获取当前识别结果
                    result = json.loads(recognizer.Result())["text"]
                    if result:
                        print(f"语音识别结果: {result}")
                        full_recognition_result += result + " "
        
        # 记录结束时间和处理时长
        end_time = datetime.now()
        process_time = (end_time - start_time).total_seconds()
        print(f"识别结束时间: {end_time}")
        print(f"处理时长: {process_time:.2f} 秒")
        
        # 保存识别结果
        if full_recognition_result.strip():
            print(f"识别完成，总结果: {full_recognition_result.strip()}")
            save_recognition_result(abs_audio_path, full_recognition_result.strip(), start_time, end_time, process_time)
        else:
            print("未识别到有效内容")
            save_recognition_result(abs_audio_path, "[未识别到有效内容]", start_time, end_time, process_time)
        
    except Exception as e:
        error_msg = f"识别过程出错: {str(e)}"
        print(error_msg)
        # 记录结束时间和处理时长
        end_time = datetime.now()
        process_time = (end_time - start_time).total_seconds()
        # 出错时保存错误信息到文件
        save_recognition_result(abs_audio_path, error_msg, start_time, end_time, process_time)
    finally:
        # 清理临时文件
        if processed_audio_path != abs_audio_path and os.path.exists(processed_audio_path):
            try:
                os.remove(processed_audio_path)
                print(f"已清理临时文件: {processed_audio_path}")
            except Exception as e:
                print(f"清理临时文件失败: {str(e)}")
                pass

def main():
    """
    主函数，执行语音识别流程
    """
    print("===== 语音识别程序启动 =====")
    
    # 获取脚本所在目录
    script_dir = os.path.dirname(os.path.abspath(__file__))
    print(f"脚本所在目录: {script_dir}")
    
    # 构建正确的音频文件路径
    # audio_file = os.path.join(script_dir, "..", "assets", "baocaiming.mp3")
    audio_file = os.path.join(script_dir, "..", "assets", "testvoice.wav")
    audio_file = os.path.join(script_dir, "..", "assets", "testvoice1.wav")
    abs_audio_file = os.path.abspath(audio_file)
    
    print(f"要处理的音频文件路径: {abs_audio_file}")
    
    # 检查文件是否存在
    if os.path.exists(abs_audio_file):
        print(f"文件存在，开始处理: {abs_audio_file}")
        recognize_from_file(abs_audio_file)
    else:
        error_msg = f"错误: 文件不存在 - {abs_audio_file}"
        print(error_msg)
        # 即使文件不存在，也要保存错误信息
        save_recognition_result(audio_file, error_msg)
    
    print("===== 语音识别程序结束 =====")

# 执行主函数
if __name__ == "__main__":
    main()