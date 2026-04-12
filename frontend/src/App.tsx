import React, { useState } from 'react';
import { Layout, Tabs, message } from 'antd';
import { InputPanel } from './components/InputPanel';
import { ResultTable } from './components/ResultTable';
import { TaskProgress } from './components/TaskProgress';
import { HistoryList } from './components/HistoryList';
import { useTaskPolling } from './hooks/useTask';
import './App.css';

const { Header, Content, Footer } = Layout;

/**
 * 主应用组件
 */
const App: React.FC = () => {
  const [currentTaskId, setCurrentTaskId] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<string>('create');

  // 使用轮询 Hook 获取任务状态
  const { task, isPolling, setIsPolling } = useTaskPolling(currentTaskId, 3000);

  /**
   * 任务创建成功回调
   */
  const handleTaskCreated = (taskId: string) => {
    setCurrentTaskId(taskId);
    setActiveTab('progress');
    message.success('任务创建成功，开始处理...');
  };

  /**
   * 任务完成回调
   */
  const handleTaskComplete = () => {
    setIsPolling(false);
    message.success('任务处理完成！');
  };

  return (
    <Layout className="app-layout">
      <Header className="app-header">
        <h1 className="app-title">ASIN 关键词排名追踪器</h1>
        <p className="app-subtitle">追踪亚马逊产品关键词排名，支持自然排名和广告排名</p>
      </Header>

      <Content className="app-content">
        <Tabs
          activeKey={activeTab}
          onChange={setActiveTab}
          items={[
            {
              key: 'create',
              label: '创建任务',
              children: (
                <InputPanel 
                  onTaskCreated={handleTaskCreated}
                />
              )
            },
            {
              key: 'progress',
              label: '任务进度',
              children: (
                <TaskProgress 
                  taskId={currentTaskId}
                  onComplete={handleTaskComplete}
                />
              ),
              disabled: !currentTaskId
            },
            {
              key: 'results',
              label: '结果查看',
              children: (
                <ResultTable 
                  taskId={currentTaskId}
                />
              ),
              disabled: !currentTaskId
            },
            {
              key: 'history',
              label: '历史记录',
              children: <HistoryList />
            }
          ]}
        />
      </Content>

      <Footer className="app-footer">
        <p>ASIN 关键词排名追踪器 v1.0.0 | 数据仅供参考</p>
      </Footer>
    </Layout>
  );
};

export default App;
