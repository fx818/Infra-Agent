import React, { useState, useEffect } from 'react';
import { architectureApi } from '../../api/architecture';
import type { ArchitectureResponse } from '../../types';
import { Send, FileCode, Cpu, Loader2, Box, Sparkles, Share2, Terminal } from 'lucide-react';
import { BlueprintGraph } from '../../components/projects/BlueprintGraph';
import { ErrorPanel } from '../../components/ErrorPanel';

interface Props {
    projectId: number;
}

export const ArchitectureTab: React.FC<Props> = ({ projectId }) => {
    const [architecture, setArchitecture] = useState<ArchitectureResponse | null>(null);
    const [messages, setMessages] = useState<any[]>([]);
    const [loading, setLoading] = useState(false);
    const [generating, setGenerating] = useState(false);
    const [prompt, setPrompt] = useState('');
    const [error, setError] = useState<any>(null);
    const [lastPrompt, setLastPrompt] = useState('');
    const [view, setView] = useState<'graph' | 'code'>('graph');


    useEffect(() => {
        loadData();
    }, [projectId]);

    const loadData = async () => {
        setLoading(true);
        try {
            const [archData, msgData] = await Promise.all([
                architectureApi.get(projectId).catch(() => null),
                architectureApi.getMessages(projectId).catch(() => [])
            ]);
            setArchitecture(archData);
            setMessages(msgData);
        } catch (error) {
            console.error('Failed to load data:', error);
        } finally {
            setLoading(false);
        }
    };

    const handleGenerate = async (e?: React.FormEvent, retryPrompt?: string) => {
        e?.preventDefault();
        const currentPrompt = retryPrompt || prompt;
        if (!currentPrompt.trim()) return;

        setGenerating(true);
        setError(null);
        setLastPrompt(currentPrompt);
        if (!retryPrompt) setPrompt('');

        // Optimistically add user message
        if (!retryPrompt) {
            setMessages(prev => [...prev, { role: 'user', content: currentPrompt }]);
        }

        try {
            let data;
            if (architecture) {
                data = await architectureApi.edit(projectId, currentPrompt);
            } else {
                data = await architectureApi.generate(projectId, currentPrompt);
            }
            setArchitecture(data);

            // Re-fetch messages to get assistant response and correct ordering
            const updatedMessages = await architectureApi.getMessages(projectId);
            setMessages(updatedMessages);
        } catch (err: any) {
            setError(err);
        } finally {
            setGenerating(false);
        }
    };

    const handleRetry = () => {
        handleGenerate(undefined, lastPrompt);
    };

    // Service type color map
    const getServiceColor = (type: string): string => {
        const colors: Record<string, string> = {
            ec2: 'from-orange-500 to-orange-600',
            ecs: 'from-orange-400 to-orange-500',
            lambda: 'from-amber-500 to-orange-500',
            s3: 'from-green-500 to-emerald-600',
            rds: 'from-blue-500 to-blue-600',
            dynamodb: 'from-blue-400 to-indigo-500',
            vpc: 'from-purple-500 to-purple-600',
            elb: 'from-violet-500 to-purple-500',
            cloudfront: 'from-purple-400 to-violet-500',
            api_gateway: 'from-rose-500 to-pink-600',
            sns: 'from-pink-500 to-rose-500',
            sqs: 'from-pink-400 to-pink-500',
            elasticache: 'from-teal-500 to-cyan-600',
            iam: 'from-red-500 to-rose-600',
        };
        return colors[type] || 'from-gray-500 to-gray-600';
    };

    return (
        <div className="flex h-full gap-4">
            {/* Left: AI Chat Panel */}
            <div className="w-[340px] shrink-0 flex flex-col glass-card overflow-hidden">
                {/* Header */}
                <div className="p-4 border-b border-border/30">
                    <div className="flex items-center gap-2.5">
                        <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center">
                            <Cpu size={16} className="text-white" />
                        </div>
                        <div>
                            <h3 className="text-sm font-semibold">AI Architect</h3>
                            <p className="text-[11px] text-muted-foreground/50">
                                {generating ? 'Generating…' : 'Ready'}
                            </p>
                        </div>
                    </div>
                </div>

                {/* Message area */}
                <div className="flex-1 overflow-y-auto p-4 space-y-4">
                    {messages.length === 0 && !generating && (
                        <div className="text-center py-12 space-y-4">
                            <div className="w-14 h-14 rounded-2xl bg-primary/10 flex items-center justify-center mx-auto">
                                <Sparkles size={24} className="text-primary/50" />
                            </div>
                            <div className="space-y-1">
                                <p className="text-sm font-medium text-muted-foreground/80">No architecture yet</p>
                                <p className="text-xs text-muted-foreground/50 leading-relaxed max-w-[240px] mx-auto">
                                    Describe your infrastructure and AI will design it for you.
                                </p>
                            </div>

                            {/* Suggestions */}
                            <div className="space-y-2 pt-2">
                                <p className="text-[10px] uppercase tracking-wider text-muted-foreground/30 font-semibold">Try saying</p>
                                {[
                                    'Create a scalable web app with ECS and RDS',
                                    'Build a serverless API with Lambda and DynamoDB',
                                    'Set up a static website with S3 and CloudFront',
                                ].map((suggestion, i) => (
                                    <button
                                        key={i}
                                        onClick={() => setPrompt(suggestion)}
                                        className="w-full text-left text-[11px] px-3 py-2 rounded-lg bg-white/[0.03] border border-border/20 text-muted-foreground/60 hover:text-foreground hover:bg-white/[0.06] hover:border-primary/20 transition-all"
                                    >
                                        "{suggestion}"
                                    </button>
                                ))}
                            </div>
                        </div>
                    )}

                    {messages.map((msg, i) => (
                        <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'} animate-fade-in`}>
                            <div className={`max-w-[85%] rounded-2xl p-3 text-[12px] leading-relaxed shadow-sm ${msg.role === 'user'
                                ? 'bg-primary text-white rounded-tr-none'
                                : 'bg-white/[0.05] border border-white/10 text-muted-foreground rounded-tl-none'
                                }`}>
                                {msg.content}
                            </div>
                        </div>
                    ))}

                    {generating && (
                        <div className="flex justify-start animate-fade-in">
                            <div className="max-w-[85%] rounded-2xl rounded-tl-none p-3 bg-white/[0.05] border border-white/10 text-muted-foreground shadow-sm flex items-center gap-3">
                                <Loader2 size={14} className="animate-spin text-primary" />
                                <span className="text-[11px]">Thinking...</span>
                            </div>
                        </div>
                    )}

                    {error && (
                        <div className="animate-fade-in">
                            <ErrorPanel
                                error={error}
                                onDismiss={() => setError(null)}
                                onRetry={lastPrompt ? handleRetry : undefined}
                            />
                        </div>
                    )}
                </div>

                {/* Input */}
                <div className="p-3 border-t border-border/30">
                    <form onSubmit={handleGenerate} className="flex gap-2">
                        <input
                            type="text"
                            value={prompt}
                            onChange={(e) => setPrompt(e.target.value)}
                            placeholder={architecture ? "Describe changes…" : "Describe your architecture…"}
                            className="input-glow flex-1 text-xs py-2.5"
                            disabled={generating}
                        />
                        <button
                            type="submit"
                            disabled={generating || !prompt.trim()}
                            className="btn-gradient px-3 py-2.5 shrink-0"
                            title={generating ? 'Generating…' : 'Send'}
                        >
                            {generating ? <Loader2 size={14} className="animate-spin" /> : <Send size={14} />}
                        </button>
                    </form>
                    {generating && (
                        <p className="text-[10px] text-muted-foreground/40 mt-1.5 text-center">
                            This may take 20–60 seconds…
                        </p>
                    )}
                </div>
            </div>

            {/* Right: Visualization & Code */}
            <div className="flex-1 flex flex-col glass-card overflow-hidden">
                {/* Header */}
                <div className="p-4 border-b border-border/30 flex justify-between items-center">
                    <div className="flex items-center gap-4">
                        <div className="flex items-center gap-2.5">
                            <FileCode size={16} className="text-muted-foreground" />
                            <h3 className="text-sm font-semibold">Blueprint</h3>
                        </div>

                        {architecture && (
                            <div className="flex items-center bg-white/5 rounded-lg p-0.5 border border-white/10">
                                <button
                                    onClick={() => setView('graph')}
                                    className={`flex items-center gap-1.5 px-2.5 py-1 rounded-md text-[10px] font-semibold transition-all ${view === 'graph'
                                        ? 'bg-primary text-white shadow-lg shadow-primary/20'
                                        : 'text-muted-foreground hover:text-foreground'
                                        }`}
                                >
                                    <Share2 size={12} />
                                    <span>Graph</span>
                                </button>
                                <button
                                    onClick={() => setView('code')}
                                    className={`flex items-center gap-1.5 px-2.5 py-1 rounded-md text-[10px] font-semibold transition-all ${view === 'code'
                                        ? 'bg-primary text-white shadow-lg shadow-primary/20'
                                        : 'text-muted-foreground hover:text-foreground'
                                        }`}
                                >
                                    <Terminal size={12} />
                                    <span>Code</span>
                                </button>
                            </div>
                        )}
                    </div>
                    {architecture && (
                        <span className="badge-info text-[10px] px-2 py-0.5 rounded-full font-semibold">
                            v{architecture.version}
                        </span>
                    )}
                </div>

                <div className="flex-1 flex flex-col bg-[#0d1117] min-h-0">
                    {loading ? (
                        <div className="flex items-center justify-center h-full">
                            <div className="flex flex-col items-center gap-3">
                                <Loader2 className="animate-spin text-primary/50" size={28} />
                                <p className="text-xs text-muted-foreground/50">Loading blueprint…</p>
                            </div>
                        </div>
                    ) : architecture ? (
                        <div className="flex flex-col h-full">
                            {/* Resources grid */}
                            <div className="p-4 border-b border-white/[0.06]">
                                <p className="text-[10px] uppercase tracking-wider text-white/20 font-semibold mb-3">
                                    Resources ({architecture.graph.nodes.length})
                                </p>
                                <div className="flex flex-wrap gap-2">
                                    {architecture.graph.nodes.map((node) => (
                                        <div
                                            key={node.id}
                                            className="flex items-center gap-2 px-2.5 py-1.5 rounded-lg bg-white/[0.04] border border-white/[0.06] hover:border-white/[0.12] transition-colors group"
                                        >
                                            <div className={`w-2 h-2 rounded-full bg-gradient-to-br ${getServiceColor(node.type)}`} />
                                            <span className="text-[11px] font-mono text-blue-300/80 group-hover:text-blue-300 transition-colors">
                                                {node.type}
                                            </span>
                                            <span className="text-white/15">·</span>
                                            <span className="text-[11px] text-white/50 group-hover:text-white/70 transition-colors">
                                                {node.id}
                                            </span>
                                        </div>
                                    ))}
                                </div>
                            </div>

                            {/* Visualization / Code area */}
                            <div className="flex-1 min-h-0 overflow-hidden relative">
                                {view === 'graph' ? (
                                    <div className="w-full h-full min-h-[400px]">
                                        {architecture.visual ? (
                                            <BlueprintGraph visualData={architecture.visual} />
                                        ) : (
                                            <div className="flex flex-col items-center justify-center h-full gap-4 text-white/20">
                                                <Share2 size={40} />
                                                <div className="text-center space-y-1">
                                                    <p className="text-sm font-medium">No layout data</p>
                                                    <p className="text-xs text-white/10">Try regenerating architecture</p>
                                                </div>
                                            </div>
                                        )}
                                    </div>
                                ) : (
                                    <div className="flex-1 h-full overflow-auto p-4">
                                        <p className="text-[10px] uppercase tracking-wider text-white/20 font-semibold mb-3 sticky top-0 bg-[#0d1117] pb-2 z-10">
                                            Terraform Configuration
                                        </p>
                                        {architecture.terraform_files?.files['main.tf'] ? (
                                            <pre className="text-[12px] leading-[1.7] text-emerald-200/70 font-mono whitespace-pre-wrap selection:bg-primary/30">
                                                {architecture.terraform_files.files['main.tf']}
                                            </pre>
                                        ) : (
                                            <p className="text-muted-foreground/30 text-sm italic">
                                                No Terraform code generated yet.
                                            </p>
                                        )}
                                    </div>
                                )}
                            </div>
                        </div>
                    ) : (
                        <div className="flex flex-col items-center justify-center h-full gap-4 text-white/20">
                            <Box size={40} />
                            <div className="text-center space-y-1">
                                <p className="text-sm font-medium">Waiting for generation</p>
                                <p className="text-xs text-white/10">Architecture will appear here</p>
                            </div>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
};
