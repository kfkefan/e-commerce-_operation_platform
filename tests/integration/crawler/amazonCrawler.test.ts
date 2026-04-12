import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest';
import { AmazonCrawler } from '../../../src/crawler/amazonCrawler';
import axios from 'axios';
import { RankFinder } from '../../../src/crawler/rankFinder';

// Mock axios
vi.mock('axios', () => {
  const mockGet = vi.fn();
  const mockCreate = vi.fn().mockReturnValue({
    get: mockGet,
    defaults: {}
  });
  
  return {
    default: {
      create: mockCreate,
      get: mockGet,
      defaults: {}
    },
    __esModule: true
  };
});

const mockedAxios = vi.mocked(axios);

// Mock user-agents
vi.mock('user-agents', () => {
  return {
    default: class MockUserAgent {
      constructor(options?: any) {
        return 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36';
      }
      toString() {
        return 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36';
      }
    }
  };
});

// Mock proxyManager
vi.mock('../../../src/crawler/proxyManager', () => {
  return {
    proxyManager: {
      initialize: vi.fn().mockResolvedValue(undefined),
      getNextProxy: vi.fn().mockReturnValue(null),
      getAxiosProxyConfig: vi.fn().mockReturnValue(undefined),
      updateProxySuccessRate: vi.fn()
    }
  };
});

// Mock p-queue
vi.mock('p-queue', () => {
  return {
    default: class MockPQueue {
      constructor(options?: any) {}
      add(fn: any) {
        return fn();
      }
    }
  };
});

// Mock axios-retry
vi.mock('axios-retry', () => {
  return {
    default: vi.fn()
  };
});

