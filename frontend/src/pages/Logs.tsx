import React, { useState, useEffect, useCallback } from 'react';
import { logsApi } from '../api/logs';
import type { LogDate, LogRow, LogsFilter } from '../api/logs';
import {
    FileText, RefreshCw, ChevronLeft, ChevronRight,
    Search, Filter, X, Clock, Activity, AlertTriangle,
    CheckCircle, XCircle, ChevronDown
} from 'lucide-react';

// ── helpers ───────────────────────────────────────────────────────
const STATUS_COLOR = (code: string) => {
    const n = parseInt(code, 10);
    if (n >= 500) return { dot: '#ef4444', text: '#fca5a5', bg: 'rgba(239,68,68,0.1)' };
    if (n >= 400) return { dot: '#f59e0b', text: '#fde68a', bg: 'rgba(245,158,11,0.1)' };
    if (n >= 200) return { dot: '#22c55e', text: '#86efac', bg: 'rgba(34,197,94,0.1)' };
    return { dot: '#6366f1', text: '#c7d2fe', bg: 'rgba(99,102,241,0.1)' };
};

const METHOD_COLOR: Record<string, string> = {
    GET: '#22c55e', POST: '#6366f1', PUT: '#f59e0b',
    PATCH: '#f59e0b', DELETE: '#ef4444', OPTIONS: '#94a3b8',
};

function fmt_duration(ms: string) {
    const n = parseFloat(ms);
    if (n > 1000) return `${(n / 1000).toFixed(2)}s`;
    return `${Math.round(n)}ms`;
}

function fmt_ts(ts: string) {
    try {
        return new Date(ts).toLocaleTimeString('en-GB', { hour12: false });
    } catch { return ts; }
}

function fmt_bytes(b: number) {
    if (b > 1024 * 1024) return `${(b / 1024 / 1024).toFixed(1)} MB`;
    if (b > 1024) return `${(b / 1024).toFixed(1)} KB`;
    return `${b} B`;
}

