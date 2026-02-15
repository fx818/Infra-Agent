import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { Lock, Mail, Loader2, Zap, ArrowRight } from 'lucide-react';

export const Register: React.FC = () => {
    const { register, login } = useAuth();
    const navigate = useNavigate();
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError('');
        setLoading(true);
        try {
            await register({ email, password });
            await login({ email, password });
            navigate('/');
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to register');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="min-h-screen flex items-center justify-center bg-background p-4 relative overflow-hidden">
            {/* Background effects */}
            <div className="absolute top-1/3 right-1/4 w-[500px] h-[500px] bg-accent/[0.06] rounded-full blur-[120px] pointer-events-none" />
            <div className="absolute bottom-1/3 left-1/4 w-[400px] h-[400px] bg-primary/[0.06] rounded-full blur-[120px] pointer-events-none" />

            <div className="w-full max-w-md animate-scale-in relative z-10">
                {/* Logo */}
                <div className="text-center mb-8">
                    <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-purple-500 to-blue-600 flex items-center justify-center mx-auto mb-4 shadow-lg shadow-purple-500/25">
                        <Zap size={28} className="text-white" />
                    </div>
                    <h1 className="text-3xl font-bold gradient-text-accent mb-1">Create Account</h1>
                    <p className="text-muted-foreground text-sm">Start building infrastructure with AI</p>
                </div>

                <div className="glass-card p-8 space-y-6">
                    {error && (
                        <div className="p-3 bg-destructive/10 text-destructive text-sm rounded-lg border border-destructive/20 animate-fade-in">
                            {error}
                        </div>
                    )}

                    <form onSubmit={handleSubmit} className="space-y-5">
                        <div className="space-y-2">
                            <label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground/80">Email</label>
                            <div className="relative">
                                <Mail className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground/50" />
                                <input
                                    type="email"
                                    required
                                    value={email}
                                    onChange={(e) => setEmail(e.target.value)}
                                    className="input-glow pl-10"
                                    placeholder="you@example.com"
                                />
                            </div>
                        </div>

                        <div className="space-y-2">
                            <label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground/80">Password</label>
                            <div className="relative">
                                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground/50" />
                                <input
                                    type="password"
                                    required
                                    value={password}
                                    onChange={(e) => setPassword(e.target.value)}
                                    className="input-glow pl-10"
                                    placeholder="••••••••"
                                    minLength={8}
                                />
                            </div>
                            <p className="text-[11px] text-muted-foreground/50 ml-1">Must be at least 8 characters</p>
                        </div>

                        <button
                            type="submit"
                            disabled={loading}
                            className="btn-gradient w-full flex items-center justify-center gap-2 py-2.5 text-sm"
                        >
                            {loading ? (
                                <Loader2 className="animate-spin h-4 w-4" />
                            ) : (
                                <>
                                    <span>Create Account</span>
                                    <ArrowRight size={16} />
                                </>
                            )}
                        </button>
                    </form>

                    <div className="relative">
                        <div className="absolute inset-0 flex items-center">
                            <div className="w-full border-t border-border/50" />
                        </div>
                        <div className="relative flex justify-center text-xs">
                            <span className="px-3 bg-card text-muted-foreground/60">or</span>
                        </div>
                    </div>

                    <p className="text-center text-sm text-muted-foreground">
                        Already have an account?{' '}
                        <Link to="/login" className="font-semibold text-primary hover:text-primary/80 transition-colors">
                            Sign in
                        </Link>
                    </p>
                </div>
            </div>
        </div>
    );
};
