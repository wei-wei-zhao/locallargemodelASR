
// 1. 加载模型（替换为你的实际路径）
const fs = require('fs');
const vosk = require('vosk');
const express = require('express');
const multer = require('multer');
const cors = require('cors');
const { exec } = require('child_process');
const ffmpeg = require('fluent-ffmpeg');
const ffmpegPath = require('ffmpeg-static');
const path = require('path');

// 设置 ffmpeg 可执行文件路径（使用 ffmpeg-static 提供的可执行文件）
// 尝试以鲁棒的方式设置 ffmpeg 可执行文件路径：
// 1) 优先使用 ffmpeg-static（如果存在且为文件）
// 2) 回退到 @ffmpeg-installer/ffmpeg（如果已安装）
// 3) 否则依赖系统 PATH 中的 ffmpeg
try {
  let resolvedFfmpegPath = ffmpegPath;
  // 某些包装可能返回对象，处理常见情况
  if (resolvedFfmpegPath && typeof resolvedFfmpegPath === 'object' && resolvedFfmpegPath.path) {
    resolvedFfmpegPath = resolvedFfmpegPath.path;
  }

  if (resolvedFfmpegPath && fs.existsSync(resolvedFfmpegPath) && fs.statSync(resolvedFfmpegPath).isFile()) {
    ffmpeg.setFfmpegPath(resolvedFfmpegPath);
    console.log('使用 ffmpeg 可执行文件（来自 ffmpeg-static）：', resolvedFfmpegPath);
  } else {
    // 尝试 @ffmpeg-installer/ffmpeg
    let triedInstaller = false;
    try {
      const ffmpegInstaller = require('@ffmpeg-installer/ffmpeg');
      if (ffmpegInstaller && ffmpegInstaller.path && fs.existsSync(ffmpegInstaller.path)) {
        ffmpeg.setFfmpegPath(ffmpegInstaller.path);
        console.log('使用 ffmpeg 可执行文件（来自 @ffmpeg-installer/ffmpeg）：', ffmpegInstaller.path);
        triedInstaller = true;
      }
    } catch (e) {
      // 忽略：模块不可用
    }

    if (!triedInstaller) {
      // 最后回退到系统 PATH 中的 ffmpeg（不显式设置）
      console.warn('未找到本地 ffmpeg 二进制文件，fluent-ffmpeg 将尝试使用系统 PATH 中的 ffmpeg。请确保已安装 ffmpeg 或安装 ffmpeg-static / @ffmpeg-installer/ffmpeg。');
    }
  }
} catch (err) {
  console.warn('设置 ffmpeg 路径时发生异常，回退到系统 ffmpeg（若可用）。错误：', err && err.message ? err.message : err);
}

// ----------------------------- 配置区域 ---------------------------------
// 模型路径（可根据需要修改）
const MODEL_PATH = './model/vosk-model-cn-0.22';
// const MODEL_PATH = "./model/vosk-model-small-cn-0.22";
// 上传临时目录
const UPLOAD_DIR = 'uploads';
const OUTPUT_DIR = 'uploadsoutput';
const RESULT_DIR = 'uploadsoutputresult';
const SAMPLE_RATE = 16000;

// 检查模型是否存在
if (!fs.existsSync(MODEL_PATH)) {
  console.error('模型路径不存在：', MODEL_PATH);
  process.exit(1);
}

// 降低 Vosk 日志
vosk.setLogLevel(0);
const model = new vosk.Model(MODEL_PATH);

// Express 应用
const app = express();
app.use(cors());

// multer 配置：文件保存到 uploads 临时目录
const upload = multer({ dest: UPLOAD_DIR + path.sep });

// 确保输出目录存在的辅助函数
function ensureDir(dirPath) {
  if (!fs.existsSync(dirPath)) {
    fs.mkdirSync(dirPath, { recursive: true });
  }
}

ensureDir(UPLOAD_DIR);
ensureDir(OUTPUT_DIR);
ensureDir(RESULT_DIR);

// ----------------------------- 工具函数 ---------------------------------
/**
 * 使用 fluent-ffmpeg 将任意音频文件转换为指定参数的 wav 文件
 * @param {string} inputPath 原始文件路径
 * @param {string} outputPath 输出 wav 路径
 * @returns {Promise<string>} 成功时返回 outputPath
 */
function convertAudio(inputPath, outputPath) {
  return new Promise((resolve, reject) => {
    ffmpeg(inputPath)
      .audioFrequency(SAMPLE_RATE) // 采样率
      .audioChannels(1) // 单声道
      .audioCodec('pcm_s16le') // PCM 16-bit
      .format('wav')
      .on('end', () => {
        console.log('音频转换完成:', outputPath);
        resolve(outputPath);
      })
      .on('error', (err) => {
        console.error('转换错误:', err.message || err);
        reject(err);
      })
      .save(outputPath);
  });
}

/**
 * 使用 Vosk 对 wav 文件执行识别
 * @param {string} wavPath wav 文件路径（采样率需与识别器一致）
 * @returns {Promise<string>} 识别出的文本
 */
