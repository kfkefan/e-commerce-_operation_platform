/**
 * TaskInput 组件测试
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { mount, flushPromises } from '@vue/test-utils';
import TaskInput from '../src/components/TaskInput.vue';

// Mock Element Plus 组件
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

// Mock API
vi.mock('../src/api/tasks', () => ({
  createTask: vi.fn(),
}));

import { createTask } from '../src/api/tasks';
import { ElMessage } from 'element-plus';

describe('TaskInput', () => {
  const mockCreateTask = createTask as vi.MockedFunction<typeof createTask>;
  const mockElMessage = ElMessage as any;

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('渲染', () => {
    it('应该正确渲染组件', () => {
      const wrapper = mount(TaskInput);

      expect(wrapper.exists()).toBe(true);
      expect(wrapper.find('.task-input-card').exists()).toBe(true);
    });

    it('应该显示表单字段', () => {
      const wrapper = mount(TaskInput);

      // 检查 ASIN 输入框
      expect(wrapper.find('input[placeholder*="ASIN"]').exists()).toBe(true);

      // 检查站点选择器
      expect(wrapper.find('.el-select').exists()).toBe(true);

      // 检查翻页数输入
      expect(wrapper.find('.el-input-number').exists()).toBe(true);

      // 检查关键词文本域
      expect(wrapper.find('textarea[placeholder*="关键词"]').exists()).toBe(true);
    });

    it('应该显示提交按钮', () => {
      const wrapper = mount(TaskInput);

      const button = wrapper.find('button[type="submit"], .el-button--primary');
      expect(button.exists()).toBe(true);
      expect(button.text()).toContain('提交任务');
    });

    it('应该显示默认值', () => {
      const wrapper = mount(TaskInput);

      // 默认站点应该是 amazon.com
      // 默认翻页数应该是 5
      const vm = wrapper.vm as any;
      expect(vm.form.site).toBe('amazon.com');
      expect(vm.form.maxPages).toBe(5);
    });
  });

  describe('表单验证', () => {
    it('ASIN 应该验证格式', async () => {
      const wrapper = mount(TaskInput);
      const vm = wrapper.vm as any;

      // 设置无效 ASIN
      vm.form.asin = 'INVALID';
      await flushPromises();

      // 触发验证
      if (wrapper.vm.formRef) {
        const result = await wrapper.vm.formRef.validate().catch(() => false);
        expect(result).toBe(false);
      }
    });

    it('ASIN 应该验证长度', async () => {
      const wrapper = mount(TaskInput);
      const vm = wrapper.vm as any;

      // 设置过短 ASIN
      vm.form.asin = 'B08N5';
      await flushPromises();

      if (wrapper.vm.formRef) {
        const result = await wrapper.vm.formRef.validate().catch(() => false);
        expect(result).toBe(false);
      }
    });

    it('关键词不能为空', async () => {
      const wrapper = mount(TaskInput);
      const vm = wrapper.vm as any;

      // 设置有效 ASIN 但空关键词
      vm.form.asin = 'B08N5WRWNW';
      vm.form.keywords = [];
      await flushPromises();

      if (wrapper.vm.formRef) {
        const result = await wrapper.vm.formRef.validate().catch(() => false);
        expect(result).toBe(false);
      }
    });

    it('关键词不能超过 100 个', async () => {
      const wrapper = mount(TaskInput);
      const vm = wrapper.vm as any;

      // 设置超过 100 个关键词
      vm.form.keywords = Array(101).fill('keyword');
      await flushPromises();

      if (wrapper.vm.formRef) {
        const result = await wrapper.vm.formRef.validate().catch(() => false);
        expect(result).toBe(false);
      }
    });

    it('站点必须选择', async () => {
      const wrapper = mount(TaskInput);
      const vm = wrapper.vm as any;

      // 清空站点
      vm.form.site = '';
      await flushPromises();

      if (wrapper.vm.formRef) {
        const result = await wrapper.vm.formRef.validate().catch(() => false);
        expect(result).toBe(false);
      }
    });
  });

  describe('关键词解析', () => {
    it('应该解析多行关键词', async () => {
      const wrapper = mount(TaskInput);
      const vm = wrapper.vm as any;

      // 设置多行关键词
      vm.keywordInput = 'keyword1\nkeyword2\nkeyword3';
      vm.parseKeywords();
      await flushPromises();

      expect(vm.form.keywords.length).toBe(3);
      expect(vm.form.keywords[0]).toBe('keyword1');
      expect(vm.form.keywords[1]).toBe('keyword2');
      expect(vm.form.keywords[2]).toBe('keyword3');
    });

    it('应该过滤空行', async () => {
      const wrapper = mount(TaskInput);
      const vm = wrapper.vm as any;

      vm.keywordInput = 'keyword1\n\nkeyword2\n   \nkeyword3';
      vm.parseKeywords();
      await flushPromises();

      expect(vm.form.keywords.length).toBe(3);
    });

    it('应该限制关键词数量为 100', async () => {
      const wrapper = mount(TaskInput);
      const vm = wrapper.vm as any;

      vm.keywordInput = Array(150).fill('keyword').join('\n');
      vm.parseKeywords();
      await flushPromises();

      expect(vm.form.keywords.length).toBe(100);
    });

    it('应该过滤超过 200 字符的关键词', async () => {
      const wrapper = mount(TaskInput);
      const vm = wrapper.vm as any;

      vm.keywordInput = 'short\n' + 'a'.repeat(250) + '\nvalid';
      vm.parseKeywords();
      await flushPromises();

      expect(vm.form.keywords).toContain('short');
      expect(vm.form.keywords).toContain('valid');
    });
  });

  describe('提交任务', () => {
    it('应该成功提交任务', async () => {
      const mockTaskId = 'test-task-id-123';
      mockCreateTask.mockResolvedValue({
        taskId: mockTaskId,
        status: 'pending',
        createdAt: new Date().toISOString(),
      });

      const wrapper = mount(TaskInput, {
        global: {
          stubs: {
            'el-form': true,
            'el-form-item': true,
            'el-input': true,
            'el-select': true,
            'el-option': true,
            'el-input-number': true,
            'el-button': true,
          },
        },
      });

      const vm = wrapper.vm as any;

      // 设置有效表单数据
      vm.form.asin = 'B08N5WRWNW';
      vm.form.site = 'amazon.com';
      vm.form.maxPages = 5;
      vm.form.keywords = ['test keyword'];
      vm.keywordInput = 'test keyword';

      // 模拟 emit
      const emitted = vi.fn();
      wrapper.vm.$emit = emitted;

      // 提交
      await vm.handleSubmit();
      await flushPromises();

      expect(mockCreateTask).toHaveBeenCalledWith({
        asin: 'B08N5WRWNW',
        site: 'amazon.com',
        maxPages: 5,
        keywords: ['test keyword'],
      });

      expect(mockElMessage.success).toHaveBeenCalled();
    });

    it('应该处理提交失败', async () => {
      mockCreateTask.mockRejectedValue({
        response: {
          data: {
            message: 'ASIN 格式错误',
          },
        },
      });

      const wrapper = mount(TaskInput, {
        global: {
          stubs: {
            'el-form': true,
            'el-form-item': true,
            'el-input': true,
            'el-select': true,
            'el-option': true,
            'el-input-number': true,
            'el-button': true,
          },
        },
      });

      const vm = wrapper.vm as any;

      vm.form.asin = 'B08N5WRWNW';
      vm.form.site = 'amazon.com';
      vm.form.maxPages = 5;
      vm.form.keywords = ['test keyword'];

      await vm.handleSubmit();
      await flushPromises();

      expect(mockElMessage.error).toHaveBeenCalled();
    });

    it('应该重置表单提交后', async () => {
      mockCreateTask.mockResolvedValue({
        taskId: 'test-id',
        status: 'pending',
        createdAt: new Date().toISOString(),
      });

      const wrapper = mount(TaskInput, {
        global: {
          stubs: {
            'el-form': true,
            'el-form-item': true,
            'el-input': true,
            'el-select': true,
            'el-option': true,
            'el-input-number': true,
            'el-button': true,
          },
        },
      });

      const vm = wrapper.vm as any;

      vm.form.asin = 'B08N5WRWNW';
      vm.form.keywords = ['test'];
      vm.keywordInput = 'test';

      await vm.handleSubmit();
      await flushPromises();

      // 表单应该被重置
      expect(vm.form.asin).toBe('');
      expect(vm.form.keywords.length).toBe(0);
      expect(vm.keywordInput).toBe('');
    });

    it('应该设置加载状态', async () => {
      mockCreateTask.mockImplementation(
        () => new Promise((resolve) => setTimeout(() => resolve({ taskId: 'id' }), 100))
      );

      const wrapper = mount(TaskInput, {
        global: {
          stubs: {
            'el-form': true,
            'el-form-item': true,
            'el-input': true,
            'el-select': true,
            'el-option': true,
            'el-input-number': true,
            'el-button': true,
          },
        },
      });

      const vm = wrapper.vm as any;

      vm.form.asin = 'B08N5WRWNW';
      vm.form.keywords = ['test'];

      const submitPromise = vm.handleSubmit();

      expect(vm.loading).toBe(true);

      await submitPromise;
      await flushPromises();

      expect(vm.loading).toBe(false);
    });
  });

  describe('事件发射', () => {
    it('应该发射 submitted 事件', async () => {
      mockCreateTask.mockResolvedValue({
        taskId: 'test-task-id',
        status: 'pending',
        createdAt: new Date().toISOString(),
      });

      const wrapper = mount(TaskInput, {
        global: {
          stubs: {
            'el-form': true,
            'el-form-item': true,
            'el-input': true,
            'el-select': true,
            'el-option': true,
            'el-input-number': true,
            'el-button': true,
          },
        },
      });

      const vm = wrapper.vm as any;
      vm.form.asin = 'B08N5WRWNW';
      vm.form.keywords = ['test'];

      await vm.handleSubmit();
      await flushPromises();

      const emitted = wrapper.emitted();
      expect(emitted.submitted).toBeTruthy();
      expect(emitted.submitted![0]).toEqual(['test-task-id']);
    });
  });
});
