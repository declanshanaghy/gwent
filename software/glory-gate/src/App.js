import React from 'react';
import logo from './logo.svg';
import './App.css';
import GloryGate from './GloryGate'

function App() {
  return (
    <div className="App">
      <header className="App-header">
        <img src={logo} className="App-logo" alt="logo" />
        <h1>
          Glory Gate, the Entrance to Novigrad
        </h1>
        <GloryGate/>
      </header>
    </div>
  );
}

export default App;