function voskRecognize(wavPath) {
  return new Promise((resolve, reject) => {
    const wf = fs.createReadStream(wavPath);
    const rec = new vosk.Recognizer({ model: model, sampleRate: SAMPLE_RATE });

    wf.on('data', (data) => {
      try {
        rec.acceptWaveform(data);
      } catch (err) {
        console.error('acceptWaveform 错误:', err);
      }
    });

    wf.on('end', () => {
      try {
        const result = rec.finalResult().text;
        rec.free();
        resolve(result);
      } catch (err) {
        reject(err);
      }
    });

    wf.on('error', (err) => reject(err));
  });
}

/**
 * 使用系统 ffmpeg 将文件转换为指定参数（备用方案，保留以防 fluent-ffmpeg 不适用）
 * @param {string} input
 * @param {string} output
 * @returns {Promise<void>}
 */
function ffmpegExecConvert(input, output) {
  return new Promise((resolve, reject) => {
    const cmd = `ffmpeg -y -i "${input}" -ar ${SAMPLE_RATE} -ac 1 -c:a pcm_s16le -f wav "${output}"`;
    exec(cmd, (err, stdout, stderr) => {
      if (err) return reject(err);
      resolve();
    });
  });
}

/**
 * 安全删除文件（存在则删除）
 */
function safeUnlink(filePath) {
  try {
    if (filePath && fs.existsSync(filePath)) fs.unlinkSync(filePath);
  } catch (err) {
    console.warn('删除临时文件失败:', filePath, err.message || err);
  }
}

// ----------------------------- 路由：简单识别（用于测试） -------------------
// POST /recognize 接收已上传的音频文件并识别（示例/测试用）
app.post('/recognize', upload.single('audio'), async (req, res) => {
  if (!req.file) return res.status(400).json({ error: '没有接收到音频文件' });
  const input = req.file.path;
  // 如果上传即为 wav 且采样率正确，可直接识别；否则先转换
  const converted = path.join(OUTPUT_DIR, `${Date.now()}_${path.basename(input)}.wav`);

  try {
    await convertAudio(input, converted).catch(async (e) => {
      // 如果 fluent-ffmpeg 转换失败，尝试命令行转换
      console.warn('fluent-ffmpeg 转换失败，尝试命令行 ffmpeg：', e.message || e);
      await ffmpegExecConvert(input, converted);
    });

    const text = await voskRecognize(converted);
    res.json({ text });
  } catch (err) {
    console.error('/recognize 失败:', err.message || err);
    res.status(500).json({ error: '识别失败', details: err.message || String(err) });
  } finally {
    // 清理临时文件
    safeUnlink(input);
    safeUnlink(converted);
  }
});

// ----------------------------- 路由：实时录音识别（保留原接口名） -------------------
app.post('/recognizeByRecord', upload.single('audio'), async (req, res) => {
  if (!req.file) return res.status(400).json({ error: '没有接收到音频文件' });
  const input = req.file.path;
  const converted = path.join(OUTPUT_DIR, `${Date.now()}_${req.file.originalname.split('.')[0]}.wav`);

  try {
    // 使用命令行 ffmpeg 转换（更兼容 webm）
    await ffmpegExecConvert(input, converted);
    const text = await voskRecognize(converted);
    res.json({ text });
  } catch (err) {
    console.error('/recognizeByRecord 失败:', err.message || err);
    res.status(500).json({ error: '识别失败', details: err.message || String(err) });
  } finally {
    safeUnlink(input);
    safeUnlink(converted);
  }
});

// ----------------------------- 路由：通用上传并返回识别结果 -------------------
app.post('/uploadAudio', upload.single('audio'), async (req, res) => {
  if (!req.file) return res.status(400).json({ error: '没有接收到音频文件' });

  const input = req.file.path; // 临时上传文件
  const baseName = `${Date.now()}`;
  const converted = path.join(OUTPUT_DIR, `${baseName}.wav`);
  const resultOut = path.join(RESULT_DIR, `${baseName}.wav`);

  try {
    // 优先使用 fluent-ffmpeg 转换，失败后回退到命令行 ffmpeg
    await convertAudio(input, converted).catch(async (e) => {
      console.warn('convertAudio 失败，尝试 ffmpegExecConvert：', e.message || e);
      await ffmpegExecConvert(input, converted);
    });

    // 生成最终的识别用文件（保证采样率与格式）
    await ffmpegExecConvert(converted, resultOut).catch(() => {});

    // 识别
    const text = await voskRecognize(resultOut);
    console.log('识别结果:', text);
    res.json({
      success: true,
      originalFile: req.file.originalname,
      text,
    });
  } catch (err) {
    console.error('/uploadAudio 处理失败:', err.message || err);
    res.status(500).json({ error: '音频处理失败', details: err.message || String(err) });
  } finally {
    // 清理临时文件
    safeUnlink(input);
    safeUnlink(converted);
    safeUnlink(resultOut);
  }
});

// 启动服务
const PORT = process.env.PORT || 3000;
app.listen(PORT, () => console.log(`服务已启动： http://localhost:${PORT}`));