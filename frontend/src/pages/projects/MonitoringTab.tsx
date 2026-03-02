import React, { useEffect, useState, useCallback } from 'react';
import api from '../../api/client';
import {
    Activity,
    BarChart3,
    Wifi,
    CheckCircle2,
    AlertTriangle,
    RefreshCw,
    Server,
    Database,
    Zap,
    Globe,
    Shield,
    Trash2,
    X,
    Loader2,
    Terminal,
    Square,
    CheckSquare,
    MinusSquare,
} from 'lucide-react';

interface Props {
    projectId: number;
}

interface ResourceMetric {
    name: string;
    type: string;
    metrics?: Record<string, any>;
}

interface StateResource {
    address: string;
    type: string;
    name: string;
}

interface MetricsResponse {
    project_id: number;
    message?: string;
    error?: string;
    resources?: ResourceMetric[];
    total_resources_in_state?: number;
    overall_health?: string;
    healthy_count?: number;
    unhealthy_count?: number;
}

interface BatchResult {
    resource_address: string;
    success: boolean;
    return_code: number;
    output: string;
}

// ── Helpers ──────────────────────────────────────────────────────

const getResourceIcon = (type: string | undefined) => {
    const t = (type || '').toLowerCase();
    if (t.includes('lambda')) return <Zap size={15} className="text-amber-400" />;
    if (t.includes('dynamodb') || t.includes('rds') || t.includes('elasticache')) return <Database size={15} className="text-blue-400" />;
    if (t.includes('apigateway')) return <Globe size={15} className="text-green-400" />;
    if (t.includes('iam')) return <Shield size={15} className="text-purple-400" />;
    if (t.includes('s3')) return <Server size={15} className="text-cyan-400" />;
    if (t.includes('ecs') || t.includes('ec2')) return <Server size={15} className="text-orange-400" />;
    if (t.includes('cloudfront') || t.includes('alb') || t.includes('lb')) return <Globe size={15} className="text-pink-400" />;
    if (t.includes('vpc') || t.includes('subnet') || t.includes('security_group')) return <Shield size={15} className="text-teal-400" />;
    return <Server size={15} className="text-muted-foreground/60" />;
};

const getResourceLabel = (type: string | undefined) => {
    const labels: Record<string, string> = {
        'aws_lambda_function': 'Lambda Function',
        'aws_dynamodb_table': 'DynamoDB Table',
        'aws_apigatewayv2_api': 'API Gateway',
        'aws_iam_role': 'IAM Role',
        'aws_iam_role_policy_attachment': 'IAM Policy',
        'aws_s3_bucket': 'S3 Bucket',
        'aws_s3_bucket_versioning': 'S3 Versioning',
        'aws_s3_bucket_public_access_block': 'S3 Public Access',
        'aws_cloudfront_distribution': 'CloudFront CDN',
        'aws_ecs_cluster': 'ECS Cluster',
        'aws_ecs_service': 'ECS Service',
        'aws_ecs_task_definition': 'ECS Task Def',
        'aws_db_instance': 'RDS Database',
        'aws_elasticache_cluster': 'ElastiCache',
        'aws_vpc': 'VPC',
        'aws_subnet': 'Subnet',
        'aws_security_group': 'Security Group',
        'aws_internet_gateway': 'Internet Gateway',
        'aws_nat_gateway': 'NAT Gateway',
        'aws_alb': 'App Load Balancer',
        'aws_lb': 'Load Balancer',
        'aws_sqs_queue': 'SQS Queue',
        'aws_sns_topic': 'SNS Topic',
    };
    return labels[type || ''] || (type || 'resource').replace('aws_', '').replace(/_/g, ' ');
};

// ── Batch Destroy Modal ───────────────────────────────────────────

interface BatchDestroyModalProps {
    resources: StateResource[];
    projectId: number;
    onClose: () => void;
    onDone: () => void;
}