describe('AmazonCrawler Integration', () => {
  let crawler: AmazonCrawler;
  const testAsin = 'B08N5WRWNW';
  const testKeyword = 'wireless earbuds';
  let mockGet: any;

  beforeEach(() => {
    vi.clearAllMocks();
    mockGet = vi.fn();
    mockedAxios.create.mockReturnValue({
      get: mockGet,
      defaults: {}
    } as any);
    
    crawler = new AmazonCrawler({
      requestDelayMin: 100,
      requestDelayMax: 200,
      maxRetries: 1,
      retryDelay: 100,
      timeout: 5000
    });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe('searchAndExtractRank', () => {
    it('应该找到自然排名', async () => {
      const mockHtml = `
        <html>
          <body>
            <div class="s-result-item" data-asin="B012345678">Product 1</div>
            <div class="s-result-item" data-asin="${testAsin}">Target Product</div>
            <div class="s-result-item" data-asin="B087654321">Product 3</div>
          </body>
        </html>
      `;

      mockGet.mockResolvedValue({ data: mockHtml });

      const result = await crawler.searchAndExtractRank(testKeyword, testAsin, 5);

      expect(result.keyword).toBe(testKeyword);
      expect(result.organicPage).toBe(1);
      expect(result.organicPosition).toBe(2);
      expect(result.status).toBe('organic_only');
    });

    it('应该找到广告排名', async () => {
      const mockHtml = `
        <html>
          <body>
            <div class="s-result-item" data-ad-id="ad1" data-asin="${testAsin}">Target Ad</div>
            <div class="s-result-item" data-asin="B012345678">Organic 1</div>
          </body>
        </html>
      `;

      mockGet.mockResolvedValue({ data: mockHtml });

      const result = await crawler.searchAndExtractRank(testKeyword, testAsin, 5);

      expect(result.keyword).toBe(testKeyword);
      expect(result.adPage).toBe(1);
      expect(result.adPosition).toBe(1);
      expect(result.status).toBe('ad_only');
    });

    it('应该同时找到自然排名和广告排名', async () => {
      const mockHtml = `
        <html>
          <body>
            <div class="s-result-item" data-ad-id="ad1" data-asin="${testAsin}">Target Ad</div>
            <div class="s-result-item" data-asin="B012345678">Organic 1</div>
            <div class="s-result-item" data-asin="${testAsin}">Target Organic</div>
          </body>
        </html>
      `;

      mockGet.mockResolvedValue({ data: mockHtml });

      const result = await crawler.searchAndExtractRank(testKeyword, testAsin, 5);

      expect(result.keyword).toBe(testKeyword);
      expect(result.organicPage).toBe(1);
      expect(result.organicPosition).toBe(2);
      expect(result.adPage).toBe(1);
      expect(result.adPosition).toBe(1);
      expect(result.status).toBe('found');
    });

    it('应该返回未找到当 ASIN 不在搜索结果中', async () => {
      const mockHtml = `
        <html>
          <body>
            <div class="s-result-item" data-asin="B012345678">Product 1</div>
            <div class="s-result-item" data-asin="B087654321">Product 2</div>
          </body>
        </html>
      `;

      mockGet.mockResolvedValue({ data: mockHtml });

      const result = await crawler.searchAndExtractRank(testKeyword, testAsin, 3);

      expect(result.keyword).toBe(testKeyword);
      expect(result.organicPage).toBeNull();
      expect(result.adPage).toBeNull();
      expect(result.status).toBe('not_found');
    });

    it('应该处理网络错误并重试', async () => {
      mockGet
        .mockRejectedValueOnce({ code: 'ETIMEDOUT', message: 'timeout' })
        .mockRejectedValueOnce({ code: 'ECONNRESET', message: 'connection reset' })
        .mockResolvedValue({ data: '<html><body></body></html>' });

      const result = await crawler.searchAndExtractRank(testKeyword, testAsin, 1);

      expect(mockGet).toHaveBeenCalledTimes(3); // 初始请求 + 2 次重试
      expect(result.status).toBe('not_found');
    });

    it('应该处理验证码页面', async () => {
      const captchaHtml = `
        <html>
          <head>
            <title>Robot Check</title>
          </head>
          <body>
            <input type="text" name="captcha_answer">
          </body>
        </html>
      `;

      mockGet.mockResolvedValue({ data: captchaHtml });

      const result = await crawler.searchAndExtractRank(testKeyword, testAsin, 5);

      expect(result.status).toBe('not_found');
    });

    it('应该处理错误页面', async () => {
      const errorHtml = `
        <html>
          <body>
            <h1>503 Service Unavailable</h1>
          </body>
        </html>
      `;

      mockGet.mockResolvedValue({ data: errorHtml });

      const result = await crawler.searchAndExtractRank(testKeyword, testAsin, 2);

      expect(result.status).toBe('not_found');
    });

    it('应该处理请求超时', async () => {
      mockGet.mockRejectedValue({ code: 'ETIMEDOUT', message: 'timeout' });

      const result = await crawler.searchAndExtractRank(testKeyword, testAsin, 1);

      expect(result.status).toBe('not_found');
    });

    it('应该处理 500 服务器错误', async () => {
      mockGet.mockRejectedValue({
        response: { status: 500 },
        message: 'Internal Server Error'
      });

      const result = await crawler.searchAndExtractRank(testKeyword, testAsin, 1);

      expect(result.status).toBe('not_found');
    });

    it('应该支持不同亚马逊站点', async () => {
      const mockHtml = `<html><body><div class="s-result-item" data-asin="${testAsin}">Product</div></body></html>`;

      mockGet.mockResolvedValue({ data: mockHtml });

      const sites = ['amazon.com', 'amazon.co.uk', 'amazon.de', 'amazon.co.jp'];

      for (const site of sites) {
        const result = await crawler.searchAndExtractRank(testKeyword, testAsin, 1, site);
        expect(result.organicPosition).toBe(1);
      }
    });
  });

  describe('pause/resume', () => {
    it('应该暂停爬虫', () => {
      crawler.pause();
      expect(crawler.isRunning()).toBe(false);
    });

    it('应该继续爬虫', () => {
      crawler.pause();
      expect(crawler.isRunning()).toBe(false);

      crawler.resume();
      expect(crawler.isRunning()).toBe(true);
    });

    it('应该清除暂停状态', () => {
      crawler.pause();
      crawler.clearPause();
      expect(crawler.isRunning()).toBe(true);
    });
  });

  describe('边界条件测试', () => {
    it('应该处理空关键词', async () => {
      const mockHtml = `<html><body></body></html>`;

      mockGet.mockResolvedValue({ data: mockHtml });

      const result = await crawler.searchAndExtractRank('', testAsin, 1);
      expect(result).toBeDefined();
      expect(result.status).toBe('not_found');
    });

    it('应该处理空 ASIN', async () => {
      const mockHtml = `<html><body><div class="s-result-item" data-asin="B012345678">Product</div></body></html>`;

      mockGet.mockResolvedValue({ data: mockHtml });

      const result = await crawler.searchAndExtractRank(testKeyword, '', 1);
      expect(result).toBeDefined();
    });

    it('应该处理 maxPages 为 0', async () => {
      const result = await crawler.searchAndExtractRank(testKeyword, testAsin, 0);
      expect(result.status).toBe('not_found');
    });

    it('应该处理大 maxPages 值', async () => {
      const mockHtml = `<html><body></body></html>`;

      mockGet.mockResolvedValue({ data: mockHtml });

      const result = await crawler.searchAndExtractRank(testKeyword, testAsin, 50);
      expect(result).toBeDefined();
    });

    it('应该处理特殊字符关键词', async () => {
      const mockHtml = `<html><body></body></html>`;

      mockGet.mockResolvedValue({ data: mockHtml });

      const specialKeyword = 'test & special <chars> "quotes"';
      const result = await crawler.searchAndExtractRank(specialKeyword, testAsin, 1);
      expect(result).toBeDefined();
    });

    it('应该处理 HTML 实体编码内容', async () => {
      const mockHtml = `
        <html>
          <body>
            <div class="s-result-item" data-asin="${testAsin}">Product &amp; More</div>
          </body>
        </html>
      `;

      mockGet.mockResolvedValue({ data: mockHtml });

      const result = await crawler.searchAndExtractRank(testKeyword, testAsin, 1);
      expect(result.organicPosition).toBe(1);
    });

    it('应该处理 malformed HTML', async () => {
      const malformedHtml = '<html><body><div>Unclosed div';

      mockGet.mockResolvedValue({ data: malformedHtml });

      const result = await crawler.searchAndExtractRank(testKeyword, testAsin, 1);
      expect(result).toBeDefined();
    });

    it('应该处理空响应', async () => {
      mockGet.mockResolvedValue({ data: '' });

      const result = await crawler.searchAndExtractRank(testKeyword, testAsin, 1);
      expect(result.status).toBe('not_found');
    });

    it('应该处理 null 响应', async () => {
      mockGet.mockResolvedValue({ data: null });

      const result = await crawler.searchAndExtractRank(testKeyword, testAsin, 1);
      expect(result).toBeDefined();
    });
  });

  describe('性能测试', () => {
    it('应该在合理时间内完成单关键词搜索', async () => {
      const mockHtml = `<html><body><div class="s-result-item" data-asin="${testAsin}">Product</div></body></html>`;

      mockGet.mockResolvedValue({ data: mockHtml });

      const startTime = Date.now();
      await crawler.searchAndExtractRank(testKeyword, testAsin, 1);
      const endTime = Date.now();

      // 考虑到延迟，应该在 2 秒内完成
      expect(endTime - startTime).toBeLessThan(2000);
    });
  });
});
