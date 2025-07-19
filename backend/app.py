from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import pandas as pd
import io
import os
from datetime import datetime
import json
import base64
from mistralai import Mistral
from openai import OpenAI
from dotenv import load_dotenv

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

def encode_pdf(pdf_file):
    """Encode the pdf to base64."""
    try:
        pdf_file.seek(0)
        return base64.b64encode(pdf_file.read()).decode('utf-8')
    except Exception as e:
        print(f"Error: {e}")
        return None

def extract_text_with_mistral_ocr(pdf_file):
    """Extract text from PDF using Mistral OCR API"""
    try:
        # Getting the base64 string
        base64_pdf = encode_pdf(pdf_file)
        if not base64_pdf:
            return "Error: Failed to convert PDF to base64"
        
        api_key = os.environ.get("MISTRAL_API_KEY")
        if not api_key:
            return "Error: MISTRAL_API_KEY not found in environment variables"
            
        client = Mistral(api_key=api_key)
        
        # Check if client has ocr attribute
        if not hasattr(client, 'ocr'):
            return "Error: OCR functionality not available in current Mistral client version. Please update mistralai package."
        
        ocr_response = client.ocr.process(
            model="mistral-ocr-latest",
            document={
                "type": "document_url",
                "document_url": f"data:application/pdf;base64,{base64_pdf}"
            },
            include_image_base64=True
        )
        
        # Extract text from the OCR response
        extracted_text = ""
        if hasattr(ocr_response, 'text'):
            extracted_text = ocr_response.text
        elif hasattr(ocr_response, 'content'):
            extracted_text = ocr_response.content
        elif hasattr(ocr_response, 'choices') and len(ocr_response.choices) > 0:
            extracted_text = ocr_response.choices[0].message.content
        else:
            # Return the full response for debugging if structure is different
            extracted_text = f"OCR Response received but structure unknown: {str(ocr_response)}"
        
        
        return extracted_text
            
    except AttributeError as e:
        return f"Error: Mistral client doesn't support OCR. Please check your mistralai package version. Details: {str(e)}"
    except Exception as e:
        return f"Error with Mistral OCR: {str(e)}"


def analyze_with_openai(text):
    """Analyze PDF text with OpenAI to extract insurance fields"""
    try:
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            return "Error: OPENAI_API_KEY not found in environment variables"
            
        client = OpenAI(api_key=api_key)
        
        prompt = f"""
Analyze the following insurance document text 

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
        
        # Use OpenAI O3 for analysis
        response = client.chat.completions.create(
            model="gpt-4o-mini",  # Use O3 model
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert at extracting information from insurance documents. Always return valid JSON. Handle OCR-extracted text that may have some formatting issues."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.1
        )
        
        return response.choices[0].message.content
            
    except Exception as e:
        return f"Error with OpenAI O3 analysis: {str(e)}"

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
        
        # Extract text using Mistral OCR
        extracted_text = extract_text_with_mistral_ocr(file)
        
        if extracted_text.startswith('Error'):
            return jsonify({'error': extracted_text}), 500
        
        # Analyze with OpenAI O3 instead of Mistral
        openai_response = analyze_with_openai(extracted_text)
        
        if openai_response.startswith('Error'):
            return jsonify({'error': openai_response}), 500
        
        # Parse JSON response
        try:
            # Clean the response to extract JSON
            json_start = openai_response.find('{')
            json_end = openai_response.rfind('}') + 1
            json_str = openai_response[json_start:json_end]
            extracted_data = json.loads(json_str)
        except Exception as parse_error:
            return jsonify({'error': f'Failed to parse OpenAI response: {str(parse_error)}'}), 500
        
        # Return the extracted data along with raw OCR text
        return jsonify({
            'success': True,
            'data': extracted_data,
            'ocr_text': extracted_text,
            'message': 'PDF processed successfully using Mistral OCR and OpenAI O3 analysis.'
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
    return jsonify({'status': 'healthy', 'message': 'PDF to Excel API is running with Mistral OCR and OpenAI O3 analysis'})

if __name__ == '__main__':
    app.run(debug=True, port=5001)