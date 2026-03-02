import React, { useState, useEffect, useRef } from 'react';
import { deploymentApi } from '../../api/deployment';
import type { DeploymentResponse } from '../../types';
import {
    Loader2,
    Rocket,
    Trash2,
    AlertCircle,
    CheckCircle2,
    XCircle,
    Clock,
    Terminal,
    RefreshCw,
    AlertTriangle,
    Copy,
    Check,
    ChevronRight,
    Shield,
    Wrench,
    Timer
} from 'lucide-react';

interface Props {
    projectId: number;
    onStatusChange?: () => void | Promise<void>;
}

// ── Phase detection helpers ────────────────────────────────────────

type DeployPhase = 'idle' | 'init' | 'plan' | 'apply' | 'destroy' | 'complete' | 'failed';

function detectPhase(logs: string): DeployPhase {
    if (!logs) return 'idle';
    const lower = logs.toLowerCase();
    if (lower.includes('[error] command failed') || lower.includes('deployment failed') || lower.includes('boto3 deployment failed') || lower.includes('boto3 destroy failed')) return 'failed';
    if (lower.includes('deployment successful') || lower.includes('provisioning complete') || lower.includes('boto3 deployment finished: success') || lower.includes('destruction complete')) return 'complete';
    if (lower.includes('starting aws resource provisioning') || lower.includes('starting boto3 deployment')) return 'apply';
    if (lower.includes('starting aws resource destruction') || lower.includes('starting boto3 destroy')) return 'destroy';
    if (lower.includes('validating infrastructure configuration')) return 'plan';
    if (lower.includes('initializing')) return 'init';
    return 'idle';
}

const PHASE_LABELS: Record<DeployPhase, string> = {
    idle: 'Waiting',
    init: 'Initializing',
    plan: 'Planning',
    apply: 'Applying',
    destroy: 'Destroying',
    complete: 'Complete',
    failed: 'Failed',
};

// ── Error parsing ──────────────────────────────────────────────────