// ── Detail Drawer ─────────────────────────────────────────────────
const DetailDrawer: React.FC<{ row: LogRow; onClose: () => void }> = ({ row, onClose }) => {
    const sc = STATUS_COLOR(row.status_code);

    const tryPretty = (s: string) => {
        try { return JSON.stringify(JSON.parse(s), null, 2); }
        catch { return s; }
    };

    return (
        <div style={{
            position: 'fixed', inset: 0, zIndex: 9999,
            display: 'flex', alignItems: 'flex-end', justifyContent: 'flex-end',
        }}>
            {/* Backdrop */}
            <div
                style={{ position: 'absolute', inset: 0, background: 'rgba(0,0,0,0.5)', backdropFilter: 'blur(4px)' }}
                onClick={onClose}
            />

            {/* Panel */}
            <div style={{
                position: 'relative', zIndex: 1,
                width: '480px', height: '100vh',
                background: '#0d1117',
                borderLeft: '1px solid rgba(255,255,255,0.08)',
                display: 'flex', flexDirection: 'column',
                animation: 'slideInRight 0.2s ease',
            }}>
                {/* Header */}
                <div style={{
                    padding: '16px 20px', borderBottom: '1px solid rgba(255,255,255,0.06)',
                    display: 'flex', alignItems: 'center', gap: '10px',
                }}>
                    <div style={{
                        padding: '6px 10px', borderRadius: '6px',
                        background: sc.bg, border: `1px solid ${sc.dot}30`,
                    }}>
                        <span style={{ fontSize: '13px', fontWeight: 700, color: sc.text }}>{row.status_code}</span>
                    </div>
                    <div style={{ flex: 1, minWidth: 0 }}>
                        <p style={{ fontSize: '12px', fontWeight: 700, color: '#f1f5f9', margin: 0 }}>
                            <span style={{ color: METHOD_COLOR[row.method] || '#94a3b8', marginRight: '8px' }}>{row.method}</span>
                            {row.path}
                        </p>
                        <p style={{ fontSize: '10px', color: 'rgba(255,255,255,0.3)', margin: '2px 0 0' }}>
                            {row.timestamp} · {fmt_duration(row.duration_ms)}
                        </p>
                    </div>
                    <button onClick={onClose} style={{ background: 'none', border: 'none', color: 'rgba(255,255,255,0.3)', cursor: 'pointer', padding: '4px' }}>
                        <X size={16} />
                    </button>
                </div>

                {/* Scrollable body */}
                <div style={{ flex: 1, overflowY: 'auto', padding: '12px 20px', display: 'flex', flexDirection: 'column', gap: '16px' }}>

                    {/* Metadata grid */}
                    <section>
                        <p style={{ fontSize: '10px', textTransform: 'uppercase', letterSpacing: '0.07em', color: 'rgba(255,255,255,0.25)', fontWeight: 700, marginBottom: '8px' }}>Request Info</p>
                        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '6px' }}>
                            {[
                                ['Method', row.method],
                                ['Status', row.status_code],
                                ['Duration', fmt_duration(row.duration_ms)],
                                ['Time', fmt_ts(row.timestamp)],
                                ['Path', row.path],
                                ['Query', row.query_params || '—'],
                            ].map(([k, v]) => (
                                <div key={k} style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.06)', borderRadius: '6px', padding: '8px 10px' }}>
                                    <p style={{ fontSize: '9px', color: 'rgba(255,255,255,0.25)', textTransform: 'uppercase', letterSpacing: '0.06em', fontWeight: 700, margin: '0 0 2px' }}>{k}</p>
                                    <p style={{ fontSize: '11px', color: '#e2e8f0', margin: 0, wordBreak: 'break-all' }}>{v}</p>
                                </div>
                            ))}
                        </div>
                    </section>

                    {/* User agent */}
                    {row.user_agent && (
                        <section>
                            <p style={{ fontSize: '10px', textTransform: 'uppercase', letterSpacing: '0.07em', color: 'rgba(255,255,255,0.25)', fontWeight: 700, marginBottom: '6px' }}>User Agent</p>
                            <p style={{ fontSize: '10px', color: 'rgba(255,255,255,0.4)', wordBreak: 'break-all', lineHeight: 1.5 }}>{row.user_agent}</p>
                        </section>
                    )}

                    {/* Request body */}
                    {row.request_body && (
                        <section>
                            <p style={{ fontSize: '10px', textTransform: 'uppercase', letterSpacing: '0.07em', color: 'rgba(255,255,255,0.25)', fontWeight: 700, marginBottom: '6px' }}>Request Body</p>
                            <pre style={{
                                background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.06)',
                                borderRadius: '6px', padding: '10px', margin: 0,
                                fontSize: '10px', color: '#86efac', overflowX: 'auto', whiteSpace: 'pre-wrap', wordBreak: 'break-all',
                            }}>{tryPretty(row.request_body)}</pre>
                        </section>
                    )}

                    {/* Response body */}
                    {row.response_body && (
                        <section>
                            <p style={{ fontSize: '10px', textTransform: 'uppercase', letterSpacing: '0.07em', color: 'rgba(255,255,255,0.25)', fontWeight: 700, marginBottom: '6px' }}>Response Body</p>
                            <pre style={{
                                background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.06)',
                                borderRadius: '6px', padding: '10px', margin: 0,
                                fontSize: '10px', color: '#c7d2fe', overflowX: 'auto', whiteSpace: 'pre-wrap', wordBreak: 'break-all',
                            }}>{tryPretty(row.response_body)}</pre>
                        </section>
                    )}

                    {/* Error */}
                    {row.error && (
                        <section>
                            <p style={{ fontSize: '10px', textTransform: 'uppercase', letterSpacing: '0.07em', color: '#f87171', fontWeight: 700, marginBottom: '6px' }}>Error</p>
                            <pre style={{
                                background: 'rgba(239,68,68,0.06)', border: '1px solid rgba(239,68,68,0.2)',
                                borderRadius: '6px', padding: '10px', margin: 0,
                                fontSize: '10px', color: '#fca5a5', whiteSpace: 'pre-wrap', wordBreak: 'break-all',
                            }}>{row.error}</pre>
                        </section>
                    )}
                </div>
            </div>
        </div>
    );
};

// ── Main Logs Page ─────────────────────────────────────────────────
const PAGE_SIZE = 100;

