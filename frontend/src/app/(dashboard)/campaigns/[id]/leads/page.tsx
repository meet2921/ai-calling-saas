'use client'

import { useState, useRef, useCallback, useEffect } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { leadsApi } from '@/lib/api/leads'
import { campaignsApi } from '@/lib/api/campaigns'
import { Upload, FileText, RotateCcw, CheckCircle2, AlertCircle, Trash2 } from 'lucide-react'

type UploadState = 'idle' | 'dragging' | 'uploading' | 'success' | 'error'

interface Lead {
  id: string
  phone: string
  name?: string
  status: string
  last_called?: string
  duration?: number
  custom_fields?: Record<string, string>
}

const LEAD_STATUS: Record<string, { color: string; dot: string; label: string }> = {
  completed:  { color: '#16a34a', dot: '#16a34a', label: 'Completed' },
  failed:     { color: '#ef4444', dot: '#ef4444', label: 'Failed' },
  no_answer:  { color: '#6b7280', dot: '#9ca3af', label: 'No answer' },
  pending:    { color: '#d97706', dot: '#d97706', label: 'Pending' },
  calling:    { color: '#2563eb', dot: '#2563eb', label: 'Calling' },
  queued:     { color: '#7c3aed', dot: '#7c3aed', label: 'Queued' },
}

