# 国旗图片批量下载程序

一个功能强大的命令行工具，用于从 https://flagcdn.com 批量下载各国国旗图片。支持异步和同步两种下载模式，提供灵活的文件命名选项和智能的文件管理功能。

## 📥 快速下载

### 方式一：克隆仓库
```bash
git clone https://github.com/your-repo/flags-downloader.git
cd flags-downloader
```

### 方式二：复制代码文件
1. 将提供的代码文件保存为 `flags-downloader.py`、`flags-downloader-async.py`、`flags-downloader-sync.py`
2. 运行对应文件开始使用

## 🚀 快速开始

### 1. 安装依赖
```bash
# 基础依赖
pip install Pillow

# 异步模式（默认）
pip install aiohttp aiofiles

# 或同步模式
pip install requests
```

### 2. 首次运行
```bash
# 运行统一版本，自动下载国家代码文件
python flags-downloader.py
```

程序会自动：
1. 从 `https://flagcdn.com/zh/codes.json` 下载国家代码
2. 生成 `codes.json`（完整数据）和 `codes.txt`（纯代码列表）
3. 开始下载默认尺寸的国旗图片

### 3. 查看帮助
```bash
python flags-downloader.py --help
```

## 📋 核心功能

### 智能国家代码管理
- **自动下载**：当本地无国家代码文件时，自动从 flagcdn.com 下载
- **双格式支持**：同时生成 `codes.json` 和 `codes.txt`
- **智能识别**：自动检测并兼容多种格式文件

### 灵活的图片配置
- **多种尺寸**：支持 40+ 种预定义尺寸
- **多格式支持**：PNG、WebP、SVG、JPG 四种格式
- **批量处理**：支持多国家、多尺寸、多格式组合下载

### 智能文件管理
- **断点续传**：自动跳过已存在的文件
- **强制重下**：通过 `-f` 参数强制重新下载
- **重试机制**：默认2次重试，提高成功率
- **失败记录**：自动保存失败任务列表

## 🔧 使用方法

### 基本命令
```bash
# 使用默认设置下载（统一版本）
python flags-downloader.py

# 指定国家代码文件
python flags-downloader.py codes.txt

# 使用JSON文件（包含国家名称）
python flags-downloader.py codes.json

# 异步专用版本
python flags-downloader-async.py

# 同步专用版本
python flags-downloader-sync.py
```

### 常用参数组合
```bash
# 下载指定尺寸和格式
python flags-downloader.py --sizes w80,256x192 --formats png,webp

# 包含国家名称在文件名中
python flags-downloader.py codes.json --include-country-name

# 高并发下载，跳过确认
python flags-downloader.py --concurrent 30 --yes

# 强制重新下载所有文件
python flags-downloader.py --force
```

## ⚙️ 参数详解

### 输入文件
- `文件路径` (可选): 国家代码文件路径，支持 `.txt` 或 `.json` 格式
  - 默认: `codes.txt`
  - 示例: `python flags-downloader.py my_codes.txt`

### 尺寸选项 (`--sizes`)
支持三种尺寸类型：
- **宽度固定**: `w20`, `w40`, `w80`, `w160`, `w320`, `w640`, `w1280`, `w2560`
- **高度固定**: `h20`, `h24`, `h40`, `h60`, `h80`, `h120`, `h240`
- **精确尺寸**: `16x12`, `20x15`, `24x18`, ..., `256x192`

```bash
# 查看所有支持的尺寸
python flags-downloader.py --list-sizes

# 使用多个尺寸
python flags-downloader.py --sizes w80,h60,80x60
```

### 格式选项 (`--formats`)
- 支持: `png`, `webp`, `svg`, `jpg`
- 默认: `png`
- 多格式用逗号分隔

```bash
# 下载PNG和WebP格式
python flags-downloader.py --formats png,webp
```

### 下载控制
- `--force`, `-f`: 强制重新下载所有文件
- `--concurrent`, `-c`: 最大并发数 (默认: 20)
- `--max-retries`, `-r`: 最大重试次数 (默认: 2)
- `--timeout`, `-t`: 请求超时时间(秒) (默认: 30)
- `--yes`, `-y`: 跳过确认提示

### 文件名格式
- `--filename-format`, `--ff`: 文件名格式
  - `simple`: `{国家代码}_{尺寸}.{格式}` (默认)
  - `full`: `{国家代码}_{尺寸}_{宽度}x{高度}.{格式}`
- `--include-country-name`, `--icn`: 在文件名中包含国家名称

### 下载模式 (`--mode`)
- `async`: 异步模式 (默认，性能最佳)
- `sync`: 同步模式 (兼容性更好)

## 📁 输出结构

程序按尺寸和格式创建目录：

