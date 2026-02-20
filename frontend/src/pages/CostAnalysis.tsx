import React, { useState, useEffect, useCallback } from 'react';
import {
    DollarSign,
    TrendingUp,
    TrendingDown,
    BarChart3,
    Calendar,
    RefreshCw,
    AlertTriangle,
    ArrowDownRight,
    Lightbulb,
    ChevronDown,
    Clock,
} from 'lucide-react';
import { getCostSummary, getCostForecast, getCostRecommendations } from '../api/costAnalysis';
import type {
    CostSummary,
    CostForecast,
    CostRecommendation,
} from '../types';

// ── Helpers ────────────────────────────────────────────────────

function formatCurrency(amount: number): string {
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD',
        minimumFractionDigits: 2,
    }).format(amount);
}

function formatDate(dateStr: string): string {
    return new Date(dateStr + 'T00:00:00').toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric',
    });
}

function formatMonthYear(dateStr: string): string {
    return new Date(dateStr + 'T00:00:00').toLocaleDateString('en-US', {
        month: 'short',
        year: 'numeric',
    });
}

function toISODate(d: Date): string {
    return d.toISOString().split('T')[0];
}

// Date presets
type Preset = {
    label: string;
    getRange: () => { start: string; end: string; granularity: 'DAILY' | 'MONTHLY' };
};

const currentYear = new Date().getFullYear();

const DATE_PRESETS: Preset[] = [
    {
        label: 'This Month',
        getRange: () => {
            const now = new Date();
            const start = new Date(now.getFullYear(), now.getMonth(), 1);
            return { start: toISODate(start), end: toISODate(now), granularity: 'DAILY' };
        },
    },
    {
        label: 'Last Month',
        getRange: () => {
            const now = new Date();
            const start = new Date(now.getFullYear(), now.getMonth() - 1, 1);
            const end = new Date(now.getFullYear(), now.getMonth(), 0);
            return { start: toISODate(start), end: toISODate(end), granularity: 'DAILY' };
        },
    },
    {
        label: 'Last 3 Months',
        getRange: () => {
            const now = new Date();
            const start = new Date(now.getFullYear(), now.getMonth() - 3, 1);
            return { start: toISODate(start), end: toISODate(now), granularity: 'MONTHLY' };
        },
    },
    {
        label: 'Last 6 Months',
        getRange: () => {
            const now = new Date();
            const start = new Date(now.getFullYear(), now.getMonth() - 6, 1);
            return { start: toISODate(start), end: toISODate(now), granularity: 'MONTHLY' };
        },
    },
    {
        label: 'This Year',
        getRange: () => {
            const now = new Date();
            const start = new Date(now.getFullYear(), 0, 1);
            return { start: toISODate(start), end: toISODate(now), granularity: 'MONTHLY' };
        },
    },
    {
        label: 'Last Year',
        getRange: () => {
            const start = new Date(currentYear - 1, 0, 1);
            const end = new Date(currentYear - 1, 11, 31);
            return { start: toISODate(start), end: toISODate(end), granularity: 'MONTHLY' };
        },
    },
    {
        label: `${currentYear - 2}`,
        getRange: () => {
            const start = new Date(currentYear - 2, 0, 1);
            const end = new Date(currentYear - 2, 11, 31);
            return { start: toISODate(start), end: toISODate(end), granularity: 'MONTHLY' };
        },
    },
    {
        label: 'Last 12 Months',
        getRange: () => {
            const now = new Date();
            const start = new Date(now.getFullYear() - 1, now.getMonth(), 1);
            return { start: toISODate(start), end: toISODate(now), granularity: 'MONTHLY' };
        },
    },
];

function getForecastRange() {
    const start = new Date();
    start.setDate(start.getDate() + 1); // forecast must start in the future
    const end = new Date();
    end.setMonth(end.getMonth() + 3);
    return { start_date: toISODate(start), end_date: toISODate(end) };
}

const priorityColors: Record<string, string> = {
    high: 'text-red-400 bg-red-400/10 border-red-400/20',
    medium: 'text-amber-400 bg-amber-400/10 border-amber-400/20',
    low: 'text-emerald-400 bg-emerald-400/10 border-emerald-400/20',
};

