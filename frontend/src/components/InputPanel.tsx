import React, { useState } from 'react';

interface InputPanelProps {
  onSubmit: (data: { asin: string; keywords: string; pages: number }) => void;
  isLoading?: boolean;
}

export const InputPanel: React.FC<InputPanelProps> = ({ onSubmit, isLoading = false }) => {
  const [asin, setAsin] = useState('');
  const [keywords, setKeywords] = useState('');
  const [pages, setPages] = useState(1);
  const [error, setError] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    // Validation
    if (!asin.trim()) {
      setError('请输入 ASIN');
      return;
    }

    if (!keywords.trim()) {
      setError('请输入关键词');
      return;
    }

    if (pages < 1 || pages > 20) {
      setError('翻页数必须在 1-20 之间');
      return;
    }

    onSubmit({ asin: asin.trim(), keywords: keywords.trim(), pages });
  };

  return (
    <div className="bg-white rounded-lg shadow-md p-6 mb-6">
      <h2 className="text-xl font-semibold mb-4 text-gray-800">任务配置</h2>
      <form onSubmit={handleSubmit} className="space-y-4">
        {/* ASIN Input */}
        <div>
          <label htmlFor="asin" className="block text-sm font-medium text-gray-700 mb-1">
            ASIN
          </label>
          <input
            type="text"
            id="asin"
            value={asin}
            onChange={(e) => setAsin(e.target.value)}
            placeholder="例如：B08N5WRWNW"
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            disabled={isLoading}
          />
        </div>

        {/* Keywords Textarea */}
        <div>
          <label htmlFor="keywords" className="block text-sm font-medium text-gray-700 mb-1">
            关键词列表
          </label>
          <textarea
            id="keywords"
            value={keywords}
            onChange={(e) => setKeywords(e.target.value)}
            placeholder="每行一个关键词，例如：&#10;wireless earbuds&#10;bluetooth headphones&#10;noise cancelling"
            rows={5}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            disabled={isLoading}
          />
        </div>

        {/* Pages Selector */}
        <div>
          <label htmlFor="pages" className="block text-sm font-medium text-gray-700 mb-1">
            翻页数
          </label>
          <select
            id="pages"
            value={pages}
            onChange={(e) => setPages(Number(e.target.value))}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            disabled={isLoading}
          >
            {Array.from({ length: 20 }, (_, i) => i + 1).map((num) => (
              <option key={num} value={num}>
                {num} 页
              </option>
            ))}
          </select>
        </div>

        {/* Error Message */}
        {error && (
          <div className="bg-red-50 border border-red-200 text-red-600 px-4 py-2 rounded-md text-sm">
            {error}
          </div>
        )}

        {/* Submit Button */}
        <button
          type="submit"
          disabled={isLoading}
          className={`w-full py-2 px-4 rounded-md font-medium transition-colors ${
            isLoading
              ? 'bg-gray-400 cursor-not-allowed'
              : 'bg-blue-600 hover:bg-blue-700 text-white'
          }`}
        >
          {isLoading ? (
            <span className="flex items-center justify-center">
              <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
              处理中...
            </span>
          ) : (
            '开始任务'
          )}
        </button>
      </form>
    </div>
  );
};
