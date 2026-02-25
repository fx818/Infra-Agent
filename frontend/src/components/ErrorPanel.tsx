import React from 'react';
import {
    AlertCircle,
    AlertTriangle,
    WifiOff,
    KeyRound,
    Zap,
    RefreshCw,
    ExternalLink,
    Clock,
} from 'lucide-react';

export interface ErrorInfo {
    title: string;
    message: string;
    suggestions: string[];
    icon: React.ReactNode;
    severity: 'error' | 'warning' | 'info';
    actionLabel?: string;
    actionHref?: string;
}

/**
 * Parse an API error into a human-friendly ErrorInfo object.
 */
export function parseApiError(err: any): ErrorInfo {
    const status = err?.response?.status || 0;
    const detail: string = err?.response?.data?.detail || err?.message || 'Unknown error';

    // Rate limit / Token limit exceeded
    if (status === 413 || status === 429 || detail.toLowerCase().includes('rate') || detail.toLowerCase().includes('token')) {
        return {
            title: 'Rate Limit Exceeded',
            severity: 'warning',
            icon: <Clock size={20} />,
            message: 'The AI provider rejected the request because it was too large or too many requests were made.',
            suggestions: [
                'Try a simpler, more concise description',
                'Wait 30–60 seconds and try again',
                'Mention only the key services you need (e.g. "Lambda, RDS, S3")',
            ],
        };
    }

    // Authentication failure
    if (status === 401 || detail.toLowerCase().includes('authentication') || detail.toLowerCase().includes('api key')) {
        return {
            title: 'API Key Invalid',
            severity: 'error',
            icon: <KeyRound size={20} />,
            message: 'Your LLM API key is missing or incorrect.',
            suggestions: [
                'Go to Settings > AI Configuration and update your API key',
                'Verify your key is correct and has not expired',
                'Make sure you have credits available in your LLM provider account',
            ],
            actionLabel: 'Open Settings',
            actionHref: '/settings',
        };
    }

    // Connection failure
    if (status === 503 || detail.toLowerCase().includes('connect') || detail.toLowerCase().includes('connection')) {
        return {
            title: 'Unable to Reach AI Provider',
            severity: 'error',
            icon: <WifiOff size={20} />,
            message: 'The backend could not connect to the LLM API endpoint.',
            suggestions: [
                'Check that your Base URL in Settings is correct (e.g. https://api.groq.com/openai/v1)',
                'Verify your internet connection is working',
                'The AI provider may be temporarily down — try again in a few minutes',
            ],
            actionLabel: 'Open Settings',
            actionHref: '/settings',
        };
    }

    // Generation / tool calling failure
    if (detail.toLowerCase().includes('generation') || detail.toLowerCase().includes('no tool') || detail.toLowerCase().includes('tool call')) {
        return {
            title: 'Generation Failed',
            severity: 'error',
            icon: <Zap size={20} />,
            message: 'The AI model could not generate a valid architecture from your description.',
            suggestions: [
                'Be more specific about the services you want (e.g. "EC2 with RDS PostgreSQL and S3")',
                'Avoid very complex single-sentence prompts — break it into parts',
                'Try regenerating — results can vary between runs',
            ],
        };
    }

    // Generic server error
    if (status >= 500) {
        return {
            title: 'Server Error',
            severity: 'error',
            icon: <AlertTriangle size={20} />,
            message: detail || 'An unexpected error occurred on the server.',
            suggestions: [
                'Try again in a moment',
                'Check the backend logs for details',
                'If the error persists, simplify your request',
            ],
        };
    }

    // Default fallback
    return {
        title: 'Something Went Wrong',
        severity: 'error',
        icon: <AlertCircle size={20} />,
        message: detail,
        suggestions: ['Try again', 'Check your configuration in Settings'],
    };
}

interface ErrorPanelProps {
    error: string | null;
    onDismiss?: () => void;
    onRetry?: () => void;
    className?: string;
}

