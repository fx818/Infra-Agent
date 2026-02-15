import React, { useEffect, useState } from 'react';
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
    Shield
} from 'lucide-react';

interface Props {
    projectId: number;
}

interface ResourceMetric {
    name: string;
    type: string;
    metrics?: Record<string, any>;
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

const getResourceIcon = (type: string | undefined) => {
    const t = (type || '').toLowerCase();
    if (t.includes('lambda')) return <Zap size={16} className="text-amber-400" />;
    if (t.includes('dynamodb') || t.includes('rds')) return <Database size={16} className="text-blue-400" />;
    if (t.includes('apigateway')) return <Globe size={16} className="text-green-400" />;
    if (t.includes('iam')) return <Shield size={16} className="text-purple-400" />;
    if (t.includes('s3')) return <Server size={16} className="text-cyan-400" />;
    return <Server size={16} className="text-muted-foreground/60" />;
};

const getResourceLabel = (type: string | undefined) => {
    const labels: Record<string, string> = {
        'aws_lambda_function': 'Lambda Function',
        'aws_dynamodb_table': 'DynamoDB Table',
        'aws_apigatewayv2_api': 'API Gateway',
        'aws_apigatewayv2_stage': 'API Stage',
        'aws_apigatewayv2_route': 'API Route',
        'aws_apigatewayv2_integration': 'API Integration',
        'aws_iam_role': 'IAM Role',
        'aws_iam_role_policy_attachment': 'IAM Policy',
        'aws_lambda_permission': 'Lambda Permission',
        'aws_s3_bucket': 'S3 Bucket',
        'aws_s3_bucket_policy': 'S3 Bucket Policy',
        'aws_cloudfront_distribution': 'CloudFront CDN',
        'aws_route53_zone': 'Route53 Zone',
        'aws_acm_certificate': 'ACM Certificate',
    };
    return labels[type || ''] || (type || 'resource').replace('aws_', '').replace(/_/g, ' ');
};

export const MonitoringTab: React.FC<Props> = ({ projectId }) => {
    const [data, setData] = useState<MetricsResponse | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');

    useEffect(() => {
        fetchMetrics();
    }, [projectId]);

    const fetchMetrics = async () => {
        setLoading(true);
        setError('');
        try {
            const res = await api.get<MetricsResponse>(`/projects/${projectId}/metrics`);
            setData(res.data);
        } catch (err: any) {
            setError(err.response?.data?.detail || err.message || 'Failed to fetch metrics');
        } finally {
            setLoading(false);
        }
    };

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

    // No deployment yet
    if (data?.message && (!data.resources || data.resources.length === 0) && !data.total_resources_in_state) {
        return (
            <div className="flex flex-col items-center justify-center h-full gap-5 animate-fade-in">
                <div className="relative">
                    <div className="w-20 h-20 rounded-2xl bg-gradient-to-br from-blue-500/10 to-purple-500/10 border border-primary/10 flex items-center justify-center">
                        <Activity size={36} className="text-primary/30" />
                    </div>
                    <div className="absolute -top-1 -right-1 w-4 h-4 rounded-full bg-yellow-500/20 border border-yellow-500/30 flex items-center justify-center">
                        <div className="w-1.5 h-1.5 rounded-full bg-yellow-500" />
                    </div>
                </div>
                <div className="text-center space-y-2">
                    <h3 className="text-lg font-semibold">No Infrastructure Deployed</h3>
                    <p className="text-xs text-muted-foreground/50 max-w-[280px] leading-relaxed">
                        Deploy your architecture first, then return here to monitor resource health and metrics.
                    </p>
                </div>
            </div>
        );
    }

    const totalRes = data?.total_resources_in_state || 0;
    const healthyCount = data?.healthy_count || totalRes;
    const unhealthyCount = data?.unhealthy_count || 0;

    return (
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
                    <button
                        onClick={fetchMetrics}
                        className="p-2 rounded-lg text-muted-foreground/50 hover:text-foreground hover:bg-white/[0.04] transition-all"
                        title="Refresh metrics"
                    >
                        <RefreshCw size={14} />
                    </button>
                </div>

                {error && (
                    <div className="mt-3 p-2.5 bg-amber-500/10 text-amber-400 text-xs rounded-lg border border-amber-500/20 flex items-center gap-2">
                        <AlertTriangle size={14} />
                        <span>{error}</span>
                    </div>
                )}
                {data?.error && (
                    <div className="mt-3 p-2.5 bg-amber-500/10 text-amber-400 text-xs rounded-lg border border-amber-500/20 flex items-center gap-2">
                        <AlertTriangle size={14} />
                        <span>{data.error}</span>
                    </div>
                )}
            </div>

            {/* Stats Grid */}
            <div className="grid grid-cols-3 gap-3">
                <div className="glass-card p-4 flex items-center gap-3">
                    <div className="w-9 h-9 rounded-lg bg-emerald-500/10 flex items-center justify-center">
                        <CheckCircle2 size={16} className="text-emerald-400" />
                    </div>
                    <div>
                        <p className="text-xl font-bold">{healthyCount}</p>
                        <p className="text-[10px] text-muted-foreground/40 uppercase tracking-wider">Healthy</p>
                    </div>
                </div>
                <div className="glass-card p-4 flex items-center gap-3">
                    <div className="w-9 h-9 rounded-lg bg-red-500/10 flex items-center justify-center">
                        <AlertTriangle size={16} className="text-red-400" />
                    </div>
                    <div>
                        <p className="text-xl font-bold">{unhealthyCount}</p>
                        <p className="text-[10px] text-muted-foreground/40 uppercase tracking-wider">Issues</p>
                    </div>
                </div>
                <div className="glass-card p-4 flex items-center gap-3">
                    <div className="w-9 h-9 rounded-lg bg-blue-500/10 flex items-center justify-center">
                        <BarChart3 size={16} className="text-blue-400" />
                    </div>
                    <div>
                        <p className="text-xl font-bold">{totalRes}</p>
                        <p className="text-[10px] text-muted-foreground/40 uppercase tracking-wider">Total</p>
                    </div>
                </div>
            </div>

            {/* Resource List */}
            <div className="glass-card flex-1 overflow-hidden flex flex-col">
                <div className="p-4 border-b border-border/30 flex items-center gap-2">
                    <Wifi size={14} className="text-muted-foreground/50" />
                    <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground/60">
                        Deployed Resources
                    </h3>
                </div>
                <div className="flex-1 overflow-auto p-3 space-y-2">
                    {data?.resources && data.resources.length > 0 ? (
                        data.resources.map((res, i) => (
                            <div key={i} className="flex items-center gap-3 p-3 rounded-lg bg-white/[0.02] border border-border/20 hover:border-border/40 transition-all">
                                <div className="w-8 h-8 rounded-lg bg-white/[0.04] flex items-center justify-center shrink-0">
                                    {getResourceIcon(res.type)}
                                </div>
                                <div className="flex-1 min-w-0">
                                    <p className="text-xs font-medium truncate">{res.name}</p>
                                    <p className="text-[10px] text-muted-foreground/40">{getResourceLabel(res.type)}</p>
                                </div>
                                <div className="flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-medium badge-success">
                                    <CheckCircle2 size={10} />
                                    <span>Active</span>
                                </div>
                            </div>
                        ))
                    ) : (
                        <div className="flex flex-col items-center justify-center h-full gap-3 py-12">
                            <p className="text-xs text-muted-foreground/40">Resource details loading from terraform state…</p>
                            <p className="text-[10px] text-muted-foreground/25">
                                {totalRes} resources tracked • CloudWatch metrics may take a few minutes to populate
                            </p>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
};