export default function LeadsUploadPage() {
  const { id } = useParams<{ id: string }>()
  const router = useRouter()

  const [uploadState, setUploadState] = useState<UploadState>('idle')
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [uploadProgress, setUploadProgress] = useState(0)
  const [uploadCount, setUploadCount] = useState<number | null>(null)
  const [errorMessage, setErrorMessage] = useState('')
  const [campaignName, setCampaignName] = useState('')

  const [leads, setLeads] = useState<Lead[]>([])
  const [leadsTotal, setLeadsTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(20)

  const [confirmLeadId, setConfirmLeadId] = useState<string | null>(null)

  const fileRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    if (!id) return
    campaignsApi.get(id).then(r => setCampaignName(r.data?.name ?? '')).catch(() => {})
    fetchLeads()
  }, [id])

  const fetchLeads = async () => {
    if (!id) return
    try {
      const res = await leadsApi.list(id, page, pageSize)
      const data = res.data
      const list = Array.isArray(data) ? data : data?.leads ?? data?.results ?? []
      setLeads(list)
      setLeadsTotal(data?.total ?? data?.count ?? list.length)
    } catch {}
  }

  useEffect(() => { fetchLeads() }, [page, pageSize])

  const validateFile = (file: File): string | null => {
    if (!file.name.toLowerCase().endsWith('.csv')) {
      return 'Invalid file format — only CSV files are supported.'
    }
    if (file.size > 10 * 1024 * 1024) {
      return 'File size exceeds 10MB limit.'
    }
    return null
  }

  const handleFile = async (file: File) => {
    const err = validateFile(file)
    if (err) {
      setSelectedFile(file)
      setErrorMessage(err)
      setUploadState('error')
      return
    }

    setSelectedFile(file)
    setUploadState('uploading')
    setUploadProgress(0)
    setErrorMessage('')

    // Simulate progress
    const interval = setInterval(() => {
      setUploadProgress(p => {
        if (p >= 90) { clearInterval(interval); return 90 }
        return p + Math.random() * 15
      })
    }, 200)

    try {
      const res = await leadsApi.upload(id!, file)
      clearInterval(interval)
      setUploadProgress(100)
      const count = res.data?.leads_added ?? res.data?.count ?? res.data?.total ?? null
      setUploadCount(count)
      setUploadState('success')
      await fetchLeads()
    } catch (e: any) {
      clearInterval(interval)
      const detail = e?.response?.data?.detail ?? 'Failed to upload leads. Please try again.'
      setErrorMessage(detail)
      setUploadState('error')
    }
  }

  const onDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setUploadState('dragging')
  }, [])

  const onDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setUploadState(prev => prev === 'dragging' ? 'idle' : prev)
  }, [])

  const onDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    const file = e.dataTransfer.files[0]
    if (file) handleFile(file)
    else setUploadState('idle')
  }, [id])

  const onFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) handleFile(file)
    e.target.value = ''
  }

  const confirmDelete = async () => {
    if (!id || !confirmLeadId) return
    try {
      await leadsApi.delete(id, confirmLeadId)
      setLeads(prev => prev.filter(l => l.id !== confirmLeadId))
      setLeadsTotal(prev => prev - 1)
    } catch {
      alert('Failed to delete lead')
    } finally {
      setConfirmLeadId(null)
    }
  }

  const resetUpload = () => {
    setUploadState('idle')
    setSelectedFile(null)
    setUploadProgress(0)
    setUploadCount(null)
    setErrorMessage('')
  }

  const isDragging = uploadState === 'dragging'
  const isUploading = uploadState === 'uploading'
  const isSuccess = uploadState === 'success'
  const isError = uploadState === 'error'

  const totalPages = Math.max(1, Math.ceil(leadsTotal / pageSize))
  const fmtDate = (d: string) =>
    new Date(d).toLocaleString('en-IN', { day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' })
  const fmtDuration = (sec: number) => {
    const m = Math.floor(sec / 60).toString().padStart(2, '0')
    const s = (sec % 60).toString().padStart(2, '0')
    return `${m}:${s}`
  }
  const fmtSize = (bytes: number) => {
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>

      {/* Upload card */}
      <div style={{ backgroundColor: 'white', border: '1px solid #e5e7eb', borderRadius: '14px', padding: '24px 28px' }}>
        <p style={{ fontSize: '16px', fontWeight: '700', color: '#2563eb', marginBottom: '20px' }}>Upload leads</p>

        <p style={{ fontSize: '13px', fontWeight: '500', color: '#374151', marginBottom: '10px' }}>Upload leads</p>

        {/* Drop zone */}
        <div
          onDragOver={onDragOver}
          onDragLeave={onDragLeave}
          onDrop={onDrop}
          onClick={() => !isUploading && fileRef.current?.click()}
          style={{
            border: `2px dashed ${isDragging ? '#2563eb' : isError ? '#ef4444' : '#d1d5db'}`,
            borderRadius: '12px',
            padding: '40px 20px',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            gap: '8px',
            cursor: isUploading ? 'default' : 'pointer',
            backgroundColor: isDragging ? '#eff6ff' : 'transparent',
            transition: 'all 0.2s',
          }}
        >
          <Upload
            size={32}
            style={{ color: isDragging ? '#2563eb' : '#6b7280', marginBottom: '4px' }}
          />
          <p style={{ fontSize: '14px', fontWeight: '500', color: isDragging ? '#2563eb' : '#374151' }}>
            Drag and drop your CSV file here
          </p>
          <p style={{ fontSize: '13px', color: '#9ca3af' }}>or</p>
          <button
            onClick={e => { e.stopPropagation(); fileRef.current?.click() }}
            disabled={isUploading}
            style={{
              padding: '7px 20px', borderRadius: '8px', fontSize: '13px', fontWeight: '500',
              border: '1px solid #d1d5db', backgroundColor: 'white', color: '#374151',
              cursor: isUploading ? 'not-allowed' : 'pointer',
            }}
          >
            Browse files
          </button>
        </div>

        <div style={{ display: 'flex', gap: '24px', marginTop: '10px' }}>
          <p style={{ fontSize: '12px', color: '#9ca3af' }}>Accepted format: CSV only</p>
          <p style={{ fontSize: '12px', color: '#9ca3af' }}>Max file size: 10MB</p>
        </div>

        {/* File row — uploading or done */}
        {selectedFile && (
          <div style={{
            marginTop: '14px',
            display: 'flex',
            alignItems: 'center',
            gap: '12px',
            padding: '12px 16px',
            backgroundColor: '#f9fafb',
            borderRadius: '10px',
            border: '1px solid #e5e7eb',
          }}>
            <FileText size={18} style={{ color: '#6b7280', flexShrink: 0 }} />
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: isUploading ? '6px' : '0' }}>
                <span style={{ fontSize: '13px', fontWeight: '500', color: '#2563eb' }}>{selectedFile.name}</span>
                {isUploading && (
                  <span style={{ fontSize: '13px', color: '#6b7280' }}>{Math.round(uploadProgress)}%</span>
                )}
              </div>
              <span style={{ fontSize: '12px', color: '#9ca3af' }}>{fmtSize(selectedFile.size)}</span>
              {isUploading && (
                <div style={{ height: '4px', backgroundColor: '#e5e7eb', borderRadius: '99px', overflow: 'hidden', marginTop: '6px' }}>
                  <div style={{
                    height: '100%',
                    width: `${uploadProgress}%`,
                    backgroundColor: '#2563eb',
                    borderRadius: '99px',
                    transition: 'width 0.3s ease',
                  }} />
                </div>
              )}
            </div>
            {!isUploading && (
              <button
                onClick={e => { e.stopPropagation(); resetUpload() }}
                style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#9ca3af', padding: '4px', flexShrink: 0 }}
                title="Remove file"
              >
                <RotateCcw size={16} />
              </button>
            )}
          </div>
        )}

        <input
          ref={fileRef}
          type="file"
          accept=".csv"
          style={{ display: 'none' }}
          onChange={onFileChange}
        />
      </div>

      {/* Success banner */}
      {isSuccess && (
        <div style={{
          display: 'flex',
          alignItems: 'flex-start',
          gap: '10px',
          backgroundColor: '#f0fdf4',
          border: '1px solid #bbf7d0',
          borderRadius: '10px',
          padding: '14px 18px',
        }}>
          <CheckCircle2 size={18} style={{ color: '#16a34a', flexShrink: 0, marginTop: '1px' }} />
          <div>
            <p style={{ fontSize: '13px', fontWeight: '600', color: '#16a34a', marginBottom: '2px' }}>
              Leads uploaded successfully
            </p>
            <p style={{ fontSize: '12px', color: '#15803d' }}>
              {uploadCount != null ? `${uploadCount.toLocaleString('en-IN')} leads have been added` : 'Leads have been added'}
              {campaignName ? ` to ${campaignName}.` : '.'}
            </p>
          </div>
        </div>
      )}

      {/* Error banner */}
      {isError && (
        <div style={{
          display: 'flex',
          alignItems: 'flex-start',
          gap: '10px',
          backgroundColor: '#fff1f2',
          border: '1px solid #fecdd3',
          borderRadius: '10px',
          padding: '14px 18px',
        }}>
          <AlertCircle size={18} style={{ color: '#ef4444', flexShrink: 0, marginTop: '1px' }} />
          <div>
            <p style={{ fontSize: '13px', fontWeight: '600', color: '#ef4444', marginBottom: '2px' }}>
              Upload Failed
            </p>
            <p style={{ fontSize: '12px', color: '#b91c1c' }}>{errorMessage}</p>
          </div>
        </div>
      )}

      {/* All leads */}
      <div>
        <p style={{ fontSize: '16px', fontWeight: '700', color: '#111827', marginBottom: '16px' }}>All leads</p>

        {leads.length === 0 ? (
          <div style={{
            backgroundColor: 'white',
            border: '1px solid #e5e7eb',
            borderRadius: '14px',
            padding: '60px 20px',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            gap: '12px',
          }}>
            <img
              src="/empty-leads.png"
              alt="No leads"
              style={{ width: '120px', opacity: 0.8 }}
              onError={e => (e.currentTarget.style.display = 'none')}
            />
            <p style={{ fontSize: '16px', fontWeight: '700', color: '#111827' }}>No leads uploaded yet</p>
            <p style={{ fontSize: '13px', color: '#9ca3af' }}>Upload a CSV file to start your campaign.</p>
          </div>
        ) : (
          <div style={{ backgroundColor: 'white', border: '1px solid #e5e7eb', borderRadius: '12px', overflow: 'hidden' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid #e5e7eb', backgroundColor: '#f9fafb' }}>
                  {['Name', 'Status', 'Phone number', 'Last Called', 'Duration', ''].map(h => (
                    <th key={h} style={{ textAlign: 'left', padding: '13px 20px', fontSize: '14px', fontWeight: '700', color: '#111827' }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {leads.map((l, i) => {
                  const name = l.name ?? l.custom_fields?.name ?? '—'
                  const s = LEAD_STATUS[l.status] ?? LEAD_STATUS.pending
                  return (
                    <tr
                      key={l.id}
                      style={{ borderBottom: i < leads.length - 1 ? '1px solid #f3f4f6' : 'none' }}
                      onMouseEnter={e => (e.currentTarget as HTMLElement).style.backgroundColor = '#f9fafb'}
                      onMouseLeave={e => (e.currentTarget as HTMLElement).style.backgroundColor = 'transparent'}
                    >
                      <td style={{ padding: '13px 20px', fontSize: '14px', fontWeight: '500', color: '#111827' }}>{name}</td>
                      <td style={{ padding: '13px 20px' }}>
                        <span style={{ display: 'inline-flex', alignItems: 'center', gap: '5px', fontSize: '13px', fontWeight: '600', color: s.color }}>
                          <span style={{ width: '7px', height: '7px', borderRadius: '50%', backgroundColor: s.dot, display: 'inline-block' }} />
                          {s.label}
                        </span>
                      </td>
                      <td style={{ padding: '13px 20px', fontSize: '13px', color: '#374151' }}>{l.phone}</td>
                      <td style={{ padding: '13px 20px', fontSize: '13px', color: '#374151' }}>
                        {l.last_called ? fmtDate(l.last_called) : '—'}
                      </td>
                      <td style={{ padding: '13px 20px', fontSize: '13px', color: '#374151' }}>
                        {l.duration != null ? fmtDuration(l.duration) : '—'}
                      </td>
                      <td style={{ padding: '13px 20px', textAlign: 'right' }}>
                        <button
                          onClick={() => setConfirmLeadId(l.id)}
                          title="Delete lead"
                          style={{
                            background: 'none', border: 'none', cursor: 'pointer',
                            color: '#9ca3af', padding: '4px', borderRadius: '6px',
                            display: 'inline-flex', alignItems: 'center',
                          }}
                          onMouseEnter={e => (e.currentTarget as HTMLElement).style.color = '#ef4444'}
                          onMouseLeave={e => (e.currentTarget as HTMLElement).style.color = '#9ca3af'}
                        >
                          <Trash2 size={15} />
                        </button>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>

            {/* Pagination */}
            <div style={{
              display: 'flex', alignItems: 'center', justifyContent: 'space-between',
              padding: '12px 20px', borderTop: '1px solid #f3f4f6',
              fontSize: '13px', color: '#6b7280',
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <select
                  value={pageSize}
                  onChange={e => { setPageSize(Number(e.target.value)); setPage(1) }}
                  style={{ padding: '4px 8px', border: '1px solid #e5e7eb', borderRadius: '6px', fontSize: '13px', color: '#374151', backgroundColor: 'white', cursor: 'pointer' }}
                >
                  {[20, 50, 100].map(n => <option key={n} value={n}>{n}</option>)}
                </select>
                <span>Items per page</span>
                <span style={{ marginLeft: '8px', color: '#374151' }}>
                  {leadsTotal === 0 ? '0' : `${(page - 1) * pageSize + 1}-${Math.min(page * pageSize, leadsTotal)}`} of {leadsTotal} items
                </span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <select
                  value={page}
                  onChange={e => setPage(Number(e.target.value))}
                  style={{ padding: '4px 8px', border: '1px solid #e5e7eb', borderRadius: '6px', fontSize: '13px', color: '#374151', backgroundColor: 'white', cursor: 'pointer' }}
                >
                  {[...Array(totalPages)].map((_, i) => <option key={i + 1} value={i + 1}>{i + 1}</option>)}
                </select>
                <span>of {totalPages} pages</span>
                <button
                  onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1}
                  style={{ width: '28px', height: '28px', border: '1px solid #e5e7eb', borderRadius: '6px', cursor: page === 1 ? 'not-allowed' : 'pointer', color: page === 1 ? '#d1d5db' : '#374151', backgroundColor: 'white', fontSize: '16px' }}
                >‹</button>
                <button
                  onClick={() => setPage(p => Math.min(totalPages, p + 1))} disabled={page >= totalPages}
                  style={{ width: '28px', height: '28px', border: '1px solid #e5e7eb', borderRadius: '6px', cursor: page >= totalPages ? 'not-allowed' : 'pointer', color: page >= totalPages ? '#d1d5db' : '#374151', backgroundColor: 'white', fontSize: '16px' }}
                >›</button>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Delete confirmation modal */}
      {confirmLeadId && (
        <div style={{
          position: 'fixed', inset: 0, zIndex: 1000,
          backgroundColor: 'rgba(0,0,0,0.4)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
        }}>
          <div style={{
            backgroundColor: 'white', borderRadius: '14px',
            padding: '28px 32px', width: '100%', maxWidth: '400px',
            boxShadow: '0 20px 60px rgba(0,0,0,0.15)',
            display: 'flex', flexDirection: 'column', gap: '16px',
          }}>
            <div>
              <p style={{ fontSize: '16px', fontWeight: '700', color: '#111827', marginBottom: '6px' }}>Delete lead?</p>
              <p style={{ fontSize: '13px', color: '#6b7280', lineHeight: '1.5' }}>
                This action cannot be undone. The lead will be permanently removed from this campaign.
              </p>
            </div>
            <div style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end' }}>
              <button
                onClick={() => setConfirmLeadId(null)}
                style={{
                  padding: '8px 20px', borderRadius: '8px', fontSize: '13px', fontWeight: '500',
                  border: '1px solid #e5e7eb', backgroundColor: 'white', color: '#374151', cursor: 'pointer',
                }}
              >
                Cancel
              </button>
              <button
                onClick={confirmDelete}
                style={{
                  padding: '8px 20px', borderRadius: '8px', fontSize: '13px', fontWeight: '600',
                  border: 'none', backgroundColor: '#ef4444', color: 'white', cursor: 'pointer',
                }}
              >
                Delete
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
