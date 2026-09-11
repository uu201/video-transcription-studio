# 模型路径自动修复说明

## 问题背景

某些版本的 ModelScope 在下载模型时，会在 `MODELSCOPE_CACHE` 指定的目录下再创建一个 `models/` 子目录，导致模型路径变成：

```
data/models/models/iic/SenseVoiceSmall/...
```

而代码期望的路径是：

```
data/models/iic/SenseVoiceSmall/...
```

这会导致模型加载失败，报错：`Not found: "D:\\...\\data\\models\\models\\iic\\SenseVoiceSmall\\..."`

## 解决方案

系统现在会在模型加载后自动检测并修复这个问题：

### 自动修复机制

在 `app/services/asr/sensevoice_provider.py` 的 `_load_model()` 方法中：

1. **设置环境变量**：将 `MODELSCOPE_CACHE` 设置为 `data/models`
2. **加载模型**：使用 FunASR 的 `AutoModel` 加载模型
3. **自动修复**：调用 `_fix_nested_models_directory()` 检查并修复嵌套目录

### 修复逻辑

```python
def _fix_nested_models_directory(self) -> None:
    """修复 ModelScope 可能创建的嵌套 models 目录。"""
    nested_models_dir = self.settings.model_dir / "models"
    
    # 如果存在 data/models/models/iic/
    if (nested_models_dir / "iic").exists():
        # 移动到 data/models/iic/
        shutil.move(str(nested_models_dir / "iic"), str(self.settings.model_dir / "iic"))
        
        # 删除空的嵌套目录
        if not list(nested_models_dir.iterdir()):
            nested_models_dir.rmdir()
```

## 对用户的影响

### ✅ 优点

1. **自动化**：用户无需手动移动文件
2. **透明**：首次加载模型时自动修复，对用户透明
3. **兼容性**：兼容不同版本的 ModelScope
4. **日志记录**：修复过程会记录日志，便于排查问题

### ⚠️ 注意事项

1. **首次加载**：首次加载模型时可能会稍慢一些（需要移动文件）
2. **磁盘空间**：修复过程会暂时占用双倍磁盘空间（移动完成后释放）
3. **失败容错**：如果修复失败，系统会记录警告但不会中断服务

## 手动修复（如果需要）

如果自动修复失败，可以手动执行：

```powershell
# Windows PowerShell
Move-Item -Path "data\models\models\iic" -Destination "data\models\iic" -Force
Remove-Item "data\models\models" -Force
```

```bash
# Linux/macOS
mv data/models/models/iic data/models/iic
rmdir data/models/models
```

## 验证模型路径

运行以下命令验证模型位置：

```powershell
# Windows
Get-ChildItem "data\models\iic\SenseVoiceSmall" | Select-Object Name, Length
```

```bash
# Linux/macOS
ls -lh data/models/iic/SenseVoiceSmall/
```

正确的文件列表应包括：
- `model.pt` (约 893 MB)
- `chn_jpn_yue_eng_ko_spectok.bpe.model`
- `config.yaml`
- `configuration.json`
- `tokens.json`

## 相关配置

在 `config/app.yaml` 中：

```yaml
paths:
  model_dir: data/models  # 模型根目录
```

环境变量会自动设置为：
- `MODELSCOPE_CACHE=data/models`
- `HF_HOME=data/models/huggingface`

## 技术细节

### ModelScope 版本差异

不同版本的 ModelScope 行为不同：

| 版本范围 | 下载路径 | 是否需要修复 |
|---------|---------|-------------|
| < 1.9.0 | `$CACHE/models/iic/...` | ✅ 需要 |
| >= 1.9.0 | `$CACHE/iic/...` | ❌ 不需要 |

本系统的自动修复机制兼容所有版本。

### 其他模型

如果使用其他 ModelScope 模型（如 VAD、分离器等），也会受益于这个自动修复机制。

## 更新历史

- **2024-XX-XX**：添加自动修复机制
- **2024-XX-XX**：修复嵌套目录导致的模型加载失败问题
