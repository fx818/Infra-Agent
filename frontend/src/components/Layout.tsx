import React from 'react';
import { Outlet, Link, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import {
    LayoutDashboard,
    Plus,
    Settings,
    LogOut,
    Server,
    Activity,
    Menu,
    X,
    Zap
} from 'lucide-react';

export const Layout: React.FC = () => {
    const { user, logout } = useAuth();
    const location = useLocation();
    const navigate = useNavigate();
    const [isMobileMenuOpen, setIsMobileMenuOpen] = React.useState(false);

    const handleLogout = () => {
        logout();
        navigate('/login');
    };

    const navItems = [
        { label: 'Dashboard', path: '/', icon: LayoutDashboard },
        { label: 'New Project', path: '/projects/new', icon: Plus },
        { label: 'Deployments', path: '/deployments', icon: Server },
        { label: 'Monitoring', path: '/monitoring', icon: Activity },
        { label: 'Settings', path: '/settings', icon: Settings },
    ];

    return (
        <div className="flex h-screen bg-background text-foreground overflow-hidden">
            {/* Sidebar */}
            <aside className={`
                fixed inset-y-0 left-0 z-50 w-[260px] transform transition-transform duration-300 ease-in-out
                ${isMobileMenuOpen ? 'translate-x-0' : '-translate-x-full'}
                md:relative md:translate-x-0
                bg-card/80 backdrop-blur-xl border-r border-border/50
            `}>
                <div className="flex flex-col h-full">
                    {/* Logo */}
                    <div className="h-16 flex items-center gap-3 px-6 border-b border-border/50">
                        <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center shadow-lg shadow-blue-500/20">
                            <Zap size={18} className="text-white" />
                        </div>
                        <span className="text-lg font-bold gradient-text">AUGS Infra Agent</span>
                        <button
                            className="ml-auto md:hidden text-muted-foreground hover:text-foreground transition-colors"
                            onClick={() => setIsMobileMenuOpen(false)}
                        >
                            <X size={20} />
                        </button>
                    </div>

                    {/* Navigation */}
                    <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
                        <p className="px-3 py-2 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground/60">
                            Navigation
                        </p>
                        {navItems.map((item) => {
                            const Icon = item.icon;
                            const isActive = location.pathname === item.path;
                            return (
                                <Link
                                    key={item.path}
                                    to={item.path}
                                    onClick={() => setIsMobileMenuOpen(false)}
                                    className={`
                                        flex items-center gap-3 px-3 py-2.5 rounded-lg text-[13px] font-medium
                                        transition-all duration-200 group relative
                                        ${isActive
                                            ? 'bg-primary/10 text-primary'
                                            : 'text-muted-foreground hover:text-foreground hover:bg-white/[0.04]'
                                        }
                                    `}
                                >
                                    {isActive && (
                                        <div className="absolute left-0 top-1/2 -translate-y-1/2 w-[3px] h-5 rounded-full bg-primary" />
                                    )}
                                    <Icon size={18} className={isActive ? 'text-primary' : 'text-muted-foreground group-hover:text-foreground'} />
                                    <span>{item.label}</span>
                                </Link>
                            );
                        })}
                    </nav>

                    {/* User section */}
                    <div className="p-3 border-t border-border/50">
                        <div className="flex items-center gap-3 px-3 py-2.5 rounded-lg bg-white/[0.03]">
                            <div className="w-8 h-8 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-white text-xs font-bold shadow-md">
                                {user?.email?.[0].toUpperCase()}
                            </div>
                            <div className="flex-1 min-w-0">
                                <p className="text-sm font-medium truncate">{user?.email}</p>
                                <p className="text-[11px] text-muted-foreground/60">Free Plan</p>
                            </div>
                        </div>
                        <button
                            onClick={handleLogout}
                            className="w-full flex items-center gap-3 px-3 py-2 mt-1 text-xs text-muted-foreground hover:text-destructive hover:bg-destructive/5 rounded-lg transition-all duration-200"
                        >
                            <LogOut size={14} />
                            <span>Sign Out</span>
                        </button>
                    </div>
                </div>
            </aside>

            {/* Main Content */}
            <main className="flex-1 flex flex-col h-full overflow-hidden relative">
                {/* Ambient glow */}
                <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[600px] h-[300px] bg-primary/[0.03] rounded-full blur-[100px] pointer-events-none" />

                {/* Mobile Header */}
                <header className="h-14 md:hidden flex items-center justify-between px-4 border-b border-border/50 bg-card/80 backdrop-blur-xl">
                    <div className="flex items-center gap-2">
                        <div className="w-6 h-6 rounded-md bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center">
                            <Zap size={12} className="text-white" />
                        </div>
                        <span className="font-bold text-sm">NL2I</span>
                    </div>
                    <button onClick={() => setIsMobileMenuOpen(true)} className="text-muted-foreground hover:text-foreground">
                        <Menu size={20} />
                    </button>
                </header>

                <div className="flex-1 overflow-y-auto p-4 md:p-6 lg:p-8 relative z-10">
                    <Outlet />
                </div>
            </main>

            {/* Overlay for mobile */}
            {isMobileMenuOpen && (
                <div
                    className="fixed inset-0 bg-black/60 backdrop-blur-sm z-40 md:hidden transition-opacity"
                    onClick={() => setIsMobileMenuOpen(false)}
                />
            )}
        </div>
    );
};
