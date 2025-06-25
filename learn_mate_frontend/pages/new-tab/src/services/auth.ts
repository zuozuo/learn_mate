// 认证管理服务

import { apiService } from './api';

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
  async login(email: string, password: string, rememberMe: boolean = false): Promise<User> {
    const response = await apiService.accountLogin(email, password, rememberMe);
    const user: User = {
      id: response.user.id,
      username: response.user.username,
      email: response.user.email,
    };
    
    // 先设置用户 token
    apiService.setToken(response.access_token);
    
    // 创建 session token 用于对话
    try {
      const sessionResponse = await apiService.createSession();
      // 使用 session token 而不是用户 token
      this.setAuth(sessionResponse.token, user);
    } catch (error) {
      console.error('Failed to create session after login:', error);
      // 如果创建 session 失败，仍然保存用户 token
      this.setAuth(response.access_token, user);
    }

    // 如果有 refresh token，保存它
    if (response.refresh_token) {
      localStorage.setItem('learn_mate_refresh_token', response.refresh_token);
    }

    return user;
  }

  // 注册
  async register(email: string, username: string, password: string): Promise<User> {
    const response = await apiService.accountRegister(email, username, password);
    const user: User = {
      id: response.id,
      username: response.username,
      email: response.email,
    };
    // 注册成功后不自动登录，返回用户信息
    return user;
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
    // 检查是否已有有效的用户 token
    const existingToken = this.getToken();
    const existingUser = this.getUser();

    // 如果已有用户信息，尝试创建新的 session
    if (existingToken && existingUser) {
      try {
        // 尝试使用现有 token 创建新 session
        apiService.setToken(existingToken);
        const sessionResponse = await apiService.createSession();
        this.setAuth(sessionResponse.token, existingUser);
        return existingUser;
      } catch (error) {
        console.warn('Failed to create session with existing token:', error);
        // 清除无效的认证信息
        this.clearAuth();
      }
    }

    // 生成临时用户ID和邮箱
    const tempUserId = `temp_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    const tempEmail = `${tempUserId}@example.com`;
    // 创建一个满足密码强度要求的临时密码
    const tempPassword = `TempPass123!${Math.random().toString(36).substr(2, 4)}`;
    const tempUser: User = { username: tempUserId, email: tempEmail };

    try {
      // 尝试注册临时用户
      const userResponse = await apiService.register(tempUserId, tempEmail, tempPassword);

      // 设置用户token
      apiService.setToken(userResponse.access_token);

      // 创建聊天会话
      const sessionResponse = await apiService.createSession();

      // 使用会话token进行后续的聊天
      this.setAuth(sessionResponse.token, tempUser);
      return tempUser;
    } catch (error) {
      console.warn('Registration failed, attempting login:', error);
      // 如果注册失败，可能是因为用户已存在，尝试登录
      try {
        const loginResponse = await apiService.login(tempEmail, tempPassword);

        // 设置用户token
        apiService.setToken(loginResponse.access_token);

        // 创建聊天会话
        const sessionResponse = await apiService.createSession();

        // 使用会话token进行后续的聊天
        this.setAuth(sessionResponse.token, tempUser);
        return tempUser;
      } catch (loginError) {
        console.error('Both registration and login failed:', loginError);
        throw new Error('Failed to create temporary session');
      }
    }
  }
}

export interface User {
  id?: string | number;
  username: string;
  email?: string;
}

export const authService = new AuthService();

// 导出 getAuthHeaders 函数供其他模块使用
export const getAuthHeaders = async (): Promise<Record<string, string>> => {
  const token = authService.getToken();
  if (!token) {
    throw new Error('No authentication token found');
  }
  return {
    Authorization: `Bearer ${token}`,
  };
};
