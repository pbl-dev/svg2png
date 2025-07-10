import os
import sys
import argparse
import logging
from pathlib import Path
from typing import List, Optional
from datetime import datetime

try:
    import cairosvg
except ImportError:
    print("Error: cairosvg is required but not installed.")
    print("Please install it with: pip install cairosvg")
    sys.exit(1)


class SVGToPNGConverter:
    def __init__(self, input_dir: str, output_dir: str, sizes: Optional[List[int]] = None, 
                 log_level: str = 'INFO'):
        self.input_dir = Path(input_dir)
        self.output_dir = Path(output_dir)
        self.sizes = sizes or [1024, 256, 128]
        
        self.setup_logging(log_level)
        
        self.stats = {
            'total_files': 0,
            'svg_files': 0,
            'converted': 0,
            'skipped': 0,
            'errors': 0,
            'png_files_created': 0
        }
        
    def setup_logging(self, log_level: str):
        log_format = '%(asctime)s - %(levelname)s - %(message)s'
        
        for handler in logging.root.handlers[:]:
            logging.root.removeHandler(handler)
        
        logging.basicConfig(
            level=getattr(logging, log_level.upper()),
            format=log_format,
            handlers=[logging.StreamHandler(sys.stdout)]
        )
            
        self.logger = logging.getLogger(__name__)
    
    def convert_svg_to_png(self, svg_path: Path, png_path: Path, size: int) -> bool:
        try:
            cairosvg.svg2png(
                url=str(svg_path),
                write_to=str(png_path),
                output_width=size,
                output_height=size
            )
            return True
        except Exception as e:
            self.logger.error(f"cairosvg conversion failed for {svg_path} (size {size}): {e}")
            return False
    
    def find_svg_files(self) -> List[Path]:
        svg_files = []
        
        for root, dirs, files in os.walk(self.input_dir):
            for file in files:
                file_path = Path(root) / file
                self.stats['total_files'] += 1
                
                if file.lower().endswith('.svg'):
                    svg_files.append(file_path)
                    self.stats['svg_files'] += 1
                else:
                    self.logger.debug(f"Skipping non-SVG file: {file_path}")
                    self.stats['skipped'] += 1
        
        return svg_files
    
    def convert_files(self):
        self.logger.info(f"Starting conversion from {self.input_dir} to {self.output_dir}")
        self.logger.info(f"Output sizes: {', '.join(map(str, self.sizes))}px")
        
        if not self.input_dir.exists():
            raise FileNotFoundError(f"Input directory does not exist: {self.input_dir}")
        
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        svg_files = self.find_svg_files()
        
        if not svg_files:
            self.logger.warning("No SVG files found in the input directory")
            return
        
        self.logger.info(f"Found {len(svg_files)} SVG files to convert")
        
        for svg_path in svg_files:
            try:
                rel_path = svg_path.relative_to(self.input_dir)
                
                base_name = rel_path.stem
                rel_dir = rel_path.parent
                
                file_converted = False
                file_errors = 0
                
                for size in self.sizes:
                    png_filename = f"{base_name}_{size}x{size}.png"
                    png_path = self.output_dir / rel_dir / png_filename
                    
                    png_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    if png_path.exists() and png_path.stat().st_mtime > svg_path.stat().st_mtime:
                        self.logger.debug(f"Skipping {svg_path} ({size}x{size}) - PNG is up to date")
                        continue
                    
                    self.logger.info(f"Converting: {svg_path} -> {png_path}")
                    
                    if self.convert_svg_to_png(svg_path, png_path, size):
                        self.stats['png_files_created'] += 1
                        file_converted = True
                        self.logger.debug(f"Successfully converted: {svg_path} ({size}x{size})")
                    else:
                        file_errors += 1
                
                if file_converted:
                    self.stats['converted'] += 1
                if file_errors == len(self.sizes):
                    self.stats['errors'] += 1
                    
            except Exception as e:
                self.logger.error(f"Error processing {svg_path}: {e}")
                self.stats['errors'] += 1
    
    def print_summary(self):
        self.logger.info("\n" + "="*60)
        self.logger.info("CONVERSION SUMMARY")
        self.logger.info("="*60)
        self.logger.info(f"Total files processed: {self.stats['total_files']}")
        self.logger.info(f"SVG files found: {self.stats['svg_files']}")
        self.logger.info(f"SVG files converted: {self.stats['converted']}")
        self.logger.info(f"PNG files created: {self.stats['png_files_created']}")
        self.logger.info(f"Non-SVG files skipped: {self.stats['skipped']}")
        self.logger.info(f"Errors: {self.stats['errors']}")
        self.logger.info(f"Output sizes: {', '.join(map(str, self.sizes))}px")
        self.logger.info("="*60)


def main():
    parser = argparse.ArgumentParser(
        description='Convert SVG files to PNG format in multiple sizes using cairosvg',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=r"""
Examples:
  %(prog)s "C:\Input\SVG Files" "C:\Output\PNG Files"
  %(prog)s input_dir output_dir --sizes 1024 256 128
  %(prog)s input_dir output_dir --log-level DEBUG
  
Default sizes: 1024x1024, 256x256, 128x128
  
Installation:
  pip install cairosvg
        """
    )
    
    parser.add_argument('input_dir', help='Input directory containing SVG files')
    parser.add_argument('output_dir', help='Output directory for PNG files')
    parser.add_argument('--sizes', nargs='+', type=int, default=[1024, 256, 128],
                        help='PNG output sizes in pixels (default: 1024 256 128)')
    parser.add_argument('--log-level', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'], 
                        default='INFO', help='Logging level (default: INFO)')
    
    args = parser.parse_args()
    
    for size in args.sizes:
        if size < 1 or size > 4096:
            print(f"Error: Size {size} is out of valid range (1-4096)")
            sys.exit(1)
    
    try:
        converter = SVGToPNGConverter(
            input_dir=args.input_dir,
            output_dir=args.output_dir,
            sizes=args.sizes,
            log_level=args.log_level
        )
        
        start_time = datetime.now()
        converter.convert_files()
        end_time = datetime.now()
        
        converter.print_summary()
        converter.logger.info(f"Total time: {end_time - start_time}")
        
    except Exception as e:
        logging.error(f"Conversion failed: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()