const SERVICE_COLORS = [
    'from-blue-500 to-blue-600',
    'from-purple-500 to-purple-600',
    'from-emerald-500 to-emerald-600',
    'from-amber-500 to-amber-600',
    'from-pink-500 to-pink-600',
    'from-cyan-500 to-cyan-600',
    'from-indigo-500 to-indigo-600',
    'from-orange-500 to-orange-600',
    'from-rose-500 to-rose-600',
    'from-teal-500 to-teal-600',
];

const BAR_COLORS = [
    'bg-blue-500',
    'bg-purple-500',
    'bg-emerald-500',
    'bg-amber-500',
    'bg-pink-500',
    'bg-cyan-500',
    'bg-indigo-500',
    'bg-orange-500',
    'bg-rose-500',
    'bg-teal-500',
    'bg-sky-500',
    'bg-violet-500',
];

// ── Component ──────────────────────────────────────────────────

export const CostAnalysis: React.FC = () => {
    const [summary, setSummary] = useState<CostSummary | null>(null);
    const [forecast, setForecast] = useState<CostForecast | null>(null);
    const [recommendations, setRecommendations] = useState<CostRecommendation[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    // Date range state
    const [activePreset, setActivePreset] = useState('Last 3 Months');
    const [startDate, setStartDate] = useState('');
    const [endDate, setEndDate] = useState('');
    const [granularity, setGranularity] = useState<'DAILY' | 'MONTHLY'>('MONTHLY');
    const [groupBy, setGroupBy] = useState<'SERVICE' | 'REGION' | 'USAGE_TYPE'>('SERVICE');
    const [showCustomRange, setShowCustomRange] = useState(false);

    // Initialize with default preset
    useEffect(() => {
        const preset = DATE_PRESETS.find(p => p.label === 'Last 3 Months');
        if (preset) {
            const range = preset.getRange();
            setStartDate(range.start);
            setEndDate(range.end);
            setGranularity(range.granularity);
        }
    }, []);

    const fetchData = useCallback(async () => {
        if (!startDate || !endDate) return;
        setLoading(true);
        setError(null);

        try {
            const forecastRange = getForecastRange();

            const [summaryRes, forecastRes, recsRes] = await Promise.allSettled([
                getCostSummary({
                    start_date: startDate,
                    end_date: endDate,
                    granularity,
                    group_by: groupBy,
                }),
                getCostForecast({
                    ...forecastRange,
                    granularity: 'MONTHLY',
                }),
                getCostRecommendations(),
            ]);

            if (summaryRes.status === 'fulfilled' && summaryRes.value.summary) {
                setSummary(summaryRes.value.summary);
            } else {
                setSummary(null);
            }
            if (forecastRes.status === 'fulfilled' && forecastRes.value.forecast) {
                setForecast(forecastRes.value.forecast);
            } else {
                setForecast(null);
            }
            if (recsRes.status === 'fulfilled') {
                setRecommendations(recsRes.value.recommendations || []);
            }
        } catch (err: any) {
            setError(err?.response?.data?.detail || 'Failed to load cost data');
        } finally {
            setLoading(false);
        }
    }, [startDate, endDate, granularity, groupBy]);

    useEffect(() => {
        fetchData();
    }, [fetchData]);

    const applyPreset = (preset: Preset) => {
        const range = preset.getRange();
        setStartDate(range.start);
        setEndDate(range.end);
        setGranularity(range.granularity);
        setActivePreset(preset.label);
        setShowCustomRange(false);
    };

    const applyCustomRange = () => {
        setActivePreset('Custom');
        setShowCustomRange(false);
    };

    // ── Derived data ───────────────────────────────────────────

    const topServices = summary
        ? Object.entries(summary.group_totals)
            .sort((a, b) => b[1] - a[1])
            .slice(0, 10)
        : [];

    const maxServiceCost = topServices.length > 0 ? topServices[0][1] : 1;
    const totalSavings = recommendations.reduce((sum, r) => sum + r.estimated_savings, 0);

    // Build daily/monthly trend from data_points
    const trendData = summary?.data_points
        ? (() => {
            const buckets: Record<string, number> = {};
            for (const dp of summary.data_points) {
                buckets[dp.date] = (buckets[dp.date] || 0) + dp.amount;
            }
            return Object.entries(buckets)
                .sort((a, b) => a[0].localeCompare(b[0]))
                .map(([date, amount]) => ({ date, amount }));
        })()
        : [];

    const maxTrend = trendData.length > 0 ? Math.max(...trendData.map(d => d.amount)) : 1;
    const avgDaily = trendData.length > 0
        ? trendData.reduce((s, d) => s + d.amount, 0) / trendData.length
        : 0;

    // ── Render ──────────────────────────────────────────────────

    return (
        <div className="max-w-7xl mx-auto space-y-6 animate-fade-in">
            {/* Page Header */}
            <div className="flex flex-col gap-4">
                <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                    <div>
                        <h1 className="text-2xl md:text-3xl font-bold">
                            Cost <span className="gradient-text">Analysis</span>
                        </h1>
                        <p className="text-sm text-muted-foreground mt-1">
                            AWS spending insights, historical costs, and forecasted spend
                        </p>
                    </div>
                    <button
                        onClick={fetchData}
                        disabled={loading}
                        className="flex items-center gap-2 px-4 py-2 rounded-lg bg-white/[0.04] border border-border/50 text-sm text-muted-foreground hover:text-foreground hover:bg-white/[0.08] transition-all duration-200 disabled:opacity-50 self-start md:self-auto"
                    >
                        <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
                        Refresh
                    </button>
                </div>

                {/* Date Presets + Controls */}
                <div className="glass-card p-4">
                    <div className="flex flex-col md:flex-row md:items-center gap-4">
                        {/* Preset Buttons */}
                        <div className="flex flex-wrap items-center gap-2 flex-1">
                            <Calendar size={14} className="text-muted-foreground flex-shrink-0" />
                            {DATE_PRESETS.map((preset) => (
                                <button
                                    key={preset.label}
                                    onClick={() => applyPreset(preset)}
                                    className={`px-3 py-1.5 rounded-md text-xs font-medium transition-all duration-200 whitespace-nowrap ${activePreset === preset.label
                                            ? 'bg-primary/20 text-primary shadow-sm border border-primary/30'
                                            : 'bg-white/[0.04] text-muted-foreground hover:text-foreground hover:bg-white/[0.08] border border-transparent'
                                        }`}
                                >
                                    {preset.label}
                                </button>
                            ))}
                            <button
                                onClick={() => setShowCustomRange(!showCustomRange)}
                                className={`px-3 py-1.5 rounded-md text-xs font-medium transition-all duration-200 whitespace-nowrap ${activePreset === 'Custom'
                                        ? 'bg-primary/20 text-primary shadow-sm border border-primary/30'
                                        : 'bg-white/[0.04] text-muted-foreground hover:text-foreground hover:bg-white/[0.08] border border-transparent'
                                    }`}
                            >
                                Custom Range
                            </button>
                        </div>

                        {/* Group By + Granularity */}
                        <div className="flex items-center gap-2">
                            <div className="relative">
                                <select
                                    value={groupBy}
                                    onChange={(e) => setGroupBy(e.target.value as typeof groupBy)}
                                    className="appearance-none bg-white/[0.06] border border-border/50 rounded-lg px-3 py-1.5 pr-7 text-xs font-medium text-foreground cursor-pointer focus:outline-none focus:border-primary/50"
                                >
                                    <option value="SERVICE">By Service</option>
                                    <option value="REGION">By Region</option>
                                    <option value="USAGE_TYPE">By Usage Type</option>
                                </select>
                                <ChevronDown size={10} className="absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground pointer-events-none" />
                            </div>
                            <div className="relative">
                                <select
                                    value={granularity}
                                    onChange={(e) => setGranularity(e.target.value as 'DAILY' | 'MONTHLY')}
                                    className="appearance-none bg-white/[0.06] border border-border/50 rounded-lg px-3 py-1.5 pr-7 text-xs font-medium text-foreground cursor-pointer focus:outline-none focus:border-primary/50"
                                >
                                    <option value="DAILY">Daily</option>
                                    <option value="MONTHLY">Monthly</option>
                                </select>
                                <ChevronDown size={10} className="absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground pointer-events-none" />
                            </div>
                        </div>
                    </div>

                    {/* Custom Date Range Picker */}
                    {showCustomRange && (
                        <div className="mt-4 pt-4 border-t border-border/30 flex flex-wrap items-end gap-4">
                            <div>
                                <label className="block text-[10px] font-semibold uppercase tracking-wider text-muted-foreground mb-1">Start Date</label>
                                <input
                                    type="date"
                                    value={startDate}
                                    onChange={(e) => setStartDate(e.target.value)}
                                    className="bg-white/[0.06] border border-border/50 rounded-lg px-3 py-1.5 text-xs text-foreground focus:outline-none focus:border-primary/50"
                                />
                            </div>
                            <div>
                                <label className="block text-[10px] font-semibold uppercase tracking-wider text-muted-foreground mb-1">End Date</label>
                                <input
                                    type="date"
                                    value={endDate}
                                    onChange={(e) => setEndDate(e.target.value)}
                                    className="bg-white/[0.06] border border-border/50 rounded-lg px-3 py-1.5 text-xs text-foreground focus:outline-none focus:border-primary/50"
                                />
                            </div>
                            <button
                                onClick={applyCustomRange}
                                className="btn-gradient text-xs px-4 py-1.5"
                            >
                                Apply
                            </button>
                        </div>
                    )}

                    {/* Current Range Indicator */}
                    <div className="mt-3 flex items-center gap-2">
                        <Clock size={12} className="text-muted-foreground/60" />
                        <span className="text-[11px] text-muted-foreground/60">
                            Showing: {startDate} → {endDate} ({granularity.toLowerCase()})
                        </span>
                    </div>
                </div>
            </div>

            {/* Error Banner */}
            {error && (
                <div className="glass-card p-4 border-red-500/30 flex items-center gap-3">
                    <AlertTriangle size={18} className="text-red-400 flex-shrink-0" />
                    <p className="text-sm text-red-300">{error}</p>
                </div>
            )}

            {/* KPI Cards */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                {/* Total Spend */}
                <div className="glass-card p-5 relative overflow-hidden group">
                    <div className="absolute inset-0 bg-gradient-to-br from-blue-500/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
                    <div className="relative">
                        <div className="flex items-center justify-between mb-3">
                            <span className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">Total Cost</span>
                            <div className="w-8 h-8 rounded-lg bg-blue-500/10 flex items-center justify-center">
                                <DollarSign size={16} className="text-blue-400" />
                            </div>
                        </div>
                        <p className="text-2xl font-bold">
                            {loading ? (
                                <span className="inline-block w-28 h-8 rounded bg-white/[0.06] animate-pulse" />
                            ) : (
                                formatCurrency(summary?.total_cost ?? 0)
                            )}
                        </p>
                        <p className="text-[11px] text-muted-foreground mt-1.5">
                            {startDate && endDate ? `${formatDate(startDate)} – ${formatDate(endDate)}` : 'Selected period'}
                        </p>
                    </div>
                </div>

                {/* Forecasted Cost */}
                <div className="glass-card p-5 relative overflow-hidden group">
                    <div className="absolute inset-0 bg-gradient-to-br from-purple-500/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
                    <div className="relative">
                        <div className="flex items-center justify-between mb-3">
                            <span className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">Forecasted (3 mo)</span>
                            <div className="w-8 h-8 rounded-lg bg-purple-500/10 flex items-center justify-center">
                                <TrendingUp size={16} className="text-purple-400" />
                            </div>
                        </div>
                        <p className="text-2xl font-bold">
                            {loading ? (
                                <span className="inline-block w-28 h-8 rounded bg-white/[0.06] animate-pulse" />
                            ) : (
                                formatCurrency(forecast?.total_forecasted ?? 0)
                            )}
                        </p>
                        <p className="text-[11px] text-muted-foreground mt-1.5">
                            {forecast ? `${formatMonthYear(forecast.start_date)} – ${formatMonthYear(forecast.end_date)}` : 'Next 3 months'}
                        </p>
                    </div>
                </div>

                {/* Average Daily/Monthly */}
                <div className="glass-card p-5 relative overflow-hidden group">
                    <div className="absolute inset-0 bg-gradient-to-br from-emerald-500/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
                    <div className="relative">
                        <div className="flex items-center justify-between mb-3">
                            <span className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">
                                Avg {granularity === 'DAILY' ? 'Daily' : 'Monthly'}
                            </span>
                            <div className="w-8 h-8 rounded-lg bg-emerald-500/10 flex items-center justify-center">
                                <BarChart3 size={16} className="text-emerald-400" />
                            </div>
                        </div>
                        <p className="text-2xl font-bold">
                            {loading ? (
                                <span className="inline-block w-24 h-8 rounded bg-white/[0.06] animate-pulse" />
                            ) : (
                                formatCurrency(avgDaily)
                            )}
                        </p>
                        <p className="text-[11px] text-muted-foreground mt-1.5">
                            Across {trendData.length} {granularity === 'DAILY' ? 'days' : 'months'}
                        </p>
                    </div>
                </div>

                {/* Potential Savings */}
                <div className="glass-card p-5 relative overflow-hidden group">
                    <div className="absolute inset-0 bg-gradient-to-br from-amber-500/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
                    <div className="relative">
                        <div className="flex items-center justify-between mb-3">
                            <span className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">Potential Savings</span>
                            <div className="w-8 h-8 rounded-lg bg-amber-500/10 flex items-center justify-center">
                                <TrendingDown size={16} className="text-amber-400" />
                            </div>
                        </div>
                        <p className="text-2xl font-bold">
                            {loading ? (
                                <span className="inline-block w-24 h-8 rounded bg-white/[0.06] animate-pulse" />
                            ) : (
                                formatCurrency(totalSavings)
                            )}
                        </p>
                        <p className="text-[11px] text-muted-foreground mt-1.5">
                            Monthly estimate
                        </p>
                    </div>
                </div>
            </div>

            {/* ── Cost Trend Chart ──────────────────────────────────── */}
            <div className="glass-card overflow-hidden">
                <div className="p-5 border-b border-border/50 flex items-center justify-between">
                    <div className="flex items-center gap-2">
                        <BarChart3 size={16} className="text-blue-400" />
                        <h2 className="text-sm font-semibold">
                            {granularity === 'DAILY' ? 'Daily' : 'Monthly'} Cost Trend
                        </h2>
                    </div>
                    <span className="text-xs text-muted-foreground">
                        {trendData.length} {granularity === 'DAILY' ? 'days' : 'months'}
                    </span>
                </div>

                <div className="p-5">
                    {loading ? (
                        <div className="flex items-end gap-1 h-48">
                            {Array.from({ length: 12 }).map((_, i) => (
                                <div key={i} className="flex-1 bg-white/[0.04] rounded-t animate-pulse" style={{ height: `${30 + Math.random() * 60}%` }} />
                            ))}
                        </div>
                    ) : trendData.length === 0 ? (
                        <div className="text-center py-16">
                            <BarChart3 size={40} className="text-muted-foreground/20 mx-auto mb-3" />
                            <p className="text-sm text-muted-foreground">No cost data for selected period</p>
                            <p className="text-xs text-muted-foreground/60 mt-1">
                                Connect AWS credentials or adjust the date range
                            </p>
                        </div>
                    ) : (
                        <div className="space-y-2">
                            {/* Chart */}
                            <div className="flex items-end gap-[2px] h-48">
                                {trendData.map((dp, i) => {
                                    const height = maxTrend > 0 ? (dp.amount / maxTrend) * 100 : 0;
                                    const barColor = BAR_COLORS[i % BAR_COLORS.length];
                                    return (
                                        <div
                                            key={dp.date}
                                            className="flex-1 group relative"
                                            style={{ height: '100%' }}
                                        >
                                            {/* Tooltip */}
                                            <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 hidden group-hover:block z-20">
                                                <div className="bg-card border border-border/50 rounded-lg px-3 py-2 shadow-lg text-center whitespace-nowrap">
                                                    <p className="text-[10px] text-muted-foreground">
                                                        {granularity === 'DAILY' ? formatDate(dp.date) : formatMonthYear(dp.date)}
                                                    </p>
                                                    <p className="text-sm font-bold">{formatCurrency(dp.amount)}</p>
                                                </div>
                                            </div>
                                            {/* Bar */}
                                            <div className="w-full h-full flex items-end">
                                                <div
                                                    className={`w-full rounded-t-sm ${barColor} opacity-70 group-hover:opacity-100 transition-all duration-200 min-h-[2px]`}
                                                    style={{ height: `${Math.max(height, 1)}%` }}
                                                />
                                            </div>
                                        </div>
                                    );
                                })}
                            </div>
                            {/* X-axis labels — show a subset */}
                            <div className="flex justify-between text-[9px] text-muted-foreground/50 px-1">
                                {trendData.length <= 12
                                    ? trendData.map((dp) => (
                                        <span key={dp.date}>
                                            {granularity === 'DAILY' ? formatDate(dp.date) : formatMonthYear(dp.date)}
                                        </span>
                                    ))
                                    : [0, Math.floor(trendData.length / 4), Math.floor(trendData.length / 2), Math.floor(3 * trendData.length / 4), trendData.length - 1].map((idx) => (
                                        <span key={trendData[idx].date}>
                                            {granularity === 'DAILY' ? formatDate(trendData[idx].date) : formatMonthYear(trendData[idx].date)}
                                        </span>
                                    ))
                                }
                            </div>
                        </div>
                    )}
                </div>
            </div>

            {/* ── Service Breakdown + Recommendations ───────────── */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                {/* Service Breakdown (2/3) */}
                <div className="lg:col-span-2 glass-card overflow-hidden">
                    <div className="p-5 border-b border-border/50 flex items-center justify-between">
                        <div className="flex items-center gap-2">
                            <DollarSign size={16} className="text-primary" />
                            <h2 className="text-sm font-semibold">
                                Cost by {groupBy === 'SERVICE' ? 'Service' : groupBy === 'REGION' ? 'Region' : 'Usage Type'}
                            </h2>
                        </div>
                        <span className="text-xs text-muted-foreground tabular-nums">
                            {topServices.length} {groupBy === 'SERVICE' ? 'services' : groupBy === 'REGION' ? 'regions' : 'types'}
                        </span>
                    </div>

                    <div className="p-5 space-y-3">
                        {loading ? (
                            Array.from({ length: 5 }).map((_, i) => (
                                <div key={i} className="space-y-2">
                                    <div className="flex justify-between items-center">
                                        <div className="w-40 h-4 rounded bg-white/[0.06] animate-pulse" />
                                        <div className="w-16 h-4 rounded bg-white/[0.06] animate-pulse" />
                                    </div>
                                    <div className="w-full h-2 rounded-full bg-white/[0.04]">
                                        <div className="h-full rounded-full bg-white/[0.06] animate-pulse" style={{ width: `${80 - i * 15}%` }} />
                                    </div>
                                </div>
                            ))
                        ) : topServices.length === 0 ? (
                            <div className="text-center py-12">
                                <DollarSign size={40} className="text-muted-foreground/20 mx-auto mb-3" />
                                <p className="text-sm text-muted-foreground">No cost data available</p>
                                <p className="text-xs text-muted-foreground/60 mt-1">
                                    Connect AWS credentials to see real spending data
                                </p>
                            </div>
                        ) : (
                            topServices.map(([service, cost], index) => {
                                const pct = (cost / maxServiceCost) * 100;
                                const totalPct = summary?.total_cost ? (cost / summary.total_cost * 100).toFixed(1) : '0';
                                const color = SERVICE_COLORS[index % SERVICE_COLORS.length];
                                return (
                                    <div key={service} className="group">
                                        <div className="flex justify-between items-center mb-1">
                                            <div className="flex items-center gap-2 min-w-0">
                                                <div className={`w-2 h-2 rounded-full bg-gradient-to-r ${color} flex-shrink-0`} />
                                                <span className="text-sm font-medium truncate">
                                                    {service}
                                                </span>
                                                <span className="text-[10px] text-muted-foreground/50 flex-shrink-0">
                                                    {totalPct}%
                                                </span>
                                            </div>
                                            <span className="text-sm font-semibold tabular-nums flex-shrink-0 ml-4">
                                                {formatCurrency(cost)}
                                            </span>
                                        </div>
                                        <div className="w-full h-1.5 rounded-full bg-white/[0.04] overflow-hidden">
                                            <div
                                                className={`h-full rounded-full bg-gradient-to-r ${color} transition-all duration-700 ease-out`}
                                                style={{ width: `${pct}%` }}
                                            />
                                        </div>
                                    </div>
                                );
                            })
                        )}
                    </div>
                </div>

                {/* Recommendations (1/3) */}
                <div className="glass-card overflow-hidden flex flex-col">
                    <div className="p-5 border-b border-border/50 flex items-center gap-2">
                        <Lightbulb size={16} className="text-amber-400" />
                        <h2 className="text-sm font-semibold">Recommendations</h2>
                    </div>

                    <div className="p-4 space-y-3 overflow-y-auto flex-1 max-h-[420px]">
                        {loading ? (
                            Array.from({ length: 3 }).map((_, i) => (
                                <div key={i} className="p-3 rounded-lg bg-white/[0.03] animate-pulse space-y-2">
                                    <div className="w-20 h-4 rounded bg-white/[0.06]" />
                                    <div className="w-full h-3 rounded bg-white/[0.04]" />
                                    <div className="w-3/4 h-3 rounded bg-white/[0.04]" />
                                </div>
                            ))
                        ) : recommendations.length === 0 ? (
                            <div className="text-center py-8">
                                <Lightbulb size={32} className="text-muted-foreground/20 mx-auto mb-2" />
                                <p className="text-xs text-muted-foreground">No recommendations</p>
                            </div>
                        ) : (
                            recommendations.map((rec, i) => (
                                <div
                                    key={i}
                                    className="p-3 rounded-lg bg-white/[0.03] border border-white/[0.05] hover:bg-white/[0.06] transition-colors duration-200"
                                >
                                    <div className="flex items-center justify-between mb-2">
                                        <span className={`text-[9px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full border ${priorityColors[rec.priority] || priorityColors.medium
                                            }`}>
                                            {rec.priority}
                                        </span>
                                        <span className="text-[10px] font-medium text-muted-foreground">
                                            {rec.service}
                                        </span>
                                    </div>
                                    <p className="text-xs text-foreground/80 leading-relaxed">
                                        {rec.recommendation}
                                    </p>
                                    {rec.estimated_savings > 0 && (
                                        <div className="flex items-center gap-1 mt-2 text-emerald-400">
                                            <ArrowDownRight size={12} />
                                            <span className="text-xs font-medium">
                                                Save {formatCurrency(rec.estimated_savings)}/mo
                                            </span>
                                        </div>
                                    )}
                                </div>
                            ))
                        )}
                    </div>
                </div>
            </div>

            {/* ── Forecast Section ──────────────────────────────── */}
            {forecast && forecast.data_points.length > 0 && (
                <div className="glass-card overflow-hidden">
                    <div className="p-5 border-b border-border/50 flex items-center justify-between">
                        <div className="flex items-center gap-2">
                            <TrendingUp size={16} className="text-purple-400" />
                            <h2 className="text-sm font-semibold">AWS Cost Forecast</h2>
                        </div>
                        <div className="flex items-center gap-3">
                            <span className="text-xs text-muted-foreground">
                                {forecast.start_date} → {forecast.end_date}
                            </span>
                            <span className="text-xs font-semibold text-purple-400">
                                Total: {formatCurrency(forecast.total_forecasted)}
                            </span>
                        </div>
                    </div>

                    <div className="p-5">
                        <div className="flex items-end gap-6 h-40 px-4">
                            {forecast.data_points.map((dp, i) => {
                                const maxAmt = Math.max(...forecast.data_points.map(d => d.amount));
                                const height = maxAmt > 0 ? (dp.amount / maxAmt) * 100 : 0;
                                return (
                                    <div key={i} className="flex-1 flex flex-col items-center gap-2">
                                        <span className="text-xs font-semibold tabular-nums text-purple-300">
                                            {formatCurrency(dp.amount)}
                                        </span>
                                        <div className="w-full relative rounded-t-md overflow-hidden" style={{ height: '100px' }}>
                                            <div
                                                className="absolute bottom-0 w-full rounded-t-md bg-gradient-to-t from-purple-600/80 to-purple-400/60 transition-all duration-700"
                                                style={{ height: `${height}%` }}
                                            />
                                            {/* Dashed forecast indicator */}
                                            <div
                                                className="absolute bottom-0 w-full border-t-2 border-dashed border-purple-400/40"
                                                style={{ bottom: `${height}%` }}
                                            />
                                        </div>
                                        <span className="text-[10px] text-muted-foreground font-medium">
                                            {formatMonthYear(dp.date)}
                                        </span>
                                    </div>
                                );
                            })}
                        </div>
                    </div>
                </div>
            )}

            {/* Footer */}
            <div className="flex items-center justify-center gap-2 text-[10px] text-muted-foreground/40 pb-6">
                <DollarSign size={10} />
                <span>Data from AWS Cost Explorer API • Costs may take up to 24 hours to reflect</span>
            </div>
        </div>
    );
};
