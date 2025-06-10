#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
图片格式转换工具

支持常见图片格式之间的转换：
- JPEG/JPG
- PNG
- BMP
- TIFF
- GIF
- WEBP
- ICO

使用方法:
    python Image_format_conversion.py input.jpg output.png
    python Image_format_conversion.py --batch input_folder output_folder --format png
"""

import os
import sys
from pathlib import Path
from typing import List, Optional
import click
from PIL import Image, ImageOps
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 支持的图片格式
SUPPORTED_FORMATS = {
    '.jpg': 'JPEG',
    '.jpeg': 'JPEG', 
    '.png': 'PNG',
    '.bmp': 'BMP',
    '.tiff': 'TIFF',
    '.tif': 'TIFF',
    '.gif': 'GIF',
    '.webp': 'WEBP',
    '.ico': 'ICO'
}

class ImageConverter:
    """图片格式转换器"""
    
    def __init__(self, quality: int = 95, optimize: bool = True):
        """
        初始化转换器
        
        Args:
            quality: JPEG质量 (1-100)
            optimize: 是否优化文件大小
        """
        self.quality = max(1, min(100, quality))
        self.optimize = optimize
        logger.info(f"初始化图片转换器 - 质量: {self.quality}, 优化: {self.optimize}")
    
    def is_supported_format(self, file_path: str) -> bool:
        """检查文件格式是否支持"""
        ext = Path(file_path).suffix.lower()
        return ext in SUPPORTED_FORMATS
    
    def get_output_format(self, output_path: str) -> str:
        """根据输出文件扩展名获取PIL格式"""
        ext = Path(output_path).suffix.lower()
        return SUPPORTED_FORMATS.get(ext, 'JPEG')
    
    def convert_single_image(self, input_path: str, output_path: str, 
                           resize: Optional[tuple] = None, 
                           maintain_aspect: bool = True) -> bool:
        """
        转换单个图片
        
        Args:
            input_path: 输入文件路径
            output_path: 输出文件路径
            resize: 调整大小 (width, height)
            maintain_aspect: 是否保持宽高比
            
        Returns:
            bool: 转换是否成功
        """
        try:
            if not os.path.exists(input_path):
                logger.error(f"输入文件不存在: {input_path}")
                return False
            
            if not self.is_supported_format(input_path):
                logger.error(f"不支持的输入格式: {input_path}")
                return False
            
            # 创建输出目录
            output_dir = Path(output_path).parent
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # 打开图片
            with Image.open(input_path) as img:
                # 转换RGBA为RGB（如果输出格式不支持透明度）
                output_format = self.get_output_format(output_path)
                if output_format in ['JPEG', 'BMP'] and img.mode in ['RGBA', 'LA']:
                    # 创建白色背景
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    if img.mode == 'RGBA':
                        background.paste(img, mask=img.split()[-1])  # 使用alpha通道作为mask
                    else:
                        background.paste(img)
                    img = background
                
                # 调整大小
                if resize:
                    if maintain_aspect:
                        img = ImageOps.fit(img, resize, Image.Resampling.LANCZOS)
                    else:
                        img = img.resize(resize, Image.Resampling.LANCZOS)
                
                # 保存参数
                save_kwargs = {'optimize': self.optimize}
                
                # 根据格式设置特定参数
                if output_format == 'JPEG':
                    save_kwargs['quality'] = self.quality
                    save_kwargs['progressive'] = True
                elif output_format == 'PNG':
                    save_kwargs['compress_level'] = 6
                elif output_format == 'WEBP':
                    save_kwargs['quality'] = self.quality
                    save_kwargs['method'] = 6
                
                # 保存图片
                img.save(output_path, format=output_format, **save_kwargs)
                
                logger.info(f"转换成功: {input_path} -> {output_path}")
                return True
                
        except Exception as e:
            logger.error(f"转换失败 {input_path}: {str(e)}")
            return False
    
    def batch_convert(self, input_dir: str, output_dir: str, 
                     target_format: str, recursive: bool = False) -> dict:
        """
        批量转换图片
        
        Args:
            input_dir: 输入目录
            output_dir: 输出目录
            target_format: 目标格式 (如: 'png', 'jpg')
            recursive: 是否递归处理子目录
            
        Returns:
            dict: 转换结果统计
        """
        if not os.path.exists(input_dir):
            logger.error(f"输入目录不存在: {input_dir}")
            return {'success': 0, 'failed': 0, 'skipped': 0}
        
        # 确保目标格式有效
        target_ext = f".{target_format.lower()}"
        if target_ext not in SUPPORTED_FORMATS:
            logger.error(f"不支持的目标格式: {target_format}")
            return {'success': 0, 'failed': 0, 'skipped': 0}
        
        input_path = Path(input_dir)
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        stats = {'success': 0, 'failed': 0, 'skipped': 0}
        
        # 获取所有图片文件
        pattern = "**/*" if recursive else "*"
        for file_path in input_path.glob(pattern):
            if file_path.is_file() and self.is_supported_format(str(file_path)):
                # 构建输出路径
                relative_path = file_path.relative_to(input_path)
                output_file = output_path / relative_path.with_suffix(target_ext)
                
                # 如果输出文件已存在且格式相同，跳过
                if output_file.exists() and file_path.suffix.lower() == target_ext:
                    logger.info(f"跳过 (已存在): {file_path}")
                    stats['skipped'] += 1
                    continue
                
                # 转换图片
                if self.convert_single_image(str(file_path), str(output_file)):
                    stats['success'] += 1
                else:
                    stats['failed'] += 1
        
        logger.info(f"批量转换完成 - 成功: {stats['success']}, "
                   f"失败: {stats['failed']}, 跳过: {stats['skipped']}")
        return stats

@click.command()
@click.argument('input_path', type=click.Path(exists=True))
@click.argument('output_path', type=click.Path(), required=False)
@click.option('--batch', '-b', is_flag=True, help='批量转换模式')
@click.option('--format', '-f', 'target_format', default='png', 
              help='目标格式 (png, jpg, bmp, tiff, gif, webp, ico)')
@click.option('--quality', '-q', default=95, type=click.IntRange(1, 100),
              help='JPEG/WEBP质量 (1-100)')
@click.option('--resize', '-r', help='调整大小 (如: 800x600)')
@click.option('--recursive', is_flag=True, help='递归处理子目录')
@click.option('--no-optimize', is_flag=True, help='禁用文件大小优化')
@click.option('--maintain-aspect/--no-maintain-aspect', default=True,
              help='是否保持宽高比')
def main(input_path, output_path, batch, target_format, quality, resize, 
         recursive, no_optimize, maintain_aspect):
    """
    图片格式转换工具
    
    单文件转换:
        python Image_format_conversion.py input.jpg output.png
    
    批量转换:
        python Image_format_conversion.py --batch input_folder output_folder --format png
    """
    
    # 解析调整大小参数
    resize_tuple = None
    if resize:
        try:
            width, height = map(int, resize.lower().split('x'))
            resize_tuple = (width, height)
        except ValueError:
            click.echo(f"错误: 无效的尺寸格式 '{resize}'. 使用格式: 800x600", err=True)
            return
    
    # 初始化转换器
    converter = ImageConverter(quality=quality, optimize=not no_optimize)
    
    if batch:
        # 批量转换模式
        if not output_path:
            output_path = f"{input_path}_converted"
        
        click.echo(f"开始批量转换...")
        click.echo(f"输入目录: {input_path}")
        click.echo(f"输出目录: {output_path}")
        click.echo(f"目标格式: {target_format.upper()}")
        
        stats = converter.batch_convert(
            input_path, output_path, target_format, recursive
        )
        
        click.echo(f"\n转换完成!")
        click.echo(f"成功: {stats['success']} 个文件")
        click.echo(f"失败: {stats['failed']} 个文件")
        click.echo(f"跳过: {stats['skipped']} 个文件")
        
    else:
        # 单文件转换模式
        if not output_path:
            # 自动生成输出文件名
            input_file = Path(input_path)
            output_path = str(input_file.with_suffix(f'.{target_format}'))
        
        click.echo(f"转换文件: {input_path} -> {output_path}")
        
        success = converter.convert_single_image(
            input_path, output_path, resize_tuple, maintain_aspect
        )
        
        if success:
            click.echo("✓ 转换成功!")
            # 显示文件大小信息
            input_size = os.path.getsize(input_path)
            output_size = os.path.getsize(output_path)
            click.echo(f"原文件大小: {input_size / 1024:.1f} KB")
            click.echo(f"转换后大小: {output_size / 1024:.1f} KB")
            click.echo(f"压缩比: {(1 - output_size/input_size) * 100:.1f}%")
        else:
            click.echo("✗ 转换失败!", err=True)
            sys.exit(1)

if __name__ == '__main__':
    main()
