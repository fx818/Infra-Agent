import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { projectsApi } from '../api/projects';
import { deploymentApi } from '../api/deployment';
import type { ProjectResponse, DeploymentResponse } from '../types';
import {
    Server,
    CheckCircle2,
    XCircle,
    Clock,
    Loader2,
    Rocket,
    ArrowUpRight,
    Trash2,
    RefreshCw,
    AlertTriangle
} from 'lucide-react';

interface ProjectDeployment {
    project: ProjectResponse;
    deployment: DeploymentResponse | null;
}

export const Deployments: React.FC = () => {
    const [items, setItems] = useState<ProjectDeployment[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        fetchAll();
    }, []);

    const fetchAll = async () => {
        setLoading(true);
        try {
            const projects = await projectsApi.getAll();
            const results: ProjectDeployment[] = [];
            for (const project of projects) {
                try {
                    const dep = await deploymentApi.getStatus(project.id);
                    results.push({ project, deployment: dep });
                } catch {
                    results.push({ project, deployment: null });
                }
            }
            setItems(results);
        } catch (err) {
            console.error('Failed to load deployments:', err);
        } finally {
            setLoading(false);
        }
    };

    const getStatusConfig = (s: string | undefined) => {
        const map: Record<string, { icon: React.ReactNode; class: string; label: string }> = {
            success: { icon: <CheckCircle2 size={14} />, class: 'badge-success', label: 'Deployed' },
            deployed: { icon: <CheckCircle2 size={14} />, class: 'badge-success', label: 'Deployed' },
            failed: { icon: <XCircle size={14} />, class: 'badge-danger', label: 'Failed' },
            running: { icon: <Loader2 size={14} className="animate-spin" />, class: 'badge-info', label: 'Running' },
            pending: { icon: <Clock size={14} />, class: 'badge-warning', label: 'Pending' },
            destroyed: { icon: <Trash2 size={14} />, class: 'badge-danger', label: 'Destroyed' },
        };
        return map[s || ''] || { icon: <Clock size={14} />, class: 'badge-warning', label: 'Not Deployed' };
    };

    if (loading) {
        return (
            <div className="flex items-center justify-center h-full">
                <div className="flex flex-col items-center gap-3">
                    <div className="w-10 h-10 rounded-full border-2 border-primary/30 border-t-primary animate-spin" />
                    <p className="text-sm text-muted-foreground">Loading deployments…</p>
                </div>
            </div>
        );
    }

    const deployed = items.filter(i => i.deployment?.status === 'success' || i.deployment?.status === 'deployed');
    const failed = items.filter(i => i.deployment?.status === 'failed');
    const total = items.length;

    return (
        <div className="max-w-5xl mx-auto space-y-6 animate-fade-in">
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-2xl font-bold tracking-tight">Deployments</h1>
                    <p className="text-sm text-muted-foreground/60 mt-1">All deployments across your Infra</p>
                </div>
                <button
                    onClick={fetchAll}
                    className="p-2 rounded-lg text-muted-foreground/50 hover:text-foreground hover:bg-white/[0.04] transition-all"
                    title="Refresh"
                >
                    <RefreshCw size={16} />
                </button>
            </div>

            {/* Summary Stats */}
            <div className="grid grid-cols-3 gap-4">
                <div className="glass-card p-4 flex items-center gap-3">
                    <div className="w-10 h-10 rounded-xl bg-blue-500/10 flex items-center justify-center">
                        <Server size={18} className="text-blue-400" />
                    </div>
                    <div>
                        <p className="text-2xl font-bold">{total}</p>
                        <p className="text-[11px] text-muted-foreground/50">Total Projects</p>
                    </div>
                </div>
                <div className="glass-card p-4 flex items-center gap-3">
                    <div className="w-10 h-10 rounded-xl bg-emerald-500/10 flex items-center justify-center">
                        <CheckCircle2 size={18} className="text-emerald-400" />
                    </div>
                    <div>
                        <p className="text-2xl font-bold">{deployed.length}</p>
                        <p className="text-[11px] text-muted-foreground/50">Active Deployments</p>
                    </div>
                </div>
                <div className="glass-card p-4 flex items-center gap-3">
                    <div className="w-10 h-10 rounded-xl bg-red-500/10 flex items-center justify-center">
                        <AlertTriangle size={18} className="text-red-400" />
                    </div>
                    <div>
                        <p className="text-2xl font-bold">{failed.length}</p>
                        <p className="text-[11px] text-muted-foreground/50">Failed</p>
                    </div>
                </div>
            </div>

            {/* Deployment List */}
            {items.length === 0 ? (
                <div className="glass-card p-16 text-center">
                    <div className="w-20 h-20 rounded-2xl bg-gradient-to-br from-blue-500/10 to-purple-500/10 border border-primary/10 flex items-center justify-center mx-auto mb-6">
                        <Server size={36} className="text-primary/30" />
                    </div>
                    <h3 className="text-lg font-semibold mb-1.5">No Infra Generated Yet</h3>
                    <p className="text-xs text-muted-foreground/50 max-w-[300px] mx-auto leading-relaxed">
                        Create a project and deploy its architecture to see it listed here.
                    </p>
                </div>
            ) : (
                <div className="space-y-3">
                    {items.map(({ project, deployment }) => {
                        const statusConfig = getStatusConfig(deployment?.status);
                        return (
                            <Link
                                key={project.id}
                                to={`/projects/${project.id}`}
                                className="glass-card p-4 flex items-center gap-4 group hover:border-primary/20 transition-all cursor-pointer block"
                            >
                                <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-blue-500/10 to-purple-500/10 border border-primary/10 flex items-center justify-center shrink-0">
                                    <Rocket size={18} className="text-primary/60" />
                                </div>
                                <div className="flex-1 min-w-0">
                                    <div className="flex items-center gap-2">
                                        <h3 className="text-sm font-semibold truncate group-hover:text-primary transition-colors">{project.name}</h3>
                                        <div className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold ${statusConfig.class}`}>
                                            {statusConfig.icon}
                                            <span>{statusConfig.label}</span>
                                        </div>
                                    </div>
                                    <div className="flex items-center gap-4 mt-1">
                                        <span className="text-[11px] text-muted-foreground/40">{project.region || 'us-east-1'}</span>
                                        {deployment?.completed_at && (
                                            <span className="text-[11px] text-muted-foreground/30">
                                                Last: {new Date(deployment.completed_at).toLocaleString()}
                                            </span>
                                        )}
                                        {deployment?.error_message && (
                                            <span className="text-[11px] text-red-400/60 truncate max-w-[300px]">
                                                {deployment.error_message}
                                            </span>
                                        )}
                                    </div>
                                </div>
                                <ArrowUpRight size={16} className="text-muted-foreground/20 group-hover:text-primary/60 transition-colors shrink-0" />
                            </Link>
                        );
                    })}
                </div>
            )}
        </div>
    );
};
