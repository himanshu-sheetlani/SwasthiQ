import { useState, useEffect } from 'react'
import axios from 'axios'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'
import './Analytics.css'

export default function Analytics() {
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
        <div className="loading">Loading analytics data...</div>
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
          <p>Please select a date to view analytics data.</p>
        </div>
      </div>
    )
  }

  const { reconciliation, validation_errors, analytics } = report.report

  // Prepare data for revenue by hour chart
  const revenueByHour = analytics.revenue_by_hour || {}
  const chartData = []
  for (let hour = 0; hour <= 23; hour++) {
    const revenue = revenueByHour[hour] || 0
    chartData.push({
      hour: `${hour}:00`,
      revenue: revenue,
      barHeight: Math.abs(revenue)
    })
  }

  return (
    <div className="content-wrapper">
      <div className="page-header">
        <h1>Analytics Dashboard</h1>
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
        </div>
      )}

      <>
        {/* Revenue by Hour Chart - Full Width */}
        <div className="chart-section-full">
          <h2>Revenue by Hour of Day (UTC)</h2>
          {Object.keys(revenueByHour).length === 0 ? (
            <div className="empty-chart">No transaction data available for this day</div>
          ) : (
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="hour" />
                <YAxis
                  label={{ value: 'Revenue (₹)', angle: -90, position: 'insideLeft' }}
                  tickFormatter={(value) => `₹${(value / 100).toFixed(0)}`}
                />
                <Tooltip contentStyle={{ padding: '0', pointerEvents: 'none' }}>
                  {({ active, payload, label }) => {
                    if (active && payload && payload.length) {
                      const datum = payload[0];
                      const revenue = datum?.revenue ?? 0;
                      return (
                        <div className="recharts-tooltip-custom">
                          <p>{label}</p>
                          <p>Net Revenue: ₹{(revenue / 100).toFixed(2)}</p>
                        </div>
                      );
                    }
                    return null;
                  }}
                </Tooltip>
                <Legend verticalAlign="top" height={36} />
                <Bar dataKey="barHeight" fill="#175AD9" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>

        {/* Bottom Section: Two Columns */}
        <div className="analytics-bottom">
          {/* Top Medicines by Quantity - Left */}
          <div className="medicines-section-left">
            <h2>Top Medicines by Quantity</h2>
            <div className="medicines-list">
              {analytics.top_medicines_by_quantity && analytics.top_medicines_by_quantity.length > 0 ? (
                <ul>
                  {analytics.top_medicines_by_quantity.slice(0, 5).map((med, index) => (
                    <li key={index}>
                      <span className="medicine-rank">#{index + 1}</span>
                      <span className="medicine-name">{med.drug_name}</span>
                      <span className="medicine-value">{med.quantity}</span>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="empty-list">No medicine data available</p>
              )}
            </div>
          </div>

          {/* Top Medicines by Revenue - Right */}
          <div className="medicines-section-right">
            <h2>Top Medicines by Revenue</h2>
            <div className="medicines-list">
              {analytics.top_medicines_by_revenue && analytics.top_medicines_by_revenue.length > 0 ? (
                <ul>
                  {analytics.top_medicines_by_revenue.slice(0, 5).map((med, index) => (
                    <li key={index}>
                      <span className="medicine-rank">#{index + 1}</span>
                      <span className="medicine-name">{med.drug_name}</span>
                      <span className="medicine-value">₹{(med.revenue_paise / 100).toFixed(2)}</span>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="empty-list">No medicine data available</p>
              )}
            </div>
          </div>
        </div>
      </>
    </div>
  )
}