export const LogsPage: React.FC = () => {
    const [dates, setDates] = useState<LogDate[]>([]);
    const [selectedDate, setSelectedDate] = useState<string>('');
    const [rows, setRows] = useState<LogRow[]>([]);
    const [total, setTotal] = useState(0);
    const [page, setPage] = useState(0);
    const [loading, setLoading] = useState(false);
    const [selectedRow, setSelectedRow] = useState<LogRow | null>(null);
    const [dateOpen, setDateOpen] = useState(false);
    const [sortDir, setSortDir] = useState<'desc' | 'asc'>('desc');

    const [filters, setFilters] = useState<LogsFilter>({ method: '', status: '', path: '' });
    const [appliedFilters, setAppliedFilters] = useState<LogsFilter>({});

    // Load available dates
    useEffect(() => {
        logsApi.getDates().then(d => {
            setDates(d);
            if (d.length > 0) setSelectedDate(d[0].date);
        }).catch(() => { });
    }, []);

    // Load rows when date/page/filters change
    const loadRows = useCallback(async () => {
        if (!selectedDate) return;
        setLoading(true);
        try {
            const resp = await logsApi.getLogs(selectedDate, {
                ...appliedFilters,
                limit: PAGE_SIZE,
                offset: page * PAGE_SIZE,
            });
            setRows(resp.rows);
            setTotal(resp.total);
        } catch { setRows([]); }
        finally { setLoading(false); }
    }, [selectedDate, page, appliedFilters]);

    useEffect(() => { loadRows(); }, [loadRows]);

    const applyFilters = () => {
        setAppliedFilters({ method: filters.method || undefined, status: filters.status || undefined, path: filters.path || undefined });
        setPage(0);
    };
    const clearFilters = () => {
        setFilters({ method: '', status: '', path: '' });
        setAppliedFilters({});
        setPage(0);
    };

    // Stats
    const stats = rows.reduce((acc, r) => {
        const n = parseInt(r.status_code, 10);
        if (n >= 500) acc.errors++;
        else if (n >= 400) acc.warnings++;
        else acc.ok++;
        acc.avgMs += parseFloat(r.duration_ms);
        return acc;
    }, { ok: 0, warnings: 0, errors: 0, avgMs: 0 });
    const avgMs = rows.length ? (stats.avgMs / rows.length).toFixed(0) : '—';

    const selectedDateInfo = dates.find(d => d.date === selectedDate);
    const totalPages = Math.ceil(total / PAGE_SIZE);

    // Sort rows by timestamp on the client
    const sortedRows = [...rows].sort((a, b) => {
        const ta = new Date(a.timestamp).getTime();
        const tb = new Date(b.timestamp).getTime();
        return sortDir === 'desc' ? tb - ta : ta - tb;
    });

    return (
        <div style={{ display: 'flex', flexDirection: 'column', height: '100%', gap: '16px' }}>
            {/* Header */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flexWrap: 'wrap' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                    <div style={{ padding: '8px', borderRadius: '10px', background: 'rgba(99,102,241,0.15)', border: '1px solid rgba(99,102,241,0.2)', display: 'flex' }}>
                        <FileText size={18} color="#6366f1" />
                    </div>
                    <div>
                        <h1 style={{ fontSize: '20px', fontWeight: 700, color: '#f1f5f9', margin: 0 }}>Request Logs</h1>
                        <p style={{ fontSize: '11px', color: 'rgba(255,255,255,0.3)', margin: 0 }}>
                            {selectedDateInfo ? `${fmt_bytes(selectedDateInfo.size_bytes)} · ${total} entries` : 'Loading…'}
                        </p>
                    </div>
                </div>

                <div style={{ flex: 1 }} />

                {/* Date picker */}
                <div style={{ position: 'relative' }}>
                    <button
                        onClick={() => setDateOpen(v => !v)}
                        style={{
                            display: 'flex', alignItems: 'center', gap: '6px',
                            padding: '6px 12px', borderRadius: '8px',
                            background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.1)',
                            color: '#e2e8f0', fontSize: '12px', fontWeight: 600, cursor: 'pointer',
                        }}
                    >
                        <Clock size={13} />
                        {selectedDate || 'Select date'}
                        <ChevronDown size={13} />
                    </button>
                    {dateOpen && (
                        <div style={{
                            position: 'absolute', top: '100%', right: 0, marginTop: '4px',
                            background: '#161b22', border: '1px solid rgba(255,255,255,0.1)',
                            borderRadius: '8px', overflow: 'hidden', zIndex: 100, minWidth: '180px',
                        }}>
                            {dates.map(d => (
                                <button
                                    key={d.date}
                                    onClick={() => { setSelectedDate(d.date); setPage(0); setDateOpen(false); }}
                                    style={{
                                        width: '100%', padding: '8px 14px', display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                                        background: d.date === selectedDate ? 'rgba(99,102,241,0.15)' : 'none',
                                        border: 'none', color: d.date === selectedDate ? '#818cf8' : 'rgba(255,255,255,0.6)',
                                        fontSize: '12px', cursor: 'pointer', fontWeight: d.date === selectedDate ? 700 : 500,
                                        gap: '12px',
                                    }}
                                >
                                    <span>{d.date}</span>
                                    <span style={{ fontSize: '10px', color: 'rgba(255,255,255,0.3)' }}>{fmt_bytes(d.size_bytes)}</span>
                                </button>
                            ))}
                        </div>
                    )}
                </div>

                <button
                    onClick={loadRows}
                    disabled={loading}
                    style={{
                        display: 'flex', alignItems: 'center', gap: '5px',
                        padding: '6px 12px', borderRadius: '8px',
                        background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.1)',
                        color: 'rgba(255,255,255,0.5)', fontSize: '12px', cursor: 'pointer',
                    }}
                >
                    <RefreshCw size={13} className={loading ? 'animate-spin' : ''} />
                    Refresh
                </button>
            </div>

            {/* Stats bar */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, minmax(0, 1fr))', gap: '10px' }}>
                {[
                    { label: 'Total', value: total, icon: <Activity size={14} />, color: '#6366f1' },
                    { label: '2xx OK', value: stats.ok, icon: <CheckCircle size={14} />, color: '#22c55e' },
                    { label: '4xx Warn', value: stats.warnings, icon: <AlertTriangle size={14} />, color: '#f59e0b' },
                    { label: '5xx Error', value: stats.errors, icon: <XCircle size={14} />, color: '#ef4444' },
                ].map(s => (
                    <div key={s.label} style={{
                        background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.06)',
                        borderRadius: '10px', padding: '12px 16px', display: 'flex', alignItems: 'center', gap: '10px',
                    }}>
                        <span style={{ color: s.color }}>{s.icon}</span>
                        <div>
                            <p style={{ fontSize: '18px', fontWeight: 700, color: '#f1f5f9', margin: 0, lineHeight: 1 }}>{s.value}</p>
                            <p style={{ fontSize: '10px', color: 'rgba(255,255,255,0.3)', margin: '3px 0 0' }}>{s.label}</p>
                        </div>
                    </div>
                ))}
            </div>

            {/* Filter bar */}
            <div style={{
                display: 'flex', gap: '8px', alignItems: 'center', flexWrap: 'wrap',
                background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.06)',
                borderRadius: '10px', padding: '10px 14px',
            }}>
                <Filter size={13} color="rgba(255,255,255,0.3)" />

                {/* Method */}
                <select
                    value={filters.method}
                    onChange={e => setFilters(f => ({ ...f, method: e.target.value }))}
                    style={{
                        background: '#161b22', border: '1px solid rgba(255,255,255,0.1)',
                        borderRadius: '6px', padding: '4px 8px', color: '#e2e8f0', fontSize: '11px', cursor: 'pointer',
                        colorScheme: 'dark',
                    }}
                >
                    <option value="">All Methods</option>
                    {['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS'].map(m => <option key={m}>{m}</option>)}
                </select>

                {/* Status */}
                <select
                    value={filters.status}
                    onChange={e => setFilters(f => ({ ...f, status: e.target.value }))}
                    style={{
                        background: '#161b22', border: '1px solid rgba(255,255,255,0.1)',
                        borderRadius: '6px', padding: '4px 8px', color: '#e2e8f0', fontSize: '11px', cursor: 'pointer',
                        colorScheme: 'dark',
                    }}
                >
                    <option value="">All Status</option>
                    <option value="2xx">2xx Success</option>
                    <option value="4xx">4xx Client Error</option>
                    <option value="5xx">5xx Server Error</option>
                    <option value="200">200</option>
                    <option value="201">201</option>
                    <option value="400">400</option>
                    <option value="401">401</option>
                    <option value="403">403</option>
                    <option value="404">404</option>
                    <option value="429">429</option>
                    <option value="500">500</option>
                </select>

                {/* Path search */}
                <div style={{ position: 'relative', flex: 1, minWidth: '160px' }}>
                    <Search size={12} style={{ position: 'absolute', left: '8px', top: '50%', transform: 'translateY(-50%)', color: 'rgba(255,255,255,0.3)' }} />
                    <input
                        type="text"
                        placeholder="Filter path…"
                        value={filters.path}
                        onChange={e => setFilters(f => ({ ...f, path: e.target.value }))}
                        onKeyDown={e => e.key === 'Enter' && applyFilters()}
                        style={{
                            width: '100%', paddingLeft: '28px', paddingRight: '8px', paddingTop: '4px', paddingBottom: '4px',
                            background: '#161b22', border: '1px solid rgba(255,255,255,0.1)',
                            borderRadius: '6px', color: '#e2e8f0', fontSize: '11px', outline: 'none',
                            colorScheme: 'dark',
                        }}
                    />
                </div>

                <button
                    onClick={applyFilters}
                    style={{
                        padding: '4px 12px', borderRadius: '6px',
                        background: 'rgba(99,102,241,0.15)', border: '1px solid rgba(99,102,241,0.3)',
                        color: '#818cf8', fontSize: '11px', fontWeight: 600, cursor: 'pointer',
                    }}
                >Apply</button>

                {(appliedFilters.method || appliedFilters.status || appliedFilters.path) && (
                    <button
                        onClick={clearFilters}
                        style={{
                            display: 'flex', alignItems: 'center', gap: '4px', padding: '4px 10px', borderRadius: '6px',
                            background: 'rgba(239,68,68,0.08)', border: '1px solid rgba(239,68,68,0.2)',
                            color: '#f87171', fontSize: '11px', cursor: 'pointer',
                        }}
                    >
                        <X size={11} />Clear
                    </button>
                )}

                <span style={{ fontSize: '10px', color: 'rgba(255,255,255,0.2)', marginLeft: 'auto' }}>
                    avg {avgMs}ms
                </span>
            </div>

            {/* Table */}
            <div style={{
                flex: 1, overflow: 'hidden', display: 'flex', flexDirection: 'column',
                background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.06)',
                borderRadius: '12px',
            }}>
                {/* Table header */}
                <div style={{
                    display: 'grid',
                    gridTemplateColumns: '160px 60px 260px 60px 80px 1fr',
                    padding: '8px 14px',
                    borderBottom: '1px solid rgba(255,255,255,0.06)',
                    position: 'sticky', top: 0,
                    background: 'rgba(13,17,23,0.95)',
                    backdropFilter: 'blur(10px)',
                }}>
                    {/* Clickable Timestamp header */}
                    <button
                        onClick={() => setSortDir(d => d === 'desc' ? 'asc' : 'desc')}
                        style={{
                            display: 'flex', alignItems: 'center', gap: '4px',
                            background: 'none', border: 'none', cursor: 'pointer', padding: 0,
                            fontSize: '9px', textTransform: 'uppercase', letterSpacing: '0.08em',
                            color: '#818cf8', fontWeight: 700,
                        }}
                    >
                        Timestamp
                        <span style={{ fontSize: '11px', lineHeight: 1 }}>{sortDir === 'desc' ? '↓' : '↑'}</span>
                    </button>
                    {['Method', 'Path', 'Status', 'Duration', 'Error / Response'].map(h => (
                        <span key={h} style={{ fontSize: '9px', textTransform: 'uppercase', letterSpacing: '0.08em', color: 'rgba(255,255,255,0.25)', fontWeight: 700 }}>{h}</span>
                    ))}
                </div>

                {/* Rows */}
                <div style={{ flex: 1, overflowY: 'auto' }}>
                    {loading ? (
                        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '120px', color: 'rgba(255,255,255,0.25)', fontSize: '12px', gap: '8px' }}>
                            <RefreshCw size={14} className="animate-spin" />Loading logs…
                        </div>
                    ) : rows.length === 0 ? (
                        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '120px', gap: '8px' }}>
                            <FileText size={24} color="rgba(255,255,255,0.15)" />
                            <p style={{ fontSize: '12px', color: 'rgba(255,255,255,0.25)' }}>No log entries found</p>
                        </div>
                    ) : sortedRows.map((row, i) => {
                        const sc = STATUS_COLOR(row.status_code);
                        const preview = row.error || row.response_body?.slice(0, 120) || '';
                        return (
                            <div
                                key={`${row._id}-${i}`}
                                onClick={() => setSelectedRow(row)}
                                style={{
                                    display: 'grid',
                                    gridTemplateColumns: '160px 60px 260px 60px 80px 1fr',
                                    padding: '7px 14px',
                                    borderBottom: '1px solid rgba(255,255,255,0.03)',
                                    cursor: 'pointer',
                                    transition: 'background 0.12s',
                                    alignItems: 'center',
                                }}
                                onMouseEnter={e => (e.currentTarget.style.background = 'rgba(255,255,255,0.04)')}
                                onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
                            >
                                <span style={{ fontSize: '10px', color: 'rgba(255,255,255,0.35)', fontFamily: 'monospace' }}>
                                    {fmt_ts(row.timestamp)}
                                </span>
                                <span style={{ fontSize: '10px', fontWeight: 700, color: METHOD_COLOR[row.method] || '#94a3b8' }}>
                                    {row.method}
                                </span>
                                <span style={{ fontSize: '10px', color: 'rgba(255,255,255,0.6)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', fontFamily: 'monospace' }}>
                                    {row.path}
                                </span>
                                <span style={{
                                    display: 'inline-flex', alignItems: 'center', gap: '4px',
                                    fontSize: '10px', fontWeight: 700, color: sc.text,
                                }}>
                                    <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: sc.dot, flexShrink: 0 }} />
                                    {row.status_code}
                                </span>
                                <span style={{ fontSize: '10px', color: 'rgba(255,255,255,0.35)', fontFamily: 'monospace' }}>
                                    {fmt_duration(row.duration_ms)}
                                </span>
                                <span style={{ fontSize: '10px', color: row.error ? '#fca5a5' : 'rgba(255,255,255,0.25)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                                    {preview || '—'}
                                </span>
                            </div>
                        );
                    })}
                </div>

                {/* Pagination */}
                {totalPages > 1 && (
                    <div style={{
                        display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '12px',
                        padding: '10px', borderTop: '1px solid rgba(255,255,255,0.06)',
                    }}>
                        <button
                            disabled={page === 0}
                            onClick={() => setPage(p => p - 1)}
                            style={{ background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '6px', padding: '4px 8px', color: 'rgba(255,255,255,0.5)', cursor: page === 0 ? 'not-allowed' : 'pointer', display: 'flex', alignItems: 'center' }}
                        >
                            <ChevronLeft size={14} />
                        </button>
                        <span style={{ fontSize: '11px', color: 'rgba(255,255,255,0.4)' }}>
                            Page {page + 1} of {totalPages} · {total} total
                        </span>
                        <button
                            disabled={page >= totalPages - 1}
                            onClick={() => setPage(p => p + 1)}
                            style={{ background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '6px', padding: '4px 8px', color: 'rgba(255,255,255,0.5)', cursor: page >= totalPages - 1 ? 'not-allowed' : 'pointer', display: 'flex', alignItems: 'center' }}
                        >
                            <ChevronRight size={14} />
                        </button>
                    </div>
                )}
            </div>

            {/* Detail drawer */}
            {selectedRow && (
                <DetailDrawer row={selectedRow} onClose={() => setSelectedRow(null)} />
            )}

            <style>{`
                @keyframes slideInRight {
                    from { transform: translateX(100%); opacity: 0; }
                    to { transform: translateX(0); opacity: 1; }
                }
            `}</style>
        </div>
    );
};
