import { useState, useEffect } from 'react'
import axios from 'axios'
import './Narrative.css'

export default function Narrative() {
  const [report, setReport] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [selectedDate, setSelectedDate] = useState('2026-07-25')

  useEffect(() => {
    fetchReport()
  }, [selectedDate])

  const fetchReport = async () => {
    try {
      setLoading(true)
      setError(null)
      
      const response = await axios.post(
        'http://localhost:8000/api/v1/reports',
        await getFileContent(selectedDate)
      )
      
      setReport(response.data)
    } catch (err) {
      setError(err.response?.data || err.message || 'Failed to fetch data')
    } finally {
      setLoading(false)
    }
  }

  const getFileContent = async (date) => {
    const fileMap = {
      '2026-07-25': '../sample_billing_dataset/billing_log_2026-07-25.json',
      '2026-07-26': '../sample_billing_dataset/billing_log_2026-07-26.json',
      '2026-07-27': '../sample_billing_dataset/billing_log_2026-07-27.json'
    }
    
    const response = await fetch(fileMap[date])
    if (!response.ok) {
      throw new Error(`Failed to load data for ${date}`)
    }
    return await response.json()
  }

  if (loading) {
    return (
      <div className="content-wrapper">
        <div className="loading">Loading narrative data...</div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="content-wrapper">
        <div className="error">
          <h2>Error Loading Data</h2>
          <p>{error}</p>
          <button onClick={() => fetchReport()}>Retry</button>
        </div>
      </div>
    )
  }

  if (!report) {
    return (
      <div className="content-wrapper">
        <div className="empty-state">
          <h2>No Data Available</h2>
          <p>Please select a date to view narrative data.</p>
        </div>
      </div>
    )
  }

  const { reconciliation, validation_errors, analytics } = report.report

  // Simple placeholder narrative
  const narrative = `On the selected date, the clinic processed financial transactions including billings, collections, and refunds. The data shows various metrics related to payment methods and medication dispensing.`;

  // Simple traced figures
  const tracedFigures = [
    { label: 'Total Billed', value: '₹0', description: 'Placeholder' },
    { label: 'Total Collected', value: '₹0', description: 'Placeholder' }
  ]

  return (
    <div className="content-wrapper">
      <div className="page-header">
        <h1>AI Narrative Summary</h1>
        <div className="date-selector">
          <label htmlFor="date-select">Select Date: </label>
          <select 
            id="date-select"
            value={selectedDate}
            onChange={(e) => setSelectedDate(e.target.value)}
          >
            <option value="2026-07-25">July 25, 2026 (Refund Day)</option>
            <option value="2026-07-26">July 26, 2026 (Empty Day)</option>
            <option value="2026-07-27">July 27, 2026 (Normal Day)</option>
          </select>
        </div>
      </div>

      {validation_errors && validation_errors.length > 0 && (
        <div className="validation-warnings">
          <h3>Validation Warnings</h3>
          <p>{validation_errors.length} record(s) had validation errors and were skipped from analysis.</p>
        </div>
      )}

      <div className="narrative-layout">
        <div className="narrative-panel">
          <h2>Generated Narrative</h2>
          <div className="narrative-text">
            <p>{narrative}</p>
          </div>
        </div>

        <div className="traced-figures-panel">
          <h2>Traced Figures</h2>
          <div className="traced-figures-content">
            {tracedFigures.map((figure, index) => (
              <div key={index} className="figure-item">
                <div className="figure-label">{figure.label}</div>
                <div className="figure-value">{figure.value}</div>
                <div className="figure-description">{figure.description}</div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
