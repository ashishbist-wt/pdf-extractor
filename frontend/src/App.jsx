import React, { useState } from 'react'
import axios from 'axios'
import './App.css'

function App() {
  const [file, setFile] = useState(null)
  const [loading, setLoading] = useState(false)
  const [extractedData, setExtractedData] = useState(null)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [displayText, setDisplayText] = useState('Text content will appear here...')

  const handleFileChange = (e) => {
    const selectedFile = e.target.files[0]
    if (selectedFile && selectedFile.type === 'application/pdf') {
      setFile(selectedFile)
      setError('')
    } else {
      setError('Please select a valid PDF file')
      setFile(null)
    }
  }

  const handleUpload = async () => {
    if (!file) {
      setError('Please select a PDF file first')
      return
    }

    setLoading(true)
    setError('')
    setSuccess('')

    const formData = new FormData()
    formData.append('file', file)

    try {
      const response = await axios.post('http://localhost:5001/upload', formData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      })

      if (response.data.success) {
        setExtractedData(response.data.data)
        setSuccess('PDF processed successfully! You can now download the Excel file.')
        
        // Update the text display area with raw OCR text
        if (response.data.ocr_text) {
          setDisplayText(response.data.ocr_text)
        } else {
          // Fallback to structured data if OCR text is not available
          const textContent = Object.entries(response.data.data)
            .map(([key, value]) => `${key}: ${value || 'Not Found'}`)
            .join('\n')
          setDisplayText(textContent)
        }
      } else {
        setError('Failed to process PDF')
      }
    } catch (err) {
      setError(err.response?.data?.error || 'An error occurred while processing the PDF')
    } finally {
      setLoading(false)
    }
  }

  const handleDownloadExcel = async () => {
    if (!extractedData) {
      setError('No data to download')
      return
    }

    try {
      const response = await axios.post('http://localhost:5001/download-excel', extractedData, {
        responseType: 'blob'
      })

      // Create blob link to download
      const url = window.URL.createObjectURL(new Blob([response.data]))
      const link = document.createElement('a')
      link.href = url
      
      // Get filename from response headers or use default
      const contentDisposition = response.headers['content-disposition']
      let filename = 'insurance_data.xlsx'
      if (contentDisposition) {
        const filenameMatch = contentDisposition.match(/filename="(.+)"/)
        if (filenameMatch) {
          filename = filenameMatch[1]
        }
      }
      
      link.setAttribute('download', filename)
      document.body.appendChild(link)
      link.click()
      link.remove()
      window.URL.revokeObjectURL(url)
      
      setSuccess('Excel file downloaded successfully!')
    } catch (err) {
      setError('Failed to download Excel file')
    }
  }

  return (
    <div className="App">
      <div className="main-container">
        {/* Left Column - PDF to Excel Converter */}
        <div className="left-column">
          <div className="converter-container">
            <h1>PDF to Excel Converter</h1>
            <p className="subtitle">Upload an insurance PDF to extract policy information</p>
            
            <div className="upload-section">
              <div className="file-input-wrapper">
                <input
                  type="file"
                  id="pdf-upload"
                  accept=".pdf"
                  onChange={handleFileChange}
                  className="file-input"
                />
                <label htmlFor="pdf-upload" className="file-label">
                  {file ? file.name : 'Choose PDF File'}
                </label>
              </div>
              
              <button 
                onClick={handleUpload} 
                disabled={!file || loading}
                className="upload-btn"
              >
                {loading ? 'Processing...' : 'Upload & Process'}
              </button>
            </div>

            {error && (
              <div className="message error">
                {error}
              </div>
            )}

            {success && (
              <div className="message success">
                {success}
              </div>
            )}

            {extractedData && (
              <div className="results-section">
                <h2>Extracted Information</h2>
                <div className="data-grid">
                  {Object.entries(extractedData).map(([key, value]) => (
                    <div key={key} className="data-item">
                      <span className="data-label">{key}:</span>
                      <span className="data-value">{value || 'Not Found'}</span>
                    </div>
                  ))}
                </div>
                
                <button 
                  onClick={handleDownloadExcel}
                  className="download-btn"
                >
                  Download Excel File
                </button>
              </div>
            )}
          </div>
        </div>

        {/* Right Column - Text Display Area */}
        <div className="right-column">
          <div className="text-display-container">
            <h2>Extracted OCR Text</h2>
            <p className="text-display-subtitle">Raw text extracted from the PDF using OCR</p>
            <div className="text-display-area">
              <pre>{displayText}</pre>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default App