import os
import json
from datetime import datetime
import shutil
import pdfplumber
import xml.etree.ElementTree as ET
from typing import Dict, List
import re

class DocumentProcessor:
    def __init__(self):
        self.received_folder = "received"
        self.parsed_folder = "parsed"
        self.completed_folder = "completed"
        
        # Create folders if they don't exist
        for folder in [self.received_folder, self.parsed_folder, self.completed_folder]:
            if not os.path.exists(folder):
                os.makedirs(folder)

    def detect_element_type(self, text: str, chars: Dict) -> str:
        """
        Detect the type of text element based on various characteristics
        """
        # Check if text is empty or whitespace
        if not text or text.isspace():
            return "empty"

        # Check for heading patterns
        heading_patterns = [
            r"^(?:CHAPTER|Section)\s+\d+",  # Chapter or Section followed by number
            r"^\d+\.\d*\s+[A-Z]",           # Numbered sections like "1.2 TITLE"
            r"^[IVXLC]+\.",                 # Roman numerals
        ]
        
        for pattern in heading_patterns:
            if re.match(pattern, text):
                return "heading"

        # Check text characteristics from chars dictionary
        if chars:
            # If text is significantly larger than average text
            if chars.get('size', 0) > chars.get('avg_size', 0) * 1.2:
                return "heading"
            # If text is bold
            if chars.get('fontname', '').lower().find('bold') != -1:
                return "subheading"

        # Check for list items
        if re.match(r'^\s*[•\-\d]+[\.\)]\s', text):
            return "list_item"

        return "paragraph"

    def create_xml_content(self, page_data: List[Dict]) -> str:
        """Convert extracted text content to XML format with enhanced structure detection"""
        root = ET.Element("content")
        current_section = None
        
        for text_obj in page_data:
            text = text_obj['text'].strip()
            chars = text_obj.get('chars', {})
            
            element_type = self.detect_element_type(text, chars)
            
            if element_type == "empty":
                continue
            elif element_type == "heading":
                heading = ET.SubElement(root, "heading")
                heading.text = text
                # Create a new section after each heading
                current_section = ET.SubElement(root, "section")
            elif element_type == "subheading":
                if current_section is None:
                    current_section = ET.SubElement(root, "section")
                subheading = ET.SubElement(current_section, "subheading")
                subheading.text = text
            elif element_type == "list_item":
                if current_section is None:
                    current_section = ET.SubElement(root, "section")
                list_item = ET.SubElement(current_section, "list_item")
                list_item.text = text
            else:  # paragraph
                if current_section is None:
                    current_section = ET.SubElement(root, "section")
                paragraph = ET.SubElement(current_section, "paragraph")
                paragraph.text = text
                
                # Add metadata if available
                if chars:
                    if 'fontname' in chars:
                        paragraph.set('font', chars['fontname'])
                    if 'size' in chars:
                        paragraph.set('size', str(chars['size']))
                
        return ET.tostring(root, encoding='unicode', method='xml')

    def extract_page_data(self, page) -> List[Dict]:
        """Extract text and its properties from a page"""
        page_data = []
        
        # Extract text with layout preservation
        words = page.extract_words(
            keep_blank_chars=True,
            x_tolerance=3,
            y_tolerance=3,
            extra_attrs=['size', 'fontname', 'top']
        )
        
        # Group words into lines based on vertical position
        current_line = []
        current_top = None
        
        for word in words:
            if current_top is None:
                current_top = word['top']
            
            # If word is on a new line (with small tolerance)
            if abs(word['top'] - current_top) > 3:
                if current_line:
                    # Process the completed line
                    line_text = ' '.join(w['text'] for w in current_line)
                    chars = {
                        'size': sum(w.get('size', 0) for w in current_line) / len(current_line),
                        'fontname': current_line[0].get('fontname', ''),
                        'avg_size': sum(w.get('size', 0) for w in words) / len(words)
                    }
                    page_data.append({'text': line_text, 'chars': chars})
                
                current_line = [word]
                current_top = word['top']
            else:
                current_line.append(word)
        
        # Process the last line
        if current_line:
            line_text = ' '.join(w['text'] for w in current_line)
            chars = {
                'size': sum(w.get('size', 0) for w in current_line) / len(current_line),
                'fontname': current_line[0].get('fontname', ''),
                'avg_size': sum(w.get('size', 0) for w in words) / len(words)
            }
            page_data.append({'text': line_text, 'chars': chars})
        
        return page_data

    def process_document(self, filename: str) -> Dict:
        """Process a single PDF document and return its JSON representation"""
        file_path = os.path.join(self.received_folder, filename)
        
        with pdfplumber.open(file_path) as pdf:
            pages_dict = {}
            
            for page_num, page in enumerate(pdf.pages, 1):
                # Extract page data with enhanced information
                page_data = self.extract_page_data(page)
                
                # Convert to XML with structure
                xml_content = self.create_xml_content(page_data)
                
                # Store page information
                pages_dict[str(page_num)] = {
                    "page_number": str(page_num),
                    "page_content": xml_content,
                    "metadata": {
                        "width": page.width,
                        "height": page.height,
                        "page_number": page_num,
                        "rotation": page.rotation or 0
                    }
                }
        
        return {
            "document_name": filename,
            "uploaded_on": datetime.now().isoformat(),
            "text": pages_dict,
            "metadata": {
                "total_pages": len(pages_dict),
                "file_size": os.path.getsize(file_path),
                "processed_timestamp": datetime.now().isoformat()
            }
        }

    def process_all_documents(self):
        """Process all PDF documents in the received folder"""
        processed_count = 0
        error_count = 0
        
        for filename in os.listdir(self.received_folder):
            if filename.lower().endswith('.pdf'):
                try:
                    print(f"Processing: {filename}")
                    # Process the document
                    json_data = self.process_document(filename)
                    
                    # Save JSON to parsed folder
                    json_filename = f"{os.path.splitext(filename)[0]}.json"
                    json_path = os.path.join(self.parsed_folder, json_filename)
                    
                    with open(json_path, 'w', encoding='utf-8') as f:
                        json.dump(json_data, f, indent=4, ensure_ascii=False)
                    
                    # Move original PDF to completed folder
                    source_path = os.path.join(self.received_folder, filename)
                    dest_path = os.path.join(self.completed_folder, filename)
                    shutil.move(source_path, dest_path)
                    
                    print(f"Successfully processed: {filename}")
                    processed_count += 1
                    
                except Exception as e:
                    print(f"Error processing {filename}: {str(e)}")
                    error_count += 1

        print(f"\nProcessing complete!")
        print(f"Successfully processed: {processed_count} documents")
        print(f"Errors encountered: {error_count} documents")

if __name__ == "__main__":
    processor = DocumentProcessor()
    processor.process_all_documents() 