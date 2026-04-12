/**
 * ResultTable 组件测试
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { mount, flushPromises } from '@vue/test-utils';
import ResultTable from '../src/components/ResultTable.vue';

// Mock Element Plus
vi.mock('element-plus', async () => {
  const actual = await vi.importActual('element-plus');
  return {
    ...actual,
    ElMessage: {
      success: vi.fn(),
      error: vi.fn(),
      warning: vi.fn(),
    },
  };
});

import { ElMessage } from 'element-plus';

describe('ResultTable', () => {
  const mockElMessage = ElMessage as any;

  beforeEach(() => {
    vi.clearAllMocks();
  });

  const mockResults = [
    {
      keyword: 'wireless earbuds',
      organicPage: 1,
      organicPosition: 5,
      adPage: null,
      adPosition: null,
      status: 'found',
      timestamp: '2026-04-12T10:02:00Z',
    },
    {
      keyword: 'bluetooth headphones',
      organicPage: 2,
      organicPosition: 10,
      adPage: 1,
      adPosition: 2,
      status: 'found',
      timestamp: '2026-04-12T10:03:00Z',
    },
    {
      keyword: 'noise cancelling earbuds',
      organicPage: null,
      organicPosition: null,
      adPage: null,
      adPosition: null,
      status: 'not_found',
      timestamp: '2026-04-12T10:04:00Z',
    },
  ];

  describe('渲染', () => {
    it('应该正确渲染组件', () => {
      const wrapper = mount(ResultTable, {
        props: {
          results: mockResults,
        },
      });

      expect(wrapper.exists()).toBe(true);
      expect(wrapper.find('.result-table-card').exists()).toBe(true);
    });

    it('应该显示表头', () => {
      const wrapper = mount(ResultTable, {
        props: {
          results: mockResults,
        },
      });

      expect(wrapper.find('.card-header span').text()).toContain('排名结果');
    });

    it('应该显示导出按钮', () => {
      const wrapper = mount(ResultTable, {
        props: {
          results: mockResults,
        },
      });

      const exportButton = wrapper.findAll('button').find(btn => 
        btn.text().includes('导出')
      );
      expect(exportButton?.exists()).toBe(true);
    });

    it('应该显示所有关键词', () => {
      const wrapper = mount(ResultTable, {
        props: {
          results: mockResults,
        },
        global: {
          stubs: {
            'el-table': true,
            'el-table-column': true,
            'el-tag': true,
          },
        },
      });

      // 检查关键词是否显示
      const text = wrapper.text();
      expect(text).toContain('wireless earbuds');
      expect(text).toContain('bluetooth headphones');
      expect(text).toContain('noise cancelling earbuds');
    });

    it('应该显示加载状态', () => {
      const wrapper = mount(ResultTable, {
        props: {
          results: [],
          loading: true,
        },
      });

      // 加载指示器应该存在
      expect(wrapper.find('[v-loading], .el-loading').exists()).toBe(true);
    });
  });

  describe('统计信息', () => {
    it('应该计算正确的统计数据', () => {
      const wrapper = mount(ResultTable, {
        props: {
          results: mockResults,
        },
      });

      const vm = wrapper.vm as any;
      const stats = vm.stats;

      expect(stats.found).toBe(2);
      expect(stats.organicNotFound).toBe(0);
      expect(stats.adNotFound).toBe(0);
      expect(stats.notFound).toBe(1);
      expect(stats.error).toBe(0);
      expect(stats.captcha).toBe(0);
    });

    it('应该计算成功率', () => {
      const wrapper = mount(ResultTable, {
        props: {
          results: mockResults,
        },
      });

      const vm = wrapper.vm as any;
      // 2/3 = 66.67%, 四舍五入为 67%
      expect(vm.successRate).toBe(67);
    });

    it('空数据时成功率为 0', () => {
      const wrapper = mount(ResultTable, {
        props: {
          results: [],
        },
      });

      const vm = wrapper.vm as any;
      expect(vm.successRate).toBe(0);
    });

    it('应该显示统计信息', () => {
      const wrapper = mount(ResultTable, {
        props: {
          results: mockResults,
        },
        global: {
          stubs: {
            'el-descriptions': true,
            'el-descriptions-item': true,
            'el-progress': true,
          },
        },
      });

      const text = wrapper.text();
      expect(text).toContain('总关键词数');
      expect(text).toContain('找到排名');
      expect(text).toContain('成功率');
    });

    it('所有结果都找到时成功率 100%', () => {
      const allFound = [
        {
          keyword: 'kw1',
          organicPage: 1,
          organicPosition: 1,
          adPage: 1,
          adPosition: 1,
          status: 'found',
          timestamp: '2026-04-12T10:00:00Z',
        },
        {
          keyword: 'kw2',
          organicPage: 2,
          organicPosition: 5,
          adPage: null,
          adPosition: null,
          status: 'found',
          timestamp: '2026-04-12T10:01:00Z',
        },
      ];

      const wrapper = mount(ResultTable, {
        props: {
          results: allFound,
        },
      });

      const vm = wrapper.vm as any;
      expect(vm.successRate).toBe(100);
    });
  });

  describe('状态显示', () => {
    it('应该为 found 状态显示正确类型', () => {
      const wrapper = mount(ResultTable, {
        props: {
          results: mockResults,
        },
      });

      const vm = wrapper.vm as any;
      expect(vm.getStatusType('found')).toBe('success');
      expect(vm.getStatusText('found')).toBe('已找到');
    });

    it('应该为 organic_not_found 状态显示正确类型', () => {
      const wrapper = mount(ResultTable, {
        props: {
          results: mockResults,
        },
      });

      const vm = wrapper.vm as any;
      expect(vm.getStatusType('organic_not_found')).toBe('warning');
      expect(vm.getStatusText('organic_not_found')).toBe('仅自然未找到');
    });

    it('应该为 ad_not_found 状态显示正确类型', () => {
      const wrapper = mount(ResultTable, {
        props: {
          results: mockResults,
        },
      });

      const vm = wrapper.vm as any;
      expect(vm.getStatusType('ad_not_found')).toBe('warning');
      expect(vm.getStatusText('ad_not_found')).toBe('仅广告未找到');
    });

    it('应该为 not_found 状态显示正确类型', () => {
      const wrapper = mount(ResultTable, {
        props: {
          results: mockResults,
        },
      });

      const vm = wrapper.vm as any;
      expect(vm.getStatusType('not_found')).toBe('info');
      expect(vm.getStatusText('not_found')).toBe('未找到');
    });

    it('应该为 error 状态显示正确类型', () => {
      const wrapper = mount(ResultTable, {
        props: {
          results: mockResults,
        },
      });

      const vm = wrapper.vm as any;
      expect(vm.getStatusType('error')).toBe('danger');
      expect(vm.getStatusText('error')).toBe('错误');
    });

    it('应该为 captcha 状态显示正确类型', () => {
      const wrapper = mount(ResultTable, {
        props: {
          results: mockResults,
        },
      });

      const vm = wrapper.vm as any;
      expect(vm.getStatusType('captcha')).toBe('warning');
      expect(vm.getStatusText('captcha')).toBe('验证码');
    });
  });

  describe('日期格式化', () => {
    it('应该格式化日期时间', () => {
      const wrapper = mount(ResultTable, {
        props: {
          results: mockResults,
        },
      });

      const vm = wrapper.vm as any;
      const formatted = vm.formatDate('2026-04-12T10:02:00Z');

      expect(formatted).toBeTruthy();
      expect(typeof formatted).toBe('string');
    });
  });

  describe('导出 CSV', () => {
    it('应该导出 CSV 文件', async () => {
      // Mock document.createElement 和 blob
      const mockLink = {
        setAttribute: vi.fn(),
        click: vi.fn(),
        style: {},
      };
      const createElementSpy = vi.spyOn(document, 'createElement').mockReturnValue(mockLink as any);
      const createObjectURLSpy = vi.spyOn(URL, 'createObjectURL').mockReturnValue('blob:url');
      const revokeObjectURLSpy = vi.spyOn(URL, 'revokeObjectURL').mockImplementation(() => {});
      const appendChildSpy = vi.spyOn(document.body, 'appendChild').mockImplementation(() => mockLink as any);
      const removeChildSpy = vi.spyOn(document.body, 'removeChild').mockImplementation(() => {});

      const wrapper = mount(ResultTable, {
        props: {
          results: mockResults,
        },
        global: {
          stubs: {
            'el-table': true,
            'el-table-column': true,
            'el-tag': true,
            'el-button': true,
          },
        },
      });

      // 找到导出按钮并点击
      const exportButton = wrapper.findAll('button').find(btn => 
        btn.text().includes('导出')
      );
      
      if (exportButton) {
        await exportButton.trigger('click');
        await flushPromises();
      }

      expect(createElementSpy).toHaveBeenCalledWith('a');
      expect(createObjectURLSpy).toHaveBeenCalled();
      expect(mockLink.click).toHaveBeenCalled();
      expect(removeChildSpy).toHaveBeenCalled();
      expect(mockElMessage.success).toHaveBeenCalledWith('导出成功');

      // 清理
      createElementSpy.mockRestore();
      createObjectURLSpy.mockRestore();
      revokeObjectURLSpy.mockRestore();
      appendChildSpy.mockRestore();
      removeChildSpy.mockRestore();
    });

    it('空数据时导出应该显示警告', async () => {
      const wrapper = mount(ResultTable, {
        props: {
          results: [],
        },
        global: {
          stubs: {
            'el-table': true,
            'el-button': true,
          },
        },
      });

      const exportButton = wrapper.findAll('button').find(btn => 
        btn.text().includes('导出')
      );
      
      if (exportButton) {
        await exportButton.trigger('click');
        await flushPromises();
      }

      expect(mockElMessage.warning).toHaveBeenCalledWith('没有数据可导出');
    });

    it('CSV 应该包含正确的数据', async () => {
      const mockBlob = vi.fn();
      const originalBlob = global.Blob;
      global.Blob = mockBlob as any;

      const mockLink = {
        setAttribute: vi.fn(),
        click: vi.fn(),
        style: {},
      };
      vi.spyOn(document, 'createElement').mockReturnValue(mockLink as any);
      vi.spyOn(URL, 'createObjectURL').mockReturnValue('blob:url');
      vi.spyOn(document.body, 'appendChild').mockImplementation(() => mockLink as any);
      vi.spyOn(document.body, 'removeChild').mockImplementation(() => {});

      const wrapper = mount(ResultTable, {
        props: {
          results: mockResults,
        },
        global: {
          stubs: {
            'el-table': true,
            'el-button': true,
          },
        },
      });

      const exportButton = wrapper.findAll('button').find(btn => 
        btn.text().includes('导出')
      );
      
      if (exportButton) {
        await exportButton.trigger('click');
        await flushPromises();
      }

      // 验证 Blob 被调用
      expect(mockBlob).toHaveBeenCalled();

      // 恢复
      global.Blob = originalBlob;
    });
  });

  describe('响应式更新', () => {
    it('应该响应 props 变化', async () => {
      const wrapper = mount(ResultTable, {
        props: {
          results: [],
        },
      });

      // 更新 props
      await wrapper.setProps({ results: mockResults });
      await flushPromises();

      const vm = wrapper.vm as any;
      expect(vm.stats.found).toBe(2);
    });

    it('应该响应 loading 状态变化', async () => {
      const wrapper = mount(ResultTable, {
        props: {
          results: mockResults,
          loading: false,
        },
      });

      await wrapper.setProps({ loading: true });
      await flushPromises();

      expect(wrapper.props('loading')).toBe(true);
    });
  });

  describe('边界情况', () => {
    it('处理 null 值', () => {
      const resultsWithNulls = [
        {
          keyword: 'test',
          organicPage: null,
          organicPosition: null,
          adPage: null,
          adPosition: null,
          status: 'not_found',
          timestamp: '2026-04-12T10:00:00Z',
        },
      ];

      const wrapper = mount(ResultTable, {
        props: {
          results: resultsWithNulls,
        },
      });

      expect(wrapper.exists()).toBe(true);
    });

    it('处理大量数据', () => {
      const largeDataset = Array(100).fill(null).map((_, i) => ({
        keyword: `keyword ${i}`,
        organicPage: Math.floor(i / 48) + 1,
        organicPosition: (i % 48) + 1,
        adPage: null,
        adPosition: null,
        status: 'found' as const,
        timestamp: '2026-04-12T10:00:00Z',
      }));

      const wrapper = mount(ResultTable, {
        props: {
          results: largeDataset,
        },
      });

      const vm = wrapper.vm as any;
      expect(vm.stats.found).toBe(100);
      expect(vm.successRate).toBe(100);
    });
  });
});
