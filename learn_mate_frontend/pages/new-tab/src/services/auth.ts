// 认证管理服务

import { apiService } from './api';

export interface User {
  username: string;
  email?: string;
}

class AuthService {
  private static readonly TOKEN_KEY = 'learn_mate_token';
  private static readonly USER_KEY = 'learn_mate_user';

  // 获取存储的token
  getToken(): string | null {
    return localStorage.getItem(AuthService.TOKEN_KEY);
  }

  // 获取存储的用户信息
  getUser(): User | null {
    const userStr = localStorage.getItem(AuthService.USER_KEY);
    return userStr ? JSON.parse(userStr) : null;
  }

  // 保存token和用户信息
  setAuth(token: string, user: User): void {
    localStorage.setItem(AuthService.TOKEN_KEY, token);
    localStorage.setItem(AuthService.USER_KEY, JSON.stringify(user));
    apiService.setToken(token);
  }

  // 清除认证信息
  clearAuth(): void {
    localStorage.removeItem(AuthService.TOKEN_KEY);
    localStorage.removeItem(AuthService.USER_KEY);
    apiService.setToken('');
  }

  // 检查是否已认证
  isAuthenticated(): boolean {
    return !!this.getToken();
  }

  // 登录
  async login(username: string, password: string): Promise<User> {
    try {
      const response = await apiService.login(username, password);
      const user: User = { username };
      this.setAuth(response.access_token, user);
      return user;
    } catch (error) {
      throw error;
    }
  }

  // 注册
  async register(username: string, email: string, password: string): Promise<User> {
    try {
      const response = await apiService.register(username, email, password);
      const user: User = { username, email };
      this.setAuth(response.access_token, user);
      return user;
    } catch (error) {
      throw error;
    }
  }

  // 登出
  logout(): void {
    this.clearAuth();
  }

  // 初始化认证状态
  init(): void {
    const token = this.getToken();
    if (token) {
      apiService.setToken(token);
    }
  }

  // 创建临时会话用户（无需真实注册）
  async createTemporarySession(): Promise<User> {
    // 生成临时用户ID
    const tempUserId = `temp_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    const tempUser: User = { username: tempUserId };
    
    try {
      // 尝试注册临时用户
      const response = await apiService.register(tempUserId, `${tempUserId}@temp.local`, 'temp_password');
      this.setAuth(response.access_token, tempUser);
      return tempUser;
    } catch (error) {
      // 如果注册失败，可能是因为用户已存在，尝试登录
      try {
        const response = await apiService.login(tempUserId, 'temp_password');
        this.setAuth(response.access_token, tempUser);
        return tempUser;
      } catch (loginError) {
        throw new Error('Failed to create temporary session');
      }
    }
  }
}

export const authService = new AuthService();