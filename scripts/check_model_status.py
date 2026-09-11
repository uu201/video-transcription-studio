#!/usr/bin/env python3
"""模型下载状态检查工具"""

import sys
from pathlib import Path


def format_size(bytes_size: int) -> str:
    """格式化文件大小"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_size < 1024.0:
            return f"{bytes_size:.2f} {unit}"
        bytes_size /= 1024.0
    return f"{bytes_size:.2f} TB"


def check_download_status(model_dir: Path):
    """检查模型下载状态"""
    print(f"检查模型目录: {model_dir}\n")

    # 检查正确位置的模型
    correct_model_dir = model_dir / "iic" / "SenseVoiceSmall"
    nested_model_dir = model_dir / "models" / "iic" / "SenseVoiceSmall"
    temp_dir = model_dir / "models" / "._____temp"

    print("=" * 60)
    print("位置 1: 正确位置 (data/models/iic/SenseVoiceSmall/)")
    print("=" * 60)

    if correct_model_dir.exists():
        model_file = correct_model_dir / "model.pt"
        if model_file.exists():
            size = model_file.stat().st_size
            print(f"✓ model.pt: {format_size(size)}")
            if size >= 890 * 1024 * 1024:
                print("  状态: 完整 ✓")
            else:
                print(f"  状态: 不完整 (期望 ~893 MB)")
        else:
            print("✗ model.pt 不存在")

        # 检查其他必需文件
        required_files = [
            "chn_jpn_yue_eng_ko_spectok.bpe.model",
            "config.yaml",
            "configuration.json",
            "tokens.json"
        ]

        for filename in required_files:
            file_path = correct_model_dir / filename
            if file_path.exists():
                size = file_path.stat().st_size
                print(f"✓ {filename}: {format_size(size)}")
            else:
                print(f"✗ {filename}: 不存在")
    else:
        print("✗ 目录不存在")

    print("\n" + "=" * 60)
    print("位置 2: 嵌套位置 (data/models/models/iic/SenseVoiceSmall/)")
    print("=" * 60)

    if nested_model_dir.exists():
        print("⚠️  检测到嵌套模型目录（需要修复）")
        model_file = nested_model_dir / "model.pt"
        if model_file.exists():
            size = model_file.stat().st_size
            print(f"✓ model.pt: {format_size(size)}")
            if size >= 890 * 1024 * 1024:
                print("  状态: 完整 ✓")
                print("\n💡 模型已下载完成，运行以下命令修复路径:")
                print("   python scripts/fix_model_path.py")
            else:
                percentage = (size / (893 * 1024 * 1024)) * 100
                print(f"  状态: 下载中... {percentage:.1f}%")
        else:
            print("✗ model.pt 不存在")
    else:
        print("✓ 不存在（正常）")

    print("\n" + "=" * 60)
    print("临时下载目录")
    print("=" * 60)

    if temp_dir.exists():
        print("⏳ 检测到临时下载目录（模型正在下载中）")
        temp_files = list(temp_dir.rglob("*"))
        if temp_files:
            print(f"   临时文件数: {len([f for f in temp_files if f.is_file()])}")
    else:
        print("✓ 不存在（正常）")

    print("\n" + "=" * 60)
    print("建议")
    print("=" * 60)

    # 给出建议
    if correct_model_dir.exists():
        model_file = correct_model_dir / "model.pt"
        if model_file.exists() and model_file.stat().st_size >= 890 * 1024 * 1024:
            print("✓ 模型已就绪，可以正常使用")
            if nested_model_dir.exists():
                print("⚠️  但存在嵌套目录，建议运行修复脚本清理:")
                print("   python scripts/fix_model_path.py")
        else:
            print("⚠️  正确位置的模型不完整，可能需要重新下载")
    elif nested_model_dir.exists():
        model_file = nested_model_dir / "model.pt"
        if model_file.exists():
            size = model_file.stat().st_size
            if size >= 890 * 1024 * 1024:
                print("✓ 嵌套位置的模型已完整，运行修复脚本:")
                print("   python scripts/fix_model_path.py")
            else:
                percentage = (size / (893 * 1024 * 1024)) * 100
                print(f"⏳ 模型正在下载中... {percentage:.1f}%")
                print("   请等待下载完成后运行修复脚本")
        else:
            print("⏳ 模型正在下载中，请稍候...")
    elif temp_dir.exists():
        print("⏳ 模型正在下载中，请稍候...")
    else:
        print("✗ 未找到模型文件，需要首次下载")
        print("   启动应用并创建一个转录任务将自动下载模型")


def main():
    """主函数"""
    script_dir = Path(__file__).parent
    project_dir = script_dir.parent
    model_dir = project_dir / "data" / "models"

    if not model_dir.exists():
        print(f"✗ 模型目录不存在: {model_dir}")
        sys.exit(1)

    check_download_status(model_dir)


if __name__ == "__main__":
    main()
