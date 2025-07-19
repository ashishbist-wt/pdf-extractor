from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import PyPDF2
from openai import OpenAI
import pandas as pd
import io
import os
from datetime import datetime
import re
from dotenv import load_dotenv
from paddleocr import PaddleOCR
from pdf2image import convert_from_bytes
from PIL import Image
import numpy as np
import json

# Load environment variables
load_dotenv()

app = Flask(__name__)

# More explicit CORS configuration
CORS(app, resources={
    r"/*": {
        "origins": ["http://localhost:3000", "http://127.0.0.1:3000"],
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"]
    }
})

# Initialize PaddleOCR (run once)
ocr = PaddleOCR(use_angle_cls=True, lang='en', show_log=False)

def detect_pdf_content_type(pdf_file):
    """Detect if PDF contains text-based or image-based content"""
    try:
        pdf_file.seek(0)  # Reset file pointer
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        
        content_analysis = {
            'total_pages': len(pdf_reader.pages),
            'text_based_pages': 0,
            'image_based_pages': 0,
            'mixed_pages': 0,
            'page_types': []
        }
        
        for page_num, page in enumerate(pdf_reader.pages):
            text = page.extract_text().strip()
            
            # Check if page has extractable text
            if len(text) > 50:  # Threshold for meaningful text
                # Check if page also has images
                if '/XObject' in page.get('/Resources', {}):
                    xobjects = page['/Resources']['/XObject'].get_object()
                    has_images = any('/Subtype' in obj.get_object() and 
                                   obj.get_object()['/Subtype'] == '/Image' 
                                   for obj in xobjects.values() if hasattr(obj, 'get_object'))
                    if has_images:
                        content_analysis['mixed_pages'] += 1
                        content_analysis['page_types'].append('mixed')
                    else:
                        content_analysis['text_based_pages'] += 1
                        content_analysis['page_types'].append('text')
                else:
                    content_analysis['text_based_pages'] += 1
                    content_analysis['page_types'].append('text')
            else:
                content_analysis['image_based_pages'] += 1
                content_analysis['page_types'].append('image')
        
        # Determine overall PDF type
        if content_analysis['text_based_pages'] > content_analysis['image_based_pages']:
            pdf_type = 'text_dominant'
        elif content_analysis['image_based_pages'] > content_analysis['text_based_pages']:
            pdf_type = 'image_dominant'
        else:
            pdf_type = 'mixed'
            
        content_analysis['pdf_type'] = pdf_type
        return content_analysis
        
    except Exception as e:
        return {
            'error': f"Error analyzing PDF content: {str(e)}",
            'pdf_type': 'unknown'
        }

def extract_text_from_pdf(pdf_file):
    """Extract text from PDF using PyPDF2"""
    try:
        pdf_file.seek(0)
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text()
        return text
    except Exception as e:
        return f"Error extracting PDF text: {str(e)}"

def extract_text_with_ocr(pdf_file):
    """Extract text from PDF using PaddleOCR for image-based content"""
    try:
        pdf_file.seek(0)
        # Convert PDF pages to images
        images = convert_from_bytes(pdf_file.read(), dpi=300)
        
        extracted_text = ""
        
        for page_num, image in enumerate(images):
            # Convert PIL image to numpy array
            img_array = np.array(image)
            
            # Use PaddleOCR to extract text
            result = ocr.ocr(img_array, cls=True)
            
            page_text = ""
            if result and result[0]:
                for line in result[0]:
                    if len(line) > 1 and line[1][0]:  # Check if text exists
                        page_text += line[1][0] + " "
            
            extracted_text += f"\n--- Page {page_num + 1} ---\n{page_text}\n"
        
        return extracted_text
        
    except Exception as e:
        return f"Error extracting text with OCR: {str(e)}"

def extract_mixed_content(pdf_file, content_analysis):
    """Extract content from mixed PDF using both methods"""
    try:
        pdf_file.seek(0)
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        
        # First try text extraction
        text_content = ""
        for page in pdf_reader.pages:
            text_content += page.extract_text()
        
        # If text extraction yields insufficient content, use OCR
        if len(text_content.strip()) < 100:
            return extract_text_with_ocr(pdf_file)
        
        # For mixed content, combine both methods
        ocr_content = ""
        if content_analysis['image_based_pages'] > 0:
            pdf_file.seek(0)
            images = convert_from_bytes(pdf_file.read(), dpi=300)
            
            for page_num, image in enumerate(images):
                if page_num < len(content_analysis['page_types']):
                    if content_analysis['page_types'][page_num] in ['image', 'mixed']:
                        img_array = np.array(image)
                        result = ocr.ocr(img_array, cls=True)
                        
                        if result and result[0]:
                            page_text = ""
                            for line in result[0]:
                                if len(line) > 1 and line[1][0]:
                                    page_text += line[1][0] + " "
                            ocr_content += f"\n--- OCR Page {page_num + 1} ---\n{page_text}\n"
        
        # Combine text and OCR content
        combined_content = text_content
        if ocr_content:
            combined_content += "\n\n--- OCR EXTRACTED CONTENT ---\n" + ocr_content
            
        return combined_content
        
    except Exception as e:
        return f"Error extracting mixed content: {str(e)}"

