import * as cheerio from 'cheerio';
import type { RankResult } from './amazonCrawler';

/**
 * ASIN 位置信息
 */
export interface AsinPosition {
  organicPage: number | null;
  organicPosition: number | null;
  adPage: number | null;
  adPosition: number | null;
  status: 'found' | 'ad_only' | 'organic_only' | 'not_found';
}

/**
 * 排名查找器
 * 负责在搜索结果中查找指定 ASIN 的排名位置
 */
export class RankFinder {
  private targetAsin: string;

  constructor(asin: string) {
    this.targetAsin = asin.toUpperCase();
  }

  /**
   * 解析 HTML 并查找 ASIN 位置
   */
  findAsinPosition(html: string, page: number): AsinPosition {
    const $ = cheerio.load(html);
    
    let organicPage: number | null = null;
    let organicPosition: number | null = null;
    let adPage: number | null = null;
    let adPosition: number | null = null;

    // 查找自然搜索结果
    const organicResult = this.findOrganicPosition($, page);
    if (organicResult) {
      organicPage = organicResult.page;
      organicPosition = organicResult.position;
    }

    // 查找广告结果
    const adResult = this.findAdPosition($, page);
    if (adResult) {
      adPage = adResult.page;
      adPosition = adResult.position;
    }

    // 确定状态
    let status: AsinPosition['status'] = 'not_found';
    if (organicPage !== null && adPage !== null) {
      status = 'found';
    } else if (adPage !== null) {
      status = 'ad_only';
    } else if (organicPage !== null) {
      status = 'organic_only';
    }

    return {
      organicPage,
      organicPosition,
      adPage,
      adPosition,
      status
    };
  }

  /**
   * 查找自然排名位置
   */
  private findOrganicPosition($: cheerio.CheerioAPI, page: number): { page: number; position: number } | null {
    // 亚马逊自然搜索结果的选择器
    // 注意：这些选择器可能会随亚马逊页面结构变化而需要更新
    const organicSelectors = [
      'div.s-result-item[data-asin]',  // 通用结果项
      'li[data-asin]',                  // 列表项格式
      'div[data-component-type="s-search-result"]'  // 搜索组件
    ];

    let position = 0;

    for (const selector of organicSelectors) {
      $(selector).each((index, element) => {
        const asin = $(element).attr('data-asin');
        if (asin && asin.toUpperCase() === this.targetAsin) {
          position = index + 1;
          return false; // 找到后退出循环
        }
      });

      if (position > 0) {
        return { page, position };
      }
    }

    return null;
  }

  /**
   * 查找广告排名位置
   */
  private findAdPosition($: cheerio.CheerioAPI, page: number): { page: number; position: number } | null {
    // 亚马逊广告结果的选择器
    const adSelectors = [
      'div.s-result-item[data-ad-id]',           // 带广告 ID 的结果
      'div[data-component-type="s-sponsored-product"]',  // 赞助产品组件
      'li[data-ad-id]',                          // 广告列表项
      'div.s-sponsored-label'                    // 赞助标签（需要找相邻元素）
    ];

    let position = 0;

    // 方法 1: 直接查找带广告标识的 ASIN
    for (const selector of adSelectors) {
      if (selector.includes('data-asin')) {
        // 如果选择器包含 ASIN，直接查找
        $(selector).each((index, element) => {
          const asin = $(element).attr('data-asin');
          if (asin && asin.toUpperCase() === this.targetAsin) {
            position = index + 1;
            return false;
          }
        });
      } else {
        // 查找广告容器，然后在其中找 ASIN
        $(selector).each((index, element) => {
          // 向上查找最近的 result-item
          const resultItem = $(element).closest('div.s-result-item, li');
          if (resultItem.length > 0) {
            const asin = resultItem.attr('data-asin');
            if (asin && asin.toUpperCase() === this.targetAsin) {
              position = index + 1;
              return false;
            }
          }
        });
      }

      if (position > 0) {
        return { page, position };
      }
    }

    // 方法 2: 查找赞助标签附近的 ASIN
    const sponsoredLabels = $('div.s-sponsored-label, span:contains("Sponsored"), span:contains("赞助")');
    if (sponsoredLabels.length > 0) {
      let adIndex = 0;
      sponsoredLabels.each((labelIndex, labelElement) => {
        // 查找标签后面的结果项
        const resultItem = $(labelElement).closest('div.s-result-item, li');
        if (resultItem.length > 0) {
          const asin = resultItem.attr('data-asin');
          if (asin && asin.toUpperCase() === this.targetAsin) {
            position = adIndex + 1;
            return false;
          }
          adIndex++;
        }
      });

      if (position > 0) {
        return { page, position };
      }
    }

    return null;
  }

  /**
   * 检测是否是验证码页面
   */
  isCaptchaPage(html: string): boolean {
    const $ = cheerio.load(html);
    
    // 检测验证码页面的特征
    const captchaIndicators = [
      'input[type="text"][name*="captcha"]',
      'img[src*="captcha"]',
      '.captcha',
      '#captcha',
      'text:contains("CAPTCHA")',
      'text:contains("验证码")',
      'text:contains("robot")',
      'text:contains("automated")'
    ];

    for (const selector of captchaIndicators) {
      if ($(selector).length > 0) {
        return true;
      }
    }

    // 检查页面标题是否包含验证码相关词汇
    const title = $('title').text().toLowerCase();
    if (title.includes('captcha') || title.includes('robot') || title.includes('automated')) {
      return true;
    }

    return false;
  }

  /**
   * 检测是否是错误页面
   */
  isErrorPage(html: string): boolean {
    const $ = cheerio.load(html);
    
    const errorIndicators = [
      'text:contains("404")',
      'text:contains("503")',
      'text:contains("Service Unavailable")',
      'text:contains("Temporarily unavailable")',
      '#twister-error-message',
      '.a-error-page'
    ];

    for (const selector of errorIndicators) {
      if ($(selector).length > 0) {
        return true;
      }
    }

    // 检查 HTTP 状态码相关的错误信息
    const body = $('body').text();
    if (body.includes('404') || body.includes('503') || body.includes('500')) {
      return true;
    }

    return false;
  }

  /**
   * 提取搜索结果总数（如果有）
   */
  extractTotalResults(html: string): number | null {
    const $ = cheerio.load(html);
    
    // 尝试从不同位置提取结果总数
    const resultTextSelectors = [
      '.sg-col-inner',  // 搜索结果统计
      '#search .a-color-state',
      '[data-component-type="search-results"]'
    ];

    for (const selector of resultTextSelectors) {
      const text = $(selector).first().text();
      const match = text.match(/(\d{1,3}(?:,\d{3})*)/);
      if (match) {
        return parseInt(match[1].replace(/,/g, ''), 10);
      }
    }

    return null;
  }

  /**
   * 将 AsinPosition 转换为 RankResult
   */
  toRankResult(
    keyword: string,
    position: AsinPosition,
    rawHtml?: string
  ): RankResult {
    return {
      keyword,
      organicPage: position.organicPage,
      organicPosition: position.organicPosition,
      adPage: position.adPage,
      adPosition: position.adPosition,
      status: position.status,
      rawHtml: rawHtml
    };
  }
}
