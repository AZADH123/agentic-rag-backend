import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { Toaster } from 'react-hot-toast'
import App from './App'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <BrowserRouter>
      <App />
      <Toaster
        position="top-right"
        toastOptions={{
          style: {
            background: '#131c2e',
            color: '#e2e8f0',
            border: '1px solid #1e2d4a',
            fontFamily: 'Inter, sans-serif',
            fontSize: '0.85rem',
          },
          success: { iconTheme: { primary: '#10b981', secondary: '#131c2e' } },
          error:   { iconTheme: { primary: '#ef4444', secondary: '#131c2e' } },
        }}
      />
    </BrowserRouter>
  </React.StrictMode>
)
