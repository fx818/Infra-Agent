import React, { useEffect, useState } from 'react';
import { awsExplorerApi, type AWSResourcesResponse, type ResourceDeleteItem, type ResourceDeleteResult } from '../api/awsExplorer';
import {
    Globe,
    Server,
    HardDrive,
    Zap,
    Database,
    Container,
    Table,
    Mail,
    Bell,
    Cpu,
    Network,
    Play,
    Shield,
    GitMerge,
    RefreshCw,
    ChevronDown,
    ChevronRight,
    AlertCircle,
    Search,
    MapPin,
    Trash2,
    CheckCircle2,
    AlertTriangle,
    X,
    Loader2,
    Square,
    CheckSquare,
    MinusSquare,
} from 'lucide-react';

// Map icon names from backend to lucide components
const ICON_MAP: Record<string, React.ElementType> = {
    server: Server,
    'hard-drive': HardDrive,
    zap: Zap,
    database: Database,
    container: Container,
    table: Table,
    mail: Mail,
    bell: Bell,
    globe: Globe,
    cpu: Cpu,
    network: Network,
    play: Play,
    shield: Shield,
    'git-merge': GitMerge,
};

const SERVICE_COLORS: Record<string, string> = {
    EC2: 'from-orange-500 to-amber-500',
    S3: 'from-green-500 to-emerald-500',
    Lambda: 'from-amber-500 to-yellow-500',
    RDS: 'from-blue-500 to-indigo-500',
    ECS: 'from-orange-400 to-orange-600',
    DynamoDB: 'from-blue-400 to-blue-600',
    SQS: 'from-purple-500 to-violet-500',
    SNS: 'from-red-400 to-pink-500',
    CloudFront: 'from-purple-400 to-indigo-500',
    ElastiCache: 'from-red-500 to-rose-500',
    'API Gateway': 'from-fuchsia-500 to-purple-500',
    'App Runner': 'from-pink-400 to-rose-500',
    VPC: 'from-teal-500 to-cyan-500',
    'Load Balancer': 'from-indigo-400 to-blue-500',
};

const STATE_COLORS: Record<string, string> = {
    running: 'text-emerald-400 bg-emerald-400/10 border-emerald-400/20',
    available: 'text-emerald-400 bg-emerald-400/10 border-emerald-400/20',
    active: 'text-emerald-400 bg-emerald-400/10 border-emerald-400/20',
    'ACTIVE': 'text-emerald-400 bg-emerald-400/10 border-emerald-400/20',
    'RUNNING': 'text-emerald-400 bg-emerald-400/10 border-emerald-400/20',
    stopped: 'text-amber-400 bg-amber-400/10 border-amber-400/20',
    terminated: 'text-red-400 bg-red-400/10 border-red-400/20',
    deleting: 'text-red-400 bg-red-400/10 border-red-400/20',
    pending: 'text-blue-400 bg-blue-400/10 border-blue-400/20',
    'CREATE_FAILED': 'text-red-400 bg-red-400/10 border-red-400/20',
};

const selKey = (service: string, id: string) => `${service}::${id}`;

// ── Delete Confirmation Modal ─────────────────────────────────────

interface DeleteModalProps {
    resources: ResourceDeleteItem[];
    region: string;
    onClose: () => void;
    onDone: () => void;
}

