import os
import json
import re
import fitz  # PyMuPDF
from pathlib import Path
from collections import defaultdict
import statistics

class AdvancedPDFExtractor:
    """
    A significantly more robust PDF outline extractor that uses advanced heuristics 
    on text properties to identify a document's semantic structure.
    It intelligently filters headers/footers and analyzes font styles to deduce the outline.
    """
    def __init__(self):
        # Regex to find explicitly numbered headings (e.g., "1.", "2.1", "Appendix A")
        self.numbered_heading_pattern = re.compile(
            r'^\s*((\d+(\.\d+)*)|(appendix\s+[a-z])|(chapter\s+\d+))\s*[\s\.]', 
            re.IGNORECASE
        )
        self.min_heading_len = 3
        self.max_heading_len = 250

    def _identify_headers_and_footers(self, doc, header_margin=0.15, footer_margin=0.90, min_occurrences=0.5):
        """Identifies recurring text in the top and bottom margins of pages."""
        header_candidates = defaultdict(int)
        footer_candidates = defaultdict(int)
        num_pages = len(doc)
        
        if num_pages == 0:
            return set(), set()
            
        for page in doc:
            # --- CORRECTED LINE HERE ---
            page_height = page.rect.height
            # Check top 15% of the page for headers
            header_zone = fitz.Rect(0, 0, page.rect.width, page_height * header_margin)
            header_text = page.get_text(clip=header_zone, sort=True).strip()
            if header_text:
                header_candidates[header_text] += 1
                
            # Check bottom 10% of the page for footers (and page numbers)
            footer_zone = fitz.Rect(0, page_height * footer_margin, page.rect.width, page_height)
            footer_text = page.get_text(clip=footer_zone, sort=True).strip()
            if footer_text:
                # Normalize by removing digits to catch "Page 1", "Page 2", etc.
                normalized_footer = re.sub(r'\d+', '', footer_text).strip()
                if normalized_footer:
                    footer_candidates[normalized_footer] += 1

        # A header/footer is text that appears on at least half the pages.
        occurrence_threshold = max(2, num_pages * min_occurrences)
        headers = {text for text, count in header_candidates.items() if count >= occurrence_threshold}
        footers = {text for text, count in footer_candidates.items() if count >= occurrence_threshold}
        
        # Also add simple page numbers to the footer set to be ignored
        for page in doc:
             # --- CORRECTED LINE HERE ---
             footer_zone = fitz.Rect(0, page.rect.height * footer_margin, page.rect.width, page.rect.height)
             for block in page.get_text("blocks", clip=footer_zone):
                 text = block[4].strip()
                 if text.isdigit():
                     footers.add(text)

        return headers, footers

    def analyze_font_styles(self, doc):
        """Analyzes the document to find the body font size and potential heading font sizes."""
        font_counts = defaultdict(lambda: defaultdict(int)) # size -> weight -> count
        for page in doc:
            for block in page.get_text("dict").get("blocks", []):
                if block["type"] == 0:
                    for line in block.get("lines", []):
                        for span in line.get("spans", []):
                            font_size = round(span["size"])
                            is_bold = "bold" in span["font"].lower() or (span['flags'] & 2**4)
                            font_counts[font_size][is_bold] += len(span["text"].strip())
        
        if not font_counts:
            return 10.0, []

        # Find body font size (most common, non-bold font)
        body_font_size = 10.0
        max_chars = 0
        for size, weights in font_counts.items():
            if not weights.get(False): continue
            if weights[False] > max_chars:
                max_chars = weights[False]
                body_font_size = float(size)
        
        # Identify heading tiers: font sizes significantly larger than the body text.
        font_size_tiers = sorted([size for size in font_counts if size > body_font_size * 1.05], reverse=True)
        
        # Consolidate tiers that are very close to each other (e.g., 14.1 and 14.2)
        final_tiers = []
        if font_size_tiers:
            final_tiers.append(font_size_tiers[0])
            for size in font_size_tiers[1:]:
                if final_tiers[-1] > size * 1.1 and len(final_tiers) < 5:
                     final_tiers.append(size)

        return body_font_size, final_tiers

    def extract_title(self, doc, default_title):
        """Extracts the document title by finding the largest text on the first page."""
        if len(doc) == 0:
            return default_title
            
        first_page = doc[0]
        max_font_size = 0
        title_text = default_title
        
        blocks = first_page.get_text("dict", sort=True)["blocks"]
        # Look for the title in the top 40% of the page
        # --- CORRECTED LINE HERE ---
        for block in filter(lambda b: b['bbox'][1] < first_page.rect.height * 0.4, blocks):
            if block["type"] == 0:
                for line in block.get("lines", []):
                    # Combine text from all spans in the line
                    line_text = "".join(span["text"] for span in line["spans"]).strip()
                    if not line_text: continue

                    avg_size = statistics.mean(s["size"] for s in line["spans"])
                    if avg_size > max_font_size:
                        max_font_size = avg_size
                        title_text = line_text
        
        return title_text
        
    def is_heading(self, block, body_font_size, page_width, headers, footers):
        """Determines if a text block is a heading using a robust set of rules."""
        if block['type'] != 0 or "lines" not in block or not block["lines"]:
            return False

        full_text = " ".join("".join(s["text"] for s in l["spans"]) for l in block["lines"]).strip()
        
        # --- Stage 1: Filter out non-headings ---
        if not full_text or len(full_text) < self.min_heading_len or len(full_text) > self.max_heading_len:
            return False
            
        # Check against identified headers and footers
        if full_text in headers:
            return False
        normalized_text = re.sub(r'\d+', '', full_text).strip()
        if normalized_text in footers:
            return False
        if full_text.isdigit():
            return False
            
        # Filter out text that looks like a normal sentence or is too long.
        if full_text.endswith('.') and not full_text.isupper() and len(full_text.split()) > 15:
            return False

        # --- Stage 2: Gather properties ---
        spans = [s for l in block['lines'] for s in l['spans']]
        if not spans: return False
        
        avg_font_size = statistics.mean(s['size'] for s in spans)
        is_bold = any("bold" in s['font'].lower() or (s['flags'] & 2**4) for s in spans)
        
        # --- Stage 3: Apply Heuristics ---
        if self.numbered_heading_pattern.match(full_text):
            return True
        if avg_font_size > body_font_size * 1.15 and (is_bold or len(full_text.split()) < 15):
            return True

        return False
        
    def get_heading_level(self, size, font_size_tiers):
        """Assigns H1, H2, etc. based on font size tiers."""
        if not font_size_tiers: return "H2"
        level = len(font_size_tiers)
        for i, tier_size in enumerate(font_size_tiers):
            if size >= tier_size * 0.95:
                level = i + 1
                break
        return f"H{min(level, 3)}"

    def extract_outline(self, pdf_path):
        """Main function to extract a structured outline from a PDF."""
        try:
            doc = fitz.open(pdf_path)
            
            # Get the default title from the filename before analyzing the document
            default_title = Path(pdf_path).stem.replace("_", " ").title()
            
            headers, footers = self._identify_headers_and_footers(doc)
            body_font_size, font_size_tiers = self.analyze_font_styles(doc)
            # Pass the default title to the extraction function
            title = self.extract_title(doc, default_title)

            headings = []
            for page_num, page in enumerate(doc):
                blocks = page.get_text("dict", sort=True)["blocks"]
                for block in blocks:
                    if self.is_heading(block, body_font_size, page.rect.width, headers, footers):
                        text = " ".join("".join(s["text"] for s in l["spans"]) for l in block["lines"]).strip()
                        avg_font_size = statistics.mean(s['size'] for l in block['lines'] for s in l['spans'])
                        headings.append({"text": text, "page": page_num + 1, "size": avg_font_size, "y": block['bbox'][1]})
            
            # --- Post-processing ---
            headings.sort(key=lambda h: (h['page'], h['y']))
            seen = set()
            unique_headings = [h for h in headings if (h["text"], h["page"]) not in seen and not seen.add((h["text"], h["page"]))]
            
            outline = []
            for h in unique_headings:
                level = self.get_heading_level(h['size'], font_size_tiers)
                outline.append({"level": level, "text": h["text"], "page": h["page"]})

            return {"title": title, "outline": outline}
        except Exception as e:
            print(f"Error processing {pdf_path.name}: {e}")
            return {"title": f"Error processing {Path(pdf_path).name}", "outline": []}

def main():
    input_dir = Path("./app/input")
    output_dir = Path("./app/output")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    extractor = AdvancedPDFExtractor()

    pdf_files = list(input_dir.glob("*.pdf"))
    if not pdf_files:
        print(f"Error: No PDF files found in '{input_dir.resolve()}'. Please add some PDFs.")
        return

    for pdf_path in pdf_files:
        print(f"\n--- Processing {pdf_path.name} ---")
        result = extractor.extract_outline(pdf_path)
        
        output_file_name = f"{pdf_path.stem}.json"
        output_path = output_dir / output_file_name
        
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=4, ensure_ascii=False)
        print(f"Successfully saved outline to: {output_path}")

if __name__ == "__main__":
    main()
    print("\nExtraction process completed!")