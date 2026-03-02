import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { projectsApi } from '../api/projects';
import type { Project } from '../types';
import { Plus, Trash2, Calendar, ArrowRight, Folder, Sparkles, Bot, Blocks, Server, CheckCircle2, AlertTriangle, Activity, Clock } from 'lucide-react';

export const Dashboard: React.FC = () => {
    const [projects, setProjects] = useState<Project[]>([]);
    const [loading, setLoading] = useState(true);
    const [activeFilters, setActiveFilters] = useState<Set<string>>(new Set());

    const fetchProjects = async () => {
        try {
            const data = await projectsApi.getAll();
            setProjects(data);
        } catch (error) {
            console.error('Failed to fetch projects:', error);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchProjects();
    }, []);

    const handleDelete = async (id: number, e: React.MouseEvent) => {
        e.preventDefault();
        e.stopPropagation();
        if (!window.confirm('Are you sure you want to delete this project?')) return;

        try {
            await projectsApi.delete(id);
            setProjects(projects.filter(p => p.id !== id));
        } catch (error) {
            console.error('Failed to delete project:', error);
        }
    };

    if (loading) {
        return (
            <div className="flex items-center justify-center h-full">
                <div className="flex flex-col items-center gap-3">
                    <div className="w-10 h-10 rounded-full border-2 border-primary/30 border-t-primary animate-spin" />
                    <p className="text-sm text-muted-foreground">Loading Infrastructure…</p>
                </div>
            </div>
        );
    }

    return (
        <div className="space-y-8 max-w-6xl mx-auto animate-fade-in">
            {/* Header */}
            <div className="flex items-end justify-between">
                <div>
                    <h1 className="text-3xl font-bold tracking-tight">Infrastructures</h1>
                    <p className="text-muted-foreground mt-1 text-sm">
                        {projects.length} project{projects.length !== 1 ? 's' : ''} • Manage your cloud infrastructure
                    </p>
                </div>
                <Link
                    to="/projects/new"
                    className="btn-gradient flex items-center gap-2 text-sm"
                >
                    <Plus size={16} />
                    <span>New Project</span>
                </Link>
            </div>

            {projects.length === 0 ? (
                <div className="glass-card p-16 text-center animate-scale-in">
                    <div className="w-20 h-20 rounded-2xl bg-gradient-to-br from-primary/20 to-accent/20 flex items-center justify-center mx-auto mb-6">
                        <Sparkles size={36} className="text-primary/60" />
                    </div>
                    <h3 className="text-xl font-semibold mb-2">No projects yet</h3>
                    <p className="text-muted-foreground text-sm mb-8 max-w-sm mx-auto">
                        Create your first project and let AI generate your cloud infrastructure architecture.
                    </p>
                    <Link
                        to="/projects/new"
                        className="btn-gradient inline-flex items-center gap-2"
                    >
                        <Plus size={16} />
                        <span>Create Your First Project</span>
                    </Link>
                </div>
            ) : (() => {
                const getFilterGroup = (p: Project): string => {
                    const s = p.status || '';
                    if (s === 'success' || s === 'deployed') return 'Deployed';
                    if (s === 'failed') return 'Failed';
                    if (s === 'partial_deployed') return 'Partial';
                    if (s === 'destroyed') return 'Destroyed';
                    return 'Inactive';
                };

                const deployedCount = projects.filter(p => getFilterGroup(p) === 'Deployed').length;
                const failedCount = projects.filter(p => getFilterGroup(p) === 'Failed').length;
                const partialCount = projects.filter(p => getFilterGroup(p) === 'Partial').length;
                const destroyedCount = projects.filter(p => getFilterGroup(p) === 'Destroyed').length;
                const inactiveCount = projects.filter(p => getFilterGroup(p) === 'Inactive').length;

                const statCards = [
                    { key: 'Total', label: 'Total', value: projects.length, icon: <Server size={18} className="text-blue-400" />, bg: 'bg-blue-500/10', ring: 'ring-blue-500/40' },
                    { key: 'Deployed', label: 'Deployed', value: deployedCount, icon: <CheckCircle2 size={18} className="text-emerald-400" />, bg: 'bg-emerald-500/10', ring: 'ring-emerald-500/40' },
                    { key: 'Failed', label: 'Failed', value: failedCount, icon: <AlertTriangle size={18} className="text-red-400" />, bg: 'bg-red-500/10', ring: 'ring-red-500/40' },
                    { key: 'Partial', label: 'Partial', value: partialCount, icon: <Activity size={18} className="text-amber-400" />, bg: 'bg-amber-500/10', ring: 'ring-amber-500/40' },
                    { key: 'Destroyed', label: 'Destroyed', value: destroyedCount, icon: <Trash2 size={18} className="text-rose-400" />, bg: 'bg-rose-500/10', ring: 'ring-rose-500/40' },
                    { key: 'Inactive', label: 'Inactive', value: inactiveCount, icon: <Clock size={18} className="text-slate-400" />, bg: 'bg-slate-500/10', ring: 'ring-slate-500/40' },
                ];

                const toggleFilter = (key: string) => {
                    if (key === 'Total') { setActiveFilters(new Set()); return; }
                    setActiveFilters(prev => {
                        const next = new Set(prev);
                        if (next.has(key)) next.delete(key); else next.add(key);
                        return next;
                    });
                };

                const filteredProjects = activeFilters.size === 0 ? projects : projects.filter(p => activeFilters.has(getFilterGroup(p)));

                return (
                    <>
                        {/* Filter Cards */}
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

                        {/* Project Grid */}
                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                            {filteredProjects.map((project, index) => (
                                <Link
                                    key={project.id}
                                    to={`/projects/${project.id}`}
                                    className="glass-card-hover p-0 block overflow-hidden animate-slide-up"
                                    style={{ animationDelay: `${index * 80}ms`, opacity: 0 }}
                                >
                                    {/* Gradient accent strip */}
                                    <div className={`h-1 w-full ${project.source === 'drag_built'
                                        ? 'bg-gradient-to-r from-violet-500 via-fuchsia-500 to-pink-500'
                                        : 'bg-gradient-to-r from-blue-500 via-purple-500 to-pink-500'
                                        } opacity-60`} />

                                    <div className="p-5">
                                        <div className="flex items-start justify-between mb-4">
                                            <div className="w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center">
                                                <Folder size={20} className="text-primary" />
                                            </div>
                                            <div className="flex items-center gap-1.5">
                                                <div style={{
                                                    display: 'flex', alignItems: 'center', gap: '4px',
                                                    padding: '2px 8px', borderRadius: '12px',
                                                    fontSize: '10px', fontWeight: 600,
                                                    background: project.source === 'drag_built'
                                                        ? 'rgba(139,92,246,0.12)'
                                                        : 'rgba(59,130,246,0.12)',
                                                    border: `1px solid ${project.source === 'drag_built'
                                                        ? 'rgba(139,92,246,0.25)'
                                                        : 'rgba(59,130,246,0.25)'}`,
                                                    color: project.source === 'drag_built' ? '#a78bfa' : '#60a5fa',
                                                }}>
                                                    {project.source === 'drag_built'
                                                        ? <><Blocks size={10} /> Drag Built</>
                                                        : <><Bot size={10} /> AI Generated</>
                                                    }
                                                </div>
                                                {(() => {
                                                    const statusMap: Record<string, { class: string; label: string }> = {
                                                        deployed: { class: 'badge-success', label: 'Deployed' },
                                                        success: { class: 'badge-success', label: 'Deployed' },
                                                        failed: { class: 'badge-danger', label: 'Failed' },
                                                        destroyed: { class: 'badge-danger', label: 'Destroyed' },
                                                        partial_deployed: { class: 'bg-amber-500/15 text-amber-400 border border-amber-500/30', label: 'Partial' },
                                                        deploying: { class: 'badge-info', label: 'Deploying' },
                                                        running: { class: 'badge-info', label: 'Running' },
                                                        pending: { class: 'badge-warning', label: 'Pending' },
                                                    };
                                                    const cfg = statusMap[project.status] || { class: 'badge-warning', label: project.status || 'Draft' };
                                                    return (
                                                        <span className={`px-2.5 py-1 rounded-full text-[11px] font-semibold ${cfg.class}`}>
                                                            {cfg.label}
                                                        </span>
                                                    );
                                                })()}
                                            </div>
                                        </div>

                                        <h3 className="text-base font-semibold mb-1.5 group-hover:text-primary transition-colors">
                                            {project.name}
                                        </h3>
                                        <p className="text-muted-foreground text-xs line-clamp-2 leading-relaxed h-8">
                                            {project.description || 'No description provided'}
                                        </p>
                                    </div>

                                    <div className="px-5 py-3 flex items-center justify-between text-[11px] text-muted-foreground/60 border-t border-border/30">
                                        <div className="flex items-center gap-1.5">
                                            <Calendar size={12} />
                                            <span>{new Date(project.created_at || '').toLocaleDateString()}</span>
                                        </div>
                                        <div className="flex items-center gap-2">
                                            <button
                                                onClick={(e) => handleDelete(project.id, e)}
                                                className="p-1.5 hover:bg-destructive/10 hover:text-destructive rounded-md transition-all"
                                            >
                                                <Trash2 size={13} />
                                            </button>
                                            <ArrowRight size={13} className="text-muted-foreground/30" />
                                        </div>
                                    </div>
                                </Link>
                            ))}
                        </div>
                    </>
                );
            })()}
        </div >
    );
};
