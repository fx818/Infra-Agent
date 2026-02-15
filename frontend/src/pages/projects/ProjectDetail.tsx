import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { projectsApi } from '../../api/projects';
import type { Project } from '../../types';
import { ArchitectureTab } from './ArchitectureTab';
import { DeploymentTab } from './DeploymentTab';
import { MonitoringTab } from './MonitoringTab';
import {
    ArrowLeft,
    Layers,
    Server,
    Activity,
    Circle
} from 'lucide-react';

export const ProjectDetail: React.FC = () => {
    const { id } = useParams<{ id: string }>();
    const [project, setProject] = useState<Project | null>(null);
    const [loading, setLoading] = useState(true);
    const [activeTab, setActiveTab] = useState<'architecture' | 'deployment' | 'monitoring'>('architecture');

    useEffect(() => {
        const fetchProject = async () => {
            if (!id) return;
            try {
                const data = await projectsApi.getOne(id);
                setProject(data);
            } catch (error) {
                console.error('Failed to fetch project:', error);
            } finally {
                setLoading(false);
            }
        };
        fetchProject();
    }, [id]);

    if (loading) {
        return (
            <div className="flex items-center justify-center h-full">
                <div className="flex flex-col items-center gap-3">
                    <div className="w-10 h-10 rounded-full border-2 border-primary/30 border-t-primary animate-spin" />
                    <p className="text-sm text-muted-foreground">Loading project…</p>
                </div>
            </div>
        );
    }

    if (!project) {
        return (
            <div className="flex flex-col items-center justify-center h-full gap-4 animate-fade-in">
                <div className="w-16 h-16 rounded-2xl bg-destructive/10 flex items-center justify-center">
                    <Circle size={32} className="text-destructive/50" />
                </div>
                <h3 className="text-lg font-semibold">Project not found</h3>
                <Link to="/" className="text-sm text-primary hover:text-primary/80 transition-colors">
                    ← Return to Dashboard
                </Link>
            </div>
        );
    }

    const tabs = [
        { key: 'architecture' as const, label: 'Architecture', icon: Layers },
        { key: 'deployment' as const, label: 'Deployment', icon: Server },
        { key: 'monitoring' as const, label: 'Monitoring', icon: Activity },
    ];

    return (
        <div className="flex flex-col h-full gap-4 animate-fade-in">
            {/* Header */}
            <div className="flex items-center gap-4">
                <Link
                    to="/"
                    className="p-2 rounded-lg text-muted-foreground hover:text-foreground hover:bg-white/[0.04] transition-all"
                >
                    <ArrowLeft size={18} />
                </Link>
                <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-3">
                        <h1 className="text-xl font-bold truncate">{project.name}</h1>
                        <span className={`px-2.5 py-0.5 rounded-full text-[11px] font-semibold shrink-0 ${project.status === 'deployed'
                                ? 'badge-success'
                                : 'badge-warning'
                            }`}>
                            {project.status.toUpperCase()}
                        </span>
                    </div>
                    {project.description && (
                        <p className="text-xs text-muted-foreground/60 truncate mt-0.5">{project.description}</p>
                    )}
                </div>
            </div>

            {/* Tabs */}
            <div className="flex items-center gap-1 p-1 rounded-xl bg-white/[0.03] border border-border/30 w-fit">
                {tabs.map((tab) => {
                    const Icon = tab.icon;
                    const isActive = activeTab === tab.key;
                    return (
                        <button
                            key={tab.key}
                            onClick={() => setActiveTab(tab.key)}
                            className={`relative flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-medium transition-all duration-200 ${isActive
                                    ? 'bg-primary/10 text-primary shadow-sm'
                                    : 'text-muted-foreground hover:text-foreground hover:bg-white/[0.04]'
                                }`}
                        >
                            <Icon size={14} />
                            <span>{tab.label}</span>
                        </button>
                    );
                })}
            </div>

            {/* Content */}
            <div className="flex-1 overflow-hidden">
                {activeTab === 'architecture' && <ArchitectureTab projectId={project.id} />}
                {activeTab === 'deployment' && <DeploymentTab projectId={project.id} />}
                {activeTab === 'monitoring' && <MonitoringTab projectId={project.id} />}
            </div>
        </div>
    );
};