const BatchDestroyModal: React.FC<BatchDestroyModalProps> = ({ resources, projectId, onClose, onDone }) => {
    const [loading, setLoading] = useState(false);
    const [results, setResults] = useState<BatchResult[]>([]);
    const [done, setDone] = useState(false);
    const [summary, setSummary] = useState<{ succeeded: number; failed: number } | null>(null);
    const [expandedIdx, setExpandedIdx] = useState<number | null>(null);

    const handleDestroy = async () => {
        setLoading(true);
        try {
            const res = await api.post(`/projects/${projectId}/resources/batch-destroy`, {
                resource_addresses: resources.map(r => r.address),
            });
            setResults(res.data.results || []);
            setSummary({ succeeded: res.data.succeeded, failed: res.data.failed });
        } catch (err: any) {
            // Treat the whole thing as one failure
            setResults(resources.map(r => ({
                resource_address: r.address,
                success: false,
                return_code: -1,
                output: err.response?.data?.detail || err.message || 'Request failed',
            })));
            setSummary({ succeeded: 0, failed: resources.length });
        } finally {
            setLoading(false);
            setDone(true);
        }
    };

    const allGood = summary && summary.failed === 0;

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm" onClick={!loading ? onClose : undefined}>
            <div
                className="w-full max-w-lg bg-[#0d0f14] border border-border/40 rounded-2xl shadow-2xl overflow-hidden mx-4"
                onClick={e => e.stopPropagation()}
                style={{ maxHeight: '85vh', display: 'flex', flexDirection: 'column' }}
            >
                {/* Header */}
                <div className="px-6 py-4 border-b border-border/30 flex items-center justify-between shrink-0">
                    <div className="flex items-center gap-2.5">
                        <div className="w-9 h-9 rounded-lg bg-red-500/10 flex items-center justify-center">
                            <Trash2 size={16} className="text-red-400" />
                        </div>
                        <div>
                            <p className="text-sm font-semibold">Destroy {resources.length} Resources</p>
                            <p className="text-[10px] text-muted-foreground/40">This action cannot be undone</p>
                        </div>
                    </div>
                    {!loading && (
                        <button onClick={onClose} className="p-1.5 rounded-lg hover:bg-white/[0.06] transition-colors">
                            <X size={14} className="text-muted-foreground/50" />
                        </button>
                    )}
                </div>

                {/* Body — scrollable */}
                <div className="overflow-auto flex-1 p-5 space-y-2">
                    {!done ? (
                        <>
                            <p className="text-xs text-muted-foreground/60 mb-3 leading-relaxed">
                                The following {resources.length} resources will be permanently destroyed from AWS:
                            </p>
                            {resources.map((r, i) => (
                                <div key={i} className="flex items-center gap-2.5 p-2.5 rounded-lg bg-white/[0.02] border border-border/20">
                                    <div className="w-7 h-7 rounded-md bg-white/[0.04] flex items-center justify-center shrink-0">
                                        {getResourceIcon(r.type)}
                                    </div>
                                    <div className="min-w-0">
                                        <p className="text-xs font-mono text-foreground/80 truncate">{r.address}</p>
                                        <p className="text-[10px] text-muted-foreground/40">{getResourceLabel(r.type)}</p>
                                    </div>
                                </div>
                            ))}
                        </>
                    ) : (
                        <>
                            {/* Summary banner */}
                            <div className={`flex items-center gap-2 p-3 rounded-xl border text-xs font-medium mb-3 ${allGood ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400' : summary?.succeeded === 0 ? 'bg-red-500/10 border-red-500/20 text-red-400' : 'bg-amber-500/10 border-amber-500/20 text-amber-400'}`}>
                                {allGood ? <CheckCircle2 size={14} /> : <AlertTriangle size={14} />}
                                {allGood
                                    ? `All ${resources.length} resources destroyed successfully`
                                    : `${summary?.succeeded} succeeded, ${summary?.failed} failed`}
                            </div>

                            {/* Per-resource results */}
                            {results.map((r, i) => (
                                <div key={i} className={`rounded-xl border overflow-hidden ${r.success ? 'border-emerald-500/20 bg-emerald-500/5' : 'border-red-500/20 bg-red-500/5'}`}>
                                    <button
                                        className="w-full flex items-center gap-2.5 p-3 text-left"
                                        onClick={() => setExpandedIdx(expandedIdx === i ? null : i)}
                                    >
                                        <div className="shrink-0">
                                            {r.success
                                                ? <CheckCircle2 size={13} className="text-emerald-400" />
                                                : <AlertTriangle size={13} className="text-red-400" />}
                                        </div>
                                        <span className="text-xs font-mono flex-1 truncate text-foreground/70">{r.resource_address}</span>
                                        <span className={`text-[10px] font-semibold shrink-0 ${r.success ? 'text-emerald-400' : 'text-red-400'}`}>
                                            {r.success ? 'Destroyed' : 'Failed'}
                                        </span>
                                    </button>
                                    {expandedIdx === i && r.output && (
                                        <div className="px-3 pb-3">
                                            <pre className="text-[10px] font-mono text-muted-foreground/50 bg-black/30 rounded-lg p-2.5 max-h-28 overflow-auto whitespace-pre-wrap leading-relaxed">
                                                {r.output}
                                            </pre>
                                        </div>
                                    )}
                                </div>
                            ))}
                        </>
                    )}
                </div>

                {/* Footer */}
                <div className="px-5 py-4 border-t border-border/20 shrink-0">
                    {!done ? (
                        <div className="flex gap-2">
                            <button
                                onClick={onClose}
                                disabled={loading}
                                className="flex-1 px-4 py-2.5 rounded-xl border border-border/30 text-xs text-muted-foreground hover:bg-white/[0.04] transition-all disabled:opacity-40"
                            >
                                Cancel
                            </button>
                            <button
                                onClick={handleDestroy}
                                disabled={loading}
                                className="flex-1 px-4 py-2.5 rounded-xl bg-red-500/10 border border-red-500/30 text-red-400 text-xs font-semibold hover:bg-red-500/20 transition-all flex items-center justify-center gap-2 disabled:opacity-50"
                            >
                                {loading
                                    ? <><Loader2 size={13} className="animate-spin" /> Destroying…</>
                                    : <><Trash2 size={13} /> Destroy All {resources.length}</>}
                            </button>
                        </div>
                    ) : (
                        <button
                            onClick={() => { onDone(); onClose(); }}
                            className="w-full px-4 py-2.5 rounded-xl border border-border/30 text-xs text-muted-foreground hover:bg-white/[0.04] transition-all"
                        >
                            Close & Refresh
                        </button>
                    )}
                </div>
            </div>
        </div>
    );
};

