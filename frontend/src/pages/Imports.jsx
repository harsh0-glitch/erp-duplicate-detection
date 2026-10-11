import { useState, useRef, useCallback, useEffect } from 'react'
import { uploadProductsFile, getImportJob } from '../services/imports'
import { formatFileSize, formatDateTime } from '../utils/format'
import { LoadingState, ErrorState, EmptyState } from '../components/StateComponents'
import StatusBadge from '../components/StatusBadge'

const JOB_STATES = ['PENDING', 'PROCESSING', 'COMPLETED', 'COMPLETED_WITH_ERRORS', 'FAILED']

const Imports = () => {
  const fileInputRef = useRef(null)
  const pollTimerRef = useRef(null)
  const [file, setFile] = useState(null)
  const [dragOver, setDragOver] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [uploadError, setUploadError] = useState(null)
  const [job, setJob] = useState(null)
  const [polling, setPolling] = useState(false)
  const [jobError, setJobError] = useState(null)

  useEffect(() => {
    return () => {
      if (pollTimerRef.current) clearTimeout(pollTimerRef.current)
    }
  }, [])

  const handleFileSelect = useCallback((selected) => {
    if (!selected) return
    const valid = selected.name.endsWith('.csv') || selected.name.endsWith('.xlsx') || selected.name.endsWith('.xls')
    if (!valid) {
      setUploadError('Only CSV and XLSX files are supported.')
      return
    }
    if (pollTimerRef.current) clearTimeout(pollTimerRef.current)
    setPolling(false)
    setUploadError(null)
    setJobError(null)
    setFile(selected)
    setJob(null)
  }, [])

  const handleDrop = useCallback((e) => {
    e.preventDefault()
    setDragOver(false)
    const f = e.dataTransfer.files[0]
    handleFileSelect(f)
  }, [handleFileSelect])

  const handleUpload = async () => {
    if (!file) return
    if (pollTimerRef.current) clearTimeout(pollTimerRef.current)
    setUploading(true)
    setUploadError(null)
    setJobError(null)
    setJob(null)
    try {
      const res = await uploadProductsFile(file)
      const jobData = res.data
      setJob(jobData)
      const jobId = jobData?.job_id || jobData?.id
      if (jobId && (jobData?.status === 'PENDING' || jobData?.status === 'PROCESSING')) {
        pollJob(jobId)
      }
    } catch (e) {
      setUploadError(e)
    } finally {
      setUploading(false)
    }
  }

  const pollJob = (jobId) => {
    setPolling(true)
    setJobError(null)
    if (pollTimerRef.current) clearTimeout(pollTimerRef.current)
    const poll = async () => {
      try {
        const res = await getImportJob(jobId)
        const data = res.data
        setJob(data)
        if (data?.status === 'PENDING' || data?.status === 'PROCESSING') {
          pollTimerRef.current = setTimeout(poll, 2000)
        } else {
          setPolling(false)
        }
      } catch (e) {
        setJobError(e)
        setPolling(false)
      }
    }
    poll()
  }

  const handleBrowse = () => fileInputRef.current?.click()

  const handleFileInput = (e) => {
    handleFileSelect(e.target.files?.[0])
    e.target.value = ''
  }

  const errors = job?.error_summary || job?.errors || job?.error_details || []
  const isProcessing = job?.status === 'PENDING' || job?.status === 'PROCESSING' || polling

  return (
    <div className="fade-in">
      <div className="page-header">
        <h2>Bulk Import</h2>
        <div className="page-subtitle">Upload products in bulk via CSV or XLSX</div>
      </div>

      {/* Upload zone */}
      <div className="panel mb-4">
        <div className="panel-body">
          <div
            className={`drop-zone ${dragOver ? 'dragover' : ''}`}
            onDrop={handleDrop}
            onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
            onDragLeave={() => setDragOver(false)}
            onClick={handleBrowse}
          >
            <div className="drop-zone-icon">↑</div>
            <div style={{ fontWeight: 600, fontSize: '1rem', color: 'var(--navy)', marginBottom: '4px' }}>
              Drag and drop your file here
            </div>
            <div style={{ fontSize: '0.85rem', color: 'var(--muted-text)' }}>
              or click to browse — CSV or XLSX
            </div>
            <input
              ref={fileInputRef}
              type="file"
              accept=".csv,.xlsx,.xls"
              style={{ display: 'none' }}
              onChange={handleFileInput}
            />
          </div>

          {uploadError && (
            <div className="card-base mt-3" style={{ padding: '12px 16px', borderColor: 'var(--muted-peach)', background: 'var(--muted-peach-light)' }}>
              <div style={{ fontSize: '0.85rem', color: '#B57A6A', fontWeight: 500 }}>
                {uploadError.message || String(uploadError)}
              </div>
            </div>
          )}

          {jobError && (
            <div className="card-base mt-3" style={{ padding: '12px 16px', borderColor: 'var(--muted-peach)', background: 'var(--muted-peach-light)' }}>
              <div style={{ fontSize: '0.85rem', color: '#B57A6A', fontWeight: 500 }}>
                {jobError.message || String(jobError)}
              </div>
            </div>
          )}

          {file && (
            <div className="mt-3" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '12px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                <div style={{
                  width: '40px', height: '40px', borderRadius: 'var(--radius-md)',
                  background: 'var(--powder-blue-light)', display: 'flex', alignItems: 'center', justifyContent: 'center',
                  fontSize: '1.2rem', color: 'var(--navy)',
                }}>
                  📄
                </div>
                <div>
                  <div style={{ fontWeight: 600, fontSize: '0.9rem' }}>{file.name}</div>
                  <div style={{ fontSize: '0.8rem', color: 'var(--muted-text)' }}>{formatFileSize(file.size)}</div>
                </div>
              </div>
              <div style={{ display: 'flex', gap: '8px' }}>
                <button className="btn-navy" onClick={handleUpload} disabled={uploading || isProcessing}>
                  {uploading ? 'Uploading…' : 'Upload'}
                </button>
                <button
                  className="btn-outline"
                  onClick={() => {
                    if (pollTimerRef.current) clearTimeout(pollTimerRef.current)
                    setPolling(false)
                    setFile(null)
                    setJob(null)
                    setJobError(null)
                  }}
                  disabled={uploading}
                >
                  Remove
                </button>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Import result */}
      {job && (
        <div className="panel fade-in">
          <div className="panel-header">
            <h3>Import Result</h3>
            <StatusBadge status={job.status} />
          </div>
          <div className="panel-body">
            <div className="stat-grid mb-4">
              <div className="stat-card">
                <div className="stat-label">Total Rows</div>
                <div className="stat-value">{job.total_rows ?? '—'}</div>
              </div>
              <div className="stat-card">
                <div className="stat-label">Successful</div>
                <div className="stat-value" style={{ color: 'var(--sage-dark)' }}>{job.successful_rows ?? '—'}</div>
              </div>
              <div className="stat-card">
                <div className="stat-label">Failed</div>
                <div className="stat-value" style={{ color: '#B85C3E' }}>{job.failed_rows ?? '—'}</div>
              </div>
              <div className="stat-card">
                <div className="stat-label">Errors</div>
                <div className="stat-value" style={{ color: 'var(--warm-yellow-dark)' }}>{errors.length}</div>
              </div>
            </div>

            {job.created_at && (
              <div style={{ fontSize: '0.85rem', color: 'var(--muted-text)', marginBottom: 'var(--space-2)' }}>
                Started: {formatDateTime(job.created_at)}
                {job.completed_at && ` · Completed: ${formatDateTime(job.completed_at)}`}
              </div>
            )}

            {isProcessing && (
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '12px', background: 'var(--powder-blue-light)', borderRadius: 'var(--radius-md)', marginBottom: 'var(--space-3)' }}>
                <div className="spinner-border spinner-border-sm" />
                <span style={{ fontSize: '0.88rem', color: 'var(--navy)' }}>Processing import…</span>
              </div>
            )}

            {errors.length > 0 && (
              <div>
                <h4 className="mb-3" style={{ color: '#B85C3E' }}>Row-Level Errors</h4>
                <div className="table-wrap" style={{ border: 'none' }}>
                  <table className="data-table">
                    <thead>
                      <tr>
                        <th>Row</th>
                        <th>SKU</th>
                        <th>Error</th>
                      </tr>
                    </thead>
                    <tbody>
                      {errors.map((err, i) => (
                        <tr key={i}>
                          <td>{err.row ?? err.row_number ?? '—'}</td>
                          <td>{err.sku || '—'}</td>
                          <td style={{ color: '#B85C3E' }}>{err.error || err.message || (typeof err === 'string' ? err : JSON.stringify(err))}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {job.status === 'COMPLETED' && errors.length === 0 && (
              <div style={{ padding: '12px', background: 'var(--sage-light)', borderRadius: 'var(--radius-md)', fontSize: '0.88rem', color: 'var(--sage-dark)', fontWeight: 500 }}>
                Import completed successfully. All rows imported.
              </div>
            )}

            {job.status === 'COMPLETED_WITH_ERRORS' && (
              <div style={{ padding: '12px', background: 'var(--muted-peach-light)', borderRadius: 'var(--radius-md)', fontSize: '0.88rem', color: '#B57A6A', fontWeight: 500, marginTop: errors.length > 0 ? 'var(--space-3)' : 0 }}>
                Import completed with errors. {job.successful_rows ?? 0} rows imported, {job.failed_rows ?? errors.length} rows failed.
              </div>
            )}

            {job.status === 'FAILED' && (
              <div style={{ padding: '12px', background: 'var(--muted-peach-light)', borderRadius: 'var(--radius-md)', fontSize: '0.88rem', color: '#B57A6A', fontWeight: 500, marginTop: errors.length > 0 ? 'var(--space-3)' : 0 }}>
                Import failed. {errors.length > 0 && !errors[0].row ? (errors[0].error || errors[0].message) : 'No products were imported.'}
              </div>
            )}
          </div>
        </div>
      )}

      {!job && !file && !uploading && (
        <div className="panel">
          <div className="panel-body">
            <EmptyState
              icon="↑"
              title="No import jobs yet"
              message="Upload a CSV or XLSX file to start importing products. Required columns: SKU, Name."
            />
          </div>
        </div>
      )}

      {/* Required columns info */}
      <div className="panel panel-sage mt-4">
        <div className="panel-header"><h3>Upload Requirements</h3></div>
        <div className="panel-body">
          <div style={{ fontSize: '0.88rem', color: 'var(--navy)' }}>
            <div className="mb-3"><strong>Required columns:</strong> SKU, Name</div>
            <div className="mb-3"><strong>Supported formats:</strong> CSV, XLSX</div>
            <div className="mb-3"><strong>Optional columns:</strong> Description, Brand, Category, Subcategory, Unit</div>
            <div><strong>Job states:</strong></div>
            <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', marginTop: '8px' }}>
              {JOB_STATES.map((s) => (
                <StatusBadge key={s} status={s.toLowerCase()} />
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default Imports
