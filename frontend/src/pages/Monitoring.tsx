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
    RefreshCw
} from 'lucide-react';

interface ProjectHealth {
    project: ProjectResponse;
    deployment: DeploymentResponse | null;
}

export const Monitoring: React.FC = () => {
    const [items, setItems] = useState<ProjectHealth[]>([]);
    const [loading, setLoading] = useState(true);

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

    const deployed = items.filter(i => i.deployment?.status === 'success' || i.deployment?.status === 'deployed');
    const failed = items.filter(i => i.deployment?.status === 'failed');
    const healthy = deployed.length;
    const total = items.length;

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
            <div className="grid grid-cols-4 gap-4">
                <div className="glass-card p-4 flex items-center gap-3">
                    <div className="w-10 h-10 rounded-xl bg-blue-500/10 flex items-center justify-center">
                        <Server size={18} className="text-blue-400" />
                    </div>
                    <div>
                        <p className="text-2xl font-bold">{total}</p>
                        <p className="text-[11px] text-muted-foreground/50">Infrastructure</p>
                    </div>
                </div>
                <div className="glass-card p-4 flex items-center gap-3">
                    <div className="w-10 h-10 rounded-xl bg-emerald-500/10 flex items-center justify-center">
                        <CheckCircle2 size={18} className="text-emerald-400" />
                    </div>
                    <div>
                        <p className="text-2xl font-bold">{healthy}</p>
                        <p className="text-[11px] text-muted-foreground/50">Healthy</p>
                    </div>
                </div>
                <div className="glass-card p-4 flex items-center gap-3">
                    <div className="w-10 h-10 rounded-xl bg-red-500/10 flex items-center justify-center">
                        <AlertTriangle size={18} className="text-red-400" />
                    </div>
                    <div>
                        <p className="text-2xl font-bold">{failed.length}</p>
                        <p className="text-[11px] text-muted-foreground/50">Issues</p>
                    </div>
                </div>
                <div className="glass-card p-4 flex items-center gap-3">
                    <div className="w-10 h-10 rounded-xl bg-amber-500/10 flex items-center justify-center">
                        <Activity size={18} className="text-amber-400" />
                    </div>
                    <div>
                        <p className="text-2xl font-bold">{healthy > 0 ? '99.9%' : '--'}</p>
                        <p className="text-[11px] text-muted-foreground/50">Uptime</p>
                    </div>
                </div>
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
                    {items.map(({ project, deployment }) => {
                        const isDeployed = deployment?.status === 'success' || deployment?.status === 'deployed';
                        const isFailed = deployment?.status === 'failed';
                        return (
                            <Link
                                key={project.id}
                                to={`/projects/${project.id}`}
                                className="glass-card p-4 flex items-center gap-4 group hover:border-primary/20 transition-all cursor-pointer block"
                            >
                                <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${isDeployed ? 'bg-emerald-500/10' : isFailed ? 'bg-red-500/10' : 'bg-white/[0.04]'
                                    }`}>
                                    {isDeployed ? (
                                        <CheckCircle2 size={18} className="text-emerald-400" />
                                    ) : isFailed ? (
                                        <AlertTriangle size={18} className="text-red-400" />
                                    ) : (
                                        <Activity size={18} className="text-muted-foreground/30" />
                                    )}
                                </div>
                                <div className="flex-1 min-w-0">
                                    <div className="flex items-center gap-2">
                                        <h3 className="text-sm font-semibold truncate group-hover:text-primary transition-colors">{project.name}</h3>
                                        <span className={`px-2 py-0.5 rounded-full text-[10px] font-semibold ${isDeployed ? 'badge-success' :
                                            isFailed ? 'badge-danger' : 'badge-warning'
                                            }`}>
                                            {isDeployed ? 'Healthy' : isFailed ? 'Error' : 'Inactive'}
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
