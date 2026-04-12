import React from 'react';

interface TaskProgressProps {
  currentKeyword: string;
  completedCount: number;
  totalCount: number;
  isRunning: boolean;
}

export const TaskProgress: React.FC<TaskProgressProps> = ({
  currentKeyword,
  completedCount,
  totalCount,
  isRunning,
}) => {
  const percentage = totalCount > 0 ? Math.round((completedCount / totalCount) * 100) : 0;

  if (!isRunning && completedCount === 0) {
    return null;
  }

  return (
    <div className="bg-white rounded-lg shadow-md p-6 mb-6">
      <h2 className="text-xl font-semibold mb-4 text-gray-800">任务进度</h2>
      
      {/* Progress Bar */}
      <div className="mb-4">
        <div className="flex justify-between mb-1">
          <span className="text-sm font-medium text-gray-700">
            {isRunning ? '处理中...' : '已完成'}
          </span>
          <span className="text-sm font-medium text-gray-700">
            {completedCount} / {totalCount}
          </span>
        </div>
        <div className="w-full bg-gray-200 rounded-full h-2.5">
          <div
            className={`h-2.5 rounded-full transition-all duration-300 ${
              isRunning ? 'bg-blue-600' : 'bg-green-600'
            }`}
            style={{ width: `${percentage}%` }}
          ></div>
        </div>
        <p className="text-sm text-gray-600 mt-1">{percentage}% 完成</p>
      </div>

      {/* Current Keyword */}
      {isRunning && currentKeyword && (
        <div className="bg-blue-50 border border-blue-200 rounded-md p-4">
          <div className="flex items-start">
            <svg className="animate-spin h-5 w-5 text-blue-600 mt-0.5 mr-3" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            <div>
              <p className="text-sm font-medium text-blue-800">当前处理</p>
              <p className="text-sm text-blue-600 mt-1 break-all">{currentKeyword}</p>
            </div>
          </div>
        </div>
      )}

      {/* Completion Status */}
      {!isRunning && completedCount > 0 && (
        <div className="bg-green-50 border border-green-200 rounded-md p-4">
          <div className="flex items-center">
            <svg className="h-6 w-6 text-green-600 mr-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <div>
              <p className="text-sm font-medium text-green-800">任务完成</p>
              <p className="text-sm text-green-600 mt-1">
                已成功处理 {completedCount} 个关键词
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
