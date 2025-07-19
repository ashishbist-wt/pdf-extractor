# PDF to Excel Converter

A full-stack application that extracts insurance policy information from PDF documents using GPT-4-mini and exports the data to Excel format.

## Features

- Upload PDF documents through a modern React frontend
- Extract text content from PDFs using PyPDF2
- Analyze documents with OpenAI GPT-4-mini to extract specific insurance fields
- Export extracted data to Excel format
- Download processed Excel files

## Extracted Fields

The application extracts the following insurance policy information:

1. Current Policy number
2. Previous Policy number
3. Customer Name
4. Vehicle Number
5. Sum Insured
6. OD premium
7. TP premium
8. Net Premium (Before Taxes)
9. Total Premium (After Taxes)
10. Insurance Company name
11. Intermediary Name

## Tech Stack

### Backend
- Python 3.8+
- Flask
- PyPDF2 (PDF text extraction)
- OpenAI API (GPT-4-mini)
- Pandas (Excel generation)
- Flask-CORS (Cross-origin requests)

### Frontend
- React 18
- Vite (Build tool)
- Axios (HTTP client)
- Modern CSS with responsive design

## Setup Instructions

### Prerequisites

1. Python 3.8 or higher
2. Node.js 16 or higher
3. OpenAI API key

### Backend Setup

1. Navigate to the backend directory:
   ```bash
   cd backend
   ```

2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Create a `.env` file from the example:
   ```bash
   cp .env.example .env
   ```

5. Add your OpenAI API key to the `.env` file:
   ```
   OPENAI_API_KEY=your_actual_api_key_here
   ```

6. Run the Flask server:
   ```bash
   python app.py
   ```

   The backend will be available at `http://localhost:5001`

### Frontend Setup

1. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Start the development server:
   ```bash
   npm run dev
   ```

   The frontend will be available at `http://localhost:3000`

## Usage

1. Open your browser and go to `http://localhost:3000`
2. Click "Choose PDF File" and select an insurance policy PDF
3. Click "Upload & Process" to analyze the document
4. Review the extracted information displayed on the page
5. Click "Download Excel File" to get the processed data in Excel format

## API Endpoints

### POST /upload
Uploads and processes a PDF file.

**Request:** Multipart form data with 'file' field containing the PDF

**Response:**
```json
{
  "success": true,
  "data": {
    "Current Policy number": "...",
    "Previous Policy number": "...",
    // ... other extracted fields
  },
  "message": "PDF processed successfully"
}
```

### POST /download-excel
Generates and downloads an Excel file from extracted data.

**Request:** JSON object with extracted data

**Response:** Excel file download

### GET /health
Health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "message": "PDF to Excel API is running"
}
```

## Environment Variables

- `OPENAI_API_KEY`: Your OpenAI API key (required)

## Error Handling

The application includes comprehensive error handling for:
- Invalid file types
- PDF processing errors
- OpenAI API errors
- Excel generation errors
- Network connectivity issues

## Development

### Running in Development Mode

1. Start the backend server: `python backend/app.py`
2. Start the frontend server: `npm run dev` (from frontend directory)
3. The frontend will proxy API requests to the backend automatically

### Building for Production

1. Build the frontend:
   ```bash
   cd frontend
   npm run build
   ```

2. The built files will be in `frontend/dist/`

## Troubleshooting

### Common Issues

1. **OpenAI API Key Error**: Make sure your API key is correctly set in the `.env` file
2. **CORS Issues**: Ensure Flask-CORS is installed and configured
3. **PDF Processing Errors**: Check that the uploaded file is a valid PDF
4. **Port Conflicts**: Make sure ports 3000 and 5000 are available

### Logs

Check the console output for both frontend and backend for detailed error messages.

## License

This project is for demonstration purposes.