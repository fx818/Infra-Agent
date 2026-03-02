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
    AlertTriangle,
    Activity
} from 'lucide-react';

interface ProjectDeployment {
    project: ProjectResponse;
    deployment: DeploymentResponse | null;
}

export const Deployments: React.FC = () => {
    const [items, setItems] = useState<ProjectDeployment[]>([]);
    const [loading, setLoading] = useState(true);
    const [activeFilters, setActiveFilters] = useState<Set<string>>(new Set());

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
            partial_deployed: { icon: <AlertTriangle size={14} />, class: 'bg-amber-500/15 text-amber-400 border border-amber-500/30', label: 'Partial Deploy' },
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

    const getFilterGroup = (item: ProjectDeployment): string => {
        const s = item.deployment?.status || item.project.status || '';
        if (s === 'success' || s === 'deployed') return 'Deployed';
        if (s === 'failed') return 'Failed';
        if (s === 'partial_deployed') return 'Partial';
        if (s === 'destroyed') return 'Destroyed';
        return 'Inactive';
    };

    const deployed = items.filter(i => getFilterGroup(i) === 'Deployed');
    const failed = items.filter(i => getFilterGroup(i) === 'Failed');
    const partial = items.filter(i => getFilterGroup(i) === 'Partial');
    const destroyedItems = items.filter(i => getFilterGroup(i) === 'Destroyed');
    const inactive = items.filter(i => getFilterGroup(i) === 'Inactive');
    const total = items.length;

    const statCards = [
        { key: 'Total', label: 'Total', value: total, icon: <Server size={18} className="text-blue-400" />, bg: 'bg-blue-500/10', ring: 'ring-blue-500/40' },
        { key: 'Deployed', label: 'Deployed', value: deployed.length, icon: <CheckCircle2 size={18} className="text-emerald-400" />, bg: 'bg-emerald-500/10', ring: 'ring-emerald-500/40' },
        { key: 'Failed', label: 'Failed', value: failed.length, icon: <AlertTriangle size={18} className="text-red-400" />, bg: 'bg-red-500/10', ring: 'ring-red-500/40' },
        { key: 'Partial', label: 'Partial', value: partial.length, icon: <Activity size={18} className="text-amber-400" />, bg: 'bg-amber-500/10', ring: 'ring-amber-500/40' },
        { key: 'Destroyed', label: 'Destroyed', value: destroyedItems.length, icon: <Trash2 size={18} className="text-rose-400" />, bg: 'bg-rose-500/10', ring: 'ring-rose-500/40' },
        { key: 'Inactive', label: 'Inactive', value: inactive.length, icon: <Clock size={18} className="text-slate-400" />, bg: 'bg-slate-500/10', ring: 'ring-slate-500/40' },
    ];

    const toggleFilter = (key: string) => {
        if (key === 'Total') { setActiveFilters(new Set()); return; }
        setActiveFilters(prev => {
            const next = new Set(prev);
            if (next.has(key)) next.delete(key); else next.add(key);
            return next;
        });
    };

    const filteredItems = activeFilters.size === 0 ? items : items.filter(i => activeFilters.has(getFilterGroup(i)));

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
            <div className="grid grid-cols-6 gap-3">
                {statCards.map(card => {
                    const isActive = card.key === 'Total' ? activeFilters.size === 0 : activeFilters.has(card.key);
                    return (
                        <div
                            key={card.key}
                            onClick={() => toggleFilter(card.key)}
                            className={`glass-card p-3 flex items-center gap-2.5 cursor-pointer transition-all hover:bg-white/[0.03] select-none ${isActive ? `ring-1 ${card.ring} bg-white/[0.02]` : 'opacity-70 hover:opacity-100'
                                }`}
                        >
                            <div className={`w-8 h-8 rounded-lg ${card.bg} flex items-center justify-center shrink-0`}>
                                {card.icon}
                            </div>
                            <div>
                                <p className="text-lg font-bold leading-none">{card.value}</p>
                                <p className="text-[10px] text-muted-foreground/50 mt-0.5">{card.label}</p>
                            </div>
                        </div>
                    );
                })}
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
                    {filteredItems.map(({ project, deployment }) => {
                        const statusConfig = getStatusConfig(deployment?.status);
                        return (
                            <Link
                                key={project.id}
                                to={`/projects/${project.id}`}
                                className="glass-card p-4 group hover:border-primary/20 transition-all cursor-pointer block"
                            >
                                <div className="flex items-center gap-4">
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
                                        </div>
                                    </div>
                                    <ArrowUpRight size={16} className="text-muted-foreground/20 group-hover:text-primary/60 transition-colors shrink-0" />
                                </div>
                                {deployment?.error_message && (
                                    <div className="mt-2 flex items-start gap-1.5 px-2.5 py-1.5 rounded-lg bg-red-500/[0.08] border border-red-500/15">
                                        <AlertTriangle size={11} className="text-red-400/70 mt-0.5 shrink-0" />
                                        <span className="text-[11px] text-red-400/70 leading-relaxed line-clamp-2">
                                            {deployment.error_message}
                                        </span>
                                    </div>
                                )}
                            </Link>
                        );
                    })}
                </div>
            )}
        </div>
    );
};