const DeleteModal: React.FC<DeleteModalProps> = ({ resources, region, onClose, onDone }) => {
    const [loading, setLoading] = useState(false);
    const [done, setDone] = useState(false);
    const [results, setResults] = useState<ResourceDeleteResult[]>([]);
    const [summary, setSummary] = useState<{ succeeded: number; failed: number } | null>(null);

    const handleDelete = async () => {
        setLoading(true);
        try {
            const resp = await awsExplorerApi.deleteResources(region, resources);
            setResults(resp.results);
            setSummary({ succeeded: resp.succeeded, failed: resp.failed });
        } catch (err: any) {
            setResults(resources.map(r => ({
                resource_id: r.resource_id,
                resource_name: r.resource_name,
                service: r.service,
                success: false,
                message: err.response?.data?.detail || err.message || 'Request failed',
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
                            <p className="text-sm font-semibold">
                                Delete {resources.length} Resource{resources.length > 1 ? 's' : ''}
                            </p>
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
                                The following {resources.length} resource{resources.length > 1 ? 's' : ''} will be permanently deleted from AWS:
                            </p>
                            {resources.map((r, i) => (
                                <div key={i} className="flex items-center gap-2.5 p-2.5 rounded-lg bg-white/[0.02] border border-border/20">
                                    <div className="w-7 h-7 rounded-md bg-red-500/10 flex items-center justify-center shrink-0">
                                        <Trash2 size={13} className="text-red-400/70" />
                                    </div>
                                    <div className="min-w-0 flex-1">
                                        <p className="text-xs font-medium text-foreground/80 truncate">{r.resource_name || r.resource_id}</p>
                                        <p className="text-[10px] text-muted-foreground/40">{r.service} · {r.resource_id}</p>
                                    </div>
                                </div>
                            ))}
                        </>
                    ) : (
                        <>
                            {/* Summary banner */}
                            <div className={`flex items-center gap-2 p-3 rounded-xl border text-xs font-medium mb-3 ${allGood
                                ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400'
                                : summary?.succeeded === 0
                                    ? 'bg-red-500/10 border-red-500/20 text-red-400'
                                    : 'bg-amber-500/10 border-amber-500/20 text-amber-400'
                                }`}>
                                {allGood ? <CheckCircle2 size={14} /> : <AlertTriangle size={14} />}
                                {allGood
                                    ? `All ${resources.length} resource${resources.length > 1 ? 's' : ''} deleted successfully`
                                    : `${summary?.succeeded} succeeded, ${summary?.failed} failed`
                                }
                            </div>

                            {/* Per-resource results */}
                            {results.map((r, i) => (
                                <div key={i} className={`rounded-xl border overflow-hidden ${r.success ? 'border-emerald-500/20 bg-emerald-500/5' : 'border-red-500/20 bg-red-500/5'
                                    }`}>
                                    <div className="flex items-start gap-2.5 p-3">
                                        <div className="shrink-0 mt-0.5">
                                            {r.success
                                                ? <CheckCircle2 size={13} className="text-emerald-400" />
                                                : <AlertTriangle size={13} className="text-red-400" />
                                            }
                                        </div>
                                        <div className="flex-1 min-w-0">
                                            <div className="flex items-center gap-2 mb-1">
                                                <p className="text-xs font-medium text-foreground/80">
                                                    {r.resource_name || r.resource_id}
                                                </p>
                                                <span className={`text-[10px] font-semibold shrink-0 px-1.5 py-0.5 rounded-full ${r.success
                                                        ? 'text-emerald-400 bg-emerald-400/10'
                                                        : 'text-red-400 bg-red-400/10'
                                                    }`}>
                                                    {r.success ? 'Deleted' : 'Failed'}
                                                </span>
                                            </div>
                                            <p className={`text-[11px] leading-relaxed break-words whitespace-pre-wrap ${r.success ? 'text-emerald-400/60' : 'text-red-300/70'
                                                }`}>
                                                {r.message}
                                            </p>
                                        </div>
                                    </div>
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
                                onClick={handleDelete}
                                disabled={loading}
                                className="flex-1 px-4 py-2.5 rounded-xl bg-red-500/10 border border-red-500/30 text-red-400 text-xs font-semibold hover:bg-red-500/20 transition-all flex items-center justify-center gap-2 disabled:opacity-50"
                            >
                                {loading
                                    ? <><Loader2 size={13} className="animate-spin" /> Deleting…</>
                                    : <><Trash2 size={13} /> Delete {resources.length} Resource{resources.length > 1 ? 's' : ''}</>
                                }
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


// ── Main Component ─────────────────────────────────────────────────

export const AWSExplorer: React.FC = () => {
    const [regions, setRegions] = useState<string[]>([]);
    const [selectedRegion, setSelectedRegion] = useState('us-east-1');
    const [data, setData] = useState<AWSResourcesResponse | null>(null);
    const [loading, setLoading] = useState(false);
    const [loadingRegions, setLoadingRegions] = useState(true);
    const [error, setError] = useState('');
    const [expandedServices, setExpandedServices] = useState<Set<string>>(new Set());
    const [searchQuery, setSearchQuery] = useState('');
    const [regionDropdownOpen, setRegionDropdownOpen] = useState(false);
    const regionDropdownRef = React.useRef<HTMLDivElement>(null);

    // Selection state
    const [selected, setSelected] = useState<Set<string>>(new Set());
    const [selectedMeta, setSelectedMeta] = useState<Map<string, ResourceDeleteItem>>(new Map());

    // Modal state
    const [deleteModalItems, setDeleteModalItems] = useState<ResourceDeleteItem[] | null>(null);

    // Close dropdown on outside click
    React.useEffect(() => {
        const handler = (e: MouseEvent) => {
            if (regionDropdownRef.current && !regionDropdownRef.current.contains(e.target as Node)) {
                setRegionDropdownOpen(false);
            }
        };
        document.addEventListener('mousedown', handler);
        return () => document.removeEventListener('mousedown', handler);
    }, []);

    useEffect(() => {
        loadRegions();
    }, []);

    useEffect(() => {
        if (selectedRegion) {
            loadResources(selectedRegion);
        }
    }, [selectedRegion]);

    const loadRegions = async () => {
        try {
            const resp = await awsExplorerApi.getRegions();
            setRegions(resp.regions);
        } catch (err: any) {
            console.error('Failed to load regions:', err);
            setRegions([
                'us-east-1', 'us-east-2', 'us-west-1', 'us-west-2',
                'eu-west-1', 'eu-west-2', 'eu-central-1',
                'ap-south-1', 'ap-southeast-1', 'ap-southeast-2', 'ap-northeast-1',
            ]);
        } finally {
            setLoadingRegions(false);
        }
    };

    const loadResources = async (region: string) => {
        setLoading(true);
        setError('');
        clearSelection();
        try {
            const resp = await awsExplorerApi.getResources(region);
            setData(resp);
            const expanded = new Set<string>();
            resp.services.forEach(s => {
                if (s.count > 0 && s.count <= 10) expanded.add(s.name);
            });
            setExpandedServices(expanded);
        } catch (err: any) {
            setError(err.response?.data?.detail || err.message || 'Failed to load resources');
            setData(null);
        } finally {
            setLoading(false);
        }
    };

    const toggleService = (name: string) => {
        setExpandedServices(prev => {
            const next = new Set(prev);
            if (next.has(name)) next.delete(name);
            else next.add(name);
            return next;
        });
    };

    const getStateColor = (state: string) => {
        return STATE_COLORS[state] || 'text-white/50 bg-white/5 border-white/10';
    };

    // ── Selection helpers ──────────────────────────────────────────

    const toggleOne = (service: string, resourceId: string, resourceName: string) => {
        const key = selKey(service, resourceId);
        setSelected(prev => {
            const next = new Set(prev);
            if (next.has(key)) next.delete(key);
            else next.add(key);
            return next;
        });
        setSelectedMeta(prev => {
            const next = new Map(prev);
            if (next.has(key)) next.delete(key);
            else next.set(key, { service, resource_id: resourceId, resource_name: resourceName });
            return next;
        });
    };

    const toggleAllInService = (serviceName: string, resources: { id: string; name: string }[]) => {
        const allKeys = resources.map(r => selKey(serviceName, r.id));
        const allSelected = allKeys.every(k => selected.has(k));

        setSelected(prev => {
            const next = new Set(prev);
            allKeys.forEach(k => allSelected ? next.delete(k) : next.add(k));
            return next;
        });
        setSelectedMeta(prev => {
            const next = new Map(prev);
            if (allSelected) {
                allKeys.forEach(k => next.delete(k));
            } else {
                resources.forEach(r =>
                    next.set(selKey(serviceName, r.id), {
                        service: serviceName,
                        resource_id: r.id,
                        resource_name: r.name,
                    })
                );
            }
            return next;
        });
    };

    const clearSelection = () => {
        setSelected(new Set());
        setSelectedMeta(new Map());
    };

    // ── Delete triggers ────────────────────────────────────────────

    const openDeleteSingle = (service: string, resourceId: string, resourceName: string) => {
        setDeleteModalItems([{ service, resource_id: resourceId, resource_name: resourceName }]);
    };

    const openDeleteBatch = () => {
        const items = Array.from(selectedMeta.values());
        if (items.length > 0) setDeleteModalItems(items);
    };

    const handleDeleteDone = () => {
        clearSelection();
        loadResources(selectedRegion);
    };

    // Filter services by search
    const filteredServices = data?.services.filter(service => {
        if (!searchQuery) return true;
        const q = searchQuery.toLowerCase();
        if (service.name.toLowerCase().includes(q)) return true;
        return service.resources.some(r =>
            r.name.toLowerCase().includes(q) ||
            r.id.toLowerCase().includes(q) ||
            r.type.toLowerCase().includes(q)
        );
    }) || [];

    return (
        <>
            {/* Delete Modal */}
            {deleteModalItems && (
                <DeleteModal
                    resources={deleteModalItems}
                    region={selectedRegion}
                    onClose={() => setDeleteModalItems(null)}
                    onDone={handleDeleteDone}
                />
            )}

            <div className="space-y-6 max-w-6xl mx-auto animate-fade-in">
                {/* Header */}
                <div className="flex items-end justify-between">
                    <div>
                        <div className="flex items-center gap-3">
                            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-cyan-500/20 to-blue-500/20 border border-cyan-500/20 flex items-center justify-center">
                                <Globe size={20} className="text-cyan-400" />
                            </div>
                            <div>
                                <h1 className="text-2xl font-bold tracking-tight">AWS Infrastructure Explorer</h1>
                                <p className="text-muted-foreground text-sm mt-0.5">
                                    Discover and manage all resources across your AWS account
                                </p>
                            </div>
                        </div>
                    </div>
                    <button
                        onClick={() => loadResources(selectedRegion)}
                        disabled={loading}
                        className="flex items-center gap-2 px-3 py-2 rounded-lg text-xs font-medium text-muted-foreground hover:text-foreground hover:bg-white/[0.04] border border-border/30 transition-all disabled:opacity-50"
                    >
                        <RefreshCw size={13} className={loading ? 'animate-spin' : ''} />
                        Refresh
                    </button>
                </div>

                {/* Region Selector + Search + Batch Action */}
                <div className="flex items-center gap-3">
                    <div className="relative" ref={regionDropdownRef}>
                        <button
                            onClick={() => setRegionDropdownOpen(!regionDropdownOpen)}
                            disabled={loadingRegions}
                            className="flex items-center gap-2 pl-3 pr-3 py-2.5 rounded-xl text-sm font-medium bg-white/[0.04] border border-border/40 text-foreground cursor-pointer hover:bg-white/[0.06] transition-all focus:outline-none focus:ring-2 focus:ring-primary/30 min-w-[220px] disabled:opacity-50"
                        >
                            <MapPin size={14} className="text-cyan-400 shrink-0" />
                            <span className="flex-1 text-left truncate">{selectedRegion}</span>
                            <ChevronDown size={14} className={`text-muted-foreground/50 transition-transform duration-200 ${regionDropdownOpen ? 'rotate-180' : ''}`} />
                        </button>

                        {regionDropdownOpen && (
                            <div className="absolute top-full left-0 mt-2 w-[280px] max-h-[340px] overflow-y-auto rounded-xl bg-[#1a1d2e]/95 backdrop-blur-xl border border-border/50 shadow-2xl shadow-black/40 z-50 py-1 animate-fade-in">
                                <p className="px-3 py-2 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground/40 border-b border-border/20 mb-1">
                                    Select Region
                                </p>
                                {regions.map(r => (
                                    <button
                                        key={r}
                                        onClick={() => {
                                            setSelectedRegion(r);
                                            setRegionDropdownOpen(false);
                                        }}
                                        className={`w-full flex items-center gap-3 px-3 py-2 text-left text-sm transition-all ${r === selectedRegion
                                            ? 'bg-primary/10 text-primary'
                                            : 'text-foreground/80 hover:bg-white/[0.04] hover:text-foreground'
                                            }`}
                                    >
                                        <MapPin size={12} className={r === selectedRegion ? 'text-primary' : 'text-muted-foreground/30'} />
                                        <span className="font-mono text-xs flex-1">{r}</span>
                                        {r === selectedRegion && (
                                            <span className="w-1.5 h-1.5 rounded-full bg-primary shadow-sm shadow-primary/50" />
                                        )}
                                    </button>
                                ))}
                            </div>
                        )}
                    </div>

                    <div className="relative flex-1 max-w-md">
                        <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground/50" />
                        <input
                            type="text"
                            placeholder="Search resources by name, ID, or type..."
                            value={searchQuery}
                            onChange={(e) => setSearchQuery(e.target.value)}
                            className="w-full pl-9 pr-4 py-2.5 rounded-xl text-sm bg-white/[0.04] border border-border/40 text-foreground placeholder:text-muted-foreground/30 focus:outline-none focus:ring-2 focus:ring-primary/30 transition-all"
                        />
                    </div>

                    {data && !loading && (
                        <span className="text-xs text-muted-foreground/50 font-mono whitespace-nowrap">
                            {data.total_resources} resource{data.total_resources !== 1 ? 's' : ''}
                        </span>
                    )}

                    {/* Batch delete button */}
                    {selected.size > 0 && (
                        <button
                            onClick={openDeleteBatch}
                            className="flex items-center gap-1.5 px-4 py-2.5 rounded-xl bg-red-500/10 border border-red-500/30 text-red-400 text-xs font-semibold hover:bg-red-500/20 transition-all shrink-0"
                        >
                            <Trash2 size={13} />
                            Delete {selected.size}
                        </button>
                    )}
                </div>

                {/* Error */}
                {error && (
                    <div className="p-4 bg-destructive/10 text-destructive text-sm rounded-xl border border-destructive/20 flex items-start gap-3 animate-fade-in">
                        <AlertCircle size={16} className="mt-0.5 shrink-0" />
                        <div>
                            <p className="font-semibold text-xs mb-1">Failed to load resources</p>
                            <p className="text-destructive/80 text-xs">{error}</p>
                        </div>
                    </div>
                )}

                {/* Loading */}
                {loading && (
                    <div className="flex flex-col items-center justify-center py-20 gap-4">
                        <div className="w-12 h-12 rounded-full border-2 border-primary/30 border-t-primary animate-spin" />
                        <p className="text-sm text-muted-foreground">Scanning AWS resources in <span className="font-mono text-primary">{selectedRegion}</span>...</p>
                        <p className="text-[11px] text-muted-foreground/40">This may take a few seconds</p>
                    </div>
                )}

                {/* Empty */}
                {!loading && data && data.total_resources === 0 && (
                    <div className="glass-card p-16 text-center">
                        <div className="w-16 h-16 rounded-2xl bg-white/[0.03] flex items-center justify-center mx-auto mb-4">
                            <Globe size={32} className="text-muted-foreground/20" />
                        </div>
                        <h3 className="text-lg font-semibold mb-2">No resources found</h3>
                        <p className="text-muted-foreground text-sm">
                            No AWS resources were detected in <span className="font-mono text-primary">{selectedRegion}</span>.
                            Try selecting a different region.
                        </p>
                    </div>
                )}

                {/* Service Groups */}
                {!loading && filteredServices.map((service) => {
                    const IconComp = ICON_MAP[service.icon] || Server;
                    const isExpanded = expandedServices.has(service.name);
                    const colorClass = SERVICE_COLORS[service.name] || 'from-gray-500 to-gray-600';

                    const visibleResources = service.resources.filter(r => {
                        if (!searchQuery) return true;
                        const q = searchQuery.toLowerCase();
                        return r.name.toLowerCase().includes(q) ||
                            r.id.toLowerCase().includes(q) ||
                            r.type.toLowerCase().includes(q);
                    });

                    const allKeys = visibleResources.map(r => selKey(service.name, r.id));
                    const allChecked = allKeys.length > 0 && allKeys.every(k => selected.has(k));
                    const someChecked = allKeys.some(k => selected.has(k));

                    return (
                        <div key={service.name} className="glass-card overflow-hidden">
                            {/* Service Header */}
                            <button
                                onClick={() => toggleService(service.name)}
                                className="w-full p-4 flex items-center gap-4 hover:bg-white/[0.02] transition-all"
                            >
                                <div className={`w-10 h-10 rounded-xl bg-gradient-to-br ${colorClass} flex items-center justify-center shadow-lg`}>
                                    <IconComp size={18} className="text-white" />
                                </div>
                                <div className="flex-1 text-left">
                                    <h3 className="text-sm font-semibold">{service.name}</h3>
                                    <p className="text-[11px] text-muted-foreground/50">
                                        {service.count} resource{service.count !== 1 ? 's' : ''}
                                        {someChecked && ` · ${allKeys.filter(k => selected.has(k)).length} selected`}
                                    </p>
                                </div>
                                <span className="flex items-center gap-2 text-[11px] font-bold text-muted-foreground/40 bg-white/[0.04] px-3 py-1.5 rounded-full border border-border/20">
                                    {service.count}
                                </span>
                                {isExpanded
                                    ? <ChevronDown size={16} className="text-muted-foreground/40" />
                                    : <ChevronRight size={16} className="text-muted-foreground/40" />
                                }
                            </button>

                            {/* Resources Table */}
                            {isExpanded && (
                                <div className="border-t border-border/20">
                                    <div className="overflow-x-auto">
                                        <table className="w-full text-xs">
                                            <thead>
                                                <tr className="text-left text-muted-foreground/40 border-b border-border/10">
                                                    <th className="px-4 py-3 w-10">
                                                        <button
                                                            onClick={() => toggleAllInService(service.name, visibleResources)}
                                                            className="p-0.5 rounded hover:bg-white/[0.06] transition-colors"
                                                            title={allChecked ? 'Deselect all' : 'Select all'}
                                                        >
                                                            {allChecked
                                                                ? <CheckSquare size={15} className="text-red-400" />
                                                                : someChecked
                                                                    ? <MinusSquare size={15} className="text-primary/70" />
                                                                    : <Square size={15} className="text-muted-foreground/25" />
                                                            }
                                                        </button>
                                                    </th>
                                                    <th className="px-4 py-3 font-semibold uppercase tracking-wider">Name</th>
                                                    <th className="px-4 py-3 font-semibold uppercase tracking-wider">ID</th>
                                                    <th className="px-4 py-3 font-semibold uppercase tracking-wider">Type</th>
                                                    <th className="px-4 py-3 font-semibold uppercase tracking-wider">State</th>
                                                    <th className="px-4 py-3 font-semibold uppercase tracking-wider">Created</th>
                                                    <th className="px-4 py-3 font-semibold uppercase tracking-wider w-16"></th>
                                                </tr>
                                            </thead>
                                            <tbody>
                                                {visibleResources.map((resource, i) => {
                                                    const key = selKey(service.name, resource.id);
                                                    const isSelected = selected.has(key);
                                                    return (
                                                        <tr
                                                            key={resource.id + i}
                                                            onClick={() => toggleOne(service.name, resource.id, resource.name)}
                                                            className={`group border-b border-border/5 cursor-pointer transition-colors select-none ${isSelected
                                                                ? 'bg-red-500/[0.04]'
                                                                : 'hover:bg-white/[0.02]'
                                                                }`}
                                                        >
                                                            <td className="px-4 py-3">
                                                                {isSelected
                                                                    ? <CheckSquare size={15} className="text-red-400" />
                                                                    : <Square size={15} className="text-muted-foreground/25" />
                                                                }
                                                            </td>
                                                            <td className="px-4 py-3 font-medium text-foreground/90 max-w-[200px] truncate">
                                                                {resource.name}
                                                            </td>
                                                            <td className="px-4 py-3 font-mono text-muted-foreground/50 max-w-[240px] truncate">
                                                                {resource.id}
                                                            </td>
                                                            <td className="px-4 py-3 text-muted-foreground/60">
                                                                {resource.type}
                                                            </td>
                                                            <td className="px-4 py-3">
                                                                <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold border ${getStateColor(resource.state)}`}>
                                                                    {resource.state || 'N/A'}
                                                                </span>
                                                            </td>
                                                            <td className="px-4 py-3 text-muted-foreground/40 font-mono whitespace-nowrap">
                                                                {resource.launch_time
                                                                    ? new Date(resource.launch_time).toLocaleDateString()
                                                                    : '—'}
                                                            </td>
                                                            <td className="px-4 py-3 text-right">
                                                                <button
                                                                    onClick={(e) => {
                                                                        e.stopPropagation();
                                                                        openDeleteSingle(service.name, resource.id, resource.name);
                                                                    }}
                                                                    className="opacity-0 group-hover:opacity-100 p-1.5 rounded-lg text-muted-foreground/30 hover:text-red-400 hover:bg-red-400/10 transition-all"
                                                                    title="Delete resource"
                                                                >
                                                                    <Trash2 size={13} />
                                                                </button>
                                                            </td>
                                                        </tr>
                                                    );
                                                })}
                                            </tbody>
                                        </table>
                                    </div>
                                </div>
                            )}
                        </div>
                    );
                })}
            </div>
        </>
    );
};
