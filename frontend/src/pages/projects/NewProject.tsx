import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { projectsApi } from '../../api/projects';
import { Loader2, ArrowLeft, Sparkles, FolderPlus } from 'lucide-react';
import { Link } from 'react-router-dom';

export const NewProject: React.FC = () => {
    const navigate = useNavigate();
    const [name, setName] = useState('');
    const [description, setDescription] = useState('');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setLoading(true);
        setError('');

        try {
            const project = await projectsApi.create({
                name,
                description,
                region: 'us-east-1',
            });
            navigate(`/projects/${project.id}`);
        } catch (err: any) {
            console.error(err);
            setError('Failed to create project');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="max-w-xl mx-auto animate-fade-in">
            <Link
                to="/"
                className="inline-flex items-center gap-2 text-xs text-muted-foreground/60 hover:text-foreground mb-6 transition-colors"
            >
                <ArrowLeft size={14} />
                Back to Dashboard
            </Link>

            <div className="mb-8">
                <div className="flex items-center gap-3 mb-3">
                    <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center shadow-lg shadow-blue-500/20">
                        <FolderPlus size={20} className="text-white" />
                    </div>
                    <div>
                        <h1 className="text-2xl font-bold">New Project</h1>
                        <p className="text-xs text-muted-foreground">Define your infrastructure scope</p>
                    </div>
                </div>
            </div>

            <div className="glass-card p-6 space-y-6">
                {error && (
                    <div className="p-3 bg-destructive/10 text-destructive text-sm rounded-lg border border-destructive/20 animate-fade-in">
                        {error}
                    </div>
                )}

                <form onSubmit={handleSubmit} className="space-y-5">
                    <div className="space-y-2">
                        <label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground/80">
                            Project Name
                        </label>
                        <input
                            type="text"
                            required
                            value={name}
                            onChange={(e) => setName(e.target.value)}
                            className="input-glow"
                            placeholder="My Cloud Architecture"
                        />
                    </div>

                    <div className="space-y-2">
                        <label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground/80">
                            Description
                        </label>
                        <textarea
                            value={description}
                            onChange={(e) => setDescription(e.target.value)}
                            className="input-glow h-28 resize-none"
                            placeholder="Describe your project's purpose and requirements…"
                        />
                    </div>

                    <div className="flex items-center gap-3 pt-3 border-t border-border/30">
                        <div className="flex items-center gap-2 text-[11px] text-muted-foreground/50">
                            <Sparkles size={12} />
                            <span>AI will generate architecture after creation</span>
                        </div>
                        <div className="flex-1" />
                        <Link
                            to="/"
                            className="px-4 py-2 text-sm text-muted-foreground hover:text-foreground border border-border/50 rounded-lg hover:bg-white/[0.03] transition-all"
                        >
                            Cancel
                        </Link>
                        <button
                            type="submit"
                            disabled={loading || !name.trim()}
                            className="btn-gradient flex items-center gap-2 text-sm"
                        >
                            {loading && <Loader2 className="animate-spin" size={14} />}
                            Create Project
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
};
