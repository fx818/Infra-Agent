import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { projectsApi } from '../api/projects';
import type { Project } from '../types';
import { Plus, Trash2, Calendar, ArrowRight, Folder, Sparkles } from 'lucide-react';

export const Dashboard: React.FC = () => {
    const [projects, setProjects] = useState<Project[]>([]);
    const [loading, setLoading] = useState(true);

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
            ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    {projects.map((project, index) => (
                        <Link
                            key={project.id}
                            to={`/projects/${project.id}`}
                            className="glass-card-hover p-0 block overflow-hidden animate-slide-up"
                            style={{ animationDelay: `${index * 80}ms`, opacity: 0 }}
                        >
                            {/* Gradient accent strip */}
                            <div className="h-1 w-full bg-gradient-to-r from-blue-500 via-purple-500 to-pink-500 opacity-60" />

                            <div className="p-5">
                                <div className="flex items-start justify-between mb-4">
                                    <div className="w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center">
                                        <Folder size={20} className="text-primary" />
                                    </div>
                                    <span className={`px-2.5 py-1 rounded-full text-[11px] font-semibold ${project.status === 'deployed'
                                            ? 'badge-success'
                                            : 'badge-warning'
                                        }`}>
                                        {project.status}
                                    </span>
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
            )}
        </div>
    );
};
