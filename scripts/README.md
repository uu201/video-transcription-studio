# 模型路径修复工具

## 问题描述

某些版本的 ModelScope 在下载模型时，会在 `MODELSCOPE_CACHE` 指定的目录下再创建一个 `models/` 子目录，导致模型路径变成：

```
data/models/models/iic/SenseVoiceSmall/...  ❌ 错误
```

而代码期望的路径是：

```
data/models/iic/SenseVoiceSmall/...  ✅ 正确
```

## 自动修复

系统会在模型加载时自动检测并修复这个问题，通常不需要手动干预。

## 手动修复

如果自动修复失败，可以使用提供的修复脚本：

### 方法 1: 使用 Python 脚本（推荐）

```bash
python scripts/fix_model_path.py
```

这个脚本会：
1. 检测嵌套的 `models/` 目录
2. 将 `iic` 目录移动到正确位置
3. 合并已存在的文件（不覆盖）
4. 清理临时文件和空目录
5. 验证模型结构完整性

### 方法 2: 手动移动文件

**Windows PowerShell:**
```powershell
# 检查是否存在嵌套目录
if (Test-Path "data\models\models\iic") {
    # 如果目标已存在，需要合并
    if (Test-Path "data\models\iic") {
        Write-Host "目标已存在，建议使用 Python 脚本进行合并"
    } else {
        Move-Item -Path "data\models\models\iic" -Destination "data\models\iic" -Force
        Remove-Item "data\models\models" -Recurse -Force
        Write-Host "修复完成"
    }
}
```

**Linux/macOS:**
```bash
# 检查是否存在嵌套目录
if [ -d "data/models/models/iic" ]; then
    # 如果目标已存在，需要合并
    if [ -d "data/models/iic" ]; then
        echo "目标已存在，建议使用 Python 脚本进行合并"
    else
        mv data/models/models/iic data/models/iic
        rm -rf data/models/models
        echo "修复完成"
    fi
fi
```

## 验证修复结果

运行以下命令验证模型位置：

```bash
python scripts/fix_model_path.py
```

输出示例：
```
2024-XX-XX 10:00:00 - INFO - 模型目录: D:\JavaProjects\视频转文案\data\models
2024-XX-XX 10:00:00 - INFO - 未检测到需要修复的问题
2024-XX-XX 10:00:00 - INFO - 
验证模型结构...
2024-XX-XX 10:00:00 - INFO - 模型文件大小: 892.92 MB
2024-XX-XX 10:00:00 - INFO - ✓ 模型结构验证通过
2024-XX-XX 10:00:00 - INFO - ✓ 所有检查通过，模型可以正常使用
```

## 预防措施

系统已经实现了自动修复机制，在模型加载时会：

1. **设置正确的环境变量**：
   ```python
   os.environ["MODELSCOPE_CACHE"] = str(model_dir)
   os.environ["MODELSCOPE_MODULES_CACHE"] = str(model_dir)
   ```

2. **加载后自动修复**：调用 `_fix_nested_models_directory()` 方法

3. **合并冲突处理**：如果目标目录已存在，自动合并文件而不是覆盖

## 常见问题

### Q1: 下载完成后还是报错找不到模型？

**A:** 等待几秒让自动修复完成，或手动运行修复脚本：
```bash
python scripts/fix_model_path.py
```

### Q2: 修复脚本报错说模型文件不完整？

**A:** 模型可能还在下载中，等待下载完成后再运行修复脚本。检查模型文件大小：
```bash
# Windows
Get-Item "data\models\models\iic\SenseVoiceSmall\model.pt" | Select-Object Length

# Linux/macOS
ls -lh data/models/models/iic/SenseVoiceSmall/model.pt
```

完整的 `model.pt` 应该约为 893 MB。

### Q3: 我已经有正确位置的模型，但又下载了一份到错误位置？

**A:** 运行修复脚本会自动合并文件，只复制缺失或不同的文件，不会造成重复。

### Q4: 可以删除嵌套的 models 目录吗？

**A:** 在确认正确位置（`data/models/iic/`）的模型完整后，可以安全删除 `data/models/models/` 目录。

## 技术细节

### ModelScope 版本差异

| ModelScope 版本 | 下载行为 | 是否需要修复 |
|----------------|---------|-------------|
| < 1.9.0 | 下载到 `$CACHE/models/iic/...` | ✅ 需要 |
| >= 1.9.0 | 下载到 `$CACHE/iic/...` | ❌ 不需要 |
| 不同环境 | 行为可能不一致 | ⚠️ 建议启用自动修复 |

### 自动修复触发时机

- **模型首次加载时**：`SenseVoiceProvider._load_model()` 方法会调用自动修复
- **启动服务时**：如果配置了预加载，会在启动时触发
- **任务执行时**：第一个转录任务会触发模型加载和自动修复

### 修复脚本逻辑

```python
1. 检测嵌套目录 data/models/models/iic/
2. 检查模型文件完整性（model.pt 大小 > 800MB）
3. 如果目标存在，合并文件（只复制缺失的）
4. 如果目标不存在，直接移动
5. 清理临时目录和空的嵌套目录
6. 验证最终结构的完整性
```

## 相关文件

- **自动修复逻辑**: `app/services/asr/sensevoice_provider.py`
- **手动修复脚本**: `scripts/fix_model_path.py`
- **详细文档**: `docs/model-path-fix.md`

## 更新日志

- **2024-XX-XX**: 添加自动修复机制
- **2024-XX-XX**: 增强修复逻辑，支持文件合并
- **2024-XX-XX**: 添加独立的修复脚本和验证功能
