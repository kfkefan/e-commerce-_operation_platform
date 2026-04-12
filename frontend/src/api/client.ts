import axios from 'axios';

// 创建 Axios 实例
const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:3000/api/v1',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json'
  }
});

// 请求拦截器
apiClient.interceptors.request.use(
  (config) => {
    // 可以在这里添加认证 token
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// 响应拦截器
apiClient.interceptors.response.use(
  (response) => {
    return response.data;
  },
  (error) => {
    // 统一错误处理
    if (error.response) {
      const { status, data } = error.response;
      
      switch (status) {
        case 400:
          console.error('请求参数错误:', data);
          break;
        case 404:
          console.error('资源不存在:', data);
          break;
        case 429:
          console.error('请求频率超限:', data);
          break;
        case 500:
          console.error('服务器错误:', data);
          break;
        default:
          console.error('请求失败:', data);
      }
    } else if (error.request) {
      console.error('网络错误:', error.message);
    } else {
      console.error('请求配置错误:', error.message);
    }
    
    return Promise.reject(error);
  }
);

export default apiClient;
