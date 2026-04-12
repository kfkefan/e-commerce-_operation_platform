/**
 * Vitest 测试设置文件
 */
import { config } from '@vue/test-utils';
import { vi } from 'vitest';

// 全局 Mock
config.global.mocks = {
  $t: (key: string) => key,
};

// Mock Element Plus
vi.mock('element-plus', () => ({
  ElMessage: {
    success: vi.fn(),
    error: vi.fn(),
    warning: vi.fn(),
    info: vi.fn(),
  },
  ElMessageBox: {
    confirm: vi.fn(),
    alert: vi.fn(),
  },
}));

// 重置 mocks
afterEach(() => {
  vi.clearAllMocks();
});
