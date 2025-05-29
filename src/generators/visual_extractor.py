"""
Visual content extraction system for papers and social media.
Extracts and processes figures, charts, and creates visual content for LinkedIn posts.
"""

import logging
import os
import asyncio
from typing import List, Dict, Optional, Tuple
from pathlib import Path
import tempfile
import hashlib
from datetime import datetime

try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False
    
try:
    from PIL import Image, ImageDraw, ImageFont
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

from src.models.base import get_db
from src.models.paper import Paper

logger = logging.getLogger(__name__)


class VisualExtractor:
    """Extracts and processes visual content for LinkedIn posts."""
    
    def __init__(self):
        self.output_dir = Path("generated_visuals")
        self.output_dir.mkdir(exist_ok=True)
        
        # LinkedIn image specifications
        self.linkedin_specs = {
            'max_width': 1200,
            'max_height': 1200,
            'min_width': 400,
            'min_height': 400,
            'formats': ['JPEG', 'PNG'],
            'max_file_size': 5 * 1024 * 1024  # 5MB
        }
        
        # Visual quality thresholds
        self.quality_thresholds = {
            'min_resolution': 400 * 400,
            'min_aspect_ratio': 0.5,
            'max_aspect_ratio': 2.0
        }
    
    def extract_paper_figures(self, paper: Paper) -> List[Dict]:
        """
        Extract figures from a paper PDF.
        
        Args:
            paper: Paper object with PDF information
            
        Returns:
            List of extracted figure information
        """
        if not PYMUPDF_AVAILABLE:
            logger.warning("PyMuPDF not available, cannot extract figures")
            return []
        
        if not paper.pdf_url:
            logger.warning(f"No PDF URL for paper {paper.arxiv_id}")
            return []
        
        try:
            # Download PDF if needed
            pdf_path = self._download_pdf(paper)
            if not pdf_path:
                return []
            
            # Extract figures
            figures = self._extract_figures_from_pdf(pdf_path, paper.arxiv_id)
            
            # Process and filter figures
            processed_figures = []
            for i, figure in enumerate(figures):
                processed = self._process_figure(figure, paper.arxiv_id, i)
                if processed and self._is_quality_figure(processed):
                    processed_figures.append(processed)
            
            logger.info(f"Extracted {len(processed_figures)} quality figures from {paper.arxiv_id}")
            return processed_figures
            
        except Exception as e:
            logger.error(f"Figure extraction failed for {paper.arxiv_id}: {e}")
            return []
    
    def _download_pdf(self, paper: Paper) -> Optional[Path]:
        """Download PDF from arXiv if not already cached."""
        # For now, assume PDFs are available or skip download
        # In a real implementation, would download from paper.pdf_url
        logger.debug(f"PDF download for {paper.arxiv_id} would happen here")
        return None
    
    def _extract_figures_from_pdf(self, pdf_path: Path, arxiv_id: str) -> List[Dict]:
        """Extract figure images from PDF using PyMuPDF."""
        figures = []
        
        try:
            doc = fitz.open(pdf_path)
            
            for page_num in range(min(len(doc), 20)):  # Limit to first 20 pages
                page = doc[page_num]
                
                # Get image list from page
                image_list = page.get_images()
                
                for img_index, img in enumerate(image_list):
                    try:
                        # Extract image
                        xref = img[0]
                        pix = fitz.Pixmap(doc, xref)
                        
                        # Skip small images (likely icons or decorations)
                        if pix.width < 100 or pix.height < 100:
                            pix = None
                            continue
                        
                        # Convert to PIL Image
                        if pix.n - pix.alpha < 4:  # GRAY or RGB
                            img_data = pix.tobytes("png")
                            
                            figures.append({
                                'data': img_data,
                                'page': page_num + 1,
                                'index': img_index,
                                'width': pix.width,
                                'height': pix.height,
                                'format': 'PNG'
                            })
                        
                        pix = None
                        
                    except Exception as e:
                        logger.warning(f"Error extracting image {img_index} from page {page_num}: {e}")
                        continue
            
            doc.close()
            
        except Exception as e:
            logger.error(f"PDF processing failed: {e}")
        
        return figures
    
    def _process_figure(self, figure: Dict, arxiv_id: str, index: int) -> Optional[Dict]:
        """Process and optimize a figure for LinkedIn."""
        if not PIL_AVAILABLE:
            return None
        
        try:
            # Load image
            image = Image.open(io.BytesIO(figure['data']))
            
            # Convert to RGB if needed
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Resize for LinkedIn
            image = self._resize_for_linkedin(image)
            
            # Add attribution watermark
            image = self._add_attribution(image, arxiv_id)
            
            # Save processed image
            filename = f"{arxiv_id}_fig_{index}_{datetime.now().strftime('%Y%m%d')}.jpg"
            output_path = self.output_dir / filename
            
            image.save(output_path, 'JPEG', quality=90, optimize=True)
            
            return {
                'path': str(output_path),
                'filename': filename,
                'width': image.width,
                'height': image.height,
                'page': figure['page'],
                'arxiv_id': arxiv_id,
                'caption': f"Figure from {arxiv_id} (Page {figure['page']})",
                'file_size': output_path.stat().st_size
            }
            
        except Exception as e:
            logger.error(f"Figure processing failed: {e}")
            return None
    
    def _resize_for_linkedin(self, image: Image.Image) -> Image.Image:
        """Resize image to fit LinkedIn specifications."""
        current_width, current_height = image.size
        
        # Calculate scaling factor
        scale_width = self.linkedin_specs['max_width'] / current_width
        scale_height = self.linkedin_specs['max_height'] / current_height
        scale = min(scale_width, scale_height, 1.0)  # Don't upscale
        
        if scale < 1.0:
            new_width = int(current_width * scale)
            new_height = int(current_height * scale)
            image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        return image
    
    def _add_attribution(self, image: Image.Image, arxiv_id: str) -> Image.Image:
        """Add subtle attribution watermark to image."""
        if not PIL_AVAILABLE:
            return image
        
        try:
            # Create a copy to modify
            watermarked = image.copy()
            draw = ImageDraw.Draw(watermarked)
            
            # Attribution text
            attribution_text = f"Source: arXiv:{arxiv_id} | via COAI Research"
            
            # Try to load a font, fallback to default
            try:
                font = ImageFont.truetype("arial.ttf", 16)
            except:
                font = ImageFont.load_default()
            
            # Position at bottom right
            text_bbox = draw.textbbox((0, 0), attribution_text, font=font)
            text_width = text_bbox[2] - text_bbox[0]
            text_height = text_bbox[3] - text_bbox[1]
            
            x = image.width - text_width - 10
            y = image.height - text_height - 10
            
            # Add semi-transparent background
            padding = 5
            bg_bbox = [
                x - padding,
                y - padding,
                x + text_width + padding,
                y + text_height + padding
            ]
            draw.rectangle(bg_bbox, fill=(255, 255, 255, 180))
            
            # Add text
            draw.text((x, y), attribution_text, fill=(50, 50, 50), font=font)
            
            return watermarked
            
        except Exception as e:
            logger.warning(f"Attribution watermark failed: {e}")
            return image
    
    def _is_quality_figure(self, figure: Dict) -> bool:
        """Check if figure meets quality standards."""
        # Resolution check
        total_pixels = figure['width'] * figure['height']
        if total_pixels < self.quality_thresholds['min_resolution']:
            return False
        
        # Aspect ratio check
        aspect_ratio = figure['width'] / figure['height']
        if (aspect_ratio < self.quality_thresholds['min_aspect_ratio'] or
            aspect_ratio > self.quality_thresholds['max_aspect_ratio']):
            return False
        
        # File size check
        if figure['file_size'] > self.linkedin_specs['max_file_size']:
            return False
        
        return True
    
    def create_quote_card(
        self,
        text: str,
        author: str = None,
        source: str = None,
        theme: str = 'professional'
    ) -> Optional[Dict]:
        """Create a quote card for social media sharing."""
        if not PIL_AVAILABLE:
            logger.warning("PIL not available, cannot create quote cards")
            return None
        
        try:
            # Card dimensions
            width, height = 1200, 800
            
            # Create image
            if theme == 'professional':
                bg_color = (45, 55, 72)  # Dark blue-gray
                text_color = (255, 255, 255)
                accent_color = (66, 153, 225)  # Blue
            else:
                bg_color = (255, 255, 255)
                text_color = (45, 55, 72)
                accent_color = (66, 153, 225)
            
            image = Image.new('RGB', (width, height), bg_color)
            draw = ImageDraw.Draw(image)
            
            # Fonts (with fallbacks)
            try:
                quote_font = ImageFont.truetype("arial.ttf", 32)
                author_font = ImageFont.truetype("arial.ttf", 24)
                source_font = ImageFont.truetype("arial.ttf", 18)
            except:
                quote_font = ImageFont.load_default()
                author_font = ImageFont.load_default()
                source_font = ImageFont.load_default()
            
            # Text wrapping
            wrapped_text = self._wrap_text(text, quote_font, width - 200)
            
            # Calculate text position
            text_height = len(wrapped_text) * 40
            start_y = (height - text_height) // 2 - 50
            
            # Draw quote text
            for i, line in enumerate(wrapped_text):
                line_width = draw.textlength(line, font=quote_font)
                x = (width - line_width) // 2
                y = start_y + i * 40
                draw.text((x, y), line, fill=text_color, font=quote_font)
            
            # Draw author
            if author:
                author_text = f"— {author}"
                author_width = draw.textlength(author_text, font=author_font)
                x = (width - author_width) // 2
                y = start_y + text_height + 30
                draw.text((x, y), author_text, fill=accent_color, font=author_font)
            
            # Draw source
            if source:
                source_text = f"Source: {source}"
                source_width = draw.textlength(source_text, font=source_font)
                x = (width - source_width) // 2
                y = height - 80
                draw.text((x, y), source_text, fill=text_color, font=source_font)
            
            # Add COAI branding
            coai_text = "COAI Research"
            coai_width = draw.textlength(coai_text, font=source_font)
            draw.text((width - coai_width - 30, 30), coai_text, fill=accent_color, font=source_font)
            
            # Save
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"quote_card_{timestamp}.jpg"
            output_path = self.output_dir / filename
            
            image.save(output_path, 'JPEG', quality=95, optimize=True)
            
            return {
                'path': str(output_path),
                'filename': filename,
                'width': width,
                'height': height,
                'type': 'quote_card',
                'theme': theme,
                'file_size': output_path.stat().st_size
            }
            
        except Exception as e:
            logger.error(f"Quote card creation failed: {e}")
            return None
    
    def _wrap_text(self, text: str, font, max_width: int) -> List[str]:
        """Wrap text to fit within specified width."""
        if not PIL_AVAILABLE:
            return [text]
        
        words = text.split()
        lines = []
        current_line = []
        
        for word in words:
            test_line = ' '.join(current_line + [word])
            # Use a temporary draw object for text measurement
            temp_img = Image.new('RGB', (1, 1))
            temp_draw = ImageDraw.Draw(temp_img)
            
            if temp_draw.textlength(test_line, font=font) <= max_width:
                current_line.append(word)
            else:
                if current_line:
                    lines.append(' '.join(current_line))
                    current_line = [word]
                else:
                    # Word is too long, force it on its own line
                    lines.append(word)
        
        if current_line:
            lines.append(' '.join(current_line))
        
        return lines
    
    def create_stats_visualization(
        self,
        data: Dict,
        title: str,
        chart_type: str = 'bar'
    ) -> Optional[Dict]:
        """Create a simple statistics visualization."""
        if not PIL_AVAILABLE:
            return None
        
        try:
            width, height = 1200, 800
            bg_color = (255, 255, 255)
            
            image = Image.new('RGB', (width, height), bg_color)
            draw = ImageDraw.Draw(image)
            
            # This would be a simplified chart
            # In practice, you'd use matplotlib or similar
            # For now, just create a placeholder
            
            draw.text((50, 50), title, fill=(50, 50, 50))
            draw.text((50, 100), "Chart visualization would go here", fill=(100, 100, 100))
            
            # Save
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"stats_{chart_type}_{timestamp}.jpg"
            output_path = self.output_dir / filename
            
            image.save(output_path, 'JPEG', quality=95)
            
            return {
                'path': str(output_path),
                'filename': filename,
                'width': width,
                'height': height,
                'type': 'stats_chart',
                'chart_type': chart_type
            }
            
        except Exception as e:
            logger.error(f"Stats visualization failed: {e}")
            return None
    
    def get_best_visual_for_content(
        self,
        content_type: str,
        source_data: Dict,
        text_content: str = None
    ) -> Optional[Dict]:
        """Get the best visual content for a given post."""
        
        if content_type == 'paper' and 'arxiv_id' in source_data:
            # Try to get paper from database
            with get_db() as db:
                paper = db.query(Paper).filter_by(
                    arxiv_id=source_data['arxiv_id']
                ).first()
                
                if paper:
                    figures = self.extract_paper_figures(paper)
                    if figures:
                        # Return the best figure (first one for now)
                        return figures[0]
        
        # Fallback: create a quote card
        if text_content:
            # Extract a good quote from the text
            quote = self._extract_quote_from_text(text_content)
            if quote:
                return self.create_quote_card(
                    text=quote,
                    source=source_data.get('title', 'Research'),
                    theme='professional'
                )
        
        return None
    
    def _extract_quote_from_text(self, text: str) -> Optional[str]:
        """Extract a quotable segment from post text."""
        # Simple extraction - take first sentence or key insight
        sentences = text.split('.')
        
        for sentence in sentences:
            sentence = sentence.strip()
            if (len(sentence) > 20 and len(sentence) < 200 and
                any(keyword in sentence.lower() for keyword in 
                    ['insight', 'key', 'important', 'shows', 'reveals', 'suggests'])):
                return sentence + '.'
        
        # Fallback: take first sentence if reasonable length
        if sentences and 20 <= len(sentences[0]) <= 200:
            return sentences[0] + '.'
        
        return None
    
    def cleanup_old_visuals(self, days: int = 30) -> int:
        """Clean up old generated visuals to save disk space."""
        cutoff_date = datetime.now().timestamp() - (days * 24 * 60 * 60)
        removed_count = 0
        
        try:
            for file_path in self.output_dir.glob("*"):
                if file_path.is_file() and file_path.stat().st_mtime < cutoff_date:
                    file_path.unlink()
                    removed_count += 1
            
            logger.info(f"Cleaned up {removed_count} old visual files")
            
        except Exception as e:
            logger.error(f"Visual cleanup failed: {e}")
        
        return removed_count


# Add missing import
import io