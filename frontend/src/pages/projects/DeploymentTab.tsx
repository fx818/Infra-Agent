import React, { useState, useEffect, useRef, useCallback } from 'react';
import { flushSync, createPortal } from 'react-dom';
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
    Timer,
    Key,
    Download,
    Server,
    RotateCcw,
    Maximize2,
    Minimize2
} from 'lucide-react';
import type { EC2KeyInfo } from '../../api/deployment';

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
    if (lower.includes('deployment successful') || lower.includes('provisioning complete') || lower.includes('boto3 deployment finished: success') || lower.includes('destruction complete') || lower.includes('phase 2/2 complete:')) return 'complete';
    if (lower.includes('starting aws resource provisioning') || lower.includes('starting boto3 deployment') || lower.includes('phase 2/2: starting fresh')) return 'apply';
    if (lower.includes('starting aws resource destruction') || lower.includes('starting boto3 destroy') || lower.includes('phase 1/2: destroying')) return 'destroy';
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
    // Success / creation lines (including LLM-repaired)
    if (trimmed.includes('\u2713 Created') || trimmed.includes('\u2713 Repaired') || trimmed.includes('\u2713 Destroyed') || trimmed.includes('is ready') || trimmed.includes('Provisioning complete') || trimmed.includes('Destruction complete') || trimmed.includes('[AUTO-ROLLBACK] \u2713')) {
        return <span key={idx} className="text-emerald-400 font-medium">{line}{'\n'}</span>;
    }
    // Failure lines — match both ✗ glyph and plain ASCII FAILED:
    if (trimmed.includes('\u2717') || trimmed.includes('FAILED:') || trimmed.includes('Repair attempt also failed')) {
        return <span key={idx} className="text-red-400 font-semibold">{line}{'\n'}</span>;
    }
    // LLM repair attempt lines
    if (trimmed.includes('LLM-assisted repair') || trimmed.includes('LLM could not')) {
        return <span key={idx} className="text-purple-400 italic">{line}{'\n'}</span>;
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
    const [redeploying, setRedeploying] = useState(false);
    const [showRedeployConfirm, setShowRedeployConfirm] = useState(false);
    const [isLogsFullScreen, setIsLogsFullScreen] = useState(false);
    const toggleLogsFullScreen = useCallback(() => setIsLogsFullScreen(v => !v), []);
    const [error, setError] = useState('');
    const [copied, setCopied] = useState(false);
    const [elapsedSeconds, setElapsedSeconds] = useState(0);
    const [liveLogs, setLiveLogs] = useState('');   // live-streamed log content (cleared after stream ends)
    const [ec2Keys, setEc2Keys] = useState<EC2KeyInfo[]>([]);
    const [copiedSsh, setCopiedSsh] = useState<string | null>(null);
    const logEndRef = useRef<HTMLDivElement>(null);
    const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

    useEffect(() => {
        fetchStatus();
        fetchEC2Keys();
    }, [projectId]);

    // Escape key exits fullscreen log view
    useEffect(() => {
        const handler = (e: KeyboardEvent) => {
            if (e.key === 'Escape' && isLogsFullScreen) setIsLogsFullScreen(false);
        };
        window.addEventListener('keydown', handler);
        return () => window.removeEventListener('keydown', handler);
    }, [isLogsFullScreen]);

    // Auto-scroll to bottom when logs update during deployment
    useEffect(() => {
        if ((deploying || redeploying) && logEndRef.current) {
            logEndRef.current.scrollIntoView({ behavior: 'smooth' });
        }
    }, [liveLogs, status?.logs, deploying, redeploying]);

    // Timer during deployment
    useEffect(() => {
        const active = deploying || redeploying;
        if (active) {
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
    }, [deploying, redeploying]);

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

    const fetchEC2Keys = async () => {
        try {
            const data = await deploymentApi.getEC2Keys(projectId);
            setEc2Keys(data.keys || []);
        } catch {
            // No EC2 keys found — silently ignore
        }
    };

    const handleDownloadPem = async (keyPairName: string) => {
        try {
            const token = localStorage.getItem('token');
            const base = (import.meta.env.VITE_API_URL as string | undefined) || 'https://arcaiengineer.in';
            // const base = (import.meta.env.VITE_API_URL as string | undefined) || 'http://localhost:8000';
            const resp = await fetch(`${base}/projects/${projectId}/ec2-key/${keyPairName}/download`, {
                headers: { Authorization: `Bearer ${token}` },
            });
            if (!resp.ok) return;
            const blob = await resp.blob();
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `${keyPairName}.pem`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
        } catch (err) {
            console.error('PEM download failed:', err);
        }
    };

    const handleCopySsh = (cmd: string) => {
        navigator.clipboard.writeText(cmd).then(() => {
            setCopiedSsh(cmd);
            setTimeout(() => setCopiedSsh(null), 2000);
        });
    };

    const handleDeploy = async () => {
        setDeploying(true);
        setError('');
        setLiveLogs('');  // clear live log pane
        // Clear previous logs when starting new deploy
        setStatus(prev => prev ? { ...prev, logs: '', status: 'running', error_message: undefined, error_details: undefined } : null);

        try {
            const token = localStorage.getItem('token');
            // const response = await fetch(`${import.meta.env.VITE_API_URL || 'https://3.92.236.1'}/projects/${projectId}/deploy/stream`, {
            // const response = await fetch(`${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/projects/${projectId}/deploy/stream`, {
            const response = await fetch(`${import.meta.env.VITE_API_URL || 'https://arcaiengineer.in'}/projects/${projectId}/deploy/stream`, {
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
                    // flushSync forces React to render this update immediately
                    // instead of batching it — required for live log streaming
                    flushSync(() => {
                        setLiveLogs(prev => prev + newContent);
                    });
                }
            }

            // Stream finished - refresh full status to get final state/timestamps
            await fetchStatus();
            await fetchEC2Keys();
            await onStatusChange?.();

        } catch (err: any) {
            const detail = err.message || 'Deployment failed';
            setError(detail);
            console.error('Deploy error:', err);
        } finally {
            // Batch liveLogs clear with deploying=false so React renders
            // status.logs instead of briefly showing the empty-logs placeholder.
            setLiveLogs('');
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

    const handleRedeploy = async () => {
        setShowRedeployConfirm(false);
        setRedeploying(true);
        setError('');
        setLiveLogs('');
        setStatus(prev => prev ? { ...prev, logs: '', status: 'running', error_message: undefined, error_details: undefined } : null);

        try {
            const token = localStorage.getItem('token');
            // const response = await fetch(`${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/projects/${projectId}/redeploy/stream`, {
            const response = await fetch(`${import.meta.env.VITE_API_URL || 'https://arcaiengineer.in'}/projects/${projectId}/redeploy/stream`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
            });

            if (!response.ok) {
                const text = await response.text();
                let detail = 'Redeploy request failed';
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

            while (true) {
                const { value, done } = await reader.read();
                if (done) break;

                sseBuffer += decoder.decode(value, { stream: true });
                const parts = sseBuffer.split('\n\n');
                sseBuffer = parts.pop() ?? '';

                let newContent = '';
                for (const part of parts) {
                    for (const line of part.split('\n')) {
                        if (line.startsWith('data: ')) {
                            newContent += line.slice(6) + '\n';
                        }
                    }
                }
                if (newContent) {
                    flushSync(() => {
                        setLiveLogs(prev => prev + newContent);
                    });
                }
            }

            await fetchStatus();
            await fetchEC2Keys();
            await onStatusChange?.();

        } catch (err: any) {
            const detail = err.message || 'Redeploy failed';
            setError(detail);
            console.error('Redeploy error:', err);
        } finally {
            setLiveLogs('');
            setRedeploying(false);
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
    const isActiveDeployment = deploying || redeploying;
    const currentPhase = isActiveDeployment ? detectPhase(liveLogs || status?.logs || '') : 'idle';
    const errorSummary = parseErrorSummary(status?.error_details);

    // Phase pipeline indicators — redeploy shows destroy→apply→complete
    const phases: DeployPhase[] = redeploying ? ['destroy', 'apply', 'complete'] : ['init', 'apply', 'complete'];
    const phaseIndex = phases.indexOf(currentPhase);

    return (
        <div className="flex flex-col gap-4 animate-fade-in pb-2">
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
                        {/* Elapsed timer during deployment / redeploy */}
                        {isActiveDeployment && (
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
                            disabled={isActiveDeployment || destroying}
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

                        {/* Redeploy button — visible whenever a deployment record exists */}
                        {status && status.status !== 'no_deployments' && (
                            <button
                                onClick={() => setShowRedeployConfirm(true)}
                                disabled={isActiveDeployment || destroying}
                                className="flex items-center gap-2 text-xs py-2 px-3 rounded-lg bg-amber-500/10 text-amber-400 border border-amber-500/20 hover:bg-amber-500/20 disabled:opacity-50 transition-all font-medium"
                                title="Destroy existing infrastructure and redeploy from scratch"
                            >
                                {redeploying ? (
                                    <>
                                        <Loader2 size={13} className="animate-spin" />
                                        <span>Redeploying…</span>
                                    </>
                                ) : (
                                    <>
                                        <RotateCcw size={13} />
                                        <span>Redeploy</span>
                                    </>
                                )}
                            </button>
                        )}

                        {(status?.status === 'deployed' || status?.status === 'success') && (
                            <button
                                onClick={handleDestroy}
                                disabled={isActiveDeployment || destroying}
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

                {/* Phase Progress Bar (visible during deployment or redeploy) */}
                {isActiveDeployment && currentPhase !== 'idle' && (
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
                {!errorSummary && status?.error_message && status?.status === 'failed' && !isActiveDeployment && (
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
            <div className="flex flex-col glass-card overflow-hidden" style={{ height: 'clamp(340px, 50vh, 600px)' }}>
                <div className="p-4 border-b border-border/30 flex items-center justify-between">
                    <div className="flex items-center gap-2">
                        <Terminal size={14} className="text-muted-foreground/50" />
                        <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground/60">
                            Deployment Logs
                        </h3>
                        {isActiveDeployment && (
                            <span className="flex items-center gap-1 px-2 py-0.5 rounded-full bg-blue-500/10 text-blue-400 text-[9px] font-semibold animate-pulse">
                                <span className="w-1.5 h-1.5 rounded-full bg-blue-400 animate-pulse" />
                                LIVE
                            </span>
                        )}
                    </div>
                    <div className="flex items-center gap-3">
                        {status?.started_at && (
                            <span className="text-[10px] text-muted-foreground/30 font-mono">
                                started: {status.started_at}
                                {status?.completed_at ? ` • completed: ${status.completed_at}` : ''}
                            </span>
                        )}
                        <button
                            onClick={toggleLogsFullScreen}
                            className="p-1.5 rounded-lg text-muted-foreground/40 hover:text-foreground hover:bg-white/[0.04] transition-all"
                            title="Full Screen Logs"
                        >
                            <Maximize2 size={13} />
                        </button>
                    </div>
                </div>
                <div className="flex-1 overflow-auto bg-[#0d1117] p-4">
                    {/* During streaming show liveLogs; afterwards show persisted status.logs */}
                    {(isActiveDeployment && liveLogs ? liveLogs : status?.logs) ? (
                        <pre className="text-[11px] leading-[1.8] font-mono whitespace-pre-wrap selection:bg-primary/30">
                            {(isActiveDeployment && liveLogs ? liveLogs : status!.logs!).split('\n').map((line, i) => colorizeLogLine(line, i))}
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

            {/* Fullscreen log portal */}
            {isLogsFullScreen && createPortal(
                <div style={{
                    position: 'fixed',
                    inset: 0,
                    zIndex: 99999,
                    background: '#0d1117',
                    display: 'flex',
                    flexDirection: 'column',
                }}>
                    {/* Header */}
                    <div style={{
                        padding: '12px 20px',
                        borderBottom: '1px solid rgba(255,255,255,0.06)',
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center',
                        background: 'rgba(13,17,23,0.8)',
                        backdropFilter: 'blur(20px)',
                        flexShrink: 0,
                    }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                            <div style={{ padding: '6px', borderRadius: '8px', background: 'rgba(99,102,241,0.12)', display: 'flex' }}>
                                <Terminal size={16} color="#6366f1" />
                            </div>
                            <div>
                                <h2 style={{ fontSize: '13px', fontWeight: 700, color: '#f1f5f9', margin: 0 }}>Deployment Logs</h2>
                                <p style={{ fontSize: '11px', color: 'rgba(255,255,255,0.3)', margin: 0 }}>
                                    {isActiveDeployment ? 'Streaming live…' : (status?.completed_at ? `Completed: ${status.completed_at}` : 'Full Screen View')}
                                </p>
                            </div>
                            {isActiveDeployment && (
                                <span style={{
                                    display: 'flex', alignItems: 'center', gap: '5px',
                                    padding: '2px 8px', borderRadius: '999px',
                                    background: 'rgba(59,130,246,0.12)',
                                    border: '1px solid rgba(59,130,246,0.25)',
                                    color: '#60a5fa', fontSize: '9px', fontWeight: 700,
                                }}>
                                    <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: '#60a5fa', display: 'inline-block', animation: 'pulse 1s infinite' }} />
                                    LIVE
                                </span>
                            )}
                        </div>
                        <button
                            onClick={toggleLogsFullScreen}
                            style={{
                                display: 'flex', alignItems: 'center', gap: '6px',
                                padding: '6px 14px', borderRadius: '8px',
                                background: 'rgba(255,255,255,0.05)',
                                border: '1px solid rgba(255,255,255,0.1)',
                                color: 'rgba(255,255,255,0.7)',
                                fontSize: '12px', fontWeight: 600, cursor: 'pointer',
                            }}
                        >
                            <Minimize2 size={13} />
                            <span>Exit Full Screen</span>
                        </button>
                    </div>
                    {/* Log content */}
                    <div style={{ flex: 1, overflow: 'auto', padding: '20px 24px', fontFamily: 'monospace' }}>
                        {(isActiveDeployment && liveLogs ? liveLogs : status?.logs) ? (
                            <pre style={{ fontSize: '12px', lineHeight: 1.9, whiteSpace: 'pre-wrap', margin: 0 }}>
                                {(isActiveDeployment && liveLogs ? liveLogs : status!.logs!).split('\n').map((line, i) => colorizeLogLine(line, i))}
                                <div ref={logEndRef} />
                            </pre>
                        ) : (
                            <div style={{ height: '100%', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: '12px', color: 'rgba(255,255,255,0.12)' }}>
                                <Terminal size={40} />
                                <p style={{ fontSize: '13px', margin: 0 }}>No deployment logs yet</p>
                            </div>
                        )}
                    </div>
                </div>,
                document.body
            )}

            {/* EC2 Connection Info — shown whenever EC2 instances with key pairs are deployed */}
            {ec2Keys.length > 0 && (
                <div className="glass-card p-5 animate-fade-in">
                    <div className="flex items-center gap-2 mb-4">
                        <Server size={15} className="text-blue-400" />
                        <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground/70">
                            EC2 Connection Info
                        </h3>
                        <span className="ml-auto text-[10px] text-muted-foreground/40 font-mono">
                            {ec2Keys.length} instance{ec2Keys.length !== 1 ? 's' : ''}
                        </span>
                    </div>
                    <div className="space-y-3">
                        {ec2Keys.map((k) => {
                            const host = k.public_dns || k.public_ip || '<public-ip-once-running>';
                            const sshAmzn = `ssh -i "${k.key_pair_name}.pem" ec2-user@${host}`;
                            const sshUbuntu = `ssh -i "${k.key_pair_name}.pem" ubuntu@${host}`;
                            return (
                                <div key={k.key_pair_name} className="p-4 rounded-xl bg-[#0d1117] border border-border/30 space-y-3">
                                    {/* Header row: key name + instance ID + download button */}
                                    <div className="flex items-center justify-between flex-wrap gap-2">
                                        <div className="flex items-center gap-2">
                                            <Key size={13} className="text-yellow-400" />
                                            <span className="text-xs font-semibold text-white/80 font-mono">{k.key_pair_name}</span>
                                            {k.instance_id && (
                                                <span className="text-[10px] text-white/30 font-mono">({k.instance_id})</span>
                                            )}
                                        </div>
                                        {k.has_pem ? (
                                            <button
                                                onClick={() => handleDownloadPem(k.key_pair_name)}
                                                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-emerald-500/10 border border-emerald-500/25 text-emerald-400 text-[11px] font-semibold hover:bg-emerald-500/20 transition-all"
                                                title="Download PEM private key"
                                            >
                                                <Download size={12} />
                                                Download .pem
                                            </button>
                                        ) : (
                                            <span className="text-[10px] text-amber-400/60 italic">PEM unavailable — AWS key creation may have failed</span>
                                        )}
                                    </div>

                                    {/* Public IP — prominent dedicated row */}
                                    <div className="flex items-center gap-3 px-3 py-2.5 rounded-lg bg-blue-500/5 border border-blue-500/15">
                                        <span className="text-[10px] text-white/40 font-medium uppercase tracking-wide w-20 shrink-0">Public IP</span>
                                        {k.public_ip ? (
                                            <div className="flex items-center gap-2 flex-1">
                                                <span className="font-mono text-sm font-bold text-blue-300">{k.public_ip}</span>
                                                <button
                                                    onClick={() => { navigator.clipboard.writeText(k.public_ip); setCopiedSsh(k.public_ip); setTimeout(() => setCopiedSsh(null), 2000); }}
                                                    className="p-1 rounded text-white/30 hover:text-white/70 transition-colors"
                                                    title="Copy IP"
                                                >
                                                    {copiedSsh === k.public_ip ? <Check size={11} className="text-emerald-400" /> : <Copy size={11} />}
                                                </button>
                                            </div>
                                        ) : (
                                            <span className="text-[11px] text-amber-400/70 italic flex items-center gap-1.5">
                                                Pending — check{' '}
                                                <a
                                                    href="https://console.aws.amazon.com/ec2/home#Instances"
                                                    target="_blank"
                                                    rel="noopener noreferrer"
                                                    className="text-blue-400 hover:underline"
                                                >
                                                    AWS EC2 Console
                                                </a>
                                                {' '}once instance is running
                                            </span>
                                        )}
                                        {k.public_dns && (
                                            <span className="text-[10px] text-white/25 font-mono truncate max-w-[260px]" title={k.public_dns}>{k.public_dns}</span>
                                        )}
                                    </div>

                                    {/* SSH commands */}
                                    <div className="space-y-2">
                                        {[{ label: 'Amazon Linux / AL2', cmd: sshAmzn }, { label: 'Ubuntu', cmd: sshUbuntu }].map(({ label, cmd }) => (
                                            <div key={label} className="group flex items-center gap-2">
                                                <span className="text-[10px] text-white/30 w-28 shrink-0">{label}</span>
                                                <code className="flex-1 text-[11px] font-mono text-cyan-300/80 bg-white/5 px-3 py-1.5 rounded-lg border border-white/5 truncate">
                                                    {cmd}
                                                </code>
                                                <button
                                                    onClick={() => handleCopySsh(cmd)}
                                                    className="shrink-0 p-1.5 rounded text-white/30 hover:text-white/70 transition-colors"
                                                    title="Copy SSH command"
                                                >
                                                    {copiedSsh === cmd ? <Check size={12} className="text-emerald-400" /> : <Copy size={12} />}
                                                </button>
                                            </div>
                                        ))}
                                    </div>
                                    {/* chmod reminder */}
                                    {k.has_pem && (
                                        <p className="text-[10px] text-amber-400/60 flex items-center gap-1.5">
                                            <span className="font-bold">!</span>
                                            Run <code className="font-mono bg-white/5 px-1 rounded">chmod 400 {k.key_pair_name}.pem</code> before connecting
                                        </p>
                                    )}
                                </div>
                            );
                        })}
                    </div>
                </div>
            )}

            {/* ── Redeploy Confirmation Dialog ─────────────────────────── */}
            {showRedeployConfirm && createPortal(
                <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fade-in">
                    <div className="glass-card w-full max-w-md p-6 space-y-4 border border-amber-500/30 shadow-2xl">
                        <div className="flex items-center gap-3">
                            <div className="w-10 h-10 rounded-xl bg-amber-500/10 border border-amber-500/20 flex items-center justify-center shrink-0">
                                <RotateCcw size={20} className="text-amber-400" />
                            </div>
                            <div>
                                <h3 className="text-sm font-bold text-white">Redeploy Infrastructure?</h3>
                                <p className="text-[11px] text-muted-foreground/60 mt-0.5">This action cannot be undone</p>
                            </div>
                        </div>

                        <div className="p-3 rounded-xl bg-amber-500/5 border border-amber-500/20 space-y-2">
                            <p className="text-[12px] text-amber-300/90 font-medium flex items-center gap-2">
                                <AlertTriangle size={13} />
                                What will happen:
                            </p>
                            <ol className="list-decimal list-inside space-y-1 text-[11px] text-white/60 pl-1">
                                <li>All existing AWS resources will be <span className="text-red-400 font-semibold">permanently destroyed</span></li>
                                <li>Fresh infrastructure will be provisioned from the current architecture</li>
                            </ol>
                        </div>

                        <p className="text-[11px] text-white/40">
                            Only proceed if you intend to replace all existing cloud resources for this project.
                        </p>

                        <div className="flex items-center gap-2 pt-1">
                            <button
                                onClick={() => setShowRedeployConfirm(false)}
                                className="flex-1 py-2 px-4 rounded-lg text-xs font-medium bg-white/5 text-white/60 hover:bg-white/10 border border-white/10 transition-all"
                            >
                                Cancel
                            </button>
                            <button
                                onClick={handleRedeploy}
                                className="flex-1 py-2 px-4 rounded-lg text-xs font-bold bg-amber-500/20 text-amber-300 hover:bg-amber-500/30 border border-amber-500/30 transition-all flex items-center justify-center gap-2"
                            >
                                <RotateCcw size={13} />
                                Delete & Redeploy
                            </button>
                        </div>
                    </div>
                </div>,
                document.body
            )}
        </div>
    );
};
