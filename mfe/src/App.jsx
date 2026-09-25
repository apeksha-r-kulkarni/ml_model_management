import React, { useState } from 'react';
import AppLayout from './components/layout/AppLayout';
import Models from './pages/Models';
import Register from './pages/Register';

function App() {
  const [currentView, setCurrentView] = useState('models');
  const [registerInitialData, setRegisterInitialData] = useState(null);

  const handleAddNewVersion = (modelData) => {
    setRegisterInitialData(modelData);
    setCurrentView('register');
  };

  const handleNavigate = (view) => {
    if (view !== 'register') {
      setRegisterInitialData(null);
    }
    setCurrentView(view);
  };

  const renderView = () => {
    switch (currentView) {
      case 'models':
        return <Models onAddNewVersion={handleAddNewVersion} onRegisterNew={() => handleNavigate('register')} />;
      case 'register':
        return <Register initialData={registerInitialData} />;
      default:
        return <Models onAddNewVersion={handleAddNewVersion} onRegisterNew={() => handleNavigate('register')} />;
    }
  };



  return (
    <AppLayout currentView={currentView} setCurrentView={handleNavigate}>
      {renderView()}
    </AppLayout>
  );
}

export default App;

