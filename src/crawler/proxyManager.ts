import axios from 'axios';
import { config } from '../config';

/**
 * 代理信息接口
 */
export interface ProxyInfo {
  ip: string;
  port: number;
  username?: string;
  password?: string;
  protocol?: 'http' | 'https';
  country?: string;
  lastChecked?: Date;
  successRate?: number;
}

/**
 * 代理管理器
 * 负责代理池的管理、轮换和健康检查
 */
export class ProxyManager {
  private proxyPool: ProxyInfo[] = [];
  private currentIndex = 0;
  private proxyPoolUrl?: string;
  private lastFetchTime: number = 0;
  private fetchInterval: number = 5 * 60 * 1000; // 5 分钟

  constructor(proxyPoolUrl?: string) {
    this.proxyPoolUrl = proxyPoolUrl || config.proxyPoolUrl;
  }

  /**
   * 初始化代理池
   */
  async initialize(): Promise<void> {
    if (!this.proxyPoolUrl) {
      console.log('未配置代理池 URL，将不使用代理');
      return;
    }

    try {
      await this.fetchProxyList();
      console.log(`代理池初始化完成，共 ${this.proxyPool.length} 个代理`);
    } catch (error) {
      console.error('代理池初始化失败', error);
    }
  }

  /**
   * 从远程服务获取代理列表
   */
  private async fetchProxyList(): Promise<void> {
    if (!this.proxyPoolUrl) return;

    // 避免频繁请求
    const now = Date.now();
    if (now - this.lastFetchTime < this.fetchInterval && this.proxyPool.length > 0) {
      return;
    }

    try {
      const response = await axios.get(this.proxyPoolUrl, {
        timeout: 10000
      });

      // 假设返回格式为：[{ip, port, username, password}, ...]
      const proxies = response.data as Array<{
        ip: string;
        port: number;
        username?: string;
        password?: string;
      }>;

      this.proxyPool = proxies.map(p => ({
        ...p,
        protocol: 'https',
        lastChecked: new Date(),
        successRate: 100
      }));

      this.lastFetchTime = now;
    } catch (error) {
      console.error('获取代理列表失败', error);
      throw error;
    }
  }

  /**
   * 添加代理到池
   */
  addProxy(proxy: ProxyInfo): void {
    this.proxyPool.push(proxy);
  }

  /**
   * 移除代理
   */
  removeProxy(proxyIp: string): void {
    this.proxyPool = this.proxyPool.filter(p => p.ip !== proxyIp);
  }

  /**
   * 获取下一个代理（轮换）
   */
  getNextProxy(): ProxyInfo | null {
    if (this.proxyPool.length === 0) {
      return null;
    }

    const proxy = this.proxyPool[this.currentIndex];
    this.currentIndex = (this.currentIndex + 1) % this.proxyPool.length;
    
    return proxy;
  }

  /**
   * 获取随机代理
   */
  getRandomProxy(): ProxyInfo | null {
    if (this.proxyPool.length === 0) {
      return null;
    }

    const randomIndex = Math.floor(Math.random() * this.proxyPool.length);
    return this.proxyPool[randomIndex];
  }

  /**
   * 获取代理池大小
   */
  getPoolSize(): number {
    return this.proxyPool.length;
  }

  /**
   * 检查代理是否可用
   */
  async checkProxy(proxy: ProxyInfo): Promise<boolean> {
    try {
      const proxyUrl = this.buildProxyUrl(proxy);
      
      const response = await axios.get('https://httpbin.org/ip', {
        proxy: {
          protocol: proxy.protocol || 'https',
          host: proxy.ip,
          port: proxy.port,
          auth: proxy.username && proxy.password ? {
            username: proxy.username,
            password: proxy.password
          } : undefined
        },
        timeout: 10000
      });

      return response.status === 200;
    } catch (error) {
      return false;
    }
  }

  /**
   * 更新代理成功率
   */
  updateProxySuccessRate(proxyIp: string, success: boolean): void {
    const proxy = this.proxyPool.find(p => p.ip === proxyIp);
    if (!proxy) return;

    const currentRate = proxy.successRate || 100;
    const newRate = success 
      ? Math.min(100, currentRate + 1)
      : Math.max(0, currentRate - 10);
    
    proxy.successRate = newRate;
    proxy.lastChecked = new Date();

    // 如果成功率太低，移除代理
    if (newRate < 50) {
      this.removeProxy(proxyIp);
      console.log(`移除低质量代理：${proxyIp} (成功率：${newRate}%)`);
    }
  }

  /**
   * 构建代理 URL
   */
  buildProxyUrl(proxy: ProxyInfo): string {
    const protocol = proxy.protocol || 'https';
    const auth = proxy.username && proxy.password
      ? `${proxy.username}:${proxy.password}@`
      : '';
    
    return `${protocol}://${auth}${proxy.ip}:${proxy.port}`;
  }

  /**
   * 获取 Axios 代理配置
   */
  getAxiosProxyConfig(proxy: ProxyInfo | null): any {
    if (!proxy) {
      return undefined;
    }

    return {
      protocol: proxy.protocol || 'https',
      host: proxy.ip,
      port: proxy.port,
      auth: proxy.username && proxy.password ? {
        username: proxy.username,
        password: proxy.password
      } : undefined
    };
  }

  /**
   * 获取所有可用代理（成功率 > 50%）
   */
  getAvailableProxies(): ProxyInfo[] {
    return this.proxyPool.filter(p => (p.successRate || 0) > 50);
  }

  /**
   * 清空代理池
   */
  clear(): void {
    this.proxyPool = [];
    this.currentIndex = 0;
  }
}

// 导出单例实例
export const proxyManager = new ProxyManager();