def process_pdf_content(pdf_file):
    """Main function to process PDF based on its content type"""
    # Analyze PDF content type
    content_analysis = detect_pdf_content_type(pdf_file)
    
    if 'error' in content_analysis:
        return content_analysis['error'], content_analysis
    
    pdf_type = content_analysis['pdf_type']
    
    # Extract content based on PDF type
    if pdf_type == 'text_dominant':
        extracted_text = extract_text_from_pdf(pdf_file)
    elif pdf_type == 'image_dominant':
        extracted_text = extract_text_with_ocr(pdf_file)
    else:  # mixed content
        extracted_text = extract_mixed_content(pdf_file, content_analysis)
    
    return extracted_text, content_analysis

def analyze_with_gpt(text, content_analysis):
    """Analyze PDF text with GPT-4-mini to extract insurance fields"""
    try:
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        # Enhanced prompt that considers the PDF type
        pdf_type_context = f"This content was extracted from a {content_analysis['pdf_type']} PDF with {content_analysis['total_pages']} pages."
        
        prompt = f"""
        {pdf_type_context}
        
        Analyze the following insurance document text and extract these specific fields. Return the response in JSON format with exact field names:
        
        1. Current Policy number
        2. Previous Policy number
        3. Customer Name
        4. Vehicle Number
        5. Sum Insured
        6. OD premium
        7. TP premium
        8. Net Premium(Before Taxes)
        9. Total Premium(After Taxes)
        10. Insurance Company name
        11. Intermediary Name
        
        Document text:
        {text}
        
        Please return only a JSON object with these exact keys:
        {{
            "Current Policy number": "",
            "Previous Policy number": "",
            "Customer Name": "",
            "Vehicle Number": "",
            "Sum Insured": "",
            "OD premium": "",
            "TP premium": "",
            "Net Premium(Before Taxes)": "",
            "Total Premium(After Taxes)": "",
            "Insurance Company name": "",
            "Intermediary Name": ""
        }}
        
        If any field is not found, use "Not Found" as the value.
        """
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are an expert at extracting information from insurance documents. Always return valid JSON. Handle OCR-extracted text that may have some formatting issues."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1
        )
        
        return response.choices[0].message.content
    except Exception as e:
        return f"Error with GPT analysis: {str(e)}"

def create_excel(data):
    """Create Excel file from extracted data"""
    try:
        # Create DataFrame
        df = pd.DataFrame([data])
        
        # Create Excel file in memory
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Insurance Data', index=False)
        
        output.seek(0)
        return output
    except Exception as e:
        return None

@app.route('/upload', methods=['POST'])
def upload_pdf():
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file uploaded'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not file.filename.lower().endswith('.pdf'):
            return jsonify({'error': 'Only PDF files are allowed'}), 400
        
        # Process PDF content with type detection
        extracted_text, content_analysis = process_pdf_content(file)
        
        if extracted_text.startswith('Error'):
            return jsonify({'error': extracted_text}), 500
        
        # Analyze with GPT
        gpt_response = analyze_with_gpt(extracted_text, content_analysis)
        
        if gpt_response.startswith('Error'):
            return jsonify({'error': gpt_response}), 500
        
        # Parse JSON response
        try:
            # Clean the response to extract JSON
            json_start = gpt_response.find('{')
            json_end = gpt_response.rfind('}') + 1
            json_str = gpt_response[json_start:json_end]
            extracted_data = json.loads(json_str)
        except:
            return jsonify({'error': 'Failed to parse GPT response'}), 500
        
        # Return the extracted data with PDF analysis info
        return jsonify({
            'success': True,
            'data': extracted_data,
            'pdf_analysis': {
                'type': content_analysis['pdf_type'],
                'total_pages': content_analysis['total_pages'],
                'text_pages': content_analysis['text_based_pages'],
                'image_pages': content_analysis['image_based_pages'],
                'mixed_pages': content_analysis['mixed_pages']
            },
            'message': f'PDF processed successfully. Detected as {content_analysis["pdf_type"]} content.'
        })
        
    except Exception as e:
        return jsonify({'error': f'Server error: {str(e)}'}), 500

@app.route('/download-excel', methods=['POST'])
def download_excel():
    try:
        data = request.json
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        # Create Excel file
        excel_file = create_excel(data)
        
        if excel_file is None:
            return jsonify({'error': 'Failed to create Excel file'}), 500
        
        # Generate filename with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'insurance_data_{timestamp}.xlsx'
        
        return send_file(
            excel_file,
            as_attachment=True,
            download_name=filename,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        
    except Exception as e:
        return jsonify({'error': f'Server error: {str(e)}'}), 500

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'healthy', 'message': 'PDF to Excel API is running'})

if __name__ == '__main__':
    app.run(debug=True, port=5001)