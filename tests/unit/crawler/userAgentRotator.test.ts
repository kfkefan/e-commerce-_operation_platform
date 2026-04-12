import { describe, it, expect, beforeEach } from 'vitest';
import { UserAgentRotator } from '../../../src/crawler/userAgentRotator';

describe('UserAgentRotator', () => {
  let rotator: UserAgentRotator;

  beforeEach(() => {
    rotator = new UserAgentRotator();
  });

  describe('getRandomUserAgent', () => {
    it('应该返回非空字符串', () => {
      const ua = rotator.getRandomUserAgent();
      expect(ua).toBeDefined();
      expect(typeof ua).toBe('string');
      expect(ua.length).toBeGreaterThan(0);
    });

    it('应该返回有效的 User-Agent 格式', () => {
      const ua = rotator.getRandomUserAgent();
      // User-Agent 应该包含浏览器信息
      expect(ua).toMatch(/Mozilla\/\d+\.\d+/);
    });

    it('应该每次返回不同的 User-Agent（随机性）', () => {
      const userAgents = new Set<string>();
      for (let i = 0; i < 10; i++) {
        userAgents.add(rotator.getRandomUserAgent());
      }
      // 由于是随机的，应该至少有一些不同的 UA
      expect(userAgents.size).toBeGreaterThan(1);
    });

    it('应该更新当前 User-Agent', () => {
      const ua = rotator.getRandomUserAgent();
      const current = rotator.getCurrentUserAgent();
      expect(current).toBe(ua);
    });
  });

  describe('getCurrentUserAgent', () => {
    it('应该在未设置时返回 null', () => {
      const freshRotator = new UserAgentRotator();
      // 注意：由于模块可能已经初始化，这里测试新实例
      expect(freshRotator.getCurrentUserAgent()).toBeNull();
    });

    it('应该在设置后返回当前 User-Agent', () => {
      const ua = rotator.getRandomUserAgent();
      const current = rotator.getCurrentUserAgent();
      expect(current).toBe(ua);
    });
  });

  describe('getDesktopUserAgent', () => {
    it('应该返回桌面端 User-Agent', () => {
      const ua = rotator.getDesktopUserAgent();
      expect(ua).toBeDefined();
      expect(typeof ua).toBe('string');
      expect(ua.length).toBeGreaterThan(0);
    });

    it('应该包含桌面浏览器特征', () => {
      const ua = rotator.getDesktopUserAgent();
      // 桌面 UA 通常包含 Windows、Macintosh 或 Linux
      expect(ua).toMatch(/(Windows|Macintosh|Linux)/);
    });
  });

  describe('getMobileUserAgent', () => {
    it('应该返回移动端 User-Agent', () => {
      const ua = rotator.getMobileUserAgent();
      expect(ua).toBeDefined();
      expect(typeof ua).toBe('string');
      expect(ua.length).toBeGreaterThan(0);
    });

    it('应该包含移动设备特征', () => {
      const ua = rotator.getMobileUserAgent();
      // 移动 UA 通常包含 Android 或 iPhone
      expect(ua).toMatch(/(Android|iPhone)/);
    });
  });

  describe('getBrowserUserAgent', () => {
    it('应该返回 Chrome User-Agent', () => {
      const ua = rotator.getBrowserUserAgent('chrome');
      expect(ua).toBeDefined();
      expect(typeof ua).toBe('string');
      expect(ua.length).toBeGreaterThan(0);
    });

    it('应该返回 Firefox User-Agent', () => {
      const ua = rotator.getBrowserUserAgent('firefox');
      expect(ua).toBeDefined();
      expect(typeof ua).toBe('string');
      expect(ua.length).toBeGreaterThan(0);
    });

    it('应该返回 Safari User-Agent', () => {
      const ua = rotator.getBrowserUserAgent('safari');
      expect(ua).toBeDefined();
      expect(typeof ua).toBe('string');
      expect(ua.length).toBeGreaterThan(0);
    });

    it('应该返回 Edge User-Agent', () => {
      const ua = rotator.getBrowserUserAgent('edge');
      expect(ua).toBeDefined();
      expect(typeof ua).toBe('string');
      expect(ua.length).toBeGreaterThan(0);
    });

    it('应该处理无效浏览器类型（返回默认）', () => {
      // @ts-ignore - 测试无效输入
      const ua = rotator.getBrowserUserAgent('invalid');
      expect(ua).toBeDefined();
      expect(typeof ua).toBe('string');
    });
  });

  describe('batchGetUserAgents', () => {
    it('应该返回指定数量的 User-Agent 数组', () => {
      const userAgents = rotator.batchGetUserAgents(5);
      expect(userAgents).toHaveLength(5);
      expect(Array.isArray(userAgents)).toBe(true);
    });

    it('应该返回空数组当数量为 0', () => {
      const userAgents = rotator.batchGetUserAgents(0);
      expect(userAgents).toHaveLength(0);
    });

    it('应该返回非空字符串数组', () => {
      const userAgents = rotator.batchGetUserAgents(3);
      userAgents.forEach(ua => {
        expect(ua).toBeDefined();
        expect(typeof ua).toBe('string');
        expect(ua.length).toBeGreaterThan(0);
      });
    });

    it('应该返回不同的 User-Agent（随机性）', () => {
      const userAgents = rotator.batchGetUserAgents(10);
      const uniqueSet = new Set(userAgents);
      // 由于是随机的，应该至少有一些不同的 UA
      expect(uniqueSet.size).toBeGreaterThan(1);
    });

    it('应该处理大数量请求', () => {
      const userAgents = rotator.batchGetUserAgents(100);
      expect(userAgents).toHaveLength(100);
    });
  });

  describe('边界条件测试', () => {
    it('应该处理负数数量（返回空数组）', () => {
      // @ts-ignore - 测试边界条件
      const userAgents = rotator.batchGetUserAgents(-1);
      expect(userAgents).toHaveLength(0);
    });

    it('应该处理非整数数量', () => {
      // @ts-ignore - 测试边界条件
      const userAgents = rotator.batchGetUserAgents(3.5);
      expect(Array.isArray(userAgents)).toBe(true);
    });

    it('应该处理极大数量', () => {
      const userAgents = rotator.batchGetUserAgents(1000);
      expect(userAgents.length).toBe(1000);
    });

    it('应该连续调用不抛出异常', () => {
      expect(() => {
        for (let i = 0; i < 100; i++) {
          rotator.getRandomUserAgent();
        }
      }).not.toThrow();
    });

    it('应该交替调用不同类型方法不抛出异常', () => {
      expect(() => {
        rotator.getRandomUserAgent();
        rotator.getDesktopUserAgent();
        rotator.getMobileUserAgent();
        rotator.getBrowserUserAgent('chrome');
        rotator.batchGetUserAgents(5);
      }).not.toThrow();
    });
  });

  describe('User-Agent 格式验证', () => {
    it('应该符合标准 User-Agent 格式', () => {
      const ua = rotator.getRandomUserAgent();
      // 标准 UA 格式：Mozilla/5.0 (平台) AppleWebKit 浏览器版本
      expect(ua).toMatch(/^Mozilla\/\d+\.\d+/);
    });

    it('应该包含平台信息', () => {
      const ua = rotator.getRandomUserAgent();
      // UA 应该包含括号内的平台信息
      expect(ua).toMatch(/\([^)]+\)/);
    });

    it('应该包含浏览器信息', () => {
      const ua = rotator.getRandomUserAgent();
      // UA 应该包含浏览器标识（Chrome、Firefox、Safari 等）
      const hasBrowser = /(Chrome|Firefox|Safari|Edg|Opera)/.test(ua);
      expect(hasBrowser).toBe(true);
    });
  });
});