// ── Main Component ────────────────────────────────────────────────

export const MonitoringTab: React.FC<Props> = ({ projectId }) => {
    const [data, setData] = useState<MetricsResponse | null>(null);
    const [stateResources, setStateResources] = useState<StateResource[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');
    const [activeTab, setActiveTab] = useState<'metrics' | 'state'>('metrics');

    // Single-resource destroy
    const [singleDestroyTarget, setSingleDestroyTarget] = useState<StateResource | null>(null);

    // Multi-select
    const [selected, setSelected] = useState<Set<string>>(new Set());
    const [showBatchModal, setShowBatchModal] = useState(false);

    const fetchMetrics = useCallback(async () => {
        setLoading(true);
        setError('');
        setSelected(new Set());
        try {
            const [metricsRes, stateRes] = await Promise.allSettled([
                api.get<MetricsResponse>(`/projects/${projectId}/metrics`),
                api.get<{ resources: StateResource[] }>(`/projects/${projectId}/resources`),
            ]);
            if (metricsRes.status === 'fulfilled') setData(metricsRes.value.data);
            if (stateRes.status === 'fulfilled') setStateResources(stateRes.value.data.resources || []);
            else if (metricsRes.status === 'rejected')
                setError((metricsRes.reason as any).response?.data?.detail || 'Failed to fetch metrics');
        } finally {
            setLoading(false);
        }
    }, [projectId]);

    useEffect(() => { fetchMetrics(); }, [fetchMetrics]);

    // Select helpers
    const allSelected = stateResources.length > 0 && selected.size === stateResources.length;
    const someSelected = selected.size > 0 && !allSelected;

    const toggleAll = () => {
        if (allSelected) setSelected(new Set());
        else setSelected(new Set(stateResources.map(r => r.address)));
    };

    const toggleOne = (addr: string) => {
        setSelected(prev => {
            const next = new Set(prev);
            if (next.has(addr)) next.delete(addr);
            else next.add(addr);
            return next;
        });
    };

    const selectedResources = stateResources.filter(r => selected.has(r.address));

    if (loading) {
        return (
            <div className="flex items-center justify-center h-full">
                <div className="flex flex-col items-center gap-3">
                    <div className="w-10 h-10 rounded-full border-2 border-primary/30 border-t-primary animate-spin" />
                    <p className="text-sm text-muted-foreground">Loading metrics…</p>
                </div>
            </div>
        );
    }

    const hasNoDeployment = !stateResources.length
        && data?.message
        && (!data.resources || data.resources.length === 0)
        && !data.total_resources_in_state;

    if (hasNoDeployment) {
        return (
            <div className="flex flex-col items-center justify-center h-full gap-5 animate-fade-in">
                <div className="w-20 h-20 rounded-2xl bg-gradient-to-br from-blue-500/10 to-purple-500/10 border border-primary/10 flex items-center justify-center">
                    <Activity size={36} className="text-primary/30" />
                </div>
                <div className="text-center space-y-2">
                    <h3 className="text-lg font-semibold">No Infrastructure Deployed</h3>
                    <p className="text-xs text-muted-foreground/50 max-w-[280px] leading-relaxed">
                        Deploy your architecture first, then return here to monitor and manage resources.
                    </p>
                </div>
            </div>
        );
    }

    const totalRes = stateResources.length || data?.total_resources_in_state || 0;
    const healthyCount = data?.healthy_count || totalRes;
    const unhealthyCount = data?.unhealthy_count || 0;

    return (
        <>
            {/* Single-resource legacy modal (kept for hover-destroy) */}
            {singleDestroyTarget && (
                <BatchDestroyModal
                    resources={[singleDestroyTarget]}
                    projectId={projectId}
                    onClose={() => setSingleDestroyTarget(null)}
                    onDone={fetchMetrics}
                />
            )}
            {/* Batch destroy modal */}
            {showBatchModal && (
                <BatchDestroyModal
                    resources={selectedResources}
                    projectId={projectId}
                    onClose={() => setShowBatchModal(false)}
                    onDone={() => { fetchMetrics(); setSelected(new Set()); }}
                />
            )}

            <div className="h-full flex flex-col gap-4 animate-fade-in overflow-auto">
                {/* Header */}
                <div className="glass-card p-5">
                    <div className="flex items-center justify-between">
                        <div className="flex items-center gap-4">
                            <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-green-500/10 to-teal-500/10 border border-green-500/10 flex items-center justify-center">
                                <Activity size={22} className="text-green-400" />
                            </div>
                            <div>
                                <h3 className="text-sm font-semibold mb-1">Infrastructure Health</h3>
                                <div className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[11px] font-semibold badge-success">
                                    <CheckCircle2 size={12} />
                                    <span>{totalRes} Resources Active</span>
                                </div>
                            </div>
                        </div>
                        <button onClick={fetchMetrics} className="p-2 rounded-lg text-muted-foreground/50 hover:text-foreground hover:bg-white/[0.04] transition-all" title="Refresh">
                            <RefreshCw size={14} />
                        </button>
                    </div>
                    {error && (
                        <div className="mt-3 p-2.5 bg-amber-500/10 text-amber-400 text-xs rounded-lg border border-amber-500/20 flex items-center gap-2">
                            <AlertTriangle size={14} /><span>{error}</span>
                        </div>
                    )}
                    {data?.error && (
                        <div className="mt-3 p-2.5 bg-amber-500/10 text-amber-400 text-xs rounded-lg border border-amber-500/20 flex items-center gap-2">
                            <AlertTriangle size={14} /><span>{data.error}</span>
                        </div>
                    )}
                </div>

                {/* Stats */}
                <div className="grid grid-cols-3 gap-3">
                    {[
                        { label: 'Healthy', value: healthyCount, icon: <CheckCircle2 size={16} className="text-emerald-400" />, color: 'bg-emerald-500/10' },
                        { label: 'Issues', value: unhealthyCount, icon: <AlertTriangle size={16} className="text-red-400" />, color: 'bg-red-500/10' },
                        { label: 'Total', value: totalRes, icon: <BarChart3 size={16} className="text-blue-400" />, color: 'bg-blue-500/10' },
                    ].map(s => (
                        <div key={s.label} className="glass-card p-4 flex items-center gap-3">
                            <div className={`w-9 h-9 rounded-lg ${s.color} flex items-center justify-center`}>{s.icon}</div>
                            <div>
                                <p className="text-xl font-bold">{s.value}</p>
                                <p className="text-[10px] text-muted-foreground/40 uppercase tracking-wider">{s.label}</p>
                            </div>
                        </div>
                    ))}
                </div>

                {/* Tabs */}
                <div className="flex gap-1 p-1 glass-card rounded-xl">
                    {(['metrics', 'state'] as const).map(tab => (
                        <button
                            key={tab}
                            onClick={() => setActiveTab(tab)}
                            className={`flex-1 flex items-center justify-center gap-1.5 py-2 rounded-lg text-xs font-medium transition-all
                                ${activeTab === tab ? 'bg-white/[0.07] text-foreground' : 'text-muted-foreground/50 hover:text-muted-foreground'}`}
                        >
                            {tab === 'metrics' ? <><Wifi size={12} />Metrics View</> : (
                                <>
                                    <Terminal size={12} />State Resources
                                    {stateResources.length > 0 && (
                                        <span className="ml-1 px-1.5 py-0.5 rounded-full bg-primary/20 text-primary text-[9px] font-bold">
                                            {stateResources.length}
                                        </span>
                                    )}
                                </>
                            )}
                        </button>
                    ))}
                </div>

                {/* Metrics view */}
                {activeTab === 'metrics' && (
                    <div className="glass-card flex-1 overflow-hidden flex flex-col">
                        <div className="p-4 border-b border-border/30 flex items-center gap-2">
                            <Wifi size={14} className="text-muted-foreground/50" />
                            <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground/60">Deployed Resources</h3>
                        </div>
                        <div className="flex-1 overflow-auto p-3 space-y-2">
                            {data?.resources && data.resources.length > 0 ? data.resources.map((res, i) => (
                                <div key={i} className="flex items-center gap-3 p-3 rounded-lg bg-white/[0.02] border border-border/20 hover:border-border/40 transition-all">
                                    <div className="w-8 h-8 rounded-lg bg-white/[0.04] flex items-center justify-center shrink-0">{getResourceIcon(res.type)}</div>
                                    <div className="flex-1 min-w-0">
                                        <p className="text-xs font-medium truncate">{res.name}</p>
                                        <p className="text-[10px] text-muted-foreground/40">{getResourceLabel(res.type)}</p>
                                    </div>
                                    <div className="flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-medium badge-success">
                                        <CheckCircle2 size={10} /><span>Active</span>
                                    </div>
                                </div>
                            )) : (
                                <div className="flex flex-col items-center justify-center h-full gap-3 py-12">
                                    <p className="text-xs text-muted-foreground/40">Resource details loading from terraform state…</p>
                                </div>
                            )}
                        </div>
                    </div>
                )}

                {/* State Resources view with multi-select */}
                {activeTab === 'state' && (
                    <div className="glass-card flex-1 overflow-hidden flex flex-col min-h-0">
                        {/* Toolbar */}
                        <div className="p-3 border-b border-border/30 flex items-center gap-2 shrink-0">
                            {/* Select-all toggle */}
                            <button
                                onClick={toggleAll}
                                className="p-1 rounded hover:bg-white/[0.06] transition-colors shrink-0"
                                title={allSelected ? 'Deselect all' : 'Select all'}
                            >
                                {allSelected
                                    ? <CheckSquare size={15} className="text-primary" />
                                    : someSelected
                                        ? <MinusSquare size={15} className="text-primary/70" />
                                        : <Square size={15} className="text-muted-foreground/40" />}
                            </button>

                            <div className="flex items-center gap-2 flex-1 min-w-0">
                                <Terminal size={13} className="text-muted-foreground/50 shrink-0" />
                                <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground/60 truncate">
                                    {selected.size > 0 ? `${selected.size} selected` : 'Terraform State'}
                                </h3>
                            </div>

                            {/* Bulk destroy button — shown only when ≥1 selected */}
                            {selected.size > 0 && (
                                <button
                                    onClick={() => setShowBatchModal(true)}
                                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-red-500/10 border border-red-500/30 text-red-400 text-xs font-semibold hover:bg-red-500/20 transition-all shrink-0"
                                >
                                    <Trash2 size={12} />
                                    Destroy {selected.size}
                                </button>
                            )}
                        </div>

                        {/* Resource list */}
                        <div className="flex-1 overflow-auto p-2 space-y-1">
                            {stateResources.length > 0 ? stateResources.map((res) => {
                                const isChecked = selected.has(res.address);
                                return (
                                    <div
                                        key={res.address}
                                        onClick={() => toggleOne(res.address)}
                                        className={`group flex items-center gap-2.5 p-3 rounded-xl border cursor-pointer transition-all select-none
                                            ${isChecked
                                                ? 'bg-red-500/5 border-red-500/25'
                                                : 'bg-white/[0.02] border-border/20 hover:border-border/40'}`}
                                    >
                                        {/* Checkbox */}
                                        <div className="shrink-0">
                                            {isChecked
                                                ? <CheckSquare size={15} className="text-red-400" />
                                                : <Square size={15} className="text-muted-foreground/25 group-hover:text-muted-foreground/50 transition-colors" />}
                                        </div>

                                        {/* Icon */}
                                        <div className="w-8 h-8 rounded-lg bg-white/[0.04] flex items-center justify-center shrink-0">
                                            {getResourceIcon(res.type)}
                                        </div>

                                        {/* Info */}
                                        <div className="flex-1 min-w-0">
                                            <p className="text-xs font-mono font-medium truncate text-foreground/80">{res.address}</p>
                                            <p className="text-[10px] text-muted-foreground/40">{getResourceLabel(res.type)}</p>
                                        </div>

                                        {/* Individual destroy (hover only, when nothing selected) */}
                                        {selected.size === 0 && (
                                            <button
                                                onClick={(e) => { e.stopPropagation(); setSingleDestroyTarget(res); }}
                                                className="opacity-0 group-hover:opacity-100 flex items-center gap-1 px-2 py-1 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-[10px] font-medium hover:bg-red-500/20 transition-all shrink-0"
                                            >
                                                <Trash2 size={11} />Destroy
                                            </button>
                                        )}
                                    </div>
                                );
                            }) : (
                                <div className="flex flex-col items-center justify-center py-16 gap-3">
                                    <Terminal size={28} className="text-muted-foreground/20" />
                                    <p className="text-xs text-muted-foreground/40">No resources in Terraform state</p>
                                </div>
                            )}
                        </div>
                    </div>
                )}
            </div>
        </>
    );
};
