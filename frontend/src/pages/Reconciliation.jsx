import { useState, useEffect } from 'react'
import axios from 'axios'
import './Reconciliation.css'

export default function Reconciliation() {
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
        // In a real app, we would fetch the actual file based on selectedDate
        // For now, we'll simulate by using the date to determine which file to load
        await getFileContent(selectedDate)
      )
      
      setReport(response.data)
      console.log('Fetched report:', response.data)
    } catch (err) {
      setError(err.response?.data || err.message || 'Failed to fetch data')
    } finally {
      setLoading(false)
    }
  }

  const getFileContent = async (date) => {
    // Map dates to their respective files
    const fileMap = {
      '2026-07-25': '/sample_billing_dataset/billing_log_2026-07-25.json',
      '2026-07-26': '/sample_billing_dataset/billing_log_2026-07-26.json',
      '2026-07-27': '/sample_billing_dataset/billing_log_2026-07-27.json'
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
        <div className="loading">Loading reconciliation data...</div>
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
          <p>Please select a date to view reconciliation data.</p>
        </div>
      </div>
    )
  }

  const { reconciliation, validation_errors } = report.report

  return (
    <div className="content-wrapper">
      <div className="page-header">
        <h1>EOD Reconciliation Dashboard</h1>
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
          <p>{validation_errors.length} record(s) had validation errors and were skipped.</p>
          <details>
            <summary>View Details</summary>
            <ul>
              {validation_errors.map((err, index) => (
                <li key={index}>
                  <strong>Record {err.record_index + 1}:</strong> 
                  {err.errors.map(e => e.msg).join(', ')}
                </li>
              ))}
            </ul>
          </details>
        </div>
      )}

      <div className="stats-grid">
        <div className="stat-card">
          <h3>Total Billed</h3>
          <div className="stat-value">₹{(reconciliation.total_billed / 100).toFixed(2)}</div>
          <p className="stat-label">Total amount charged to patients</p>
        </div>
        
        <div className="stat-card">
          <h3>Total Collected</h3>
          <div className="stat-value">₹{(reconciliation.total_collected / 100).toFixed(2)}</div>
          <p className="stat-label">Total amount received from patients</p>
        </div>
        
        <div className="stat-card">
          <h3>Outstanding</h3>
          <div className="stat-value">₹{(reconciliation.outstanding / 100).toFixed(2)}</div>
          <p className="stat-label">Amount still owed (Billed - Collected)</p>
        </div>
        
        <div className="stat-card">
          <h3>Total Refunds</h3>
          <div className="stat-value">₹{(reconciliation.total_refunds / 100).toFixed(2)}</div>
          <p className="stat-label">Total amount refunded to patients</p>
        </div>
      </div>

      <div className="section">
        <h2>Payment Mode Breakdown</h2>
        <div className="table-container">
          <table>
            <thead>
              <tr>
                <th>Payment Mode</th>
                <th>Billed (₹)</th>
                <th>Collected (₹)</th>
                <th>Refunds (₹)</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td>Cash</td>
                <td>₹{(reconciliation.total_billed_by_mode.cash / 100).toFixed(2)}</td>
                <td>₹{(reconciliation.total_collected_by_mode.cash / 100).toFixed(2)}</td>
                <td>₹{(reconciliation.total_refunds_by_mode.cash / 100).toFixed(2)}</td>
              </tr>
              <tr>
                <td>Card</td>
                <td>₹{(reconciliation.total_billed_by_mode.card / 100).toFixed(2)}</td>
                <td>₹{(reconciliation.total_collected_by_mode.card / 100).toFixed(2)}</td>
                <td>₹{(reconciliation.total_refunds_by_mode.card / 100).toFixed(2)}</td>
              </tr>
              <tr>
                <td>UPI</td>
                <td>₹{(reconciliation.total_billed_by_mode.upi / 100).toFixed(2)}</td>
                <td>₹{(reconciliation.total_collected_by_mode.upi / 100).toFixed(2)}</td>
                <td>₹{(reconciliation.total_refunds_by_mode.upi / 100).toFixed(2)}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
