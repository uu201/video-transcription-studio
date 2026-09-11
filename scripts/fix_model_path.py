#!/usr/bin/env python3
"""模型路径修复工具

用于修复 ModelScope 下载时创建的嵌套 models 目录问题。
"""

import logging
import shutil
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def fix_nested_models_directory(model_dir: Path) -> bool:
    """修复嵌套的 models 目录。

    Args:
        model_dir: 模型根目录（如 data/models）

    Returns:
        是否进行了修复操作
    """
    nested_models_dir = model_dir / "models"
    if not nested_models_dir.exists():
        logger.info("未发现嵌套的 models 目录")
        return False

    nested_iic_dir = nested_models_dir / "iic"
    target_iic_dir = model_dir / "iic"

    if not nested_iic_dir.exists():
        logger.info("嵌套目录中没有 iic 文件夹")
        # 检查临时目录
        temp_dir = nested_models_dir / "._____temp"
        if temp_dir.exists():
            logger.warning("检测到临时下载目录，模型可能还在下载中")
        return False

    # 检查模型文件是否完整
    nested_model_file = nested_iic_dir / "SenseVoiceSmall" / "model.pt"
    if nested_model_file.exists():
        size_mb = nested_model_file.stat().st_size / (1024 * 1024)
        logger.info(f"发现嵌套模型文件，大小: {size_mb:.2f} MB")
        if size_mb < 800:
            logger.warning("模型文件可能未下载完成，跳过修复")
            return False

    # 开始修复
    if target_iic_dir.exists():
        logger.info("目标目录已存在，进行合并...")
        # 遍历嵌套目录中的所有内容
        for item in nested_iic_dir.rglob("*"):
            if item.is_file():
                relative_path = item.relative_to(nested_iic_dir)
                target_path = target_iic_dir / relative_path

                # 如果目标文件不存在或大小不同，则复制
                if not target_path.exists() or target_path.stat().st_size != item.stat().st_size:
                    target_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(str(item), str(target_path))
                    logger.info(f"已复制: {relative_path}")

        # 删除嵌套目录
        shutil.rmtree(str(nested_iic_dir))
        logger.info(f"已删除嵌套目录: {nested_iic_dir}")
    else:
        logger.info(f"移动模型目录: {nested_iic_dir} -> {target_iic_dir}")
        shutil.move(str(nested_iic_dir), str(target_iic_dir))

    # 清理临时目录
    temp_dir = nested_models_dir / "._____temp"
    if temp_dir.exists():
        try:
            shutil.rmtree(str(temp_dir))
            logger.info(f"已删除临时目录: {temp_dir}")
        except PermissionError as e:
            logger.warning(f"无法删除临时目录（文件被占用）: {e}")
            logger.info("临时目录将在下次修复时自动清理")
        except Exception as e:
            logger.warning(f"删除临时目录失败: {e}")

    # 删除空的 models 目录
    if nested_models_dir.exists():
        try:
            remaining = list(nested_models_dir.iterdir())
            if not remaining:
                nested_models_dir.rmdir()
                logger.info(f"已删除空的嵌套目录: {nested_models_dir}")
            else:
                logger.info(f"嵌套目录还有其他内容: {[item.name for item in remaining]}")
        except Exception as e:
            logger.warning(f"清理嵌套目录失败: {e}")

    return True


def verify_model_structure(model_dir: Path) -> bool:
    """验证模型目录结构是否正确。

    Args:
        model_dir: 模型根目录

    Returns:
        模型结构是否正确
    """
    iic_dir = model_dir / "iic" / "SenseVoiceSmall"
    if not iic_dir.exists():
        logger.error(f"模型目录不存在: {iic_dir}")
        return False

    model_file = iic_dir / "model.pt"
    if not model_file.exists():
        logger.error(f"模型文件不存在: {model_file}")
        return False

    size_mb = model_file.stat().st_size / (1024 * 1024)
    logger.info(f"模型文件大小: {size_mb:.2f} MB")

    required_files = [
        "chn_jpn_yue_eng_ko_spectok.bpe.model",
        "config.yaml",
        "configuration.json",
        "tokens.json"
    ]

    for filename in required_files:
        file_path = iic_dir / filename
        if not file_path.exists():
            logger.warning(f"缺少配置文件: {filename}")
            return False

    logger.info("✓ 模型结构验证通过")
    return True


def main():
    """主函数"""
    # 确定项目根目录
    script_dir = Path(__file__).parent
    project_dir = script_dir.parent
    model_dir = project_dir / "data" / "models"

    if not model_dir.exists():
        logger.error(f"模型目录不存在: {model_dir}")
        sys.exit(1)

    logger.info(f"模型目录: {model_dir}")

    # 执行修复
    fixed = fix_nested_models_directory(model_dir)
    if fixed:
        logger.info("✓ 模型路径修复完成")
    else:
        logger.info("未检测到需要修复的问题")

    # 验证模型结构
    logger.info("\n验证模型结构...")
    if verify_model_structure(model_dir):
        logger.info("✓ 所有检查通过，模型可以正常使用")
        sys.exit(0)
    else:
        logger.error("✗ 模型结构验证失败")
        sys.exit(1)


if __name__ == "__main__":
    main()
