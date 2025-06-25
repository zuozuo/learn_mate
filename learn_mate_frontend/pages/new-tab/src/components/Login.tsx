import { authService } from '../services/auth';
import { useState } from 'react';
import type React from 'react';
import './Login.scss';

interface LoginProps {
  onLoginSuccess: () => void;
}

export const Login: React.FC<LoginProps> = ({ onLoginSuccess }) => {
  const [isLogin, setIsLogin] = useState(true);
  const [email, setEmail] = useState('');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [rememberMe, setRememberMe] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      if (isLogin) {
        // 登录
        const response = await authService.login(email, password, rememberMe);
        if (response) {
          onLoginSuccess();
        }
      } else {
        // 注册
        if (!username) {
          setError('请输入用户名');
          return;
        }
        const response = await authService.register(email, username, password);
        if (response) {
          // 注册成功后自动登录
          const loginResponse = await authService.login(email, password, false);
          if (loginResponse) {
            onLoginSuccess();
          }
        }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : '操作失败，请重试');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-container">
      <div className="login-box">
        <div className="login-header">
          <h1>LearnMate</h1>
          <p>{isLogin ? '登录您的账户' : '创建新账户'}</p>
        </div>

        <form onSubmit={handleSubmit} className="login-form">
          <div className="form-group">
            <label htmlFor="email">邮箱</label>
            <input
              type="email"
              id="email"
              value={email}
              onChange={e => setEmail(e.target.value)}
              placeholder="请输入邮箱"
              required
              disabled={loading}
            />
          </div>

          {!isLogin && (
            <div className="form-group">
              <label htmlFor="username">用户名</label>
              <input
                type="text"
                id="username"
                value={username}
                onChange={e => setUsername(e.target.value)}
                placeholder="请输入用户名"
                pattern="[a-zA-Z0-9_-]{3,50}"
                title="用户名只能包含字母、数字、下划线和横线，3-50个字符"
                required
                disabled={loading}
              />
            </div>
          )}

          <div className="form-group">
            <label htmlFor="password">密码</label>
            <input
              type="password"
              id="password"
              value={password}
              onChange={e => setPassword(e.target.value)}
              placeholder="请输入密码"
              minLength={8}
              required
              disabled={loading}
            />
          </div>

          {isLogin && (
            <div className="form-group checkbox-group">
              <label>
                <input
                  type="checkbox"
                  checked={rememberMe}
                  onChange={e => setRememberMe(e.target.checked)}
                  disabled={loading}
                />
                记住我
              </label>
            </div>
          )}

          {error && <div className="error-message">{error}</div>}

          <button type="submit" className="submit-button" disabled={loading}>
            {loading ? '处理中...' : isLogin ? '登录' : '注册'}
          </button>
        </form>

        <div className="login-footer">
          <button
            type="button"
            className="switch-button"
            onClick={() => {
              setIsLogin(!isLogin);
              setError('');
            }}
            disabled={loading}>
            {isLogin ? '没有账户？立即注册' : '已有账户？立即登录'}
          </button>

          <button
            type="button"
            className="guest-button"
            onClick={async () => {
              setLoading(true);
              try {
                await authService.createTemporarySession();
                onLoginSuccess();
              } catch (err) {
                setError(err instanceof Error ? err.message : '创建临时会话失败');
              } finally {
                setLoading(false);
              }
            }}
            disabled={loading}>
            以访客身份继续
          </button>
        </div>
      </div>
    </div>
  );
};
