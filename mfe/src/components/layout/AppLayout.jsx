import React from 'react';

export default function AppLayout({ currentView, setCurrentView, children }) {
  return (
    <div className="flex h-screen bg-gray-50 font-sans text-gray-900">
      {/* Sidebar */}
      <aside className="w-64 bg-gray-900 text-white flex flex-col shadow-lg z-10">
        <div className="p-6 border-b border-gray-800">
          <h2 className="text-2xl font-bold tracking-tight text-white flex items-center">
            <span className="bg-blue-600 text-white p-1 rounded mr-2 text-sm">ML</span> 
            Registry
          </h2>
        </div>
        <nav className="flex-1 px-4 py-6 space-y-2">
          {['models', 'register'].map((view) => (
            <button
              key={view}
              onClick={() => setCurrentView(view)}
              className={`w-full flex items-center px-4 py-3 text-sm font-medium rounded-md transition-colors ${
                currentView === view
                  ? 'bg-blue-600 text-white shadow-md'
                  : 'text-gray-300 hover:bg-gray-800 hover:text-white'
              }`}
            >
              {view === 'models' ? 'Models Inventory' : 'Register Model'}
            </button>
          ))}
        </nav>



        <div className="p-4 border-t border-gray-800 text-xs text-gray-500 text-center">
          ML Model Management v1.0
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 overflow-y-auto">
        <div className="p-8 pb-20">
          {children}
        </div>
      </main>
    </div>
  );
}