```
w80_png/                    # simple格式
├── cn_w80.png
├── us_w80.png
└── ...

w80_png_full/              # full格式  
├── cn_w80_40x80.png
├── us_w80_100x53.png
└── ...

w80_png_named/             # 包含国家名称
├── cn_w80_中国.png
├── us_w80_美国.png
└── ...
```

## 📝 使用示例

### 示例1：基本下载所有国家
```bash
# 下载所有国家的默认尺寸PNG图片
python flags-downloader.py

# 输出：w80_png/ 目录，包含200+个国旗文件
```

### 示例2：自定义尺寸和格式
```bash
# 下载三种尺寸的PNG和WebP图片
python flags-downloader.py --sizes w80,h60,80x60 --formats png,webp

# 输出：6个目录，每个目录200+个文件
# w80_png/, w80_webp/, h60_png/, h60_webp/, 80x60_png/, 80x60_webp/
```

### 示例3：包含国家名称
```bash
# 使用json文件，在文件名中包含国家名称
python flags-downloader.py codes.json --include-country-name --sizes w80

# 输出文件名示例：
# cn_w80_中国.png
# us_w80_美国.png
# jp_w80_日本.png
```

### 示例4：完整格式下载
```bash
# 使用完整文件名格式，包含实际图片尺寸
python flags-downloader.py --filename-format full --sizes w80

# 输出文件名示例：
# cn_w80_40x80.png  (中国国旗实际尺寸)
# us_w80_100x53.png  (美国国旗实际尺寸)
```

### 示例5：高级批量处理
```bash
# 跳过确认，强制重下，高并发，包含国家名称
python flags-downloader.py codes.json \
  --yes \
  --force \
  --concurrent 30 \
  --include-country-name \
  --sizes w80,w160,256x192 \
  --formats png,webp
```

## ❓ 常见问题

### Q1: 首次运行时报"找不到文件"错误？
**A**: 这是正常现象。程序会自动检测并下载国家代码文件，只需按照提示操作即可。

### Q2: 下载速度很慢怎么办？
**A**: 可以调整 `--concurrent` 参数提高并发数：
```bash
python flags-downloader.py --concurrent 50
```

### Q3: 部分国家下载失败怎么办？
**A**: 程序会自动重试，最终失败的任务会保存到 `failed_downloads_时间戳.txt` 文件中。

### Q4: 如何只下载特定国家的国旗？
**A**: 创建自定义的 `my_codes.txt` 文件：
```
cn
us
jp
gb
de
fr
```
然后运行：
```bash
python flags-downloader.py my_codes.txt
```

### Q5: 支持哪些图片格式？
**A**: 支持 PNG、WebP、SVG、JPG 四种格式。SVG是矢量格式，其他是位图格式。

### Q6: 文件名中的特殊字符如何处理？
**A**: 程序会自动处理特殊字符，确保生成合法的文件名。

## 📊 性能优化建议

1. **网络环境好时**：使用异步模式，提高并发数
   ```bash
   python flags-downloader.py --mode async --concurrent 50
   ```

2. **网络环境差时**：使用同步模式，降低并发数
   ```bash
   python flags-downloader.py --mode sync --concurrent 10 --timeout 60
   ```

3. **批量下载时**：合理选择尺寸，避免下载过大文件
   ```bash
   # 推荐尺寸
   python flags-downloader.py --sizes w80,80x60
   ```

## 🔍 故障排除

### 错误：SSL证书验证失败
```bash
# 临时解决方案（不推荐生产环境）
export PYTHONHTTPSVERIFY=0
python flags-downloader.py
```

### 错误：模块未找到
```bash
# 安装缺失的模块
pip install aiohttp aiofiles Pillow

# 或使用同步模式（不需要aiohttp）
python flags-downloader.py --mode sync
```

### 错误：权限不足
```bash
# 确保有写入权限
chmod +x flags-downloader.py
```

## 📄 文件说明

- `flags-downloader.py` - 主程序（统一版本，支持两种模式）
- `flags-downloader-async.py` - 纯异步版本
- `flags-downloader-sync.py` - 纯同步版本
- `codes.json` - 国家代码JSON文件（自动生成）
- `codes.txt` - 国家代码文本文件（自动生成）
- `failed_downloads_*.txt` - 失败任务记录（自动生成）

## 📜 许可证

本项目仅供学习和研究使用。国旗图片版权归各自国家所有，请遵守相关法律法规和网站使用条款。

## 🤝 贡献

欢迎提交 Issue 和 Pull Request 来改进这个工具。

## 📞 支持

如有问题，请：
1. 查看本文档的"常见问题"部分
2. 检查错误信息中的提示
3. 提交 Issue 描述具体问题

---

**开始使用**：只需运行 `python flags-downloader.py`，程序会引导您完成所有步骤！