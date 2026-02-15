import React, { useState, useEffect } from 'react';
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
    AlertTriangle
} from 'lucide-react';

interface Props {
    projectId: number;
}

export const DeploymentTab: React.FC<Props> = ({ projectId }) => {
    const [status, setStatus] = useState<DeploymentResponse | null>(null);
    const [loading, setLoading] = useState(true);
    const [deploying, setDeploying] = useState(false);
    const [destroying, setDestroying] = useState(false);
    const [error, setError] = useState('');

    useEffect(() => {
        fetchStatus();
    }, [projectId]);

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
        setStatus(prev => prev ? { ...prev, logs: '', status: 'running' } : null);

        try {
            const token = localStorage.getItem('token'); // Simplistic auth retrieval
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
                throw new Error(text || 'Deployment request failed');
            }

            if (!response.body) throw new Error('No response body');

            const reader = response.body.getReader();
            const decoder = new TextDecoder();

            // Initial status
            setStatus(prev => ({
                ...prev!,
                status: 'running',
                logs: 'Initializing stream...\n'
            }));

            while (true) {
                const { value, done } = await reader.read();
                if (done) break;

                const chunk = decoder.decode(value, { stream: true });
                setStatus(prev => ({
                    ...prev!,
                    logs: (prev?.logs || '') + chunk
                }));
            }

            // Stream finished - refresh full status to get final state/timestamps
            await fetchStatus();

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
        }
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

                {/* Error from local state */}
                {error && (
                    <div className="mt-4 p-3 bg-destructive/10 text-destructive text-xs rounded-lg border border-destructive/20 flex items-start gap-2 animate-fade-in">
                        <AlertCircle size={14} className="mt-0.5 shrink-0" />
                        <div className="space-y-1">
                            <p className="font-semibold">Request Error</p>
                            <p className="text-destructive/80">{error}</p>
                        </div>
                    </div>
                )}

                {/* Error from deployment record (backend) */}
                {status?.error_message && (
                    <div className="mt-4 p-3 bg-amber-500/10 text-amber-400 text-xs rounded-lg border border-amber-500/20 flex items-start gap-2 animate-fade-in">
                        <AlertTriangle size={14} className="mt-0.5 shrink-0" />
                        <div className="space-y-1">
                            <p className="font-semibold">Deployment Error</p>
                            <p className="text-amber-400/80 font-mono">{status.error_message}</p>
                        </div>
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
                        <pre className="text-[11px] leading-[1.8] text-emerald-200/60 font-mono whitespace-pre-wrap selection:bg-primary/30">
                            {status.logs}
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
