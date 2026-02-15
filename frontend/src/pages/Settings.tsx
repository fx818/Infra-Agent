import React, { useEffect, useState } from 'react';
import api from '../api/client';
import {
    Settings as SettingsIcon,
    Key,
    Shield,
    CheckCircle2,
    XCircle,
    Loader2,
    Save,
    Trash2,
    Eye,
    EyeOff,
    Globe,
    Bot,
} from 'lucide-react';

interface AWSStatus {
    configured: boolean;
    message: string;
}

interface Preferences {
    default_region: string;
    default_vpc: boolean;
    naming_convention: string;
    tags: Record<string, string>;
}

interface LLMConfig {
    api_key: string;
    base_url: string;
    model: string;
}

const AWS_REGIONS = [
    'us-east-1', 'us-east-2', 'us-west-1', 'us-west-2',
    'eu-west-1', 'eu-west-2', 'eu-central-1',
    'ap-southeast-1', 'ap-southeast-2', 'ap-northeast-1',
];

export const Settings: React.FC = () => {
    const [awsStatus, setAwsStatus] = useState<AWSStatus | null>(null);
    const [prefs, setPrefs] = useState<Preferences>({
        default_region: 'us-east-1',
        default_vpc: true,
        naming_convention: 'project-resource',
        tags: {},
    });
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [message, setMessage] = useState('');
    const [messageType, setMessageType] = useState<'success' | 'error'>('success');

    // AWS Credentials form
    const [accessKey, setAccessKey] = useState('');
    const [secretKey, setSecretKey] = useState('');
    const [showSecret, setShowSecret] = useState(false);
    const [savingCreds, setSavingCreds] = useState(false);

    // LLM Config form
    const [llmConfig, setLlmConfig] = useState<LLMConfig>({
        api_key: '',
        base_url: 'https://api.openai.com/v1',
        model: 'gpt-4o',
    });
    const [savingLlm, setSavingLlm] = useState(false);
    const [showLlmKey, setShowLlmKey] = useState(false);
    const [deletingPrefs, setDeletingPrefs] = useState(false);
    const [deletingLlm, setDeletingLlm] = useState(false);

    useEffect(() => {
        fetchData();
    }, []);

    const fetchData = async () => {
        setLoading(true);
        try {
            const [credRes, prefRes, llmRes] = await Promise.all([
                api.get<AWSStatus>('/config/aws-credentials/status'),
                api.get<Preferences>('/config/'),
                api.get<LLMConfig>('/config/llm'),
            ]);
            setAwsStatus(credRes.data);
            setPrefs(prefRes.data);
            setLlmConfig(llmRes.data);
        } catch (err: any) {
            console.error('Failed to load settings:', err);
        } finally {
            setLoading(false);
        }
    };

    const showMessage = (msg: string, type: 'success' | 'error') => {
        setMessage(msg);
        setMessageType(type);
        setTimeout(() => setMessage(''), 4000);
    };

    const handleSavePrefs = async () => {
        setSaving(true);
        try {
            await api.put('/config/', prefs);
            showMessage('Preferences saved successfully', 'success');
        } catch (err: any) {
            showMessage(err.response?.data?.detail || 'Failed to save preferences', 'error');
        } finally {
            setSaving(false);
        }
    };

    const handleDeletePrefs = async () => {
        if (!window.confirm('Are you sure you want to reset preferences to default?')) return;
        setDeletingPrefs(true);
        try {
            const res = await api.delete<Preferences>('/config/');
            setPrefs(res.data);
            showMessage('Preferences reset to default', 'success');
        } catch (err: any) {
            showMessage(err.response?.data?.detail || 'Failed to reset preferences', 'error');
        } finally {
            setDeletingPrefs(false);
        }
    };

    const handleSaveCreds = async () => {
        if (!accessKey || !secretKey) {
            showMessage('Both Access Key and Secret Key are required', 'error');
            return;
        }
        setSavingCreds(true);
        try {
            await api.put('/config/aws-credentials', {
                aws_access_key_id: accessKey,
                aws_secret_access_key: secretKey,
            });
            setAccessKey('');
            setSecretKey('');
            setAwsStatus({ configured: true, message: 'AWS credentials are configured' });
            showMessage('AWS credentials saved securely', 'success');
        } catch (err: any) {
            showMessage(err.response?.data?.detail || 'Failed to save credentials', 'error');
        } finally {
            setSavingCreds(false);
        }
    };

    const handleDeleteCreds = async () => {
        if (!window.confirm('Are you sure you want to remove your AWS credentials?')) return;
        try {
            await api.delete('/config/aws-credentials');
            setAwsStatus({ configured: false, message: 'No AWS credentials set' });
            showMessage('AWS credentials removed', 'success');
        } catch (err: any) {
            showMessage(err.response?.data?.detail || 'Failed to remove credentials', 'error');
        }
    };

    const handleSaveLlm = async () => {
        setSavingLlm(true);
        try {
            const payload = { ...llmConfig };
            // Don't send masked key back if it hasn't changed
            if (payload.api_key && payload.api_key.startsWith('sk-...')) {
                delete (payload as any).api_key;
            }

            await api.put('/config/llm', payload);
            await fetchData(); // Refresh to get updated status
            showMessage('LLM configuration saved', 'success');
        } catch (err: any) {
            showMessage(err.response?.data?.detail || 'Failed to save LLM config', 'error');
        } finally {
            setSavingLlm(false);
        }
    };

    const handleDeleteLlm = async () => {
        if (!window.confirm('Are you sure you want to remove LLM configuration?')) return;
        setDeletingLlm(true);
        try {
            await api.delete('/config/llm');
            setLlmConfig({ api_key: '', base_url: 'https://api.openai.com/v1', model: 'gpt-4o' });
            showMessage('LLM configuration removed', 'success');
        } catch (err: any) {
            showMessage(err.response?.data?.detail || 'Failed to remove LLM config', 'error');
        } finally {
            setDeletingLlm(false);
        }
    };

    if (loading) {
        return (
            <div className="flex items-center justify-center h-full">
                <div className="flex flex-col items-center gap-3">
                    <div className="w-10 h-10 rounded-full border-2 border-primary/30 border-t-primary animate-spin" />
                    <p className="text-sm text-muted-foreground">Loading settings…</p>
                </div>
            </div>
        );
    }

    return (
        <div className="max-w-3xl mx-auto space-y-6 animate-fade-in">
            <div>
                <h1 className="text-2xl font-bold tracking-tight">Settings</h1>
                <p className="text-sm text-muted-foreground/60 mt-1">Manage your account, AWS credentials, and preferences</p>
            </div>

            {/* Toast Message */}
            {message && (
                <div className={`p-3 rounded-lg text-xs font-medium flex items-center gap-2 animate-fade-in ${messageType === 'success'
                    ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                    : 'bg-red-500/10 text-red-400 border border-red-500/20'
                    }`}>
                    {messageType === 'success' ? <CheckCircle2 size={14} /> : <XCircle size={14} />}
                    {message}
                </div>
            )}

            {/* AWS Credentials */}
            <div className="glass-card overflow-hidden">
                <div className="p-5 border-b border-border/30">
                    <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-xl bg-amber-500/10 flex items-center justify-center">
                            <Key size={18} className="text-amber-400" />
                        </div>
                        <div>
                            <h2 className="text-sm font-semibold">AWS Credentials</h2>
                            <p className="text-[11px] text-muted-foreground/50">Required for deploying infrastructure</p>
                        </div>
                        <div className="ml-auto">
                            {awsStatus?.configured ? (
                                <div className="flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[10px] font-semibold badge-success">
                                    <CheckCircle2 size={10} />
                                    <span>Configured</span>
                                </div>
                            ) : (
                                <div className="flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[10px] font-semibold badge-warning">
                                    <Shield size={10} />
                                    <span>Not Set</span>
                                </div>
                            )}
                        </div>
                    </div>
                </div>
                <div className="p-5 space-y-4">
                    <div>
                        <label className="block text-[11px] font-medium text-muted-foreground/60 uppercase tracking-wider mb-1.5">
                            AWS Access Key ID
                        </label>
                        <input
                            type="text"
                            value={accessKey}
                            onChange={(e) => setAccessKey(e.target.value)}
                            placeholder={awsStatus?.configured ? '••••••••••••' : 'AKIAIOSFODNN7EXAMPLE'}
                            className="w-full px-3 py-2 bg-white/[0.03] border border-border/30 rounded-lg text-xs text-foreground placeholder:text-muted-foreground/25 focus:outline-none focus:border-primary/40 focus:ring-1 focus:ring-primary/20 transition-all font-mono"
                        />
                    </div>
                    <div>
                        <label className="block text-[11px] font-medium text-muted-foreground/60 uppercase tracking-wider mb-1.5">
                            AWS Secret Access Key
                        </label>
                        <div className="relative">
                            <input
                                type={showSecret ? 'text' : 'password'}
                                value={secretKey}
                                onChange={(e) => setSecretKey(e.target.value)}
                                placeholder={awsStatus?.configured ? '••••••••••••••••••••' : 'wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY'}
                                className="w-full px-3 py-2 pr-10 bg-white/[0.03] border border-border/30 rounded-lg text-xs text-foreground placeholder:text-muted-foreground/25 focus:outline-none focus:border-primary/40 focus:ring-1 focus:ring-primary/20 transition-all font-mono"
                            />
                            <button
                                onClick={() => setShowSecret(!showSecret)}
                                className="absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground/30 hover:text-muted-foreground/60 transition-colors"
                            >
                                {showSecret ? <EyeOff size={14} /> : <Eye size={14} />}
                            </button>
                        </div>
                    </div>
                    <div className="flex items-center gap-2 pt-1">
                        <button
                            onClick={handleSaveCreds}
                            disabled={savingCreds}
                            className="btn-gradient flex items-center gap-2 text-xs py-2"
                        >
                            {savingCreds ? (
                                <><Loader2 size={13} className="animate-spin" /><span>Saving…</span></>
                            ) : (
                                <><Save size={13} /><span>Save Credentials</span></>
                            )}
                        </button>
                        {awsStatus?.configured && (
                            <button
                                onClick={handleDeleteCreds}
                                className="flex items-center gap-2 text-xs py-2 px-3 rounded-lg bg-destructive/10 text-destructive border border-destructive/20 hover:bg-destructive/20 transition-all font-medium"
                            >
                                <Trash2 size={13} />
                                <span>Remove</span>
                            </button>
                        )}
                    </div>
                </div>
            </div>


  {/* LLM Configuration */}
            <div className="glass-card overflow-hidden">
                <div className="p-5 border-b border-border/30">
                    <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-xl bg-blue-500/10 flex items-center justify-center">
                            <Bot size={18} className="text-blue-400" />
                        </div>
                        <div>
                            <h2 className="text-sm font-semibold">AI Configuration</h2>
                            <p className="text-[11px] text-muted-foreground/50">Configure the LLM provider for generation</p>
                        </div>
                        <div className="ml-auto">
                            {llmConfig.api_key ? (
                                <div className="flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[10px] font-semibold badge-success">
                                    <CheckCircle2 size={10} />
                                    <span>Configured</span>
                                </div>
                            ) : (
                                <div className="flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[10px] font-semibold badge-warning">
                                    <Shield size={10} />
                                    <span>Not Set</span>
                                </div>
                            )}
                        </div>
                    </div>
                </div>
                <div className="p-5 space-y-4">
                    <div>
                        <label className="block text-[11px] font-medium text-muted-foreground/60 uppercase tracking-wider mb-1.5">
                            Base URL
                        </label>
                        <input
                            type="text"
                            value={llmConfig.base_url}
                            onChange={(e) => setLlmConfig({ ...llmConfig, base_url: e.target.value })}
                            placeholder="https://api.openai.com/v1"
                            className="w-full px-3 py-2 bg-white/[0.03] border border-border/30 rounded-lg text-xs text-foreground placeholder:text-muted-foreground/25 focus:outline-none focus:border-primary/40 focus:ring-1 focus:ring-primary/20 transition-all font-mono"
                        />
                    </div>
                    <div>
                        <label className="block text-[11px] font-medium text-muted-foreground/60 uppercase tracking-wider mb-1.5">
                            API Key
                        </label>
                        <div className="relative">
                            <input
                                type={showLlmKey ? 'text' : 'password'}
                                value={llmConfig.api_key || ''}
                                onChange={(e) => setLlmConfig({ ...llmConfig, api_key: e.target.value })}
                                placeholder="sk-..."
                                className="w-full px-3 py-2 pr-10 bg-white/[0.03] border border-border/30 rounded-lg text-xs text-foreground placeholder:text-muted-foreground/25 focus:outline-none focus:border-primary/40 focus:ring-1 focus:ring-primary/20 transition-all font-mono"
                            />
                            <button
                                onClick={() => setShowLlmKey(!showLlmKey)}
                                className="absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground/30 hover:text-muted-foreground/60 transition-colors"
                            >
                                {showLlmKey ? <EyeOff size={14} /> : <Eye size={14} />}
                            </button>
                        </div>
                    </div>
                    <div>
                        <label className="block text-[11px] font-medium text-muted-foreground/60 uppercase tracking-wider mb-1.5">
                            Model Name
                        </label>
                        <input
                            type="text"
                            value={llmConfig.model}
                            onChange={(e) => setLlmConfig({ ...llmConfig, model: e.target.value })}
                            placeholder="gpt-4o"
                            className="w-full px-3 py-2 bg-white/[0.03] border border-border/30 rounded-lg text-xs text-foreground placeholder:text-muted-foreground/25 focus:outline-none focus:border-primary/40 focus:ring-1 focus:ring-primary/20 transition-all font-mono"
                        />
                    </div>
                    <div className="flex items-center gap-2 pt-1">
                        <button
                            onClick={handleSaveLlm}
                            disabled={savingLlm}
                            className="btn-gradient flex items-center gap-2 text-xs py-2"
                        >
                            {savingLlm ? (
                                <><Loader2 size={13} className="animate-spin" /><span>Saving…</span></>
                            ) : (
                                <><Save size={13} /><span>Save AI Settings</span></>
                            )}
                        </button>
                        {(llmConfig.api_key || llmConfig.base_url !== 'https://api.openai.com/v1' || llmConfig.model !== 'gpt-4o') && (
                            <button
                                onClick={handleDeleteLlm}
                                disabled={deletingLlm}
                                className="flex items-center gap-2 text-xs py-2 px-3 rounded-lg bg-destructive/10 text-destructive border border-destructive/20 hover:bg-destructive/20 transition-all font-medium"
                            >
                                {deletingLlm ? <Loader2 size={13} className="animate-spin" /> : <Trash2 size={13} />}
                                <span>Remove</span>
                            </button>
                        )}
                    </div>
                </div>
            </div>


            {/* Preferences */}
            <div className="glass-card overflow-hidden">
                <div className="p-5 border-b border-border/30">
                    <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-xl bg-violet-500/10 flex items-center justify-center">
                            <SettingsIcon size={18} className="text-violet-400" />
                        </div>
                        <div>
                            <h2 className="text-sm font-semibold">Preferences</h2>
                            <p className="text-[11px] text-muted-foreground/50">Default settings for new projects</p>
                        </div>
                        <div className="ml-auto">
                            <div className="flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[10px] font-semibold badge-success">
                                <CheckCircle2 size={10} />
                                <span>Configured</span>
                            </div>
                        </div>
                    </div>
                </div>
                <div className="p-5 space-y-4">
                    <div>
                        <label className="block text-[11px] font-medium text-muted-foreground/60 uppercase tracking-wider mb-1.5">
                            Default AWS Region
                        </label>
                        <div className="relative">
                            <Globe size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground/30" />
                            <select
                                value={prefs.default_region}
                                onChange={(e) => setPrefs({ ...prefs, default_region: e.target.value })}
                                className="w-full px-3 py-2 pl-9 bg-white/[0.03] border border-border/30 rounded-lg text-xs text-foreground focus:outline-none focus:border-primary/40 focus:ring-1 focus:ring-primary/20 transition-all appearance-none cursor-pointer"
                            >
                                {AWS_REGIONS.map(r => (
                                    <option key={r} value={r}>{r}</option>
                                ))}
                            </select>
                        </div>
                    </div>
                    <div>
                        <label className="block text-[11px] font-medium text-muted-foreground/60 uppercase tracking-wider mb-2">
                            Naming Convention
                        </label>
                        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                            {[
                                { val: 'project-resource', label: 'Project - Resource', ex: 'myproject-webserver' },
                                { val: 'environment-project-resource', label: 'Env - Project - Resource', ex: 'dev-myproject-webserver' },
                                { val: 'kebab-case', label: 'Kebab Case', ex: 'webserver' }
                            ].map((opt) => (
                                <div
                                    key={opt.val}
                                    onClick={() => setPrefs({ ...prefs, naming_convention: opt.val })}
                                    className={`cursor-pointer rounded-lg border-2 p-3 transition-all ${prefs.naming_convention === opt.val
                                        ? 'border-primary bg-primary/5'
                                        : 'border-border/40 hover:border-border/80 bg-white/[0.02]'
                                        }`}
                                >
                                    <div className="flex items-center justify-between mb-1">
                                        <span className="text-xs font-medium">{opt.label}</span>
                                        {prefs.naming_convention === opt.val && <CheckCircle2 size={12} className="text-primary" />}
                                    </div>
                                    <div className="text-[10px] text-muted-foreground font-mono opacity-80">
                                        {opt.ex}
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>
                    <div className="flex items-center gap-3">
                        <label className="relative inline-flex items-center cursor-pointer">
                            <input
                                type="checkbox"
                                checked={prefs.default_vpc}
                                onChange={(e) => setPrefs({ ...prefs, default_vpc: e.target.checked })}
                                className="sr-only peer"
                            />
                            <div className="w-9 h-5 bg-white/[0.06] peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-muted-foreground/40 peer-checked:after:bg-primary after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-primary/20 border border-border/30" />
                        </label>
                        <div>
                            <p className="text-xs font-medium">Use Default VPC</p>
                            <p className="text-[10px] text-muted-foreground/40">Use the account's default VPC for new resources</p>
                        </div>
                    </div>
                    <div className="flex items-center gap-2 pt-2">
                        <button
                            onClick={handleSavePrefs}
                            disabled={saving}
                            className="btn-gradient flex items-center gap-2 text-xs py-2"
                        >
                            {saving ? (
                                <><Loader2 size={13} className="animate-spin" /><span>Saving…</span></>
                            ) : (
                                <><Save size={13} /><span>Save Preferences</span></>
                            )}
                        </button>
                        <button
                            onClick={handleDeletePrefs}
                            disabled={deletingPrefs}
                            className="flex items-center gap-2 text-xs py-2 px-3 rounded-lg bg-destructive/10 text-destructive border border-destructive/20 hover:bg-destructive/20 transition-all font-medium"
                        >
                            {deletingPrefs ? <Loader2 size={13} className="animate-spin" /> : <Trash2 size={13} />}
                            <span>Reset Defaults</span>
                        </button>
                    </div>
                </div>
            </div>

          
        </div>
    );
};
