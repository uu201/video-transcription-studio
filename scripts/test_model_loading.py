#!/usr/bin/env python3
"""测试模型加载逻辑"""

import os
import sys
from pathlib import Path

# 添加项目路径
project_dir = Path(__file__).parent.parent
sys.path.insert(0, str(project_dir))

from app.config import load_settings


def test_model_path_logic():
    """测试模型路径逻辑"""
    settings = load_settings()

    print("=" * 60)
    print("模型路径配置")
    print("=" * 60)
    print(f"模型根目录: {settings.model_dir}")
    print(f"模型 ID: {settings.asr_model}")
    print()

    # 检查本地模型路径
    local_model_path = settings.model_dir / "iic" / "SenseVoiceSmall"
    model_file = local_model_path / "model.pt"

    print("=" * 60)
    print("本地模型检查")
    print("=" * 60)
    print(f"本地路径: {local_model_path}")
    print(f"目录存在: {'✓' if local_model_path.exists() else '✗'}")
    print(f"模型文件存在: {'✓' if model_file.exists() else '✗'}")

    if model_file.exists():
        size_mb = model_file.stat().st_size / (1024 * 1024)
        print(f"模型文件大小: {size_mb:.2f} MB")
        print()

        # 检查其他必需文件
        required_files = [
            "chn_jpn_yue_eng_ko_spectok.bpe.model",
            "config.yaml",
            "configuration.json",
            "tokens.json"
        ]

        print("必需文件检查:")
        all_exists = True
        for filename in required_files:
            file_path = local_model_path / filename
            exists = file_path.exists()
            print(f"  {'✓' if exists else '✗'} {filename}")
            if not exists:
                all_exists = False

        print()
        if all_exists:
            print("✓ 本地模型完整，将直接使用本地路径加载")
            print(f"  模型路径: {local_model_path}")
            print("  不会重新下载！")
        else:
            print("✗ 本地模型不完整，可能需要重新下载")
    else:
        print()
        print("⚠️  本地模型不存在，将从 ModelScope 下载")
        print(f"  模型 ID: {settings.asr_model}")

    print()
    print("=" * 60)
    print("环境变量设置")
    print("=" * 60)
    print(f"MODELSCOPE_CACHE: {os.getenv('MODELSCOPE_CACHE', '未设置')}")
    print(f"MODELSCOPE_MODULES_CACHE: {os.getenv('MODELSCOPE_MODULES_CACHE', '未设置')}")
    print(f"HF_HOME: {os.getenv('HF_HOME', '未设置')}")
    print()

    print("启动时将设置:")
    print(f"  MODELSCOPE_CACHE={settings.model_dir}")
    print(f"  MODELSCOPE_MODULES_CACHE={settings.model_dir}")
    print(f"  HF_HOME={settings.model_dir / 'huggingface'}")


if __name__ == "__main__":
    test_model_path_logic()
