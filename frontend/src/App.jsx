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
  const [activeTab, setActiveTab] = useState('raw')

  // Function to convert markdown and base64 to HTML
  const formatTextToHtml = (text) => {
    if (!text || text === 'Text content will appear here...') {
      return '<p>No formatted data available. Please upload and process a PDF first.</p>'
    }

    let formattedText = text
      // Convert literal \n to actual newlines first
      .replace(/\\n/g, '\n')
      // Convert base64 images to img tags
      .replace(/data:image\/[a-zA-Z]*;base64,[a-zA-Z0-9+\/=]*/g, (match) => {
        return `<img src="${match}" alt="Extracted Image" style="max-width: 100%; height: auto; margin: 10px 0; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);" />`
      })
      // Convert markdown headers
      .replace(/^### (.*$)/gim, '<h3>$1</h3>')
      .replace(/^## (.*$)/gim, '<h2>$1</h2>')
      .replace(/^# (.*$)/gim, '<h1>$1</h1>')
      // Convert markdown bold and italic
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      .replace(/\*(.*?)\*/g, '<em>$1</em>')
      // Convert markdown links
      .replace(/\[([^\]]+)\]\(([^\)]+)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>')
      // Convert markdown code blocks
      .replace(/```([\s\S]*?)```/g, '<pre><code>$1</code></pre>')
      // Convert inline code
      .replace(/`([^`]+)`/g, '<code>$1</code>')
      // Convert markdown lists
      .replace(/^\* (.+)$/gm, '<li>$1</li>')
      .replace(/^- (.+)$/gm, '<li>$1</li>')
      // Wrap consecutive list items in ul tags
      .replace(/((<li>.*<\/li>\s*)+)/g, '<ul>$1</ul>')
      // Convert line breaks
      .replace(/\n\n/g, '</p><p>')
      .replace(/\n/g, '<br>')
      // Wrap in paragraphs
      .replace(/^/, '<p>')
      .replace(/$/, '</p>')
      // Clean up empty paragraphs
      .replace(/<p><\/p>/g, '')
      // Fix paragraph tags around other block elements
      .replace(/<p>(<h[1-6]>)/g, '$1')
      .replace(/(<\/h[1-6]>)<\/p>/g, '$1')
      .replace(/<p>(<ul>)/g, '$1')
      .replace(/(<\/ul>)<\/p>/g, '$1')
      .replace(/<p>(<pre>)/g, '$1')
      .replace(/(<\/pre>)<\/p>/g, '$1')
      .replace(/<p>(<img)/g, '$1')
      .replace(/(\/>)<\/p>/g, '$1')

    return formattedText
  }

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
            
            {/* Tab Navigation */}
            <div className="tab-navigation">
              <button 
                className={`tab-button ${activeTab === 'raw' ? 'active' : ''}`}
                onClick={() => setActiveTab('raw')}
              >
                Raw Data
              </button>
              <button 
                className={`tab-button ${activeTab === 'formatted' ? 'active' : ''}`}
                onClick={() => setActiveTab('formatted')}
              >
                Formatted Data
              </button>
            </div>
            
            {/* Tab Content */}
            <div className="tab-content">
              {activeTab === 'raw' && (
                <div className="text-display-area">
                  <p className="text-display-subtitle">Raw text extracted from the PDF using OCR</p>
                  <pre>{displayText}</pre>
                </div>
              )}
              
              {activeTab === 'formatted' && (
                <div className="text-display-area">
                  <p className="text-display-subtitle">Markdown and images converted to HTML</p>
                  <div className="formatted-html-content" dangerouslySetInnerHTML={{
                    __html: formatTextToHtml(displayText)
                  }} />
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default App