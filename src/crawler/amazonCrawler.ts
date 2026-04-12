import axios, { AxiosError } from 'axios';
import axiosRetry from 'axios-retry';
import PQueue from 'p-queue';
import { config } from '../config';
import { userAgentRotator } from './userAgentRotator';
import { proxyManager } from './proxyManager';
import { RankFinder } from './rankFinder';

/**
 * 排名结果类型
 */
export interface RankResult {
  keyword: string;
  organicPage: number | null;
  organicPosition: number | null;
  adPage: number | null;
  adPosition: number | null;
  status: 'found' | 'ad_only' | 'organic_only' | 'not_found';
  rawHtml?: string;
}

/**
 * 爬虫配置
 */
export interface ScraperConfig {
  requestDelayMin: number;
  requestDelayMax: number;
  maxRetries: number;
  retryDelay: number;
  timeout: number;
}

/**
 * 亚马逊爬虫核心类
 * 负责搜索亚马逊并提取 ASIN 排名信息
 */
export class AmazonCrawler {
  private config: ScraperConfig;
  private rankFinder: RankFinder | null = null;
  private requestQueue: PQueue;
  private isPaused = false;

  constructor(config?: Partial<ScraperConfig>) {
    this.config = {
      requestDelayMin: config?.requestDelayMin ?? 2000,
      requestDelayMax: config?.requestDelayMax ?? 5000,
      maxRetries: config?.maxRetries ?? 3,
      retryDelay: config?.retryDelay ?? 1000,
      timeout: config?.timeout ?? 30000
    };

    // 初始化请求队列（单并发，速率限制）
    this.requestQueue = new PQueue({
      concurrency: 1,
      interval: this.config.requestDelayMin,
      intervalCap: 1
    });

    // 初始化代理池
    try {
      proxyManager.initialize().catch(console.error);
    } catch (e) {
      // 忽略初始化错误
    }
  }

  /**
   * 搜索并提取排名
   * @param keyword 搜索关键词
   * @param targetAsin 目标 ASIN
   * @param maxPages 最大翻页数
   * @param site 亚马逊站点域名
   */
  async searchAndExtractRank(
    keyword: string,
    targetAsin: string,
    maxPages: number,
    site: string = 'amazon.com'
  ): Promise<RankResult> {
    this.rankFinder = new RankFinder(targetAsin);
    
    let finalResult: RankResult = {
      keyword,
      organicPage: null,
      organicPosition: null,
      adPage: null,
      adPosition: null,
      status: 'not_found'
    };

    // 逐页搜索
    for (let page = 1; page <= maxPages && !this.isPaused; page++) {
      try {
        // 添加随机延迟
        await this.randomDelay();

        // 获取搜索页面 HTML
        const html = await this.fetchSearchPage(keyword, page, site);

        // 检查是否是验证码页面
        if (this.rankFinder.isCaptchaPage(html)) {
          console.warn(`检测到验证码页面，暂停爬虫。关键词：${keyword}`);
          this.isPaused = true;
          finalResult.status = 'not_found';
          break;
        }

        // 检查是否是错误页面
        if (this.rankFinder.isErrorPage(html)) {
          console.warn(`检测到错误页面，重试。关键词：${keyword}, 页码：${page}`);
          continue;
        }

        // 查找 ASIN 位置
        const position = this.rankFinder.findAsinPosition(html, page);

        // 如果找到，记录结果并停止搜索
        if (position.status !== 'not_found') {
          finalResult = this.rankFinder.toRankResult(keyword, position, html);
          console.log(`找到排名 - 关键词：${keyword}, 状态：${position.status}, 自然页：${position.organicPage}, 广告页：${position.adPage}`);
          break;
        }

        // 如果已经翻到最后一页还没找到
        if (page === maxPages) {
          finalResult = this.rankFinder.toRankResult(keyword, position, html);
        }

      } catch (error) {
        console.error(`爬取失败 - 关键词：${keyword}, 页码：${page}`, error);
        
        // 如果是网络错误，继续尝试下一页
        if (this.isNetworkError(error)) {
          continue;
        }
        
        // 其他错误，返回未找到
        finalResult.status = 'not_found';
      }
    }

    // 重置爬虫状态
    this.isPaused = false;
    this.rankFinder = null;

    return finalResult;
  }

  /**
   * 获取搜索页面 HTML
   */
  private async fetchSearchPage(
    keyword: string,
    page: number,
    site: string
  ): Promise<string> {
    return this.requestQueue.add(async () => {
      // 构建搜索 URL
      const baseUrl = `https://www.${site}`;
      const searchPath = '/s';
      const params = new URLSearchParams({
        k: keyword,
        page: page.toString()
      });

      const url = `${baseUrl}${searchPath}?${params.toString()}`;

      // 获取代理配置
      const proxy = proxyManager.getNextProxy();

      // 创建 Axios 实例
      const client = axios.create({
        timeout: this.config.timeout,
        proxy: proxyManager.getAxiosProxyConfig(proxy),
        headers: {
          'User-Agent': userAgentRotator.getRandomUserAgent(),
          'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
          'Accept-Language': 'en-US,en;q=0.9',
          'Accept-Encoding': 'gzip, deflate, br',
          'Connection': 'keep-alive',
          'Upgrade-Insecure-Requests': '1',
          'Cache-Control': 'max-age=0'
        }
      });

      // 配置重试机制
      axiosRetry(client, {
        retries: this.config.maxRetries,
        retryDelay: (retryCount) => {
          return this.config.retryDelay * Math.pow(2, retryCount);
        },
        retryCondition: (error) => {
          return this.isNetworkError(error) || 
                 (error.response && error.response.status >= 500);
        },
        onRetry: (retryCount, error, requestConfig) => {
          console.log(`重试请求 - URL: ${url}, 次数：${retryCount}, 原因：${error.message}`);
          // 轮换 User-Agent
          if (requestConfig.headers) {
            requestConfig.headers['User-Agent'] = userAgentRotator.getRandomUserAgent();
          }
        }
      });

      // 发送请求
      const response = await client.get(url);
      
      // 更新代理成功率
      if (proxy) {
        proxyManager.updateProxySuccessRate(proxy.ip, true);
      }

      return response.data;
    });
  }

  /**
   * 随机延迟
   */
  private async randomDelay(): Promise<void> {
    const delay = Math.random() * (this.config.requestDelayMax - this.config.requestDelayMin) + 
                  this.config.requestDelayMin;
    return new Promise(resolve => setTimeout(resolve, delay));
  }

  /**
   * 判断是否是网络错误
   */
  private isNetworkError(error: any): boolean {
    if (!error) return false;
    
    const networkErrorCodes = [
      'ETIMEDOUT',
      'ECONNRESET',
      'ECONNREFUSED',
      'ENOTFOUND',
      'ENETUNREACH',
      'EAI_AGAIN'
    ];

    return networkErrorCodes.includes(error.code) ||
           (error.response && error.response.status >= 500) ||
           error.message?.includes('timeout') ||
           error.message?.includes('network');
  }

  /**
   * 暂停爬虫
   */
  pause(): void {
    this.isPaused = true;
    console.log('爬虫已暂停');
  }

  /**
   * 继续爬虫
   */
  resume(): void {
    this.isPaused = false;
    console.log('爬虫已继续');
  }

  /**
   * 检查爬虫状态
   */
  isRunning(): boolean {
    return !this.isPaused;
  }

  /**
   * 清除暂停状态
   */
  clearPause(): void {
    this.isPaused = false;
  }
}

// 导出单例实例（可选）
export const amazonCrawler = new AmazonCrawler();
