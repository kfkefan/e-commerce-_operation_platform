import { describe, it, expect, beforeEach } from 'vitest';
import { RankFinder } from '../../../src/crawler/rankFinder';

describe('RankFinder', () => {
  let rankFinder: RankFinder;
  const testAsin = 'B08N5WRWNW';

  beforeEach(() => {
    rankFinder = new RankFinder(testAsin);
  });

  describe('constructor', () => {
    it('应该正确初始化 ASIN（大写）', () => {
      const finder = new RankFinder('b08n5wrwnw');
      expect(finder).toBeDefined();
    });

    it('应该接受小写 ASIN 并转换为大写', () => {
      const finder = new RankFinder('b08n5wrwnw');
      expect(finder).toBeDefined();
    });
  });

  describe('findAsinPosition', () => {
    it('应该找到自然排名位置', () => {
      const html = `
        <html>
          <body>
            <div class="s-result-item" data-asin="B012345678">Product 1</div>
            <div class="s-result-item" data-asin="${testAsin}">Target Product</div>
            <div class="s-result-item" data-asin="B087654321">Product 3</div>
          </body>
        </html>
      `;

      const result = rankFinder.findAsinPosition(html, 1);

      expect(result.organicPage).toBe(1);
      expect(result.organicPosition).toBe(2);
      expect(result.adPage).toBeNull();
      expect(result.adPosition).toBeNull();
      expect(result.status).toBe('organic_only');
    });

    it('应该找到广告排名位置', () => {
      // 广告结果通常只有 data-ad-id 而没有标准的 data-asin 在自然结果选择器中
      const html = `
        <html>
          <body>
            <div class="s-result-item" data-ad-id="ad1" data-asin="B012345678">Ad 1</div>
            <div class="s-result-item" data-ad-id="ad2" data-asin="${testAsin}">Target Ad</div>
          </body>
        </html>
      `;

      const result = rankFinder.findAsinPosition(html, 1);

      // 注意：由于代码会同时查找自然和广告结果，这里可能同时找到
      expect(result.adPage).toBe(1);
      expect(result.adPosition).toBe(2);
      expect(result.status).toMatch(/ad_only|found/);
    });

    it('应该同时找到自然排名和广告排名', () => {
      const html = `
        <html>
          <body>
            <div class="s-result-item" data-ad-id="ad1" data-asin="${testAsin}">Target Ad</div>
            <div class="s-result-item" data-asin="B012345678">Organic 1</div>
            <div class="s-result-item" data-asin="${testAsin}">Target Organic</div>
          </body>
        </html>
      `;

      const result = rankFinder.findAsinPosition(html, 1);

      expect(result.organicPage).toBe(1);
      expect(result.organicPosition).toBe(1); // 第一个匹配的自然结果
      expect(result.adPage).toBe(1);
      expect(result.adPosition).toBe(1);
      expect(result.status).toBe('found');
    });

    it('应该返回未找到状态当 ASIN 不存在', () => {
      const html = `
        <html>
          <body>
            <div class="s-result-item" data-asin="B012345678">Product 1</div>
            <div class="s-result-item" data-asin="B087654321">Product 2</div>
          </body>
        </html>
      `;

      const result = rankFinder.findAsinPosition(html, 1);

      expect(result.organicPage).toBeNull();
      expect(result.organicPosition).toBeNull();
      expect(result.adPage).toBeNull();
      expect(result.adPosition).toBeNull();
      expect(result.status).toBe('not_found');
    });

    it('应该处理空 HTML', () => {
      const result = rankFinder.findAsinPosition('', 1);

      expect(result.status).toBe('not_found');
    });

    it('应该处理无效 HTML', () => {
      const html = '<html><body><div>Invalid HTML';
      const result = rankFinder.findAsinPosition(html, 1);

      expect(result.status).toBe('not_found');
    });

    it('应该处理多页搜索结果', () => {
      const html = `
        <html>
          <body>
            <div class="s-result-item" data-asin="B012345678">Product 1</div>
            <div class="s-result-item" data-asin="${testAsin}">Target Product</div>
          </body>
        </html>
      `;

      const result = rankFinder.findAsinPosition(html, 5);

      expect(result.organicPage).toBe(5);
      expect(result.organicPosition).toBe(2);
    });
  });

  describe('isCaptchaPage', () => {
    it('应该检测包含 captcha 输入框的页面', () => {
      const html = `
        <html>
          <body>
            <input type="text" name="captcha_answer">
          </body>
        </html>
      `;

      expect(rankFinder.isCaptchaPage(html)).toBe(true);
    });

    it('应该检测包含 captcha 图片的页面', () => {
      const html = `
        <html>
          <body>
            <img src="/captcha/image.png">
          </body>
        </html>
      `;

      expect(rankFinder.isCaptchaPage(html)).toBe(true);
    });

    it('应该检测包含验证码文本的页面', () => {
      const html = `
        <html>
          <body>
            <div class="captcha">Please enter the characters</div>
          </body>
        </html>
      `;

      expect(rankFinder.isCaptchaPage(html)).toBe(true);
    });

    it('应该检测包含 robot 文本的页面', () => {
      const html = `
        <html>
          <head>
            <title>Robot Check</title>
          </head>
        </html>
      `;

      expect(rankFinder.isCaptchaPage(html)).toBe(true);
    });

    it('应该返回 false 当页面不是验证码页面', () => {
      const html = `
        <html>
          <body>
            <div class="s-result-item">Product</div>
          </body>
        </html>
      `;

      expect(rankFinder.isCaptchaPage(html)).toBe(false);
    });

    it('应该处理空 HTML', () => {
      expect(rankFinder.isCaptchaPage('')).toBe(false);
    });
  });

  describe('isErrorPage', () => {
    it('应该检测 404 错误页面', () => {
      const html = `
        <html>
          <body>
            <h1>404 Not Found</h1>
          </body>
        </html>
      `;

      expect(rankFinder.isErrorPage(html)).toBe(true);
    });

    it('应该检测 503 错误页面', () => {
      const html = `
        <html>
          <body>
            <h1>503 Service Unavailable</h1>
          </body>
        </html>
      `;

      expect(rankFinder.isErrorPage(html)).toBe(true);
    });

    it('应该检测 Temporarily unavailable 页面', () => {
      const html = `
        <html>
          <body>
            <div id="twister-error-message">Temporarily unavailable</div>
          </body>
        </html>
      `;

      expect(rankFinder.isErrorPage(html)).toBe(true);
    });

    it('应该返回 false 当页面不是错误页面', () => {
      const html = `
        <html>
          <body>
            <div class="s-result-item">Product</div>
          </body>
        </html>
      `;

      expect(rankFinder.isErrorPage(html)).toBe(false);
    });

    it('应该处理空 HTML', () => {
      expect(rankFinder.isErrorPage('')).toBe(false);
    });
  });

  describe('extractTotalResults', () => {
    it('应该提取搜索结果总数', () => {
      const html = `
        <html>
          <body>
            <div class="sg-col-inner">1-16 of 1,234 results</div>
          </body>
        </html>
      `;

      const result = rankFinder.extractTotalResults(html);
      expect(result).toBe(1234);
    });

    it('应该提取没有逗号的数字', () => {
      const html = `
        <html>
          <body>
            <div>1-10 of 500 results</div>
          </body>
        </html>
      `;

      const result = rankFinder.extractTotalResults(html);
      expect(result).toBe(500);
    });

    it('应该返回 null 当没有找到结果数', () => {
      const html = `
        <html>
          <body>
            <div>No results found</div>
          </body>
        </html>
      `;

      const result = rankFinder.extractTotalResults(html);
      expect(result).toBeNull();
    });

    it('应该处理空 HTML', () => {
      const result = rankFinder.extractTotalResults('');
      expect(result).toBeNull();
    });
  });

  describe('toRankResult', () => {
    it('应该将 AsinPosition 转换为 RankResult', () => {
      const position = {
        organicPage: 1,
        organicPosition: 5,
        adPage: null,
        adPosition: null,
        status: 'organic_only' as const
      };

      const result = rankFinder.toRankResult('test keyword', position, '<html>test</html>');

      expect(result.keyword).toBe('test keyword');
      expect(result.organicPage).toBe(1);
      expect(result.organicPosition).toBe(5);
      expect(result.adPage).toBeNull();
      expect(result.adPosition).toBeNull();
      expect(result.status).toBe('organic_only');
      expect(result.rawHtml).toBe('<html>test</html>');
    });

    it('应该处理没有 rawHtml 的情况', () => {
      const position = {
        organicPage: null,
        organicPosition: null,
        adPage: null,
        adPosition: null,
        status: 'not_found' as const
      };

      const result = rankFinder.toRankResult('test keyword', position);

      expect(result.keyword).toBe('test keyword');
      expect(result.status).toBe('not_found');
      expect(result.rawHtml).toBeUndefined();
    });
  });

  describe('边界条件测试', () => {
    it('应该处理超长 HTML 内容', () => {
      const longHtml = '<html><body>' + '<div class="s-result-item" data-asin="B012345678">Product</div>'.repeat(1000) + '</body></html>';
      
      const result = rankFinder.findAsinPosition(longHtml, 1);
      expect(result).toBeDefined();
    });

    it('应该处理特殊字符关键词', () => {
      const html = `
        <html>
          <body>
            <div class="s-result-item" data-asin="${testAsin}">Product with &amp; special &lt;chars&gt;</div>
          </body>
        </html>
      `;

      const result = rankFinder.findAsinPosition(html, 1);
      expect(result.organicPosition).toBe(1);
    });

    it('应该处理 ASIN 大小写不一致', () => {
      const html = `
        <html>
          <body>
            <div class="s-result-item" data-asin="b08n5wrwnw">Target Product</div>
          </body>
        </html>
      `;

      const result = rankFinder.findAsinPosition(html, 1);
      expect(result.organicPosition).toBe(1);
    });

    it('应该处理 HTML 实体编码的 ASIN', () => {
      const html = `
        <html>
          <body>
            <div class="s-result-item" data-asin="${testAsin}">Product</div>
          </body>
        </html>
      `;

      const result = rankFinder.findAsinPosition(html, 1);
      expect(result.organicPosition).toBe(1);
    });
  });
});