const severityStyles = {
    error: {
        bg: 'rgba(239,68,68,0.08)',
        border: 'rgba(239,68,68,0.25)',
        iconColor: '#f87171',
        titleColor: '#fca5a5',
    },
    warning: {
        bg: 'rgba(234,179,8,0.08)',
        border: 'rgba(234,179,8,0.25)',
        iconColor: '#fbbf24',
        titleColor: '#fde68a',
    },
    info: {
        bg: 'rgba(99,102,241,0.08)',
        border: 'rgba(99,102,241,0.25)',
        iconColor: '#818cf8',
        titleColor: '#c7d2fe',
    },
};

export const ErrorPanel: React.FC<ErrorPanelProps> = ({ error, onDismiss, onRetry }) => {
    if (!error) return null;

    const info = parseApiError({ message: error, response: { data: { detail: error } } });
    const styles = severityStyles[info.severity];

    return (
        <div
            style={{
                background: styles.bg,
                border: `1px solid ${styles.border}`,
                borderRadius: '10px',
                padding: '12px 14px',
                display: 'flex',
                flexDirection: 'column',
                gap: '8px',
                animationName: 'fadeIn',
                animationDuration: '0.2s',
            }}
        >
            {/* Header */}
            <div style={{ display: 'flex', alignItems: 'flex-start', gap: '10px' }}>
                <span style={{ color: styles.iconColor, flexShrink: 0, marginTop: '1px' }}>
                    {info.icon}
                </span>
                <div style={{ flex: 1, minWidth: 0 }}>
                    <p style={{ fontSize: '12px', fontWeight: 700, color: styles.titleColor, margin: 0 }}>
                        {info.title}
                    </p>
                    <p style={{ fontSize: '11px', color: 'rgba(255,255,255,0.55)', marginTop: '3px', lineHeight: 1.5 }}>
                        {info.message}
                    </p>
                </div>
                {onDismiss && (
                    <button
                        onClick={onDismiss}
                        style={{
                            background: 'none',
                            border: 'none',
                            color: 'rgba(255,255,255,0.3)',
                            cursor: 'pointer',
                            fontSize: '16px',
                            lineHeight: 1,
                            padding: '0 2px',
                            flexShrink: 0,
                        }}
                        title="Dismiss"
                    >
                        ×
                    </button>
                )}
            </div>

            {/* Suggestions */}
            {info.suggestions.length > 0 && (
                <div style={{ paddingLeft: '30px' }}>
                    <p style={{ fontSize: '10px', textTransform: 'uppercase', letterSpacing: '0.06em', color: 'rgba(255,255,255,0.25)', marginBottom: '4px', fontWeight: 700 }}>
                        Suggestions
                    </p>
                    <ul style={{ margin: 0, padding: '0 0 0 14px', display: 'flex', flexDirection: 'column', gap: '3px' }}>
                        {info.suggestions.map((s, i) => (
                            <li key={i} style={{ fontSize: '11px', color: 'rgba(255,255,255,0.45)', lineHeight: 1.5 }}>
                                {s}
                            </li>
                        ))}
                    </ul>
                </div>
            )}

            {/* Actions */}
            <div style={{ display: 'flex', gap: '8px', paddingLeft: '30px', flexWrap: 'wrap' }}>
                {onRetry && (
                    <button
                        onClick={onRetry}
                        style={{
                            display: 'flex',
                            alignItems: 'center',
                            gap: '4px',
                            padding: '4px 10px',
                            borderRadius: '6px',
                            background: 'rgba(255,255,255,0.06)',
                            border: '1px solid rgba(255,255,255,0.1)',
                            color: 'rgba(255,255,255,0.6)',
                            fontSize: '11px',
                            fontWeight: 600,
                            cursor: 'pointer',
                        }}
                    >
                        <RefreshCw size={11} />
                        Retry
                    </button>
                )}
                {info.actionLabel && info.actionHref && (
                    <a
                        href={info.actionHref}
                        style={{
                            display: 'flex',
                            alignItems: 'center',
                            gap: '4px',
                            padding: '4px 10px',
                            borderRadius: '6px',
                            background: styles.bg,
                            border: `1px solid ${styles.border}`,
                            color: styles.iconColor,
                            fontSize: '11px',
                            fontWeight: 600,
                            textDecoration: 'none',
                        }}
                    >
                        <ExternalLink size={11} />
                        {info.actionLabel}
                    </a>
                )}
            </div>
        </div>
    );
};