function parseErrorSummary(errorDetails?: string): { category: string; explanation: string; fix: string } | null {
    if (!errorDetails) return null;
    const categoryMatch = errorDetails.match(/## Error Category: (\w+)/);
    const fixMatch = errorDetails.match(/### Suggested Fix\n([\s\S]*?)$/);
    const explanationMatch = errorDetails.match(/^(.+?)(?=\n\n###|\n###)/m);

    return {
        category: categoryMatch?.[1] || 'UNKNOWN',
        explanation: explanationMatch?.[1]?.replace(/^## Error Category: \w+\n\n/, '') || 'An error occurred during deployment.',
        fix: fixMatch?.[1]?.trim() || 'Try regenerating the architecture and deploying again.',
    };
}

function getCategoryIcon(category: string) {
    switch (category) {
        case 'PERMISSION_DENIED': return <Shield size={16} className="text-red-400" />;
        case 'INVALID_CONFIG': return <Wrench size={16} className="text-amber-400" />;
        default: return <AlertTriangle size={16} className="text-red-400" />;
    }
}

function getCategoryColor(category: string): string {
    switch (category) {
        case 'PERMISSION_DENIED': return 'border-red-500/30 bg-red-500/5';
        case 'INVALID_CONFIG': return 'border-amber-500/30 bg-amber-500/5';
        case 'RESOURCE_LIMIT': return 'border-orange-500/30 bg-orange-500/5';
        case 'RESOURCE_CONFLICT': return 'border-yellow-500/30 bg-yellow-500/5';
        case 'PROVIDER_ERROR': return 'border-purple-500/30 bg-purple-500/5';
        case 'STATE_ERROR': return 'border-cyan-500/30 bg-cyan-500/5';
        case 'NETWORK_ERROR': return 'border-blue-500/30 bg-blue-500/5';
        default: return 'border-red-500/30 bg-red-500/5';
    }
}

// ── Log line colorization ──────────────────────────────────────────

function colorizeLogLine(line: string, idx: number) {
    const trimmed = line.trim();
    if (!trimmed) return <span key={idx}>{'\n'}</span>;

    // Error lines
    if (trimmed.startsWith('Error:') || trimmed.startsWith('│') && trimmed.toLowerCase().includes('error') || trimmed.includes('[ERROR]')) {
        return <span key={idx} className="text-red-400 font-semibold">{line}{'\n'}</span>;
    }
    // Warning lines
    if (trimmed.startsWith('Warning:') || trimmed.includes('[WARNING]')) {
        return <span key={idx} className="text-amber-400">{line}{'\n'}</span>;
    }
    // Success / creation lines
    if (trimmed.includes('✓ Created') || trimmed.includes('✓ Destroyed') || trimmed.includes('is ready') || trimmed.includes('Provisioning complete') || trimmed.includes('Destruction complete') || trimmed.includes('[AUTO-ROLLBACK] ✓')) {
        return <span key={idx} className="text-emerald-400 font-medium">{line}{'\n'}</span>;
    }
    // Failure lines from boto3
    if (trimmed.includes('✗ FAILED')) {
        return <span key={idx} className="text-red-400 font-semibold">{line}{'\n'}</span>;
    }
    // Phase markers
    if (trimmed.startsWith('=== ') || trimmed.startsWith('Starting deployment') || trimmed.startsWith('Deployment complete')) {
        return <span key={idx} className="text-blue-400 font-semibold">{line}{'\n'}</span>;
    }
    // Waiting for resource readiness
    if (trimmed.includes('⏳ Waiting')) {
        return <span key={idx} className="text-cyan-300/70 italic">{line}{'\n'}</span>;
    }
    // Plan output
    if (trimmed.startsWith('+') || trimmed.startsWith('# ')) {
        return <span key={idx} className="text-emerald-300/50">{line}{'\n'}</span>;
    }
    if (trimmed.startsWith('-') && !trimmed.startsWith('---')) {
        return <span key={idx} className="text-red-300/50">{line}{'\n'}</span>;
    }
    if (trimmed.startsWith('~')) {
        return <span key={idx} className="text-amber-300/50">{line}{'\n'}</span>;
    }
    // Rollback lines
    if (trimmed.includes('[AUTO-ROLLBACK]')) {
        return <span key={idx} className="text-orange-400 font-medium">{line}{'\n'}</span>;
    }
    // Default
    return <span key={idx} className="text-emerald-200/50">{line}{'\n'}</span>;
}

// ── Main Component ─────────────────────────────────────────────────

export const DeploymentTab: React.FC<Props> = ({ projectId, onStatusChange }) => {
    const [status, setStatus] = useState<DeploymentResponse | null>(null);
    const [loading, setLoading] = useState(true);
    const [deploying, setDeploying] = useState(false);
    const [destroying, setDestroying] = useState(false);
    const [error, setError] = useState('');
    const [copied, setCopied] = useState(false);
    const [elapsedSeconds, setElapsedSeconds] = useState(0);
    const logEndRef = useRef<HTMLDivElement>(null);
    const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

    useEffect(() => {
        fetchStatus();
    }, [projectId]);

    // Auto-scroll to bottom when logs update during deployment
    useEffect(() => {
        if (deploying && logEndRef.current) {
            logEndRef.current.scrollIntoView({ behavior: 'smooth' });
        }
    }, [status?.logs, deploying]);

    // Timer during deployment
    useEffect(() => {
        if (deploying) {
            setElapsedSeconds(0);
            timerRef.current = setInterval(() => {
                setElapsedSeconds(prev => prev + 1);
            }, 1000);
        } else {
            if (timerRef.current) {
                clearInterval(timerRef.current);
                timerRef.current = null;
            }
        }
        return () => {
            if (timerRef.current) clearInterval(timerRef.current);
        };
    }, [deploying]);

    const fetchStatus = async () => {
        try {
            const data = await deploymentApi.getStatus(projectId);
            setStatus(data);
            setError('');
        } catch (err: any) {
            console.error('Failed to fetch deployment status:', err);
        } finally {
            setLoading(false);
        }
    };

    const handleDeploy = async () => {
        setDeploying(true);
        setError('');
        // Clear previous logs when starting new deploy
        setStatus(prev => prev ? { ...prev, logs: '', status: 'running', error_message: undefined, error_details: undefined } : null);

        try {
            const token = localStorage.getItem('token');
            const response = await fetch(`${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/projects/${projectId}/deploy/stream`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({ action: 'apply' })
            });

            if (!response.ok) {
                const text = await response.text();
                let detail = 'Deployment request failed';
                try {
                    const errJson = JSON.parse(text);
                    detail = errJson.detail || text;
                } catch {
                    detail = text || detail;
                }
                throw new Error(detail);
            }

            if (!response.body) throw new Error('No response body');

            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let sseBuffer = '';

            // Initial status
            setStatus(prev => ({
                ...prev!,
                status: 'running',
                logs: ''
            }));

            while (true) {
                const { value, done } = await reader.read();
                if (done) break;

                sseBuffer += decoder.decode(value, { stream: true });

                // Parse complete SSE events (separated by \n\n)
                const parts = sseBuffer.split('\n\n');
                sseBuffer = parts.pop() ?? '';   // keep incomplete last chunk

                let newContent = '';
                for (const part of parts) {
                    for (const line of part.split('\n')) {
                        if (line.startsWith('data: ')) {
                            newContent += line.slice(6) + '\n';
                        }
                    }
                }
                if (newContent) {
                    setStatus(prev => ({
                        ...prev!,
                        logs: (prev?.logs || '') + newContent
                    }));
                }
            }

            // Stream finished - refresh full status to get final state/timestamps
            await fetchStatus();
            await onStatusChange?.();

        } catch (err: any) {
            const detail = err.message || 'Deployment failed';
            setError(detail);
            console.error('Deploy error:', err);
        } finally {
            setDeploying(false);
        }
    };

    const handleDestroy = async () => {
        if (!window.confirm('Are you sure you want to destroy all deployed resources? This action cannot be undone.')) return;
        setDestroying(true);
        setError('');
        try {
            const result = await deploymentApi.destroy(projectId);
            setStatus(result);
        } catch (err: any) {
            const detail = err.response?.data?.detail || err.message || 'Destroy failed';
            setError(detail);
            console.error('Destroy error:', err.response?.data || err);
        } finally {
            setDestroying(false);
            await fetchStatus();
            await onStatusChange?.();
        }
    };

    const handleCopyError = () => {
        const textToCopy = status?.error_message || status?.error_details || error;
        if (textToCopy) {
            navigator.clipboard.writeText(textToCopy);
            setCopied(true);
            setTimeout(() => setCopied(false), 2000);
        }
    };

    const formatElapsed = (seconds: number) => {
        const m = Math.floor(seconds / 60);
        const s = seconds % 60;
        return m > 0 ? `${m}m ${s}s` : `${s}s`;
    };

    const getStatusConfig = (s: string) => {
        const map: Record<string, { icon: React.ReactNode; class: string; label: string }> = {
            success: { icon: <CheckCircle2 size={16} />, class: 'badge-success', label: 'Success' },
            deployed: { icon: <CheckCircle2 size={16} />, class: 'badge-success', label: 'Deployed' },
            failed: { icon: <XCircle size={16} />, class: 'badge-danger', label: 'Failed' },
            running: { icon: <Loader2 size={16} className="animate-spin" />, class: 'badge-info', label: 'Running' },
            deploying: { icon: <Loader2 size={16} className="animate-spin" />, class: 'badge-info', label: 'Deploying' },
            pending: { icon: <Clock size={16} />, class: 'badge-warning', label: 'Pending' },
            destroying: { icon: <Loader2 size={16} className="animate-spin" />, class: 'badge-warning', label: 'Destroying' },
            destroyed: { icon: <Trash2 size={16} />, class: 'badge-danger', label: 'Destroyed' },
            partial_deployed: { icon: <AlertTriangle size={16} />, class: 'bg-amber-500/15 text-amber-400 border border-amber-500/30', label: 'Partial Deploy' },
        };
        return map[s] || { icon: <Clock size={16} />, class: 'badge-warning', label: s || 'Not Deployed' };
    };

    if (loading) {
        return (
            <div className="flex items-center justify-center h-full">
                <div className="flex flex-col items-center gap-3">
                    <div className="w-10 h-10 rounded-full border-2 border-primary/30 border-t-primary animate-spin" />
                    <p className="text-sm text-muted-foreground">Loading deployment status…</p>
                </div>
            </div>
        );
    }

    const statusInfo = getStatusConfig(status?.status || '');
    const currentPhase = deploying ? detectPhase(status?.logs || '') : 'idle';
    const errorSummary = parseErrorSummary(status?.error_details);

    // Phase pipeline indicators
    const phases: DeployPhase[] = ['init', 'apply', 'complete'];
    const phaseIndex = phases.indexOf(currentPhase);

    return (
        <div className="h-full flex flex-col gap-4 animate-fade-in">
            {/* Status & Actions */}
            <div className="glass-card p-5">
                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-4">
                        <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-blue-500/10 to-purple-500/10 border border-primary/10 flex items-center justify-center">
                            <Rocket size={22} className="text-primary/70" />
                        </div>
                        <div>
                            <h3 className="text-sm font-semibold mb-1">Deployment Status</h3>
                            <div className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[11px] font-semibold ${statusInfo.class}`}>
                                {statusInfo.icon}
                                <span>{statusInfo.label}</span>
                            </div>
                        </div>
                    </div>

                    <div className="flex items-center gap-2">
                        {/* Elapsed timer during deployment */}
                        {deploying && (
                            <span className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-blue-500/10 border border-blue-500/20 text-blue-400 text-[11px] font-mono font-semibold animate-pulse">
                                <Timer size={12} />
                                {formatElapsed(elapsedSeconds)}
                            </span>
                        )}

                        <button
                            onClick={fetchStatus}
                            className="p-2 rounded-lg text-muted-foreground/50 hover:text-foreground hover:bg-white/[0.04] transition-all"
                            title="Refresh status"
                        >
                            <RefreshCw size={14} />
                        </button>

                        <button
                            onClick={handleDeploy}
                            disabled={deploying || destroying}
                            className="btn-gradient flex items-center gap-2 text-xs py-2"
                        >
                            {deploying ? (
                                <>
                                    <Loader2 size={13} className="animate-spin" />
                                    <span>Deploying…</span>
                                </>
                            ) : (
                                <>
                                    <Rocket size={13} />
                                    <span>Deploy Changes</span>
                                </>
                            )}
                        </button>

                        {(status?.status === 'deployed' || status?.status === 'success') && (
                            <button
                                onClick={handleDestroy}
                                disabled={deploying || destroying}
                                className="flex items-center gap-2 text-xs py-2 px-3 rounded-lg bg-destructive/10 text-destructive border border-destructive/20 hover:bg-destructive/20 disabled:opacity-50 transition-all font-medium"
                            >
                                {destroying ? (
                                    <>
                                        <Loader2 size={13} className="animate-spin" />
                                        <span>Destroying…</span>
                                    </>
                                ) : (
                                    <>
                                        <Trash2 size={13} />
                                        <span>Destroy</span>
                                    </>
                                )}
                            </button>
                        )}
                    </div>
                </div>

                {/* Phase Progress Bar (visible during deployment) */}
                {deploying && currentPhase !== 'idle' && (
                    <div className="mt-4 flex items-center gap-2 animate-fade-in">
                        {phases.map((phase, i) => {
                            const isActive = currentPhase === phase;
                            const isPast = phaseIndex > i;
                            const isFailed = currentPhase === 'failed' && phase === phases[phaseIndex];
                            return (
                                <React.Fragment key={phase}>
                                    {i > 0 && (
                                        <div className={`flex-1 h-0.5 rounded-full transition-all duration-500 ${isPast ? 'bg-emerald-500' : 'bg-white/10'}`} />
                                    )}
                                    <div className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[10px] font-semibold transition-all duration-300 ${isActive ? 'bg-blue-500/20 text-blue-400 border border-blue-500/30' :
                                        isPast ? 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/20' :
                                            isFailed ? 'bg-red-500/15 text-red-400 border border-red-500/20' :
                                                'bg-white/5 text-white/30 border border-white/10'
                                        }`}>
                                        {isActive && <Loader2 size={10} className="animate-spin" />}
                                        {isPast && <CheckCircle2 size={10} />}
                                        {isFailed && <XCircle size={10} />}
                                        {!isActive && !isPast && !isFailed && <ChevronRight size={10} />}
                                        <span>{PHASE_LABELS[phase]}</span>
                                    </div>
                                </React.Fragment>
                            );
                        })}
                    </div>
                )}

                {/* Error from local state (request-level) */}
                {error && (
                    <div className="mt-4 p-3 bg-destructive/10 text-destructive text-xs rounded-lg border border-destructive/20 flex items-start gap-2 animate-fade-in">
                        <AlertCircle size={14} className="mt-0.5 shrink-0" />
                        <div className="space-y-1 flex-1">
                            <p className="font-semibold">Request Error</p>
                            <p className="text-destructive/80">{error}</p>
                        </div>
                    </div>
                )}

                {/* Structured Error Summary (from backend classification) */}
                {errorSummary && status?.status === 'failed' && !deploying && (
                    <div className={`mt-4 p-4 rounded-xl border animate-fade-in ${getCategoryColor(errorSummary.category)}`}>
                        <div className="flex items-start gap-3">
                            {getCategoryIcon(errorSummary.category)}
                            <div className="flex-1 space-y-2">
                                <div className="flex items-center justify-between">
                                    <span className="text-xs font-bold tracking-wider uppercase text-white/70">
                                        {errorSummary.category.replace(/_/g, ' ')}
                                    </span>
                                    <button
                                        onClick={handleCopyError}
                                        className="flex items-center gap-1 text-[10px] text-white/40 hover:text-white/70 transition-colors"
                                        title="Copy error details"
                                    >
                                        {copied ? <Check size={10} /> : <Copy size={10} />}
                                        <span>{copied ? 'Copied' : 'Copy'}</span>
                                    </button>
                                </div>
                                <p className="text-[12px] text-white/60 leading-relaxed">
                                    {errorSummary.explanation}
                                </p>
                                <div className="pt-2 border-t border-white/5">
                                    <pre className="text-[11px] text-white/40 whitespace-pre-wrap font-mono leading-relaxed">
                                        {errorSummary.fix}
                                    </pre>
                                </div>
                            </div>
                        </div>
                    </div>
                )}

                {/* Fallback: simple error from deployment record (when no details available) */}
                {!errorSummary && status?.error_message && status?.status === 'failed' && !deploying && (
                    <div className="mt-4 p-3 bg-amber-500/10 text-amber-400 text-xs rounded-lg border border-amber-500/20 flex items-start gap-2 animate-fade-in">
                        <AlertTriangle size={14} className="mt-0.5 shrink-0" />
                        <div className="space-y-1 flex-1">
                            <p className="font-semibold">Deployment Error</p>
                            <p className="text-amber-400/80 font-mono">{status.error_message}</p>
                        </div>
                        <button
                            onClick={handleCopyError}
                            className="p-1 rounded text-amber-400/40 hover:text-amber-400/80 transition-colors shrink-0"
                            title="Copy error"
                        >
                            {copied ? <Check size={12} /> : <Copy size={12} />}
                        </button>
                    </div>
                )}
            </div>

            {/* Logs */}
            <div className="flex-1 flex flex-col glass-card overflow-hidden">
                <div className="p-4 border-b border-border/30 flex items-center justify-between">
                    <div className="flex items-center gap-2">
                        <Terminal size={14} className="text-muted-foreground/50" />
                        <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground/60">
                            Deployment Logs
                        </h3>
                        {deploying && (
                            <span className="flex items-center gap-1 px-2 py-0.5 rounded-full bg-blue-500/10 text-blue-400 text-[9px] font-semibold animate-pulse">
                                <span className="w-1.5 h-1.5 rounded-full bg-blue-400 animate-pulse" />
                                LIVE
                            </span>
                        )}
                    </div>
                    {status?.started_at && (
                        <span className="text-[10px] text-muted-foreground/30 font-mono">
                            started: {status.started_at}
                            {status?.completed_at ? ` • completed: ${status.completed_at}` : ''}
                        </span>
                    )}
                </div>
                <div className="flex-1 overflow-auto bg-[#0d1117] p-4">
                    {status?.logs ? (
                        <pre className="text-[11px] leading-[1.8] font-mono whitespace-pre-wrap selection:bg-primary/30">
                            {status.logs.split('\n').map((line, i) => colorizeLogLine(line, i))}
                            <div ref={logEndRef} />
                        </pre>
                    ) : (
                        <div className="flex flex-col items-center justify-center h-full gap-3 text-white/15">
                            <Terminal size={32} />
                            <p className="text-xs">No deployment logs yet</p>
                            <p className="text-[10px] text-white/8">Click "Deploy Changes" to start a deployment</p>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
};
