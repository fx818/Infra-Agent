import React, { createContext, useContext, useState, useEffect } from 'react';
import api from '../api/client';
import type { User, TokenResponse, UserLogin, UserCreate } from '../types';

interface AuthContextType {
    user: User | null;
    isAuthenticated: boolean;
    isLoading: boolean;
    login: (data: UserLogin) => Promise<void>;
    register: (data: UserCreate) => Promise<void>;
    logout: () => void;
    checkAuth: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
    const [user, setUser] = useState<User | null>(null);
    const [isLoading, setIsLoading] = useState(true);

    const checkAuth = async () => {
        const token = localStorage.getItem('token');
        if (!token) {
            setUser(null);
            setIsLoading(false);
            return;
        }

        try {
            const response = await api.get<User>('/auth/me');
            setUser(response.data);
        } catch (error) {
            console.error('Auth check failed:', error);
            localStorage.removeItem('token');
            setUser(null);
        } finally {
            setIsLoading(false);
        }
    };

    useEffect(() => {
        checkAuth();
    }, []);

    const login = async (data: UserLogin) => {
        const response = await api.post<TokenResponse>('/auth/login', data);
        localStorage.setItem('token', response.data.access_token);
        await checkAuth();
    };

    const register = async (data: UserCreate) => {
        await api.post<User>('/auth/register', data);
        // After register, you might want to auto-login or redirect to login
        // For now, let's assume we redirect to login (implemented in UI)
    };

    const logout = () => {
        localStorage.removeItem('token');
        setUser(null);
        // Redirect to login is handled by protected routes
    };

    return (
        <AuthContext.Provider value={{ user, isAuthenticated: !!user, isLoading, login, register, logout, checkAuth }}>
            {children}
        </AuthContext.Provider>
    );
};

export const useAuth = () => {
    const context = useContext(AuthContext);
    if (context === undefined) {
        throw new Error('useAuth must be used within an AuthProvider');
    }
    return context;
};
