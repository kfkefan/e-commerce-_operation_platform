import UserAgent from 'user-agents';
import { config } from '../config';

/**
 * User-Agent 轮换器
 * 负责生成和管理随机的 User-Agent 字符串
 */
export class UserAgentRotator {
  private userAgent: UserAgent | null = null;

  /**
   * 获取随机 User-Agent
   */
  getRandomUserAgent(): string {
    this.userAgent = new UserAgent();
    return this.userAgent.toString();
  }

  /**
   * 获取当前 User-Agent
   */
  getCurrentUserAgent(): string | null {
    return this.userAgent?.toString() || null;
  }

  /**
   * 获取桌面端 User-Agent
   */
  getDesktopUserAgent(): string {
    return new UserAgent({ deviceCategory: 'desktop' }).toString();
  }

  /**
   * 获取移动端 User-Agent
   */
  getMobileUserAgent(): string {
    return new UserAgent({ deviceCategory: 'mobile' }).toString();
  }

  /**
   * 获取指定浏览器的 User-Agent
   */
  getBrowserUserAgent(browser: 'chrome' | 'firefox' | 'safari' | 'edge'): string {
    const userAgent = new UserAgent();
    const uaString = userAgent.toString();
    
    // 根据浏览器类型筛选（简化实现，实际可以更精确）
    switch (browser) {
      case 'chrome':
        return uaString.includes('Chrome') ? uaString : this.getDesktopUserAgent();
      case 'firefox':
        return uaString.includes('Firefox') ? uaString : this.getDesktopUserAgent();
      case 'safari':
        return uaString.includes('Safari') && !uaString.includes('Chrome') 
          ? uaString 
          : this.getDesktopUserAgent();
      case 'edge':
        return uaString.includes('Edg') ? uaString : this.getDesktopUserAgent();
      default:
        return this.getDesktopUserAgent();
    }
  }

  /**
   * 批量获取多个 User-Agent
   */
  batchGetUserAgents(count: number): string[] {
    const userAgents: string[] = [];
    for (let i = 0; i < count; i++) {
      userAgents.push(this.getRandomUserAgent());
    }
    return userAgents;
  }
}

// 导出单例实例
export const userAgentRotator = new UserAgentRotator();
