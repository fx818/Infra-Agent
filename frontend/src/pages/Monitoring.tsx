import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { projectsApi } from '../api/projects';
import { deploymentApi } from '../api/deployment';
import type { ProjectResponse, DeploymentResponse } from '../types';
import {
    Activity,
    CheckCircle2,
    AlertTriangle,
    ArrowUpRight,
    Zap,
    Database,
    Globe,
    Server,
    RefreshCw,
    Trash2,
    Clock
} from 'lucide-react';

interface ProjectHealth {
    project: ProjectResponse;
    deployment: DeploymentResponse | null;
}

export const Monitoring: React.FC = () => {
    const [items, setItems] = useState<ProjectHealth[]>([]);
    const [loading, setLoading] = useState(true);
    const [activeFilters, setActiveFilters] = useState<Set<string>>(new Set());

    useEffect(() => {
        fetchAll();
    }, []);

    const fetchAll = async () => {
        setLoading(true);
        try {
            const projects = await projectsApi.getAll();
            const results: ProjectHealth[] = [];
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
            console.error('Failed to load data:', err);
        } finally {
            setLoading(false);
        }
    };

    if (loading) {
        return (
            <div className="flex items-center justify-center h-full">
                <div className="flex flex-col items-center gap-3">
                    <div className="w-10 h-10 rounded-full border-2 border-primary/30 border-t-primary animate-spin" />
                    <p className="text-sm text-muted-foreground">Loading monitoring data…</p>
                </div>
            </div>
        );
    }

    const getStatus = (item: ProjectHealth) => item.deployment?.status || item.project.status || '';

    const getFilterGroup = (item: ProjectHealth): string => {
        const s = getStatus(item);
        if (s === 'success' || s === 'deployed') return 'Deployed';
        if (s === 'failed') return 'Failed';
        if (s === 'partial_deployed') return 'Partial';
        if (s === 'destroyed') return 'Destroyed';
        return 'Inactive';
    };

    const deployed = items.filter(i => getFilterGroup(i) === 'Deployed');
    const failed = items.filter(i => getFilterGroup(i) === 'Failed');
    const partial = items.filter(i => getFilterGroup(i) === 'Partial');
    const destroyed = items.filter(i => getFilterGroup(i) === 'Destroyed');
    const inactive = items.filter(i => getFilterGroup(i) === 'Inactive');
    const total = items.length;

    const statCards = [
        { key: 'Total', label: 'Total', value: total, icon: <Server size={18} className="text-blue-400" />, bg: 'bg-blue-500/10', ring: 'ring-blue-500/40' },
        { key: 'Deployed', label: 'Deployed', value: deployed.length, icon: <CheckCircle2 size={18} className="text-emerald-400" />, bg: 'bg-emerald-500/10', ring: 'ring-emerald-500/40' },
        { key: 'Failed', label: 'Failed', value: failed.length, icon: <AlertTriangle size={18} className="text-red-400" />, bg: 'bg-red-500/10', ring: 'ring-red-500/40' },
        { key: 'Partial', label: 'Partial', value: partial.length, icon: <Activity size={18} className="text-amber-400" />, bg: 'bg-amber-500/10', ring: 'ring-amber-500/40' },
        { key: 'Destroyed', label: 'Destroyed', value: destroyed.length, icon: <Trash2 size={18} className="text-rose-400" />, bg: 'bg-rose-500/10', ring: 'ring-rose-500/40' },
        { key: 'Inactive', label: 'Inactive', value: inactive.length, icon: <Clock size={18} className="text-slate-400" />, bg: 'bg-slate-500/10', ring: 'ring-slate-500/40' },
    ];

    const toggleFilter = (key: string) => {
        if (key === 'Total') {
            setActiveFilters(new Set());
            return;
        }
        setActiveFilters(prev => {
            const next = new Set(prev);
            if (next.has(key)) next.delete(key);
            else next.add(key);
            return next;
        });
    };

    const filteredItems = activeFilters.size === 0
        ? items
        : items.filter(i => activeFilters.has(getFilterGroup(i)));

    return (
        <div className="max-w-5xl mx-auto space-y-6 animate-fade-in">
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-2xl font-bold tracking-tight">Monitoring</h1>
                    <p className="text-sm text-muted-foreground/60 mt-1">System-wide infrastructure health and metrics</p>
                </div>
                <button
                    onClick={fetchAll}
                    className="p-2 rounded-lg text-muted-foreground/50 hover:text-foreground hover:bg-white/[0.04] transition-all"
                    title="Refresh"
                >
                    <RefreshCw size={16} />
                </button>
            </div>

            {/* Health Overview */}
            <div className="grid grid-cols-6 gap-3">
                {statCards.map(card => {
                    const isActive = card.key === 'Total'
                        ? activeFilters.size === 0
                        : activeFilters.has(card.key);
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

            {/* Project Health List */}
            {items.length === 0 ? (
                <div className="glass-card p-16 text-center">
                    <div className="w-20 h-20 rounded-2xl bg-gradient-to-br from-green-500/10 to-teal-500/10 border border-green-500/10 flex items-center justify-center mx-auto mb-6">
                        <Activity size={36} className="text-green-500/30" />
                    </div>
                    <h3 className="text-lg font-semibold mb-1.5">No Infra Architecture to Monitor</h3>
                    <p className="text-xs text-muted-foreground/50 max-w-[300px] mx-auto leading-relaxed">
                        Create and deploy a project to start monitoring infrastructure health.
                    </p>
                </div>
            ) : (
                <div className="space-y-3">
                    {filteredItems.map(({ project, deployment }) => {
                        const status = deployment?.status || project.status || '';
                        const isDeployed = status === 'success' || status === 'deployed';
                        const isFailed = status === 'failed';
                        const isPartial = status === 'partial_deployed';
                        const isDestroyed = status === 'destroyed';

                        const iconBg = isDeployed ? 'bg-emerald-500/10'
                            : isFailed ? 'bg-red-500/10'
                                : isPartial ? 'bg-amber-500/10'
                                    : isDestroyed ? 'bg-red-500/10'
                                        : 'bg-white/[0.04]';

                        const iconEl = isDeployed ? <CheckCircle2 size={18} className="text-emerald-400" />
                            : isFailed ? <AlertTriangle size={18} className="text-red-400" />
                                : isPartial ? <AlertTriangle size={18} className="text-amber-400" />
                                    : isDestroyed ? <AlertTriangle size={18} className="text-red-400" />
                                        : <Activity size={18} className="text-muted-foreground/30" />;

                        const badgeClass = isDeployed ? 'badge-success'
                            : isFailed ? 'badge-danger'
                                : isPartial ? 'bg-amber-500/15 text-amber-400 border border-amber-500/30'
                                    : isDestroyed ? 'badge-danger'
                                        : 'badge-warning';

                        const badgeLabel = isDeployed ? 'Healthy'
                            : isFailed ? 'Error'
                                : isPartial ? 'Partial'
                                    : isDestroyed ? 'Destroyed'
                                        : 'Inactive';
                        return (
                            <Link
                                key={project.id}
                                to={`/projects/${project.id}`}
                                className="glass-card p-4 flex items-center gap-4 group hover:border-primary/20 transition-all cursor-pointer block"
                            >
                                <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${iconBg}`}>
                                    {iconEl}
                                </div>
                                <div className="flex-1 min-w-0">
                                    <div className="flex items-center gap-2">
                                        <h3 className="text-sm font-semibold truncate group-hover:text-primary transition-colors">{project.name}</h3>
                                        <span className={`px-2 py-0.5 rounded-full text-[10px] font-semibold ${badgeClass}`}>
                                            {badgeLabel}
                                        </span>
                                    </div>
                                    <div className="flex items-center gap-4 mt-1">
                                        <span className="text-[11px] text-muted-foreground/40">{project.region || 'us-east-1'}</span>
                                        {deployment?.completed_at && (
                                            <span className="text-[11px] text-muted-foreground/30">
                                                Last check: {new Date(deployment.completed_at).toLocaleString()}
                                            </span>
                                        )}
                                    </div>
                                </div>
                                <div className="flex items-center gap-4 shrink-0">
                                    {isDeployed && (
                                        <div className="flex items-center gap-3 text-[11px] text-muted-foreground/30">
                                            <span className="flex items-center gap-1"><Zap size={11} />Lambda</span>
                                            <span className="flex items-center gap-1"><Database size={11} />DynamoDB</span>
                                            <span className="flex items-center gap-1"><Globe size={11} />API</span>
                                        </div>
                                    )}
                                    <ArrowUpRight size={16} className="text-muted-foreground/20 group-hover:text-primary/60 transition-colors" />
                                </div>
                            </Link>
                        );
                    })}
                </div>
            )}
        </div>
    );
};
