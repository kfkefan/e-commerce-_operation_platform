import React from 'react';

interface RankingResult {
  id: string;
  keyword: string;
  organicRank: number | null;
  adRank: number | null;
  status: 'found' | 'not_found' | 'error';
}

interface ResultTableProps {
  results: RankingResult[];
  isLoading?: boolean;
}

export const ResultTable: React.FC<ResultTableProps> = ({ results, isLoading = false }) => {
  if (isLoading) {
    return (
      <div className="bg-white rounded-lg shadow-md p-6">
        <h2 className="text-xl font-semibold mb-4 text-gray-800">查询结果</h2>
        <div className="flex items-center justify-center py-12">
          <div className="text-center">
            <svg className="animate-spin h-10 w-10 text-blue-600 mx-auto mb-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            <p className="text-gray-600">正在查询排名...</p>
          </div>
        </div>
      </div>
    );
  }

  if (results.length === 0) {
    return (
      <div className="bg-white rounded-lg shadow-md p-6">
        <h2 className="text-xl font-semibold mb-4 text-gray-800">查询结果</h2>
        <div className="text-center py-12">
          <svg className="h-16 w-16 text-gray-400 mx-auto mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
          <p className="text-gray-600">暂无数据，请先提交任务</p>
        </div>
      </div>
    );
  }

  const getStatusBadge = (status: RankingResult['status']) => {
    switch (status) {
      case 'found':
        return <span className="px-2 py-1 bg-green-100 text-green-800 text-xs rounded-full">已找到</span>;
      case 'not_found':
        return <span className="px-2 py-1 bg-yellow-100 text-yellow-800 text-xs rounded-full">未找到</span>;
      case 'error':
        return <span className="px-2 py-1 bg-red-100 text-red-800 text-xs rounded-full">错误</span>;
      default:
        return null;
    }
  };

  const renderRank = (rank: number | null) => {
    if (rank === null) {
      return <span className="text-gray-400">-</span>;
    }
    return (
      <span className={`font-medium ${rank <= 10 ? 'text-green-600' : rank <= 50 ? 'text-yellow-600' : 'text-gray-600'}`}>
        {rank}
      </span>
    );
  };

  return (
    <div className="bg-white rounded-lg shadow-md p-6">
      <h2 className="text-xl font-semibold mb-4 text-gray-800">查询结果</h2>
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                关键词
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                自然排名
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                广告排名
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                状态
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {results.map((result) => (
              <tr key={result.id} className="hover:bg-gray-50">
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                  {result.keyword}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm">
                  {renderRank(result.organicRank)}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm">
                  {renderRank(result.adRank)}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm">
                  {getStatusBadge(result.status)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};
